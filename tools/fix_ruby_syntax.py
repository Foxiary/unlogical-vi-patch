# -*- coding: utf-8 -*-
"""Repair the malformed ruby tags in ScenarioData — punctuation only.

Every edit here is mechanical: a stray space or a stray apostrophe inside the
tag.  Not one word of the translation changes, and no tag whose base is still
Japanese is touched — those need a translator's decision and are only reported
(see tools\\README.md).

The five tags, with what the Japanese script has:

  [Châu Ngọc 'Cherish]                 space before the separator
      JP [珠玉'チェリッシュ]
  [Hỏa Thủ' kỹ năng]                   space after the separator
      JP [火守'スキル]
  [dic no=252 text=điều chỉnh'tuning'] trailing apostrophe
      JP [dic no=252 text=チューニング]   (no ruby at all)
  [見習い天使'Spirit']                  trailing apostrophe
      JP [見習い天使'スピリット]           (base still Japanese - reported)
  [dic no=361 text=Fallin' Gals]       a band name, NOT a ruby
      JP [dic no=361 text=フォーリンギャルズ]
      The engine splits a tag on ', so this renders as "Fallin" with "Gals"
      floating above it.  Swapping U+0027 for the typographic U+2019 the rest
      of the script already uses keeps the name and kills the false ruby.

Fixing a tag changes its width, so the messages carrying them are re-wrapped
from scratch afterwards — otherwise the break points no longer match what TMP
will draw and the annotation drifts again.

    python tools\\fix_ruby_syntax.py            # dry run
    python tools\\fix_ruby_syntax.py --apply
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

import UnityPy                      # noqa: E402
import adv_layout as L              # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "scenario01.prerubysyntax")

APPLY = "--apply" in sys.argv

# id -> (broken tag, repaired tag)
REPAIRS = {
    "108/txt/0174": ("[Châu Ngọc 'Cherish]", "[Châu Ngọc'Cherish]"),
    "75/txt/1089": ("[Hỏa Thủ' kỹ năng]", "[Hỏa Thủ'kỹ năng]"),
    "72/txt/0380": ("[dic no=252 text=điều chỉnh'tuning']", "[dic no=252 text=điều chỉnh'tuning]"),
    "106/txt/1045": ("[見習い天使'Spirit']", "[見習い天使'Spirit]"),
    "95/txt/0236": ("[dic no=361 text=Fallin' Gals]", "[dic no=361 text=Fallin’ Gals]"),
}


def enc(s):
    return json.dumps(s, ensure_ascii=False)[1:-1]


def main():
    env = UnityPy.load(BUNDLE)
    obj = next((o for o in env.objects
                if o.type.name == "TextAsset" and o.read().m_Name == "ScenarioData"), None)
    if obj is None:
        raise SystemExit("ScenarioData not found in " + BUNDLE)
    d = obj.read()
    raw = d.m_Script
    data = json.loads(raw.lstrip("﻿"))

    plan = []
    for e in data["target"]:
        sid = e["scenarioID"]
        for j, t in enumerate(e["text"]):
            rid = "%d/txt/%04d" % (sid, j)
            if rid not in REPAIRS or not isinstance(t, str):
                continue
            bad, good = REPAIRS[rid]
            if bad not in t:
                print("!! %s no longer contains %r" % (rid, bad))
                continue
            flat = t.replace("\n", " ").replace(bad, good)
            size, lines = L.autosize(flat)
            new = "\n".join(lines)
            plan.append((rid, size, t, new))

    missing = set(REPAIRS) - {p[0] for p in plan}
    if missing:
        print("!! not located:", sorted(missing))

    print("tags repaired:", len(plan))
    for rid, size, old, new in plan:
        print("\n--- %s   size %s   %d lines" % (rid, size, len(new.split("\n"))))
        for l in old.split("\n"):
            print("   OLD |", l)
        for l in new.split("\n"):
            print("   NEW |", l)

    out = raw
    for rid, size, old, new in plan:
        a, b = enc(old), enc(new)
        n1 = out.count('"' + a + '"')
        n2 = out.count("\\n" + a + "\\n")
        if n1:
            out = out.replace('"' + a + '"', '"' + b + '"')
        if n2:
            out = out.replace("\\n" + a + "\\n", "\\n" + b + "\\n")
        if not n1 and not n2:
            print("!! %s: text not found in the raw JSON" % rid)

    new_data = json.loads(out.lstrip("﻿"))
    changed = 0
    for a, b in zip(data["target"], new_data["target"]):
        for k in a:
            if k not in ("text", "scriptText"):
                assert a[k] == b[k], "unexpected change in " + k
        for x, y in zip(a["text"], b["text"]):
            if x != y:
                changed += 1
    print("\ntext[] entries changed:", changed)

    bad = [(rid, l) for rid, size, _, new in plan for l in new.split("\n")
           if L.line_width(l, size) > L.BOX_W]
    print("emitted lines wider than the box:", len(bad))

    if not APPLY:
        print("\nDRY RUN — pass --apply to write the bundle")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(BUNDLE, BACKUP)
        print("backup ->", BACKUP)
    d.m_Script = out
    d.save()
    blob = env.file.save(packer="lz4")
    with open(BUNDLE, "wb") as f:
        f.write(blob)
    print("written", BUNDLE, os.path.getsize(BUNDLE))


main()
