# -*- coding: utf-8 -*-
"""Soi một danh từ riêng tiếng Nhật có đang được dịch NHIỀU KIỂU hay không.

## Vì sao cần

Trong một phiên làm việc, cùng một lớp lỗi phải tìm bằng tay ba lần, lần nào cũng nhờ
tình cờ chứ không nhờ công cụ:

```
黒服   ->  "Hắc phục" 216 chỗ  /  "Áo đen" 60 chỗ
救済   ->  "Cứu Rỗi"           /  "Cứu Tế"
火守   ->  "Hoả Thủ"  /  "Hỏa Thủ"  /  "Hộ Hỏa"
```

Không phép kiểm nào bắt được. `--audit-sheet` so sheet với build **theo từng ô**, nên
hai ô cùng lệch một kiểu thì nó im. `--check-chat` chỉ soi 184 cặp chat. Phép ghép
`cmd`↔`alert` so NGUYÊN CÂU Nhật, nên `スキル更新：火守` và
`スキル『火守』が付与されました` không thành cặp — chúng chỉ dùng chung một danh từ.

Trục đúng là **thuật ngữ**, không phải ô và cũng không phải câu.

## Cách làm

Ghép 1:1 theo vị trí với bản gốc 1.0.2, rồi:

1. Rút danh từ riêng từ bản GỐC: mọi cụm trong `『…』` và cả hai nửa của thẻ ruby
   `[gốc'đọc]`. Đây là chỗ chính game tự đánh dấu tên riêng — không phải tôi đoán.
2. Với mỗi thuật ngữ, gom mọi ô có nó, rút "ứng viên bản dịch" từ phía tiếng Việt.
3. Xét **ĐỘ PHỦ**: bản dịch thật của một thuật ngữ phải có mặt ở gần như MỌI ô nói về
   nó. Lấy ứng viên phủ rộng nhất, rồi chỉ ra các ô nó KHÔNG phủ — đó là chỗ lạc đàn.

Bản đầu tôi làm khác và sai: liệt mọi cụm hoa rồi báo khi có >= 2 cụm. Với thuật ngữ
xuất hiện 301 ô, những tên riêng đi ngang câu (Miyabi, Kohaku) trông y hệt một cách
dịch, và nhiễu nhấn chìm tín hiệu.

Hai cái bẫy nhỏ đã dính:

- `[A-ZA-Y]` với dải Unicode **không phải** lớp chữ hoa. Dải À(00C0)-Ỹ(1EF8) chứa cả
  chữ thường tiếng Việt, nên nó bắt cả `ũng`, `ày`. Phải hỏi `isupper()` từng ký tự.
- Chữ hoa **đầu câu** không nói lên điều gì, phải bỏ.

## Ba loại nhiễu đã lọc (01/09/2026)

Vòng rà 16 mục cho ra 4 lỗi thật; 12 mục còn lại là nhiễu, và chúng rơi gọn vào ba lớp.
Lọc xong: **16 -> 6 mục, không mất lỗi thật nào** (kiểm bằng cách chạy lại trên
`_backup\\scenario01.UNLOGICAL_v2(81)` — bản trước khi vá — vẫn báo đủ `議論時間` và
`代行`).

1. **Thẻ ruby bị đếm hai lần.** `[議論時間'ディスカッションタイム]` sinh hai thuật ngữ bám
   vào đúng một tập ô, nên mọi lỗi ruby đều được báo hai lần với nội dung y hệt. Gộp lại
   một mục, in nhãn `gốc'đọc`.
2. **Tên riêng trong ngoặc kép nằm trong ngoặc thoại bị bỏ sót.** `re.finditer` không
   chồng lấn, nên một regex gộp cả ba loại ngoặc sẽ MỞ ở `「` rồi ĐÓNG ở dấu `"` đầu
   tiên: `「À, cái tên "Miyabi" là…」` cho ra rác `À, cái tên ` còn `Miyabi` thì mất hẳn.
   Ô đó bị báo là "không nhắc tên thuật ngữ" trong khi nó có nhắc. Nay quét riêng từng
   loại ngoặc.
3. **Dạng ruby tiếng Việt so với dạng trần.** Bản dịch viết `[Kính giới'Recollection]`
   ở lần nhắc đầu rồi các lần sau chỉ ghi `Kính giới` — đúng quy ước. Bước "bỏ chuỗi
   con" lại xoá ứng viên `Kính giới`, để dạng ruby làm bản dịch chính, rồi báo 4 ô cuối
   truyện là thiếu. Nay `_goc()` gộp hai dạng khi trả lời "ô này có nhắc tên không",
   nhưng KHÔNG dùng lúc chọn bản dịch chính.

Kèm theo: hoà nhau về độ phủ thì ứng viên **nằm trong ngoặc** thắng. `自己犠牲` có 3 ô
`Tự hy sinh` (đều trong ngoặc) và 3 ô `Pegasus là` (chỉ là hai từ dính nhau trong câu
"Lá bài Pegasus là…"); không có luật này thì ai thắng tuỳ thứ tự `Counter`, và nó đã
từng lật.

Đây là phép **gợi ý**, không phải chốt chặn: nó chỉ chỗ đáng nhìn, người quyết định.
Đừng đợi nó về 0 — 6 mục còn lại đã rà từng ô và đều đúng như đang có.

    python tools\\check_term_consistency.py                # mọi thuật ngữ
    python tools\\check_term_consistency.py --term=...     # một thuật ngữ
    python tools\\check_term_consistency.py --min=3        # chỉ thuật ngữ >= 3 ô
    python tools\\check_term_consistency.py --build=<file> # soi một bản build khác
"""
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402

