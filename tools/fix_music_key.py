"""Dịch bảng phím tắt màn MUSIC (sprite UL_music_key trong sharedassets13.assets).

Bốn dòng gợi ý phím ở góc dưới bên phải màn MUSIC là **tranh vẽ sẵn** nằm trong
atlas `sactx-0-1024x2048-ASTC 4x4-Music-594a0ae0`, không phải chuỗi, nên tìm chữ
trong romfs hay global-metadata.dat đều không ra.

    Ⓐ 再生/停止   Ⓑ 戻る        ->   Ⓐ Play/Stop   Ⓑ Back
    Ⓨ 一時停止    Ⓧ モード切替   ->   Ⓨ Pause       Ⓧ Mode

Sprite này **tight-mesh** (116 đỉnh / 106 tam giác ôm sát nét chữ Nhật), nên chỉ
vẽ lại pixel là trong game chữ sẽ thủng lỗ chỗ. Script dựng lại mesh thành một
quad phủ kín ô, lấy mẫu từ `UL_music_bg_base_02` (pid 61) cùng file.

    python tools/fix_music_key.py            # chạy thử, xuất PNG xem trước
    python tools/fix_music_key.py --apply    # backup + vá vào romfs

Backup: _backup/sharedassets13.assets.premusickey
"""

import os
import shutil
import struct
import sys

import numpy as np
import UnityPy
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROMFS = os.path.join(ROOT, "romfs", "Data", "sharedassets13.assets")
BACKUP = os.path.join(ROOT, "_backup", "sharedassets13.assets.premusickey")
STOCK_RESS = r"D:\Downloads\UNLOGICAL_v2\Data\sharedassets13.assets.resS"
FONT = (r"C:\Users\ADMIN\AppData\Local\Temp\claude\d--Downloads-010068501ff9a000"
        r"\9d4f7fb5-9b6c-4487-a5b3-fbf1cbd6951d\scratchpad\fonts\font_BASE.ttf")
OUT = os.path.join(os.environ.get("TEMP", "."), "unlogical_musickey")

ATLAS_PID = 47
SPRITE_PID = 73
QUAD_TEMPLATE_PID = 61

# Ô của UL_music_key trong atlas, gốc dưới-trái theo Unity.
ATLAS_RECT = (300.0267333984375, 1384.0267333984375, 352.8970947265625, 75.94650268554688)

INK = (255, 210, 217, 255)      # hồng #FFD2D9, đo từ chính bản gốc
FONT_SIZE = 28
TEXT_GAP = 8                    # khoảng cách từ mép nút tròn tới chữ (bản gốc: 8)
COL1_X = 2                      # cột nút tròn thứ nhất (giữ nguyên bản gốc)
LABELS = [("Play/Stop", "Back"), ("Pause", "Mode")]


def unity_rect_to_pil(rect, tex_h):
    x, y, w, h = rect
    left = int(round(x))
    top = int(round(tex_h - y - h))
    return left, top, left + int(round(w)), top + int(round(h))


def ink_runs(mask):
    """Các đoạn liên tục có mực, trả về danh sách (đầu, cuối) đã gộp khe <= 3px."""
    runs, cur = [], None
    for i, v in enumerate(mask):
        if v and cur is None:
            cur = i
        elif not v and cur is not None:
            runs.append((cur, i - 1))
            cur = None
    if cur is not None:
        runs.append((cur, len(mask) - 1))
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] <= 3:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(r)
    return merged


def find_buttons(crop):
    """Cắt bốn nút tròn Ⓐ Ⓑ Ⓨ Ⓧ ra khỏi tranh gốc để dùng lại nguyên xi."""
    a = np.array(crop)[..., 3]
    h = a.shape[0]
    rows = ink_runs(a.max(axis=1) > 8)
    assert len(rows) == 2, f"cần đúng 2 dòng, thấy {rows}"
    out = []
    for y0, y1 in rows:
        band = a[y0:y1 + 1]
        cols = ink_runs(band.max(axis=0) > 8)
        # nút tròn là đoạn đầu của dòng và đoạn bắt đầu ở cột thứ hai (x ~ 180)
        first = cols[0]
        second = next(c for c in cols if c[0] >= 170)
        tiles = []
        for x0, x1 in (first, second):
            sub = a[:, x0:x1 + 1]
            ys = np.where(sub.max(axis=1) > 8)[0]
            ys = [y for y in ys if y0 <= y <= y1]
            tiles.append((crop.crop((x0, min(ys), x1 + 1, max(ys) + 1)), x0, min(ys)))
        out.append(tiles)
    assert h  # giữ tham chiếu
    return out


