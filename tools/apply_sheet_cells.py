# -*- coding: utf-8 -*-
"""Pull a specific set of cells down from a new sheet snapshot, three-way and guarded.

For the common round: "I fixed a term on the sheet, here is the export."  Not a full
merge — `--match` narrows it to the cells you actually mean, so a terminology pass
does not drag every other unrelated edit along with it.

Three-way, because the user edits the packed game too (see the merge memory):

    new == build                 -> đã có, bỏ qua
    new != build, base == build  -> áp
    new != build, base != build  -> hai bên đều đổi, BÁO rồi bỏ qua

Ids come from the sheet's own ID column:

    76/txt/0011                      -> ScenarioData scenarioID 76, text[11]
    TerminalHomeAlertData/alert/id71 -> json bundle, that asset, field, entry id
    DictionaryData/dic_body/id102    -> ditto, but DictionaryData keys on `no` (KEY_OF)

Guards on every cell before it is written:

- `[...]` tag multiset must match, so a cell cannot rewrite a lookup key
- `[主人公]` must be present on both sides or neither
- quotes must balance (`"` even, 「」/『』 counts equal)
- **hard line breaks are carried from the build**, never taken from the sheet: the
  `sd_*` Vietnamese column is one flat line, so writing it verbatim flattens the
  layout (1 530 breaks were destroyed that way once).  difflib maps the old break
  positions onto the new wording.
- an `sd_*` cell that merely **mirrors a Genebark chat message** is skipped, naming the
  Genebark cell that owns it: writing it is futile, because `fix_chat_use_genebark.py
  --apply` — the mandatory first step after every merge — copies the Genebark wording
  straight back over it, silently.  184 pairs, recomputed every run from
  `fix_chat_use_genebark.pairs()`; `--take-sheet` deliberately does not unlock them.
  The pair count is asserted, because a stock tree that is *present but wrong* makes
  `pairs()` quietly return fewer (measured: 93 against the translated tree) and the
  guard would switch itself off without a word.

`--check-chat` audits all 184 pairs on one snapshot regardless of what changed this
round — the in-merge "SỬA NHẦM Ô" warning only fires the single round a cell moves,
so without it a wrong-cell edit goes quiet forever once the snapshot becomes the base.

    python tools\\apply_sheet_cells.py --check-chat
    python tools\\apply_sheet_cells.py --match mainframe
    python tools\\apply_sheet_cells.py --match mainframe --apply
    python tools\\apply_sheet_cells.py --new "…(23).xlsx" --base "…(22).xlsx" --match X
    python tools\apply_sheet_cells.py --take-sheet=71/txt/0064,80/txt/0170 --apply
"""
import ast
import difflib
import glob
import io
import json
import os
import re
import shutil
import sys
import types

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402
from openpyxl import load_workbook   # noqa: E402

SCENARIO = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
JSONB = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
SNAPSHOTS = r"D:\Downloads\UNLOGICAL_v2*.xlsx"

APPLY = "--apply" in sys.argv
# Soi ĐỨNG YÊN cả bảng cặp trên snapshot mới nhất, không phụ thuộc vòng này có ô nào
# đổi hay không — xem `check_chat()`.
CHECK_CHAT = "--check-chat" in sys.argv
AUDIT = "--audit-sheet" in sys.argv


def arg(name, default=None):
    """Đọc `--ten=gia-tri`, và cả `--ten gia-tri` cách nhau bằng khoảng trắng.

    Dạng cách nhau bằng khoảng trắng trước đây bị BỎ QUA KHÔNG MỘT LỜI: `--new` không
    khớp tiền tố `--new=` nên `arg()` trả None, `main()` lặng lẽ rơi về `newest_two()`
    và merge HAI SNAPSHOT MỚI NHẤT thay cho cặp vừa chỉ định — với `--apply` là ghi
    nhầm hẳn một bộ ô. Chỉ hai dòng "sheet mới/sheet nền" ở đầu output tố cáo. Mà chính
    docstring đầu file lại đang dạy đúng dạng đó (`--new "…(23).xlsx"`), nên đây là cái
    bẫy tự kho dựng cho người dùng của nó. Lỗi có sẵn, không do đợt chốt chặn ô dẫn xuất.

    Giá trị bắt đầu bằng `--` thì không ăn: `--match --apply` phải ra None chứ không
    được nuốt mất cờ `--apply`.
    """
    for i, a in enumerate(sys.argv):
        if a.startswith("--%s=" % name):
            return a.split("=", 1)[1]
        if (a == "--%s" % name and i + 1 < len(sys.argv)
                and not sys.argv[i + 1].startswith("--")):
            return sys.argv[i + 1]
    return default


MATCH = arg("match")
# `--take-sheet=id,id,…`: những ô đã xem bằng mắt và chốt "sheet thắng", dù build cũng đã
# đổi. Sinh ra khi snapshot đã merge bị **tải đè lên cùng tên file** nên không còn bản nền
# nào khớp build: vòng (32) export lại 18/08 làm 27 ô báo "cả hai bên đổi" mà 26 trong số
# đó hai bên chỉ khác dấu nháy. Phải liệt kê id tường minh — không có chế độ "lấy tất".
TAKE = {x.strip() for x in (arg("take-sheet") or "").split(",") if x.strip()}
# `--force-sheet=id,…`: kéo ô vào `todo` DÙ sheet không đổi giữa hai snapshot.
# Cần vì phép so ba chiều chỉ nhìn ô có `new != base`; ô mà sheet ĐÚNG, build SAI,
# nhưng sheet đứng yên thì không vòng nào thấy (xem `audit_sheet`). Đây là đường
# duy nhất để hành động theo kết quả `--audit-sheet`. Ngầm bật `--take-sheet` cho
# chính những id đó, vì theo định nghĩa build đang khác.
FORCE = {x.strip() for x in (arg("force-sheet") or "").split(",") if x.strip()}

TAG = re.compile(r"\[[^\[\]\n]*\]")
STOCK_ROOT = r"D:\Downloads\UNLOGICAL_v2\Data\StreamingAssets"
STOCK_SCEN = os.path.join(STOCK_ROOT, "scenario", "scenario01")
STOCK_JSON = os.path.join(STOCK_ROOT, "json", "json")
SD_ID = re.compile(r"^(\d+)/txt/(\d+)$")
DATA_ID = re.compile(r"^([A-Za-z&]+Data)/([A-Za-z_]+)/id(\d+)$")
# Chat Genebark: id KHÔNG mang khoá `id` mà mang **chỉ số tuyệt đối** trong `data[]`;
# `gid` có thể là nhiều nhóm nối bằng `;` (`g23;24cユーリ_294`) nên đừng ăn một số.
# Chỉ mở `chat`. `spk` là KHOÁ (`player` / `藍`), sheet để VN == JP — dịch là hỏng chat.
GB_ID = re.compile(r"^GenebarkChatMainData/chat/g[\d;]+c.+?_(\d+)$")
# Lựa chọn: `selText[idx]` là JSON LỒNG trong JSON — `{"target":[…]}` — nên phải parse
# rồi ghi lại, không thay chuỗi thô được.
SEL_ID = re.compile(r"^(\d+)/sel/(\d+)/(\d+)$")
# Tiêu đề câu hỏi Q&A: `Q&AData.list[g].title[q]`, chuỗi trần.
QA_ID = re.compile(r"^Q&AData/qa_title/g(\d+)_q(\d+)$")
# Thông báo Terminal: `{sID}/cmd/{n}` = lệnh thứ n trong `scriptText` của scenario đó.
# CHỈ đếm lệnh có NGOẶC KÉP `text="…"` — bên xuất sheet bỏ qua dạng không ngoặc, và bản
# gốc có đúng một chỗ như thế (`71` @12609, `敗北者が確定しました…` chưa dịch). Tính cả nó
# thì lệch chỉ số từ đó trở đi; chỉ đếm dạng có ngoặc thì khớp 116/116.
CMD_ID = re.compile(r"^(\d+)/cmd/(\d+)$")
_Q = chr(34)
CMD_ARG = re.compile(r"\[(?:terinfo|geninfo|select_monitor)\b[^\]]*?text=" + _Q + r"([^" + _Q + r"]*)" + _Q)


def backup_path(base):
    """Không bao giờ **bỏ qua** backup vì tên đã tồn tại.

    Tên backup lấy từ tên file snapshot, mà người dùng tải lại **đè lên cùng tên** (memory
    merge: "N là thứ tự tải, không phải thời gian"). Nên `_backup\\scenario01.UNLOGICAL_v2(32)`
    đã có nghĩa là *vòng trước cùng tên sheet*, không phải vòng này — bỏ qua là mất đúng
    cái mốc để lùi một bước. Thật: `(32)` được export lại 18/08 14:11 sau khi vòng `(32)`
    đầu đã merge xong, hai nội dung khác nhau 670 ô.
    """
    if not os.path.exists(base):
        return base
    i = 2
    while os.path.exists("%s-%d" % (base, i)):
        i += 1
    return "%s-%d" % (base, i)


def newest_two():
    cands = sorted(glob.glob(SNAPSHOTS), key=os.path.getmtime, reverse=True)
    if len(cands) < 2:
        raise SystemExit("cần ít nhất hai snapshot khớp " + SNAPSHOTS)
    return cands[0], cands[1]


def read_sheet(path):
    """{id: (tiếng Việt, tiếng Nhật)} — sd_* dịch ở cột D, Nhật ở cột C; tab *Data
    dịch ở cột C, Nhật ở cột B.

    **Làm phẳng `\\n` của sheet ngay ở đây.** Quy ước của cả tool là "sheet giữ câu chữ,
    build giữ ngắt dòng" — nên mọi so sánh phía dưới đều làm phẳng phía build
    (`cur.replace("\\n", " ")`). 56/41.247 ô của snapshot (32) lại có `\\n` thật, và
    những ô đó thì so nguyên văn *không bao giờ* khớp: `80/txt/0166` bị báo "cả hai bên
    đổi" trong khi thực tế chỉ sheet đổi (dấu `‘ ’` cong → `"`). `carry_breaks()` cũng
    giả định phía mới là một dòng phẳng, nên để `\\n` sống sót tới đó là chồng ngắt dòng.
    """
    wb = load_workbook(path, read_only=True, data_only=True)
    out = {}
    unknown = {}
    for ws in wb.worksheets:
        vcol, jcol = (3, 2) if ws.title.startswith("sd_") else (2, 1)
        for row in ws.iter_rows(values_only=True):
            if not row or not isinstance(row[0], str):
                continue
            key = row[0].strip()
            if not (SD_ID.match(key) or DATA_ID.match(key) or GB_ID.match(key)
                    or SEL_ID.match(key) or QA_ID.match(key)
                    or CMD_ID.match(key)):
                # KHÔNG bỏ im lặng. Một `continue` trần ở đây từng che **3003 hàng**
                # của snapshot (42) mà không in ra một chữ nào: cả tab
                # `GenebarkChatMainData` (2388 hàng), 449 hàng `sel`, 116 hàng `cmd`,
                # 50 hàng `qa_title`. Sửa mấy ô đó trên sheet thì tool không hề thấy,
                # nên chúng không bao giờ xuống game — và không có dấu hiệu gì.
                # Xem tools/README.md "ID sheet mà tool không đọc".
                if "/" in key:
                    rec = unknown.setdefault(id_shape(key), [0, key, set()])
                    rec[0] += 1
                    rec[2].add(ws.title)
                continue
            val = row[vcol] if len(row) > vcol and isinstance(row[vcol], str) else ""
            jp = row[jcol] if len(row) > jcol and isinstance(row[jcol], str) else ""
            val = val.replace("\r\n", "\n")
            if ws.title.startswith("sd_"):
                # `sd_*` giữ quy ước cũ: build sở hữu ngắt dòng, sheet chỉ giữ câu chữ.
                val = val.replace("\n", " ")
            else:
                # Tab *Data thì SHEET sở hữu ngắt dòng. Đổi Alt+Enter thành dấu `\n` văn
                # bản để đi tiếp bằng đúng đường của `expand_breaks()`; gộp khoảng trắng
                # hai bên, vì `space + Alt+Enter` mà để nguyên sẽ thành space đôi rồi
                # `carry_breaks` chỉ ăn một cái — đúng lỗi space rác của vòng (40).
                val = re.sub(r"[ \t　]*\n[ \t　]*", BS_N, val)
            out[key] = (val, jp)
    wb.close()
    return out, unknown


