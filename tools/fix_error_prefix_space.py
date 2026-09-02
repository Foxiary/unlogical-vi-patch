# -*- coding: utf-8 -*-
"""`[Error]` dính liền tiêu đề — chèn một dấu cách (`SceneReplayData`, bundle `json`).

Ba tiêu đề của Ending List mở đầu bằng tiền tố `[Error]`:

    #recollection_02  [Error]自己犠牲のペガサス   -> [Error]Pegasus của sự hy sinh
    #recollection_03  [Error]夢想家のグリフォン   -> [Error]Griffin của kẻ mộng mơ
    #recollection_04  [Error]合理主義のケルベロス -> [Error]Cerberus của chủ nghĩa duy lý

Bản gốc viết liền vì sau `]` là chữ Nhật — tiếng Nhật không cần dấu cách để tách chữ.
Bản dịch thì sau `]` là chữ Latin nên `]P` dính vào nhau, đọc như một từ. Chèn đúng
**một** dấu cách sau `]`, không đụng bất cứ ký tự nào khác.

`[Error]` ở đây là chữ hiển thị, không phải thẻ lệnh: `SceneReplayData.title.jp` được
TMP vẽ thẳng, không qua bộ phân tích `[...]` của kịch bản (ảnh chụp máy thật cho thấy
`[Error]` hiện nguyên văn trên màn hình).

**Hai chỗ phải đổi cùng lúc.** Ngoài danh sách Ending List, thẻ THE END sau mỗi BAD END
**vẽ lại chính chuỗi này thành tranh** (`fix_endcard_title.py` đọc `SceneReplayData`),
và ba ending 002/003/004 đều có thẻ. Sửa xong bảng thì phải chạy:

    python tools\\fix_endcard_title.py --apply

nếu không thẻ và danh sách lệch nhau đúng một dấu cách.

Sửa thẳng trên văn bản JSON (thay từng `"jp":"<cũ>"`, như `fix_music_title_case.py`) để
BOM và định dạng còn nguyên; so cấu trúc trước/sau, chỉ ba trường `title.jp` được khác.

    python tools\\fix_error_prefix_space.py [--apply]
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

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
BACKUP = os.path.join(ROOT, "_backup", "json.preerrorspace")
ASSET = "SceneReplayData"
PREFIX = "[Error]"
APPLY = "--apply" in sys.argv

# Ô chữ của một hàng Ending List sau bản vá marquee: mask 502 px, cỡ chữ ghim 32,
# `m_characterSpacing` 3,8 (xem fix_recollection_list.py / fix_recollection_marquee.py).
BOX_W, POINT, CHAR_SPACING, FONT = 502.0, 58.0, 3.8, 32.0


def width(s):
    return sum(A.glyph_advance(c) + CHAR_SPACING for c in s) * FONT / POINT


def rows(doc):
    return [it for g in doc["list"] for it in g["items"]]


def fixed(s):
    """Chuẩn hoá: đúng một dấu cách sau `]`. Chạy lại lần hai không đổi gì nữa."""
    return PREFIX + " " + s[len(PREFIX):].lstrip(" ") if s.startswith(PREFIX) else s


def main():
    env = UnityPy.load(BUNDLE)
    obj = next((o for o in env.objects
                if o.type.name == "TextAsset" and o.read().m_Name == ASSET), None)
    if obj is None:
        raise SystemExit("không thấy TextAsset %s trong %s" % (ASSET, BUNDLE))
    d = obj.read()
    raw = d.m_Script if isinstance(d.m_Script, str) else bytes(d.m_Script).decode("utf-8")
    before = json.loads(raw.lstrip("\ufeff"))

    out = raw
    n = 0
    for it in rows(before):
        old = it["title"]["jp"]
        if not old.startswith(PREFIX):
            continue
        new = fixed(old)
        needle = json.dumps(old, ensure_ascii=False)
        if out.count('"jp":' + needle) != 1:
            raise SystemExit("%r không xuất hiện đúng 1 lần trong %s" % (old, ASSET))
        mark = "giữ nguyên" if old == new else "%.0f -> %.0f px" % (width(old), width(new))
        print("  %-18s %-46s %s" % (it["label"], new, mark))
        if old != new:
            out = out.replace('"jp":' + needle,
                              '"jp":' + json.dumps(new, ensure_ascii=False), 1)
            n += 1

    after = json.loads(out.lstrip("\ufeff"))
    a, b = rows(before), rows(after)
    assert len(a) == len(b), "số mục đổi"
    for x, y in zip(a, b):
        assert x.keys() == y.keys() and all(x[k] == y[k] for k in x if k != "title"), \
            "trường ngoài title bị đổi: %s" % x["label"]
        assert x["title"].keys() == y["title"].keys()
        assert all(x["title"][k] == y["title"][k] for k in x["title"] if k != "jp"), \
            "slot EN/CN bị đổi: %s" % x["label"]
        assert y["title"]["jp"] == fixed(x["title"]["jp"]), "tiêu đề sai: %s" % x["label"]
    assert out.startswith("\ufeff") == raw.startswith("\ufeff")
    assert len(out) == len(raw) + n, "độ dài lệch, không chỉ chèn dấu cách"

    print("\nđổi %d/%d tiêu đề (khung chữ %.0f px — tiêu đề dài hơn thì chạy chữ)"
          % (n, len(a), BOX_W))
    if n == 0:
        print("không có gì để làm")
        return
    if not APPLY:
        print("CHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        shutil.copy2(BUNDLE, BACKUP)
        print("backup ->", BACKUP)
    d.m_Script = out
    d.save()
    blob = env.file.save(packer="lz4")          # bundle: bắt buộc lz4
    with open(BUNDLE, "wb") as f:
        f.write(blob)
    print("đã ghi %s (%s byte)" % (BUNDLE, format(os.path.getsize(BUNDLE), ",")))

    chk = next(o.read() for o in UnityPy.load(BUNDLE).objects
               if o.type.name == "TextAsset" and o.read().m_Name == ASSET)
    chk_raw = chk.m_Script if isinstance(chk.m_Script, str) else bytes(chk.m_Script).decode("utf-8")
    assert chk_raw == out, "đọc lại không khớp"
    print("đọc lại: khớp")
    print("\nNHỚ chạy lại thẻ THE END:  python tools\\fix_endcard_title.py --apply")


main()
