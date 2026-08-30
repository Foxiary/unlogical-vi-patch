"""Sửa nghĩa dòng 2 của thẻ báo xác thực thành công (`UL_pass_c_frame_acce`).

    JP    アクセス権を確認しました。          (đã xác nhận xong)
    cũ    ĐANG KIỂM TRA QUYỀN TRUY CẬP…      (đang diễn ra — sai thì)
    mới   ĐÃ XÁC NHẬN QUYỀN TRUY CẬP.

Ba dòng của thẻ này là **tranh vẽ sẵn**, nên "dịch lại" nghĩa là vẽ lại pixel. Font
dùng để vẽ tranh mod **không có trên máy** — quét toàn bộ 383 font (`C:\\Windows\\Fonts`,
font người dùng, 7 font nhúng trong bundle) chỉ ra IoU cao nhất 0,78 trên chữ `TRUY`
và 0,76 trên từng chữ cái rời, tức không phải font nào trong số đó. Nên script
**không render chữ**: nó **cắt dán chính nét chữ đã có** trong cùng tấm tranh.

Chữ cần / nguồn (toạ độ trong ô atlas 755×320 của `UL_pass_c_frame_acce`):

| cụm | lấy từ | x |
|---|---|---|
| `ĐA` | dòng 2, `ĐANG` | 117–159 |
| `XÁC` | dòng 1, `XÁC NHẬN…` | 115–175 |
| `NHẬN` | dòng 1 | 191–272 |
| `QUYỀN` | dòng 2 | 378–476 |
| `TRUY` | dòng 2 | 491–572 |
| `CẬP.` | dòng 2, `CẬP…` — lấy tới **dấu chấm đầu** của dấu ba chấm | 588–655 |

Chỉ thiếu đúng một chữ: **dấu ngã của `Ã`**. Cả tấm không có `Ã` nào; nguồn duy nhất
là `UL_pass_a_frame_moji` (`XIN HÃY NHẬP MẬT KHẨU`) — cùng font nhưng cao chữ hoa 22
px thay vì 27, nên dấu ngã được phóng đúng tỉ lệ 27/22 rồi dán lên chữ `A`.

Hình học đo từ chính ba dòng gốc: bước chữ 21 px (chữ `M` 28, `I` và `.` hẹp hơn),
khe giữa hai từ 15–16 px tuỳ cặp chữ, tâm dòng x=393 (cả ba dòng đều vậy), đỉnh chữ
hoa y=216. Dải xoá là y 198–252: đúng hai hàng 198 và 252 có alpha bằng 0 trên toàn
chiều ngang, nên xoá trong đó không chạm dấu của dòng 1 và dòng 3.

    python tools\\fix_password_access_line.py            # xuất PNG xem trước
    python tools\\fix_password_access_line.py --check     # thoát 1 nếu chưa vá
    python tools\\fix_password_access_line.py --apply     # backup + vá vào romfs

Backup: `_backup\\sharedassets16.assets.preaccessline`
"""

import os
import shutil
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import UnityPy
from keyart import Container

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROMFS = os.path.join(ROOT, "romfs", "Data", "sharedassets16.assets")
BACKUP = os.path.join(ROOT, "_backup", "sharedassets16.assets.preaccessline")
OUT = os.path.join(os.environ.get("TEMP", "."), "unlogical_passline")

CARD = "UL_pass_c_frame_acce"
PROMPT = "UL_pass_a_frame_moji"
N_OBJECTS = 13

BAND = (198, 252)          # dải xoá, cả hai mép đều alpha = 0
CAP_TOP = 216              # đỉnh chữ hoa của dòng 2
CENTRE = 393               # tâm ngang của cả ba dòng
LINE1_DY = 54              # dòng 1 (đỉnh 162) -> dòng 2 (đỉnh 216)
MARGIN = 6                 # lề cắt, nhỏ hơn nửa khe giữa hai từ (15) nên không chạm nhau

# (nhãn, hàng cắt, x mực trái, x mực phải, lề phải, dời dọc)
PIECES = [
    # `N` của `ĐANG` bắt đầu ngay ở 162, nên lề phải chỉ được 1 px
    ("ĐA",    (199, 252), 117, 159, 1, 0),
    ("XÁC",   (148, 198), 115, 175, MARGIN, LINE1_DY),
    ("NHẬN",  (148, 198), 191, 272, MARGIN, LINE1_DY),
    ("QUYỀN", (199, 252), 378, 476, MARGIN, 0),
    ("TRUY",  (199, 252), 491, 572, MARGIN, 0),
    # dấu chấm thứ hai của `…` bắt đầu ở 658; cắt ở 656 để không kéo theo nó
    ("CẬP.",  (199, 252), 588, 655, 1, 0),
]
GAPS = [16, 16, 16, 15, 16]        # khe trước từ thứ 2..6, đo theo đúng cặp chữ

