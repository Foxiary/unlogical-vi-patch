# -*- coding: utf-8 -*-
"""Thu ô chữ SHORT STORY để không dòng nào lấn qua lề của watermark UL.

`level10` pid 719 `RenderCanvas_Final/Message(SS)/SSText` — rect **1700×944,28**,
`m_AnchoredPosition (-787, 437)`, `m_Pivot (0, 1)`, anchor điểm giữa. Trên canvas 1920×1080
hộp nằm ở **x 173..1873**, tức lề trái 173 px mà lề phải chỉ **47 px** — lệch hẳn.

Watermark tam giác UL ở góc dưới-phải, đo trên ảnh chụp Ryujinx (pixel chính xác,
`_2026-08-18_18-00-52.png`): **x 1725..1842, y 930..1050** → lề phải của nó **78 px**. Hộp
chữ do đó rộng hơn lề cho phép **31 px**, và TMP wrap đúng ở rect nên dòng nào đầy sẽ dừng
ở 1699,9 px = mép 1873, tức lấn qua tam giác 31 px.

Đo trên build: **348 / 2 872 dòng (12,1%)** của 15 script short story lấn qua, và tất cả đều
dồn sát 1699,x — đúng dấu hiệu "rect là thứ giới hạn, không phải câu chữ".

Giá phải trả khi thu rect (đo bằng `adv_layout` với charSpacing 3,6, cỡ 32):

| rect | tổng dòng | dòng lấn | thêm dòng | mép phải |
|---|---|---|---|---|
| 1700 (hiện tại) | 2 872 | 348 | — | 1873 |
| 1690 | 2 883 | 221 | +11 | 1863 |
| 1680 | 2 890 | 128 | +18 | 1853 |
| **1669** | **2 896** | **0** | **+24** | **1842** |
| 1650 | 2 905 | 0 | +33 | 1823 |
| 1574 (cân với lề trái) | 3 020 | 0 | +148 | 1747 |

**Đã chốt 18/08/2026: lề trái 120, mép phải giữ 1842 → rect 1722** (`--left=120`). Người dùng
chọn 120 làm mức trung dung sau khi xem `tools/ss_margin_preview_*.png`.

| lề trái | rect | dòng | qua 1842 | trang >16 slot | dòng đụng biên nghiêng |
|---|---|---|---|---|---|
| 173 (gốc) | 1700 | 2 872 | 348 | 2 | — |
| 173 | 1669 | 2 896 | 0 | 2 | 3 (tệ nhất +22) |
| **120** | **1722** | **2 850** | **0** | **1** | **3 (tệ nhất +44)** |
| 78 (cân) | 1764 | 2 809 | 0 | 0 | 1 (+7) |

Đánh đổi phải biết: rect rộng hơn thì dòng **dài hơn mới wrap**, nên chỗ đụng biên nghiêng
*nặng thêm* (+22 → +44) dù tổng số dòng và số trang quá slot đều giảm. Muốn sạch hẳn cả hai
thì phải xuống 78; muốn giữ bố cục gần bản gốc thì 173. 120 nằm giữa.

`m_Pivot.x = 0` nên thu `m_SizeDelta.x` **ghim mép trái, chỉ kéo mép phải vào** — không phải
bù vị trí, giống `fix_adv_box_width.py`. `level10` không có type tree nhúng nên **vá byte tại
chỗ**, kích thước file không đổi (`env.file.save()` lên level10 sẽ ghi rỗng phần lớn object —
xem CLAUDE.md).

**Phân trang do SCRIPT quyết, không phải do khung.** Trang ngắt ở lệnh `[nextpage]` trong
`scriptText_Line` — cột script gốc, không được sửa (`check_scripts.py` so chuỗi lệnh với bản
gốc). Nên bản dịch dài hơn thì chỉ có hai lối: rút chữ, hoặc chịu. Thêm `[nextpage]` là không
được.

Hình học tam giác, khớp bằng số trên ảnh Ryujinx (chỉ lấy các hàng sạch, y 935..980 và
1030..1049; các hàng khác lẫn vệt sáng của nền):

    mép phải  x = 1842            đỉnh y ≈ 932, đáy y ≈ 1050
    biên trái x = 2774 - y        (nghiêng 45°, khớp -1,007)

Hộp cao 944 px / bước dòng 56,7 = **16 slot dòng**, hộp y 103..1047. Slot 15..17 nằm ngang
hàng tam giác nên giới hạn ở đó chặt hơn rect:

| slot | y | biên trái tam giác | giới hạn bề rộng |
|---|---|---|---|
| <=14 | ..897 | (không đụng) | 1669 = rect |
| 15 | 897..954 | 1820 | **1647** |
| 16 | 954..1011 | 1763 | **1590** |
| 17 | 1011..1047 | 1727 | **1554** |

`--check` audit cả ba thứ trên toàn bộ **360 trang / 15 script** SS. Ở lề 120:

- **0** dòng vượt mép phải tam giác (bản gốc: 348)
- **1** trang dùng 17 slot: `sID 141` trang 8
- **3** dòng đụng biên nghiêng: `141` trang 8 slot 16, `16` trang 8 slot 15, `16` trang 16 slot 15

Bốn chỗ đó cần **rút chữ** — không ngắt dòng thêm được, vì thêm dòng là thêm slot mà `141`
trang 8 đã quá slot. Chúng nằm trong `KNOWN` để gate chỉ đỏ khi có chỗ MỚI. `--check` in số px
sống, **không** ghi cứng ở đây: câu chữ đổi theo từng vòng sheet.

> `139` trang 6 và `133` trang 24 có token `[主人公]`, bề rộng **phụ thuộc tên người chơi** —
> `adv_layout` chỉ ước bằng "Kanna" (5 ký tự). Tên dài hơn thì hai chỗ đó rộng thêm.

    python tools\fix_ss_box_width.py [--apply] [--revert]
    python tools\fix_ss_box_width.py --check     # audit dữ liệu, chỗ MỚI -> exit 1
"""
import io
import json
import os
import re
import shutil
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy          # noqa: E402
import adv_layout as A  # noqa: E402