ALERT = "TerminalHomeAlertData/"
# Hai bản Nhật cùng một câu nhưng gõ riêng cho hai chỗ hiện: bản alert có `：` đầu dòng
# tên, bản terinfo không. Bỏ khoảng trắng / `　` / `：` trước khi so.
NORM_JP = re.compile(r"[\s　：:]+")


def norm_jp(s):
    return NORM_JP.sub("", str(s).replace(BS_N, ""))


# `cmd` và `TerminalHomeAlertData` là CẶP SINH ĐÔI: bản gốc 1.0.2 tự nó có hai chuỗi cho
# cùng một sự việc — `[terinfo]` hiện đè lên cảnh lúc nó xảy ra, `alert` nằm trong nhật ký
# app Terminal đọc lại sau. 30 cặp như vậy, khác nhau đúng dấu `：` và cách xuống dòng.
#
# Đã từng cho `cmd` DẪN XUẤT từ `alert` (vô điều kiện, rồi rút lại thành "chỉ điền ô
# trống"). Bỏ hẳn từ snapshot (62): người dịch đã điền đủ cả 30 cặp nên không còn ô nào
# để điền, và hai chỗ hiện khác nhau thì vốn được phép dùng câu khác nhau.
#
# Cái còn phải giữ là `norm_jp`: hai ô sinh đôi thường mang CÙNG bản dịch, mà bản Nhật
# lại khác nhau — đúng dấu hiệu mà `duplicate_paste` đi tìm. Chuẩn hoá trước khi so thì
# chúng thành một, và lưới không kêu oan nữa.


def id_shape(key):
    """Dạng chuẩn hoá của một ID để gộp báo cáo: số -> `N`, chữ ngoài ASCII -> `<c>`."""
    return re.sub(r"[^\x00-\x7f]+", "<c>", re.sub(r"\d+", "N", key))


def report_unknown(unknown, label):
    """In TO TIẾNG những hàng có ID mà `read_sheet` không đọc được.

    Chỉ báo, không chặn: vòng merge vẫn chạy như cũ cho các ô đọc được. Mục đích là
    không bao giờ để lặp lại tình trạng "sheet sửa rồi mà game không đổi, không ai
    biết vì sao".
    """
    if not unknown:
        return
    tot = sum(v[0] for v in unknown.values())
    print("!! %s: %d hàng có ID mà tool KHÔNG đọc được (%d dạng)."
          % (label, tot, len(unknown)))
    print("   Sửa những ô này trên sheet cũng KHÔNG xuống được game — chưa có đường ghi.")
    for sh in sorted(unknown, key=lambda k: (-unknown[k][0], k)):
        n, ex, tabs = unknown[sh]
        t = ", ".join(sorted(tabs)[:3]) + ("…" if len(tabs) > 3 else "")
        print("   %6d  %-42s ví dụ: %s" % (n, sh, ex))
        print("           tab: %s" % t)
    print('   (xem tools/README.md "ID sheet mà tool không đọc")')
    print()


# Nhãn field trên sheet KHÔNG phải tên field thật, và khoá gốc cũng không luôn là `data`.
# Đo 18/08 trên snapshot (37): trong 11 nhãn sheet dùng chỉ `TerminalHomeAlertData/alert`
# là khớp thẳng, `rule_body` có nhánh riêng, còn lại 262 hàng **không bao giờ áp được** —
# 5 nhãn sai tên field và 257 hàng không có id tương ứng trong asset.
# Lớp lỗi này ẩn được lâu vì tool chạy theo diff: một nhãn sai chỉ lộ ra ở vòng nào
# đúng mấy hàng đó tình cờ đổi (vòng (39): 6/44 hàng note đổi -> 6 dòng "không có field").
FIELD_MAP = {
    ("GenebarkNoteData", "note"): ("data", "text"),
    ("GenebarkNewsData", "news_title"): ("data", "title"),
    ("GenebarkNewsData", "news_body"): ("data", "text"),
    ("TerminalControlSkillData", "skill_name"): ("data", "request"),
    ("TerminalControlSkillData", "skill_desc"): ("data", "caption"),
    ("TerminalProfileData", "prof_name"): ("info", "name"),
    ("TerminalProfileData", "prof_comment"): ("info", "comment"),
    ("ShortStoryData", "ss_title"): ("list", "title"),
    ("TerminalRuleData", "rule_title"): ("data.items", "title"),
    ("TerminalHomeAlertData", "alert"): ("data", "alert"),
    ("DictionaryData", "dic_title"): ("data", "title"),
    ("DictionaryData", "dic_ruby"): ("data", "ruby"),
    ("DictionaryData", "dic_body"): ("data", "text"),
}

# Khoá tra mục cũng không phải asset nào cũng là `id`. DictionaryData khoá bằng `no`
# (80 mục, không có field `id` nào) — tra bằng `id` thì mọi hàng của tab từ điển báo
# "không có id N", đúng lớp lỗi ẩn lâu như mấy nhãn field sai ở trên. Tab từ điển do
# `tools\export_dictionary_sheet.py` sinh ra, vẫn dùng dạng id `…/id<no>` ở cột A cho
# khớp `DATA_ID`; chỗ đổi là ở đây, không phải ở cột A.
KEY_OF = {"DictionaryData": "no"}

# `\n` dạng VĂN BẢN (U+005C U+006E) là cách các tab *Data khai báo ngắt dòng — asset thì
# chỉ dùng U+000A. Snapshot (37) có 2 dấu như vậy ở note id1, khớp đúng 3 dòng của build;
# (39) xoá hết, làm 6 note thành một dòng phẳng. Xem [[unlogical-text-overflow]].
BS_N = chr(92) + "n"        # viết bằng chr() để khỏi lẫn với escape thật


def expand_breaks(s):
    """`\\n` văn bản -> U+000A, GỘP khoảng trắng hai bên.

    Sheet hay gõ `ngày 9 \\n・ Tài liệu` (có space trước dấu), để nguyên thì dòng trên
    mang space đuôi — cùng lớp lỗi với `space + Alt+Enter` thành space đôi.
    """
    return re.sub(r"[ \t　]*%s[ \t　]*" % re.escape(BS_N), "\n", s)


def entries(dj, root):
    """List các mục của asset, theo đúng khoá gốc của từng asset.

    Khoá *nhận dạng* mục thì xem `KEY_OF` — phần lớn asset dùng `id`, DictionaryData
    dùng `no`.
    """
    if root == "data.items":
        out = []
        for g in dj.get("data", []):
            out.extend(g.get("items", []))
        return out
    rows = dj.get(root)
    return rows if isinstance(rows, list) else []


def field_get(ent, field):
    """Giá trị field, gỡ một tầng `{"jp": …}` nếu có (note/news bọc thế)."""
    v = ent.get(field)
    return v.get("jp", "") if isinstance(v, dict) else v


def field_set(ent, field, val):
    """Ghi field, giữ nguyên tầng `{"jp": …}` nếu mục vốn bọc thế."""
    if isinstance(ent.get(field), dict):
        ent[field]["jp"] = val
    else:
        ent[field] = val


# Bản mã hoá JSON của asset dùng dấu phân cách SÍT, không có space. Phải khớp đúng thì
# mới tìm lại được nguyên mục trong chuỗi thô — xem `json_edits`.
JDUMP = dict(ensure_ascii=False, separators=(",", ":"))


RULE_ID = re.compile(r"^([A-Za-z&]+Data)/rule_body/id(\d+)$")


def read_rule_rows(path):
    """{(id, trang): tiếng Việt} cho tab TerminalRuleData.

    **Giữ thứ tự hàng**: mỗi id lặp lại một hàng cho mỗi trang, hàng thứ k là
    `content[k]`. Nhét vào dict theo id là gộp 39 hàng thành 21 và tab trông như
    không map được (memory `unlogical-sheet-merge`).
    """
    wb = load_workbook(path, read_only=True, data_only=True)
    out, seen = {}, {}
    for ws in wb.worksheets:
        if not ws.title.startswith("TerminalRuleData"):
            continue
        for row in ws.iter_rows(values_only=True):
            if not row or not isinstance(row[0], str):
                continue
            m = RULE_ID.match(row[0].strip())
            if not m:
                continue
            i = int(m.group(2))
            k = seen.get(i, -1) + 1
            seen[i] = k
            out[(i, k)] = row[2] if len(row) > 2 and isinstance(row[2], str) else ""
    wb.close()
    return out


def merge_rule_text(build, sheet):
    """Lấy CÂU CHỮ của sheet, giữ KHOẢNG TRẮNG ĐẦU DÒNG của build.

    Sheet đã rã hết `　` thành một space ASCII và biến dòng trắng thành một dấu
    cách, nên áp nguyên văn là ép thụt lề còn 1/3 và phá cả bậc bullet của trang
    RULE. None nếu số dòng hai bên khác nhau — chỗ đó cần người xem.
    """
    b, s = build.split("\n"), sheet.split("\n")
    if len(b) != len(s):
        return None
    out = []
    for bl, sl in zip(b, s):
        if not bl.strip():                 # dòng trắng của build giữ nguyên
            out.append(bl)
            continue
        lead = bl[:len(bl) - len(bl.lstrip("　 "))]
        out.append(lead + sl.strip())
    return "\n".join(out)


def duplicate_paste(todo, skip=()):
    """Bắt lỗi "bản dịch rơi vào sai ô": hai ô đổi trong cùng vòng mà bản dịch mới
    giống nhau từng chữ trong khi bản Nhật của chúng khác nhau — dấu hiệu dán đè.

    Đã bắt được thật ở snapshot (24): `71/txt/0379` mang bản dịch của `71/txt/0377`.
    """
    # `skip`: ô đã được người duyệt liệt kê tường minh qua --force-sheet. Lưới này so
    # "cùng bản dịch mới, khác bản Nhật", nên nó bắt oan các thán từ ngắn giống nhau
    # (`「...!」` xuất hiện ở 9 ô, bản Nhật `「……！」` và `「――、」`). Với ô đã duyệt thì
    # tín hiệu đó không còn giá trị.
    by_val = {}
    for key, bv, nv, jp in todo:
        if key in skip:
            continue
        by_val.setdefault(nv, []).append((key, jp, bv))
    bad = set()
    for nv, rows in by_val.items():
        # So bản Nhật ĐÃ CHUẨN HOÁ. Cặp `cmd`/`alert` sinh đôi chỉ khác dấu `：` và cách
        # xuống dòng; để nguyên thì chúng đếm là "hai bản Nhật khác nhau" và lưới báo
        # dán đè cho một việc hoàn toàn đúng (96/cmd/0001 với alert/id66).
        if len(rows) < 2 or len({norm_jp(jp) for _, jp, _ in rows}) < 2:
            continue
        # Trùng nhau TỪ TRƯỚC vòng này thì không phải dán đè. Dán đè tạo ra va chạm MỚI;
        # còn `70/txt/0748` / `0864` / `1036` vốn đã dùng chung một bản dịch từ lâu — ba
        # câu chỉ khác nhau dấu `、` và thể lịch sự (`思う` / `思います`), tức các nhánh
        # rẽ của cùng một lời thoại, và người dịch cố ý cho chúng cùng một câu. Vòng (84)
        # chỉ bỏ ruby `Operator` ở cả ba, thế mà lưới báo hai ô "dán đè".
        #
        # Nhánh `ratio` bên dưới không cứu được: cả ba sửa nhẹ như nhau nên tỉ lệ xấp xỉ
        # bằng nhau, `max` chọn bừa một ô rồi kết tội hai ô kia.
        if len({bv for _, _, bv in rows}) < 2:
            continue
        # Ô nào bị dán đè thì bản mới của nó KHÁC XA bản cũ của chính nó; ô lành chỉ
        # sửa nhẹ. Nhờ vậy không chặn oan ô lành trong cùng nhóm.
        ratio = {key: difflib.SequenceMatcher(None, bv, nv).ratio() for key, _, bv in rows}
        keep = max(ratio, key=ratio.get)
        for key in ratio:
            if key != keep or ratio[keep] < 0.6:
                bad.add(key)
    return bad


