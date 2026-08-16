# -*- coding: utf-8 -*-
"""Bào mỏng nhãn tab SOUND do mod vẽ cho khớp nét chữ gốc.

## Vì sao

Sau khi `fix_alpha_bleed.py` trả lại phần viền bị ăn mất, nhãn mod lộ ra là
**vốn được vẽ đậm hơn** nét gốc. Đo bề dày thân đứng trong atlas, cô lập từng
nhãn bằng mesh tight của chính sprite:

    gốc   BGM 3.59   MOVIE 3.74   VOICE 3.72          -> trung vị 3.72
    mod   18 dải, từ 3.83 đến 4.16                    -> trung vị 4.00

Trên màn cũng đúng chừng đó: `MOVIE` chữ `M` 3.66 px, `MIYABI` chữ `M` 4.04 px.
Chênh 0.28 px, mắt đọc ra thành "đậm hơn một cấp weight".

(`SE` 6.02 và `ch_17_unkn` 5.64 là ngoại lệ của thước đo, không phải nét đậm:
`SE` chỉ có hai chữ mà `S` toàn nét cong, `???` thì không có thân đứng nào.
Bỏ cả hai ra khỏi mốc.)

## Cách làm

Bào mòn **0.125 px mỗi bên** — siêu lấy mẫu ×8 rồi lọc min 3×3 một vòng, thu
nhỏ lại bằng trung bình khối. Chỉ đụng kênh alpha; RGB đã loang đúng từ đợt
trước nên giữ nguyên.

> **Cô lập bằng mesh, không cô lập bằng ô cắt.** Rect của các dải **chồng lên
> nhau** (`ch_03_ai` và `ch_11_hida` trùm nhau gần trọn; `ch_05_yuri` nằm lọt
> trong `com_frame_01_base`) — đó chính là lý do atlas phải dùng mesh tight. Cắt
> theo `textureRect` thì bào nhầm sang tranh của sprite khác. Mesh của mỗi sprite
> là **đúng** những điểm nó vẽ: với `ch_02_kai`, 792/792 điểm có mực ở nửa trái
> đều nằm trong mesh; với `ch_01_miya`, mesh ôm gọn ô chữ và bỏ ngoài 3522 điểm
> của hai sprite tab xếp chèn.

Mesh là tập quad thẳng trục, đọc từ luồng vertex 0 (float3, 12 B/đỉnh) rồi đổi
sang toạ độ ô cắt bằng nghịch đảo công thức trong `fix_volume_ends.py`.

    python tools\\fix_label_weight.py            # chạy thử, in bảng đo
    python tools\\fix_label_weight.py --apply    # backup, vá, ghi, đọc lại kiểm

Backup: `_backup\\sharedassets7.assets.prelabelweight`.
"""
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np                        # noqa: E402
from PIL import Image                     # noqa: E402

from keyart import Container              # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TARGET = os.path.join(ROOT, "romfs", "Data", "sharedassets7.assets")
BACKUP = os.path.join(ROOT, "_backup", "sharedassets7.assets.prelabelweight")
PREVIEW = os.path.join(HERE, "label_weight_preview.png")

PREFIX = "UL_option_sound_menu_"
STOCK = ("BGM", "MOVIE", "SE", "VOICE", "ch_17_unkn")   # nhãn gốc, không đụng
GAUGE = ("BGM", "MOVIE", "VOICE")                       # mốc để so nét
LX = 600                   # nửa trái của dải là vùng nhãn
SS = 8                     # hệ số siêu lấy mẫu
KERODE = 1                 # số subpixel bào mỗi bên -> SS phần px
PILL = (134, 80, 169)

APPLY = "--apply" in sys.argv


