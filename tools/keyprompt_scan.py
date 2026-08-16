"""Kiểm kê toàn bộ dải "key prompt" của game và tách chúng thành từng khối.

Chạy:  python tools\keyprompt_scan.py            # in bảng + xuất ảnh phóng to
"""

import io
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from keyart import Container

STOCK = "D:/Downloads/UNLOGICAL_v2/Data"
PATCH = "D:/Downloads/010068501ff9a000/romfs/Data"

# (file trong Data, tên sprite) — mọi dải phím của game
TARGETS = [
    ("sharedassets5.assets", "UL_library_key"),
    ("sharedassets5.assets", "UL_library_key2"),
    ("sharedassets5.assets", "UL_library_key3"),
    ("sharedassets5.assets", "UL_library_key4"),
    ("sharedassets5.assets", "UL_library_key5"),
    ("sharedassets6.assets", "UL_section_abc_com_key"),
    ("sharedassets7.assets", "UL_option_com_key"),
    ("sharedassets9.assets", "UL_archive_key"),
    ("sharedassets10.assets", "UL_map_key"),
    ("sharedassets11.assets", "UL_manual_key"),
    ("sharedassets13.assets", "UL_music_key"),
    ("sharedassets17.assets", "UL_short_a_key"),
    ("sharedassets17.assets", "UL_short_c_history_key"),
    ("sharedassets19.assets", "UL_salo_key"),
    ("sharedassets21.assets", "UL_recolle_key"),
    ("sharedassets22.assets", "UL_dictionary_key"),
    ("StreamingAssets/scene/scene_jp", "UL_movie_a_key"),
    ("StreamingAssets/ui/ui_jp", "UL_q&a_key"),
    ("StreamingAssets/ui/ui_jp", "UL_short_a_key"),
    ("StreamingAssets/ui/ui_jp", "UL_short_c_history_key"),
    ("StreamingAssets/ui/ui_jp", "UL_status_a_com_key"),
    ("StreamingAssets/ui/ui_jp", "UL_status_b_ind_key"),
    ("StreamingAssets/ui/ui_jp", "UL_sys_plate_key"),
    ("StreamingAssets/ui/ui_jp", "UL_section_abc_com_key"),
    ("StreamingAssets/ui/ui_jp", "UL_adv_backlog_key"),
    ("StreamingAssets/ui/ui_jp", "UL_adv_backlog_key2"),
]

ALPHA = 40


def rows(mask):
    """Cắt ảnh thành các dòng chữ theo khoảng trắng ngang."""
    ink = mask.any(axis=1)
    out, start = [], None
    for i, v in enumerate(ink):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(ink)))
    return out


def groups(mask, gap):
    """Cắt một dòng thành các khối theo khoảng trắng dọc >= gap."""
    ink = mask.any(axis=0)
    out, start, blank = [], None, 0
    for i, v in enumerate(ink):
        if v:
            if start is None:
                start = i
            blank = 0
        elif start is not None:
            blank += 1
            if blank >= gap:
                out.append((start, i - blank + 1))
                start = None
    if start is not None:
        out.append((start, len(ink)))
    return out


def describe(img, gap=7):
    a = np.asarray(img)
    m = a[:, :, 3] > ALPHA
    res = []
    for r0, r1 in rows(m):
        line = []
        for c0, c1 in groups(m[r0:r1], gap):
            sub = a[r0:r1, c0:c1]
            om = sub[:, :, 3] > 128
            col = tuple(int(v) for v in np.median(sub[:, :, :3][om], axis=0)) if om.any() else (0, 0, 0)
            line.append(dict(x0=c0, x1=c1, w=c1 - c0, col=col))
        res.append(dict(y0=r0, y1=r1, h=r1 - r0, items=line))
    return res


def main():
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_keyprompt")
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)
    for rel, name in TARGETS:
        for root, tag in ((PATCH, "patch"), (STOCK, "stock")):
            p = os.path.join(root, rel).replace("\\", "/")
            if not os.path.exists(p):
                continue
            try:
                c = Container(p)
                s = c.sprite(name)
                img = s.crop()
            except Exception as e:
                print(f"{tag:5s} {rel:34s} {name:26s} bỏ qua ({type(e).__name__})")
                continue
            slug = f"{os.path.basename(rel)}__{name.replace('&','and')}__{tag}"
            img.save(os.path.join(outdir, slug + ".png"))
            desc = describe(img)
            print(f"{tag:5s} {rel:34s} {name:26s} {img.width}x{img.height} verts={s.vertex_count()}")
            for ln in desc:
                items = " | ".join(f"{it['x0']}-{it['x1']}({it['w']}) {it['col']}" for it in ln["items"])
                print(f"        y{ln['y0']}-{ln['y1']}: {items}")
            break


if __name__ == "__main__":
    main()
