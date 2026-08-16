# -*- coding: utf-8 -*-
"""Hard-wrap every ADV message in ScenarioData that carries a ruby annotation.

Ruby_Text lays the annotation out against the message's OWN line array (the
text split on \\n).  It knows nothing about TextMeshPro's automatic word wrap,
so as soon as the base word is pushed onto the next line by that wrap, the ruby
stays behind at the pre-wrap spot — one line too high and far off to the right.
The Japanese script never hits this because every message is hard-wrapped at
source; the Vietnamese one collapsed each message onto a single line.

The fix is to treat the ruby-bearing messages the way the Japanese ones are
treated: real newlines at the points TMP would have wrapped, computed from the
real font metrics and always a hair inside the box so TMP finds nothing left to
wrap.  Only \\n insertions are made, straight into the raw JSON text, so
nothing else in the 17 MB asset can drift.

    python tools\\wrap_ruby_lines.py            # dry run + report
    python tools\\wrap_ruby_lines.py --apply    # back up, patch, repack
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

import UnityPy                      # noqa: E402
import adv_layout as L              # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "scenario01.prerubywrap")
REPORT = os.path.join(HERE, "rubywrap_report.txt")

RUBY_TAG = re.compile(r"\[[^\[\]\n]*'[^\[\]\n]*\]")
PLAYER_TOKEN = "[主人公]"
LONG_NAME = "Kannakanna"    # headroom in case the player typed a longer name

APPLY = "--apply" in sys.argv


def wrap_message(msg):
    if PLAYER_TOKEN in msg:
        old = L.DEFAULT_PLAYER_NAME
        L.DEFAULT_PLAYER_NAME = LONG_NAME
        try:
            return L.autosize(msg)
        finally:
            L.DEFAULT_PLAYER_NAME = old
    return L.autosize(msg)


def enc(s):
    """The message as it appears inside the JSON text."""
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

    plan, meta = {}, []
    for i, e in enumerate(data["target"]):
        for j, t in enumerate(e.get("text") or []):
            if not isinstance(t, str) or "\n" in t or not RUBY_TAG.search(t):
                continue
            if t in plan:
                continue
            size, lines = wrap_message(t)
            if len(lines) < 2:
                continue
            new = "\n".join(lines)
            assert "".join(new.split()) == "".join(t.split()), "wrap altered the text"
            plan[t] = new
            meta.append((i, j, size, len(lines), t, new))

    print("ruby messages needing a break: %d" % len(plan))
    if meta:
        widest = max((L.line_width(l, s) / L.BOX_W)
                     for _, _, s, _, _, new in meta for l in new.split("\n"))
        print("widest emitted line: %.1f%% of the %d px box" % (widest * 100, L.BOX_W))
        print("line counts:", {n: sum(1 for m in meta if m[3] == n)
                               for n in sorted({m[3] for m in meta})})

        with open(REPORT, "w", encoding="utf-8") as f:
            for i, j, size, n, t, new in meta:
                f.write("--- entry %d text[%d]  size %s  %d lines\n" % (i, j, size, n))
                f.write("OLD " + t + "\n")
                for l in new.split("\n"):
                    f.write("NEW " + l + "\n")
                f.write("\n")
        print("report ->", REPORT)

    out = raw
    hits_text = hits_script = 0
    missing = []
    for t, new in plan.items():
        a, b = enc(t), enc(new)
        n1 = out.count('"' + a + '"')
        n2 = out.count("\\n" + a + "\\n")
        if not n1 and not n2:
            missing.append(t)
            continue
        if n1:
            out = out.replace('"' + a + '"', '"' + b + '"')
            hits_text += n1
        if n2:
            out = out.replace("\\n" + a + "\\n", "\\n" + b + "\\n")
            hits_script += n2
    print("replaced in text[]: %d   in scriptText: %d   not found: %d"
          % (hits_text, hits_script, len(missing)))

    new_data = json.loads(out.lstrip("﻿"))
    old_t, new_t = data["target"], new_data["target"]
    assert len(old_t) == len(new_t)
    changed = 0
    for a, b in zip(old_t, new_t):
        assert a.keys() == b.keys()
        for k in a:
            if k not in ("text", "scriptText"):
                assert a[k] == b[k], "unexpected change in " + k
        assert len(a["text"]) == len(b["text"])
        for x, y in zip(a["text"], b["text"]):
            if x != y:
                assert plan.get(x) == y, "text[] changed in an unplanned way"
                changed += 1
    print("verified: only planned text[] edits (%d) plus their scriptText mirrors" % changed)

    bad = []
    for e in new_t:
        for t in e["text"]:
            if not isinstance(t, str) or not RUBY_TAG.search(t):
                continue
            if "\n" in t:
                if L.fits(t.split("\n")) is None:
                    bad.append(t)
            elif len(L.autosize(t)[1]) > 1:
                bad.append(t)
    print("ruby messages TMP would still re-wrap:", len(bad))

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
