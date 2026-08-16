"""Dịch nốt các dải phím còn tiếng Nhật ở chân màn hình.

Cách làm: giữ nguyên **icon nút bấm** (Ⓐ Ⓑ Ⓨ Ⓧ) cắt thẳng từ tranh gốc, chỉ xoá
phần chữ Nhật rồi vẽ lại bằng font UI của chính game — `FOT-NewRodin ProN DB`
**cỡ 28**, đúng font/cỡ `tools\fix_music_key.py` đã dùng cho `UL_music_key`
(khớp IoU 0.993). Cỡ 28 cho nét chữ cao ~24 px, gần bằng đĩa nút 29 px, đúng tỉ
lệ tranh tiếng Anh chính chủ của nhà phát triển (`UL_term_key_02`: chữ cao 27,
đĩa 27). Ô nào hẹp quá thì tự rút cỡ xuống cho vừa, chỗ dư đẩy hết vào khoảng
cách giữa các cụm nên cụm `Ⓑ Back` luôn nằm sát mép phải như bản Nhật.

Ảnh **luôn dựng từ bản gốc 1.0.2**, không đọc lại bản vá — nhờ vậy chạy bao
nhiêu lần cũng ra cùng kết quả và đổi tham số là vẽ lại được. Sau đó dựng lại
mesh thành quad full-rect, nếu không nét mới sẽ bị mesh tight cũ xén thủng —
xem [[unitypy-switch-bundle-repack]].

    python tools\fix_key_prompts.py            # chạy thử, xuất ảnh xem trước
    python tools\fix_key_prompts.py --apply    # backup rồi vá thật
    python tools\fix_key_prompts.py --only ui_jp --apply
"""

import io
import os
import shutil
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from keyart import Container

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PATCH = os.path.join(ROOT, "romfs", "Data")
STOCK = "D:/Downloads/UNLOGICAL_v2/Data"
BACKUP = os.path.join(ROOT, "_backup")
PREVIEW = os.path.join(ROOT, "_keyprompt")

_FONTDIR = ("C:/Users/ADMIN/AppData/Local/Temp/claude/D--Downloads-010068501ff9a000/"
            "9d4f7fb5-9b6c-4487-a5b3-fbf1cbd6951d/scratchpad/fonts/")
FONT = _FONTDIR + "font_BASE.ttf"        # FOT-NewRodin ProN DB — chữ UI gothic
FONT_PIXEL = _FONTDIR + "ULPixel.ttf"    # mặt chữ dot-matrix của màn nhập tên

SIZE_MAX = 28          # cỡ chuẩn của bản vá, ứng với đĩa nút 29 px
SIZE_MIN = 14
GAP_ICON_TEXT = 6      # icon -> chữ; tranh chính chủ dùng 5-6
GAP_GROUP_MIN = 12     # giữa hai cụm; tranh chính chủ (UL_term_key_02) dùng 12
GAP_GROUP_MAX = 34

