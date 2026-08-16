# -*- coding: utf-8 -*-
"""Giao việc ngắt dòng của ô tóm tắt chương lại cho TextMeshPro.

Đi kèm bản vá IPS tắt `DefaultMaxCharsPerLine` (xem `make_ips.py`). Trước đây
code game tự ngắt mỗi 18 ký tự nên component để `m_TextWrappingMode = 0`; tắt
code đi mà không bật wrap thì cả đoạn thành một dòng dài rồi bị mask cắt.

    ChapterSelect/Story/SynopsisTitle/Mask/MainText   (ui_jp)
        mask 620x474, fontSize 31.25, charSpacing 5.8, lineSpacing 33

Bước dòng = fontSize × (116/58 + 33/100) = 2.33 × fontSize, nên khung chứa
6 dòng ở cỡ 31.25 và 11 dòng ở cỡ 18. Với bề rộng trung bình ~0.616 em thì sức
chứa đi từ ~192 lên ~616 ký tự — đủ cho tóm tắt dài nhất (496).

`m_fontSizeMax` ghim đúng `m_fontSize` gốc; để nguyên 72 là mục ngắn bị phóng to.

    python tools\\fix_synopsis_box.py [--apply]
"""
import io
import os
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

import UnityPy   # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BACKUP = os.path.join(ROOT, "_backup", "ui_jp.presynwrap2")
APPLY = "--apply" in sys.argv

MAIN_TEXT = -1764327492018131728          # Mask/MainText
CHANGES = {
    # TMP KHÔNG được wrap: code game vẫn tự chèn ngắt dòng (mỗi 24 ký tự) và
    # đếm số dòng đó để chia trang cho thanh cuộn. TMP ngắt thêm một lần nữa thì
    # số dòng thật > số dòng code tưởng, và phần dôi ra rơi vào khoảng giữa hai
    # trang, không cuộn tới được.
    "m_TextWrappingMode": 0,
    # KHÔNG auto-size: ô này có thanh cuộn riêng (`StorySlider` trong ui_jp), nên
    # phần dôi ra cuộn xuống chứ không cần thu nhỏ chữ. Giữ nguyên cỡ 31.25 cho
    # mọi mục, đọc thoải mái hơn là 43 mục mỗi mục một cỡ.
    "m_enableAutoSizing": 0,
    "m_fontSizeMin": 18.0,                # = gốc
    "m_fontSizeMax": 72.0,                # = gốc (không dùng tới khi auto-size tắt)
}
# Dấu phụ chồng của tiếng Việt (ắ = trăng + sắc) vươn cao hơn đường ascender của
# font, nên dòng ĐẦU bị mask xén mất dấu sắc: đo trên ảnh chụp thì dòng 1 chỉ cao
# 27 px trên baseline trong khi dấu sắc cần 32. Lề trên gốc lại là -1, tức còn
# kéo chữ lên thêm 1 px nữa. Đẩy xuống 6 px là vừa đủ (thiếu 5) mà vẫn giữ được
# 7 dòng một trang: 6*72.8 + 31.25 = 468.05 <= 474 - 5.
MARGIN_TOP = 5.0


def main():
    env = UnityPy.load(BUNDLE)
    target = None
    for o in env.objects:
        if o.path_id == MAIN_TEXT and o.type.name == "MonoBehaviour":
            target = o
            break
    if target is None:
        raise SystemExit("không thấy MainText pid %d" % MAIN_TEXT)

    tree = target.read_typetree()
    print("MainText  fontSize=%s wrap=%s autosize=%s min=%s max=%s margin=%s"
          % (tree["m_fontSize"], tree["m_TextWrappingMode"], tree["m_enableAutoSizing"],
             tree["m_fontSizeMin"], tree["m_fontSizeMax"], tree["m_margin"]))
    assert abs(tree["m_fontSize"] - 31.25) < 1e-6, "fontSize gốc đã khác"

    changed = []
    if tree["m_margin"]["y"] != MARGIN_TOP:
        changed.append("m_margin.y %s -> %s" % (tree["m_margin"]["y"], MARGIN_TOP))
        tree["m_margin"]["y"] = MARGIN_TOP
    for k, v in CHANGES.items():
        if tree[k] != v:
            changed.append("%s %s -> %s" % (k, tree[k], v))
            tree[k] = v
    if not changed:
        print("đã đúng trạng thái đích, không cần sửa")
        return
    for c in changed:
        print("   " + c)

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(BUNDLE, BACKUP)
        print("backup ->", BACKUP)
    target.save_typetree(tree)
    blob = env.file.save(packer="lz4")
    with open(BUNDLE, "wb") as f:
        f.write(blob)
    print("đã ghi", BUNDLE, os.path.getsize(BUNDLE))

    for o in UnityPy.load(BUNDLE).objects:
        if o.path_id == MAIN_TEXT and o.type.name == "MonoBehaviour":
            t = o.read_typetree()
            print("  đọc lại: wrap=%s autosize=%s min=%s max=%s"
                  % (t["m_TextWrappingMode"], t["m_enableAutoSizing"],
                     t["m_fontSizeMin"], t["m_fontSizeMax"]))


main()
