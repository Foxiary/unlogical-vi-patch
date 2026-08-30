# -*- coding: utf-8 -*-
"""Lọc ảnh chụp nào có băng-rôn [terinfo], và cắt riêng vùng băng-rôn ra để xem.

Băng-rôn nằm góc trên phải, đo từ `level10`:

```
Panel  600 x 124  pivot (1, .5)  anchoredPosition (942, 237)
Text   580 x  94  size 32, không wrap
trên khung 1920 x 1080  ->  x 1302..1902,  y 241..365
```

Nhận diện: vùng đó lúc không có băng-rôn là nền cảnh (đủ màu, ít tương phản cục bộ);
lúc có băng-rôn là nền tối đặc + chữ sáng. Đo bằng **tỉ lệ điểm rất tối** và **độ lệch
chuẩn theo cột** — chữ trắng trên nền tối cho cả hai đều cao.

    python e2e\\checks\\find_terinfo.py e2e\\out\\terinfo_2026-08-29_04-00-00
"""
import io
import os
import sys

if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PIL import Image   # noqa: E402

BOX = (1302, 241, 1902, 365)      # x0, y0, x1, y1 trên khung 1920x1080


def score(path):
    im = Image.open(path).convert("RGB")
    if im.size != (1920, 1080):
        im = im.resize((1920, 1080))
    crop = im.crop(BOX)
    px = crop.convert("L")
    w, h = px.size
    data = list(px.getdata())
    dark = sum(1 for v in data if v < 60) / float(len(data))
    bright = sum(1 for v in data if v > 190) / float(len(data))
    return crop, dark, bright


def main():
    if len(sys.argv) < 2:
        raise SystemExit("dùng: find_terinfo.py <thư mục ảnh>")
    d = sys.argv[1]
    outdir = os.path.join(d, "banner")
    os.makedirs(outdir, exist_ok=True)
    rows = []
    for f in sorted(os.listdir(d)):
        if not f.lower().endswith(".png"):
            continue
        p = os.path.join(d, f)
        try:
            crop, dark, bright = score(p)
        except Exception as e:
            print("  %-22s LỖI %s" % (f, e))
            continue
        # băng-rôn: nền tối chiếm phần lớn VÀ có chữ sáng rõ
        hit = dark > 0.45 and bright > 0.02
        rows.append((f, dark, bright, hit))
        if hit:
            crop.save(os.path.join(outdir, f))
    print("%-24s %6s %7s  %s" % ("ảnh", "tối", "sáng", ""))
    for f, dk, br, hit in rows:
        print("%-24s %6.3f %7.3f  %s" % (f, dk, br, "CÓ BĂNG-RÔN" if hit else ""))
    n = sum(1 for r in rows if r[3])
    print("\n%d/%d ảnh có băng-rôn -> %s" % (n, len(rows), outdir))


if __name__ == "__main__":
    main()