# Từ vựng bám theo tiếng Anh chính chủ của game (UL_map_key, UL_term_key_02):
#   決定 -> Select, 戻る -> Back, 再生 -> Play, シーン再生(開始) -> Play scene
#
# Mỗi sprite: danh sách (icon_x0, icon_x1, chữ mới). Chữ thay cho toàn bộ phần
# nằm giữa icon này và icon kế tiếp.
JOBS = [
    ("sharedassets5.assets", "assets", [                      # LIBRARY
        ("UL_library_key",  [(2, 31, "Select"), (121, 150, "Back"),
                             (239, 269, "CG comment"), (480, 510, "Play scene")]),
        ("UL_library_key2", [(2, 31, "Select"), (121, 150, "Back"),
                             (239, 269, "CG comment")]),
        ("UL_library_key3", [(2, 31, "Select"), (121, 150, "Back"),
                             (239, 269, "Play scene")]),
        ("UL_library_key4", [(2, 31, "Back")]),
        ("UL_library_key5", [(2, 31, "Select"), (121, 150, "Back")]),
    ]),
    ("sharedassets6.assets", "assets", [                      # SECTION SELECT
        ("UL_section_abc_com_key", [(2, 32, "Select"), (124, 153, "Back")]),
    ]),
    ("sharedassets7.assets", "assets", [                      # OPTION
        ("UL_option_com_key", [(2, 31, "Back"), (120, 149, "Reset")]),
    ]),
    ("sharedassets9.assets", "assets", [                      # ARCHIVE
        ("UL_archive_key", [(2, 31, "Select"), (124, 153, "Back")]),
    ]),
    ("sharedassets11.assets", "assets", [                     # MANUAL
        ("UL_manual_key", [(2, 31, "Back")]),
    ]),
    ("sharedassets19.assets", "assets", [                     # SAVE / LOAD
        ("UL_salo_key", [(2, 31, "Lock"), (141, 170, "Select"), (263, 292, "Back")]),
    ]),
    ("StreamingAssets/scene/scene_jp", "bundle", [
        ("UL_movie_a_key", [(2, 31, "Play"), (123, 153, "Back")]),   # MOVIE
        # Màn nhập tên. Dòng dưới không có nút (icon = None) và phải giữ mặt chữ
        # dot-matrix `ULPixel` cỡ 24 cho khớp ô "LAST NAME / Suzuno" ngay trên nó
        # — đo lại từ bản vá cũ, khớp IoU 0.978.
        ("UL_name_key", [
            [(2, 31, "Enter Text"), (184, 213, "Back"), (303, 332, "Reset")],
            [(None, None, "Please enter your name", FONT_PIXEL, 24)],
        ]),
    ]),
    # SHORT STORY — `level17` lấy dải phím từ **sharedassets17**, không phải ui_jp:
    # Image `Kay` (pid 225) trỏ m_Sprite = {m_FileID 4, m_PathID 58}, mà external
    # thứ 4 của level17 chính là sharedassets17.assets. Hai sprite này có bản sao
    # trùng tên trong ui_jp; vá bản đó thì màn hình không đổi.
    ("sharedassets17.assets", "assets", [
        ("UL_short_a_key",          [(2, 31, "Select"), (124, 153, "Back")]),
        ("UL_short_c_history_key",  [(2, 32, "Back")]),
    ]),
    ("sharedassets21.assets", "assets", [                     # RECOLLECTION
        ("UL_recolle_key", [(2, 31, "Play scene"), (202, 231, "Back")]),
    ]),
    ("StreamingAssets/ui/ui_jp", "bundle", [
        ("UL_q&a_key",              [(2, 31, "Select"), (124, 153, "Back")]),
        ("UL_short_a_key",          [(2, 31, "Select"), (124, 153, "Back")]),
        ("UL_short_c_history_key",  [(2, 32, "Back")]),
        ("UL_status_a_com_key",     [(2, 31, "Back")]),
        ("UL_status_b_ind_key",     [(2, 36, "Back")]),
        # đang là "Enter", đổi cho đồng bộ với các màn khác
        ("UL_section_abc_com_key",  [(2, 32, "Select"), (124, 153, "Back")]),
        # backlog trong game: hai dòng, dòng dưới mở đầu bằng cặp nút ⓁⓇ
        ("UL_adv_backlog_key", [
            [(2, 32, "Play Voice"), (183, 212, "Rewind")],
            [(2, 66, "Fast Forward"), (215, 245, "Back")],
        ]),
        ("UL_adv_backlog_key2", [
            [(183, 213, "Play Voice")],
            [(2, 66, "Fast Forward"), (215, 245, "Back")],
        ]),
    ]),
]


def ink_color(img):
    a = np.asarray(img)
    m = a[:, :, 3] > 128
    return tuple(int(v) for v in np.median(a[:, :, :3][m], axis=0))


def icon_rows(img, x0, x1):
    """Dải dọc mà icon chiếm, để canh baseline."""
    a = np.asarray(img)[:, x0:x1, 3] > 40
    ys = np.nonzero(a.any(axis=1))[0]
    return int(ys.min()), int(ys.max()) + 1


PROBE_X = 50


def text_metrics(word, font):
    """(lệch bút so với mép trái nét, bề ngang nét thật)."""
    probe = Image.new("L", (900, 200), 0)
    ImageDraw.Draw(probe).text((PROBE_X, 150), word, font=font, fill=255, anchor="ls")
    xs = np.nonzero((np.asarray(probe) > 8).any(axis=0))[0]
    l, r = int(xs.min()), int(xs.max()) + 1
    return PROBE_X - l, r - l


def is_disc(img, x0, x1, y0=0, y1=None):
    """Ô [x0,x1) có đúng là icon nút bấm không? Khối rộng gấp đôi = cặp nút (ⓁⓇ)."""
    a = np.asarray(img)[y0:y1, x0:x1, 3] > 60
    ys = np.nonzero(a.any(axis=1))[0]
    if len(ys) == 0:
        return 0.0
    sub = a[ys.min():ys.max() + 1]
    h, w = sub.shape
    k = max(1, int(round(w / float(h))))          # số nút nằm cạnh nhau
    scores = []
    for i in range(k):
        part = sub[:, round(i * w / k):round((i + 1) * w / k)]
        ph, pw = part.shape
        d = min(ph, pw)
        if d < 12:
            return 0.0
        yy, xx = np.mgrid[0:ph, 0:pw]
        r = (d - 1) / 2.0
        disc = ((yy - (ph - 1) / 2.0) ** 2 + (xx - (pw - 1) / 2.0) ** 2) <= r * r
        scores.append((part & disc).sum() / max(1, (part | disc).sum()))
    return min(scores)