SCEN = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
JSONB = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
STOCK = r"D:\Downloads\UNLOGICAL_v2\Data\StreamingAssets"


def arg(name, default=None):
    for a in sys.argv:
        if a.startswith("--%s=" % name):
            return a.split("=", 1)[1]
    return default


ONLY = arg("term")
MIN_CELLS = int(arg("min", "2"))
BUILD = arg("build", SCEN)

JP_BRACKET = re.compile("\u300e([^\u300e\u300f\n]{1,14})\u300f")
JP_RUBY = re.compile(r"\[([^\[\]\n']{1,14})'([^\[\]\n]{1,14})\]")
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
# KHONG lay `'` lam dau trich dan: `'` la dau phan cach cua the ruby `[goc'doc]`, nen
# coi no la ngoac se cat `[Kinh gioi'Recollection]` thanh ung vien gia va bao cao mot
# the ruby HOP LE nhu la loi.
# NHIEU 2/3 -- MOI loai ngoac quet RIENG, khong gop vao mot lop ky tu.
#
# Ban truoc gop ca ba loai vao mot regex. `re.finditer` khong chong lan, nen voi
# `\u300cA, cai ten "Miyabi" la do...\u300d` no MO o `\u300c` roi DONG o dau `"`: ra ung vien rac
# `A, cai ten `, con `Miyabi` khong bao gio duoc rut. Nhanh chu-hoa cung khong cuu
# duoc vi `Miyabi` dung ngay sau dau `"` -- bi coi la hoa DAU CAU nen bi bo.
#
# Hau qua: moi ten rieng dat trong ngoac kep BEN TRONG ngoac thoai deu vo hinh, va o
# do bi bao la "khong nhac ten thuat ngu" trong khi no co nhac -- `[\u96c5\u706b] 7/8` chinh
# la vay, o "lac dan" that ra viet dung `"Miyabi"`.
VN_QUOTES = [
    re.compile("\"([^\"\n]{1,30})\""),
    re.compile("\u300e([^\u300e\u300f\n]{1,30})\u300f"),
    re.compile("\u300c([^\u300c\u300d\n]{1,30})\u300d"),
]


def _goc(c):
    """Dang ruby tieng Viet `[X'Y]` -> `X`. Chuoi khong phai ruby thi tra ve nguyen.

    NHIEU 3/3. Ban dich viet ruby o lan nhac DAU (`[Kinh gioi'Recollection]`) roi cac
    lan sau chi ghi `Kinh gioi` -- dung quy uoc, khong phai lech thuat ngu. Nhung buoc
    "bo chuoi con" lai xoa ung vien `Kinh gioi` (vi no nam trong dang ruby), de dang
    ruby lam ban dich chinh, roi bao 4 o cuoi truyen la "thieu".

    Phai got ca dau `[` mo: khong thi con `[Kinh gioi`, mot chuoi khac han.

    Van bat duoc loi that: `Thoi gian thao luan'Discussion Time` va
    `thoi gian thao luan'discussion time` got xong ra HAI goc khac nhau vi lech chu hoa.
    """
    if "'" not in c:
        return c
    g = c.split("'", 1)[0].strip().lstrip("[").strip()
    return g if len(g) >= 2 and "[" not in g else c
