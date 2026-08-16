# -*- coding: utf-8 -*-
"""Make the terminal dictionary's ruby fit its box without shrinking the text.

The screen the player opens from the terminal is **level22**, not the ADV
dictionary popup in level10 — different widget, much tighter:

    RenderCanvas/Note/Title/Mask_Title/Title (TMP)  pid 330
        mask 500x40   size 32, charSpacing 3.5, NoWrap, no auto-size
    RenderCanvas/Note/Title/Mask_Ryby/Ruby (TMP)    pid 332
        mask 180x14   size 12, charSpacing 15,  NoWrap, no auto-size

Both are centre-aligned inside a mask, so anything too wide is cut off at BOTH
ends.  `m_characterSpacing = 15` was tuned for the six full-width kana of the
stock placeholder `ルビのサイズ`; a Latin word pays that tracking **per letter**,
which is the whole reason "Non-complainant offense" runs to 243 px in a 180 px
box.  There are no kana rubies left, so the tracking buys nothing and dropping
it to 0 brings every ruby inside the box at full size.

Auto-sizing the ruby was rejected on purpose: at 12 px it is already the
smallest text on the screen and shrinking it further is unreadable.

`level22` carries no embedded type trees, so this patches the file **bytes in
place** rather than re-serialising (re-serialising writes the unparsed objects
back empty).  Field layout from m_fontSize, all 4 bytes each:

    +0 m_fontSize  +4 m_fontSizeBase  +8 m_fontWeight  +12 m_enableAutoSizing
    +16 m_fontSizeMin  +20 m_fontSizeMax  +24 m_fontStyle
    +28 m_HorizontalAlignment  +32 m_VerticalAlignment  +36 m_textAlignment
    +40 m_characterSpacing

    python tools\\fix_dictionary_box.py [--title] [--apply]

`--title` additionally auto-sizes the TITLE (26-32); that one is 32 px, so
shrinking it a little is far less painful than shrinking the ruby.
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

LEVEL = os.path.join(ROOT, "romfs", "Data", "level22")
UI = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BACKUP = os.path.join(ROOT, "_backup", "level22.predicbox")

APPLY = "--apply" in sys.argv
DO_TITLE = "--title" in sys.argv

RUBY_PID, TITLE_PID = 332, 330
MASK_RYBY_RT = 232          # RenderCanvas/Note/Title/Mask_Ryby
OFF_AUTOSIZE, OFF_MIN, OFF_MAX, OFF_CSPACE = 12, 16, 20, 40

# Mask_Ryby chỉ rộng 180 px — đủ cho 12 chữ kana, không đủ cho một từ tiếng Anh
# viết hoa.  Nới bằng Mask_Title (500) là vừa: nó nằm giữa cùng một khối, khung
# cha `Title` rộng 564 và khung hồng vẽ sẵn còn rộng hơn nữa, nên không đụng gì.
MASK_RYBY_OLD_W, MASK_RYBY_NEW_W = 180.0, 500.0


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


def find_anchor(blob, start, length, font_size):
    chunk = bytes(blob[start:start + length])
    anchor = struct.pack("<ffi", font_size, font_size, 400)
    hits = [i for i in range(len(chunk) - len(anchor) + 1)
            if chunk[i:i + len(anchor)] == anchor]
    if len(hits) != 1:
        raise SystemExit("mỏ neo khớp %d lần (phải là 1)" % len(hits))
    return start + hits[0]


def main():
    nodes = borrowed_nodes()
    env = UnityPy.load(LEVEL)
    spans, trees = {}, {}
    for o in env.objects:
        if o.path_id in (RUBY_PID, TITLE_PID):
            spans[o.path_id] = (o.byte_start, o.byte_size)
            trees[o.path_id] = o.read_typetree(nodes)
    for pid, name in ((RUBY_PID, "Ruby  mask 180x14"), (TITLE_PID, "Title mask 500x40")):
        t = trees[pid]
        print("pid %-5s %-20s size=%s autosize=%s min=%s max=%s charSpacing=%s"
              % (pid, name, t["m_fontSize"], t["m_enableAutoSizing"],
                 t["m_fontSizeMin"], t["m_fontSizeMax"], t["m_characterSpacing"]))

    blob = bytearray(open(LEVEL, "rb").read())
    n0 = len(blob)

    # --- ruby: bỏ tracking, KHÔNG auto-size
    start, length = spans[RUBY_PID]
    off = find_anchor(blob, start, length, 12.0)
    cs, = struct.unpack_from("<f", blob, off + OFF_CSPACE)
    assert abs(cs - 15.0) < 1e-3 or abs(cs) < 1e-6, "charSpacing lạ: %s" % cs
    if abs(cs) > 1e-6:
        print("\nruby  @%d  charSpacing %.1f -> 0.0   (auto-size để nguyên = tắt)" % (off, cs))
        struct.pack_into("<f", blob, off + OFF_CSPACE, 0.0)
    else:
        print("\nruby  charSpacing đã là 0")

    # --- nới Mask_Ryby: 180 -> 500
    rt = next(o for o in env.objects if o.path_id == MASK_RYBY_RT)
    t = rt.read_typetree()
    cur_w = t["m_SizeDelta"]["x"]
    if abs(cur_w - MASK_RYBY_NEW_W) < 1e-3:
        print("mask  Mask_Ryby đã rộng %.0f" % cur_w)
    else:
        assert abs(cur_w - MASK_RYBY_OLD_W) < 1e-3, "bề rộng mask lạ: %s" % cur_w
        tail = struct.pack(
            "<ffffffffff",
            t["m_AnchorMin"]["x"], t["m_AnchorMin"]["y"],
            t["m_AnchorMax"]["x"], t["m_AnchorMax"]["y"],
            t["m_AnchoredPosition"]["x"], t["m_AnchoredPosition"]["y"],
            t["m_SizeDelta"]["x"], t["m_SizeDelta"]["y"],
            t["m_Pivot"]["x"], t["m_Pivot"]["y"])
        hits = [i for i in range(len(blob) - len(tail) + 1) if blob[i:i + len(tail)] == tail]
        if len(hits) != 1:
            raise SystemExit("mỏ neo RectTransform khớp %d lần" % len(hits))
        off_w = hits[0] + 24          # bỏ qua anchorMin/Max + anchoredPosition
        old, = struct.unpack_from("<f", blob, off_w)
        assert abs(old - MASK_RYBY_OLD_W) < 1e-3
        print("mask  Mask_Ryby @%d  rộng %.0f -> %.0f  (cao %.0f giữ nguyên)"
              % (off_w, old, MASK_RYBY_NEW_W, t["m_SizeDelta"]["y"]))
        struct.pack_into("<f", blob, off_w, MASK_RYBY_NEW_W)

    # --- title: auto-size, tuỳ chọn
    if DO_TITLE:
        start, length = spans[TITLE_PID]
        off = find_anchor(blob, start, length, 32.0)
        auto, fmin, fmax = struct.unpack_from("<iff", blob, off + OFF_AUTOSIZE)
        assert auto == 0 and abs(fmax - 72.0) < 1e-3
        print("title @%d  autosize %s->1  min %s->26  max %s->32" % (off, auto, fmin, fmax))
        struct.pack_into("<iff", blob, off + OFF_AUTOSIZE, 1, 26.0, 32.0)

    assert len(blob) == n0, "độ dài file đổi"

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi" + ("" if DO_TITLE else " (thêm --title để làm cả tiêu đề)"))
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(LEVEL, BACKUP)
        print("backup ->", BACKUP)
    open(LEVEL, "wb").write(blob)
    print("đã ghi", LEVEL, os.path.getsize(LEVEL))

    for o in UnityPy.load(LEVEL).objects:
        if o.path_id in (RUBY_PID, TITLE_PID):
            t = o.read_typetree(nodes)
            print("  đọc lại pid %-5s size=%s autosize=%s min=%s max=%s charSpacing=%s"
                  % (o.path_id, t["m_fontSize"], t["m_enableAutoSizing"],
                     t["m_fontSizeMin"], t["m_fontSizeMax"], t["m_characterSpacing"]))


main()