_stock_cache = {}


def stock_art(rel, name):
    """Ảnh sprite trong bản gốc (chưa dịch) — mốc để biết đã sửa hay chưa."""
    if rel not in _stock_cache:
        p = os.path.join(STOCK, rel).replace("\\", "/")
        _stock_cache[rel] = Container(p)
    return _stock_cache[rel].sprite(name).crop()


def as_rows(spec):
    """Cho phép khai báo một dòng (danh sách tuple) hoặc nhiều dòng (danh sách dòng)."""
    return spec if isinstance(spec[0], list) else [spec]


def ink_bands(img):
    """Các dải dòng có mực, theo thứ tự từ trên xuống."""
    m = np.asarray(img)[:, :, 3] > 60
    rowmask = m.any(axis=1)
    out, st = [], None
    for i, v in enumerate(rowmask):
        if v and st is None:
            st = i
        elif not v and st is not None:
            out.append((st, i))
            st = None
    if st is not None:
        out.append((st, len(rowmask)))
    return out


def check_spec(img, name, spec):
    """Toạ độ icon khai báo phải trỏ đúng vào nút bấm của **tranh gốc**."""
    rows = as_rows(spec)
    bands = ink_bands(img)
    if len(bands) != len(rows):
        raise ValueError(f"{name}: tranh gốc có {len(bands)} dòng, khai báo {len(rows)}")
    for (y0, y1), row in zip(bands, rows):
        for x0, x1, *_ in row:
            if x0 is None:                     # cụm chỉ có chữ, không có nút
                continue
            s = is_disc(img, x0, x1, y0, y1)
            if s < 0.72:
                raise ValueError(f"{name}: x{x0}-{x1} y{y0}-{y1} không phải nút bấm (IoU {s:.2f})")


def baseline_for(font, iy0, iy1):
    """Baseline sao cho một từ không có nét thò xuống nằm giữa đĩa nút."""
    probe = Image.new("L", (400, 300), 0)
    ImageDraw.Draw(probe).text((40, 200), "Back", font=font, fill=255, anchor="ls")
    ys = np.nonzero((np.asarray(probe) > 60).any(axis=1))[0]
    top_off = 200 - int(ys.min())
    ink_h = int(ys.max()) - int(ys.min()) + 1
    return int(round(iy0 + ((iy1 - iy0) - ink_h) / 2.0 + top_off))


