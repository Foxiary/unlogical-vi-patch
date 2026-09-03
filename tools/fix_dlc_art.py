# -*- coding: utf-8 -*-
"""Vẽ lại chữ Nhật nướng trong tranh của DLC 1 (title AOC `010068501FF9B001`) và phần vỏ
DLC nằm trong game gốc.

Ba nhóm tranh (xem tools/README.md "DLC là một title khác"):

  AOC  sprite/sprite_jp_aoc01   5 thumbnail `UL_dlc_c_win_02_0N_*` (680x480): dải phụ đề
                                dưới thanh CHAPTER ghi `朝のひと時` bằng font điểm ảnh trắng,
                                bên phải là tên Latin (giữ). Đổi thành TITLE.
                                `UL_dlc_a_headsup_01` (1920x1080): màn Caution, ba dòng
                                chữ xanh đậm (0,51,91) trên nền trắng, cao 29 px, canh giữa.
  GỐC  sprite/sprite02          5 cửa sổ CHAPTER `UL_dlc_cd_win_01_0N_*` (480x152): tên
                                nhân vật bằng font điểm ảnh tím (136,81,170) bên phải icon.
                                Đổi thành tên La-tinh như `DLCData_01` đã đổi.

Hai dải phím `UL_dlc_b_key` / `UL_dlc_cd_key` (texture02) không ở đây: chúng là "key prompt"
như mọi màn khác, nên khai trong `fix_key_prompts.py` (JOBS) để cùng một cách vẽ.

Cách làm, theo đúng bài học của `keyart`/`fix_key_prompts`: luôn dựng từ bản GỐC (AOC dump
`D:\\Downloads\\UNLOGICAL_DLC1\\romfs`, game gốc `D:\\Downloads\\UNLOGICAL_v2`), xoá đúng
pixel mực cũ (không tô khung, để giữ lưới nền), vẽ chữ mới bằng font trích từ `ui_jp`
(`fontcache.py`), rồi **dựng lại mesh thành quad** vì sprite gốc mesh tight sẽ xén nét mới.
Ghi ra: AOC -> bản làm việc `D:\\Downloads\\010068501ff9b001\\romfs\\sprite\\sprite_jp_aoc01`;
game gốc -> `romfs/Data/StreamingAssets/sprite/sprite02` trong clone (file ship MỚI).

    python tools\\fix_dlc_art.py               # chạy thử: xuất ảnh xem trước vào _preview\\dlc_art
    python tools\\fix_dlc_art.py --apply
    python tools\\fix_dlc_art.py --check       # bundle đã ghi vẽ đúng (render qua mesh == ô đã dán)
"""
import io
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from keyart import Container, render_check   # noqa: E402
from fontcache import ttf                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

# `--dlc N` (mặc định 1). DLC 2 (title 010068501FF9B002) cùng khung tranh, tiền tố sprite
# `UL_dlc_d_*`, phụ đề `デート`, Caution chỉ hai dòng (không có dòng ※). Phần vỏ trong game gốc
# (sprite02/texture02, tiền tố `cd`) dùng chung cho cả hai DLC nên chỉ vá ở lượt --dlc 1.
DLC = int(sys.argv[sys.argv.index("--dlc") + 1]) if "--dlc" in sys.argv else 1
LETTER = {1: "c", 2: "d"}[DLC]
STOCK_AOC = r"D:\Downloads\UNLOGICAL_DLC%d\romfs" % DLC
WORK_AOC = r"D:\Downloads\010068501ff9b00%d\romfs" % DLC
STOCK_BASE = r"D:\Downloads\UNLOGICAL_v2\Data\StreamingAssets"
PATCH_BASE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets")
PREVIEW = os.path.join(ROOT, "_preview", "dlc_art")
BACKUP = os.path.join(ROOT, "_backup")

# ---- chữ -------------------------------------------------------------------------------
TITLE = {1: "Khoảnh khắc ban mai",      # 朝のひと時 — tiêu đề chung của 5 truyện DLC 1
         2: "Hẹn hò"}[DLC]              # デート — DLC 2
