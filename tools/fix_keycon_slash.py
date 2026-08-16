# -*- coding: utf-8 -*-
"""Bỏ dấu cách hai bên dấu `/` trên nhãn `GENEBARK / TERMINAL` của tab KEY-CONFIG.

Nhãn này là **hình vẽ sẵn** (`UL_option_keycon_menu_jenetar` trong
`sharedassets7.assets`, atlas `…-Option-546c882d`), không phải chuỗi ký tự.
Bản dịch nới nó từ 405 lên 596 px, dài hơn ô hiển thị, nên chữ `L` cuối bị
xén — xem ảnh chụp `_2026-08-17_05-43-33.png`.

Đo trên chính tấm ảnh: khoảng cách giữa các chữ cái là 9–12 px, còn hai khoảng
quanh dấu `/` là **26 px**. Rút mỗi bên về 10 px là dôi ra 32 px, đủ để chữ
`L` lọt vào trong ô.

> ### Vì sao dịch chữ sang trái chứ không thu nhỏ ảnh
>
> `SpriteSlot.paste()` bắt buộc ảnh đúng bằng ô atlas. Thu hẹp ảnh sẽ phải sửa
> `textureRect`, mesh và `uvTransform` — ba thứ đã từng làm hỏng art ở dự án
> này. Giữ nguyên 596 px và dồn chữ sang trái thì **không đụng gì tới hình học**,
> phần dôi bên phải để trong suốt.
>
> ### KHÔNG gọi `full_rect_mesh()` ở atlas này
>
> `fix_volume_ends.py` đã dính: atlas Option xếp sát nét và Unity nhét sprite
> khác vào chỗ trống bên trong hình chữ nhật, nên phủ full-rect thì `X BUTTON`,
> `SKIP CHOICES`… hiện đè lên hàng khác. Ở đây không cần: nét mới nằm gọn trong
> vùng nét cũ (cột 0..539 so với 0..571), nên mesh tight sẵn có đã phủ đủ.

Các cột được ghép lại lấy nguyên từ ảnh cũ, nên giữ nguyên khử răng cưa và cả
phần RGB đã tràn ra vùng trong suốt — không cần dựng lại bleed.

Chạy với --write để ghi.
"""
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from keyart import Container

WRITE = "--write" in sys.argv
PATCH = r"D:\Downloads\010068501ff9a000\romfs\Data"
BACKUP = r"D:\Downloads\010068501ff9a000\_backup"
REL = "sharedassets7.assets"
NAME = "UL_option_keycon_menu_jenetar"
KEEP = 10          # khoảng cách chữ cái bình thường, đo được 9–12


def ink_runs(img):
    px = img.load()
    w, h = img.size
    ink = [any(px[x, y][3] > 16 for y in range(h)) for x in range(w)]
    runs, x = [], 0
    while x < w:
        v, s = ink[x], x
        while x < w and ink[x] == v:
            x += 1
        runs.append((v, s, x - 1, x - s))
    return runs


def close_slash_gaps(img):
    """Cắt hai khoảng trắng rộng nhất (hai bên dấu /) xuống còn KEEP px."""
    runs = ink_runs(img)
    wide = sorted((r for r in runs if not r[0]), key=lambda r: -r[3])[:2]
    wide = sorted(wide, key=lambda r: r[1])
    if len(wide) != 2 or wide[0][3] < 20:
        raise SystemExit("khong tim thay hai khoang cach quanh dau / nhu mong doi: %s" % (wide,))
    (_, g1a, g1b, g1n), (_, g2a, g2b, g2n) = wide

    parts = [img.crop((0, 0, g1a, img.height)),                 # tới hết chữ K
             img.crop((g1a, 0, g1a + KEEP, img.height)),        # khoảng hẹp
             img.crop((g1b + 1, 0, g2a, img.height)),           # dấu /
             img.crop((g2a, 0, g2a + KEEP, img.height)),        # khoảng hẹp
             img.crop((g2b + 1, 0, img.width, img.height))]     # từ chữ T trở đi

    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    x = 0
    for p in parts:
        out.paste(p, (x, 0))
        x += p.width
    saved = (g1n - KEEP) + (g2n - KEEP)
    return out, saved, (g1n, g2n)


src = os.path.join(PATCH, REL)
c = Container(src)
s = c.sprite(NAME)
before = s.crop()
after, saved, gaps = close_slash_gaps(before)

b_runs = [r for r in ink_runs(before) if r[0]]
a_runs = [r for r in ink_runs(after) if r[0]]
print("%s  %dx%d" % (NAME, before.width, before.height))
print("  khoang quanh dau /: %d va %d px  ->  %d px moi ben" % (gaps[0], gaps[1], KEEP))
print("  net: cot %d..%d  ->  %d..%d   (thu ngan %d px)"
      % (b_runs[0][1], b_runs[-1][2], a_runs[0][1], a_runs[-1][2], saved))
assert a_runs[-1][2] <= b_runs[-1][2], "net moi phai nam trong vung net cu"

prev = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_preview")
os.makedirs(prev, exist_ok=True)
side = Image.new("RGB", (before.width, before.height * 2 + 6), (60, 40, 90))
side.paste(Image.alpha_composite(Image.new("RGBA", before.size, (60, 40, 90, 255)), before).convert("RGB"), (0, 0))
side.paste(Image.alpha_composite(Image.new("RGBA", after.size, (60, 40, 90, 255)), after).convert("RGB"),
           (0, before.height + 6))
side.save(os.path.join(prev, "keycon_slash.png"))
print("  xem truoc -> tools/_preview/keycon_slash.png")

if not WRITE:
    print("\nCHAY THU - them --write de ghi")
    sys.exit(0)

s.paste(after)                      # co y KHONG goi full_rect_mesh()
dst = os.path.join(PATCH, REL)
stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(os.path.getmtime(dst)))
bak = os.path.join(BACKUP, "sharedassets7.assets.prekeyconslash-%s" % stamp)
if not os.path.exists(bak):
    shutil.copy2(dst, bak)
    print("  backup ->", os.path.basename(bak))
n = c.save(dst + ".out")
shutil.move(dst + ".out", dst)
print("  da ghi %s (%s byte)" % (REL, format(os.path.getsize(dst), ",")))

chk = Container(dst).sprite(NAME).crop()
r = [x for x in ink_runs(chk) if x[0]]
print("  doc lai: net cot %d..%d" % (r[0][1], r[-1][2]))
