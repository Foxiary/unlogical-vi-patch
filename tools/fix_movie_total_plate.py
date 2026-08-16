"""Dịch ô GET/TOTAL của màn MOVIE (`UL_movie_a_total_plate` trong `scene_jp`).

Ô này là tranh pixel: khung, chữ `GET/TOTAL`, đường kẻ, con robot và hai dòng
`なまえ：` / `すずの` đều nằm chung một sprite 348×243. Chỉ xoá hai dòng kana rồi
vẽ lại `NAME:` / `Suzuno` bằng `ULPixel`, canh chữ hoa cao đúng 21 px cho khớp
với `GET/TOTAL` ngay phía trên. Khung, đường kẻ và robot không đụng tới.

Sprite dùng mesh tight (29 đỉnh) nên phải dựng lại thành quad, xem
[[unitypy-switch-bundle-repack]].

    python tools\fix_movie_total_plate.py [--apply]
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
TARGET = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scene", "scene_jp")
STOCK = "D:/Downloads/UNLOGICAL_v2/Data/StreamingAssets/scene/scene_jp"
BACKUP = os.path.join(ROOT, "_backup")
PREVIEW = os.path.join(ROOT, "_keyprompt")
FONT = ("C:/Users/ADMIN/AppData/Local/Temp/claude/D--Downloads-010068501ff9a000/"
        "9d4f7fb5-9b6c-4487-a5b3-fbf1cbd6951d/scratchpad/fonts/ULPixel.ttf")

NAME = "UL_movie_a_total_plate"
WIPE = (60, 134, 192, 208)      # vùng xoá: chỉ hai dòng kana, chừa robot ở x>=196
LINES = [                       # (chữ mới, x trái, dải dòng của chữ cũ)
    ("NAME:",  72, (141, 165)),
    ("Suzuno", 72, (177, 201)),
]
CAP_H = 21                      # chiều cao chữ hoa của "GET/TOTAL" cùng ô
TRACK = 4                       # giãn chữ, bám theo nhịp của "GET/TOTAL"


def cap_size(font_path, target):
    """Cỡ font cho chiều cao chữ hoa đúng bằng `target`."""
    best = None
    for size in range(8, 60):
        f = ImageFont.truetype(font_path, size)
        im = Image.new("L", (200, 200), 0)
        ImageDraw.Draw(im).text((40, 40), "N", font=f, fill=255)
        ys = np.nonzero((np.asarray(im) > 60).any(axis=1))[0]
        if not len(ys):
            continue
        h = ys.max() - ys.min() + 1
        if best is None or abs(h - target) < abs(best[1] - target):
            best = (size, h)
    return best


def draw_tracked(draw, xy, text, font, fill, track):
    """Vẽ từng ký tự, cộng thêm khoảng giãn — PIL không có tuỳ chọn tracking."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + track
    return x - track


def build(img):
    w, h = img.size
    a = np.array(img)
    lum = a[:, :, :3].astype(int).sum(axis=2)
    ink = (a[:, :, 3] > 60) & (lum > 600)          # chữ trắng
    plate = np.median(a[:, :, :3][(a[:, :, 3] > 60) & (lum < 500)], axis=0)
    colour = tuple(int(v) for v in np.median(a[:, :, :3][ink], axis=0))

    size, got = cap_size(FONT, CAP_H)
    font = ImageFont.truetype(FONT, size)

    out = Image.fromarray(a)
    x0, y0, x1, y1 = WIPE
    out.paste(Image.new("RGBA", (x1 - x0, y1 - y0),
                        tuple(int(v) for v in plate) + (255,)), (x0, y0))

    layer = Image.new("L", (w, h), 0)
    dr = ImageDraw.Draw(layer)
    for text, left, (ty0, ty1) in LINES:
        probe = Image.new("L", (400, 200), 0)
        ImageDraw.Draw(probe).text((40, 40), text, font=font, fill=255)
        ys = np.nonzero((np.asarray(probe) > 60).any(axis=1))[0]
        top_off = int(ys.min()) - 40
        dr.text((0, 0), "", font=font)             # giữ PIL yên tâm
        end = draw_tracked(dr, (left, ty0 + (ty1 - ty0 - CAP_H) // 2 - top_off),
                           text, font, 255, TRACK)
        print(f"    {text:8s} x{left}-{int(end)}  dòng y{ty0}-{ty1}")
    tint = Image.new("RGBA", (w, h), colour + (255,))
    tint.putalpha(layer)
    out.alpha_composite(tint)
    print(f"    ULPixel cỡ {size} (chữ hoa cao {got} px), giãn {TRACK}, màu {colour}")
    return out


def main():
    apply = "--apply" in sys.argv
    os.makedirs(PREVIEW, exist_ok=True)
    work = os.path.join(PREVIEW, "_work")
    os.makedirs(work, exist_ok=True)
    tmp = os.path.join(work, "scene_jp").replace("\\", "/")
    shutil.copy(TARGET, tmp)

    c = Container(tmp)
    s = c.sprite(NAME)
    before = s.crop()
    after = build(Container(STOCK).sprite(NAME).crop())
    s.paste(after)
    s.full_rect_mesh()

    side = Image.new("RGB", (before.width * 2 + 8, before.height), (250, 250, 250))
    for i, im in enumerate((before, after)):
        flat = Image.alpha_composite(Image.new("RGBA", im.size, (250, 250, 250, 255)), im)
        side.paste(flat.convert("RGB"), (i * (before.width + 8), 0))
    side.save(os.path.join(PREVIEW, f"scene_jp__{NAME}.png"))

    if apply:
        os.makedirs(BACKUP, exist_ok=True)
        shutil.copy(TARGET, os.path.join(
            BACKUP, "scene_jp.pretotalplate-" + time.strftime("%Y%m%d-%H%M%S")))
        n = c.save(tmp + ".out", packer="lz4")
        shutil.move(tmp + ".out", TARGET)
        print(f"scene_jp: ghi {n:,} byte")
    else:
        print("chạy thử, chưa ghi —", os.path.join(PREVIEW, f"scene_jp__{NAME}.png"))


if __name__ == "__main__":
    main()
