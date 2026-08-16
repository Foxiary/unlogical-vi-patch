"""Dịch hai nhãn còn tiếng Nhật ở màn SECTION SELECT.

| sprite | cũ | mới | ghi chú |
|---|---|---|---|
| `UL_section_b_opera_ON_moji` (241×30) | オペレータースキル | Operator Skill | giãn chữ cho đầy ô, đúng như bản Nhật |
| `UL_section_c_love_HIGH_on` / `LOW_on` (504×92) | 好感度 xếp dọc | Likability xoay 90° | ô nhãn 25×89 ở mép phải |

Từ tiếng Anh lấy từ chính hình nền của game: `UL_section_b_bg_on_operator` in
"OPERATOR SKILL", `UL_section_c_chara_*` in "Likability" và "High/Low" **xoay
theo chiều kim đồng hồ, đọc từ trên xuống** — nhãn dọc bám đúng chiều đó.

Cả hai sprite có bản trùng tên ở `sharedassets6.assets` (bản cảnh thực đọc) và
`ui_jp`, nên vá cả hai.

    python tools\fix_section_labels.py [--apply]
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
FONT = ("C:/Users/ADMIN/AppData/Local/Temp/claude/D--Downloads-010068501ff9a000/"
        "9d4f7fb5-9b6c-4487-a5b3-fbf1cbd6951d/scratchpad/fonts/font_BASE.ttf")

TARGETS = [("sharedassets6.assets", "assets"), ("StreamingAssets/ui/ui_jp", "bundle")]
JOBS = [("UL_section_b_opera_ON_moji", "wide", "Operator Skill"),
        ("UL_section_c_love_HIGH_on", "side", "Likability"),
        ("UL_section_c_love_LOW_on", "side", "Likability")]


def ink_box(mask):
    ys, xs = np.nonzero(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def cap_size(target):
    best = None
    for size in range(8, 60):
        f = ImageFont.truetype(FONT, size)
        im = Image.new("L", (200, 200), 0)
        ImageDraw.Draw(im).text((40, 40), "L", font=f, fill=255)
        ys = np.nonzero((np.asarray(im) > 60).any(axis=1))[0]
        if not len(ys):
            continue
        h = ys.max() - ys.min() + 1
        if best is None or abs(h - target) < abs(best[1] - target):
            best = (size, h)
    return best[0]


def render(text, size, track=0):
    """Ảnh mask khít nét của một chuỗi, có thể giãn chữ."""
    font = ImageFont.truetype(FONT, size)
    im = Image.new("L", (1400, 300), 0)
    dr = ImageDraw.Draw(im)
    x = 60
    for ch in text:
        dr.text((x, 220), ch, font=font, fill=255, anchor="ls")
        x += dr.textlength(ch, font=font) + track
    a = np.asarray(im) > 60
    ys, xs = np.nonzero(a)
    return Image.fromarray((a[ys.min():ys.max() + 1, xs.min():xs.max() + 1] * 255).astype("uint8"))


def build(img, kind, text):
    w, h = img.size
    a = np.array(img)
    op = a[:, :, 3] > 60
    colour = tuple(int(v) for v in np.median(a[:, :, :3][op], axis=0))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layer = Image.new("L", (w, h), 0)

    if kind == "wide":                       # cả sprite là một dòng chữ
        x0, y0, x1, y1 = ink_box(op)
        size = cap_size(int((y1 - y0) * 0.78))
        best = None
        for track in range(0, 30):
            g = render(text, size, track)
            if g.width > x1 - x0:
                break
            best = (g, track)
        g, track = best
        layer.paste(g, (x0, y0 + (y1 - y0 - g.height) // 2))
        print(f"    cỡ {size}, giãn {track} -> {g.width}px (ô {x1 - x0}px)")
    else:                                    # nhãn dọc ở mép phải
        cols = op.any(axis=0)
        xs = np.nonzero(cols)[0]
        gaps = []
        st = None
        for i in range(xs.min(), xs.max() + 1):
            if not cols[i]:
                st = i if st is None else st
            elif st is not None:
                if i - st >= 5:
                    gaps.append(i)
                st = None
        x0 = gaps[-1]
        bx0, by0, bx1, by1 = ink_box(op[:, x0:])
        bx0 += x0
        bx1 += x0
        out.paste(Image.fromarray(a), (0, 0))
        out.paste(Image.new("RGBA", (w - x0, h), (0, 0, 0, 0)), (x0, 0))
        size = cap_size(bx1 - bx0 - 4)
        while True:
            g = render(text, size).rotate(-90, expand=True)   # đọc từ trên xuống
            if g.height <= by1 - by0 and g.width <= bx1 - bx0:
                break
            size -= 1
        layer.paste(g, (bx0 + (bx1 - bx0 - g.width) // 2, by0 + (by1 - by0 - g.height) // 2))
        print(f"    cỡ {size} -> {g.width}x{g.height} (ô {bx1 - bx0}x{by1 - by0})")

    if kind == "wide":
        out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    tint = Image.new("RGBA", (w, h), colour + (255,))
    tint.putalpha(layer)
    out.alpha_composite(tint)
    return out


def main():
    apply = "--apply" in sys.argv
    os.makedirs(PREVIEW, exist_ok=True)
    work = os.path.join(PREVIEW, "_work")
    os.makedirs(work, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")

    for rel, kind in TARGETS:
        src = os.path.join(PATCH, rel).replace("\\", "/")
        if not os.path.exists(src):
            src = os.path.join(STOCK, rel).replace("\\", "/")
        base = os.path.basename(rel)
        tmp = os.path.join(work, base).replace("\\", "/")
        shutil.copy(src, tmp)
        res = os.path.join(STOCK, rel).replace("\\", "/") + ".resS"
        if os.path.exists(res) and not os.path.exists(tmp + ".resS"):
            shutil.copy(res, tmp + ".resS")

        print(f"{rel}:")
        c = Container(tmp)
        origin = Container(os.path.join(STOCK, rel).replace("\\", "/"))
        for name, mode, text in JOBS:
            s = c.sprite(name)
            before = s.crop()
            print(f"  {name} {before.size}")
            after = build(origin.sprite(name).crop(), mode, text)
            s.paste(after)
            s.full_rect_mesh()
            side = Image.new("RGB", (before.width, before.height * 2 + 8), (250, 250, 250))
            for i, im in enumerate((before, after)):
                flat = Image.alpha_composite(
                    Image.new("RGBA", im.size, (250, 250, 250, 255)), im)
                side.paste(flat.convert("RGB"), (0, i * (before.height + 8)))
            side.save(os.path.join(PREVIEW, f"{base}__{name}.png"))

        if apply:
            dst = os.path.join(PATCH, rel).replace("\\", "/")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                os.makedirs(BACKUP, exist_ok=True)
                shutil.copy(dst, os.path.join(BACKUP, f"{base}.presectionlabel-{stamp}"))
            n = c.save(tmp + ".out", packer="lz4" if kind == "bundle" else None)
            shutil.move(tmp + ".out", dst)
            print(f"    ghi {n:,} byte")
        else:
            print("    chạy thử, chưa ghi")


if __name__ == "__main__":
    main()