CAUTION = {
    1: [
        "Nội dung này có tiết lộ diễn biến của phần chính.",           # 当コンテンツには、本編のネタバレが含まれています。
        "Khuyến nghị chơi sau khi đã hoàn thành phần chính.",           # 本編をクリアしてからのプレイを推奨いたします。
        "※Truyện của Miyabi là ngoại truyện sau 『END No.12 Hình hài của hạnh phúc』.",  # ※雅火は『END No.12 幸せのかたち』後のSSです。
    ],
    2: [
        "Nội dung này có tiết lộ diễn biến của phần chính.",
        "Khuyến nghị chơi sau khi đã hoàn thành phần chính.",
    ],
}[DLC]
# tên trong cửa sổ CHAPTER = charaName của DLCData_01 (apply_dlc_sheet.CHARA_NAME)
NAMES = {"01_miya": "Miyabi", "02_kai": "Munakata Kai", "03_ran": "Nagamori Ran",
         "04_soi": "Yasaka Soichi", "05_yuri": "Yuri"}

PIXEL = "FOT-DotGothic12Std-M"      # font điểm ảnh của game (ULPixel)
ROUND = "FOT-DNPShueiMGoStd-B"      # gothic tròn đậm — nét của màn Caution
TITLE_H = 17                        # chữ `朝のひと時` cao 17 px trên thumbnail (đo cả 5 ảnh)
NAME_SIZE = 30                      # kanji tên trong cửa sổ CHAPTER cao 28 px -> DotGothic cỡ 30


def lum(a):
    return a[..., :3].astype(int).sum(2)


def bbox(mask):
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def erase(img, mask, fill=None):
    """Xoá đúng pixel `mask`. `fill=None`: mỗi hàng lấy trung vị pixel không-mực của hàng đó
    (giữ nền chuyển màu); có `fill` thì tô thẳng."""
    a = np.array(img)
    if fill is not None:
        a[mask] = fill
    else:
        for y in np.nonzero(mask.any(axis=1))[0]:
            row, m = a[y], mask[y]
            if (~m).sum():
                a[y][m] = np.median(row[~m], axis=0).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


def grow(mask, r):
    """Nở mặt nạ r pixel về bốn phía — vơ luôn viền khử răng cưa nhạt của chữ cũ."""
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= np.roll(np.roll(mask, dy, 0), dx, 1)
    return out


def draw_text(img, text, font, color, x=None, cx=None, mid_y=None, top_y=None, right=None, crisp=False):
    """Vẽ `text`; canh ngang theo x (trái) / cx (giữa) / right (phải), dọc theo hộp mực.
    `crisp`: không khử răng cưa — cho font điểm ảnh, nét gốc là chấm vuông đặc."""
    d = ImageDraw.Draw(img)
    if crisp:
        d.fontmode = "1"
    l, t, r, b = d.textbbox((0, 0), text, font=font, anchor="ls")
    w, h = r - l, b - t
    if cx is not None:
        x0 = cx - w / 2 - l
    elif right is not None:
        x0 = right - w - l
    else:
        x0 = x - l
    if mid_y is not None:
        y0 = mid_y - (t + b) / 2
    else:
        y0 = top_y - t
    d.text((x0, y0), text, font=font, fill=color, anchor="ls")
    return (int(x0 + l), int(y0 + t), int(x0 + r), int(y0 + b))


def match_size(font_name, sample, target_h, lo=8, hi=72):
    """Cỡ font mà một chữ mẫu (kanji/kana đầy ô) vẽ ra cao đúng bằng chữ Nhật cũ.

    Không làm tròn về bội của 12: DotGothic12 là font outline, vẽ được mọi cỡ; chữ gốc
    trên thumbnail cao 17 px, tức cỡ ~18, chứ không phải 12 hay 24."""
    best = None
    for size in range(lo, hi + 1):
        f = ImageFont.truetype(ttf(font_name), size)
        l, t, r, b = ImageDraw.Draw(Image.new("L", (4, 4))).textbbox((0, 0), sample, font=f, anchor="ls")
        d = abs((b - t) - target_h)
        if best is None or d < best[0]:
            best = (d, size, f)
    return best[1], best[2]


def fit_size(font_name, text, max_w, start, floor=8, step=1):
    size = start
    while size > floor:
        f = ImageFont.truetype(ttf(font_name), size)
        l, t, r, b = ImageDraw.Draw(Image.new("L", (4, 4))).textbbox((0, 0), text, font=f, anchor="ls")
        if r - l <= max_w:
            return size, f
        size -= step
    return size, ImageFont.truetype(ttf(font_name), size)