# Chu hoa o nhung vi tri nay khong noi len dieu gi: dau cau, va ngay sau dau mo ngoac.
# Thieu `\u300c` (kieu ngoac thoai cua game) thi `Mot`, `Von`, `Thay` lot luoi va bi
# doc nham thanh mot cach dich khac.
SENT_END = (".", "!", "?", "\u2026", "\u300d", "\u300f", "\u2015", "\u2014",
            "\u300c", "\u300e", "(", "\uff08", "\u201c", '"', "'", ":", "\uff1a",
            ",", ";", "-")


def load(path, name):
    for o in UnityPy.load(path).objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        if d.m_Name == name:
            r = d.m_Script
            s = r if isinstance(r, str) else bytes(r).decode("utf-8", "replace")
            return json.loads(s.lstrip("\ufeff"))
    raise SystemExit("khong thay %s trong %s" % (name, path))


def dump_assets(path):
    d = {}
    for o in UnityPy.load(path).objects:
        if o.type.name != "TextAsset":
            continue
        t = o.read()
        r = t.m_Script
        d[t.m_Name] = r if isinstance(r, str) else bytes(r).decode("utf-8", "replace")
    return d


def pairs():
    """[(jp, vn)] ghep 1:1 theo vi tri, gom ScenarioData va cac asset json."""
    out = []
    og = load(os.path.join(STOCK, "scenario", "scenario01"), "ScenarioData")
    cur = load(BUILD, "ScenarioData")
    if len(og["target"]) != len(cur["target"]):
        raise SystemExit("so target lech giua goc va build")
    for a, b in zip(og["target"], cur["target"]):
        for xo, xc in zip(a.get("text") or [], b.get("text") or []):
            if xo and xc:
                out.append((xo, xc))
        for so, sc in zip(a.get("selText") or [], b.get("selText") or []):
            if not so or not sc:
                continue
            try:
                lo = json.loads(so)["target"]
                lc = json.loads(sc)["target"]
            except Exception:
                continue
            for xo, xc in zip(lo, lc):
                if xo and xc:
                    out.append((xo, xc))

    do = dump_assets(os.path.join(STOCK, "json", "json"))
    dc = dump_assets(JSONB)
    STR = re.compile(r'"([^"\\]{2,200})"')
    for k in do:
        if k not in dc:
            continue
        a = STR.findall(do[k])
        b = STR.findall(dc[k])
        if len(a) == len(b):
            out.extend((x, y) for x, y in zip(a, b) if x and y)
    return out


def candidates(vn):
    """(moi ung vien, rieng cac ung vien NAM TRONG NGOAC TRICH DAN).

    Ngoac la tin hieu manh nhat: ban goc danh dau ten rieng bang `『』`, va ban dich giu
    lai bang `"..."` hoac `『』`. Moi ca lech thuat ngu tim duoc bang tay trong phien nay
    -- "Ho Hoa", "Tran Chau", "Me cung toa lau dai" -- deu nam trong ngoac. Con cum hoa
    tran thi phan lon la rac (`Xe buc anh`, `Dang nao thi anh`).
    """
    c = set()
    quoted = set()
    toks = [(m.group(0), m.start(), m.end()) for m in WORD.finditer(vn)]
    n = len(toks)
    for a in range(n):
        if not toks[a][0][:1].isupper():
            continue
        truoc = vn[:toks[a][1]].rstrip()
        dau_cau = (not truoc) or truoc[-1] in SENT_END
        # Tieng Viet thuong chi HOA CHU DAU cua ten rieng: `Kinh gioi`, `Hoa Thu`,
        # `Trai tim thien su`. Neu chi noi cac tu HOA lien tiep thi ung vien bi cat cut
        # thanh `Kinh`, `Thien` -- do la ly do bao cao truoc do ghi "hau het dich la
        # 'Kinh'". Nen cho noi them toi 3 tu THUONG sau tu hoa dau tien.
        for b in range(a, min(a + 4, n)):
            if b > a and toks[b][1] - toks[b - 1][2] > 1:
                break                      # co dau cau chen giua -> dut cum
            if dau_cau and b == a:
                continue
            t = vn[toks[a][1]:toks[b][2]]
            if len(t) >= 2:
                c.add(t)
    for rx in VN_QUOTES:
        for m in rx.finditer(vn):
            t = m.group(1).strip()
            if 2 <= len(t) <= 30:
                c.add(t)
                quoted.add(t)
    return c, quoted


