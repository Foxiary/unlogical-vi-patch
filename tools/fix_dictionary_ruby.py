# -*- coding: utf-8 -*-
"""Clean up the `ruby` field of DictionaryData.

30 of the 80 entries carry a third field, `ruby`, next to `title` and `text`.
It is the furigana drawn above the title on the archive screen (`level10`
pid 896, `DictionaryLayer/…/Mask_Ryby/Ruby (TMP)`), and all 30 were still the
untouched Japanese — so the archive floated kana over Vietnamese titles.

24 of them are hiragana readings of the old kanji title and mean nothing once
the title is Vietnamese; KiEL's reading is dropped for the same reason. The
remaining five are katakana loanwords that ARE the English term, so they carry
over as the English word.

`no=400` also loses its invented "(Sync)": the stock title is 適合 read
マッチング, and every ruby tag in the script glosses it `Matching`. "Sync"
appeared exactly once in the whole patch and nowhere in the Japanese.

    python tools\\fix_dictionary_ruby.py [--apply]
"""
import io
import json
import os
import re
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
BACKUP = os.path.join(ROOT, "_backup", "json.predicruby")
APPLY = "--apply" in sys.argv

# katakana readings that are really the English term.  Ruby is set in CAPITALS —
# at 12 px it reads far better than mixed case.
TRANSLATE = {
    112: "OPERATOR",    # オペレーター  — Ban điều hành
    212: "SPIRIT",      # スピリット    — Thiên thần tập sự
    250: "",            # ダウ          — trùng y hệt tiêu đề "DAW", bỏ hẳn
    255: "TRAINER",     # トレーナー    — Người nuôi dưỡng
    400: "MATCHING",    # マッチング    — Sự tương thích
}
# Ruby nào còn kana thì xoá trắng; ruby đã là chữ Latin thì để nguyên cho
# `fix_dictionary_titles.py` quản — nếu không, chạy lại file này sẽ xoá sạch
# những ruby mà bước kia vừa thêm.
TITLES = {
    400: ("Sự tương thích (Sync)", "Sự tương thích"),
}
KANA = re.compile(r"[぀-ヿ]")


def main():
    env = UnityPy.load(BUNDLE)
    obj = next((o for o in env.objects
                if o.type.name == "TextAsset" and o.read().m_Name == "DictionaryData"), None)
    if obj is None:
        raise SystemExit("DictionaryData not found in " + BUNDLE)
    d = obj.read()
    raw = d.m_Script
    if not isinstance(raw, str):
        raw = bytes(raw).decode("utf-8")
    data = json.loads(raw.lstrip("﻿"))

    edits = []          # (mô tả, chuỗi cũ, chuỗi mới)
    for it in data["data"]:
        no = it["no"]
        if "ruby" in it:
            old = it["ruby"]["jp"]
            new = TRANSLATE[no] if no in TRANSLATE else ("" if KANA.search(old) else old)
            if old != new:
                edits.append(("no=%-4s ruby   %-24r -> %r  [%s]" % (no, old, new, it["title"]["jp"]),
                              '"ruby":{"jp":"%s"}' % old,
                              '"ruby":{"jp":"%s"}' % new))
        if no in TITLES and it["title"]["jp"] != TITLES[no][1]:
            old, new = TITLES[no]
            assert it["title"]["jp"] == old, "tiêu đề no=%s đã khác: %r" % (no, it["title"]["jp"])
            edits.append(("no=%-4s title  %-24r -> %r" % (no, old, new),
                          '"title":{"jp":"%s"}' % old,
                          '"title":{"jp":"%s"}' % new))

    blanked = sum(1 for e in edits if e[2].endswith('""}') and '"ruby"' in e[1])
    print("số thay đổi: %d   (xoá trắng %d ruby, dịch %d ruby, sửa %d tiêu đề)"
          % (len(edits), blanked, len(TRANSLATE), len(TITLES)))
    for desc, _, _ in edits:
        print("  " + desc)

    out = raw
    for desc, a, b in edits:
        n = out.count(a)
        if n != 1:
            raise SystemExit("khớp %d lần (phải là 1) cho: %s" % (n, a))
        out = out.replace(a, b)

    after = json.loads(out.lstrip("﻿"))

    def walk(x, path=""):
        if isinstance(x, dict):
            for k, v in x.items():
                yield from walk(v, path + "/" + str(k))
        elif isinstance(x, list):
            for i, v in enumerate(x):
                yield from walk(v, path + "[%d]" % i)
        else:
            yield path, x

    b0, b1 = dict(walk(data)), dict(walk(after))
    assert b0.keys() == b1.keys(), "cấu trúc JSON đổi"
    diffs = [k for k in b0 if b0[k] != b1[k]]
    print("\ntrường thay đổi: %d (dự kiến %d)" % (len(diffs), len(edits)))
    assert len(diffs) == len(edits)
    assert all(k.endswith("/ruby/jp") or k.endswith("/title/jp") for k in diffs)

    left = [it["no"] for it in after["data"]
            if "ruby" in it and any("぀" <= c <= "ヿ" for c in it["ruby"]["jp"])]
    print("ruby còn kana sau khi sửa:", left or "không còn")

    if not APPLY:
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