# --------------------------------------------------------------- mesh -> mặt nạ
def mesh_mask(slot, W, H):
    """Đúng những điểm sprite này vẽ. Rect chồng nhau nên phải hỏi mesh."""
    tree = slot.tree
    vd = tree["m_RD"]["m_VertexData"]
    n = vd["m_VertexCount"]
    data = bytes(vd["m_DataSize"])
    pos = [struct.unpack_from("<fff", data, 12 * i) for i in range(n)]

    p2u = tree["m_PixelsToUnits"]
    mr, pv = tree["m_Rect"], tree["m_Pivot"]
    off = slot.rd["textureRectOffset"]
    bx = mr["width"] * pv["x"] - off["x"]
    by = mr["height"] * pv["y"] - off["y"]

    m = np.zeros((H, W), bool)
    for i in range(0, n - 3, 4):
        g = pos[i:i + 4]
        xs = [v[0] * p2u + bx for v in g]
        ys = [H - (v[1] * p2u + by) for v in g]
        x0, x1 = max(0, int(np.floor(min(xs)))), min(W, int(np.ceil(max(xs))))
        y0, y1 = max(0, int(np.floor(min(ys)))), min(H, int(np.ceil(max(ys))))
        m[y0:y1, x0:x1] = True
    return m


# ------------------------------------------------------------------ bào mòn
def erode(cov, ss=SS, k=KERODE):
    """Bào mòn k/ss pixel mỗi bên, giữ khử răng cưa (min 3x3 ở mức siêu lấy mẫu)."""
    H, W = cov.shape
    up = np.repeat(np.repeat(cov.astype(np.float32), ss, 0), ss, 1)
    for _ in range(k):
        out = up.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                t = np.roll(np.roll(up, dy, 0), dx, 1)
                if dy > 0:
                    t[:dy] = 0
                elif dy < 0:
                    t[dy:] = 0
                if dx > 0:
                    t[:, :dx] = 0
                elif dx < 0:
                    t[:, dx:] = 0
                np.minimum(out, t, out=out)
        up = out
    return up.reshape(H, ss, W, ss).mean(axis=(1, 3))


# -------------------------------------------------------------------- đo đạc
def stem_widths(cov):
    """Bề dày thân đứng: đoạn chạy ngang ở dải hàng giữa của mỗi chữ."""
    H, W = cov.shape
    colmax = cov.max(0)
    groups, s = [], None
    for x in range(W + 1):
        on = x < W and colmax[x] >= 0.5
        if on and s is None:
            s = x
        elif not on and s is not None:
            groups.append((s, x))
            s = None
    vals = []
    for a, b in groups:
        rows = np.where(cov[:, a:b].max(1) >= 0.5)[0]
        if len(rows) < 18:
            continue
        lo, hi = rows[0], rows[-1]
        for y in range(int(lo + (hi - lo) * 0.35), int(lo + (hi - lo) * 0.65) + 1):
            n, started = 0.0, False
            for x in range(max(0, a - 2), min(W, b + 2)):
                v = cov[y, x]
                if v >= 0.12:
                    n += v
                    started = True
                elif started:
                    break
            if n > 0.5:
                vals.append(n)
    return sorted(vals)


def label_cov(c, name):
    """Phủ của riêng nhãn: alpha ∩ mesh ∩ nửa trái."""
    s = c.sprite(name)
    img = s.crop()
    W, H = img.size
    a = np.array(img)[:, :, 3].astype(np.float32) / 255.0
    m = mesh_mask(s, W, H)
    m[:, LX:] = False
    return s, img, m, np.where(m, a, 0.0)[:, :LX]


