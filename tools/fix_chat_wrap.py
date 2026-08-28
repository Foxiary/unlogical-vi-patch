# -*- coding: utf-8 -*-
"""Ngắt dòng cho asset chat Genebark — **theo dấu câu**, và không dòng nào quá lề.

Widget: `ui_jp` › `genebark.prefab` › `GenebarkChatContentItem` (1388×166) ›
`Message_TMP` rect **1210×80**, cỡ **32**, `characterSpacing` **5**,
`lineSpacing` −60, `m_TextWrappingMode = 1` (wrap **BẬT**), `m_overflowMode = 0`,
`m_margin` 0. Không có bong bóng — mỗi tin là một khối chữ canh trái, giữa các tin có
vạch `UnderLine` rộng 1388.

## Vì sao cần tool này

Bản Việt hiện ngắt theo **bề rộng**, không theo dấu câu: đo 926 chỗ ngắt trong asset
thì **843 (91%) nằm giữa câu**, 52 sau dấu kết câu, 31 sau dấu phẩy. Ra những chỗ đọc
gãy như `…gửi đến rồi. Tôi ⏎ check qua thì thấy ok…`. Đó là di sản của đợt ngắt dòng
10/08/2026 (backup `_backup\\scenario01.prechatbreaks`, tool đã mất) — nó bắt chước cách
tác giả Nhật canh dòng cho khung của họ, mà tiếng Việt không có vị trí tương ứng.

Luật lấy gốc từ caption giữa màn (`fix_center_caption_wrap.split_punct`, memory
`unlogical-line-break-punctuation`) — **ưu tiên dấu câu, không cân độ dài** — nhưng phải
đổi một chỗ cho khớp cách bản Nhật ngắt: **dấu kết câu (`. ! ? ...`) thì LUÔN ngắt, dấu
phẩy (`, ; :`) chỉ dùng khi câu còn quá lề.** Gom tham lam tới sát khung như bản
caption sẽ gộp mất những câu mà bản Nhật tách ra — đo được 346/1194 ô bị gộp. Xem bảng so
ba luật trong docstring của `split_punct()`.

## Lề phải phải bằng lề trái — và vì sao KHÔNG được nhờ TMP tự ngắt

Yêu cầu 28/08/2026: *"lề phải nên giống lề trái, từ viền tới icon ảnh"*. Đo trên ảnh
`_2026-08-28_13-17-14.png`, quy về canvas bằng tỉ lệ vạch ngăn (1283 px ảnh / 1388 prefab
= 0,9243; hiệu chỉnh chéo trên 5 dòng biết trước chữ ra tỉ lệ 0,919–0,929, khớp):

| mốc | canvas px |
|---|---|
| mép trái panel (`UnderLine`) | 39 |
| mép trái icon | 84 ⇒ **lề trái = 45** |
| mép trái chữ | 177 |
| mép phải panel | 1427 |

⇒ chữ phải dừng ở `1427 − 45 = 1382`, tức bề rộng **1382 − 177 = 1205 px**. Đó là `LIMIT`.

**Bản đầu của tool để mệnh đề quá dài cho TMP tự ngắt — điều đó phá lề.** Bề rộng wrap
*thực tế* của TMP **không phải 1210 như prefab ghi**: kẹp được từ `data[40]`, một dòng
trong dữ liệu mà máy vẽ thành hai — vẽ hết `…quá nửa số buổi` (1269 px) rồi mới xuống
hàng khi thêm ` đâu` (1342 px), nên `W ∈ [1269, 1342)`. Rộng hơn lề 1205, nên mỗi dòng
nhờ TMP là chữ chạy quá mép panel — trên ảnh, dòng đó chạy tới x=1800 trong khi vạch ngăn
dừng ở 1774.

Nên bây giờ **không dòng nào được nhờ TMP**: sau dấu kết câu và dấu phẩy, còn quá lề thì
`split_space_balanced()` ngắt ở khoảng trắng. Kết quả: dòng rộng nhất đúng 1205 px ⇒ mép
phải 1382 ⇒ **lề phải 45 = lề trái 45**.

## Số đo, và nó được hiệu chỉnh thế nào

Chat dùng **font khác** ô thoại ADV: `FOT-DNPShueiMGoStd-B SDF-Dynamic`. Bản Dynamic có
glyph table **rỗng** (nạp lúc chạy), nên lấy advance từ bản tĩnh cùng typeface
`FOT-DNPShueiMGoStd-B SDF` trong `font_jp` (2803 ký tự, pointSize 58). Dùng advance của
`adv_layout` (font `FOT-NewRodinProN-DB`) cho chat là **sai font**.

Công thức: `(Σadvance + 5×n) × 32 / 58`. Hiệu chỉnh trên ảnh chụp Ryujinx thật
`_2026-08-14_21-39-21.png`: tỉ lệ canvas→màn hình lấy từ vạch `UnderLine` (đo 1283 px /
prefab 1388 = 0,9243), rồi so 10 dòng chữ biết trước — tỉ lệ model/đo trung bình **1,010**,
dòng dài nhất khớp đúng (799 px so với 799). Công thức kiểu `fix_adv_wrap.wd()`
(`(n−1)×CS×F/100`) thấp hơn 6%, **không dùng cho widget này**.

Mốc kiểm chứng: đo bản Nhật gốc ra **0/1194 dòng vượt 1210**, rộng nhất 834 px (69%) —
nhà phát triển canh rất thoáng. Bản Việt trước khi sửa: **7 ô có dòng vượt**, rộng nhất
1376 px.

## Chốt chặn

- Chỉ đổi **space thành `\\n`**: assert bản làm phẳng trước và sau giống hệt nhau.
- Không cắt bên trong `[...]` — tag được che trước khi tách rồi trả lại.
- `[主人公]` đo theo **tên engine thật sự vẽ** (`Kanna`), không đo 5 ký tự của tag.
- Sau khi ghi, đòi **mọi** dòng ≤ 1205 — không còn ngoại lệ nào. Bản đầu tha dòng
  "không cắt được theo dấu câu"; nay không tha, vì TMP ngắt rộng hơn lề.

**Tự dò lại từ câu chữ hiện tại**, nên chạy lại được sau mỗi vòng merge (sheet làm phẳng
sạch `\\n`). Không ghim theo chỉ số ô.

    python tools\\fix_chat_wrap.py            # chạy thử
    python tools\\fix_chat_wrap.py --apply
    python tools\\fix_chat_wrap.py --check    # gate, còn dòng nào quá lề -> exit 1
"""
import collections
import io
import json
import os
import re
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
FONT_BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "font", "font_jp")
FONT_ASSET = "FOT-DNPShueiMGoStd-B SDF"
CACHE = os.path.join(HERE, "_chat_advances.json")
STOCK = r"D:\Downloads\UNLOGICAL_v2\Data\StreamingAssets\json\json"
BACKUP = os.path.join(ROOT, "_backup", "json.chatwrap")

APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

POINT_SIZE = 58.0
FONT_SIZE = 32.0
CHAR_SPACING = 5.0
# Lề: đo trên ảnh chụp thật `_2026-08-28_13-17-14.png`, quy về canvas bằng tỉ lệ vạch
# ngăn — mép trái panel 39, mép trái icon 84 (=> lề trái 45), mép trái chữ 177, mép phải
# panel 1427. Lề phải bằng lề trái ⇒ chữ dừng ở 1427−45=1382 ⇒ bề rộng 1382−177 = 1205.
LIMIT = 1205.0

# Tên engine thay vào `[主人公]`. **Không phải `環無`** như `adv_layout` dùng: ảnh chụp máy
# thật cho thấy bản Việt hiện `Kanna`, và hai cái rộng khác nhau — `環無` 69,5 px so với
# `Kanna` 105,5 px, lệch +36 px trên mỗi lần xuất hiện (40 mục chat có token).
# Đo lại 28/08 bằng tên thật: dòng có token rộng nhất 1146 px, vẫn dưới lề 1205 nên bản
# đã ghi không phải làm lại.
# LƯU Ý: người chơi tự đặt tên được, tên dài hơn `Kanna` sẽ nới các dòng này ra thêm —
# 1146 px chừa được 59 px, tức khoảng 3 ký tự Latin nữa.
DEFAULT_PLAYER_NAME = "Kanna"

