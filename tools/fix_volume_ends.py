# -*- coding: utf-8 -*-
"""Đổi `小` / `大` ở hai đầu 23 dải thanh trượt tab SOUND thành `−` / `+`.

Mỗi dòng của tab SOUND là **một sprite dải ngang** (~1094x35) trong
`sharedassets7.assets`, atlas `sactx-0-2048x2048-ASTC 4x4-Option-546c882d`.
Sprite gộp cả ba thứ vào một tấm: nhãn ở mép trái, 10 vạch nghiêng ở giữa, và
hai chữ `小` / `大` ở hai đầu thang. Không có chuỗi ký tự nào.

Hình học đo từ chính tranh (phân đoạn theo màu tím, chỉ xét `x > 600` để không
đụng nhãn tên cũng vẽ màu tím ở mép trái — `SOICHI` và `HOTARU` dính đúng bẫy đó):

    小   x 627..653  (27 px)   |   大   x 1065..1091  (26 px)

> ### KHÔNG dùng `full_rect_mesh()` cho những sprite này
>
> Đã thử một lần và hỏng. Atlas xếp **sát nét**: `textureRect` của một dải rộng
> 1094 px nhưng nét thật chỉ chiếm vài mảng rời, và Unity **nhét sprite khác vào
> chỗ trống bên trong chính hình chữ nhật đó**. Mesh tight là thứ duy nhất giữ
> cho mỗi dải chỉ vẽ phần của mình. Phủ full-rect thì `X BUTTON`, `SKIP CHOICES`,
> `QUICK LOAD`, `B STICK` … hiện thẳng vào giữa hàng âm lượng.
>
> Nhưng mesh tight lại **không phủ hết ô chữ** — nó bám sát nét `小`/`大`, nên nét
> `−`/`+` mới vẽ ra sẽ bị xén thành từng mảnh. Cách đúng: **nối thêm đúng hai
> quad** phủ hai ô chữ, giữ nguyên toàn bộ mesh cũ.

Mesh gốc vốn đã là một tập quad thẳng trục (`indexCount = 6 * số quad`, thứ tự
`0,1,2, 0,2,3`), và **UV trong dữ liệu gốc toàn số 0** — Unity tự suy UV từ
`textureRect`, không đọc UV của mesh. Nên quad nối thêm cũng để UV 0 cho khớp.

Đổi từ pixel của ô cắt sang toạ độ sprite (đã kiểm chứng số học trên
`ch_02_kai`: đỉnh dưới −0.18 và đỉnh trên 0.17 khớp đúng công thức):

    local_x = (textureRectOffset.x - m_Rect.width  * pivot.x + px) / m_PixelsToUnits
    local_y = (textureRectOffset.y - m_Rect.height * pivot.y + (H - py)) / m_PixelsToUnits

Hai luồng vertex nằm liền nhau trong `m_DataSize`: luồng 0 là float3 vị trí
(12 B/đỉnh), **đệm cho tròn 16 B**, rồi luồng 1 là float2 UV (8 B/đỉnh).

    python tools\\fix_volume_ends.py            # chạy thử, xuất ảnh đối chiếu
    python tools\\fix_volume_ends.py --apply    # backup, vá, ghi đè, kiểm lại

Backup: `_backup\\sharedassets7.assets.prevolends`.

> Tab GAME **không** đụng tới: cặp nhãn ở đó là `遅/速`, `薄/濃`, `中/大`,
> `既読/強制`, `ON/OFF` — chữ có nghĩa, `−/+` không diễn đạt được "chậm/nhanh"
> hay "nhạt/đậm". Việc đó phải vẽ chữ, tách thành đợt riêng.
>
> Nhãn tên nhân vật ở mép trái **đã là chữ Latin từ trước** (MIYABI, KAI, RAN,
> KOHAKU, SHINJU, HOTARU …) — đừng vẽ lại.
"""
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw          # noqa: E402

from keyart import Container              # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TARGET = os.path.join(ROOT, "romfs", "Data", "sharedassets7.assets")
BACKUP = os.path.join(ROOT, "_backup", "sharedassets7.assets.prevolends")
PREVIEW = os.path.join(HERE, "volume_ends_preview.png")

PREFIX = "UL_option_sound_menu_"
N_STRIPS = 23
SEARCH_FROM = 600          # bỏ qua nhãn tên ở mép trái
MIN_RUN = 4                # cột tím liên tiếp tối thiểu để tính là nét
MERGE_GAP = 8              # khe giữa các nét của cùng một chữ (小 có 2 khe)
PAD = 1                    # nới ô chữ ra 1 px cho chắc khi phủ quad
SS = 4                     # hệ số siêu lấy mẫu

BAR_LEN = 22.0             # bề ngang nét `−` và nhánh của `+`
BAR_THICK = 3.0            # khớp nét ngang của `大`

APPLY = "--apply" in sys.argv


# ---------------------------------------------------------------- phân đoạn
def is_purple(px):
    r, g, b, a = px
    return a > 100 and b > r > g and (b - g) > 40 and r > 90


def glyph_boxes(img):
    """Hai hộp chữ ở nửa phải của dải, đo bằng phân đoạn màu."""
    W, H = img.size
    px = img.load()
    cols = [any(is_purple(px[x, y]) for y in range(H)) for x in range(W)]

    runs, start = [], None
    for x in range(SEARCH_FROM, W + 1):
        on = x < W and cols[x]
        if on and start is None:
            start = x
        elif not on and start is not None:
            if x - start >= MIN_RUN:
                runs.append([start, x])
            start = None

    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] <= MERGE_GAP:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))

    boxes = []
    for a, b in merged:
        ys = [y for y in range(H) for x in range(a, b) if is_purple(px[x, y])]
        boxes.append((max(0, a - PAD), max(0, min(ys) - PAD),
                      min(W, b + PAD), min(H, max(ys) + 1 + PAD)))
    return boxes