def weigh(c):
    out = {}
    for n in sorted(x for x in c.sprite_names() if x.startswith(PREFIX)):
        _, _, _, cov = label_cov(c, n)
        v = stem_widths(cov)
        if v:
            out[n.replace(PREFIX, "")] = v[len(v) // 2]
    return out


def show(tbl, tag):
    g = sorted(tbl[k] for k in GAUGE if k in tbl)
    mod = sorted(v for k, v in tbl.items() if k not in STOCK)
    print("\n--- %s ---" % tag)
    print("   gốc (%s): %s  -> mốc %.2f"
          % ("/".join(GAUGE), " ".join("%.2f" % x for x in g), g[len(g) // 2]))
    print("   mod (%d dải): trung vị %.2f  min %.2f  max %.2f"
          % (len(mod), mod[len(mod) // 2], mod[0], mod[-1]))
    return g[len(g) // 2], mod[len(mod) // 2]


# --------------------------------------------------------------------- chính
def main():
    c = Container(TARGET)
    before = weigh(c)
    gauge, _ = show(before, "TRƯỚC")

    tex = [o for o in c.objects if o.type.name == "Texture2D"
           and o.read().m_Width >= 512]
    if len(tex) != 1:
        raise SystemExit("mong đợi 1 texture atlas, thấy %d" % len(tex))
    obj = tex[0]
    key = (id(obj.assets_file), obj.path_id)
    atlas = np.array(c.tex_image(key))

    targets = [n for n in sorted(x for x in c.sprite_names() if x.startswith(PREFIX))
               if n.replace(PREFIX, "") not in STOCK]
    print("\nbào %d dải, %d/%d px mỗi bên" % (len(targets), KERODE, SS))

    seen = np.zeros(atlas.shape[:2], bool)
    tiles = []
    total = 0
    for n in targets:
        s, img, m, _ = label_cov(c, n)
        b = s.box()
        a = np.array(img)[:, :, 3].astype(np.float32) / 255.0
        new_a = erode(a)
        sub = atlas[b[1]:b[3], b[0]:b[2], 3]
        clash = int((seen[b[1]:b[3], b[0]:b[2]] & m).sum())
        if clash:
            raise SystemExit("%s: mặt nạ đè lên dải đã xử lý (%d điểm)" % (n, clash))
        seen[b[1]:b[3], b[0]:b[2]] |= m
        upd = np.where(m, np.clip(new_a * 255.0, 0, 255).round(), sub)
        total += int((upd != sub).sum())
        atlas[b[1]:b[3], b[0]:b[2], 3] = upd.astype(np.uint8)
        if n.replace(PREFIX, "") in ("ch_01_miya", "ch_02_kai"):
            tiles.append((n, img.copy()))

    print("điểm alpha đổi: %s" % format(total, ","))

    new_img = Image.fromarray(atlas, "RGBA")

    def as_seen(src, b, w=300):
        arr = np.array(src.crop((b[0], b[1], b[0] + w, b[1] + 35))).astype(np.float32)
        q = (arr + np.roll(arr, -1, 1) + np.roll(arr, -1, 0)
             + np.roll(np.roll(arr, -1, 0), -1, 1)) / 4.0
        al = q[:, :, 3:4] / 255.0
        px = q[:, :, :3] * al + np.array(PILL, np.float32) * (1 - al)
        return Image.fromarray(px.round().astype(np.uint8), "RGB")

    old_img = c.tex_image(key)
    sheet_src = []
    for short in ("MOVIE", "ch_01_miya", "ch_02_kai"):
        b = c.sprite(PREFIX + short).box()
        sheet_src.append(as_seen(old_img, b))
        sheet_src.append(as_seen(new_img, b))
    S = 3
    sheet = Image.new("RGB", (300 * S, sum(t.height for t in sheet_src) * S + 4 * len(sheet_src)), PILL)
    y = 0
    for t in sheet_src:
        sheet.paste(t.resize((t.width * S, t.height * S), Image.NEAREST), (0, y))
        y += t.height * S + 4
    sheet.save(PREVIEW)
    print("ảnh đối chiếu (MOVIE / miya trước-sau / kai trước-sau) -> %s" % PREVIEW)
    _ = tiles, gauge

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    c._imgs[key] = new_img
    c.dirty_tex.add(key)
    if not os.path.exists(BACKUP):
        shutil.copy2(TARGET, BACKUP)
        print("\nbackup -> %s" % BACKUP)
    n = c.save(TARGET)
    print("đã ghi %s (%s byte)" % (TARGET, format(n, ",")))

    show(weigh(Container(TARGET)), "SAU (đọc lại từ disk)")


if __name__ == "__main__":
    main()