LEVEL = os.path.join(ROOT, "romfs", "Data", "level10")
BACKUP = os.path.join(ROOT, "_backup", "level10.ssboxw")
APPLY = "--apply" in sys.argv
REVERT = "--revert" in sys.argv
CHECK = "--check" in sys.argv
# `--left=<px>`: đặt lề trái, mép phải giữ ở 1842 (lề 78 = lề của window_icon_ss).
# Đổi HAI float: anchoredPosition.x lẫn sizeDelta.x. `--symmetric` = `--left=78`.
def _arg_left():
    for a in sys.argv:
        if a.startswith("--left="):
            return float(a.split("=", 1)[1])
    return 78.0 if "--symmetric" in sys.argv else None


LEFT = _arg_left()
SYM = LEFT is not None

RECT_PID = 719          # Message(SS)/SSText
NAME = "Message(SS)/SSText"
if SYM:
    RIGHT = 1842.0
    NEW_X = LEFT - 960.0
    NEW_W = RIGHT - LEFT
    if REVERT:
        OLD_X, OLD_W = NEW_X, NEW_W
        NEW_X, NEW_W = -787.0, 1669.0
    else:
        OLD_X, OLD_W = -787.0, 1669.0
else:
    OLD_W, NEW_W = (1669.0, 1700.0) if REVERT else (1700.0, 1669.0)
    OLD_X = NEW_X = None


def tail(t):
    return struct.pack(
        "<ffffffffff",
        t["m_AnchorMin"]["x"], t["m_AnchorMin"]["y"],
        t["m_AnchorMax"]["x"], t["m_AnchorMax"]["y"],
        t["m_AnchoredPosition"]["x"], t["m_AnchoredPosition"]["y"],
        t["m_SizeDelta"]["x"], t["m_SizeDelta"]["y"],
        t["m_Pivot"]["x"], t["m_Pivot"]["y"])