TILDE_SRC = (0, 11, 183, 202)      # dấu ngã trong UL_pass_a_frame_moji
MOJI_CAP = 22                      # cao chữ hoa của tấm đó
CARD_CAP = 27                      # cao chữ hoa của thẻ này
TILDE_BASE = CAP_TOP - 2           # đáy mực dấu ngã, giữ đúng khe 1 hàng như bản 22 px
CONTRAST = 3.0                     # kéo lại độ sắc sau khi phóng, xem scale_glyph()

DONE_TEXT = "ĐÃ XÁC NHẬN QUYỀN TRUY CẬP."


def vis(rgba):
    """Mực nhìn thấy = RGB nhân alpha. Alpha một mình là viền đen, béo gấp đôi."""
    a = rgba.astype(float)
    return a[..., :3].mean(axis=2) * a[..., 3] / 255.0


def ink_box(mask):
    ys, xs = np.where(mask)
    return xs.min(), xs.max(), ys.min(), ys.max()


def scale_glyph(tile, scale, contrast=CONTRAST):
    """Phóng một chữ rời, phóng riêng mực trắng và viền đen rồi ghép lại.

    Phóng thẳng RGBA cho ra nét nhoè hơn hẳn mấy chữ bên cạnh (Lanczos rải mép 1 px
    thành ~3 px). Tách hai lớp — `I` là mực nhìn thấy, `O` là alpha tức mực + viền —
    phóng từng lớp rồi kéo tương phản quanh 0,5 để mép co lại còn ~1 px, sau đó dựng
    lại RGB từ `I/O` để tích `RGB x alpha` vẫn đúng bằng mực gốc.
    """
    h = int(round(tile.shape[0] * scale))
    w = int(round(tile.shape[1] * scale))

    def layer(m):
        big = Image.fromarray((m * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)
        return np.clip((np.asarray(big, float) / 255 - 0.5) * contrast + 0.5, 0, 1)

    ink = layer(tile[..., :3].mean(axis=2) * tile[..., 3] / 255.0 / 255.0)
    out = np.maximum(layer(tile[..., 3] / 255.0), ink)
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[..., :3] = (np.where(out > 0.01, np.clip(ink / np.maximum(out, 1e-6), 0, 1), 1.0)
                     * 255).round()[..., None]
    rgba[..., 3] = (out * 255).round()
    return rgba


def already_patched(card):
    """Dòng 2 đã vá thì mực chỉ còn ~514 px bề ngang thay vì 553."""
    v = vis(card)[BAND[0]:BAND[1] + 1]
    xs = np.where((v >= 100).any(axis=0))[0]
    return int(xs.max() - xs.min() + 1)


def build_band(card, prompt):
    """Dựng dải mới trong một lớp RGBA rỗng, cùng kích thước ô sprite."""
    h, w = card.shape[:2]
    band = np.zeros((h, w, 4), np.uint8)
    band[..., :3] = 255                      # nền trong suốt của tranh gốc là TRẮNG
    band[..., 3] = 0

    widths = [r - l + 1 for _, _, l, r, _, _ in PIECES]
    total = sum(widths) + sum(GAPS)
    x = int(round(CENTRE - total / 2.0))
    print(f"  bề ngang mới {total} px (cũ 553), mực bắt đầu x={x}, tâm {CENTRE}")

    placed = {}
    for i, (label, (y0, y1), left, right, mright, dy) in enumerate(PIECES):
        if i:
            x += GAPS[i - 1]
        cut = card[y0:y1 + 1, left - MARGIN:right + mright + 1]
        ty0 = y0 + dy
        tx0 = x - MARGIN
        band[ty0:ty0 + cut.shape[0], tx0:tx0 + cut.shape[1]] = cut
        placed[label] = (x, x + widths[i] - 1)
        print(f"  {label:6s} x{left}..{right} -> {x}..{x + widths[i] - 1}"
              + (f"  (dời dọc +{dy})" if dy else ""))
        x += widths[i]

    # --- dấu ngã: phóng từ tấm UL_pass_a_frame_moji ---------------------------
    y0, y1, x0, x1 = TILDE_SRC
    tile = prompt[y0:y1, x0:x1].astype(float)
    scale = CARD_CAP / MOJI_CAP
    big = scale_glyph(tile, scale)
    bl, br, bt, bb = ink_box(vis(big) >= 100)

    a_left, a_right = placed["ĐA"][0] + (141 - 117), placed["ĐA"][0] + (159 - 117)
    cx = (a_left + a_right) / 2.0
    ox = int(round(cx - (bl + br) / 2.0))
    oy = TILDE_BASE - bb
    print(f"  dấu ngã: {tile.shape[1]}x{tile.shape[0]} -> {big.shape[1]}x{big.shape[0]}"
          f" (x{scale:.3f}), mực {br - bl + 1}x{bb - bt + 1} tại x{ox + bl}..{ox + br},"
          f" y{oy + bt}..{oy + bb}")

    # dán ưu tiên alpha: chỗ dấu ngã đục hơn thì thắng, chỗ trống giữ nguyên nền
    dst = band[oy:oy + big.shape[0], ox:ox + big.shape[1]]
    take = big[..., 3] > dst[..., 3]
    dst[take] = big[take]
    return band


def main(argv):
    check_only = "--check" in argv
    apply_it = "--apply" in argv
    os.makedirs(OUT, exist_ok=True)

    c = Container(ROMFS)
    card_slot = c.sprite(CARD)
    card = np.array(card_slot.crop())
    prompt = np.array(c.sprite(PROMPT).crop())

    width_now = already_patched(card)
    if width_now < 540:
        print(f"đã vá rồi: dòng 2 rộng {width_now} px  ->  {DONE_TEXT}")
        return 0
    print(f"chưa vá: dòng 2 rộng {width_now} px (ĐANG KIỂM TRA QUYỀN TRUY CẬP…)")
    if check_only:
        return 1

    edge = max(int(card[BAND[0], :, 3].max()), int(card[BAND[1], :, 3].max()))
    assert edge < 8, f"mép dải xoá còn alpha {edge} — dấu của dòng 1/3 sẽ bị cắt"

    band = build_band(card, prompt)
    out = card.copy()
    out[BAND[0]:BAND[1] + 1] = band[BAND[0]:BAND[1] + 1]

    sheet = Image.new("RGB", (card.shape[1], card.shape[0] * 2 + 12), (40, 40, 40))
    for i, layer in enumerate((card, out)):
        bg = Image.new("RGBA", (layer.shape[1], layer.shape[0]), (0, 0, 0, 255))
        bg.alpha_composite(Image.fromarray(layer))
        sheet.paste(bg.convert("RGB"), (0, i * (layer.shape[0] + 12)))
    sheet.save(os.path.join(OUT, "before_after.png"))
    print(f"  ảnh so sánh -> {os.path.join(OUT, 'before_after.png')}")

    if not apply_it:
        print("  chạy thử xong. Thêm --apply để vá.")
        return 1

    if not os.path.exists(BACKUP):
        shutil.copy(ROMFS, BACKUP)
        print(f"  backup -> {BACKUP}")

    card_slot.paste(Image.fromarray(out))
    patched = os.path.join(OUT, "patched.assets")
    size = c.save(patched)

    check = UnityPy.load(patched)
    got = list(check.objects)
    empty = [o.path_id for o in got if o.byte_size == 0]
    if len(got) != N_OBJECTS or empty:
        raise SystemExit(f"HỎNG: {len(got)} object, {len(empty)} rỗng — không ghi")
    print(f"  kiểm tra bản vá: {len(got)} object, {size:,} byte")

    shutil.copy(patched, ROMFS)
    print(f"  đã ghi {ROMFS} ({os.path.getsize(ROMFS):,} byte)")

    # Đọc lại từ disk. Mã hoá lại ASTC đụng cả atlas, nên đo luôn thiệt hại
    # trên chín sprite KHÔNG sửa.
    after = Container(ROMFS)
    w = already_patched(np.array(after.sprite(CARD).crop()))
    print(f"  đọc lại: dòng 2 rộng {w} px")
    for name in sorted(after.sprite_names()):
        if name == CARD:
            continue
        a = np.array(c.sprite(name).crop()).astype(float)
        b = np.array(after.sprite(name).crop()).astype(float)
        mse = ((a - b) ** 2).mean()
        psnr = float("inf") if mse == 0 else 10 * np.log10(255 ** 2 / mse)
        print(f"    {name:34s} PSNR {psnr:6.1f} dB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