def load_text(path, name):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name == "TextAsset" and o.read().m_Name == name:
            d = o.read()
            raw = d.m_Script
            if not isinstance(raw, str):
                raw = bytes(raw).decode("utf-8")
            return env, d, raw
    raise SystemExit("không thấy %s trong %s" % (name, path))


def carry_breaks(old, new):
    """Đặt lại các `\\n` của bản build lên câu chữ mới, theo vị trí ký tự đã khớp."""
    if "\n" not in old:
        return new
    flat = old.replace("\n", " ")
    sm = difflib.SequenceMatcher(None, flat, new, autojunk=False)
    mapping = {}
    for a, b, n in sm.get_matching_blocks():
        for i in range(n):
            mapping[a + i] = b + i
    out = list(new)
    marks = []
    for i, c in enumerate(flat):
        if c == " " and old[i] == "\n":
            j = mapping.get(i)
            if j is not None and j < len(out) and out[j] == " ":
                marks.append(j)
    for j in marks:
        out[j] = "\n"
    got = "".join(out)
    if got.count("\n") != old.count("\n"):
        return None            # không đặt lại đủ -> để người xem quyết
    return got


RUBY = re.compile(r"\[([^\[\]\n']*?)'([^\[\]\n]*?)\]")
DIC = re.compile(r"\[dic\s+no=(\d+)\s+text=([^\[\]\n]*)\]")


def tag_key(t):
    """Khoá so sánh tag: phần nào là KHOÁ TRA CỨU thì so nguyên văn, phần nào chỉ để
    hiển thị thì bỏ qua.

    - `[gốc'ruby]`: cả hai nửa đều là chữ hiển thị, nên **cho phép đảo** (so theo tập
      hợp) — đó là đợt sửa `[Người lựa chọn'Selector]` -> `[Selector'Người lựa chọn]`.
      Đổi *nội dung* một nửa thì vẫn bị chặn.
    - `[dic no=N text=X]`: `no` là khoá, `text` là chữ hiển thị.
    - còn lại (lệnh diễn xuất, `[se file=…]`, `[主人公]`) so nguyên văn.
    """
    m = RUBY.fullmatch(t)
    if m and not t.startswith("[dic "):
        return "RUBY:" + "|".join(sorted([m.group(1), m.group(2)]))
    m = DIC.fullmatch(t)
    if m:
        return "DIC:" + m.group(1)
    return t


def is_ruby(t):
    return bool(RUBY.fullmatch(t)) and not t.startswith("[dic ")


# Những ô mà mất CẢ HAI nửa ruby là ĐÚNG chứ không phải xoá hụt. Danh sách phải nhỏ
# và mỗi mục phải nói rõ vì sao — đây là chỗ duy nhất tắt được chốt ruby.
RUBY_DROP_OK = {
    # 105/txt/0293 — `主の記憶をもとに、登場人物も忠実に再現されます`.
    # `再現される` là "được tái hiện", một động từ. Bản dịch cũ đọc nhầm nó thành tên
    # thuật ngữ: "các nhân vật cũng được [Kính giới'Recollection] trung thực". Vòng (87)
    # sửa thành "được tái hiện lại một cách chuẩn xác nhất", nên thuật ngữ biến mất hoàn
    # toàn là đúng — nó vốn không được phép có mặt trong câu này.
    "105/txt/0293",
}


def ruby_change_ok(old, new, key=None):
    """Tag ruby được phép đổi theo ba cách: giữ nguyên, **đảo hai nửa**, hoặc **bỏ tag
    mà giữ lại một nửa làm chữ thường** (vòng (28) bỏ gloss: `[Thiên thần tập sự'Spirit]`
    -> `Spirit`). Mất tag mà cả hai nửa cũng mất thì là xoá hụt — chặn, trừ `RUBY_DROP_OK`."""
    if key in RUBY_DROP_OK:
        return None
    for t in TAG.findall(old):
        if not is_ruby(t):
            continue
        if t in new:
            continue
        m = RUBY.fullmatch(t)
        if "[%s'%s]" % (m.group(2), m.group(1)) in new:
            continue
        # So KHÔNG phân biệt hoa/thường: một nửa ruby thường đổi vai khi bỏ tag, từ tên
        # riêng đứng đầu thành danh từ chung giữa câu. `[Đình Chỉ'Kỹ năng]` -> `kỹ năng
        # Ngưng đọng` vẫn giữ nửa `Kỹ năng`, chỉ khác chữ hoa — so nguyên văn thì chặn oan.
        low = new.lower()
        if m.group(1).lower() in low or m.group(2).lower() in low:
            continue
        return "mất tag ruby %s mà không giữ lại nửa nào" % t
    return None


_STOCK_TAGS = None


def stock_tags():
    """Tập MỌI `[...]` từng xuất hiện trong dữ liệu GỐC 1.0.2.

    Dùng để phân biệt KHOÁ TRA CỨU thật với ngoặc vuông do bản dịch tự đẻ ra.

    Chốt `lookup` trong `guards()` vốn coi mọi tag không-ruby không-dic là khoá, nên nó
    chặn cả việc SỬA một thẻ ruby viết hỏng. Bản gốc chỉ có **3** ngoặc trần trong
    `text[]` — `[posteffect colorinvert start|end]` và `[wait time=500]` — còn build có
    22, tức 19 cái mới sinh ra khi dịch `[育成者'トレーナー]` thành `[người huấn luyện]`:
    giữ ngoặc mà bỏ mất dấu `'`, thành thứ không phải ruby, không phải `[dic]`, không
    phải lệnh nào. Engine sẽ in nguyên dấu ngoặc ra màn hình hoặc nuốt cả cụm.

    Tag nào KHÔNG có trong bản gốc thì không thể là khoá tra cứu — engine chưa bao giờ
    biết tới nó. Bỏ nó khỏi phép so cho phép sửa, mà vẫn chặn việc làm mất tag thật:
    hai bên vẫn so danh sách tag hợp lệ, thiếu một cái là chặn.
    """
    global _STOCK_TAGS
    if _STOCK_TAGS is None:
        tags = set()
        for path, names in ((STOCK_SCEN, None), (STOCK_JSON, None)):
            if not os.path.exists(path):
                raise SystemExit("không thấy cây gốc %s — cần nó cho chốt tag" % path)
            env = UnityPy.load(path)
            for o in env.objects:
                if o.type.name != "TextAsset":
                    continue
                d = o.read()
                r = d.m_Script
                s = r if isinstance(r, str) else bytes(r).decode("utf-8", "replace")
                tags.update(TAG.findall(s))
        _STOCK_TAGS = tags
        print("chốt tag: %d dạng `[...]` có trong bản gốc" % len(tags))
    return _STOCK_TAGS


def guards(old, new, key=None):
    bad = []
    # Ô trắng không bao giờ được ghi đè lên chữ đang có: đúng lớp lỗi đã làm
    # `107/txt/0099` và `0302` rỗng hẳn trên máy (bản Nhật là 「…………」). Tool này so
    # theo diff nên không chạm vào ô không đổi, nhưng một pass "áp nguyên sheet" thì có.
    if not new.strip() and old.strip():
        bad.append("ô sheet trắng mà build đang có chữ")
    # Khoá tra cứu: lệnh diễn xuất, [主人公], [se file=…]… phải khớp từng cái.
    ok = stock_tags()
    lookup = lambda s: sorted(t for t in TAG.findall(s)                      # noqa: E731
                              if not is_ruby(t) and not DIC.fullmatch(t) and t in ok)
    if lookup(old) != lookup(new):
        bad.append("tag khoá tra cứu bị đổi")
    # Link từ điển: `no=` không được đổi/mất (chữ hiển thị thì tuỳ).
    dic_nos = lambda s: sorted(m.group(1) for m in DIC.finditer(s))          # noqa: E731
    if dic_nos(old) != dic_nos(new):
        bad.append("link [dic no=…] bị đổi hoặc mất")
    r = ruby_change_ok(old, new, key)
    if r:
        bad.append(r)
    if ("[主人公]" in old) != ("[主人公]" in new):
        bad.append("token [主人公] chỉ có ở một bên")
    if new.count('"') % 2:
        bad.append("số dấu \" lẻ")
    for a, b in (("「", "」"), ("『", "』")):
        if new.count(a) != new.count(b):
            bad.append("ngoặc %s%s không cân" % (a, b))
    return bad



# ------------------------------------------------------------------ ô dẫn xuất
# Một tin nhắn chat Genebark nằm ở HAI asset, và sheet cho sửa CẢ HAI ô:
#
#     GenebarkChatMainData/chat/g1c戒_102   <- SỞ HỮU (app chat trong Genebark)
#     86/txt/0395                           <- DẪN XUẤT (chiếu lại trong cảnh ADV)
#
# `tools\\fix_chat_use_genebark.py` chép Genebark -> ScenarioData cho 184 cặp, và
# CLAUDE.md bắt chạy nó `--apply` **ngay đầu** đợt dựng lại bố cục sau mỗi lần merge.
# Nên ghi ô `sd_*` dẫn xuất ở đây là ghi rồi mất: bước ngay sau lật lại nguyên văn bản
# Genebark, KHÔNG một dòng cảnh báo. Đo 30/08 trên build hiện tại: 184/184 cặp đang
# "đã giống" và trên sheet (62) cũng 0/184 cặp lệch chữ — bẫy đang ngủ, nó chỉ cắn vào
# đúng lần đầu có người sửa ô `sd_*` trên sheet.
_TOOL_MODS = {}


