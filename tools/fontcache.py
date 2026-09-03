# -*- coding: utf-8 -*-
"""Trích TTF nhúng trong `ui_jp` của bản dịch ra đĩa cho PIL dùng.

Các tool vẽ chữ lên tranh (`fix_key_prompts.py`, `fix_music_key.py`,
`fix_movie_total_plate.py`, `fix_dlc_art.py`…) cần file .ttf thật. Bản đầu tiên để
chúng trong scratchpad của một phiên Claude (`…/9d4f7fb5-…/scratchpad/fonts/`) — thư mục
đó đã mất ngày 03/09/2026 và mọi tool trỏ vào nó đều chết. Font nào cũng nằm sẵn trong
`ui_jp` (Font asset, `m_FontData` là TTF nguyên vẹn, đã có dấu tiếng Việt), nên trích ra
`<repo>/_fonts/<tên>.ttf` khi cần — thư mục này gitignore, mất thì tự dựng lại.

    from fontcache import ttf
    path = ttf("FOT-NewRodinProN-DB")     # chữ UI gothic (font_BASE.ttf cũ)
    path = ttf("FOT-DotGothic12Std-M")    # chữ điểm ảnh (ULPixel.ttf cũ)

Tên có trong ui_jp: FOT-NewRodinProN-DB, FOT-DotGothic12Std-M, FOT-DNPShueiMGoStd-B,
FOT-DNPShueiMGoStd-L, FOT-iroha21popuraStdN-R, LiberationSans.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UI_JP = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
CACHE = os.path.join(ROOT, "_fonts")

# tên cũ trong các tool đời đầu -> tên Font asset
ALIASES = {"font_BASE": "FOT-NewRodinProN-DB", "ULPixel": "FOT-DotGothic12Std-M"}


def ttf(name, bundle=UI_JP, cache=CACHE):
    name = ALIASES.get(name, name)
    path = os.path.join(cache, name + ".ttf")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    import UnityPy
    os.makedirs(cache, exist_ok=True)
    for o in UnityPy.load(bundle).objects:
        if o.type.name != "Font":
            continue
        d = o.read()
        if d.m_Name == name:
            with open(path, "wb") as f:
                f.write(bytes(d.m_FontData))
            return path
    raise FileNotFoundError("không có Font %r trong %s" % (name, bundle))
