# -*- coding: utf-8 -*-
"""Replace a term inside one TextAsset of the StreamingAssets `json` bundle.

The bundle holds the UI/system data that has no tab in the upstream sheet
(DictionaryData, ChapterData, SceneReplayData, ScriptDialogData, MusicData,
MapData, AnimationTextData), so terminology fixes there have to be made here.

Edits the raw JSON text, so nothing but the term itself can change.

    python tools\\json_term.py DictionaryData "Thiên sứ tập sự" "Thiên thần tập sự"
    python tools\\json_term.py DictionaryData "..." "..." --apply
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

import UnityPy   # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")

args = [a for a in sys.argv[1:] if not a.startswith("--")]
APPLY = "--apply" in sys.argv
if len(args) < 3:
    raise SystemExit(__doc__)
ASSET, OLD, NEW = args[0], args[1], args[2]
BACKUP = os.path.join(ROOT, "_backup", "json.pre" + ASSET.lower()[:12] + "term")


def main():
    env = UnityPy.load(BUNDLE)
    obj = None
    for o in env.objects:
        if o.type.name == "TextAsset" and o.read().m_Name == ASSET:
            obj = o
            break
    if obj is None:
        raise SystemExit("%s not found in %s" % (ASSET, BUNDLE))
    d = obj.read()
    raw = d.m_Script
    if not isinstance(raw, str):
        raw = bytes(raw).decode("utf-8")

    n = raw.count(OLD)
    print("%s: %r xuất hiện %d lần" % (ASSET, OLD, n))
    if n == 0:
        raise SystemExit("không có gì để thay")

    before = json.loads(raw.lstrip("﻿"))
    out = raw.replace(OLD, NEW)
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

    b = dict(walk(before))
    a = dict(walk(after))
    assert b.keys() == a.keys(), "cấu trúc JSON đổi"
    diffs = [(k, b[k], a[k]) for k in b if b[k] != a[k]]
    print("số trường thay đổi: %d" % len(diffs))
    for k, x, y in diffs:
        print("   %s" % k)
        print("      %r" % x)
        print("   -> %r" % y)
    for k, x, y in diffs:
        assert isinstance(x, str) and x.replace(OLD, NEW) == y, "thay đổi ngoài dự kiến ở " + k

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
