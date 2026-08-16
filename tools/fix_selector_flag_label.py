"""Dịch nhãn `セレクター / フラグ` ở màn SECTION SELECT.

Nhãn này **nằm chung sprite với thanh chọn**: `UL_section_b_skill_chara_frame_base`
(1104×100) gồm thanh tím + khối navy + hai dòng katakana ở mép phải. Grep không
ra vì là tranh, và dò theo tên sprite cũng không ra vì tên chỉ nói "frame_base".

Sprite có bản trùng tên ở **cả hai nơi** — `sharedassets6.assets` (cảnh dựng sẵn,
là bản game thực đọc) và `ui_jp` — nên vá cả hai.

    python tools\fix_selector_flag_label.py [--apply]
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

NAME = "UL_section_b_skill_chara_frame_base"
TARGETS = [("sharedassets6.assets", "assets"),
           ("StreamingAssets/ui/ui_jp", "bundle")]
WIPE = (972, 6, 1104, 92)     # thanh chọn kết thúc ở x=947, nên từ 972 là trống
LEFT = 980
LINES = [("Selector", (13, 38)), ("Flag", (58, 83))]
CAP_H = 19                    # katakana cao 25 px; chữ Latin cùng cỡ quang học


def cap_size(target):
    best = None
    for size in range(8, 60):
        f = ImageFont.truetype(FONT, size)
        im = Image.new("L", (200, 200), 0)
        ImageDraw.Draw(im).text((40, 40), "S", font=f, fill=255)
        ys = np.nonzero((np.asarray(im) > 60).any(axis=1))[0]
        if not len(ys):
            continue
        h = ys.max() - ys.min() + 1
        if best is None or abs(h - target) < abs(best[1] - target):
            best = (size, h)
    return best


def build(img):
    w, h = img.size
    a = np.array(img)
    op = a[:, :, 3] > 60
    label = op.copy()
    label[:, :WIPE[0]] = False
    colour = tuple(int(v) for v in np.median(a[:, :, :3][label], axis=0))

    size, got = cap_size(CAP_H)
    font = ImageFont.truetype(FONT, size)

    out = Image.fromarray(a)
    out.paste(Image.new("RGBA", (WIPE[2] - WIPE[0], WIPE[3] - WIPE[1]), (0, 0, 0, 0)),
              (WIPE[0], WIPE[1]))

    layer = Image.new("L", (w, h), 0)
    dr = ImageDraw.Draw(layer)
    for text, (y0, y1) in LINES:
        probe = Image.new("L", (400, 200), 0)
        ImageDraw.Draw(probe).text((40, 120), text, font=font, fill=255, anchor="ls")
        arr = np.asarray(probe) > 60
        ys = np.nonzero(arr.any(axis=1))[0]
        xs = np.nonzero(arr.any(axis=0))[0]
        ink_h = int(ys.max()) - int(ys.min()) + 1
        top = y0 + (y1 - y0 - ink_h) // 2
        dr.text((LEFT + (40 - int(xs.min())), top + (120 - int(ys.min()))),
                text, font=font, fill=255, anchor="ls")
        print(f"    {text:9s} x{LEFT}-{LEFT + int(xs.max()) - int(xs.min()) + 1}"
              f"  dòng y{y0}-{y1}")
    tint = Image.new("RGBA", (w, h), colour + (255,))
    tint.putalpha(layer)
    out.alpha_composite(tint)
    print(f"    NewRodin cỡ {size} (chữ hoa cao {got} px), màu {colour}")
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
        s = c.sprite(NAME)
        before = s.crop()
        after = build(Container(os.path.join(STOCK, rel).replace("\\", "/")).sprite(NAME).crop())
        s.paste(after)
        s.full_rect_mesh()

        side = Image.new("RGB", (before.width, before.height * 2 + 8), (250, 250, 250))
        for i, im in enumerate((before, after)):
            flat = Image.alpha_composite(Image.new("RGBA", im.size, (250, 250, 250, 255)), im)
            side.paste(flat.convert("RGB"), (0, i * (before.height + 8)))
        side.save(os.path.join(PREVIEW, f"{base}__{NAME}.png"))

        if apply:
            dst = os.path.join(PATCH, rel).replace("\\", "/")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                os.makedirs(BACKUP, exist_ok=True)
                shutil.copy(dst, os.path.join(BACKUP, f"{base}.preselflag-{stamp}"))
            n = c.save(tmp + ".out", packer="lz4" if kind == "bundle" else None)
            shutil.move(tmp + ".out", dst)
            print(f"    ghi {n:,} byte")
        else:
            print("    chạy thử, chưa ghi")


if __name__ == "__main__":
    main()
