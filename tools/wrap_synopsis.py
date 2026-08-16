# -*- coding: utf-8 -*-
"""Ngắt dòng tóm tắt chương theo TỪ, đúng bề rộng khung.

`SetNoteTextFromString` cắt cứng mỗi `DefaultMaxCharsPerLine` ký tự, không nhìn
khoảng trắng — để dữ liệu thành đoạn liền thì ra `…một nh / à sáng tạo…`. Nhưng
nó **tôn trọng `\\n` có sẵn**: chỉ đoạn nào dài quá mới bị cắt. (Bằng chứng: bản
dịch cũ ngắt tay ≤18 và hiển thị đúng theo từ, và phép thử `<size=21.5>` trước
đây cho thấy nó đếm 18 ký tự *trong từng dòng đã lưu*.)

Nên cách đúng là ngắt sẵn theo từ ở phía dữ liệu, rồi đặt hằng số trong bản vá
cao hơn dòng dài nhất để engine không bao giờ phải cắt.

Khung: `SynopsisTitle/Mask` 620×474, `MainText` lề trái 11 → 609 px dùng được,
fontSize 31.25, charSpacing 5.8, lineSpacing 33 → bước dòng 72.8, 7 dòng/trang.

    python tools\\wrap_synopsis.py [--apply]
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

import UnityPy         # noqa: E402
import adv_layout as L  # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
BACKUP = os.path.join(ROOT, "_backup", "json.presynwordwrap")
APPLY = "--apply" in sys.argv

BOX_W, SIZE, CSPACE = 609.0, 31.25, 5.8
SAFETY = 0.97          # mô hình đo hơi rộng hơn thực tế, chừa mép cho chắc
LIMIT = BOX_W * SAFETY


def width(s):
    return sum((L.glyph_advance(c) + CSPACE) for c in s) * SIZE / L.POINT_SIZE


def wrap(text):
    lines, cur = [], ""
    for word in text.split(" "):
        cand = word if not cur else cur + " " + word
        if cur and width(cand) > LIMIT:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def syn(it):
    v = it["synopsis"]
    return v["jp"] if isinstance(v, dict) else v


def main():
    env = UnityPy.load(BUNDLE)
    obj = next((o for o in env.objects
                if o.type.name == "TextAsset" and o.read().m_Name == "ChapterData"), None)
    if obj is None:
        raise SystemExit("không thấy ChapterData")
    d = obj.read()
    raw = d.m_Script
    if not isinstance(raw, str):
        raw = bytes(raw).decode("utf-8")
    data = json.loads(raw.lstrip("﻿"))
    items = [it for g in data["list"] for it in g["items"]]

    out = raw
    changed = 0
    max_chars, max_px, max_lines = 0, 0.0, 0
    worst_line, worst_item = "", ""
    for it in items:
        old = syn(it)
        if not old:
            continue
        flat = " ".join(x.strip() for x in old.split("\n") if x.strip())
        lines = wrap(flat)
        new = "\n".join(lines)
        for ln in lines:
            if len(ln) > max_chars:
                max_chars, worst_line = len(ln), ln
            if width(ln) > max_px:
                max_px = width(ln)
        if len(lines) > max_lines:
            max_lines, worst_item = len(lines), it["label"]
        if new == old:
            continue
        a = json.dumps(old, ensure_ascii=False)
        b = json.dumps(new, ensure_ascii=False)
        if out.count(a) != 1:
            raise SystemExit("chuỗi khớp %d lần ở %s" % (out.count(a), it["label"]))
        out = out.replace(a, b, 1)
        changed += 1

    print("mục ngắt lại: %d / %d" % (changed, len(items)))
    print("dòng dài nhất: %d ký tự — %r" % (max_chars, worst_line))
    print("dòng rộng nhất: %.0f px / %.0f (%.1f%%)" % (max_px, BOX_W, max_px / BOX_W * 100))
    print("nhiều dòng nhất: %d dòng (%s) -> %d trang 7 dòng"
          % (max_lines, worst_item, -(-max_lines // 7)))
    print("\n=> hằng số DefaultMaxCharsPerLine phải >= %d để engine không cắt thêm" % max_chars)

    after = json.loads(out.lstrip("﻿"))
    assert len(after["list"]) == len(data["list"])
    for g0, g1 in zip(data["list"], after["list"]):
        for i0, i1 in zip(g0["items"], g1["items"]):
            for k in i0:
                if k != "synopsis":
                    assert i0[k] == i1[k], "đổi ngoài dự kiến ở " + k
            a0 = syn(i0).replace("\n", " ").replace("  ", " ")
            a1 = syn(i1).replace("\n", " ").replace("  ", " ")
            assert "".join(a0.split()) == "".join(a1.split()), "mất chữ ở " + i0["label"]
    print("kiểm tra: không mất chữ, không đổi trường nào khác")

    if not APPLY:
        ex = next(it for it in items if syn(it))
        print("\nví dụ %s:" % ex["label"])
        for ln in wrap(" ".join(x.strip() for x in syn(ex).split("\n") if x.strip()))[:8]:
            print("   [%2d ký tự %5.0f px] %s" % (len(ln), width(ln), ln))
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(BUNDLE, BACKUP)
        print("backup ->", BACKUP)
    d.m_Script = out
    d.save()
    blob = env.file.save(packer="lz4")
    with open(BUNDLE, "wb") as f:
        f.write(blob)
    print("đã ghi", BUNDLE, os.path.getsize(BUNDLE))


main()