# ---- từng loại tranh --------------------------------------------------------------------
def thumbnail(img, name, report):
    """Dải phụ đề: chữ trắng điểm ảnh trên nền (146,190,214), y ~66..104. Xoá `朝のひと時`
    (cụm mực sáng bên TRÁI, x < 340), vẽ TITLE cùng cỡ, cùng mép trái."""
    a = np.array(img)
    # dải màu: mỗi nhân vật một màu (Ran xanh xám (146,190,214), Kai vàng…), nhưng đều là
    # dải phẳng, tối hơn nền trắng của thanh CHAPTER phía trên và không tối như tranh dưới:
    # hàng nào trong y 40..140 có trung vị độ sáng (R+G+B) của cột 20..340 nằm 250..690 là
    # dải; chữ trắng trên dải sáng hơn 650.
    # Tranh phía dưới (mây, trời) cũng sáng ~666 nên không lọc bằng ngưỡng được: lấy CỤM
    # hàng liên tục đầu tiên dưới thanh trắng có độ sáng gần nhau (±20) — đó là dải phẳng.
    med = np.median(lum(a)[40:140, 20:340], axis=1)
    below = [i for i, v in enumerate(med) if v < 700]
    ref = float(np.median(med[below[0]:below[0] + 6]))     # bỏ hàng mép đang chuyển màu
    # Dải phẳng tuyệt đối (trung vị lệch 0), còn hàng đầu của tranh dưới dải hồng của Miyabi
    # (DLC 2) lệch có 8 và 14 — dung sai 20 gộp luôn tranh vào dải, siết còn 5. Không dùng độ
    # lệch chuẩn theo hàng: hàng có chữ trắng rộng (DLC 1, 5 chữ) lệch chuẩn cao hơn cả tranh.
    rows = [i for i in range(below[0], len(med)) if abs(med[i] - ref) <= 5]
    first = last = rows[0]
    while last + 1 in rows:
        last += 1
    y_bar0, y_bar1 = 40 + first, 40 + last + 1
    if y_bar1 - y_bar0 < 20:
        raise SystemExit("%s: dải phụ đề chỉ %d hàng" % (name, y_bar1 - y_bar0))
    band = np.zeros(a.shape[:2], bool)
    band[y_bar0:y_bar1, 100:340] = True
    # chữ trắng sáng hơn dải; ngưỡng phải TƯƠNG ĐỐI vì dải của Soichi (227,204,251) đã sáng 682
    ink = band & (lum(a) > ref + 40) & (a[..., 3] > 128)
    bb = bbox(ink)
    if bb is None:
        raise SystemExit("%s: không thấy chữ phụ đề" % name)
    color = tuple(int(v) for v in np.median(a[ink][:, :3], axis=0)) + (255,)
    x0, y0, x1, y1 = bb
    out = erase(img, grow(ink, 1) & band)
    # `朝のひと時` cao 17 px trên cả năm thumbnail; dải sáng của Soichi làm mặt nạ hụt một
    # hàng nên không dùng số đo từng ảnh — cỡ chung cho cả năm.
    size, font = match_size(PIXEL, "朝", TITLE_H)
    box = draw_text(out, TITLE, font, color, x=x0, mid_y=(y0 + y1) / 2, crisp=True)
    report.append("%-26s phụ đề JP x%d..%d y%d..%d (cao %d) -> %r cỡ %d, hộp mới x%d..%d" % (
        name, x0, x1, y0, y1, y1 - y0, TITLE, size, box[0], box[2]))
    if box[2] > 400:
        raise SystemExit("%s: tiêu đề mới rộng tới x=%d, đè lên tên bên phải" % (name, box[2]))
    return out


