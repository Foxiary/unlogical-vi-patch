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
# Game code used to hard-break the synopsis every 18 characters
# (Chapter.get_DefaultMaxCharsPerLine, RVA 0x1998AC0). The exefs IPS32 raises it 18 -> 24 --
# NOT to 0: the same routine (SetNoteTextFromString) counts those lines to page the StorySlider,
# so disabling the wrap left it seeing one line, one page, and the scrollbar dead. MainText
# stays at m_TextWrappingMode = 0 for the same reason: a second wrap by TMP would desync the
# page count from what is drawn. Long entries page
# rather than clip. Both halves must ship together — see the note printed at the end.
WRAP = 40        # what the patched binary enforces (IPS: 18 -> 40)
BOX_LINES = 7    # the 620x474 mask shows 7 lines at fontSize 31.25 before scrolling

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

# The engine chops at exactly WRAP characters and ignores spaces, so leaving the synopsis as one
# flowing paragraph splits words mid-syllable. It does respect stored newlines, so tools\
# wrap_synopsis.py wraps by word to the real box width and the constant is set above the longest
# line. Assert both halves of that: every synopsis is wrapped, and no line reaches the constant.
nowrap = [p['label'] for _, p in P if p['synopsis']['jp'] and '\n' not in p['synopsis']['jp']]
check(not nowrap, 'synopsis is hard-wrapped by word (engine chops mid-word otherwise)',
      ', '.join(nowrap[:4]))

longest = max(((len(ln), p['label'], ln)
               for _, p in P for ln in p['synopsis']['jp'].split('\n')), default=(0, '', ''))
check(longest[0] < WRAP, 'no synopsis line reaches the %d-char engine chop' % WRAP,
      '%s has %d chars: %r' % (longest[1], longest[0], longest[2]))

tbrk = [p['label'] for _, p in P if '\n' in p['title']['jp']]
check(not tbrk, 'no hard line breaks in title', ', '.join(tbrk[:4]))

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

# informational: this data is only half the fix, and the other half ships outside romfs
CAP = BOX_LINES * WRAP
sizes = [(len(i['synopsis']['jp']), i['label']) for _, i in P]
over = [x for x in sizes if x[0] > CAP]
print()
print('NOTE synopsis length: min %d, max %d chars. Worst: %s' % (
    min(n for n, _ in sizes), max(n for n, _ in sizes),
    ', '.join('%s=%d' % (lab, n) for n, lab in sorted(sizes, reverse=True)[:3])))
print('     %d of %d exceed the %d x %d = %d one page shows; they page'
      % (len(over), len(sizes), BOX_LINES, WRAP, CAP))
print('     on StorySlider instead of clipping.')
print('     REMINDER this flowing text only renders correctly with BOTH halves installed:')
print('       exefs/669EA2FE0282C2C0EFEA4DA183419FB7.ips  (DefaultMaxCharsPerLine 18 -> 40)')
print('       ui_jp  SynopsisTitle/Mask/MainText  m_margin.y = 5  (dau chong tieng Viet)')
print('     The .ips lives beside romfs, not inside it, so it is easy to leave out of a release.')

print()
print('%d check(s) failed' % len(fails) if fails else 'all checks passed')
sys.exit(1 if fails else 0)
