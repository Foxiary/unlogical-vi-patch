# -*- coding: utf-8 -*-
"""Ngắt dòng cho asset chat Genebark — **ngắt cứng CHỈ ở dấu câu**, phần thừa để engine.

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

## Lề phải bằng lề trái — và giới hạn của việc nhờ TMP

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

Bản 28/08 vì thế thêm tầng ba: ngắt ở **khoảng trắng** cho những mệnh đề không có dấu
câu nào. **Đã gỡ 30/08** theo yêu cầu người dùng — *"ngắt cứng chỉ còn ở dấu câu, phần
thừa để engine"*. Ngắt ở khoảng trắng là ngắt **giữa mệnh đề**, tức đúng cái lỗi mà cả
đợt này sinh ra để sửa; giữ nó là tự mâu thuẫn.

Đánh đổi đã biết và đã chấp nhận: **79 dòng** (64 ở asset app, 15 ở ScenarioData) không
còn dấu câu nào để cắt, nên TMP ngắt chúng ở bề rộng của nó và **chữ chạy quá lề phải
12–136 px**. Muốn engine ngắt ĐÚNG lề thì phải **thu `Message_TMP` lại**, không phải ngắt
cứng thêm — nhưng đo được bề rộng wrap thực tế là [1269, 1342) trong khi prefab ghi 1210,
tức con số prefab đang bị `ChatItemUI` (script gắn trên hàng chat) ghi đè. Chưa thử thu.

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
- `--check` chỉ FAIL khi dòng quá lề mà **còn cắt được theo dấu câu**. Mệnh đề liền thì
  liệt kê ra kèm mức quá lề, không tính là lỗi — đó là chủ ý.

**Tự dò lại từ câu chữ hiện tại**, nên chạy lại được sau mỗi vòng merge (sheet làm phẳng
sạch `\\n`). Không ghim theo chỉ số ô.

    python tools\\fix_chat_wrap.py            # chạy thử
    python tools\\fix_chat_wrap.py --apply
    python tools\\fix_chat_wrap.py --check    # gate, còn dòng CẮT ĐƯỢC mà quá lề -> exit 1
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
SCENARIO = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
SC_BACKUP = os.path.join(ROOT, "_backup", "scenario01.chatwrap")

APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

POINT_SIZE = 58.0
FONT_SIZE = 32.0
CHAR_SPACING = 5.0
# Lề, chốt 30/08/2026. Yêu cầu: *"vạch phải giống bản Nhật gốc, không chấp nhận bất kì
# thay đổi vị trí và độ dài vạch, chỉ tác động phần text box thôi"*.
#
# Nên KHÔNG thu `sizeDelta` (vạch `UnderLine` là con của rect, thu là vạch dịch — đo được
# 318..1600 ở ô 1210 so với 268..1445 ở ô 900). Thay vào đó thu `m_margin.PHẢI = 45` trong
# `ui_jp`: nó thu vùng vẽ chữ bên trong rect, rect không đổi nên vạch đứng yên tuyệt đối.
# Xem tools\set_chat_box_width.py.
#
#   vùng chữ = 1210 − 45 = 1165 canvas
#   model đo cao hơn TMP ~5% (kẹp A/B: W_model/box ∈ [1,049; 1,109))
#   => LIMIT = 1165 × 1,049 ≈ 1222, làm tròn xuống cho chắc
LIMIT = 1220.0

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
    # KHÔNG có tầng ba. Mệnh đề không còn dấu câu nào để cắt thì để nguyên — engine lo.
    # Chốt 30/08/2026: ngắt cứng chỉ được đặt ở dấu câu; ngắt ở khoảng trắng là ngắt giữa
    # mệnh đề, tức đúng cái lỗi mà cả đợt này sinh ra để sửa. Đánh đổi đã biết: 79 dòng
    # như vậy sẽ do TMP ngắt ở bề rộng của nó ([1269, 1342) canvas px), tức quá lề 1205
    # từ 12 đến 136 px. Muốn engine ngắt ĐÚNG lề thì phải thu `Message_TMP` lại, không
    # phải ngắt cứng thêm — xem docstring đầu file.
    return [back(x) for x in out]


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


def do_scenario():
    """Tin nh\u1eafn chat n\u1eb1m trong `ScenarioData` \u2014 ch\u1ed7 m\u00e0n CHAT th\u1eadt s\u1ef1 \u0111\u1ecdc.

    **\u0110\u00e2y m\u1edbi l\u00e0 asset m\u00e0n h\u00ecnh v\u1ebd.** `GenebarkChatMainData` kh\u00f4ng ph\u1ea3i: ba d\u00f2ng \u0111\u1ea7u c\u1ee7a
    \u1ea3nh `_2026-08-30_01-36-35.png` (`May qu\u00e1. T\u1ea7m m\u1ea5y gi\u1edd th\u00ec b\u00e0n \u0111\u01b0\u1ee3c nh\u1ec9?`, `H\u1eedm. \u0110\u1ec3
    t\u00f4i h\u1ecdc xong\u2026`, `Ok. C\u1ed1 l\u00ean nha`) **kh\u00f4ng c\u00f3 trong** asset \u0111\u00f3, m\u00e0 n\u1eb1m li\u00ean ti\u1ebfp \u1edf
    `ScenarioData` `68/txt/0123\u20130129`, \u0111\u00fang th\u1ee9 t\u1ef1 tr\u00ean m\u00e0n h\u00ecnh.

    Nh\u1eadn di\u1ec7n \u00f4 chat b\u1eb1ng nameplate d\u1ea1ng t\u00e0i kho\u1ea3n (`talkName` c\u00f3 `@`) \u2014 289 \u00f4.

    Ch\u00fang v\u1ebd \u1edf **widget chat**, kh\u00f4ng ph\u1ea3i \u00f4 tho\u1ea1i ADV. \u0110o 6 d\u00f2ng bi\u1ebft tr\u01b0\u1edbc ch\u1eef tr\u00ean
    \u1ea3nh: model chat (ShueiMGo-B, c\u1ee1 32, spacing 5) kh\u1edbp t\u1ec9 l\u1ec7 **1,002**; model ADV
    (NewRodin, c\u1ee1 42) l\u1ec7ch **1,595\u00d7**. N\u00ean `fix_adv_wrap.py` \u0111ang t\u00ednh 289 \u00f4 n\u00e0y b\u1eb1ng
    sai font v\u00e0 sai c\u1ee1 \u2014 xem ghi ch\u00fa trong tools/README.md.
    """
    env, d, raw = load_asset(SCENARIO, "ScenarioData")
    data = json.loads(raw.lstrip("\ufeff"))

    todo, stat = [], collections.Counter()
    for ti, e in enumerate(data["target"]):
        tn = e.get("talkName") or []
        tx = e.get("text") or []
        for i, nm in enumerate(tn):
            if not nm or "@" not in nm or i >= len(tx):
                continue
            old = tx[i] or ""
            if not old.strip():
                continue
            stat["\u00f4 chat"] += 1
            new = "\n".join(split_punct(flat(old)))
            assert flat(new) == flat(old), "%s/txt/%d: ch\u1eef b\u1ecb \u0111\u1ed5i" % (e["scenarioID"], i)
            if new == old:
                stat["  \u0111\u00e3 \u0111\u00fang"] += 1
                continue
            todo.append((ti, e["scenarioID"], i, old, new))
            stat["  s\u1ebd \u0111\u1ed5i"] += 1
    for key in sorted(stat):
        print("   %-34s %d" % (key, stat[key]))

    if CHECK:
        bad = [(e["scenarioID"], i, width(l), l)
               for e in data["target"]
               for i, nm in enumerate(e.get("talkName") or [])
               if nm and "@" in nm and i < len(e.get("text") or [])
               for l in ((e["text"][i] or "").split("\n"))
               if l and width(l) > LIMIT]
        still = [x for x in bad if not unbreakable(x[3])]
        left = [x for x in bad if unbreakable(x[3])]
        print("   d\u00f2ng chat ScenarioData qu\u00e1 l\u1ec1 %.0f px: %d \u2014 %d c\u00f2n c\u1eaft \u0111\u01b0\u1ee3c"
              % (LIMIT, len(bad), len(still)))
        if left:
            ws = [w for _, _, w, _ in left]
            print("      %d d\u00f2ng \u0111\u1ec3 engine ng\u1eaft, qu\u00e1 l\u1ec1 %.0f..%.0f px"
                  % (len(left), min(ws) - LIMIT, max(ws) - LIMIT))
        for sid, i, w, ln in sorted(still, key=lambda x: -x[2])[:6]:
            print("      FAIL %s/txt/%04d  %.0f px  %r" % (sid, i, w, ln[:60]))
        return len(still)

    if not APPLY:
        for ti, sid, i, old, new in todo[:4]:
            print("\n-> %s/txt/%04d" % (sid, i))
            print("   c\u0169 : %r" % old.replace("\n", "\u23ce")[:96])
            print("   m\u1edbi: %r" % new.replace("\n", "\u23ce")[:96])
        return len(todo)
    if not todo:
        return 0

    out = raw
    enc_a = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))  # noqa: E731
    enc_s = lambda x: json.dumps(x, ensure_ascii=False)                        # noqa: E731
    # V\u00e1 theo C\u1ea2 M\u1ea2NG `text[]` nh\u01b0 `fix_chat_use_genebark.py`: c\u00f3 tin nh\u1eafn tr\u00f9ng nhau
    # t\u1eebng ch\u1eef, thay theo chu\u1ed7i s\u1ebd \u0111\u1ee5ng c\u1ea3 hai.
    for ti in sorted({t[0] for t in todo}):
        arr_old = list(data["target"][ti]["text"])
        arr_new = list(arr_old)
        for t2, sid, i, old, new in [t for t in todo if t[0] == ti]:
            assert arr_new[i] == old
            arr_new[i] = new
        oj, nj = enc_a(arr_old), enc_a(arr_new)
        if out.count(oj) != 1:
            raise SystemExit("m\u1ea3ng text[] target[%d] kh\u1edbp %d l\u1ea7n" % (ti, out.count(oj)))
        out = out.replace(oj, nj)
    mirrored = failed = 0
    for ti in sorted({t[0] for t in todo}):
        script = cur = data["target"][ti]["scriptText"]
        for t2, sid, i, old, new in [t for t in todo if t[0] == ti]:
            lines, ol = cur.split("\n"), old.split("\n")
            hits = [k for k in range(len(lines) - len(ol) + 1) if lines[k:k + len(ol)] == ol]
            if len(hits) == 1:
                lines[hits[0]:hits[0] + len(ol)] = new.split("\n")
                cur = "\n".join(lines)
                mirrored += 1
            else:
                failed += 1
        if cur != script:
            oj, nj = enc_s(script), enc_s(cur)
            if out.count(oj) != 1:
                raise SystemExit("scriptText target[%d] kh\u1edbp %d l\u1ea7n" % (ti, out.count(oj)))
            out = out.replace(oj, nj)
    print("   scriptText: mirror %d, b\u1ecf %d" % (mirrored, failed))

    bak = SC_BACKUP
    n = 2
    while os.path.exists(bak):
        bak = "%s-%d" % (SC_BACKUP, n)
        n += 1
    shutil.copy2(SCENARIO, bak)
    print("   backup ->", bak)
    d.m_Script = ("\ufeff" if raw.startswith("\ufeff") else "") + out.lstrip("\ufeff")
    d.save()
    with open(SCENARIO, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("   \u0111\u00e3 ghi", SCENARIO, os.path.getsize(SCENARIO))

    _, _, back = load_asset(SCENARIO, "ScenarioData")
    db = json.loads(back.lstrip("\ufeff"))
    for ti, sid, i, old, new in todo:
        assert db["target"][ti]["text"][i] == new, "\u0111\u1ecdc l\u1ea1i %s/txt/%d sai" % (sid, i)
    for a, b in zip(data["target"], db["target"]):
        for fld in ("text", "talkName", "selText", "scriptText_Line", "loadLine"):
            x, y = a.get(fld), b.get(fld)
            if isinstance(x, list) and len(x) != len(y):
                raise SystemExit("sID %s %s: \u0111\u1ed9 d\u00e0i m\u1ea3ng \u0111\u1ed5i" % (a["scenarioID"], fld))
    print("   \u0111\u1ecdc l\u1ea1i: %d \u00f4 kh\u1edbp, \u0111\u1ed9 d\u00e0i m\u1ecdi m\u1ea3ng kh\u00f4ng \u0111\u1ed5i" % len(todo))
    return len(todo)


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
        print("\n%d dòng để engine ngắt (mệnh đề liền, không còn dấu câu):" % len(left_over))
        for k, w, ln in sorted(left_over, key=lambda x: -x[1])[:8]:
            print("   data[%-5d] %.0f px  %r" % (k, w, ln[:72]))

    if CHECK:
        # Từ 28/08/2026 chốt chặt hơn: KHÔNG dòng nào được quá lề. Trước đó tha những
        # dòng "không cắt được theo dấu câu" vì tính để TMP tự ngắt — nhưng bề rộng wrap
        # thực tế của TMP là [1269, 1342) canvas px, RỘNG HƠN lề 1205, nên tha là để chữ
        # chạy quá lề phải. Xem docstring đầu file.
        rows = [(r_i, width(l), l)
                for r_i, r in enumerate(data)
                for l in (r.get("content") or "").split("\n")
                if l and width(l) > LIMIT]
        bad = [x for x in rows if not unbreakable(x[2])]
        left = [x for x in rows if unbreakable(x[2])]
        print("\ndòng quá lề %.0f px: %d — trong đó %d còn cắt được theo dấu câu"
              % (LIMIT, len(rows), len(bad)))
        if left:
            ws = [w for _, w, _ in left]
            print("   %d dòng để engine ngắt (mệnh đề liền), quá lề %.0f..%.0f px"
                  % (len(left), min(ws) - LIMIT, max(ws) - LIMIT))
        for k, w, ln in sorted(bad, key=lambda x: -x[1])[:8]:
            print("   FAIL data[%-5d] %.0f px  %r" % (k, w, ln[:64]))
        if bad:
            print("\nchạy `python tools\\fix_chat_wrap.py --apply`")
            raise SystemExit(1)
        print("PASS không dòng nào còn cắt được mà vẫn quá lề")
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


def run():
    # Hai asset, cùng một luật và cùng số đo widget:
    #   GenebarkChatMainData  -> app CHAT mở từ menu Genebark
    #   ScenarioData.text[]   -> cảnh ADV vẽ giao diện chat trong lúc kể chuyện
    # Chúng KHÔNG phải bản sao của nhau; ảnh 30/08 cho thấy app đã ngắt đúng trong khi
    # cảnh ADV vẫn phẳng, vì bản đầu của tool chỉ ghi asset thứ nhất.
    print("=== 1/2  GenebarkChatMainData (app CHAT) ===")
    rc = main()
    print("\n=== 2/2  ScenarioData (cảnh ADV vẽ giao diện chat) ===")
    n = do_scenario()
    if CHECK:
        if n:
            print("\nchạy `python tools\\fix_chat_wrap.py --apply`")
            raise SystemExit(1)
        print("PASS ScenarioData: không dòng chat nào quá lề")
    elif not APPLY:
        print("\n%d ô ScenarioData sẽ đổi. CHẠY THỬ — thêm --apply để ghi" % n)
    return rc


run()