def main():
    ps = pairs()
    print("o ghep duoc (goc <-> build): %d" % len(ps))

    # `『』` trong ban goc dung cho HAI viec khac nhau: dat ten rieng, va nhan manh mot
    # tu thong thuong. `本番` co 3 o dong ngoac nhung 17 o khac dung tran -- do la tu
    # thuong ("tran that", "man choi that", "luc bat dau that su"), dich linh hoat theo
    # ngu canh moi dung, ep ve mot chuoi la sai. Nen dem ca hai kieu roi bo tu nao xuat
    # hien NGOAI ngoac nhieu hon trong ngoac.
    ngoai = Counter()
    trong = Counter()
    for jp, _vn in ps:
        for t in JP_BRACKET.findall(jp):
            trong[t] += 1
        for t in set(JP_BRACKET.findall(jp)):
            pass
    for jp, _vn in ps:
        sach = JP_BRACKET.sub("", jp)
        for t in trong:
            if t in sach:
                ngoai[t] += 1

    terms = defaultdict(list)
    co_ruby = set()
    doc_cua = {}          # nua DOC -> nua GOC, de gop cap ruby lai lam mot muc
    for i, (jp, _vn) in enumerate(ps):
        found = set(JP_BRACKET.findall(jp))
        for a, b in JP_RUBY.findall(jp):
            found.add(a)
            found.add(b)
            co_ruby.add(a)
            co_ruby.add(b)
            doc_cua[b] = a
        for t in found:
            terms[t].append(i)
    print("thuat ngu rut tu ban goc: %d" % len(terms))

    # NHIEU 1/3 -- the ruby `[goc'doc]` sinh HAI thuat ngu bam vao dung mot tap o, nen
    # moi loi ruby luon duoc bao hai lan voi noi dung y het nhau (`[議論時間]` va
    # `[ディスカッションタイム]`). Bo nua DOC khi nua GOC co cung tap o, va in nhan
    # `goc'doc` de khong mat thong tin.
    bo_nua_doc = set()
    nhan_ruby = {}
    for b, a in doc_cua.items():
        if a in terms and set(terms[a]) == set(terms[b]):
            bo_nua_doc.add(b)
            nhan_ruby[a] = "%s'%s" % (a, b)

    bao = []
    for t, idxs in terms.items():
        if ONLY and t != ONLY:
            continue
        if t in bo_nua_doc and not ONLY:
            continue
        if len(idxs) < MIN_CELLS:
            continue
        cov = Counter()
        cand_of = {}
        quo_of = {}
        for i2 in idxs:
            cs, qs = candidates(ps[i2][1])
            cand_of[i2] = cs
            quo_of[i2] = qs
            for c in cs:
                cov[c] += 1
        if not cov:
            continue
        # Dang ruby tieng Viet `X'Y` va dang tran `X` la CUNG mot cach goi -- xem `_goc`.
        # Chi dung de tra loi "o nay co nhac ten thuat ngu khong", KHONG dung de chon
        # ban dich chinh: got o buoc chon se lam `[Hy sinh than minh'Pegasus]` rut lai
        # va keo `Pegasus la` len lam ban dich chinh.
        goc_of = {i2: {_goc(c) for c in cand_of[i2]} for i2 in idxs}
        # Bo ung vien la CHUOI CON cua mot ung vien khac co do phu tuong duong.
        #
        # Khong co buoc nay thi `Hoa` (6/6) thang `Hoa Thu` (5/6) va phu luon ca o
        # dung `Ho Hoa` -- khong con o nao "thieu", nen ca 火守 bi bo sot. Nguong 0.8
        # de khong cat nham chieu nguoc: `Spirit` phu rong hon `Cac Spirit` nhieu, la
        # ban dich that, phai giu.
        loai = set()
        for a in cov:
            for b in cov:
                if a != b and a in b and cov[b] >= cov[a] * 0.8:
                    loai.add(a)
                    break
        cov = Counter({c: n for c, n in cov.items() if c not in loai})
        if not cov:
            continue
        # Hoa nhau ve do phu thi ung vien NAM TRONG NGOAC thang -- cung ly le voi
        # `candidates()`: ngoac la cho ban dich danh dau ten rieng.
        #
        # `自己犠牲` co dung 3 o cho `Tu hy sinh` (deu trong ngoac) va 3 o cho
        # `Pegasus la` (khong o nao trong ngoac, chi la hai tu dinh nhau trong cau
        # "La bai Pegasus la ..."). Khong co luat nay thi ai thang phu thuoc vao thu tu
        # Counter -- va no da tung lat, bien bao cao thanh "hau het dich la 'Pegasus la'".
        q_cov = Counter()
        for i2 in idxs:
            for c in quo_of[i2]:
                q_cov[c] += 1
        top, ntop = max(cov.items(), key=lambda kv: (kv[1], q_cov.get(kv[0], 0), -len(kv[0])))
        if ntop < max(2, len(idxs) * 0.6):
            continue           # chua du chac `top` chinh la ban dich cua thuat ngu
        gtop = _goc(top)
        thieu = [i2 for i2 in idxs
                 if top not in cand_of[i2] and gtop not in goc_of[i2]]
        if not thieu or len(thieu) > 10:
            continue
        # Chi bao khi o lac dan THAT SU co mot cach goi khac -- neu no chi khong nhac
        # ten thuat ngu thi do la dien dat binh thuong, khong phai lech thuat ngu.
        # Truoc buoc nay: 55 muc, phan lon la danh tu chung (`人間` -> "con nguoi").
        pho_bien = {c for c in cov if cov[c] >= max(2, ntop * 0.5)}
        # Cach goi thay the phai NAM TRONG NGOAC. Khong co dieu kien nay thi moi cum
        # hoa tran deu thanh ung vien va bao cao ngap rac -- do la buoc lam so muc
        # nhay 25 -> 39 ma khong them mot loi that nao.
        co_thay = []
        for i2 in thieu:
            khac = [c for c in quo_of[i2]
                    if c not in pho_bien and len(c) >= 3
                    and c not in top and top not in c]
            if khac:
                co_thay.append((i2, sorted(khac, key=len, reverse=True)[:3]))
        if not co_thay:
            continue
        # TEN RIENG hay danh tu chung? Hai tin hieu, deu lay tu du lieu chu khong doan:
        #   - thuat ngu co the RUBY `[han'katakana]`: game tu danh dau la ten rieng;
        #   - ban dich chiem uu the viet HOA.
        # Khong loc thi `人間` -> "con nguoi", `好き` -> "thich", `誰か` -> "ai do" tran
        # vao danh sach, va "cach goi khac" chung nhat duoc chi la chu hoa dau cau.
        if not (t in co_ruby or top[:1].isupper()):
            continue
        # tu thong thuong duoc nhan manh bang `『』`, khong phai ten rieng
        if t not in co_ruby and ngoai.get(t, 0) > trong.get(t, 0):
            continue
        bao.append((t, len(idxs), top, ntop, co_thay))

    bao.sort(key=lambda r: (len(r[4]), -r[1]))
    print("")
    print("THUAT NGU CO O LAC DAN: %d" % len(bao))
    print("")
    for t, n, top, ntop, co_thay in bao:
        print("  [%s]  %d o -- hau het dich la %r (%d/%d)"
              % (nhan_ruby.get(t, t), n, top, ntop, n))
        for i2, khac in co_thay:
            print("      o dung %s thay vi %r:" % (" / ".join(repr(k) for k in khac), top))
            print("         JP: %r" % ps[i2][0].replace("\n", " ")[:76])
            print("         VN: %r" % ps[i2][1].replace("\n", " ")[:76])
        print("")


if __name__ == "__main__":
    main()