def layout_row(img, row, band, w, font_path):
    """Xếp một dòng: trả về (danh sách việc vẽ, cỡ chữ, khoảng cách cụm)."""
    y0, y1 = band
    if row[0][0] is None:                      # dòng chỉ có chữ (câu nhắc)
        iy0, iy1 = y0, y1
    else:
        iy0, iy1 = icon_rows(img.crop((0, y0, w, y1)), row[0][0], row[0][1])
        iy0 += y0
        iy1 += y0
    ref = iy1 - iy0 if row[0][0] is None else min(row[0][1] - row[0][0], iy1 - iy0)
    icon_span = sum(x1 - x0 for x0, x1, *_ in row if x0 is not None)
    n_icon = sum(1 for x0, *_ in row if x0 is not None)
    n = len(row)

    # phần tử đầu dòng có thể kèm font riêng và cỡ ghim: (x0, x1, chữ, font[, cỡ])
    if len(row[0]) > 3:
        font_path = row[0][3]
    fixed = row[0][4] if len(row[0]) > 4 else None
    bases = [fixed] if fixed else range(SIZE_MAX, SIZE_MIN - 1, -1)

    for base in bases:
        size = base if fixed else max(SIZE_MIN, int(round(base * ref / 29.0)))
        font = ImageFont.truetype(font_path, size)
        metrics = [text_metrics(item[2], font) for item in row]
        natural = ((row[0][0] or 0) + icon_span + n_icon * GAP_ICON_TEXT
                   + sum(m[1] for m in metrics) + (n - 1) * GAP_GROUP_MIN)
        if natural > w:
            continue

        slack = w - natural
        gap, start = GAP_GROUP_MIN, (row[0][0] or 0)
        if n > 1:
            gap = min(GAP_GROUP_MAX, GAP_GROUP_MIN + slack // (n - 1))
            start += slack - (gap - GAP_GROUP_MIN) * (n - 1)
        else:
            start += slack

        bl = baseline_for(font, iy0, iy1)
        plan, x = [], start
        for item, (pen, ink_w) in zip(row, metrics):
            ix0, ix1, word = item[0], item[1], item[2]
            if ix0 is not None:
                plan.append(((ix0, y0, ix1, y1), x))
                x += ix1 - ix0 + GAP_ICON_TEXT
            plan.append((word, (x + pen, bl), font))
            x += ink_w + gap
        return plan, size, gap
    raise ValueError("không xếp vừa bề ngang")


def compose(img, spec, font_path=FONT):
    """Dựng lại dải: icon cắt từ tranh gốc, chữ Nhật thay bằng chữ Anh.

    Cỡ chữ lấy lớn nhất còn xếp vừa bề ngang ô, rồi bao nhiêu chỗ dư dồn hết
    vào khoảng cách giữa các cụm — dải căng đầy ô đúng như bản Nhật, và cụm
    `Ⓑ Back` bị đẩy sang phải thay vì để trống một khoảng ở mép.
    """
    w, h = img.size
    col = ink_color(img)
    rows = as_rows(spec)
    bands = ink_bands(img)

    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layer = Image.new("L", (w, h), 0)
    dr = ImageDraw.Draw(layer)
    sizes, gaps = [], []
    for row, band in zip(rows, bands):
        plan, size, gap = layout_row(img, row, band, w, font_path)
        sizes.append(size)
        gaps.append(gap)
        for item in plan:
            if len(item) == 2:                        # (hộp icon, x mới)
                box, x = item
                out.paste(img.crop(box), (x, box[1]))
            else:                                     # (chữ, vị trí, font)
                word, pos, font = item
                dr.text(pos, word, font=font, fill=255, anchor="ls")

    tint = Image.new("RGBA", (w, h), col + (255,))
    tint.putalpha(layer)
    out.alpha_composite(tint)
    return out, min(sizes), min(gaps)


def source_path(rel):
    p = os.path.join(PATCH, rel).replace("\\", "/")
    if os.path.exists(p):
        return p, True
    return os.path.join(STOCK, rel).replace("\\", "/"), False


def main():
    apply = "--apply" in sys.argv
    # --only <chuỗi>: chỉ chạy những file có chuỗi đó trong đường dẫn
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    os.makedirs(PREVIEW, exist_ok=True)
    work = os.path.join(PREVIEW, "_work")
    os.makedirs(work, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")

    for rel, kind, sprites in JOBS:
        if only and only not in rel:
            continue
        src, in_patch = source_path(rel)
        base = os.path.basename(rel)
        # đọc từ một bản sao, mượn .resS của bản gốc nếu bản vá thiếu
        tmp = os.path.join(work, base).replace("\\", "/")
        shutil.copy(src, tmp)
        res = os.path.join(STOCK, rel).replace("\\", "/") + ".resS"
        if os.path.exists(res) and not os.path.exists(tmp + ".resS"):
            shutil.copy(res, tmp + ".resS")

        c = Container(tmp)
        touched = 0
        for name, spec in sprites:
            s = c.sprite(name)
            before = s.crop()                 # đang có gì trong bản vá (để so sánh)
            origin = stock_art(rel, name)     # nguồn dựng: luôn là bản gốc
            check_spec(origin, name, spec)
            after, size, gap = compose(origin, spec)
            s.paste(after)
            s.full_rect_mesh()
            touched += 1
            slug = f"{base}__{name.replace('&', 'and')}"
            side = Image.new("RGB", (max(before.width, after.width),
                                     before.height + after.height + 6), (250, 250, 250))
            side.paste(Image.alpha_composite(
                Image.new("RGBA", before.size, (250, 250, 250, 255)), before).convert("RGB"), (0, 0))
            side.paste(Image.alpha_composite(
                Image.new("RGBA", after.size, (250, 250, 250, 255)), after).convert("RGB"),
                (0, before.height + 6))
            side.save(os.path.join(PREVIEW, slug + ".png"))
            print(f"  {name:26s} {before.size[0]}x{before.size[1]} font={size} gap={gap}")

        if not touched:
            print(f"{rel}: không còn gì để sửa")
            continue

        if apply:
            dst = os.path.join(PATCH, rel).replace("\\", "/")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                os.makedirs(BACKUP, exist_ok=True)
                shutil.copy(dst, os.path.join(BACKUP, f"{base}.prekeyprompt-{stamp}"))
            n = c.save(tmp + ".out", packer="lz4" if kind == "bundle" else None)
            shutil.move(tmp + ".out", dst)
            print(f"{rel}: ghi {n:,} byte (nguồn {'vá' if in_patch else 'gốc'})")
        else:
            print(f"{rel}: chạy thử, chưa ghi (nguồn {'vá' if in_patch else 'gốc'})")

    print("\nẢnh xem trước:", PREVIEW)
    if not apply:
        print("Chạy lại với --apply để vá thật.")


if __name__ == "__main__":
    main()
