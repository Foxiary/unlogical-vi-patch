# -*- coding: utf-8 -*-
"""Which screen is this? Cheap pixel probes so run.ps1 can retry instead of guessing sleeps.

Prints one of: section-select | menu | loading | title | other
then the probe values, so a mis-classification is debuggable.

Probes are sampled at FULL resolution - downscaling averages the game's thin light-on-white
strokes away and made an earlier version classify the title screen as section-select.

Calibrated on 1920x1080 Ryujinx captures:

  region          title            menu/loading   section-select   intro
  select_tag      (250,248,253)    (0,0,0)        (242,167,184)    (153,147,182)
  common_tab      (249,242,252)    (0,0,0)        (185,136,189)    (147,129,151)
  topleft         (253,250,252)    (0,0,0)        (250,246,252)    (193,139,173)

The salmon "SELECT" tab is the reliable marker for the chapter list.

Usage: python identify.py <shot.png>
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

REGIONS = {
    'select_tag': (0.080, 0.270, 0.125, 0.325),   # the pink SELECT tab on the chapter list
    'common_tab': (0.165, 0.050, 0.285, 0.095),   # highlighted route tab
    'topleft':    (0.005, 0.005, 0.050, 0.050),
    # ATTENTION and CAUTION are white screens carrying a dark navy banner across the middle,
    # with the word in pink inside it. Everything else is light or dark in that band, not navy.
    'banner':     (0.420, 0.285, 0.600, 0.325),
}
# The main-menu list, used to tell a real menu from any other dark screen.
MENU_ROWS = (0.42, 0.49, 0.58, 0.90)


def mean_of(px, W, H, box, stride=2):
    x0, y0, x1, y1 = box
    n = r = g = b = 0
    for y in range(int(y0 * H), int(y1 * H), stride):
        for x in range(int(x0 * W), int(x1 * W), stride):
            pr, pg, pb = px[x, y]
            r += pr; g += pg; b += pb; n += 1
    n = max(1, n)
    return (r // n, g // n, b // n)


def door_count(px, W, H, stride=4):
    """Pink loading door, searched over the WHOLE frame.

    There are two loading screens: one with the door centred, one on dark navy with the door in
    the bottom-right corner. Probing only the centre classified the second as a dark screen with
    no door, which fell through to 'menu' and made the runner mash DOWN at a loading screen.
    """
    c = 0
    for y in range(0, H, stride):
        for x in range(0, W, stride):
            r, g, b = px[x, y]
            if r > 190 and 40 < g < 150 and 100 < b < 200:
                c += 1
    return c


def has_menu_cursor(px, W, H):
    """True if one main-menu row is drawn in purple, i.e. this really is the menu.

    ATTENTION and CAUTION are also white text on black and land in the same rows, so white
    pixels alone are not enough - only the menu has a highlighted (purple) entry.
    """
    from menu_cursor import ROWS, X0, X1
    for _, y0, y1 in ROWS:
        purple = 0
        for y in range(int(y0 * H), int(y1 * H), 2):
            for x in range(int(X0 * W), int(X1 * W), 2):
                r, g, b = px[x, y]
                if b > 140 and b - g > 35 and r > g and b > r:
                    purple += 1
                    if purple >= 40:
                        return True
    return False


def menu_white(px, W, H, stride=3):
    """Near-white glyph pixels where the five main-menu items sit."""
    x0, y0, x1, y1 = MENU_ROWS
    c = 0
    for y in range(int(y0 * H), int(y1 * H), stride):
        for x in range(int(x0 * W), int(x1 * W), stride):
            r, g, b = px[x, y]
            if r > 235 and g > 235 and b > 235:
                c += 1
    return c


def classify(path):
    im = Image.open(path).convert('RGB')
    W, H = im.size
    px = im.load()
    m = {k: mean_of(px, W, H, v) for k, v in REGIONS.items()}
    door = door_count(px, W, H)
    white = menu_white(px, W, H)

    st = m['select_tag']
    tl = m['topleft']
    bn = m['banner']
    salmon = st[0] > 215 and (st[0] - st[1]) > 40 and 0 < (st[2] - st[1]) < 60
    dark = sum(tl) / 3.0 < 45
    whiteish = tl[0] > 235 and tl[1] > 235 and tl[2] > 235
    navy_banner = sum(bn) / 3.0 < 110 and (bn[2] - bn[0]) > 15

    if salmon:
        label = 'section-select'
    elif whiteish and navy_banner:
        label = 'notice'            # ATTENTION / CAUTION - one A each clears them
    elif dark:
        # a dark screen is only the menu if the highlighted row is actually drawn
        if white >= 200 and has_menu_cursor(px, W, H):
            label = 'menu'
        elif door >= 150:
            label = 'loading'
        else:
            label = 'busy'          # black / fading / still booting - just wait
    elif whiteish:
        label = 'title'
    else:
        label = 'other'
    return label, m, door, white


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('other')
        print('  no path given')
        sys.exit(2)
    lab, m, door, white = classify(sys.argv[1])
    print(lab)
    print('  ' + '  '.join('%s=%s' % (k, v) for k, v in m.items()) +
          '  door=%d menuWhite=%d' % (door, white))