def load_tool_module(name):
    """Nạp một tool khác trong `tools/` như THƯ VIỆN — cắt hai tác dụng phụ cấp module.

    `import fix_chat_use_genebark` thẳng là KHÔNG ĐƯỢC. Hai lý do, cả hai đã dính thật:

    1. Nó gán `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, …)` ở đầu file, y hệt
       file này. Hai wrapper cùng bọc MỘT buffer; wrapper nào bị gom rác trước thì
       `__del__` của nó ĐÓNG buffer chung, và mọi `print` sau đó ném
       `ValueError: I/O operation on closed file`. Tệ hơn phần nhìn thấy: chữ còn nằm
       trong đệm của wrapper kia mất hẳn, không để lại dấu vết. Đã tái hiện đúng lỗi
       này ngay khi dựng bản vá (một script phụ vô tình bọc chồng, dòng
       "read_sheet (62): … s" biến mất còn tiến trình thì chết ở `print`).
    2. Nó gọi `main()` TRẦN ở cuối file — cả hai tool đều không có
       `if __name__ == "__main__"`. `main()` đó đọc `APPLY = "--apply" in sys.argv`,
       tức argv của TIẾN TRÌNH NÀY: chạy `apply_sheet_cells.py --match X --apply` sẽ
       khiến fix_chat_use_genebark thấy `APPLY=True` và GHI THẲNG vào
       `romfs\\…\\scenario01` (kèm backup) TRƯỚC khi merge kịp bắt đầu. Đã kiểm chứng:
       nạp với argv có `--apply` cho `mod.APPLY is True`.

    Nên: đọc mã nguồn, bỏ đúng hai loại lệnh đó khỏi AST cấp cao nhất, rồi exec phần
    còn lại vào một namespace module riêng. File kia không phải sửa một chữ — nó là
    file CLAUDE.md gọi trực tiếp trong quy trình bắt buộc, càng ít đụng càng tốt.

    Lọc HẸP có chủ ý: chỉ cắt phép gán vào `sys.stdout`, và lệnh gọi trần tên đúng
    `main`. Cắt rộng hơn (mọi `ast.Expr` là `Call`) sẽ nuốt luôn
    `sys.path.insert(0, HERE)` và module hết chạy được.
    """
    if name in _TOOL_MODS:
        return _TOOL_MODS[name]
    path = os.path.join(HERE, name + ".py")
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    body = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Attribute) and t.attr == "stdout"
                and isinstance(t.value, ast.Name) and t.value.id == "sys"
                for t in node.targets):
            continue                                    # bỏ bọc chồng stdout
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "main"):
            continue                                    # bỏ lệnh chạy main()
        body.append(node)
    tree.body = body
    mod = types.ModuleType(name)
    mod.__file__ = path          # HERE/ROOT của module đó tính từ đây
    keep = sys.stdout
    exec(compile(tree, path, "exec"), mod.__dict__)
    if sys.stdout is not keep:
        # Bộ lọc trên đã hụt (ai đó viết `sys.stdout = …` theo kiểu khác). `detach()`
        # trước khi trả lại, không thì wrapper mồ côi bị gom rác sẽ đóng buffer chung
        # và giết mọi print về sau — đúng cái bẫy docstring vừa tả.
        try:
            sys.stdout.detach()
        except Exception:
            pass
        sys.stdout = keep
        print("!! %s vẫn bọc lại sys.stdout — đã gỡ, xem load_tool_module()" % name)
    _TOOL_MODS[name] = mod
    return mod


# Số cặp `pairs()` ghép được trên bản gốc 1.0.2 — BẤT BIẾN, không phụ thuộc build
# hiện tại lẫn sheet. Lệch thì hoặc cây gốc sai, hoặc LUẬT GHÉP vừa đổi.
#
# 184 -> 231 (01/09/2026): luật cũ đòi câu Nhật DUY NHẤT ở cả hai bên, quá chặt vì bản
# gốc lưu trùng cả đoạn hội thoại sang nhiều `groupIDs`. Luật mới ghép theo
# (câu Nhật, người nói) và chọn chủ bằng `groupIDs` — xem `fix_chat_use_genebark.pairs`.
PAIRS_EXPECTED = 231
_DERIVED = None


def derived_sd_ids():
    """{'86/txt/0395': 'GenebarkChatMainData/chat/g1c戒_102', …} — ô `sd_*` mà một ô
    chat Genebark sở hữu.

    TỰ TÍNH bằng chính `fix_chat_use_genebark.pairs()`, không nhúng danh sách cứng:
    pairs() ghép 1:1 theo bản Nhật DUY NHẤT ở cả hai bên và đọc từ bản GỐC
    `D:\\Downloads\\UNLOGICAL_v2` — nên kết quả cố định, không phụ thuộc build hiện tại
    và không trôi theo từng đợt sửa. 184 cặp; khớp 184/184 với bảng đối chiếu dựng tay
    (thiếu 0, thừa 0).

    Nhãn ô Genebark dựng lại từ chính hàng của asset gốc: `g{groupIDs}c{charID}_{k}`,
    đúng cột A của tab sheet — đối chiếu 184/184 nhãn, 0 lệch. Hai chỗ dễ sai:
    `groupIDs` (số nhiều) là CHUỖI và có thể là nhiều nhóm nối bằng `;`
    (`g23;24cユーリ_294`) nên đừng ép sang số; và phần tên là `charID`, KHÔNG phải
    `speaker` — `speaker` mang `player`/tên người nói, `charID` mới là nhân vật của
    đoạn chat.

    NẠP LƯỜI + nhớ đệm: vòng merge nào không có ô `sd_*` nào đổi thì không mở bundle
    nào. Đo: 0,21 s cho lần gọi đầu (nạp module 0,6 s đã cache sẵn vì UnityPy import
    trước; mở bundle json 0,00 s + scenario01 gốc 0,10 s + json.loads 0,08 s), 0 s
    cho các lần sau.

    CỐ Ý CHẶN CẢ 184, không tái tạo bộ lọc của `fix_chat_use_genebark.main()` (nameplate
    có `@`, bản Nhật không mở `「`, `guards(old, new, jp)`). Bộ lọc đó phụ thuộc NỘI DUNG
    nên không đoán trước được, và hai tool cùng suy luận về một điều kiện động là nguồn
    lỗi mới. Đo hiện tại: 184/184 qua cả hai chốt cấu trúc, nên chặn cả 184 là đúng.
    """
    global _DERIVED
    if _DERIVED is None:
        gb = load_tool_module("fix_chat_use_genebark")
        _, _, raw_g = gb.load_text(os.path.join(gb.STOCK, "json", "json"),
                                   "GenebarkChatMainData")
        rows = json.loads(raw_g.lstrip("\ufeff"))["data"]
        _DERIVED = {}
        for k, sid, i, _jp in gb.pairs():
            r = rows[k]
            _DERIVED["%d/txt/%04d" % (sid, i)] = "GenebarkChatMainData/chat/g%sc%s_%d" % (
                r.get("groupIDs") or "", r.get("charID") or "", k)
        # Cây gốc THIẾU thì `load_text` đã ném SystemExit — ầm ĩ, tốt. Cây gốc CÓ MẶT
        # mà NỘI DUNG SAI thì không ai kêu: `pairs()` chỉ ghép được ít cặp hơn và chốt
        # chặn tự tắt bớt trong im lặng. Đo thật (30/08): trỏ STOCK sang cây ĐÃ DỊCH
        # `romfs` cho **93** cặp chứ không phải 0 — tức 91 ô dẫn xuất lọt lưới, vòng
        # merge ghi chúng, rồi `fix_chat_use_genebark --apply` lật lại nguyên văn: đúng
        # cái bẫy vừa vá mở lại, lần này còn khó thấy hơn vì người dùng tin là đã có
        # chốt. Nên: số cặp là BẤT BIẾN của bản gốc 1.0.2, lệch một cặp cũng dừng.
        if len(_DERIVED) != PAIRS_EXPECTED:
            n = len(_DERIVED)
            _DERIVED = None
            print("!! chốt chặn chat: ghép được %d cặp, bản gốc 1.0.2 phải ra %d."
                  % (n, PAIRS_EXPECTED))
            print("   Hai nguyên nhân, kiểm theo thứ tự này:")
            print("   1) LUẬT GHÉP trong fix_chat_use_genebark.pairs() vừa đổi")
            print("      -> nếu đúng ý, cập nhật PAIRS_EXPECTED thành %d." % n)
            print("   2) cây gốc không phải bản 1.0.2 chưa sửa: %s" % gb.STOCK)
            print("      (thường do chép đè bằng cây đã dịch, hoặc dump bản game khác)")
            print("   ĐỪNG merge tiếp khi chưa rõ: chốt chặn ô chat dẫn xuất lệch %d ô."
                  % (PAIRS_EXPECTED - n))
            raise SystemExit("cây gốc sai — chốt chặn ô chat dẫn xuất không tin được")
        print("chốt chặn chat: %d cặp ô dẫn xuất (tính từ bản gốc)" % len(_DERIVED))
    return _DERIVED


def flat_cell(s):
    """Làm phẳng một ô sheet để SO CÂU CHỮ (không so bố cục).

    `read_sheet` để hai tab khai ngắt dòng theo hai kiểu khác nhau: tab `sd_*` đã đổi
    `\\n` thành khoảng trắng, tab *Data thì giữ lại dạng `\\n` VĂN BẢN. So nguyên văn
    thì mọi cặp có xuống dòng đều báo "khác chữ" một cách vô nghĩa.
    """
    return re.sub(r"[\s\u3000]+", " ", (s or "").replace(BS_N, " ")).strip()


def check_chat(new_f):
    """Soi CẢ bảng cặp trên một snapshot, bất kể vòng này có ô nào đổi hay không.

    Vì sao cần chế độ riêng: cảnh báo "SỬA NHẦM Ô" trong `main()` chỉ nổ ĐÚNG MỘT VÒNG.
    `todo` chỉ gồm ô có `new != base`, nên vòng sau — khi snapshot vừa rồi đã thành sheet
    NỀN — ô vẫn lệch y nguyên nhưng không còn "đã đổi", và không tool nào nhắc lại nữa.
    Bản dịch nằm vĩnh viễn trên sheet mà không bao giờ lên màn hình. Đúng lớp lỗi memory
    `unlogical-wrong-cell-audit` đã ghi: lưới dán đè chỉ thấy vòng hiện tại.

    Ở đây so ô `sd_*` với ô Genebark SỞ HỮU nó, trên cùng một snapshot. Lệch = bản dịch
    đã rơi vào ô dẫn xuất; game hiện bản Genebark nên chữ đó sẽ không bao giờ thấy được.

        python tools\\apply_sheet_cells.py --check-chat
    """
    print("sheet      : %s" % new_f)
    new, _ = read_sheet(new_f)
    print("ô đọc được: %d" % len(new))
    owner = derived_sd_ids()
    miss, bad = [], []
    for sd_key, gb_key in sorted(owner.items()):
        sd, gb = new.get(sd_key), new.get(gb_key)
        if sd is None or gb is None:
            miss.append((sd_key, gb_key, sd is None))
            continue
        if flat_cell(sd[0]) != flat_cell(gb[0]):
            bad.append((sd_key, gb_key, sd[0], gb[0]))
    for sd_key, gb_key, sd_missing in miss:
        print("  FAIL %-14s không thấy %s trên sheet"
              % (sd_key, sd_key if sd_missing else gb_key))
    for sd_key, gb_key, sv, gv in bad:
        print("  FAIL %-14s lệch với %s" % (sd_key, gb_key.split("/")[-1]))
        print("         sd_*     : %r" % flat_cell(sv)[:76])
        print("         Genebark : %r" % flat_cell(gv)[:76])
    if miss or bad:
        print("\n%d/%d cặp lệch — game hiện bản Genebark, nên bản dịch ở ô sd_* KHÔNG"
              " lên màn hình." % (len(miss) + len(bad), len(owner)))
        print("   Chép bản dịch sang tab GenebarkChatMainData (ô sở hữu) rồi export lại.")
        raise SystemExit(1)
    print("PASS %d/%d cặp: ô sd_* và ô Genebark sở hữu nói cùng một câu" % (len(owner),
                                                                           len(owner)))