TAG = re.compile(r"\[[^\[\]\n]*\]")
# Dấu câu + khoảng trắng.  Đòi có khoảng trắng phía sau nên `16h`, `1.5` không bị tách.
SENT = re.compile(r"(?<=[.!?…])\s+")      # dấu KẾT CÂU — luôn ngắt
COMMA = re.compile(r"(?<=[,;:])\s+")      # dấu phẩy — chỉ ngắt khi dòng còn quá khung
PUNCT = re.compile(r"(?<=[.!?,;:…])\s+")  # cả hai, dùng cho chốt "còn cắt được không"
MASK = "\uf8ff"                # ký tự riêng, không có trong dữ liệu


def load_advances():
    if os.path.exists(CACHE):
        return {int(k): v for k, v in json.load(open(CACHE)).items()}
    env = UnityPy.load(FONT_BUNDLE)
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if not isinstance(t, dict) or t.get("m_Name") != FONT_ASSET:
            continue
        g = {x["m_Index"]: x["m_Metrics"]["m_HorizontalAdvance"] for x in t["m_GlyphTable"]}
        adv = {c["m_Unicode"]: g[c["m_GlyphIndex"]]
               for c in t["m_CharacterTable"] if c["m_GlyphIndex"] in g}
        json.dump({str(k): v for k, v in adv.items()}, open(CACHE, "w"))
        return adv
    raise SystemExit("không thấy %s trong %s" % (FONT_ASSET, FONT_BUNDLE))


ADV = load_advances()


def shown(s):
    """Chữ engine thật sự vẽ: `[主人公]` thành tên mặc định, tag khác giữ nguyên."""
    return TAG.sub(lambda m: DEFAULT_PLAYER_NAME if m.group(0) == "[主人公]" else m.group(0), s)


def width(s):
    d = shown(s)
    return (sum(ADV.get(ord(c), POINT_SIZE) for c in d) + CHAR_SPACING * len(d)) \
        * FONT_SIZE / POINT_SIZE


def flat(s):
    return re.sub(r"[ \t\u3000]*\n[ \t\u3000]*", " ", s or "").strip()


def split_space_balanced(seg, W):
    """Chốt chặn cuối: mệnh đề không có dấu câu nào mà vẫn quá lề thì ngắt ở **khoảng
    trắng**, chọn chỗ **cân nhất** mà cả hai dòng đều trong lề.

    Cân, không tham lam — khác luật dấu câu ở trên. Gom tham lam tới sát lề sinh ra đuôi
    cụt: `data[89]` ra dòng hai chỉ **60 px** (`đấy`), `data[40]` ra `buổi đâu` 148 px.
    Cân thì ra 643/586 và 678/654. Luật "ngắt theo dấu câu, không cân độ dài" áp cho việc
    *chọn giữa dấu câu và cân*; ở đây không còn dấu câu nào để chọn, nên cân là đúng.

    Mệnh đề rộng nhất trong asset là 1841 px < 2×1205, nên mọi ca đều chỉ cần hai dòng.
    """
    ws = seg.split(" ")
    best = None
    for i in range(1, len(ws)):
        a, b = " ".join(ws[:i]), " ".join(ws[i:])
        wa, wb = W(a), W(b)
        if wa <= LIMIT and wb <= LIMIT:
            d = abs(wa - wb)
            if best is None or d < best[0]:
                best = (d, a, b)
    if best:
        return [best[1], best[2]]
    # Không chỗ nào chia đôi được (một từ dài hơn cả lề) -> tham lam, và báo ra.
    out, cur = [], ""
    for w in ws:
        cand = (cur + " " + w) if cur else w
        if cur and W(cand) > LIMIT:
            out.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out