def caution(img, name, report):
    """Ba dòng chữ tối canh giữa x=960; xoá pixel tối trong ba dải rồi vẽ CAUTION."""
    a = np.array(img)
    dark = (lum(a) < 300) & (a[..., 3] > 128)
    rows = dark[:, 300:1650].sum(1)
    bands, start = [], None
    for y in range(a.shape[0]):
        if rows[y] > 3 and start is None:
            start = y
        if rows[y] <= 3 and start is not None:
            if 12 < y - start < 60:
                bands.append((start, y))
            start = None
    if len(bands) != len(CAUTION):
        raise SystemExit("%s: chờ %d dải chữ, thấy %s" % (name, len(CAUTION), bands))
    color = tuple(int(v) for v in np.median(a[dark & (np.arange(a.shape[0])[:, None] >= bands[0][0])][:, :3], axis=0)) + (255,)
    mask = np.zeros(a.shape[:2], bool)
    for y0, y1 in bands:
        mask[y0 - 6:y1 + 6, 300:1650] = True
    # Nở 2 px để lấy viền khử răng cưa, và xoá luôn pixel XÁM TRUNG TÍNH (chấm mờ ở hai
    # đầu dòng, không có lõi tối để nở tới); đường kẻ trang trí dọc x~960 màu tím nhạt có
    # sắc (R, B cao hơn G) nên không bị dính.
    # `< 720` chứ không phải 740: hoạ tiết hồng nhạt (255,240,242) ở x~1040..1100 nằm dưới
    # dòng 1 có lum 737 và độ sắc thấp, 740 sẽ xoá mất nó.
    r, g, b = (a[..., i].astype(int) for i in range(3))
    gray = (lum(a) < 720) & (abs(r - g) < 30) & (abs(b - g) < 30)
    out = erase(img, mask & (grow(dark, 2) | gray), fill=(255, 255, 255, 255))
    h = int(round(np.mean([y1 - y0 for y0, y1 in bands])))
    size = h + 3                                  # kana cao ~h => em ~h+3 với Shuei MGo
    for (y0, y1), text in zip(bands, CAUTION):
        s, font = fit_size(ROUND, text, 1500, size)
        box = draw_text(out, text, font, color, cx=960, mid_y=(y0 + y1) / 2)
        report.append("%-26s dòng y%d..%d -> cỡ %d, rộng %d: %r" % (name, y0, y1, s, box[2] - box[0], text))
    return out


def chapter_window(img, name, report):
    """Tên Nhật tím bên phải icon (icon x<180 trong ô). Xoá pixel tím ở x>=180, vẽ tên La-tinh
    cùng font điểm ảnh, cùng mép trái, canh giữa theo chiều dọc của chữ cũ."""
    key = next(k for k in NAMES if name.endswith(k))
    a = np.array(img)
    r, g, b, al = (a[..., i].astype(int) for i in range(4))
    purple = (al > 128) & (b > 120) & (r < 170) & (g < 110)
    # Icon và tên cùng màu tím. Icon của Miyabi thò sang phải quá x=178 nên không cắt bằng
    # một mốc x cố định được: dò cột có mực trong y 55..130 từ x=120, cụm đầu là icon, tên
    # bắt đầu sau khoảng trống >= 8 cột đầu tiên.
    cols = purple[55:130, :].any(axis=0)
    x = 120
    while x < a.shape[1] and not cols[x]:
        x += 1
    while x < a.shape[1] and cols[x]:
        x += 1                                   # hết cụm icon
    gap = 0
    while x < a.shape[1] and gap < 8:
        gap = gap + 1 if not cols[x] else 0
        x += 1
    while x < a.shape[1] and not cols[x]:
        x += 1
    text_x0 = x
    ink = purple.copy()
    ink[:, :text_x0 - 1] = False
    ink[:55, :] = False
    ink[130:, :] = False
    bb = bbox(ink)
    if bb is None:
        raise SystemExit("%s: không thấy tên tím" % name)
    color = tuple(int(v) for v in np.median(a[ink][:, :3], axis=0)) + (255,)
    x0, y0, x1, y1 = bb
    # Nền dưới tên là trắng phẳng (lưới sàn bắt đầu dưới y~118, lưới tường từ x~395), nên
    # xoá MỌI pixel không trắng trong khung tên nới 2 px — mặt nạ theo màu bỏ sót viền pha.
    wipe = np.zeros(a.shape[:2], bool)
    wipe[max(0, y0 - 2):y1 + 2, max(0, x0 - 2):x1 + 2] = True
    wipe &= lum(a) < 740
    out = erase(img, wipe, fill=(255, 255, 255, 255))
    # Kanji tên gốc cao 28 px ở cả 4 cửa sổ có kanji (katakana ユーリ thấp hơn); cùng một
    # cỡ cho cả năm để năm tên đứng cạnh nhau không so le.
    font = ImageFont.truetype(ttf(PIXEL), NAME_SIZE)
    size = NAME_SIZE
    box = draw_text(out, NAMES[key], font, color, x=x0, mid_y=(y0 + y1) / 2, crisp=True)
    report.append("%-26s tên JP x%d..%d y%d..%d (cao %d) -> %r cỡ %d, hộp mới x%d..%d" % (
        name, x0, x1, y0, y1, y1 - y0, NAMES[key], size, box[0], box[2]))
    if box[2] > img.width - 30:
        raise SystemExit("%s: tên mới rộng tới x=%d, vượt ô" % (name, box[2]))
    return out


