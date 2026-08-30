"""Màn PASSWORD thủng chữ — dựng lại mesh của 5 sprite trong `sharedassets16.assets`.

Màn nhập mật khẩu (`level16` = `Assets/Scene/Title.unity`) là **tranh vẽ sẵn**: cả
dòng nhắc lẫn hai bảng thông báo thành công/thất bại nằm trong atlas
`sactx-0-1024x2048-ASTC 4x4-PassWord-289d7772`. Tìm chuỗi trong `romfs`,
`global-metadata.dat` hay `SystemTextData` đều không ra.

Bản mod đã vẽ lại tiếng Việt (01/08/2026) nhưng **không dựng lại mesh**. Năm sprite
này tight-mesh — lưới ôm sát nét chữ Nhật gốc — nên nét mới nằm ngoài đường viền cũ
bị xén sạch. Trong game dòng nhắc hiện ra là

    ×N Ⱶ ÁY | HẬP N IT KHẨU        thay vì   XIN HÃY NHẬP MẬT KHẨU

Đúng cái bẫy đã gặp ở màn ARCHIVE và MUSIC (xem `keyart.full_rect_mesh`): vẽ lại
pixel thôi chưa đủ, phải thay lưới bằng một quad 4 đỉnh phủ kín ô atlas.

    python tools\fix_password_mesh.py            # soi, xuất PNG mô phỏng
    python tools\fix_password_mesh.py --check     # chỉ soi, có lỗi thì exit 1
    python tools\fix_password_mesh.py --apply     # backup + vá vào romfs

Backup: `_backup\sharedassets16.assets.premeshfix`

Script **không đụng tới texture** — atlas ASTC giữ nguyên byte, chỉ `m_RD` của
sprite bị viết lại. Mã hoá lại ASTC một lần nữa chỉ tổ mất chất lượng.
"""

import os
import shutil
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import UnityPy
from keyart import Container

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROMFS = os.path.join(ROOT, "romfs", "Data", "sharedassets16.assets")
BACKUP = os.path.join(ROOT, "_backup", "sharedassets16.assets.premeshfix")
STOCK = r"D:\Downloads\UNLOGICAL_v2\Data\sharedassets16.assets"
OUT = os.path.join(os.environ.get("TEMP", "."), "unlogical_passmesh")

N_OBJECTS = 13          # PreloadData + Texture2D + 10 Sprite + SpriteAtlas
ALPHA_INK = 128         # nét thật, không tính viền khử răng cưa của ASTC
SUPERSAMPLE = 4