# ---------------------------------------------------------------- audit dữ liệu
SCEN = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
STOCK = r"D:\Downloads\UNLOGICAL_v2\Data\StreamingAssets\scenario\scenario01"

FONT_SIZE = 32.0
SS_CHAR_SPACING = 3.6
LINE_SPACING_PCT = -22.7
BOX_TOP = 103.0                 # 1080 - (540 + 437)
BOX_H = 944.28
TRI_RIGHT = 1842.0
TRI_TOP, TRI_BOTTOM = 932.0, 1050.0

# Chỗ đã biết, cần RÚT CHỮ (thêm ngắt dòng là thêm slot). Gate chỉ đỏ khi có chỗ MỚI.
# Cập nhật 18/08/2026 sau khi đặt lề trái 120 (rect 1722): `133` trang 24 và hai chỗ
# `136`/`139` tự hết, đổi lại `16` trang 8 và 16 chớm vào (rect rộng hơn -> dòng dài hơn
# mới wrap). Con số +px KHÔNG ghi ở đây: câu chữ đổi theo từng vòng sheet, `--check` in
# giá trị sống. (Đã bị lừa một lần: ô `141/txt/0040` đổi câu giữa hai lần đo, +75 -> +22.)
KNOWN_OVER = {(141, 8)}                                       # trang dùng 17 slot
KNOWN_TOUCH = {(141, 8, 16), (16, 8, 15), (16, 16, 15)}       # dòng đụng biên nghiêng


def pitch():
    return FONT_SIZE * (A.UNITS_LINE_HEIGHT / A.POINT_SIZE + LINE_SPACING_PCT / 100.0)


def tri_left(y):
    """Biên trái tam giác ở độ cao y; +inf nếu độ cao đó không có tam giác."""
    if y < TRI_TOP or y > TRI_BOTTOM:
        return float("inf")
    return 2774.0 - y


def slot_limit(slot, rect_w, box_left):
    """Giới hạn bề rộng cho slot dòng thứ `slot` (1-based)."""
    y0 = BOX_TOP + (slot - 1) * pitch()
    xl = min(tri_left(y0), tri_left(y0 + pitch()))
    return min(rect_w, xl - box_left)


def _scen(path):
    for o in UnityPy.load(path).objects:
        if o.type.name == "TextAsset" and o.read().m_Name == "ScenarioData":
            r = o.read().m_Script
            raw = r if isinstance(r, str) else bytes(r).decode("utf-8")
            return json.loads(raw.lstrip("\ufeff"))
    raise SystemExit("không thấy ScenarioData trong " + path)