def ink_colour(img, box):
    """Màu đặc trưng của nét trong hộp."""
    px = img.load()
    hits = {}
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            p = px[x, y]
            if is_purple(p) and p[3] > 200:
                hits[p[:3]] = hits.get(p[:3], 0) + 1
    return max(hits, key=hits.get) if hits else (134, 81, 170)


def draw_sign(size, kind, colour):
    """`−` hoặc `+` vẽ ở độ phân giải SS lần rồi thu nhỏ cho mép mượt."""
    w, h = size
    big = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    cx, cy = w * SS / 2.0, h * SS / 2.0
    half_len, half_th = BAR_LEN * SS / 2.0, BAR_THICK * SS / 2.0
    d.rectangle([cx - half_len, cy - half_th, cx + half_len, cy + half_th],
                fill=colour + (255,))
    if kind == "+":
        d.rectangle([cx - half_th, cy - half_len, cx + half_th, cy + half_len],
                    fill=colour + (255,))
    return big.resize((w, h), Image.LANCZOS)


# ------------------------------------------------------------------- mesh
def add_quads(slot, boxes, crop_h):
    """Nối thêm một quad cho mỗi hộp, giữ nguyên mesh tight sẵn có."""
    tree = slot.tree
    rd = tree["m_RD"]
    vd = rd["m_VertexData"]
    n = vd["m_VertexCount"]
    data = bytes(vd["m_DataSize"])

    s0_len = 12 * n
    pad = (-s0_len) % 16
    stream0 = data[:s0_len]
    stream1 = data[s0_len + pad:s0_len + pad + 8 * n]
    if len(stream1) != 8 * n:
        raise SystemExit("%s: bố cục vertex lạ (len=%d, n=%d)" % (slot.name, len(data), n))

    p2u = tree["m_PixelsToUnits"]
    mr, pv = tree["m_Rect"], tree["m_Pivot"]
    off = slot.rd["textureRectOffset"]
    base_x = off["x"] - mr["width"] * pv["x"]
    base_y = off["y"] - mr["height"] * pv["y"]

    new_pos = b""
    idx = list(rd["m_IndexBuffer"])
    added = 0
    for (l, t, r, b) in boxes:
        x0, x1 = (base_x + l) / p2u, (base_x + r) / p2u
        y0, y1 = (base_y + crop_h - b) / p2u, (base_y + crop_h - t) / p2u
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):   # BL BR TR TL
            new_pos += struct.pack("<fff", x, y, 0.0)
        v = n + added
        for i in (v, v + 1, v + 2, v, v + 2, v + 3):
            idx += [i & 0xFF, (i >> 8) & 0xFF]
        added += 4

    new_n = n + added
    new_pad = (-12 * new_n) % 16
    vd["m_VertexCount"] = new_n
    vd["m_DataSize"] = stream0 + new_pos + b"\x00" * new_pad + stream1 + b"\x00" * (8 * added)
    rd["m_IndexBuffer"] = idx

    sm = rd["m_SubMeshes"][0]
    sm["indexCount"] += 6 * len(boxes)
    sm["vertexCount"] = new_n
    slot.c.dirty_sprites[(id(slot.file), slot.path_id)] = (slot.obj, tree)


# ------------------------------------------------------------------- chính
def plan(c):
    out = []
    names = sorted(n for n in c.sprite_names() if n.startswith(PREFIX))
    if len(names) != N_STRIPS:
        raise SystemExit("mong đợi %d dải, thấy %d — dừng" % (N_STRIPS, len(names)))
    for name in names:
        s = c.sprite(name)
        img = s.crop()
        boxes = glyph_boxes(img)
        if len(boxes) != 2:
            raise SystemExit("%s: thấy %d hộp chữ (mong đợi 2): %s" % (name, len(boxes), boxes))
        if boxes[0][2] >= boxes[1][0]:
            raise SystemExit("%s: hai hộp chồng nhau: %s" % (name, boxes))
        out.append((s, img, boxes))
    return out


def main():
    c = Container(TARGET)
    work = plan(c)
    print("dải tab SOUND: %d" % len(work))

    previews = []
    for s, img, boxes in work:
        before = img.copy()
        for box, kind in zip(boxes, ("-", "+")):
            colour = ink_colour(img, box)
            w, h = box[2] - box[0], box[3] - box[1]
            img.paste((0, 0, 0, 0), box)                 # xoá hẳn, kể cả alpha
            img.alpha_composite(draw_sign((w, h), kind, colour), (box[0], box[1]))
        print("   %-34s 小 %-22s 大 %-22s verts %d -> %d"
              % (s.name, boxes[0], boxes[1], s.vertex_count(), s.vertex_count() + 8))
        previews.append((before, img.copy()))
        if APPLY:
            s.paste(img)
            add_quads(s, boxes, img.size[1])

    tiles = []
    for b, a in previews[:6]:
        tiles += [b.crop((600, 0, b.width, b.height)), a.crop((600, 0, a.width, a.height))]
    sheet = Image.new("RGBA", (max(t.width for t in tiles) + 8,
                               sum(t.height + 4 for t in tiles) + 4), (20, 20, 28, 255))
    y = 4
    for t in tiles:
        sheet.paste(t, (4, y), t)
        y += t.height + 4
    sheet.save(PREVIEW)
    print("\nảnh đối chiếu (trước/sau xen kẽ) -> %s" % PREVIEW)

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(TARGET, BACKUP)
        print("backup -> %s" % BACKUP)
    n = c.save(TARGET)
    print("đã ghi %s (%s byte)" % (TARGET, format(n, ",")))


if __name__ == "__main__":
    main()