JOBS = [
    # (bundle gốc, bundle đích, [(tên sprite hoặc tiền tố, hàm)])
    (os.path.join(STOCK_AOC, "sprite", "sprite_jp_aoc0%d" % DLC),
     os.path.join(WORK_AOC, "sprite", "sprite_jp_aoc0%d" % DLC),
     [("UL_dlc_%s_win_02_" % LETTER, thumbnail), ("UL_dlc_a_headsup_0%d" % DLC, caution)]),
]
if DLC == 1:
    JOBS.append((os.path.join(STOCK_BASE, "sprite", "sprite02"), os.path.join(PATCH_BASE, "sprite", "sprite02"),
                 [("UL_dlc_cd_win_01_", chapter_window)]))


def targets(c, prefix):
    return [n for n in c.sprite_names() if n.startswith(prefix)]


def main():
    os.makedirs(PREVIEW, exist_ok=True)
    if CHECK:
        bad = 0
        for src, dst, jobs in JOBS:
            if not os.path.exists(dst):
                print("THIẾU", dst); bad += 1; continue
            c = Container(dst)
            for prefix, _fn in jobs:
                for n in targets(c, prefix):
                    s = c.sprite(n)
                    if s.vertex_count() != 4:
                        print("FAIL %s: mesh %d đỉnh (chưa dựng quad)" % (n, s.vertex_count())); bad += 1
                    rendered = render_check(dst, n).convert("RGBA")
                    if np.array(rendered).shape != np.array(s.crop()).shape or not np.array_equal(np.array(rendered), np.array(s.crop())):
                        print("FAIL %s: ảnh render qua mesh khác ô atlas" % n); bad += 1
            print("%s: %d sprite kiểm" % (os.path.basename(dst), sum(len(targets(c, p)) for p, _ in jobs)))
        if bad:
            raise SystemExit("%d lỗi" % bad)
        print("PASS")
        return

    for src, dst, jobs in JOBS:
        work = os.path.join(PREVIEW, "_work_" + os.path.basename(src))
        shutil.copy(src, work)
        c = Container(work)
        report = []
        sheet_parts = []
        for prefix, fn in jobs:
            for n in targets(c, prefix):
                s = c.sprite(n)
                before = s.crop()
                after = fn(before.copy(), n, report)
                s.paste(after)
                s.full_rect_mesh()
                sheet_parts.append((n, before, after))
                after.save(os.path.join(PREVIEW, n + ".png"))     # ảnh sau, đủ cỡ, để soi kỹ
        for line in report:
            print("  " + line)
        # ảnh xem trước: trước/sau từng sprite, thu về bề ngang 900
        rows = []
        for n, b, a in sheet_parts:
            pair = Image.new("RGBA", (b.width * 2 + 10, b.height), (60, 60, 60, 255))
            pair.alpha_composite(b, (0, 0)); pair.alpha_composite(a, (b.width + 10, 0))
            if pair.width > 1800:
                pair = pair.resize((1800, int(pair.height * 1800 / pair.width)))
            rows.append((n, pair))
        H = sum(p.height + 22 for _, p in rows); W = max(p.width for _, p in rows)
        sheet = Image.new("RGB", (W, H), (30, 30, 30)); d = ImageDraw.Draw(sheet); y = 0
        for n, p in rows:
            d.text((4, y + 4), n, fill=(255, 255, 0)); sheet.paste(p.convert("RGB"), (0, y + 20)); y += p.height + 22
        pv = os.path.join(PREVIEW, os.path.basename(src) + ".png")
        sheet.save(pv)
        print("%s: %d sprite, xem trước -> %s" % (os.path.basename(src), len(sheet_parts), pv))
        if not APPLY:
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            os.makedirs(BACKUP, exist_ok=True)
            shutil.copy2(dst, os.path.join(BACKUP, os.path.basename(dst) + ".predlcart"))
        n = c.save(work + ".out", packer="lz4")
        shutil.move(work + ".out", dst)
        print("  đã ghi %s (%d B)" % (dst, n))
    if not APPLY:
        print("\nCHẠY THỬ — xem ảnh trong %s rồi thêm --apply" % PREVIEW)


if __name__ == "__main__":
    main()