def mesh_mask(sprite, size):
    """Ảnh xám: vùng mà lưới của sprite thực sự vẽ ra, toạ độ PIL của ô atlas."""
    w, h = size
    tree = sprite.tree
    rd = tree["m_RD"]
    vd = rd["m_VertexData"]
    data = bytes(vd["m_DataSize"])
    pos = [struct.unpack_from("<fff", data, i * 12)[:2] for i in range(vd["m_VertexCount"])]
    idx = bytes(rd["m_IndexBuffer"])
    tris = struct.unpack_from("<%dH" % (len(idx) // 2), idx, 0)

    p2u = tree["m_PixelsToUnits"]
    pivot, rect, off = tree["m_Pivot"], tree["m_Rect"], rd["textureRectOffset"]
    px = [(x * p2u + rect["width"] * pivot["x"] - off["x"],
           y * p2u + rect["height"] * pivot["y"] - off["y"]) for x, y in pos]

    s = SUPERSAMPLE
    mask = Image.new("L", (w * s, h * s), 0)
    draw = ImageDraw.Draw(mask)
    for i in range(0, len(tris), 3):
        draw.polygon([(px[tris[i + k]][0] * s, (h - px[tris[i + k]][1]) * s)
                      for k in range(3)], fill=255)
    return np.array(mask.resize((w, h), Image.BILINEAR))


def audit(container):
    """[(tên, sprite, số đỉnh, số pixel nét bị xén)] cho từng sprite của màn."""
    rows = []
    for name in sorted(container.sprite_names()):
        sprite = container.sprite(name)
        crop = sprite.crop()
        mask = mesh_mask(sprite, crop.size)
        alpha = np.array(crop)[..., 3]
        lost = int(((alpha >= ALPHA_INK) & (mask < 128)).sum())
        rows.append((name, sprite, sprite.vertex_count(), lost))
    return rows


def preview(container, rows):
    """Xuất PNG: nét gốc và nét sau khi bị lưới xén, để mắt người đối chiếu."""
    os.makedirs(OUT, exist_ok=True)
    for name, sprite, _, lost in rows:
        if not lost:
            continue
        crop = sprite.crop()
        mask = mesh_mask(sprite, crop.size)
        arr = np.array(crop)
        clipped = arr.copy()
        clipped[..., 3] = (arr[..., 3].astype(int) * mask // 255).astype("uint8")
        w, h = crop.size
        sheet = Image.new("RGB", (w, h * 2 + 12), (40, 40, 40))
        for i, layer in enumerate((arr, clipped)):
            bg = Image.new("RGBA", (w, h), (0, 0, 0, 255))
            bg.alpha_composite(Image.fromarray(layer))
            sheet.paste(bg.convert("RGB"), (0, i * (h + 12)))
        sheet.save(os.path.join(OUT, f"{name}.png"))
    print(f"  ảnh mô phỏng (trên: tranh trong atlas, dưới: game vẽ ra) -> {OUT}")


def main(argv):
    check_only = "--check" in argv
    apply_it = "--apply" in argv

    container = Container(ROMFS)
    rows = audit(container)
    broken = [r for r in rows if r[3]]

    print(f"{ROMFS}")
    for name, _, verts, lost in rows:
        flag = "  <-- XÉN MẤT NÉT" if lost else ""
        print(f"  {name:34s} {verts:4d} đỉnh   mất {lost:6d} px{flag}")

    if not broken:
        print("\nOK: không sprite nào bị lưới xén mất nét.")
        return 0

    print(f"\n{len(broken)} sprite bị xén, tổng {sum(r[3] for r in broken):,} px nét.")
    if check_only:
        return 1
    if not apply_it:
        preview(container, rows)
        print("  chạy thử xong. Thêm --apply để vá.")
        return 1

    if not os.path.exists(BACKUP):
        shutil.copy(ROMFS, BACKUP)
        print(f"  backup -> {BACKUP}")

    for name, sprite, verts, lost in broken:
        sprite.full_rect_mesh()
        print(f"  {name}: {verts} đỉnh -> 4 đỉnh (quad phủ kín ô)")

    os.makedirs(OUT, exist_ok=True)
    patched = os.path.join(OUT, "patched.assets")
    size = container.save(patched)

    # Serialize xong mới kiểm tra: env.file.save() từng ghi rỗng các object không
    # đụng tới khi mở nhầm file nguồn ở chế độ "wb" (xem fix_music_key.py).
    check = UnityPy.load(patched)
    got = list(check.objects)
    empty = [o.path_id for o in got if o.byte_size == 0]
    if len(got) != N_OBJECTS or empty:
        raise SystemExit(f"HỎNG: {len(got)} object, {len(empty)} rỗng {empty[:8]} — không ghi")
    tex = next(o.read_typetree() for o in got if o.type.name == "Texture2D")
    if len(tex["image data"]) != 1024 * 2048:
        raise SystemExit(f"HỎNG: atlas còn {len(tex['image data'])} byte — không ghi")
    print(f"  kiểm tra bản vá: {len(got)} object, {size:,} byte, atlas nguyên vẹn")

    shutil.copy(patched, ROMFS)
    print(f"  đã ghi {ROMFS} ({os.path.getsize(ROMFS):,} byte)")

    # Đọc lại từ disk, không tin giá trị trong bộ nhớ.
    again = [r for r in audit(Container(ROMFS)) if r[3]]
    if again:
        raise SystemExit(f"VẪN XÉN: {[r[0] for r in again]}")
    print("  đọc lại từ disk: 0 sprite bị xén.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