def split_punct(s):
    """**Dấu kết câu trước, dấu phẩy chỉ khi cần.** Mệnh đề quá dài thì để nguyên.

    Che `[...]` trước khi tách để một dấu câu nằm trong tag không thành chỗ ngắt.

    Đã đo ba luật trên 1194 mục, lấy "khớp số dòng bản Nhật" làm thước:

    | luật | khớp JP | ít dòng hơn JP | nhiều dòng hơn JP |
    |---|---|---|---|
    | gom tham lam tới 1210 | 70% | **346** | 7 |
    | ngắt sau MỌI dấu câu | 62% | 107 | **342** |
    | **kết câu trước, phẩy khi cần** | **74%** | 159 | 156 |

    Gom tham lam **gộp mất câu mà bản Nhật tách**: `data[15]` bản Nhật hai dòng
    (`ちゃんとケーブル挿さってる？` / `またＵＳＢ半挿しになってない？`) mà gom lại chỉ 920 px
    nên ra một dòng. Ngắt sau mọi dấu phẩy thì ngược lại, gãy hơn cả cái đang sửa:
    `data[12]` ra `Này,` / `tự nhiên máy mất tiếng luôn...`.

    Luật này cho `data[729]` ra **đúng ba dòng như bản Nhật** (554 / 219 / 1038 px).
    """
    tags = []

    def hide(m):
        tags.append(m.group(0))
        return MASK + str(len(tags) - 1) + MASK

    masked = TAG.sub(hide, s)

    def back(x):
        return re.sub(MASK + r"(\d+)" + MASK, lambda m: tags[int(m.group(1))], x)

    out = []
    for sent in SENT.split(masked):
        if not sent:
            continue
        if width(back(sent)) <= LIMIT:
            out.append(sent)
            continue
        # Câu này quá khung -> mới dùng tới dấu phẩy, gom tham lam.
        cur = ""
        for part in COMMA.split(sent):
            cand = (cur + " " + part) if cur else part
            if cur and width(back(cand)) > LIMIT:
                out.append(cur)
                cur = part
            else:
                cur = cand
        if cur:
            out.append(cur)
    # Chốt chặn cuối: còn dòng nào quá lề thì ngắt ở khoảng trắng. Không nhờ TMP nữa —
    # bề rộng wrap thực tế của TMP là [1269, 1342) canvas px, RỘNG HƠN lề 1205, nên để
    # nó ngắt là chữ chạy quá lề phải. Xem docstring đầu file.
    fin = []
    for line in out:
        if width(back(line)) <= LIMIT:
            fin.append(line)
        else:
            fin.extend(split_space_balanced(line, lambda x: width(back(x))))
    return [back(x) for x in fin]


def unbreakable(line):
    """Dòng này còn cắt được theo dấu câu nữa không?"""
    tags = []
    masked = TAG.sub(lambda m: (tags.append(m.group(0)), MASK)[1], line)
    return len(PUNCT.split(masked)) == 1


def load_asset(path, name="GenebarkChatMainData"):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name == "TextAsset":
            d = o.read()
            if d.m_Name == name:
                raw = d.m_Script
                if not isinstance(raw, str):
                    raw = bytes(raw).decode("utf-8")
                return env, d, raw
    raise SystemExit("không thấy %s trong %s" % (name, path))


