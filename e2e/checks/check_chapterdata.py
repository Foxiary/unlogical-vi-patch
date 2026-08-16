# -*- coding: utf-8 -*-
"""Static checks on ChapterData inside the packed romfs bundle. No game needed.

Guards the class of bug that started this: translated text landing in the wrong entry.
A fluent, self-consistent Vietnamese blurb in the wrong slot is invisible to proof-reading,
so the checks lean on fields the translator should never have touched.

Exit code 0 = all pass, 1 = at least one FAIL.
"""
import sys, io, json, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

PATCHED = r'D:\Downloads\010068501ff9a000\romfs\Data\StreamingAssets\json\json'
STOCK = r'D:\Downloads\UNLOGICAL_v2\Data\StreamingAssets\json\json'
WRAP = 18        # the engine re-breaks the synopsis every 18 characters
BOX_LINES = 7    # the 620x474 mask shows 7 lines at fontSize 31.25

fails = []
notes = []


def check(ok, name, detail=''):
    print('%-4s %s%s' % ('PASS' if ok else 'FAIL', name, ('  -- ' + detail) if detail else ''))
    if not ok:
        fails.append(name)


def load(path):
    for o in UnityPy.load(path).objects:
        if o.type.name == 'TextAsset':
            d = o.read()
            if d.m_Name == 'ChapterData':
                s = d.m_Script
                s = s if isinstance(s, str) else bytes(s).decode('utf-8', 'ignore')
                return json.loads(s.lstrip('\ufeff'))
    raise SystemExit('ChapterData not found in ' + path)


pa, st = load(PATCHED), load(STOCK)
P = [(gi, it) for gi, g in enumerate(pa['list']) for it in g['items']]
S = [(gi, it) for gi, g in enumerate(st['list']) for it in g['items']]

print('=== ChapterData: %d patched entries / %d stock entries ===' % (len(P), len(S)))
check(len(P) == len(S), 'entry count matches stock', '%d vs %d' % (len(P), len(S)))

keys_p = [(g, i['label'], i['file'], i['chapterNo'], i['routeNo'], i['extraRouteNo']) for g, i in P]
keys_s = [(g, i['label'], i['file'], i['chapterNo'], i['routeNo'], i['extraRouteNo']) for g, i in S]
check(keys_p == keys_s, 'entry keys (label/file/chapterNo/routeNo) untouched')

drift = [(s['label'], s['chapter']['jp'], p['chapter']['jp'])
         for (_, s), (_, p) in zip(S, P) if s['chapter']['jp'] != p['chapter']['jp']]
check(not drift, 'English chapter labels identical to stock',
      '; '.join('%s %r->%r' % d for d in drift[:4]))

suffix = [p['chapter']['jp'] for _, p in P if re.search(r'\((Yuri|Miyabi|Kai|Ran|Soichi)\)', p['chapter']['jp'], re.I)]
check(not suffix, 'no route suffix leaked into a chapter label', ', '.join(suffix[:4]))

tags = [p['label'] for _, p in P if '<size' in p['synopsis']['jp'] or '<size' in p['title']['jp']]
check(not tags, 'no leftover rich-text size tags', ', '.join(tags[:4]))

longl = [(p['label'], max(len(l) for l in p['synopsis']['jp'].split('\n'))) for _, p in P
         if any(len(l) > WRAP for l in p['synopsis']['jp'].split('\n'))]
check(not longl, 'every synopsis line <= %d chars (engine wrap width)' % WRAP,
      ', '.join('%s:%d' % x for x in longl[:4]))

# 永守 藍 is romanised "Ran" everywhere (TerminalProfileData ruby "Nagamori Ran", route tab RAN)
ai = [p['label'] for _, p in P
      if re.search(r'\b(?:là|với|của|cho)\s+Ai\b', p['synopsis']['jp'])]
check(not ai, 'no entry romanises 藍 as "Ai" instead of "Ran"', ', '.join(ai))

# the original defect duplicated a route's text into another route's slot
seen = {}
dupes = []
for g, i in P:
    t = i['title']['jp']
    if t in seen and seen[t][0] != g:
        dupes.append('%r in group %d and %d' % (t, seen[t][0], g))
    seen.setdefault(t, (g, i['label']))
check(not dupes, 'no title reused across route groups', '; '.join(dupes[:3]))

# informational: how much of each blurb the box can actually show
lines = [(len(i['synopsis']['jp'].split('\n')), i['label']) for _, i in P]
clipped = [x for x in lines if x[0] > BOX_LINES]
print()
print('NOTE synopsis lines per entry: min %d, max %d; the box shows %d.' % (
    min(l for l, _ in lines), max(l for l, _ in lines), BOX_LINES))
print('     %d of %d entries are longer than the box (%d x %d = %d chars of capacity).' % (
    len(clipped), len(lines), BOX_LINES, WRAP, BOX_LINES * WRAP))
print('     Pre-existing: the box is driven by game code, not by this data. Worst: %s' %
      ', '.join('%s=%d lines' % (lab, n) for n, lab in sorted(lines, reverse=True)[:3]))

print()
print('%d check(s) failed' % len(fails) if fails else 'all checks passed')
sys.exit(1 if fails else 0)
