# -*- coding: utf-8 -*-
"""Thu rect ô caption giữa màn (`EXTRAText`) 1920 → 1764 để TMP tự wrap trong lề an toàn.

Widget: `level10` TMP pid 898 `RenderCanvas_Final/EXTRALayer/EXTRAText`, RectTransform
pid **722**: anchors (0,5, 0,5), pivot (0,5, 0,5), anchoredPosition (0, 0), rect
**1920×720** — đúng bằng canvas, nên TMP wrap ở mép màn và dòng dài đè lên tam giác
watermark UL ở góc dưới-phải (lề 78 px mỗi bên, đo trên ảnh Ryujinx — xem
`fix_center_caption_wrap.py`).

Trước đây chặn bằng dữ liệu: caption nào quá 1764 px thì ngắt cứng theo dấu câu, câu không
có dấu câu thì ngắt theo từ. Ngắt theo từ là ngắt lấp chỗ, và nó lộ ra ở ô tóm tắt thẻ
SAVE/LOAD (731 px, 3 dòng): ảnh máy thật IMG_7241, `85/txt/0767` ra `thông tin có thể` đứng
một hàng rồi câu bị cắt. Thu rect thì TMP wrap ở 1764 cho cả 41 ô, không cần ngắt theo từ
nữa; pivot giữa nên rect co đều hai bên, chữ vẫn canh giữa màn, mỗi bên còn đúng 78 px.

Ngắt theo dấu câu đang có trong dữ liệu giữ nguyên (theo nhịp bản Nhật); ba ô ngắt theo từ
được `fix_center_caption_wrap.py` nối lại cùng đợt (02/09/2026).

`level10` không nhúng type tree nên vá byte tại chỗ, cùng cách `fix_adv_box_width.py`: mỏ
neo là PPtr `m_Father` + đuôi 10 float của RectTransform (anchorMin, anchorMax,
anchoredPosition, sizeDelta, pivot); `sizeDelta.x` nằm ở +12+24. Rect 1920×720 canh giữa
là hình học phổ biến trong scene nên riêng đuôi 10 float không đủ làm mỏ neo — phải kèm
cha (`EXTRALayer`, pid 791) và đòi khớp đúng một lần.

    python tools\\fix_caption_box_width.py             # chạy thử
    python tools\\fix_caption_box_width.py --apply
    python tools\\fix_caption_box_width.py --revert --apply
    python tools\\fix_caption_box_width.py --check     # exit 1 nếu rect chưa phải 1764
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
BACKUP = os.path.join(ROOT, "_backup", "level10.captionboxw")
APPLY = "--apply" in sys.argv
REVERT = "--revert" in sys.argv
CHECK = "--check" in sys.argv

RECT_PID, TMP_PID, FATHER_PID = 722, 898, 791
STOCK_W, SAFE_W = 1920.0, 1764.0
OLD_W, NEW_W = (SAFE_W, STOCK_W) if REVERT else (STOCK_W, SAFE_W)


def anchor(t):
    """PPtr m_Father + 10 float đuôi RectTransform — đúng thứ tự Unity serialize."""
    return struct.pack("<iq", t["m_Father"]["m_FileID"], t["m_Father"]["m_PathID"]) + struct.pack(
        "<ffffffffff",
        t["m_AnchorMin"]["x"], t["m_AnchorMin"]["y"],
        t["m_AnchorMax"]["x"], t["m_AnchorMax"]["y"],
        t["m_AnchoredPosition"]["x"], t["m_AnchoredPosition"]["y"],
        t["m_SizeDelta"]["x"], t["m_SizeDelta"]["y"],
        t["m_Pivot"]["x"], t["m_Pivot"]["y"])


def main():
    env = UnityPy.load(LEVEL)
    objs = {o.path_id: o for o in env.objects}
    o = objs.get(RECT_PID)
    if o is None or o.type.name != "RectTransform":
        raise SystemExit("pid %d không phải RectTransform" % RECT_PID)
    t = o.read_typetree()
    go = objs[t["m_GameObject"]["m_PathID"]].read_typetree()["m_Name"]
    tmp_go = struct.unpack_from("<iq", objs[TMP_PID].get_raw_data(), 0)[1]
    print("pid %d RectTransform của %s  size=(%.0f,%.0f) pos=(%.0f,%.0f) anchors=(%.2f,%.2f)-(%.2f,%.2f) pivot=(%.2f,%.2f)"
          % (RECT_PID, go, t["m_SizeDelta"]["x"], t["m_SizeDelta"]["y"],
             t["m_AnchoredPosition"]["x"], t["m_AnchoredPosition"]["y"],
             t["m_AnchorMin"]["x"], t["m_AnchorMin"]["y"], t["m_AnchorMax"]["x"], t["m_AnchorMax"]["y"],
             t["m_Pivot"]["x"], t["m_Pivot"]["y"]))
    assert go == "EXTRAText", "GameObject là %r, chờ EXTRAText" % go
    assert tmp_go == t["m_GameObject"]["m_PathID"], "TMP pid %d không nằm trên GameObject này" % TMP_PID
    assert t["m_Father"]["m_PathID"] == FATHER_PID, "cha là pid %d, chờ %d" % (t["m_Father"]["m_PathID"], FATHER_PID)
    assert abs(t["m_Pivot"]["x"] - 0.5) < 1e-6 and abs(t["m_AnchoredPosition"]["x"]) < 1e-6, \
        "pivot/anchoredPosition lạ — thu rect sẽ làm lệch tâm"
    assert abs(t["m_AnchorMin"]["x"] - 0.5) < 1e-6 and abs(t["m_AnchorMax"]["x"] - 0.5) < 1e-6, \
        "anchors không phải điểm giữa — sizeDelta không còn là bề rộng tuyệt đối"

    cur_w = t["m_SizeDelta"]["x"]
    if CHECK:
        if abs(cur_w - SAFE_W) < 1e-3:
            print("OK — rect EXTRAText = %.0f px, TMP wrap trong lề an toàn" % SAFE_W)
            return
        raise SystemExit("rect EXTRAText = %.0f px (chờ %.0f) — chạy `python tools\\fix_caption_box_width.py --apply`"
                         % (cur_w, SAFE_W))
    if abs(cur_w - NEW_W) < 1e-3:
        print("đã là %.0f, không cần sửa" % NEW_W)
        return
    assert abs(cur_w - OLD_W) < 1e-3, "bề rộng lạ: %.1f (chờ %.0f)" % (cur_w, OLD_W)

    blob = bytearray(open(LEVEL, "rb").read())
    n0 = len(blob)
    pat = anchor(t)
    hits = [i for i in range(len(blob) - len(pat) + 1) if blob[i:i + len(pat)] == pat]
    if len(hits) != 1:
        raise SystemExit("mỏ neo khớp %d lần (chờ 1)" % len(hits))
    off = hits[0] + 12 + 24                 # bỏ PPtr cha, anchorMin/Max, anchoredPosition
    cur, = struct.unpack_from("<f", blob, off)
    assert abs(cur - OLD_W) < 1e-3, "byte tại %d là %.1f" % (off, cur)
    struct.pack_into("<f", blob, off, NEW_W)
    print("   @%d  sizeDelta.x %.0f -> %.0f  (lề mỗi bên %.0f px)" % (off, cur, NEW_W, (STOCK_W - NEW_W) / 2))
    assert len(blob) == n0, "kích thước file đổi"

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(LEVEL, BACKUP)
        print("backup ->", BACKUP)
    old = open(LEVEL, "rb").read()
    open(LEVEL, "wb").write(blob)
    print("đã ghi", LEVEL, os.path.getsize(LEVEL))

    # đọc lại: đúng một object đổi, đúng 4 byte
    diff = [i for i in range(len(old)) if old[i] != blob[i]]
    assert diff and diff[0] >= off and diff[-1] < off + 4, "đổi ngoài dải 4 byte: %s" % diff[:8]
    env2 = UnityPy.load(LEVEL)
    t2 = next(o for o in env2.objects if o.path_id == RECT_PID).read_typetree()
    assert abs(t2["m_SizeDelta"]["x"] - NEW_W) < 1e-3
    for k in ("m_AnchorMin", "m_AnchorMax", "m_AnchoredPosition", "m_Pivot"):
        assert t2[k] == t[k], "%s đổi" % k
    assert abs(t2["m_SizeDelta"]["y"] - t["m_SizeDelta"]["y"]) < 1e-6
    print("  đọc lại pid %d size=(%.0f,%.0f), %d byte đổi, phần còn lại nguyên vẹn"
          % (RECT_PID, t2["m_SizeDelta"]["x"], t2["m_SizeDelta"]["y"], len(diff)))


main()
