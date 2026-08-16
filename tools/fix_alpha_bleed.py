# -*- coding: utf-8 -*-
"""Trả lại **loang màu** cho vùng trong suốt của atlas `sharedassets7.assets`.

## Triệu chứng

Trên tab SOUND của màn OPTION, nhãn tên nhân vật do mod vẽ lại (`MIYABI`, `KAI`,
`RAN` …) trông **mảnh hơn** nhãn gốc (`SE`, `VOICE`) chừng một cấp weight, dù
cùng typeface và cùng chiều cao chữ hoa 25 px.

Không phải font. Đo thân chữ `I` — chữ có mặt trong cả `VOICE`, `MIYABI`, `KAI`
nên so được một-đối-một, tính cả phủ khử răng cưa:

                        trong atlas      trên màn hình
    VOICE   (gốc)         3.75 px          3.77 px      <- đi qua nguyên vẹn
    MIYABI  (mod)    4.02 / 3.82 px   3.04 / 2.79 px    <- rụng ~1 px
    KAI     (mod)         3.82 px          2.96 px

Tranh mod vẽ **đủ dày**; nó rụng nét trên đường từ atlas ra màn hình.

## Nguyên nhân

Nhà phát hành trải màu mực ra **khắp** nền trong suốt. Dải `雅火` gốc giữ RGB
`255,148,190` ở mọi điểm, kể cả điểm `alpha = 0`. Tranh mod thì để RGB `0,0,0`
sát ngay cạnh nét, và chính điểm khử răng cưa cũng mang RGB đã bị kéo tối:

    ch_01_miya   x=  38        39          40..42        43
       RGB      0,0,0     80,46,60    255,148,191   245,142,184
       A            0           25            255           235

Hai chỗ nền đen lọt vào nét:

1. **ASTC 4×4** để RGB và alpha chung một khối, nên nền đen kéo tối RGB của điểm
   viền nằm cùng khối — thấy ngay trong atlas: `A=25` mà RGB chỉ còn `80,46,60`.
2. **GPU lấy mẫu song tuyến.** Texel trong suốt mang RGB `0,0,0` vẫn được tính
   vào phép nội suy (alpha không premultiply), nên viền pha về phía đen.

Chỗ (2) là chỗ ăn hết phần nét. Mô phỏng lại đúng phép nội suy — trung bình 2×2
texel rồi ghép lên nền tím — tái tạo lại y hệt số đo trên màn:

                    texel   song tuyến   đo trên màn
    VOICE            3.75         3.75          3.77   <- miễn nhiễm, RGB đã loang
    ch_01_miya       3.82         3.03          3.04
    ch_02_kai        3.31         2.96          2.96

Nên trên màn, điểm viền pha về phía **đen** thay vì về phía hồng — kênh blue tụt
còn 117, thấp hơn cả nền (169) lẫn mực (191). Mắt không tính viền đó vào thân
chữ nữa, nét mỏng đi ~1 px.

Vì mô phỏng khớp tới hai chữ số thập phân nên kiểm tra được **không cần chạy
game**: `report()` đo cả hai cột, cột "song tuyến" chính là cái mắt nhìn thấy.

18/23 dải tab SOUND dính lỗi; tỉ lệ điểm viền hỏng 4% (gốc) → 50% (mod). Năm
dải sạch (`BGM`, `MOVIE`, `SE`, `VOICE`, `ch_17_unkn`) đúng là năm dải chưa vẽ
lại. `VOICE` báo 19% là **dương tính giả** — thước đo quét cả nửa trái ô sprite
nên vớ phải `UL_option_keycon_button_X` xếp chèn ngay trong đó.

## Cách sửa

Giãn màu từ điểm đục gần nhất ra mọi điểm chưa đục, **giữ nguyên kênh alpha**.
Đúng quy ước của tranh gốc. Hình dạng, vị trí, cỡ chữ không đổi — chỉ trả lại
màu cho phần viền, nên không cần vẽ lại chữ và không đụng tới mesh.

Vá cả texture atlas chứ không riêng 23 dải SOUND: mọi sprite mod vẽ lại trong
cùng file (dải phím Ⓐ/Ⓑ, hai đầu thang `−`/`+` …) đều dính cùng một lỗi.

    python tools\\fix_alpha_bleed.py            # chạy thử, in số đo
    python tools\\fix_alpha_bleed.py --apply    # backup, vá, ghi, đọc lại kiểm

Backup: `_backup\\sharedassets7.assets.prebleed`.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np                        # noqa: E402
from PIL import Image                     # noqa: E402

from keyart import Container              # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TARGET = os.path.join(ROOT, "romfs", "Data", "sharedassets7.assets")
BACKUP = os.path.join(ROOT, "_backup", "sharedassets7.assets.prebleed")
PREVIEW = os.path.join(HERE, "alpha_bleed_preview.png")

SOLID = 250        # alpha >= mức này thì coi là điểm đục, làm nguồn màu
RADIUS = 4         # số vòng giãn. Song tuyến chỉ chạm texel kề (1), khối ASTC
                   # rộng 4 px (3). Để rộng hơn là **có hại**: atlas xếp sát nét
                   # nên nét mảnh của sprite hàng xóm sẽ bị hút mất màu — thấy rõ
                   # ở `X BUTTON` nằm chèn trong ô của `VOICE` khi thử bán kính 12.
PILL = (134, 80, 169)      # màu nền ô nhãn, để dựng thử cảnh ghép

PREFIX = "UL_option_sound_menu_"
PROBE = [("VOICE", 66, 82), ("ch_01_miya", 34, 48), ("ch_02_kai", 62, 76)]

APPLY = "--apply" in sys.argv


# ------------------------------------------------------------------ giãn màu
def bleed(rgba):
    """RGB của mọi điểm chưa đục := RGB điểm đục gần nhất. Alpha giữ nguyên."""
    a = rgba[:, :, 3]
    rgb = rgba[:, :, :3].astype(np.int16)
    known = a >= SOLID
    out = np.where(known[:, :, None], rgb, 0).astype(np.int16)
    have = known.copy()

    for _ in range(RADIUS):
        if have.all():
            break
        acc = np.zeros(out.shape, np.int32)
        cnt = np.zeros(have.shape, np.int32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                sv = np.roll(np.roll(have, dy, 0), dx, 1)
                so = np.roll(np.roll(out, dy, 0), dx, 1)
                if dy > 0:
                    sv[:dy] = False
                elif dy < 0:
                    sv[dy:] = False
                if dx > 0:
                    sv[:, :dx] = False
                elif dx < 0:
                    sv[:, dx:] = False
                acc += np.where(sv[:, :, None], so, 0)
                cnt += sv
        fill = (~have) & (cnt > 0)
        if not fill.any():
            break
        avg = np.zeros_like(out)
        nz = cnt > 0
        avg[nz] = (acc[nz] / cnt[nz][:, None]).round()
        out = np.where(fill[:, :, None], avg, out)
        have |= fill

    res = rgba.copy()
    res[:, :, :3] = np.where(known[:, :, None], rgb, out).astype(np.uint8)
    return res, int((~known).sum()), int(have.sum() - known.sum())


# -------------------------------------------------------------------- đo đạc
def bilinear_half(arr):
    """Trung bình 2x2 texel — đúng phép nội suy khi lệch nửa texel."""
    a = arr.astype(np.float32)
    return (a + np.roll(a, -1, 1) + np.roll(a, -1, 0)
            + np.roll(np.roll(a, -1, 0), -1, 1)) / 4.0


def stem_at(arr, xa, xb):
    """Bề ngang thân đứng trong dải cột [xa, xb), sau khi ghép lên nền ô nhãn.

    `arr` là float RGBA. Đo bằng phủ chiếu lên trục nền->mực, nên không phụ
    thuộc chữ trắng hay chữ màu."""
    al = arr[:, :, 3:4] / 255.0
    bg = np.array(PILL, np.float32)
    out = arr[:, :, :3] * al + bg * (1 - al)
    band = out[:, xa:xb].reshape(-1, 3)      # chỉ dải cột đang đo — quét cả
    ink = band[((band - bg) ** 2).sum(1).argmax()]   # sprite sẽ vớ phải hàng xóm
    v = ink - bg
    vv = float((v * v).sum()) or 1.0
    cov = np.clip(((out - bg) * v).sum(2) / vv, 0, 1)[:, xa:xb]
    rows = np.where(cov.max(1) >= 0.5)[0]
    if not len(rows):
        return 0.0, tuple(int(t) for t in ink)
    per = np.sort(cov[rows].sum(1))
    return float(per[len(per) // 2]), tuple(int(t) for t in ink)


def bad_edge_pct(img):
    """% điểm khử răng cưa có RGB tối hơn hẳn màu mực -> sẽ pha ra viền tối."""
    W, H = img.size
    W = min(W, 600)
    px = img.load()
    solid = [(x, y) for y in range(H) for x in range(W) if px[x, y][3] >= SOLID]
    if not solid:
        return None
    med = lambda i: sorted(px[x, y][i] for x, y in solid)[len(solid) // 2]
    ink = (med(0), med(1), med(2))
    lum_ink = 0.299 * ink[0] + 0.587 * ink[1] + 0.114 * ink[2]
    edge = bad = 0
    for y in range(H):
        for x in range(W):
            p = px[x, y]
            if not (20 <= p[3] < SOLID):
                continue
            edge += 1
            if 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] < lum_ink * 0.75:
                bad += 1
    return 100.0 * bad / edge if edge else 0.0


def report(path, tag):
    c = Container(path)
    print("\n--- %s ---" % tag)
    print("%-14s %-18s %7s %11s %10s" % ("dải", "mực", "texel", "song tuyến", "viền hỏng"))
    for short, xa, xb in PROBE:
        img = c.sprite(PREFIX + short).crop()
        arr = np.array(img)
        raw, ink = stem_at(arr.astype(np.float32), xa, xb)
        bil, _ = stem_at(bilinear_half(arr), xa, xb)
        print("%-14s %-18s %7.2f %11.2f %9.0f%%"
              % (short, str(ink), raw, bil, bad_edge_pct(img)))
    pcts = []
    for n in sorted(x for x in c.sprite_names() if x.startswith(PREFIX)):
        p = bad_edge_pct(c.sprite(n).crop())
        if p is not None:
            pcts.append(p)
    print("23 dải SOUND: viền hỏng trung bình %.0f%%, số dải >20%%: %d"
          % (sum(pcts) / len(pcts), sum(1 for p in pcts if p > 20)))
    return c


# --------------------------------------------------------------------- chính
def main():
    c = report(TARGET, "TRƯỚC")

    tex = [o for o in c.objects if o.type.name == "Texture2D"
           and o.read().m_Width >= 512]
    if len(tex) != 1:
        raise SystemExit("mong đợi 1 texture atlas, thấy %d" % len(tex))
    obj = tex[0]
    key = (id(obj.assets_file), obj.path_id)
    img = c.tex_image(key)
    print("\natlas %s  %dx%d" % (obj.read().m_Name, img.width, img.height))

    arr = np.array(img)
    fixed, n_open, n_filled = bleed(arr)
    changed = int((arr[:, :, :3] != fixed[:, :, :3]).any(axis=2).sum())
    print("điểm chưa đục: %s | được cấp màu: %s | RGB đổi: %s | alpha đổi: %d"
          % (format(n_open, ","), format(n_filled, ","), format(changed, ","),
             int((arr[:, :, 3] != fixed[:, :, 3]).sum())))

    new = Image.fromarray(fixed, "RGBA")

    # ảnh đối chiếu: dựng đúng như GPU (song tuyến) rồi ghép lên nền ô nhãn
    def as_seen(src, b, w=320, h=35):
        a = bilinear_half(np.array(src.crop((b[0], b[1], b[0] + w, b[1] + h))))
        al = a[:, :, 3:4] / 255.0
        px = a[:, :, :3] * al + np.array(PILL, np.float32) * (1 - al)
        return Image.fromarray(px.round().astype(np.uint8), "RGB")

    tiles = []
    for short in ("VOICE", "ch_01_miya", "ch_02_kai"):
        b = c.sprite(PREFIX + short).box()
        tiles += [as_seen(img, b), as_seen(new, b)]
    S = 3
    sheet = Image.new("RGB", (320 * S, sum(t.height for t in tiles) * S + 4 * len(tiles)), PILL)
    y = 0
    for t in tiles:
        sheet.paste(t.resize((t.width * S, t.height * S), Image.NEAREST), (0, y))
        y += t.height * S + 4
    sheet.save(PREVIEW)
    print("ảnh đối chiếu (mỗi cặp: trước / sau) -> %s" % PREVIEW)

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    c._imgs[key] = new
    c.dirty_tex.add(key)
    if not os.path.exists(BACKUP):
        shutil.copy2(TARGET, BACKUP)
        print("\nbackup -> %s" % BACKUP)
    n = c.save(TARGET)
    print("đã ghi %s (%s byte)" % (TARGET, format(n, ",")))

    report(TARGET, "SAU (đọc lại từ disk)")


if __name__ == "__main__":
    main()
