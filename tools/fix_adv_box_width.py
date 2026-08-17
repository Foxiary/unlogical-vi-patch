# -*- coding: utf-8 -*-
"""Narrow the ADV message text box so no line can slide under the corner art.

The box art is cut diagonally at its bottom right.  The text rect is 1400 px wide
but the art only leaves (measured off a real 1280x720 capture, canvas px from the
text's left edge at 308):

    line 1   1430      line 2   1364      line 3   1301      line 4   ~1240

TMP wraps at the rect and knows nothing about the art, so any line that happens to
fill the rect runs onto the dark diagonal and its tail stops being readable — the
state in `SPOILER_IMG_3011.jpg`.  Measured over the build: **3 992 of 37 951 ADV
messages (10.5%)** have such a line, 356 of them by more than 80 px.

Fix: make the rect itself 1280 wide.  `m_Pivot.x = 0` on both text rects, so
shrinking `m_SizeDelta.x` pins the left edge and pulls only the right edge in —
no position compensation, and nothing else in the box moves.

    level10 pid 564  Message(Normal)/Text     rect 1400x186 -> 1280x186
    level10 pid 581  Message(Highest)/Text    rect 1400x186 -> 1280x186

Why 1280 and not a data pass: with the model validated against both captures,

    khung   ở cỡ 42   nhỏ hơn 42   chạm hoạ tiết
    1400     37 285          666           3 992
    1300     36 760        1 191             448
    1280     36 620        1 331               2

and hard-wrapping the data instead costs **936** shrunk messages (more than the
665 this costs) plus a re-run after every sheet merge.  One float each, forever.

`level10` carries no embedded type trees, so this patches bytes in place — the
RectTransform anchor is the 10-float tail (anchorMin, anchorMax, anchoredPosition,
sizeDelta, pivot) and `sizeDelta.x` sits at +24, the same trick as
`fix_dictionary_box.py`.

    python tools\\fix_adv_box_width.py [--apply] [--revert]
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

LEVEL = os.path.join(ROOT, "romfs", "Data", "level10")
BACKUP = os.path.join(ROOT, "_backup", "level10.advboxw")
APPLY = "--apply" in sys.argv
REVERT = "--revert" in sys.argv

RECTS = {564: "Message(Normal)/Text", 581: "Message(Highest)/Text"}
OLD_W, NEW_W = (1280.0, 1400.0) if REVERT else (1400.0, 1280.0)


def tail(t):
    return struct.pack(
        "<ffffffffff",
        t["m_AnchorMin"]["x"], t["m_AnchorMin"]["y"],
        t["m_AnchorMax"]["x"], t["m_AnchorMax"]["y"],
        t["m_AnchoredPosition"]["x"], t["m_AnchoredPosition"]["y"],
        t["m_SizeDelta"]["x"], t["m_SizeDelta"]["y"],
        t["m_Pivot"]["x"], t["m_Pivot"]["y"])


def main():
    env = UnityPy.load(LEVEL)
    trees = {}
    for o in env.objects:
        if o.path_id in RECTS and o.type.name == "RectTransform":
            trees[o.path_id] = o.read_typetree()
    if len(trees) != len(RECTS):
        raise SystemExit("chỉ thấy %d/%d RectTransform" % (len(trees), len(RECTS)))

    for pid, name in RECTS.items():
        t = trees[pid]
        print("pid %-4d %-24s size=(%.0f,%.0f) pos=(%.0f,%.0f) pivot=(%.1f,%.1f)"
              % (pid, name, t["m_SizeDelta"]["x"], t["m_SizeDelta"]["y"],
                 t["m_AnchoredPosition"]["x"], t["m_AnchoredPosition"]["y"],
                 t["m_Pivot"]["x"], t["m_Pivot"]["y"]))
        assert t["m_Pivot"]["x"] == 0.0, "pivot.x != 0, thu bề rộng sẽ làm dịch chữ"
        if abs(t["m_SizeDelta"]["x"] - NEW_W) < 1e-3:
            print("   đã là %.0f, không cần sửa" % NEW_W)
            return
        assert abs(t["m_SizeDelta"]["x"] - OLD_W) < 1e-3, \
            "bề rộng lạ: %.1f (chờ %.0f)" % (t["m_SizeDelta"]["x"], OLD_W)

    blob = bytearray(open(LEVEL, "rb").read())
    n0 = len(blob)
    for pid, name in RECTS.items():
        pat = tail(trees[pid])
        hits = [i for i in range(len(blob) - len(pat) + 1) if blob[i:i + len(pat)] == pat]
        # hai rect giống nhau từng byte nên mỗi mẫu khớp đúng 2 lần; vá cả hai một lượt
        if len(hits) != len(RECTS):
            raise SystemExit("mỏ neo của pid %d khớp %d lần (chờ %d)" % (pid, len(hits), len(RECTS)))
        for h in hits:
            off = h + 24                    # bỏ qua anchorMin/Max + anchoredPosition
            cur, = struct.unpack_from("<f", blob, off)
            assert abs(cur - OLD_W) < 1e-3, "byte tại %d là %.1f" % (off, cur)
            struct.pack_into("<f", blob, off, NEW_W)
            print("   @%d  sizeDelta.x %.0f -> %.0f" % (off, cur, NEW_W))
        break                               # một mẫu đã bao cả hai rect

    assert len(blob) == n0, "kích thước file đổi"
    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(LEVEL, BACKUP)
        print("backup ->", BACKUP)
    open(LEVEL, "wb").write(blob)
    print("đã ghi", LEVEL, os.path.getsize(LEVEL))

    for o in UnityPy.load(LEVEL).objects:
        if o.path_id in RECTS and o.type.name == "RectTransform":
            t = o.read_typetree()
            print("  đọc lại pid %-4d size=(%.0f,%.0f) pos=(%.0f,%.0f)"
                  % (o.path_id, t["m_SizeDelta"]["x"], t["m_SizeDelta"]["y"],
                     t["m_AnchoredPosition"]["x"], t["m_AnchoredPosition"]["y"]))
            assert abs(t["m_SizeDelta"]["x"] - NEW_W) < 1e-3


main()
