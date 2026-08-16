# -*- coding: utf-8 -*-
"""Dải phím màn Ending List vẫn còn tiếng Nhật: `Ⓐシーン再生 Ⓑ戻る`.

`UL_recolle_key` (300×34) trong `sharedassets21.assets`, atlas
`sactx-0-2048x2048-ASTC 4x4-Recollection`. Đây là **tranh vẽ**, không phải chuỗi
— `シーン再生` chỉ xuất hiện trong `resources.assets` ở một hộp thoại xác nhận
khác (`SystemText` id 42) và trong `global-metadata.dat`, không dính gì tới dải
này.

Dùng lại đúng đường ống của `fix_key_prompts.py`: giữ nguyên icon Ⓐ/Ⓑ cắt từ
tranh gốc, vẽ lại phần chữ bằng font UI của game, rồi dựng mesh thành quad
full-rect (sprite này tight-mesh 85 đỉnh — không dựng lại là nét mới bị xén
thủng, xem [[unitypy-switch-bundle-repack]]).

Tách riêng khỏi `fix_key_prompts.py` để chỉ đụng vào **một** file: chạy lại
script kia sẽ ghi đè cả `sharedassets5/6/11`, `scene_jp`, `ui_jp`.

    python tools\\fix_recollection_key.py            # chạy thử, xuất ảnh xem trước
    python tools\\fix_recollection_key.py --apply    # backup rồi vá thật
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from keyart import Container, render_check          # noqa: E402
from fix_key_prompts import compose                 # noqa: E402

# `fix_key_prompts` đã bọc sys.stdout thành utf-8 khi import; **đừng bọc lại** —
# cái bọc cũ mất tham chiếu sẽ bị thu hồi và đóng luôn buffer bên dưới.

APPLY = "--apply" in sys.argv

REL = "sharedassets21.assets"
NAME = "UL_recolle_key"
# (icon_x0, icon_x1, chữ mới) — chữ thay cho tất cả những gì nằm giữa icon này
# và icon kế tiếp.  Toạ độ đo bằng keyprompt_scan.describe():
#   2-31 Ⓐ | 39-179 シーン再生 | 202-231 Ⓑ | 238-300 戻る
# "Play scene" / "Back" bám theo tiếng Anh chính chủ của game trong UL_library_key.
SPEC = [(2, 31, "Play scene"), (202, 231, "Back")]

PATCH = os.path.join(ROOT, "romfs", "Data")
STOCK = r"D:\Downloads\UNLOGICAL_v2\Data"
BACKUP = os.path.join(ROOT, "_backup", "sharedassets21.assets.prerecollekey")
WORK = os.path.join(ROOT, "_keyprompt", "_work")
PREVIEW = os.path.join(ROOT, "_keyprompt")

TMP_PID = 169          # RecollectionButton/Text — phải sống sót qua lần ghi này


def opaque(img):
    return int((np.asarray(img)[:, :, 3] > 8).sum())


def main():
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)

    src = os.path.join(PATCH, REL)
    in_patch = os.path.exists(src)
    if not in_patch:
        src = os.path.join(STOCK, REL)
    tmp = os.path.join(WORK, REL).replace("\\", "/")
    shutil.copy(src, tmp)
    res = os.path.join(STOCK, REL) + ".resS"          # bản vá không kèm .resS
    if os.path.exists(res) and not os.path.exists(tmp + ".resS"):
        shutil.copy(res, tmp + ".resS")

    c = Container(tmp)
    s = c.sprite(NAME)

    # Tranh nguồn LUÔN lấy từ bản gốc 1.0.2, không lấy từ bản vá: toạ độ icon
    # trong SPEC là của bố cục tiếng Nhật, chạy lần hai trên tranh đã dịch sẽ cắt
    # nhầm chỗ (Ⓑ đã dịch sang trái ~26 px). Nhờ vậy chạy lại bao nhiêu lần cũng
    # ra đúng một kết quả.
    ref = os.path.join(WORK, "stock." + REL).replace("\\", "/")
    shutil.copy(os.path.join(STOCK, REL), ref)
    if os.path.exists(res) and not os.path.exists(ref + ".resS"):
        shutil.copy(res, ref + ".resS")
    sref = Container(ref).sprite(NAME)
    before = sref.crop()
    print("%s  %dx%d  verts=%d (vá) / %d (gốc)  — tranh nguồn: gốc 1.0.2" %
          (NAME, before.width, before.height, s.vertex_count(), sref.vertex_count()))
    if s.crop().size != before.size:
        raise SystemExit("ô atlas của bản vá khác bản gốc")

    after, size, gap = compose(before, SPEC)
    print("   font=%d  gap=%d  mực=%s" % (size, gap, after.getpixel((0, 0)) and "—"))
    s.paste(after)
    s.full_rect_mesh()

    side = Image.new("RGB", (before.width, before.height * 2 + 6), (250, 250, 250))
    for i, im in enumerate((before, after)):
        flat = Image.alpha_composite(Image.new("RGBA", im.size, (250, 250, 250, 255)), im)
        side.paste(flat.convert("RGB"), (0, i * (before.height + 6)))
    prev = os.path.join(PREVIEW, "sharedassets21.assets__UL_recolle_key.png")
    side.save(prev)
    print("   ảnh xem trước ->", prev)

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    out = tmp + ".out"
    n = c.save(out)
    print("dựng %s byte" % format(n, ","))

    # --- kiểm tra trên chính file vừa dựng, trước khi thay file thật ---------
    drawn = render_check(out, NAME)                   # đi qua mesh, đúng như game vẽ
    lost = opaque(after) - opaque(drawn)
    print("pixel đục: vẽ mới %d, game vẽ ra %d, hụt %d" %
          (opaque(after), opaque(drawn), lost))
    if lost > 0:
        raise SystemExit("mesh vẫn xén mất nét — dừng, không ghi")

    import UnityPy
    env = UnityPy.load(out)
    objs = list(env.objects)
    zero = [o.path_id for o in objs if o.byte_size == 0]
    print("object: %d, byte_size=0: %d" % (len(objs), len(zero)))
    if len(objs) != 174 or zero:
        raise SystemExit("số object sai hoặc có object rỗng — dừng, không ghi")

    env0 = UnityPy.load(os.path.join(PATCH, "StreamingAssets", "ui", "ui_jp"))
    nodes = next(o.serialized_type.nodes for o in env0.objects
                 if o.type.name == "MonoBehaviour"
                 and isinstance(getattr(o, "read_typetree")(), dict)
                 and "m_enableAutoSizing" in o.read_typetree())
    tt = next(o for o in objs if o.path_id == TMP_PID).read_typetree(nodes=nodes)
    keep = {k: tt[k] for k in ("m_TextWrappingMode", "m_enableAutoSizing",
                               "m_fontSizeMin", "m_fontSizeMax")}
    print("pid %d giữ nguyên: %s" % (TMP_PID, keep))
    if keep != {"m_TextWrappingMode": 0, "m_enableAutoSizing": 1,
                "m_fontSizeMin": 17.0, "m_fontSizeMax": 32.0}:
        raise SystemExit("bản vá Ending List bị mất — dừng, không ghi")

    dst = os.path.join(PATCH, REL)
    if os.path.exists(dst) and not os.path.exists(BACKUP):
        shutil.copy2(dst, BACKUP)
        print("backup ->", BACKUP)
    # `UnityPy.load(out)` ở bước kiểm tra vẫn giữ handle nên `move` bị Windows
    # chặn — chép nội dung sang rồi mới dọn file tạm.
    with open(out, "rb") as f:
        blob = f.read()
    with open(dst, "wb") as f:
        f.write(blob)
    try:
        os.remove(out)
    except OSError:
        pass
    print("đã ghi %s (%s byte)" % (dst, format(os.path.getsize(dst), ",")))


main()
