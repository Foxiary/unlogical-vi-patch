# -*- coding: utf-8 -*-
"""Gỡ ngắt dòng cứng trong tóm tắt chương, trả việc xuống dòng cho TextMeshPro.

Cả 43 tóm tắt trong `ChapterData` đều đã được ngắt tay ở ≤18 ký tự để tuân theo
luật 18 ký tự của code game. Vá code cho `DefaultMaxCharsPerLine` trả về 0 nên
không còn ai ép ngắt nữa — nhưng những `\\n` đã nằm sẵn trong chuỗi thì vẫn giữ
nguyên bố cục cũ, nên màn hình **không đổi gì cả**. Phải gỡ chúng ra.

Khung `ChapterSelect/Story/SynopsisTitle/Mask` = 620×474, `MainText` lề trái 11
→ bề rộng dùng được 609. fontSize 31.25, charSpacing 5.8, lineSpacing 33
→ bước dòng = fontSize × (116/58 + 33/100) = 2.33 × fontSize.

    python tools\\unwrap_synopsis.py [--apply]
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

import UnityPy        # noqa: E402
import adv_layout as L  # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
BACKUP = os.path.join(ROOT, "_backup", "json.presynunwrap")
APPLY = "--apply" in sys.argv

BOX_W, BOX_H = 609.0, 474.0
SIZE_MAX, SIZE_MIN = 31.25, 18.0
CSPACE, LINESPACE_PCT = 5.8, 33.0


def syn(it):
    v = it["synopsis"]
    return v["jp"] if isinstance(v, dict) else v


def width(s, size):
    return sum((L.glyph_advance(c) + CSPACE) for c in s) * size / L.POINT_SIZE


def pitch(size):
    return size * (L.UNITS_LINE_HEIGHT / L.POINT_SIZE + LINESPACE_PCT / 100.0)


def height(n, size):
    return (n - 1) * pitch(size) + size * (L.UNITS_ASC - L.UNITS_DESC) / L.POINT_SIZE


def wrap(text, size):
    lines, cur = [], ""
    for word in text.split(" "):
        cand = word if not cur else cur + " " + word
        if cur and width(cand, size) > BOX_W:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def fit(text):
    size = SIZE_MAX
    while size >= SIZE_MIN:
        lines = wrap(text, size)
        if height(len(lines), size) <= BOX_H:
            return size, lines
        size -= 0.25
    return None, wrap(text, SIZE_MIN)


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
    blanks = sum(1 for it in items if "\n\n" in (syn(it) or ""))
    print("mục: %d   có dòng trống (ngắt đoạn thật): %d" % (len(items), blanks))

    out = raw
    changed, worst, fails = 0, (99.0, None), []
    for it in items:
        old = syn(it)
        if not old or "\n" not in old:
            continue
        new = " ".join(x.strip() for x in old.split("\n") if x.strip())
        size, lines = fit(new)
        if size is None:
            fails.append((it["label"], len(new), len(lines)))
            size = SIZE_MIN
        if size < worst[0]:
            worst = (size, it["label"])
        a = json.dumps(old, ensure_ascii=False)
        b = json.dumps(new, ensure_ascii=False)
        n = out.count(a)
        if n != 1:
            raise SystemExit("chuỗi khớp %d lần ở %s" % (n, it["label"]))
        out = out.replace(a, b)
        changed += 1

    print("gỡ ngắt dòng: %d mục" % changed)
    print("cỡ chữ nhỏ nhất phải dùng: %.2f  (%s)" % worst)
    print("mục không vừa kể cả ở cỡ %.0f: %d" % (SIZE_MIN, len(fails)))
    for lb, n, ln in fails:
        print("   %-14s %d ký tự -> %d dòng" % (lb, n, ln))

    after = json.loads(out.lstrip("﻿"))
    assert len(after["list"]) == len(data["list"])
    diffs = sum(1 for g0, g1 in zip(data["list"], after["list"])
                for i0, i1 in zip(g0["items"], g1["items"]) if i0 != i1)
    print("mục thay đổi khi so lại: %d" % diffs)
    assert diffs == changed

    if not APPLY:
        ex = next(it for it in items if syn(it))
        print("\nví dụ %s:" % ex["label"])
        for ln in fit(" ".join(x.strip() for x in syn(ex).split("\n") if x.strip()))[1]:
            print("   [%2d] %s" % (len(ln), ln))
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
