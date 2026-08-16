# -*- coding: utf-8 -*-
"""Ending List (Recollection) — tiêu đề tràn khung rồi đè lên dòng dưới.

Mỗi dòng của danh sách là prefab `RecollectionButton` trong
`sharedassets21.assets` (bundle riêng của `level21`, cảnh Recollection):

    RecollectionButton   rect 596 x 51
      Off/LeftParts      icon 36 x 44 ở x = 43..79
      Text  (pid 169)    stretch kín ô, margin trái 94  ->  bề rộng chữ 502

`Text` để `m_TextWrappingMode = 1` (Normal) và **tắt** auto-size ở cỡ 32, còn
`m_overflowMode = 0` (Overflow) — nên tiêu đề nào dài quá 502 px thì xuống dòng
thứ hai và **vẽ tràn ra ngoài ô cao 51 px**, đè thẳng lên dòng kế tiếp. Chuỗi
mẫu của bản gốc là `ああああ五ああああ十あああ四` = 14 chữ toàn rộng, tức khung
này vốn chỉ được thiết kế cho tiêu đề tiếng Nhật ngắn.

16/38 tiêu đề tiếng Việt trong `SceneReplayData` vượt 502 px.

Cách sửa: `m_TextWrappingMode = 0` (NoWrap) + bật auto-size `[FONT_MIN, 32]`.
NoWrap thì auto-size chỉ còn co theo **bề rộng**, một dòng duy nhất, không bao
giờ đụng vào ô bên dưới. `m_fontSizeMax` phải ghim đúng `m_fontSize` gốc (32),
vì auto-size chọn cỡ LỚN NHẤT vừa khung và giá trị gốc `m_fontSizeMax = 72` sẽ
thổi phồng những tiêu đề ngắn.

    python tools\\fix_recollection_list.py            # chạy thử
    python tools\\fix_recollection_list.py --apply    # backup, vá, ghi

Chạy lại vô hại: đã ở trạng thái đích thì bỏ qua.
"""
import io
import json
import os
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy            # noqa: E402
import adv_layout as A    # noqa: E402

APPLY = "--apply" in sys.argv

STOCK = r"D:\Downloads\UNLOGICAL_v2\Data\sharedassets21.assets"
TARGET = os.path.join(ROOT, "romfs", "Data", "sharedassets21.assets")
BACKUP = os.path.join(ROOT, "_backup", "sharedassets21.assets.prerecolle")
UI_JP = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
JSON_BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")

TEXT_PID = 169           # TextMeshProUGUI trên GameObject 118 ("Text")
BOX_W = 596.0 - 94.0     # rect 596, margin trái 94, phải 0
POINT = 58.0             # FOT-NewRodinProN-DB SDF
CHAR_SPACING = 3.8       # m_characterSpacing của chính component này
FONT_MAX = 32.0
FONT_MIN = 17.0


def width(s, fs=FONT_MAX):
    """Bề rộng một dòng, cùng mô hình đã hiệu chuẩn trong adv_layout."""
    return sum(A.glyph_advance(c) + CHAR_SPACING for c in s) * fs / POINT


def tmp_nodes():
    """`sharedassets21.assets` không nhúng type tree — mượn của bundle ui_jp."""
    env = UnityPy.load(UI_JP)
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            tt = o.read_typetree()
        except Exception:
            continue
        if isinstance(tt, dict) and "m_enableAutoSizing" in tt:
            return o.serialized_type.nodes
    raise SystemExit("không tìm được type tree của TMP trong " + UI_JP)


def titles():
    env = UnityPy.load(JSON_BUNDLE)
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        if d.m_Name != "SceneReplayData":
            continue
        raw = d.m_Script
        if not isinstance(raw, str):
            raw = bytes(raw).decode("utf-8")
        data = json.loads(raw.lstrip("\ufeff"))
        return [(it["label"], it["title"]["jp"])
                for g in data["list"] for it in g["items"]]
    raise SystemExit("không thấy SceneReplayData")


def report():
    rows = titles()
    over = [(lab, t, width(t)) for lab, t in rows if width(t) > BOX_W]
    print("tiêu đề: %d, bề rộng khung %.0f px, cỡ chữ gốc %.0f" %
          (len(rows), BOX_W, FONT_MAX))
    print("tràn khung ở cỡ 32: %d" % len(over))
    for lab, t, w in sorted(over, key=lambda r: -r[2]):
        print("   %-20s %6.1f px -> cần cỡ %5.1f   %s" %
              (lab, w, FONT_MAX * BOX_W / w, t))
    worst = max(width(t) for _, t in rows)
    print("cỡ nhỏ nhất sẽ dùng: %.1f (FONT_MIN = %.0f)" %
          (FONT_MAX * BOX_W / worst, FONT_MIN))
    if FONT_MAX * BOX_W / worst < FONT_MIN:
        print("   !! FONT_MIN quá cao, vẫn còn tiêu đề bị cắt")


def main():
    report()
    print()

    if not os.path.exists(TARGET):
        print("romfs chưa có sharedassets21.assets — sẽ chép từ bản gốc 1.0.2")
        src = STOCK
    else:
        src = TARGET
    if not os.path.exists(src):
        raise SystemExit("không thấy " + src)

    nodes = tmp_nodes()
    env = UnityPy.load(src)
    obj = next((o for o in env.objects if o.path_id == TEXT_PID), None)
    if obj is None or obj.type.name != "MonoBehaviour":
        raise SystemExit("không thấy MonoBehaviour pid %d trong %s" % (TEXT_PID, src))
    tt = obj.read_typetree(nodes=nodes)
    if tt["m_GameObject"]["m_PathID"] != 118:
        raise SystemExit("pid %d không nằm trên GameObject 118" % TEXT_PID)

    want = {
        "m_TextWrappingMode": 0,      # NoWrap — không bao giờ tràn xuống dòng 2
        "m_enableAutoSizing": 1,
        "m_fontSizeMin": FONT_MIN,
        "m_fontSizeMax": FONT_MAX,    # = m_fontSize gốc, đừng để 72
    }
    print("pid %d (RecollectionButton/Text), m_fontSize = %s" % (TEXT_PID, tt["m_fontSize"]))
    changed = False
    for k, v in want.items():
        cur = tt[k]
        if cur != v:
            print("   %-20s %r -> %r" % (k, cur, v))
            changed = True
        else:
            print("   %-20s %r (giữ nguyên)" % (k, cur))
    if not changed and src == TARGET:
        print("\nđã ở trạng thái đích, không có gì để làm")
        return

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(src, BACKUP)
        print("backup ->", BACKUP)

    tt.update(want)
    obj.save_typetree(tt, nodes)
    blob = env.file.save()
    with open(TARGET, "wb") as f:
        f.write(blob)
    print("đã ghi %s (%d byte)" % (TARGET, os.path.getsize(TARGET)))


main()
