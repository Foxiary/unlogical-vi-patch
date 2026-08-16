# -*- coding: utf-8 -*-
"""Which main-menu item is highlighted? Prints "<index> <name>", or "-1 unknown".

The cursor does not always start on the same item, so the runner has to read it rather than
assume - blindly sending one DOWN once landed the test in the LOAD screen instead of `section`.

The highlighted row is the only one drawn in purple, and it is the only one with no white
glyph pixels. Measured on 1920x1080 captures:

               LOAD highlighted      section highlighted
  NEW GAME     purple    0/white 899  purple   0/white 899
  LOAD         purple 1626/white   0  purple   0/white1537
  section      purple    0/white  69  purple 328/white   0
  ARCHIVE      purple    0/white 624  purple   0/white 624
  OPTION       purple    0/white 562  purple   0/white 562

Usage: python menu_cursor.py <shot.png>
"""
import sys, io
from PIL import Image

# NB: the stdout rewrap lives under __main__ on purpose. identify.py imports this module, and a
# second TextIOWrapper over the same buffer closes the caller's stdout when it is collected.

ROWS = [
    ('NEW GAME', 0.495, 0.545),
    ('LOAD',     0.578, 0.628),
    ('section',  0.665, 0.715),
    ('ARCHIVE',  0.752, 0.802),
    ('OPTION',   0.842, 0.892),
]
X0, X1 = 0.42, 0.58


def cursor(path):
    im = Image.open(path).convert('RGB')
    W, H = im.size
    px = im.load()
    scores = []
    for name, y0, y1 in ROWS:
        purple = 0
        for y in range(int(y0 * H), int(y1 * H), 2):
            for x in range(int(X0 * W), int(X1 * W), 2):
                r, g, b = px[x, y]
                if b > 140 and b - g > 35 and r > g and b > r:
                    purple += 1
        scores.append((purple, name))
    best = max(range(len(scores)), key=lambda i: scores[i][0])
    if scores[best][0] < 40:
        return -1, 'unknown', scores
    return best, scores[best][1], scores


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if len(sys.argv) < 2:
        print('-1 unknown')
        sys.exit(2)
    i, name, scores = cursor(sys.argv[1])
    print('%d %s' % (i, name))
    print('  ' + '  '.join('%s=%d' % (n, p) for p, n in scores))