def build_values():
    """{id sheet: giá trị đang có trong BUILD} cho mọi dạng id đọc được.

    Dùng lại đúng các đường đọc của `main()`, chỉ khác là quét TẤT CẢ thay vì theo `todo`.
    Chat Genebark đánh địa chỉ bằng CHỈ SỐ nên để dưới khoá riêng `__gbidx__<n>`.
    """
    out = {}
    _, _, raw_s = load_text(SCENARIO, "ScenarioData")
    data_s = json.loads(raw_s.lstrip("﻿"))
    for t in data_s["target"]:
        sid = t["scenarioID"]
        for i, x in enumerate(t.get("text") or []):
            out["%d/txt/%04d" % (sid, i)] = x
        for n, a in enumerate(CMD_ARG.findall(t["scriptText"])):
            out["%d/cmd/%04d" % (sid, n)] = a.replace(BS_N, "\n")
        for j, raw in enumerate(t.get("selText") or []):
            if not raw:
                continue
            try:
                opts = json.loads(raw)["target"]
            except Exception:
                continue
            for k, v in enumerate(opts):
                out["%d/sel/%04d/%04d" % (sid, j, k)] = v

    _, _, raw_q = load_text(JSONB, "Q&AData")
    for g, grp in enumerate(json.loads(raw_q.lstrip("﻿"))["list"]):
        for q, ttl in enumerate(grp.get("title") or []):
            out["Q&AData/qa_title/g%d_q%d" % (g, q)] = ttl

    _, _, raw_g = load_text(JSONB, "GenebarkChatMainData")
    for n, r in enumerate(json.loads(raw_g.lstrip("﻿"))["data"]):
        out["__gbidx__%d" % n] = r.get("content") or ""

    # MỌI tab bundle json trong FIELD_MAP, không riêng Q&A.
    #
    # Thiếu khối này thì `--audit-sheet` mù với 578 hàng: cả tab DictionaryData,
    # ShortStoryData, TerminalRuleData/ProfileData/ControlSkillData/HomeAlertData,
    # GenebarkNewsData và GenebarkNoteData đều rơi vào "id không có ở build" và bị
    # đếm như id rác. Vòng merge ba chiều vẫn ghi được chúng, nên lỗi ẩn: ô nào SHEET
    # ĐÚNG - BUILD SAI mà sheet đứng yên thì không phép nào nhìn tới. Người dùng bắt
    # được bằng mắt ở tab DictionaryData (17 ô lệch, có ô lệch hẳn tên mục:
    # `Gyafun` vs `Tắt đài`, `Người nuôi dưỡng` vs `Kỹ sư huấn luyện`) — đúng lớp lỗi
    # mà chế độ audit sinh ra để chặn.
    for (asset, sfield), (root, field) in sorted(FIELD_MAP.items()):
        try:
            _, _, raw_a = load_text(JSONB, asset)
        except SystemExit:
            continue
        dj = json.loads(raw_a.lstrip("﻿"))
        ekey = KEY_OF.get(asset, "id")
        for e in entries(dj, root):
            if ekey not in e or field not in e:
                continue
            out["%s/%s/id%s" % (asset, sfield, e[ekey])] = field_get(e, field)
    return out


AUDIT_BO = re.compile("[\\s\\u3000『』「」\"'()（）：:.,!?…-]+")


def audit_sheet(new_f):
    """So MỌI ô sheet với build, bất kể vòng này có gì đổi.

    Vì sao phải có chế độ riêng: `main()` là phép so BA CHIỀU — nó chỉ hành động trên ô
    có `new != base`. Ô mà SHEET ĐÚNG, BUILD SAI, nhưng sheet ĐỨNG YÊN thì không vòng
    merge nào nhìn tới, mãi mãi. Hai đường dẫn tới trạng thái đó, cả hai đã xảy ra thật
    (đo trên snapshot (63), 30/08/2026):

    - ô từng đổi rồi bị chặn "CẢ HAI BÊN ĐỔI" mà không ai lấy; vòng sau sheet không đổi
      nữa nên nó biến khỏi tầm nhìn — `89/cmd/0001`..`0003`;
    - build bị sửa tay lệch khỏi sheet từ lâu, sheet chưa hề đổi suốt 58..63 —
      `69/cmd/*`, `70/cmd/*`, `75/cmd/*`, `76/txt/0025`.

    Lần chạy đầu tiên tìm ra **94 ô** như vậy, trong khi cách đếm-từ-khoá thủ công trước
    đó chỉ thấy 12. Đó là lý do phải soi có hệ thống chứ không grep vài cụm.

    KHÔNG tự áp. Trong 94 ô chắc chắn có ô mà BUILD mới đúng — bố cục ngắt dòng, bản sửa
    sau merge, hoặc quyết định chỉ tồn tại ở build. Chế độ này chỉ phân loại để duyệt:

        dấu câu        chỉ khác dấu/ngoặc/khoảng trắng
        chữ            khác chữ nhưng còn nhận ra nhau (giống >= 60%)
        câu khác hẳn   viết lại

    Bỏ qua ô sheet TRỐNG (build giữ bản dịch là đúng) và 184 ô dẫn xuất Genebark
    (`derived_sd_ids`, tab Genebark sở hữu — xem `--check-chat`).

        python tools\\apply_sheet_cells.py --audit-sheet [--new=…]
    """
    print("sheet     : %s" % new_f)
    sheet, _ = read_sheet(new_f)
    build = build_values()
    owner = derived_sd_ids()
    gb_by_n = {}
    for k in sheet:
        m = GB_ID.match(k)
        if m:
            gb_by_n[k] = "__gbidx__" + m.group(1)

    nhom = {"dấu câu": [], "chữ": [], "câu khác hẳn": []}
    bo_trong = bo_dan_xuat = ngoai_build = 0
    bo_ngat = 0
    for key, (sv, jp) in sheet.items():
        if key in owner:
            bo_dan_xuat += 1
            continue
        bkey = gb_by_n.get(key, key)
        if bkey not in build:
            ngoai_build += 1
            continue
        if not sv.strip():
            bo_trong += 1
            continue
        a, b = flat_cell(sv), flat_cell(build[bkey])
        if a == b:
            continue
        # Chỉ khác ở CHỖ NGẮT DÒNG thì không phải lệch bản dịch, và sheet không tài nào
        # diễn đạt được nó. `flat_cell` đổi `\n` thành khoảng TRẮNG, nên ô nào build ngắt
        # ở chỗ sheet không có space là bị báo oan mãi mãi: `g53c奏壱_641` build ghi
        # `......\nXin lỗi em…`, sheet ghi `......Xin lỗi em…` — làm phẳng ra
        # `...... Xin` vs `......Xin`. Nó nằm lì trong báo cáo suốt mấy vòng và tôi đã
        # xếp nhầm nó vào "khác dấu câu".
        # MỖI chỗ `\n` của build được phép ứng với "" HOẶC " " bên sheet — không hơn.
        #
        # Sheet là bản làm phẳng của build, và người gõ lúc thì chèn space thay chỗ
        # xuống dòng lúc thì không, ngay trong cùng một ô: `...\nVâng.\nEm không nên đi`
        # thành `...Vâng. Em không nên đi` — chỗ đầu không space, chỗ sau có.
        #
        # Nên không thể so bằng một phép biến đổi cố định. Bản trước xoá HẾT `\n` rồi
        # so, và nó chỉ đúng với ô có một chỗ ngắt; ô hai chỗ ngắt thì `luôn.Anh` không
        # bao giờ khớp `luôn. Anh`, để lọt 9 ô báo oan.
        #
        # Dựng mẫu từ CHÍNH các dòng của build, nối bằng `" ?"`. Chặt đúng mức cần: nó
        # chỉ tha chỗ xuống dòng, còn thiếu space giữa hai chữ trong CÙNG một dòng
        # (`xelửa` / `xe lửa`) thì vẫn bị bắt.
        bdong = [p for p in (flat_cell(x) for x in str(build[bkey]).split("\n")) if p]
        if bdong and re.fullmatch(" ?".join(re.escape(p) for p in bdong), a):
            bo_ngat += 1
            continue
        if AUDIT_BO.sub("", a) == AUDIT_BO.sub("", b):
            nhom["dấu câu"].append((key, b, a, jp))
        elif difflib.SequenceMatcher(None, a, b).ratio() >= 0.6:
            nhom["chữ"].append((key, b, a, jp))
        else:
            nhom["câu khác hẳn"].append((key, b, a, jp))

    tong = sum(len(v) for v in nhom.values())
    print("ô sheet đọc được  : %d" % len(sheet))
    print("bỏ qua ô trống    : %d" % bo_trong)
    print("bỏ qua ô dẫn xuất : %d" % bo_dan_xuat)
    print("id không có ở build: %d" % ngoai_build)
    print("bỏ qua ô chỉ khác NGẮT DÒNG: %d" % bo_ngat)
    print("\nÔ SHEET KHÁC BUILD: %d" % tong)
    for ten in ("dấu câu", "chữ", "câu khác hẳn"):
        rows = nhom[ten]
        print("\n===== %s — %d ô =====" % (ten.upper(), len(rows)))
        for key, b, a, jp in sorted(rows, key=lambda r: r[0]):
            print("  %s" % key)
            print("     build: %r" % b[:86])
            print("     sheet: %r" % a[:86])
    if tong:
        print("\nDUYỆT rồi áp: --take-sheet=<id,id,…> --apply")
        print("   (--take-sheet bỏ điều kiện 'build chưa ai sửa', vẫn qua đủ chốt còn lại)")
        raise SystemExit(1)
    print("\nPASS sheet và build nói cùng một câu ở mọi ô")


