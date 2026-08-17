# -*- coding: utf-8 -*-
"""Post-merge gate: no message may LOSE a hard line break or a leading indent.

A sheet merge writes `text[]` from cells that are one flat line, so it flattens
layout that only exists in the build.  This has already happened twice — 1 530
breaks across six `json` assets in one pass, and every `　` indent of the novel
lists.  Nothing offline caught either; both were spotted on screen.

So diff the packed bundle against the pre-merge backup, per message, on the two
things a flat cell cannot carry:

    real newlines   U+000A
    indented lines  a line starting with 　 (U+3000) or a space

Losing either is an error; gaining is fine (that is what the fixers do).

    python tools\\check_layout_breaks.py                      # so với backup mới nhất
    python tools\\check_layout_breaks.py _backup\\scenario01.novellist
    python tools\\check_layout_breaks.py --json               # gate cho bundle json

Exit code 1 when anything was lost, so it can sit next to `check_scripts.py`.
"""
import glob
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402

DO_JSON = "--json" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]

if DO_JSON:
    LIVE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
    PATTERN = os.path.join(ROOT, "_backup", "json.*")
else:
    LIVE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
    PATTERN = os.path.join(ROOT, "_backup", "scenario01.*")

MAX_SHOW = 12


def newest_backup():
    cands = [p for p in glob.glob(PATTERN) if os.path.isfile(p)]
    if not cands:
        raise SystemExit("không thấy backup nào khớp " + PATTERN)
    return max(cands, key=os.path.getmtime)


def texts(path):
    """{khoá: chuỗi} cho mọi chuỗi hiển thị trong bundle."""
    out = {}
    for o in UnityPy.load(path).objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        raw = d.m_Script
        if not isinstance(raw, str):
            try:
                raw = bytes(raw).decode("utf-8")
            except UnicodeDecodeError:
                continue
        if not raw.lstrip("﻿").startswith(("{", "[")):
            continue
        try:
            data = json.loads(raw.lstrip("﻿"))
        except ValueError:
            continue

        def walk(x, path_):
            if isinstance(x, dict):
                for k, v in x.items():
                    walk(v, path_ + "/" + str(k))
            elif isinstance(x, list):
                for i, v in enumerate(x):
                    walk(v, path_ + "[%d]" % i)
            elif isinstance(x, str) and x:
                out[path_] = x
        walk(data, d.m_Name)
    return out


def indented(s):
    return sum(1 for l in s.split("\n") if l[:1] in ("　", " "))


def main():
    base = args[0] if args else newest_backup()
    print("bản nền : %s" % base)
    print("bản hiện: %s" % LIVE)
    before, after = texts(base), texts(LIVE)
    common = before.keys() & after.keys()
    print("chuỗi: nền %d, hiện %d, so được %d" % (len(before), len(after), len(common)))

    lost_nl, lost_ind = [], []
    tot_nl_b = tot_nl_a = tot_i_b = tot_i_a = 0
    for k in common:
        b, a = before[k], after[k]
        nb, na = b.count("\n"), a.count("\n")
        ib, ia = indented(b), indented(a)
        tot_nl_b += nb; tot_nl_a += na; tot_i_b += ib; tot_i_a += ia
        if na < nb:
            lost_nl.append((k, nb, na, a))
        if ia < ib:
            lost_ind.append((k, ib, ia, a))

    print("ngắt dòng : %d -> %d  (%+d)" % (tot_nl_b, tot_nl_a, tot_nl_a - tot_nl_b))
    print("dòng thụt : %d -> %d  (%+d)" % (tot_i_b, tot_i_a, tot_i_a - tot_i_b))
    only_before = sorted(before.keys() - after.keys())
    only_after = sorted(after.keys() - before.keys())
    if only_before:
        print("! %d chuỗi có ở nền mà mất ở bản hiện, ví dụ: %s" % (len(only_before), only_before[:3]))
    if only_after:
        print("  %d chuỗi mới xuất hiện, ví dụ: %s" % (len(only_after), only_after[:3]))

    for label, rows in (("MẤT NGẮT DÒNG", lost_nl), ("MẤT THỤT LỀ", lost_ind)):
        if not rows:
            continue
        print("\n%s: %d chuỗi" % (label, len(rows)))
        for k, b, a, s in sorted(rows)[:MAX_SHOW]:
            print("  %-42s %d -> %d   %r" % (k, b, a, s.split("\n")[0][:52]))
        if len(rows) > MAX_SHOW:
            print("  … còn %d chuỗi nữa" % (len(rows) - MAX_SHOW))

    if lost_nl or lost_ind or only_before:
        print("\nFAIL — merge đã làm phẳng bố cục. Chạy lại các fixer:")
        print("   python tools\\fix_novel_list_wrap.py --apply")
        print("   python tools\\fix_dictionary_wrap.py --apply")
        raise SystemExit(1)
    print("\nPASS không chuỗi nào mất ngắt dòng hay thụt lề")


main()
