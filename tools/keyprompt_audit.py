"""Kiểm kê mọi dải phím (key prompt) của game và xuất một tấm ảnh tổng hợp.

Đọc bản vá trước, thiếu file nào mới lấy bản gốc. File `.resS` thiếu trong bản vá
thì mượn của bản gốc qua thư mục làm việc tạm (game tự lấy từ romfs nền, nên
không cần chép `.resS` vào bản vá).

    python tools\keyprompt_audit.py [thư_mục_xuất]
"""

import io
import os
import shutil
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from keyart import Container
from keyprompt_scan import TARGETS, STOCK, PATCH


def load(rel, work):
    """Trả về Container của bản vá (mượn .resS bản gốc), hoặc của bản gốc."""
    pp = os.path.join(PATCH, rel).replace("\\", "/")
    sp = os.path.join(STOCK, rel).replace("\\", "/")
    if os.path.exists(pp):
        base = os.path.basename(rel)
        dst = os.path.join(work, base).replace("\\", "/")
        shutil.copy(pp, dst)
        res = sp + ".resS"
        if os.path.exists(res) and not os.path.exists(dst + ".resS"):
            shutil.copy(res, dst + ".resS")
        return Container(dst), "vá"
    return Container(sp), "gốc"


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "_keyprompt")
    outdir = os.path.abspath(outdir)
    work = os.path.join(outdir, "_work")
    os.makedirs(work, exist_ok=True)

    cache = {}
    rows = []
    for rel, name in TARGETS:
        if rel not in cache:
            cache[rel] = load(rel, work)
        c, tag = cache[rel]
        s = c.sprite(name)
        img = s.crop()
        label = f"{os.path.basename(rel)}  {name}  [{tag}] {img.width}x{img.height} v{s.vertex_count()}"
        rows.append((label, img))
        print(label)

    pad, lw = 12, 560
    W = lw + max(im.width for _, im in rows) + pad
    H = sum(im.height + pad for _, im in rows) + pad
    sheet = Image.new("RGBA", (W, H), (250, 250, 250, 255))
    dr = ImageDraw.Draw(sheet)
    y = pad
    for label, im in rows:
        dr.text((6, y + im.height // 2 - 6), label, fill=(0, 0, 0, 255))
        sheet.alpha_composite(im, (lw, y))
        y += im.height + pad
    p = os.path.join(outdir, "_audit.png")
    sheet.convert("RGB").save(p)
    print("->", p)


if __name__ == "__main__":
    main()
