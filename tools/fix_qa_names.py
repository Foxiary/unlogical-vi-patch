# -*- coding: utf-8 -*-
"""Dịch tên nhân vật trên dải tiêu đề màn Q&A.

Tên là **tranh vẽ**, không phải chuỗi: `Q&A_Front_Individual_01..05` trong `ui_jp`
mỗi cái có một `Name` (Image, rect 328×54) trỏ vào sprite
`UL_q&a_chara_icon_frame_nm_0N_*`. Sprite đóng gói **rất sát nét**, `m_Rect` là
328×54 nhưng ô trong atlas chỉ bằng đúng phần mực.

| sprite | ô atlas | gốc | thành |
|---|---|---|---|
| `nm_01_miya` | 82×40  | 雅火        | Miyabi        |
| `nm_02_kai`  | 148×40 | 宗像　戒     | Munakata Kai  |
| `nm_03_ran`  | 148×40 | 永守　藍     | Nagamori Ran  |
| `nm_04_soi`  | 190×40 | 弥坂　奏壱   | Yasaka Soichi |
| `nm_05_yuri` | 118×37 | ユーリ       | Yuri          |

Cách đọc lấy đúng bảng tên của chính bản dịch — nameplate trong `ScenarioData`
ghi cả hai vế (`雅火/Miyabi`, `宗像 戒/Munakata Kai`, `永守 藍/Nagamori Ran`,
`弥坂 奏壱/Yasaka Soichi`, `神楽 侑莉/Yuri`), khớp luôn hậu tố tên file
(`miya`, `kai`, `ran`, `soi`, `yuri`).

**Cỡ chữ 24 là do ô hẹp nhất quyết định.** Font `FOT-DotGothic12Std-M`
(= `ULPixel.ttf`, nhúng ngay trong `ui_jp`) đơn cách, mỗi chữ Latin rộng nửa em:

    "Munakata Kai" / "Nagamori Ran" = 12 chữ -> 12 * 24/2 = 144 px, ô chỉ có 148

Năm nhãn này thay nhau vào **cùng một chỗ** trên màn hình khi đổi nhân vật, nên
phải chung một cỡ — xem bài học ARCHIVE trong [[unlogical-baked-art-screens]].
24 cũng đúng **2× lưới điểm ảnh** của font (thiết kế 12 px/em), nên nét sắc gọn;
27–28 vừa ô nhưng lẻ lưới, nét sẽ răng cưa không đều.

> **Không nới ô ra được.** Muốn cỡ 36 (3× lưới, gần với sức nặng của chữ kanji
> gốc) thì "Miyabi" cần 102 px, mà ô của nó chỉ 82. Quanh ô tuy có 151 px trong
> suốt bên trái và 22 px bên phải, nhưng vùng đó **nằm trong `textureRect` của
> hai sprite khác** (x 567..859 và x 941..1022) — vẽ đè vào là mực hiện lên giữa
> hai sprite kia. Muốn to hơn phải dời hẳn ô sang chỗ trống thật của atlas, tức
> phải sửa `textureRect` + `uvTransform` + mesh.
>
> `uvTransform` chính là phép biến đổi affine từ toạ độ sprite sang pixel atlas,
> đã kiểm chứng trên `nm_01_miya`:
> `texX = localX * uvTransform.x + uvTransform.y`, với `uvTransform.x = m_PixelsToUnits`
> và `localX = (textureRectOffset.x - m_Rect.width * pivot.x) / m_PixelsToUnits`.
> Nới ô mà giữ nguyên `localX` thì `uvTransform` **không đổi**.
"""
import gc
import hashlib
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from keyart import Container

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UI_JP = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BACKUP = os.path.join(ROOT, "_backup", "ui_jp.preqanames")
PREVIEW = os.path.join(ROOT, "_keyprompt")

FONT = ("C:/Users/ADMIN/AppData/Local/Temp/claude/D--Downloads-010068501ff9a000/"
        "9d4f7fb5-9b6c-4487-a5b3-fbf1cbd6951d/scratchpad/fonts/ULPixel.ttf")
SIZE = 24

NAMES = [
    ("UL_q&a_chara_icon_frame_nm_01_miya", "Miyabi"),
    ("UL_q&a_chara_icon_frame_nm_02_kai", "Munakata Kai"),
    ("UL_q&a_chara_icon_frame_nm_03_ran", "Nagamori Ran"),
    ("UL_q&a_chara_icon_frame_nm_04_soi", "Yasaka Soichi"),
    ("UL_q&a_chara_icon_frame_nm_05_yuri", "Yuri"),
]