def audit(rect_w, box_left):
    A.CHAR_SPACING = SS_CHAR_SPACING
    live, jp = _scen(SCEN), _scen(STOCK)
    cap = int(BOX_H // pitch())
    print()
    print("audit: rect %.0f, hộp y %.0f..%.0f, bước dòng %.1f -> %d slot/trang"
          % (rect_w, BOX_TOP, BOX_TOP + BOX_H, pitch(), cap))
    right_over, over_pages, touches, pages = [], [], [], 0
    for ti, t in enumerate(live["target"]):
        L = jp["target"][ti]["scriptText_Line"]
        if not any(re.match(r"^\s*\[textmode=4\]", l) for l in L):
            continue
        pg = [k for k, l in enumerate(L) if re.match(r"^\s*\[nextpage\]", l.strip())]
        bounds = [0] + pg + [len(L)]
        for pi in range(len(bounds) - 1):
            lo, hi = bounds[pi], bounds[pi + 1]
            idxs = [j for j in range(len(t["text"])) if lo <= t["loadLine"][j] < hi]
            if not idxs:
                continue
            pages += 1
            slot = 1
            for j in idxs:
                for hard in t["text"][j].split("\n"):
                    seq = A.wrap(hard, FONT_SIZE, limit=rect_w) if hard.strip() else [""]
                    for ln in seq:
                        w = A.line_width(ln, FONT_SIZE) if ln else 0.0
                        if box_left + w > TRI_RIGHT:
                            right_over.append((t["scenarioID"], pi, slot, w))
                        lim = slot_limit(slot, rect_w, box_left)
                        if slot <= cap and w > lim:
                            touches.append((t["scenarioID"], pi, slot, w, lim, ln))
                        slot += 1
                slot += 1                      # dòng trắng giữa các đoạn
            used = slot - 2
            if used > cap:
                over_pages.append((t["scenarioID"], pi, used))
    print("  %d trang SS / 15 script" % pages)
    print("  vượt mép phải tam giác (x>%.0f) : %d" % (TRI_RIGHT, len(right_over)))
    print("  trang quá %d slot                : %d" % (cap, len(over_pages)))
    print("  dòng đụng biên nghiêng           : %d" % len(touches))

    fresh = []
    for sID, pi, n in over_pages:
        known = (sID, pi) in KNOWN_OVER
        if not known:
            fresh.append(("trang", sID, pi))
        print("   %s sID %-4s trang %-3d dùng %d slot"
              % ("TỒN " if known else "MỚI ", sID, pi, n))
    for sID, pi, slot, w, lim, ln in touches:
        known = (sID, pi, slot) in KNOWN_TOUCH
        if not known:
            fresh.append(("dòng", sID, pi))
        print("   %s sID %-4s trang %-3d slot %-3d %7.1f px (giới hạn %.0f, +%.0f) %r"
              % ("TỒN " if known else "MỚI ", sID, pi, slot, w, lim, w - lim, ln[:40]))
    for sID, pi, slot, w in right_over[:8]:
        fresh.append(("mép phải", sID, pi))
        print("   MỚI  sID %-4s trang %-3d slot %-3d %7.1f px vượt mép phải"
              % (sID, pi, slot, w))
    print()
    if fresh:
        print("%d chỗ MỚI — cần rút chữ" % len(fresh))
        raise SystemExit(1)
    print("PASS không có chỗ mới; %d chỗ tồn trong KNOWN cần rút chữ trên sheet"
          % (len(KNOWN_OVER) + len(KNOWN_TOUCH)))


def main():
    env = UnityPy.load(LEVEL)
    t = None
    for o in env.objects:
        if o.path_id == RECT_PID and o.type.name == "RectTransform":
            t = o.read_typetree()
            break
    if t is None:
        raise SystemExit("không thấy RectTransform pid %d trong level10" % RECT_PID)

    print("pid %-4d %-20s size=(%.2f,%.2f) pos=(%.0f,%.0f) pivot=(%.1f,%.1f)"
          % (RECT_PID, NAME, t["m_SizeDelta"]["x"], t["m_SizeDelta"]["y"],
             t["m_AnchoredPosition"]["x"], t["m_AnchoredPosition"]["y"],
             t["m_Pivot"]["x"], t["m_Pivot"]["y"]))
    left = 960.0 + t["m_AnchoredPosition"]["x"]
    print("   trên canvas 1920: x %.0f..%.0f  (lề trái %.0f, lề phải %.0f)"
          % (left, left + t["m_SizeDelta"]["x"], left, 1920 - left - t["m_SizeDelta"]["x"]))
    print("   tam giác UL: mép phải %.0f, biên trái x=2774-y, y %.0f..%.0f"
          % (TRI_RIGHT, TRI_TOP, TRI_BOTTOM))

    if CHECK:
        audit(t["m_SizeDelta"]["x"], left)
        return

    assert t["m_Pivot"]["x"] == 0.0, "pivot.x != 0, thu bề rộng sẽ làm dịch chữ"
    if abs(t["m_SizeDelta"]["x"] - NEW_W) < 1e-3:
        print("   đã là %.0f, không cần sửa" % NEW_W)
        return
    assert abs(t["m_SizeDelta"]["x"] - OLD_W) < 1e-3, \
        "bề rộng lạ: %.2f (chờ %.0f)" % (t["m_SizeDelta"]["x"], OLD_W)

    blob = bytearray(open(LEVEL, "rb").read())
    n0 = len(blob)
    pat = tail(t)
    hits = [i for i in range(len(blob) - len(pat) + 1) if blob[i:i + len(pat)] == pat]
    if len(hits) != 1:
        raise SystemExit("mỏ neo khớp %d lần (phải là 1)" % len(hits))
    off = hits[0] + 24              # bỏ qua anchorMin/Max + anchoredPosition
    cur, = struct.unpack_from("<f", blob, off)
    assert abs(cur - OLD_W) < 1e-3, "byte tại %d là %.2f" % (off, cur)
    struct.pack_into("<f", blob, off, NEW_W)
    new_left = left
    if SYM:
        offx = hits[0] + 16        # anchoredPosition.x
        curx, = struct.unpack_from("<f", blob, offx)
        assert abs(curx - OLD_X) < 1e-3, "anchoredPosition.x tại %d là %.2f" % (offx, curx)
        struct.pack_into("<f", blob, offx, NEW_X)
        new_left = 960.0 + NEW_X
        print("   @%d  anchoredPosition.x %.0f -> %.0f  -> mép trái %.0f, lề %.0f px"
              % (offx, curx, NEW_X, new_left, new_left))
    print("   @%d  sizeDelta.x %.0f -> %.0f   -> mép phải %.0f, lề %.0f px"
          % (off, cur, NEW_W, new_left + NEW_W, 1920 - new_left - NEW_W))
    assert len(blob) == n0, "kích thước file đổi"

    # chỉ được khác đúng 4 byte đó
    orig = bytearray(open(LEVEL, "rb").read())
    diff = [i for i in range(n0) if orig[i] != blob[i]]
    print("   khác bản cũ %d byte, dải %d..%d" % (len(diff), min(diff), max(diff)))
    lo_ok = min(off, hits[0] + 16) if SYM else off
    hi_ok = off + 4
    assert len(diff) <= 8 and min(diff) >= lo_ok and max(diff) < hi_ok, "đổi byte ngoài dự kiến"

    if not APPLY:
        print()
        print("CHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(LEVEL, BACKUP)
        print("backup ->", BACKUP)
    open(LEVEL, "wb").write(blob)
    print("đã ghi", LEVEL, os.path.getsize(LEVEL))

    for o in UnityPy.load(LEVEL).objects:
        if o.path_id == RECT_PID and o.type.name == "RectTransform":
            t2 = o.read_typetree()
            print("  đọc lại pid %d size=(%.2f,%.2f) pos=(%.0f,%.0f) pivot=(%.1f,%.1f)"
                  % (RECT_PID, t2["m_SizeDelta"]["x"], t2["m_SizeDelta"]["y"],
                     t2["m_AnchoredPosition"]["x"], t2["m_AnchoredPosition"]["y"],
                     t2["m_Pivot"]["x"], t2["m_Pivot"]["y"]))
            assert abs(t2["m_SizeDelta"]["x"] - NEW_W) < 1e-3
            assert abs(t2["m_SizeDelta"]["y"] - t["m_SizeDelta"]["y"]) < 1e-3
            if SYM:
                assert abs(t2["m_AnchoredPosition"]["x"] - NEW_X) < 1e-3
                assert t2["m_AnchoredPosition"]["y"] == t["m_AnchoredPosition"]["y"]
            else:
                assert t2["m_AnchoredPosition"] == t["m_AnchoredPosition"]
            print("  chiều cao, vị trí, pivot nguyên vẹn")


main()