def main():
    new_f, base_f = arg("new"), arg("base")
    if not new_f or not base_f:
        n, b = newest_two()
        new_f, base_f = new_f or n, base_f or b
    if CHECK_CHAT:
        check_chat(new_f)
        return
    if AUDIT:
        audit_sheet(new_f)
        return
    print("sheet mới : %s" % new_f)
    print("sheet nền : %s" % base_f)
    print("lọc       : %s" % (MATCH or "(không lọc — mọi ô đã đổi)"))
    new, unknown_new = read_sheet(new_f)
    base, _ = read_sheet(base_f)
    print("ô đọc được: %d\n" % len(new))
    report_unknown(unknown_new, "sheet mới")


    pat = re.compile(MATCH, re.I) if MATCH else None
    todo = []
    for key, (nv, jp) in new.items():
        b = base.get(key)
        if b is None or nv == b[0]:
            continue
        if pat and not (pat.search(nv) or pat.search(b[0])):
            continue
        todo.append((key, b[0], nv, jp))
    if FORCE:
        have = {t[0] for t in todo}
        them = 0
        for key in sorted(FORCE):
            if key in have:
                TAKE.add(key); continue
            if key not in new:
                print("! --force-sheet: %s không có trên sheet" % key); continue
            nv, jp = new[key]
            todo.append((key, nv, nv, jp))
            TAKE.add(key)
            them += 1
        print("--force-sheet: nạp thêm %d ô (sheet không đổi nhưng build lệch)" % them)
    print("ô đã đổi trên sheet và khớp bộ lọc: %d" % len(todo))
    dup = duplicate_paste(todo, skip=FORCE)
    if dup:
        print("\n!! %d ô có DẤU HIỆU DÁN ĐÈ trên sheet "
              "(bản dịch mới trùng nhau mà bản Nhật khác nhau)" % len(dup))
        for key in sorted(dup):
            jp = next(j for k, _, _, j in todo if k == key)
            print("   %-14s JP: %r" % (key, jp[:64].replace("\n", "⏎")))
        print("   -> bỏ qua những ô này; sửa trên sheet rồi chạy lại")
        todo = [t for t in todo if t[0] not in dup]

    # Ô `sd_*` chỉ CHIẾU LẠI một tin nhắn chat mà bản Genebark sở hữu thì không ghi —
    # xem `derived_sd_ids()`. Ba lựa chọn về CHỖ ĐẶT, và chỗ này là chỗ duy nhất đúng:
    #
    # - KHÔNG lọc trong `read_sheet()`: nó chạy cho cả `new` lẫn `base`, loại ở đó thì
    #   cặp ô biến mất khỏi cả hai phía nên phép so ba chiều không sinh ra mục nào và
    #   tool im lặng tuyệt đối — đổi một cái bẫy im lặng lấy một cái bẫy im lặng khác,
    #   đúng lớp lỗi mà `report_unknown()` được dựng ra để chống. Còn làm hụt "ô đọc
    #   được" đi 184 và rút 184 ô khỏi lưới `duplicate_paste`.
    # - SAU `duplicate_paste`: ô dẫn xuất vẫn được đếm và vẫn đi qua lưới dán đè. Một
    #   bản dịch dán nhầm vào ô chat vẫn đáng báo, kể cả khi ô đó sẽ không được ghi —
    #   người dùng còn phải sửa nó trên sheet.
    # - TRƯỚC `if not todo: return`: vòng nào chỉ toàn ô dẫn xuất thì thoát sớm, KHÔNG
    #   mở scenario01 (7,8 MB nén / 13,9 MB JSON) lẫn bundle json.
    #
    # Và vì khối này nằm NGOÀI vòng lặp áp, `--take-sheet` không gỡ được nó — đúng ý:
    # `--take-sheet` chỉ bỏ điều kiện "build chưa ai sửa", còn ô dẫn xuất thì ghi kiểu
    # gì cũng bị lật lại, honour nó là nói dối người dùng.
    if any(SD_ID.match(t[0]) for t in todo):
        owner = derived_sd_ids()          # nạp lười: chỉ tính khi thật sự có ô sd_*
        drop = [t for t in todo if t[0] in owner]
        wrong = []
        if drop:
            print("\n%d ô sd_* là BẢN CHIẾU của chat Genebark — KHÔNG ghi:" % len(drop))
            for key, _bv, nv, _jp in sorted(drop):
                gb_key = owner[key]
                print("   -  %-14s ô dẫn xuất — tab Genebark (%s) sở hữu, bỏ qua"
                      % (key, gb_key.split("/")[-1]))
                gb = new.get(gb_key)
                if gb is None:
                    wrong.append(key)
                    print("      !! không thấy %s trên sheet — không đối chiếu được"
                          % gb_key)
                elif flat_cell(nv) != flat_cell(gb[0]):
                    # Ô Genebark là ô game thật sự hiện. Sửa ở ô dẫn xuất mà không sửa
                    # ô sở hữu = sửa nhầm chỗ: chữ mới sẽ không bao giờ lên màn hình.
                    wrong.append(key)
                    print("      !! SỬA NHẦM Ô — bản dịch mới KHÁC ô Genebark, mà game")
                    print("         hiện bản Genebark, nên sửa này sẽ không thấy được")
                    print("         sd_*     : %r" % flat_cell(nv)[:76])
                    print("         Genebark : %r" % flat_cell(gb[0])[:76])
            if wrong:
                print("!! %d/%d ô trên là SỬA NHẦM Ô — chép bản dịch sang tab"
                      " GenebarkChatMainData rồi chạy lại" % (len(wrong), len(drop)))
            print("=> bỏ qua %d ô dẫn xuất. Sau merge vẫn phải chạy:" % len(drop))
            print("   python tools\\fix_chat_use_genebark.py --apply")
            todo = [t for t in todo if t[0] not in owner]

    # Nhánh `rule_body` KHÔNG đi qua `todo` — nó map theo (id, trang) từ tab riêng —
    # nên `rkeys` phải tính TRƯỚC khi quyết định thoát sớm, không thì một vòng chỉ sửa
    # trang RULE bị bỏ qua HOÀN TOÀN: không ghi, không báo, và cả dòng tổng kết "áp
    # được:" lẫn "CHẠY THỬ" cũng không in ra nên không có gì để người dùng thấy là
    # thiếu. Vòng sau snapshot này thành sheet NỀN, `rn == rb`, khác biệt biến mất
    # vĩnh viễn — đúng lớp "sheet sửa rồi mà game không đổi" mà `report_unknown()`
    # được dựng ra để chống.
    #
    # Lỗi này CÓ SẴN từ trước chốt chặn ô dẫn xuất (đo: bản .bak cũng nuốt một vòng
    # chỉ đổi rule_body), nhưng chốt chặn làm nó dễ trúng hơn hẳn — vòng nào mọi ô
    # đổi đều là ô chat dẫn xuất cũng rút `todo` về rỗng, mà một vòng chỉ có 1-2 ô
    # đổi là chuyện thường ở kho này.
    #
    # Giá: 2,2 s mở thêm hai workbook ở đúng nhánh thoát sớm (đo 30/08: 1,09 + 1,14 s).
    # Nhánh không thoát sớm vốn đã trả khoản này, nên vòng merge thường không đổi.
    rn, rb = read_rule_rows(new_f), read_rule_rows(base_f)
    rkeys = [k for k in rn if k in rb and rn[k] != rb[k]]
    print()
    if not todo and not rkeys:
        return

    env_s, d_s, raw_s = load_text(SCENARIO, "ScenarioData")
    data_s = json.loads(raw_s.lstrip("﻿"))
    sid_map = {t["scenarioID"]: ti for ti, t in enumerate(data_s["target"])}
    out_s, changed_s = raw_s, []
    json_edits = []
    gb_data = None            # nạp lười, chỉ khi có ô chat Genebark
    gb_edits = []
    sel_edits = []
    qa_edits = []
    qa_list = None
    cmd_edits = []

    for key, bv, nv, _jp in sorted(todo):
        m = SD_ID.match(key)
        if m:
            sid, idx = int(m.group(1)), int(m.group(2))
            ti = sid_map.get(sid)
            if ti is None:
                print("! %s: không có scenarioID %d" % (key, sid)); continue
            cur = data_s["target"][ti]["text"][idx]
            kind = "ScenarioData"
        elif CMD_ID.match(key):
            m = CMD_ID.match(key)
            sid, cn = int(m.group(1)), int(m.group(2))
            ti = sid_map.get(sid)
            if ti is None:
                print("! %s: không có scenarioID %d" % (key, sid)); continue
            args = CMD_ARG.findall(data_s["target"][ti]["scriptText"])
            if cn >= len(args):
                print("! %s: scenario chỉ có %d lệnh có ngoặc" % (key, len(args))); continue
            # Trong tham số lệnh, ngắt dòng là `\\n` dạng VĂN BẢN (2 ký tự) chứ không phải
            # U+000A — cùng quy ước với các tab *Data. Phải mở ra trước, không thì
            # `carry_breaks` không thấy ngắt nào để đắp lại và câu bị làm phẳng.
            cur = args[cn].replace(BS_N, chr(10))
            kind = "cmd"
        elif SEL_ID.match(key):
            m = SEL_ID.match(key)
            sid, sidx, opt = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            ti = sid_map.get(sid)
            if ti is None:
                print("! %s: không có scenarioID %d" % (key, sid)); continue
            arr = data_s["target"][ti].get("selText") or []
            if sidx >= len(arr) or not arr[sidx]:
                print("! %s: selText[%d] trống" % (key, sidx)); continue
            try:
                opts = json.loads(arr[sidx])["target"]
            except Exception as e:
                print("! %s: selText[%d] không parse được (%s)" % (key, sidx, e)); continue
            if opt >= len(opts):
                print("! %s: chỉ có %d lựa chọn" % (key, len(opts))); continue
            cur = opts[opt]
            kind = "selText"
        elif QA_ID.match(key):
            m = QA_ID.match(key)
            qg, qq = int(m.group(1)), int(m.group(2))
            if qa_list is None:
                _, _, raw_q = load_text(JSONB, "Q&AData")
                qa_list = json.loads(raw_q.lstrip("﻿"))["list"]
            if qg >= len(qa_list) or qq >= len(qa_list[qg].get("title") or []):
                print("! %s: không có nhóm %d câu %d" % (key, qg, qq)); continue
            cur = qa_list[qg]["title"][qq]
            kind = "Q&AData"
        elif GB_ID.match(key):
            # Chat Genebark địa chỉ bằng CHỈ SỐ tuyệt đối trong data[], không bằng khoá id.
            gn = int(GB_ID.match(key).group(1))
            if gb_data is None:
                _, _, raw_g = load_text(JSONB, "GenebarkChatMainData")
                gb_data = json.loads(raw_g.lstrip("﻿"))["data"]
            if gn >= len(gb_data):
                print("! %s: data[] chỉ có %d mục" % (key, len(gb_data))); continue
            cur = gb_data[gn].get("content") or ""
            kind = "GenebarkChatMainData"
        elif RULE_ID.match(key):
            continue                     # xử lý riêng ở nhánh rule_body bên dưới
        else:
            m = DATA_ID.match(key)
            if not m:
                print("! %s: id lạ" % key); continue
            asset, sfield, eid = m.group(1), m.group(2), int(m.group(3))
            root, field = FIELD_MAP.get((asset, sfield), ("data", sfield))
            _, _, raw_j = load_text(JSONB, asset)
            dj = json.loads(raw_j.lstrip("﻿"))
            ekey = KEY_OF.get(asset, "id")
            ent = next((e for e in entries(dj, root) if e.get(ekey) == eid), None)
            if ent is None:
                print("! %s: không có %s %d trong %s (khoá gốc %r)"
                      % (key, ekey, eid, asset, root)); continue
            # Tên field của sheet phải giải được ra field thật. Đọc `""` cho field không
            # tồn tại thì ô trông như "build trống" và bị báo sai là "cả hai bên đổi".
            if field not in ent:
                print("! %s: %s không có field %r (nhãn sheet %r; có: %s)"
                      % (key, asset, field, sfield, ", ".join(sorted(ent)))); continue
            cur = field_get(ent, field)
            kind = asset

        # So ba chiều trên bản ĐÃ LÀM PHẲNG: build giữ `\n` mà sheet thì không, nên
        # so nguyên văn sẽ báo "cả hai bên đổi" cho cả những ô build vốn đã đúng.
        # Tab *Data khai ngắt dòng bằng `\n` VĂN BẢN, asset thì dùng U+000A. Phải mở ra
        # trước khi so, không thì ô nào có dấu đó cũng "không bao giờ khớp".
        nv_x = expand_breaks(nv)                     # bản có ngắt dòng do SHEET khai
        nv, bv = nv_x.replace("\n", " "), expand_breaks(bv).replace("\n", " ")
        flat_cur = cur.replace("\n", " ")
        # "Đã có bản mới" phải so NGUYÊN VĂN khi sheet tự khai ngắt dòng — không thì ô chỉ
        # khác bố cục mà giống câu chữ sẽ bị bỏ qua, và cấu trúc mới không bao giờ xuống
        # (vòng (40): 4 hàng note đúng kiểu đó).
        if (cur == nv_x) if "\n" in nv_x else (flat_cur == nv):
            print("=  %-34s đã có bản mới" % key); continue
        if flat_cur != bv and key in TAKE:
            # Người đã xem và chốt "sheet thắng ô này". Vẫn qua đủ các chốt còn lại
            # (tag khoá tra cứu, `no=` của [dic], [主人公], ngoặc cân, carry_breaks) —
            # `--take-sheet` chỉ bỏ *một* điều kiện: "build chưa ai sửa".
            print("~  %-34s LẤY THEO SHEET (--take-sheet, đè bản build)" % key)
            print("      build bị đè: %r" % flat_cur[:88])
        elif flat_cur != bv:
            print("!! %-34s CẢ HAI BÊN ĐỔI — bỏ qua" % key)
            print("      nền   : %r" % bv[:88])
            print("      build : %r" % flat_cur[:88])
            print("      sheet : %r" % nv[:88])
            continue
        # Tham số lệnh được phân định BẰNG dấu " — `[terinfo text="…"]` — nên một dấu "
        # trong nội dung sẽ KẾT THÚC tham số sớm và phần sau thành rác. Bản gốc 1.0.2 có
        # 0 chỗ như vậy; vòng (60) lấy bản sheet dùng " thay `『』` và làm hỏng 3 lệnh ở
        # sID 72 — game chỉ đọc được `Phát hiện `. Không tự thay dấu: đó là quyết định
        # câu chữ, phải sửa trên sheet.
        if kind == "cmd" and '"' in nv:
            print("!! %-34s chốt chặn: tham số lệnh KHÔNG được chứa dấu %s "
                  "(nó kết thúc tham số). Dùng 『』 trên sheet." % (key, '"'))
            continue
        bad = guards(cur, nv, key)
        if bad:
            print("!! %-34s chốt chặn: %s" % (key, "; ".join(bad))); continue
        # Sheet có tự khai ngắt dòng thì SHEET thắng — chỉ các tab *Data làm được, bằng
        # `\n` văn bản. Không khai thì đắp lại ngắt dòng của build như cũ.
        if "\n" in nv_x:
            val = nv_x
        else:
            val = carry_breaks(cur, nv)
            if val is None:
                print("!! %-34s không đặt lại được %d ngắt dòng — bỏ qua"
                      % (key, cur.count("\n"))); continue
        # Space ASCII đứng ngay trước một ngắt dòng cứng thì không bao giờ có nghĩa, mà
        # `carry_breaks` sinh ra nó khi ô sheet có space đôi: `71/txt/0344` ra `. ⏎Cô`.
        # (Chỉ cắt space/tab — `　` SAU ngắt dòng là thụt lề thật, phải giữ.)
        val = re.sub(r"[ \t]+\n", "\n", val)
        # Chốt chặn LÀM PHẲNG: không ô nào được mất ngắt dòng so với build. Đây đúng là
        # lớp hỏng đã phá 1 530 ngắt dòng một lần, và vòng (39) tái diễn — 6 hàng note bị
        # xoá hết dấu `\n` văn bản nên sẽ làm phẳng note 3 dòng thành 1.
        # …nhưng chỉ khi sheet KHÔNG tự khai bố cục. Sheet có khai thì nó là bên có thẩm
        # quyền và việc giảm dòng là chủ ý: vòng (40) id6 nối lại đúng 3 dòng như bản gốc
        # (build đang 4 dòng, ngắt giữa cụm "cách nào / khác là"), chặn là chặn oan.
        if "\n" not in nv_x and val.count("\n") < cur.count("\n"):
            print("!! %-34s chốt chặn: sheet làm phẳng, mất %d ngắt dòng (build %d -> %d)"
                  % (key, cur.count("\n") - val.count("\n"),
                     cur.count("\n"), val.count("\n"))); continue

        print("-> %-34s %s" % (key, kind))
        print("      cũ : %r" % cur[:88].replace("\n", "⏎"))
        print("      mới: %r" % val[:88].replace("\n", "⏎"))
        if kind == "ScenarioData":
            changed_s.append((ti, sid, idx, cur, val))
        elif kind == "GenebarkChatMainData":
            gb_edits.append((gn, cur, val))
        elif kind == "cmd":
            cmd_edits.append((ti, sid, cn, cur, val))
        elif kind == "selText":
            sel_edits.append((ti, sid, sidx, opt, cur, val))
        elif kind == "Q&AData":
            qa_edits.append((qg, qq, cur, val))
        else:
            json_edits.append((kind, field, eid, cur, val, root))

    # ---- ScenarioData: text[] + bản sao scriptText
    # Vá theo CẢ MẢNG `text[]` của từng target, không theo từng chuỗi: có những câu
    # trùng nhau từng chữ (70/txt/1216 và 1218), thay theo chuỗi sẽ đụng cả hai.
    if changed_s:
        def enc(x):
            return json.dumps(x, ensure_ascii=False, separators=(",", ":"))
        for ti in sorted({c[0] for c in changed_s}):
            arr_old = list(data_s["target"][ti]["text"])
            arr_new = list(arr_old)
            for t2, sid, idx, cur, val in [c for c in changed_s if c[0] == ti]:
                assert arr_new[idx] == cur, "text[%d] không như đã đọc" % idx
                arr_new[idx] = val
            oj, nj = enc(arr_old), enc(arr_new)
            if out_s.count(oj) != 1:
                raise SystemExit("mảng text[] của target[%d] khớp %d lần" % (ti, out_s.count(oj)))
            out_s = out_s.replace(oj, nj)
        for ti in sorted({c[0] for c in changed_s}):
            script = cur_script = data_s["target"][ti]["scriptText"]
            for t2, sid, idx, cur, val in [c for c in changed_s if c[0] == ti]:
                lines = cur_script.split("\n")
                ol = cur.split("\n")
                hits = [k for k in range(len(lines) - len(ol) + 1) if lines[k:k + len(ol)] == ol]
                if len(hits) == 1:
                    lines[hits[0]:hits[0] + len(ol)] = val.split("\n")
                    cur_script = "\n".join(lines)
                else:
                    print("   (scriptText sID=%s text[%d]: khớp %d lần, bỏ qua mirror)"
                          % (sid, idx, len(hits)))
            if cur_script != script:
                oj, nj = (json.dumps(script, ensure_ascii=False),
                          json.dumps(cur_script, ensure_ascii=False))
                if out_s.count(oj) != 1:
                    raise SystemExit("scriptText target[%d] khớp %d lần" % (ti, out_s.count(oj)))
                out_s = out_s.replace(oj, nj)
                # PHẢI đồng bộ lại `data_s`, không chỉ `out_s`. Nhánh `cmd` bên dưới đọc
                # `data_s[...]["scriptText"]` rồi tìm bản mã hoá JSON của nó trong `out_s`;
                # nếu ở đây chỉ sửa `out_s` thì hai bên lệch và nhánh cmd chết với
                # "scriptText khớp 0 lần" — chỉ xảy ra khi cùng một scenario có CẢ ô `txt`
                # lẫn ô `cmd` đổi trong một vòng (sID 69 vòng (68), sID 103 vòng (72)).
                data_s["target"][ti]["scriptText"] = cur_script

    # ---- nhánh rule_body: map theo (id, trang), giữ khoảng trắng đầu dòng của build
    rule_edits = []                      # rn / rb / rkeys đã tính trước phần thoát sớm
    if rkeys:
        _, _, raw_r = load_text(JSONB, "TerminalRuleData")
        tr = json.loads(raw_r.lstrip("﻿"))
        items = {it["id"]: it for g in tr["data"] for it in g["items"]}
        print("hàng rule_body đổi trên sheet: %d" % len(rkeys))
        for (i, k) in sorted(rkeys):
            it = items.get(i)
            if it is None or k >= len(it.get("content", [])):
                print("!! rule_body id%d trang %d: không có trong asset" % (i, k))
                continue
            cur = it["content"][k]["text"]
            val = merge_rule_text(cur, rn[(i, k)])
            if val is None:
                print("!! rule_body id%d trang %d: số dòng lệch (build %d / sheet %d) — bỏ qua"
                      % (i, k, cur.count("\n") + 1, rn[(i, k)].count("\n") + 1))
                continue
            if val == cur:
                print("=  rule_body id%d trang %d: đã có bản mới" % (i, k))
                continue
            # So ba chiều như nhánh ScenarioData. Nhánh này vốn thiếu chốt đó, nên một
            # bản sửa làm thẳng trên build bị vòng merge sau **âm thầm lật lại** — đã
            # xảy ra thật: `fix_terminal_term.py` đổi id30/44/45 thành "Terminal", sheet
            # vẫn ghi "terminal", vòng chạy lại sẽ hạ chữ hoa xuống.
            # Dùng chính `merge_rule_text` với sheet NỀN: ra đúng `cur` thì build chưa ai
            # sửa; khác `cur` thì hai bên đều đổi.
            base_val = merge_rule_text(cur, rb[(i, k)])
            if base_val is not None and base_val != cur:
                print("!! rule_body id%d trang %d: CẢ HAI BÊN ĐỔI — bỏ qua" % (i, k))
                for l in difflib.unified_diff(base_val.split("\n"), cur.split("\n"),
                                              "nền", "build", lineterm="", n=0):
                    if l[:1] in "+-" and l[:3] not in ("+++", "---"):
                        print("      %s" % l[:96])
                continue
            if val.count("　") < cur.count("　"):
                print("!! rule_body id%d trang %d: mất %d thụt lề `　` — bỏ qua"
                      % (i, k, cur.count("　") - val.count("　")))
                continue
            bad = guards(cur, val)
            if bad:
                print("!! rule_body id%d trang %d: %s" % (i, k, "; ".join(bad)))
                continue
            diff = [l for l in difflib.unified_diff(cur.split("\n"), val.split("\n"),
                                                    lineterm="", n=0)
                    if l[:1] in "+-" and l[:3] not in ("+++", "---")]
            print("-> rule_body id%d trang %d  (%d dòng đổi)" % (i, k, len(diff) // 2))
            for l in diff[:4]:
                print("      %s" % l[:96])
            rule_edits.append((i, k, cur, val))

    print("\náp được: %d ô ScenarioData, %d lựa chọn, %d thông báo, "
          "%d ô chat Genebark, %d tiêu đề Q&A, %d ô bundle json, %d trang rule_body"
          % (len(changed_s), len(sel_edits), len(cmd_edits), len(gb_edits),
             len(qa_edits), len(json_edits), len(rule_edits)))
    # ---- Thông báo Terminal: [terinfo|geninfo|select_monitor] text="…"
    if cmd_edits:
        # Lệnh CHẠY từ script chương (game dùng `loadLine` trỏ vào đó); `scriptText` chỉ là
        # bản sao. Nên phải sửa CẢ HAI, bỏ sót một bên là vòng đối chiếu sau lại thấy lệch
        # — đúng bài học của `fix_stage_term.py`.
        # `str.replace` thay MỌI chỗ, nên hai ô cùng scenario mà cùng chuỗi nguồn thì ô
        # đầu đã sửa luôn phần của ô sau, và ô sau báo "không thấy chuỗi cũ"
        # (116/cmd/2 với 116/cmd/3, cùng nguồn `…thua cuộc\\nArisawa Zadkiel`). Kết quả
        # vẫn đúng NHƯNG chỉ vì hai ô tình cờ cùng bản dịch — khác nhau thì ô sau bị ô
        # đầu ghi đè trong im lặng. Gộp theo (scenario, chuỗi nguồn), chốt bản dịch phải
        # nhất quán, rồi thay một lần.
        groups = {}
        for ti, sid, cn, cur, val in cmd_edits:
            groups.setdefault((ti, sid, cur), []).append((cn, val))
        for (ti, sid, cur), rows in groups.items():
            vals = {v for _cn, v in rows}
            if len(vals) > 1:
                raise SystemExit("cmd sID=%d: cùng chuỗi nguồn %r nhưng %d bản dịch "
                                 "khác nhau (%s)" % (sid, cur[:40], len(vals),
                                 ", ".join("cmd/%d" % c for c, _ in rows)))
            cn, val = rows[0]
            cur = cur.replace(chr(10), BS_N)
            val = val.replace(chr(10), BS_N)
            src = data_s["target"][ti]["scriptText"]
            n_hit = src.count(_Q + cur + _Q)
            if n_hit < 1:
                print("! %d/cmd/%d: không thấy chuỗi cũ trong scriptText" % (sid, cn))
                continue
            if n_hit != len(rows):
                print("   (sID=%d: chuỗi nguồn có %d chỗ, sheet khai %d ô — thay cả %d)"
                      % (sid, n_hit, len(rows), n_hit))
            enc_old = json.dumps(src, ensure_ascii=False)
            enc_new = json.dumps(src.replace(_Q + cur + _Q, _Q + val + _Q), ensure_ascii=False)
            if out_s.count(enc_old) != 1:
                raise SystemExit("cmd sID=%d: scriptText khớp %d lần" % (sid, out_s.count(enc_old)))
            out_s = out_s.replace(enc_old, enc_new)
            data_s["target"][ti]["scriptText"] = src.replace(_Q + cur + _Q, _Q + val + _Q)
        # …và trong 143 script chương: thay MỌI chỗ có cùng chuỗi nguồn. Chuỗi nguồn giống
        # nhau thì bản dịch cũng phải giống nhau, nên thay hết là đúng chứ không phải ẩu.
        chap_hits = 0
        for o in env_s.objects:
            if o.type.name != "TextAsset":
                continue
            dch = o.read()
            if dch.m_Name == "ScenarioData":
                continue
            raw_c = dch.m_Script
            raw_c = raw_c if isinstance(raw_c, str) else bytes(raw_c).decode("utf-8", "replace")
            new_c = raw_c
            for _ti, _sid, _cn, cur, val in cmd_edits:
                new_c = new_c.replace(_Q + cur.replace(chr(10), BS_N) + _Q,
                                      _Q + val.replace(chr(10), BS_N) + _Q)
            if new_c != raw_c:
                chap_hits += 1
                dch.m_Script = new_c
                dch.save()
        print("   (%d script chương cũng được sửa theo)" % chap_hits)

    # ---- ScenarioData.selText: JSON LỒNG trong JSON
    if sel_edits:
        # Vá theo CẢ chuỗi `selText[idx]` (một JSON `{"target":[…]}`), không theo từng
        # lựa chọn: hai lựa chọn có thể trùng chữ nhau, thay theo chuỗi sẽ đụng cả hai.
        for ti, sid, sidx in sorted({(a, b, c) for a, b, c, _o, _u, _v in sel_edits}):
            cur_raw = data_s["target"][ti]["selText"][sidx]
            doc = json.loads(cur_raw)
            for a, b, c, opt, cu, val in sel_edits:
                if (a, b, c) != (ti, sid, sidx):
                    continue
                assert doc["target"][opt] == cu, "selText[%d] lựa chọn %d không như đã đọc" % (sidx, opt)
                doc["target"][opt] = val
            new_raw = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
            oj = json.dumps(cur_raw, ensure_ascii=False)
            nj = json.dumps(new_raw, ensure_ascii=False)
            if out_s.count(oj) != 1:
                raise SystemExit("selText sID=%d [%d]: chuỗi cũ khớp %d lần"
                                 % (sid, sidx, out_s.count(oj)))
            out_s = out_s.replace(oj, nj)

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    tag = os.path.splitext(os.path.basename(new_f))[0].replace(" ", "")
    json_bak = [None]        # bundle json bị hai nhánh ghi, chỉ chụp backup một lần
    if changed_s or sel_edits or cmd_edits:
        bak = backup_path(os.path.join(ROOT, "_backup", "scenario01.%s" % tag))
        shutil.copy2(SCENARIO, bak); print("backup ->", bak)
        d_s.m_Script = ("﻿" if raw_s.startswith("﻿") else "") + out_s.lstrip("﻿")
        d_s.save()
        with open(SCENARIO, "wb") as f:
            f.write(env_s.file.save(packer="lz4"))
        print("đã ghi", SCENARIO, os.path.getsize(SCENARIO))
        _, _, back = load_text(SCENARIO, "ScenarioData")
        rd = json.loads(back.lstrip("﻿"))
        for ti, sid, idx, cur, val in changed_s:
            assert rd["target"][ti]["text"][idx] == val, "đọc lại %s text[%d] sai" % (sid, idx)
            assert rd["target"][ti]["loadLine"] == data_s["target"][ti]["loadLine"]
        for ti, sid, sidx, opt, cur, val in sel_edits:
            got = json.loads(rd["target"][ti]["selText"][sidx])["target"][opt]
            assert got == val, "đọc lại selText sID=%s [%d/%d] sai" % (sid, sidx, opt)
        if sel_edits:
            print("  đọc lại: %d lựa chọn khớp" % len(sel_edits))
        print("  đọc lại: %d ô khớp, loadLine nguyên vẹn" % len(changed_s))

    if rule_edits:
        if json_bak[0] is None:
            json_bak[0] = backup_path(os.path.join(ROOT, "_backup", "json.%s" % tag))
            shutil.copy2(JSONB, json_bak[0]); print("backup ->", json_bak[0])
        env_r, d_r, raw_r = load_text(JSONB, "TerminalRuleData")
        out_r = raw_r
        for i, k, cur, val in rule_edits:
            oj, nj = json.dumps(cur, ensure_ascii=False), json.dumps(val, ensure_ascii=False)
            if out_r.count(oj) != 1:
                raise SystemExit("rule_body id%d trang %d khớp %d lần" % (i, k, out_r.count(oj)))
            out_r = out_r.replace(oj, nj)
        d_r.m_Script = ("﻿" if raw_r.startswith("﻿") else "") + out_r.lstrip("﻿")
        d_r.save()
        with open(JSONB, "wb") as f:
            f.write(env_r.file.save(packer="lz4"))
        print("đã ghi", JSONB, os.path.getsize(JSONB))
        _, _, back = load_text(JSONB, "TerminalRuleData")
        tr2 = json.loads(back.lstrip("﻿"))
        items2 = {it["id"]: it for g in tr2["data"] for it in g["items"]}
        for i, k, cur, val in rule_edits:
            assert items2[i]["content"][k]["text"] == val, \
                "đọc lại rule_body id%d trang %d sai" % (i, k)
        print("  đọc lại: %d trang rule_body khớp" % len(rule_edits))

    if qa_edits:
        if json_bak[0] is None:
            json_bak[0] = backup_path(os.path.join(ROOT, "_backup", "json.%s" % tag))
            shutil.copy2(JSONB, json_bak[0]); print("backup ->", json_bak[0])
        env_q, d_q, raw_q = load_text(JSONB, "Q&AData")
        out_q = raw_q
        for qg, qq, cur, val in qa_edits:
            oj, nj = json.dumps(cur, ensure_ascii=False), json.dumps(val, ensure_ascii=False)
            if out_q.count(oj) != 1:
                raise SystemExit("Q&A g%d_q%d: chuỗi cũ khớp %d lần" % (qg, qq, out_q.count(oj)))
            out_q = out_q.replace(oj, nj)
        d_q.m_Script = ("\ufeff" if raw_q.startswith("\ufeff") else "") + out_q.lstrip("\ufeff")
        d_q.save()
        with open(JSONB, "wb") as f:
            f.write(env_q.file.save(packer="lz4"))
        print("đã ghi", JSONB, os.path.getsize(JSONB))
        _, _, back_q = load_text(JSONB, "Q&AData")
        lq = json.loads(back_q.lstrip("\ufeff"))["list"]
        for qg, qq, cur, val in qa_edits:
            assert lq[qg]["title"][qq] == val, "đọc lại Q&A g%d_q%d sai" % (qg, qq)
        print("  đọc lại: %d tiêu đề Q&A khớp" % len(qa_edits))

    if gb_edits:
        # Chat Genebark: gán theo CHỈ SỐ rồi dump lại cả asset. Không thay theo chuỗi như
        # nhánh *Data bên dưới, vì nội dung chat có câu trùng nhau (`OK`, `Ừ`…) nên
        # `count(cũ) != 1` sẽ nổ oan. Chốt bù: so bản đã parse, chỉ đúng những chỉ số đã
        # định mới được khác.
        if json_bak[0] is None:
            json_bak[0] = backup_path(os.path.join(ROOT, "_backup", "json.%s" % tag))
            shutil.copy2(JSONB, json_bak[0]); print("backup ->", json_bak[0])
        env_g, d_g, raw_g = load_text(JSONB, "GenebarkChatMainData")
        doc_g = json.loads(raw_g.lstrip("\ufeff"))
        before_g = [(e.get("content") or "") for e in doc_g["data"]]
        spk_b = [e.get("speaker") for e in doc_g["data"]]
        for gn, cur, val in gb_edits:
            assert before_g[gn] == cur, "data[%d] không như đã đọc" % gn
            doc_g["data"][gn]["content"] = val
        bom_g = "\ufeff" if raw_g.startswith("\ufeff") else ""
        d_g.m_Script = bom_g + json.dumps(doc_g, ensure_ascii=False, separators=(",", ":"))
        d_g.save()
        with open(JSONB, "wb") as f:
            f.write(env_g.file.save(packer="lz4"))
        print("đã ghi", JSONB, os.path.getsize(JSONB))
        _, _, back_g = load_text(JSONB, "GenebarkChatMainData")
        doc_b = json.loads(back_g.lstrip("\ufeff"))
        after_g = [(e.get("content") or "") for e in doc_b["data"]]
        assert len(after_g) == len(before_g), "số mục data[] đổi"
        want = {gn: val for gn, _c, val in gb_edits}
        for n, (a, b) in enumerate(zip(before_g, after_g)):
            assert b == want.get(n, a), "data[%d] đổi ngoài dự kiến" % n
        # `speaker` là KHOÁ — không được xê dịch một ly.
        assert spk_b == [e.get("speaker") for e in doc_b["data"]], "cột speaker bị đổi"
        print("  đọc lại: %d ô chat khớp, %d ô khác nguyên vẹn, speaker nguyên vẹn"
              % (len(gb_edits), len(after_g) - len(gb_edits)))

    if json_edits:
        if json_bak[0] is None:
            json_bak[0] = backup_path(os.path.join(ROOT, "_backup", "json.%s" % tag))
            shutil.copy2(JSONB, json_bak[0]); print("backup ->", json_bak[0])
        for asset in sorted({e[0] for e in json_edits}):
            env_j, d_j, raw_j = load_text(JSONB, asset)
            out_j = raw_j
            # Thay theo NGUYÊN MỤC, không theo chuỗi giá trị.
            #
            # Bản trước tìm-thay bằng chính chuỗi cũ, gộp các ô trùng chuỗi lại rồi đòi
            # số chỗ khớp bằng số ô sheet khai. Cách đó sập ở hai chỗ:
            #
            #  - **chuỗi cũ RỖNG**. `dic_ruby/id105` build đang để trống, mà `""` khớp 22
            #    chỗ (mọi ruby trống trong asset), nên nó `SystemExit` — và vì
            #    ScenarioData đã ghi xong từ trước, cả vòng dừng ở trạng thái ghi DỞ:
            #    85 ô thoại đã vào, 15 ô từ điển thì không, không câu nào báo là đã mất.
            #  - hai mục trùng nhau cả chuỗi cũ lẫn ý nghĩa (`TerminalHomeAlertData`
            #    id17/id18) phải gộp thủ công mới thay được.
            #
            # Khoá mục (`id`/`no`) là thứ duy nhất chắc chắn duy nhất, nên dựng lại bản
            # mã hoá JSON của CẢ MỤC và thay đúng một lần. Không đụng được sang mục khác,
            # và giá trị cũ rỗng hay trùng đều không còn là vấn đề.
            ekey = KEY_OF.get(asset, "id")
            dj0 = json.loads(raw_j.lstrip("﻿"))
            per = {}
            for a, field, eid, cur, val, root in [e for e in json_edits if e[0] == asset]:
                per.setdefault((root, eid), []).append((field, cur, val))
            for (root, eid), fields in sorted(per.items(), key=lambda kv: str(kv[0])):
                ent = next((e for e in entries(dj0, root) if e.get(ekey) == eid), None)
                if ent is None:
                    raise SystemExit("%s: không có %s %s khi ghi" % (asset, ekey, eid))
                oj = json.dumps(ent, **JDUMP)
                n_hit = out_j.count(oj)
                if n_hit != 1:
                    raise SystemExit("%s %s%s: nguyên mục khớp %d chỗ trong asset (cần 1)"
                                     % (asset, ekey, eid, n_hit))
                new_ent = json.loads(json.dumps(ent, **JDUMP))
                for field, cur, val in fields:
                    if field_get(new_ent, field) != cur:
                        raise SystemExit("%s %s%s field %r không như đã đọc"
                                         % (asset, ekey, eid, field))
                    field_set(new_ent, field, val)
                out_j = out_j.replace(oj, json.dumps(new_ent, **JDUMP), 1)
            d_j.m_Script = ("﻿" if raw_j.startswith("﻿") else "") + out_j.lstrip("﻿")
            d_j.save()
            with open(JSONB, "wb") as f:
                f.write(env_j.file.save(packer="lz4"))
            print("đã ghi", JSONB, os.path.getsize(JSONB))
            _, _, back = load_text(JSONB, asset)
            dj_back = json.loads(back.lstrip("﻿"))
            for a, field, eid, cur, val, root in [e for e in json_edits if e[0] == asset]:
                ent = next(e for e in entries(dj_back, root)
                           if e.get(KEY_OF.get(asset, "id")) == eid)
                assert field_get(ent, field) == val, "đọc lại %s id%d sai" % (asset, eid)
            print("  đọc lại: %s khớp" % asset)


main()
