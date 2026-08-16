"""Dịch dải phím nghiêng của SYSTEM MENU (`UL_sys_plate_key` trong `ui_jp`).

Dải này nghiêng ~15° nên không dùng chung được với `fix_key_prompts.py`. Cách làm:
xoay **ảnh phân tích** cho chữ nằm ngang để đo toạ độ, nhưng chỉ xoay *lớp chữ
mới* khi ghép trở lại — icon Ⓐ Ⓑ và toàn bộ mã vạch, khung tem giữ nguyên pixel
gốc, không hề bị lấy mẫu lại.

    python tools\fix_sys_plate_key.py [--apply]
"""

import io
import os
import shutil
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from keyart import Container

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TARGET = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
STOCK = "D:/Downloads/UNLOGICAL_v2/Data/StreamingAssets/ui/ui_jp"
BACKUP = os.path.join(ROOT, "_backup")
PREVIEW = os.path.join(ROOT, "_keyprompt")
FONT = ("C:/Users/ADMIN/AppData/Local/Temp/claude/D--Downloads-010068501ff9a000/"
        "9d4f7fb5-9b6c-4487-a5b3-fbf1cbd6951d/scratchpad/fonts/font_BASE.ttf")

NAME = "UL_sys_plate_key"
CENTER = (86.0, 187.0)        # tâm icon Ⓐ
ANGLE = 14.975                # độ nghiêng của dải, đo từ tâm Ⓐ -> tâm Ⓑ
BAND = (168, 206)             # dòng của dải chữ trong hệ đã xoay (đã chừa mã vạch)
WORDS = [                     # (mép phải icon, x xoá từ, x xoá đến, chữ mới)
    (101, 104, 194, "Select"),
    (227, 231, 303, "Back"),
]
ICON_ROWS = (172, 202)        # đĩa nút chiếm dòng nào trong hệ đã xoay
SIZE = 22                     # lớn nhất mà "Select" vẫn không chạm icon Ⓑ ở x=197
GAP = 6


def baseline_for(font, iy0, iy1):
    """Baseline sao cho một từ không có nét thò xuống nằm giữa đĩa nút."""
    probe = Image.new("L", (400, 300), 0)
    ImageDraw.Draw(probe).text((40, 200), "Back", font=font, fill=255, anchor="ls")
    ys = np.nonzero((np.asarray(probe) > 60).any(axis=1))[0]
    ink_h = int(ys.max()) - int(ys.min()) + 1
    return int(round(iy0 + ((iy1 - iy0) - ink_h) / 2.0 + (200 - int(ys.min()))))


def build(img):
    w, h = img.size
    a = np.asarray(img)
    col = tuple(int(v) for v in np.median(a[:, :, :3][a[:, :, 3] > 128], axis=0))
    font = ImageFont.truetype(FONT, SIZE)
    baseline = baseline_for(font, *ICON_ROWS)

    # lớp chữ + mặt nạ xoá, cả hai dựng trong hệ đã xoay cho chữ nằm ngang
    text_rot = Image.new("L", (w, h), 0)
    wipe_rot = Image.new("L", (w, h), 0)
    dt, dw = ImageDraw.Draw(text_rot), ImageDraw.Draw(wipe_rot)
    for icon_right, wipe0, wipe1, word in WORDS:
        dw.rectangle([wipe0, BAND[0], wipe1, BAND[1]], fill=255)
        probe = Image.new("L", (600, 200), 0)
        ImageDraw.Draw(probe).text((50, 150), word, font=font, fill=255, anchor="ls")
        xs = np.nonzero((np.asarray(probe) > 8).any(axis=0))[0]
        pen = 50 - int(xs.min())
        dt.text((icon_right + GAP + pen, baseline), word, font=font, fill=255, anchor="ls")

    # đưa hai lớp về hệ toạ độ gốc
    text = text_rot.rotate(ANGLE, resample=Image.BICUBIC, center=CENTER)
    wipe = wipe_rot.rotate(ANGLE, resample=Image.BICUBIC, center=CENTER)

    out = img.copy()
    arr = np.array(out)
    arr[:, :, 3] = np.where(np.asarray(wipe) > 110, 0, arr[:, :, 3])
    out = Image.fromarray(arr)

    tint = Image.new("RGBA", (w, h), col + (255,))
    tint.putalpha(text)
    out.alpha_composite(tint)
    return out


def main():
    apply = "--apply" in sys.argv
    os.makedirs(PREVIEW, exist_ok=True)
    work = os.path.join(PREVIEW, "_work")
    os.makedirs(work, exist_ok=True)
    tmp = os.path.join(work, "ui_jp").replace("\\", "/")
    shutil.copy(TARGET, tmp)

    c = Container(tmp)
    s = c.sprite(NAME)
    before = s.crop()                       # đang có gì trong bản vá (để so sánh)
    origin = Container(STOCK).sprite(NAME).crop()   # nguồn dựng: luôn là bản gốc
    after = build(origin)
    s.paste(after)
    s.full_rect_mesh()

    side = Image.new("RGB", (before.width, before.height * 2 + 8), (250, 250, 250))
    for i, im in enumerate((before, after)):
        flat = Image.alpha_composite(Image.new("RGBA", im.size, (250, 250, 250, 255)), im)
        side.paste(flat.convert("RGB"), (0, i * (before.height + 8)))
    side.save(os.path.join(PREVIEW, f"ui_jp__{NAME}.png"))

    if apply:
        os.makedirs(BACKUP, exist_ok=True)
        shutil.copy(TARGET, os.path.join(
            BACKUP, "ui_jp.presysplate-" + time.strftime("%Y%m%d-%H%M%S")))
        n = c.save(tmp + ".out", packer="lz4")
        shutil.move(tmp + ".out", TARGET)
        print(f"ui_jp: ghi {n:,} byte")
    else:
        print("chạy thử, chưa ghi —", os.path.join(PREVIEW, f"ui_jp__{NAME}.png"))


if __name__ == "__main__":
    main()
