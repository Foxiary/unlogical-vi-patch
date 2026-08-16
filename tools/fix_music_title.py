# -*- coding: utf-8 -*-
"""Bỏ tracking của tên bài hát ở màn MUSIC.

`MusicRoom.trackTitle` = `level13` pid 244 `Music/RenderCanvas/MusicRoom/TrackTitle`:
rect 400×100, lề trái 14 → **386 px dùng được**, cỡ 32, charSpacing 6, NoWrap,
không auto-size. Chuỗi mẫu bản gốc `ラジエイター１１文字入` đo được 371 px — ô được
cắt vừa khít 11 chữ toàn rộng.

`charSpacing 6` là để giãn 11 chữ kana cho đẹp. Tên tiếng Việt dài 8–45 ký tự
phải trả khoảng giãn đó cho **từng chữ cái**, nên đây là bước đầu tiên cần bỏ —
không đụng cỡ chữ, không đụng bản dịch.

`level13` không nằm sẵn trong romfs nên script chép từ bản gốc 1.0.2 sang trước.
File này không nhúng type tree, nên **vá byte tại chỗ**; bố cục trường tính từ
`m_fontSize`, mỗi trường 4 byte: +12 autosize, +16 min, +20 max, +24 fontStyle,
+28 hAlign, +32 vAlign, +36 textAlign, **+40 characterSpacing**.

    python tools\\fix_music_title.py [--apply]
"""
import io
import os
import shutil
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402

STOCK = r"D:\Downloads\UNLOGICAL_v2\Data\level13"
LEVEL = os.path.join(ROOT, "romfs", "Data", "level13")
UI = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BACKUP = os.path.join(ROOT, "_backup", "level13.stock")
APPLY = "--apply" in sys.argv

TITLE_PID = 244
FONT_SIZE = 32.0
OFF_CSPACE = 40
NEW_CSPACE = 0.0


def borrowed_nodes():
    for o in UnityPy.load(UI).objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if isinstance(t, dict) and "m_enableAutoSizing" in t:
            return o.serialized_type.node
    raise SystemExit("không mượn được type tree từ ui_jp")


def main():
    if not os.path.exists(LEVEL):
        print("level13 chưa có trong romfs — chép từ bản gốc")
        if APPLY:
            shutil.copy2(STOCK, LEVEL)
            shutil.copy2(STOCK, BACKUP)
            print("   %s -> %s" % (STOCK, LEVEL))
            print("   backup gốc -> %s" % BACKUP)
        else:
            print("   (chạy thử: đọc thẳng bản gốc)")

    src = LEVEL if os.path.exists(LEVEL) else STOCK
    nodes = borrowed_nodes()
    env = UnityPy.load(src)
    obj = next((o for o in env.objects if o.path_id == TITLE_PID
                and o.type.name == "MonoBehaviour"), None)
    if obj is None:
        raise SystemExit("không thấy pid %d trong %s" % (TITLE_PID, src))
    t = obj.read_typetree(nodes)
    print("\nTrackTitle  size=%s wrap=%s autosize=%s charSpacing=%s"
          % (t["m_fontSize"], t["m_TextWrappingMode"], t["m_enableAutoSizing"],
             t["m_characterSpacing"]))
    if abs(t["m_characterSpacing"] - NEW_CSPACE) < 1e-6:
        print("đã là %s, không cần sửa" % NEW_CSPACE)
        return

    blob = bytearray(open(src, "rb").read())
    n0 = len(blob)
    start, length = obj.byte_start, obj.byte_size
    chunk = bytes(blob[start:start + length])
    anchor = struct.pack("<ffi", FONT_SIZE, FONT_SIZE, 400)
    hits = [i for i in range(len(chunk) - len(anchor) + 1)
            if chunk[i:i + len(anchor)] == anchor]
    if len(hits) != 1:
        raise SystemExit("mỏ neo khớp %d lần (phải là 1)" % len(hits))
    off = start + hits[0] + OFF_CSPACE
    cur, = struct.unpack_from("<f", blob, off)
    assert abs(cur - t["m_characterSpacing"]) < 1e-4, "lệch offset: %s vs %s" % (cur, t["m_characterSpacing"])
    print("charSpacing @%d  %.1f -> %.1f" % (off, cur, NEW_CSPACE))
    struct.pack_into("<f", blob, off, NEW_CSPACE)
    assert len(blob) == n0

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    open(LEVEL, "wb").write(blob)
    print("đã ghi", LEVEL, os.path.getsize(LEVEL))
    for o in UnityPy.load(LEVEL).objects:
        if o.path_id == TITLE_PID and o.type.name == "MonoBehaviour":
            t2 = o.read_typetree(nodes)
            print("  đọc lại: charSpacing=%s  (cỡ %s, wrap %s, autosize %s)"
                  % (t2["m_characterSpacing"], t2["m_fontSize"],
                     t2["m_TextWrappingMode"], t2["m_enableAutoSizing"]))


main()