def ink_layer(text, size):
    """Ảnh L cắt sát nét của chuỗi."""
    f = ImageFont.truetype(FONT, size)
    probe = Image.new("L", (1400, 300), 0)
    ImageDraw.Draw(probe).text((80, 220), text, font=f, fill=255, anchor="ls")
    a = np.asarray(probe)
    xs = np.nonzero((a > 8).any(axis=0))[0]
    ys = np.nonzero((a > 8).any(axis=1))[0]
    return probe.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def ink_colour(img):
    a = np.asarray(img)
    m = a[:, :, 3] > 128
    return tuple(int(v) for v in np.median(a[:, :, :3][m], axis=0))


def compose(before, text):
    """Xoá trắng ô rồi vẽ chữ mới căn giữa, giữ đúng màu mực gốc."""
    w, h = before.size
    colour = ink_colour(before)
    glyphs = ink_layer(text, SIZE)
    iw, ih = glyphs.size
    if iw > w or ih > h:
        raise ValueError("%r cần %dx%d, ô chỉ %dx%d" % (text, iw, ih, w, h))
    layer = Image.new("L", (w, h), 0)
    layer.paste(glyphs, ((w - iw) // 2, (h - ih) // 2))
    out = Image.new("RGBA", (w, h), colour + (255,))
    out.putalpha(layer)
    return out, iw, ih, colour


def main():
    apply_ = "--apply" in sys.argv
    os.makedirs(PREVIEW, exist_ok=True)
    c = Container(UI_JP)
    strips = []
    for name, text in NAMES:
        s = c.sprite(name)
        before = s.crop()
        after, iw, ih, colour = compose(before, text)
        print("  %-38s ô %3dx%-3d  %-14s nét %3dx%-3d dư %3d px  màu %s  đỉnh %d"
              % (name.replace("UL_q&a_chara_icon_frame_", ""), before.width, before.height,
                 text, iw, ih, before.width - iw, colour, s.vertex_count()))
        s.paste(after)
        s.full_rect_mesh()
        strips.append((before, after))

    # ảnh xem trước: gốc ở trên, bản mới ở dưới
    pad = 6
    W = max(b.width for b, _ in strips) + pad * 2
    H = sum(b.height * 2 + pad * 3 for b, _ in strips)
    sheet = Image.new("RGBA", (W, H), (254, 160, 174, 255))
    y = pad
    for before, after in strips:
        sheet.alpha_composite(before, (pad, y))
        y += before.height
        sheet.alpha_composite(after, (pad, y))
        y += after.height + pad * 2
    out = os.path.join(PREVIEW, "qa_names.png")
    sheet.convert("RGB").resize((W * 2, H * 2), Image.NEAREST).save(out)
    print("\nẢnh xem trước:", out)

    if not apply_:
        print("(chạy thử — thêm --apply để ghi)")
        return
    if not os.path.exists(BACKUP):
        shutil.copy2(UI_JP, BACKUP)
        print("backup: _backup\\ui_jp.preqanames")
    tmp = UI_JP + ".out"
    n = c.save(tmp, packer="lz4")

    # Ryujinx giữ `ui_jp` mở khi đang chạy: mở ghi thì được nhưng **rename thì
    # không** (thiếu FILE_SHARE_DELETE), nên `os.replace` báo WinError 5. Ghi đè
    # tại chỗ rồi đối chiếu hash — vẫn phải đóng Container trước, vì UnityPy còn
    # giữ handle của chính file nguồn.
    del c
    gc.collect()
    data = open(tmp, "rb").read()
    want = hashlib.sha256(data).hexdigest()
    with open(UI_JP, "r+b") as f:
        f.write(data)
        f.truncate(len(data))
        f.flush()
        os.fsync(f.fileno())
    got = hashlib.sha256(open(UI_JP, "rb").read()).hexdigest()
    if got != want:
        raise SystemExit("ghi hỏng — khôi phục từ %s" % BACKUP)
    os.remove(tmp)
    print("đã ghi %s (%s byte)" % (UI_JP, format(n, ",")))


if __name__ == "__main__":
    main()