def main():
    env, d, raw = load_asset(BUNDLE)
    data = json.loads(raw.lstrip("\ufeff"))["data"]
    try:
        _, _, sraw = load_asset(STOCK)
        stock = json.loads(sraw.lstrip("\ufeff"))["data"]
    except SystemExit:
        stock = None

    print("Message_TMP %.0f px | cỡ %.0f | charSpacing %.0f | font %s"
          % (LIMIT, FONT_SIZE, CHAR_SPACING, FONT_ASSET))
    if stock:
        wmax = max(width(l) for r in stock for l in (r.get("content") or "").split("\n"))
        nover = sum(1 for r in stock for l in (r.get("content") or "").split("\n")
                    if width(l) > LIMIT)
        print("mốc bản Nhật: rộng nhất %.0f px (%.0f%%), %d dòng vượt khung"
              % (wmax, 100 * wmax / LIMIT, nover))

    todo, stat = [], collections.Counter()
    left_over = []
    for k, r in enumerate(data):
        old = r.get("content") or ""
        if not old.strip():
            continue
        new = "\n".join(split_punct(flat(old)))
        assert flat(new) == flat(old), "data[%d]: chữ bị đổi" % k
        for ln in new.split("\n"):
            if width(ln) > LIMIT:
                stat["dòng còn vượt (mệnh đề không cắt được)"] += 1
                left_over.append((k, width(ln), ln))
        if new == old:
            stat["đã đúng"] += 1
            continue
        a, b = old.count("\n") + 1, new.count("\n") + 1
        stat["sẽ đổi"] += 1
        stat["  ít dòng hơn" if b < a else ("  nhiều dòng hơn" if b > a else "  cùng số dòng")] += 1
        todo.append((k, old, new))

    print()
    for key in sorted(stat):
        print("   %-42s %d" % (key, stat[key]))
    if left_over:
        print("\n%d dòng vẫn vượt 1210 vì là một mệnh đề liền — TMP tự ngắt:" % len(left_over))
        for k, w, ln in sorted(left_over, key=lambda x: -x[1])[:8]:
            print("   data[%-5d] %.0f px  %r" % (k, w, ln[:72]))

    if CHECK:
        # Từ 28/08/2026 chốt chặt hơn: KHÔNG dòng nào được quá lề. Trước đó tha những
        # dòng "không cắt được theo dấu câu" vì tính để TMP tự ngắt — nhưng bề rộng wrap
        # thực tế của TMP là [1269, 1342) canvas px, RỘNG HƠN lề 1205, nên tha là để chữ
        # chạy quá lề phải. Xem docstring đầu file.
        bad = [(r_i, width(l), l)
               for r_i, r in enumerate(data)
               for l in (r.get("content") or "").split("\n")
               if width(l) > LIMIT]
        print("\ndòng vượt lề %.0f px: %d" % (LIMIT, len(bad)))
        for k, w, ln in sorted(bad, key=lambda x: -x[1])[:8]:
            one = " " not in ln.strip()
            print("   FAIL data[%-5d] %.0f px  %s%r"
                  % (k, w, "(một từ, không ngắt được) " if one else "", ln[:64]))
        if bad:
            print("\nchạy `python tools\\fix_chat_wrap.py --apply`")
            raise SystemExit(1)
        print("PASS không dòng nào quá lề")
        return

    if not APPLY:
        print("\n%d ô sẽ đổi. CHẠY THỬ — thêm --apply để ghi" % len(todo))
        for k, old, new in todo[:6]:
            print("\n-> data[%d]" % k)
            print("   cũ : %r" % old.replace("\n", "\u23ce")[:96])
            print("   mới: %r" % new.replace("\n", "\u23ce")[:96])
        return
    if not todo:
        return

    # GỘP THEO NỘI DUNG trước khi thay. Nhiều ô trùng nhau từng chữ (cùng câu ở hai
    # nhóm chat) — thay-tất-cả cho ô đầu làm chuỗi cũ của ô sau biến mất, rồi lượt sau
    # báo "không thấy chuỗi cũ" và dừng giữa đường. Thật: `data[174]` trùng một ô trước.
    uniq = {}
    for k, old, new in todo:
        if old in uniq and uniq[old][1] != new:
            raise SystemExit("hai ô cùng chữ cũ mà ra chữ mới khác nhau: data[%d]" % k)
        uniq.setdefault(old, (k, new))
    print("   %d ô -> %d chuỗi khác nhau" % (len(todo), len(uniq)))

    out = raw
    for old, (k, new) in uniq.items():
        oj, nj = json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False)
        if out.count(oj) == 0:
            raise SystemExit("data[%d]: không thấy chuỗi cũ đã mã hoá" % k)
        out = out.replace(oj, nj)

    bak = BACKUP
    i = 2
    while os.path.exists(bak):
        bak = "%s-%d" % (BACKUP, i)
        i += 1
    shutil.copy2(BUNDLE, bak)
    print("\nbackup ->", bak)
    d.m_Script = ("\ufeff" if raw.startswith("\ufeff") else "") + out.lstrip("\ufeff")
    d.save()
    with open(BUNDLE, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi", BUNDLE, os.path.getsize(BUNDLE))

    _, _, back = load_asset(BUNDLE)
    db = json.loads(back.lstrip("\ufeff"))["data"]
    assert len(db) == len(data), "số mục đổi"
    for k, old, new in todo:
        assert db[k]["content"] == new, "đọc lại data[%d] sai: %r" % (k, db[k]["content"])
    nl = sum((r.get("content") or "").count("\n") for r in db)
    print("đọc lại: %d ô khớp, tổng ngắt dòng %d" % (len(todo), nl))


main()