def build_art(crop):
    w, h = crop.size
    buttons = find_buttons(crop)
    font = ImageFont.truetype(FONT, FONT_SIZE)
    # căn chữ theo chiều cao chữ hoa để 'y' thòng xuống không kéo lệch dòng
    cap = font.getbbox("H", anchor="ls")
    cap_mid = (cap[1] + cap[3]) / 2.0

    col1_w = max(font.getlength(row[0]) for row in LABELS)
    col2_w = max(font.getlength(row[1]) for row in LABELS)
    btn_w = max(t[0].width for row in buttons for t in row)
    col2_x = COL1_X + btn_w + TEXT_GAP + int(round(col1_w)) + 15
    total = col2_x + btn_w + TEXT_GAP + col2_w
    print(f"  bố cục: cột1 {col1_w:.0f}px, cột2 {col2_w:.0f}px, nút {btn_w}px, "
          f"cột2 bắt đầu x={col2_x}, tổng {total:.0f}/{w}px")
    if total > w:
        raise SystemExit(f"TRÀN {total - w:.0f}px — giảm FONT_SIZE hoặc rút gọn nhãn")

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for (tile1, _, y1), (tile2, _, y2), labels in (
            (buttons[0][0], buttons[0][1], LABELS[0]),
            (buttons[1][0], buttons[1][1], LABELS[1])):
        img.paste(tile1, (COL1_X, y1), tile1)
        img.paste(tile2, (col2_x, y2), tile2)
        for tile, bx, by, text in ((tile1, COL1_X, y1, labels[0]),
                                   (tile2, col2_x, y2, labels[1])):
            centre = by + tile.height / 2.0
            draw.text((bx + tile.width + TEXT_GAP, centre - cap_mid), text,
                      font=font, fill=INK, anchor="ls")
    return img


def quad_bytes(sprite):
    """Bốn đỉnh phủ kín ô sprite: TL, TR, BL, BR — thứ tự của mẫu pid 61/57."""
    rect, rd = sprite.m_Rect, sprite.m_RD
    ppu = sprite.m_PixelsToUnits
    x0 = (rd.textureRectOffset.x - rect.width * sprite.m_Pivot.x) / ppu
    y0 = (rd.textureRectOffset.y - rect.height * sprite.m_Pivot.y) / ppu
    x1 = x0 + rd.textureRect.width / ppu
    y1 = y0 + rd.textureRect.height / ppu
    pos = struct.pack("<12f", x0, y1, 0.0, x1, y1, 0.0, x0, y0, 0.0, x1, y0, 0.0)
    return pos + b"\x00" * 32, struct.pack("<6H", 0, 1, 2, 2, 1, 3), (x0, y0, x1, y1)


def main(apply_it):
    os.makedirs(OUT, exist_ok=True)
    work = os.path.join(OUT, "sharedassets13.assets")
    shutil.copy(ROMFS, work)
    if not os.path.exists(work + ".resS"):
        shutil.copy(STOCK_RESS, work + ".resS")   # romfs không giữ .resS, Ryujinx tự rơi về bản gốc

    env = UnityPy.load(work)
    objs = {o.path_id: o for o in env.objects}
    tex = objs[ATLAS_PID].read()
    sprite = objs[SPRITE_PID].read()
    assert sprite.m_Name == "UL_music_key", sprite.m_Name

    atlas = tex.image
    box = unity_rect_to_pil(ATLAS_RECT, tex.m_Height)
    crop = atlas.crop(box)
    print(f"atlas {tex.m_Width}x{tex.m_Height}, ô {box}, sprite {crop.size}")
    crop.save(os.path.join(OUT, "before.png"))

    art = build_art(crop)
    art.save(os.path.join(OUT, "after.png"))

    new_atlas = atlas.copy()
    new_atlas.paste(art, box[:2])     # dán đè, không trộn: ô cũ bị xoá sạch
    new_atlas.save(os.path.join(OUT, "atlas_after.png"))

    verts, idx, corners = quad_bytes(sprite)
    old_v = sprite.m_RD.m_VertexData.m_VertexCount
    print(f"  mesh: {old_v} đỉnh / {len(sprite.m_RD.m_IndexBuffer) // 2} chỉ số"
          f" -> 4 đỉnh / 6 chỉ số, quad {tuple(round(c, 4) for c in corners)}")

    if not apply_it:
        print(f"\nchạy thử xong, xem {OUT}. Thêm --apply để vá.")
        return

    if not os.path.exists(BACKUP):
        shutil.copy(ROMFS, BACKUP)
        print(f"  backup -> {BACKUP}")

    tex.image = new_atlas
    tex.save()

    rd = sprite.m_RD
    rd.m_VertexData.m_VertexCount = 4
    rd.m_VertexData.m_DataSize = verts
    rd.m_IndexBuffer = idx
    rd.m_SubMeshes[0].indexCount = 6
    rd.m_SubMeshes[0].vertexCount = 4
    rd.m_SubMeshes[0].firstVertex = 0
    rd.m_SubMeshes[0].firstByte = 0
    sprite.save()

    # Serialize hết ra bộ nhớ TRƯỚC khi mở file để ghi. Mở "wb" thẳng lên chính
    # file đang load sẽ cắt trắng nó trước khi env.file.save() kịp đọc, và 106
    # object không đụng tới sẽ được ghi lại rỗng — file vẫn đủ 108 object nên
    # mọi kiểm tra hời hợt đều lọt.
    data = env.file.save()
    out = os.path.join(OUT, "patched.assets")
    with open(out, "wb") as fh:
        fh.write(data)

    check = UnityPy.load(out)
    got = list(check.objects)
    empty = [o.path_id for o in got if o.byte_size == 0]
    if len(got) != 108 or empty:
        raise SystemExit(f"HỎNG: {len(got)} object, {len(empty)} object rỗng {empty[:8]} — không ghi")
    print(f"  kiểm tra: {len(got)} object, tổng {sum(o.byte_size for o in got):,} byte, 0 object rỗng")

    shutil.copy(out, ROMFS)
    print(f"  đã ghi {ROMFS} ({os.path.getsize(ROMFS):,} byte)")


if __name__ == "__main__":
    main("--apply" in sys.argv)
