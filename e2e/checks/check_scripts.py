# -*- coding: utf-8 -*-
"""Structural check on the chapter scripts: the engine executes these, so their command
sequence must match stock exactly. Only tag ARGUMENTS may be translated.

This catches the class of bug where a translation pass silently drops or mangles a command -
found 2026-08-15 that 00_04 had lost an [env カメラ移動 ...] camera reset (3406 -> 3405 commands),
which no amount of proof-reading the Vietnamese would reveal.

Exit code 0 = all pass, 1 = at least one script differs structurally.
"""
import sys, io, re, difflib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

PATCH = r'D:\Downloads\010068501ff9a000\romfs\Data\StreamingAssets\scenario\scenario01'
STOCK = r'D:\Downloads\UNLOGICAL_v2\Data\StreamingAssets\scenario\scenario01'
CMD = re.compile(r'^\s*\[([^\]]*)\]\s*$')
SKIP = {'ScenarioData', 'LoadData'}


def scripts(path):
    out = {}
    for o in UnityPy.load(path).objects:
        if o.type.name == 'TextAsset':
            d = o.read()
            if d.m_Name in SKIP:
                continue
            s = d.m_Script
            out[d.m_Name] = s if isinstance(s, str) else bytes(s).decode('utf-8', 'ignore')
    return out


def keywords(text):
    out = []
    for line in text.replace('\r\n', '\n').split('\n'):
        m = CMD.match(line)
        if m:
            c = m.group(1)
            out.append(c.split()[0] if c.split() else c)
    return out


def labels(text):
    return re.findall(r'^\s*(\*[^\s|]+)', text, re.M)


ps, ss = scripts(PATCH), scripts(STOCK)
fails = []
print('scripts: patched=%d stock=%d' % (len(ps), len(ss)))

missing = sorted(set(ss) - set(ps))
extra = sorted(set(ps) - set(ss))
print('%-4s script assets present in stock' % ('PASS' if not missing else 'FAIL'), end='')
print('  -- missing: %s' % missing if missing else '')
if missing:
    fails.append('missing scripts')
if extra:
    print('NOTE extra scripts not in stock: %s' % extra)

bad_cmds, bad_labels = [], []
for name in sorted(ss):
    a, b = keywords(ss[name]), keywords(ps.get(name, ''))
    if a != b:
        bad_cmds.append((name, a, b))
    la, lb = labels(ss[name]), labels(ps.get(name, ''))
    if la != lb:
        bad_labels.append((name, len(la), len(lb)))

print('%-4s command sequence identical to stock in all %d scripts' % (
    'PASS' if not bad_cmds else 'FAIL', len(ss)))
for name, a, b in bad_cmds:
    print('     %s: stock %d commands, patched %d' % (name, len(a), len(b)))
    for line in difflib.unified_diff(a, b, 'stock', 'patched', lineterm='', n=2):
        if line.startswith(('-', '+')) and not line.startswith(('---', '+++')):
            print('        %s' % line)
    fails.append('commands:' + name)

print('%-4s scene labels identical to stock' % ('PASS' if not bad_labels else 'FAIL'))
for name, na, nb in bad_labels:
    print('     %s: stock %d labels, patched %d' % (name, na, nb))
    fails.append('labels:' + name)

print()
print('%d check(s) failed' % len(fails) if fails else 'all checks passed')
sys.exit(1 if fails else 0)
