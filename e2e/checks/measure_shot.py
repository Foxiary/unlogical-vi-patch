# -*- coding: utf-8 -*-
"""Measure how the synopsis actually rendered in a capture, and compare against the data.

Reports rendered line pitch -> font size, widest rendered line, and how many of the entry's
lines made it inside the mask. Numbers, not eyeballing, so a regression is provable.

  pitch = fontSize * (faceLineHeight/pointSize + m_lineSpacing/100) = 2.33 * fontSize
          (FOT-NewRodinProN-DB: pointSize 58, lineHeight 116; MainText m_lineSpacing = 33)

Usage: python measure_shot.py <shot.png> [entry-label]     default label *PRO-00-01
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

PJ = r'D:\Downloads\010068501ff9a000\romfs\Data\StreamingAssets\json\json'
INK = (0, 61, 99)          # MainText m_fontColor
TOL = 70
PITCH_FACTOR = 2.33
BOX_W, BOX_H = 609.0, 474.0
# synopsis area, normalised, from the measured layout
X0, X1, Y0, Y1 = 0.470, 0.860, 0.330, 0.880


def entry(label):
    for o in __import__('UnityPy').load(PJ).objects:
        if o.type.name == 'TextAsset':
            d = o.read()
            if d.m_Name == 'ChapterData':
                s = d.m_Script
                s = s if isinstance(s, str) else bytes(s).decode('utf-8', 'ignore')
                j = json.loads(s.lstrip('\ufeff'))
                for g in j['list']:
                    for it in g['items']:
                        if it['label'] == label:
                            return it
    return None


def bands(path):
    im = Image.open(path).convert('RGB')
    W, H = im.size
    px = im.load()
    rows = []
    for y in range(int(Y0 * H), int(Y1 * H)):
        n = 0; xmin = xmax = None
        for x in range(int(X0 * W), int(X1 * W)):
            c = px[x, y]
            if abs(c[0]-INK[0]) < TOL and abs(c[1]-INK[1]) < TOL and abs(c[2]-INK[2]) < TOL:
                n += 1
                if xmin is None: xmin = x
                xmax = x
        rows.append((y, n, xmin, xmax))
    raw, cur = [], None
    for y, n, xmin, xmax in rows:
        if n >= 3:
            cur = [y, y, xmin, xmax] if cur is None else [cur[0], y, min(cur[2], xmin), max(cur[3], xmax)]
        else:
            if cur: raw.append(cur); cur = None
    if cur: raw.append(cur)
    # merge bands closer than 20px: Vietnamese diacritics form their own band
    out = []
    for b in raw:
        if out and b[0] - out[-1][1] < 20:
            p = out[-1]
            out[-1] = [p[0], b[1], min(p[2], b[2]), max(p[3], b[3])]
        else:
            out.append(list(b))
    return out, W, H


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit('usage: measure_shot.py <shot.png> [label]')
    path = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else '*PRO-00-01'
    bs, W, H = bands(path)
    scale = 1920.0 / W                      # report in canvas px
    print('capture %dx%d, %d rendered line(s) of synopsis ink' % (W, H, len(bs)))
    if len(bs) < 2:
        raise SystemExit('not enough text found - is this the section-select screen?')
    pitches = [(bs[i+1][0] - bs[i][0]) * scale for i in range(len(bs) - 1)]
    avg = sum(pitches) / len(pitches)
    widest = max(b[3] - b[2] + 1 for b in bs) * scale
    print('  line pitch   %.2f canvas px  -> fontSize %.2f' % (avg, avg / PITCH_FACTOR))
    print('  widest line  %.0f px of the %.0f px box (%.0f%% used)' % (widest, BOX_W, widest / BOX_W * 100))

    it = entry(label)
    if it:
        stored = it['synopsis']['jp'].split('\n')
        print('  entry %s: %d stored line(s), %d rendered -> %d hidden' % (
            label, len(stored), len(bs), max(0, len(stored) - len(bs))))
        print('  title stored: %r' % it['title']['jp'])
        print('  first stored line: %r' % stored[0])
    else:
        print('  entry %s not found in ChapterData' % label)
