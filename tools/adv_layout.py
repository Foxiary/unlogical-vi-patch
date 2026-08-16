# -*- coding: utf-8 -*-
"""Layout model for the ADV message box — the same lines TextMeshPro draws.

Geometry, read from `level10` (pids 886 / 887, `Message(Normal)/Text` and
`Message(Highest)/Text`) and from the `FOT-NewRodinProN-DB SDF` font asset in
the `font_jp` bundle:

    rect             1400 x 186
    font             pointSize 58, unitsPerEm 1000, lineHeight 116,
                     ascender 51.04, descender -6.96
    m_fontSize       42, auto-size 28..42
    characterSpacing 5.3       lineSpacing -42 (percent of fontSize)

    advance(px)  = (glyphAdvance + characterSpacing) * fontSize / pointSize
    line pitch   = fontSize * (lineHeight/pointSize + lineSpacing/100)
    block height = (n-1) * pitch + fontSize * (asc-desc)/pointSize

Calibrated against a real screenshot: predicted word positions across a 730 px
run land within 2.4 px, always erring slightly wide, and the model reproduces
the game's own break points character for character.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROMFS = os.path.join(os.path.dirname(HERE), "romfs", "Data")
FONT_BUNDLE = os.path.join(ROMFS, "StreamingAssets", "font", "font_jp")
FONT_ASSET = "FOT-NewRodinProN-DB SDF"
CACHE = os.path.join(HERE, "_advances.json")

POINT_SIZE = 58.0
UNITS_LINE_HEIGHT = 116.0
UNITS_ASC = 51.04
UNITS_DESC = -6.96

BOX_W = 1400.0
BOX_H = 186.0
FONT_MAX = 42.0
FONT_MIN = 28.0
CHAR_SPACING = 5.3
LINE_SPACING_PCT = -42.0

# Wrap a hair inside the box.  The point of hard-wrapping is that TMP finds
# nothing left to wrap; a line measured at 99.9% is one kerning pair away from
# being re-wrapped, which would put the ruby back where it started.
SAFETY = 0.985

DEFAULT_PLAYER_NAME = "Kanna"   # metadata literal 15063; only a width estimate

_FALLBACK_ADV = 58.0


def _load_advances():
    if os.path.exists(CACHE):
        return {int(k): v for k, v in json.load(open(CACHE)).items()}
    import UnityPy
    env = UnityPy.load(FONT_BUNDLE)
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if not isinstance(t, dict) or t.get("m_Name") != FONT_ASSET:
            continue
        glyphs = {g["m_Index"]: g["m_Metrics"]["m_HorizontalAdvance"]
                  for g in t["m_GlyphTable"]}
        adv = {c["m_Unicode"]: glyphs[c["m_GlyphIndex"]]
               for c in t["m_CharacterTable"] if c["m_GlyphIndex"] in glyphs}
        json.dump(adv, open(CACHE, "w"))
        return adv
    raise SystemExit("font asset %s not found in %s" % (FONT_ASSET, FONT_BUNDLE))


ADV = _load_advances()


def glyph_advance(ch):
    return ADV.get(ord(ch), _FALLBACK_ADV)


def line_pitch(font_size):
    return font_size * (UNITS_LINE_HEIGHT / POINT_SIZE + LINE_SPACING_PCT / 100.0)


def block_height(n_lines, font_size):
    first = font_size * (UNITS_ASC - UNITS_DESC) / POINT_SIZE
    return (n_lines - 1) * line_pitch(font_size) + first


# ---------------------------------------------------------------- tokenising

DIC = re.compile(r"\[dic\b[^\[\]\n]*?text=([^\[\]\n]*?)\]")
RUBY = re.compile(r"\[([^\[\]\n]*?)'([^\[\]\n]*?)\]")
PLAYER = re.compile(r"\[主人公\]")
ANY_TAG = re.compile(r"\[[^\[\]\n]*\]")


def tag_display(tag):
    """What a bracket tag actually puts on screen (the ruby is an overlay)."""
    m = DIC.fullmatch(tag)
    if m:
        inner = m.group(1)
        r = RUBY.fullmatch("[" + inner + "]")
        return r.group(1) if r else inner
    m = RUBY.fullmatch(tag)
    if m:
        return m.group(1)
    if PLAYER.fullmatch(tag):
        return DEFAULT_PLAYER_NAME
    return tag


class Unit(object):
    __slots__ = ("raw", "disp", "atomic")

    def __init__(self, raw, disp, atomic=False):
        self.raw = raw
        self.disp = disp
        self.atomic = atomic

    def width(self, font_size):
        sc = font_size / POINT_SIZE
        return sum((glyph_advance(c) + CHAR_SPACING) for c in self.disp) * sc


def tokenize(line):
    units = []
    pos = 0
    for m in ANY_TAG.finditer(line):
        for ch in line[pos:m.start()]:
            units.append(Unit(ch, ch))
        units.append(Unit(m.group(0), tag_display(m.group(0)), atomic=True))
        pos = m.end()
    for ch in line[pos:]:
        units.append(Unit(ch, ch))
    return units


def _is_cjk(ch):
    o = ord(ch)
    return (0x3000 <= o <= 0x303F or 0x3040 <= o <= 0x30FF or
            0x4E00 <= o <= 0x9FFF or 0xFF00 <= o <= 0xFF60)


NO_LEAD = set("、。，．！？」』）】〉》’”…・ー々ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ,.!?)]}")
NO_TRAIL = set("「『（【〈《‘“([{")


def wrap(line, font_size, limit=None):
    """Greedy word wrap; no emitted line is ever wider than `limit`."""
    limit = BOX_W * SAFETY if limit is None else limit
    units = tokenize(line)
    lines = []
    cur = []
    cur_w = 0.0
    breaks = []

    def flush(upto):
        nonlocal cur, cur_w, breaks
        lines.append(cur[:upto])
        cur = cur[upto:]
        cur_w = sum(u.width(font_size) for u in cur)
        breaks = []

    def legal(idx, incoming):
        if idx <= 0 or idx > len(cur):
            return False
        head = cur[idx].disp if idx < len(cur) else incoming.disp
        if head and head[0] in NO_LEAD:
            return False
        tail = "".join(x.disp for x in cur[:idx]).rstrip()
        if tail and tail[-1] in NO_TRAIL:
            return False
        return True

    for u in units:
        w = u.width(font_size)
        if u.disp == " " and not u.atomic:
            cur.append(u)            # a trailing space may hang past the edge
            cur_w += w
            breaks.append(len(cur))
            continue
        if cur and cur_w + w > limit:
            brk = None
            for cand in reversed(breaks):
                if legal(cand, u):
                    brk = cand
                    break
            if brk is None and not u.atomic and _is_cjk(u.disp) and legal(len(cur), u):
                brk = len(cur)
            if brk is None and len(cur) > 1:
                brk = len(cur)       # nothing legal: cut here rather than hand
            if brk:                  # TMP a line it would re-wrap itself
                flush(brk)
        cur.append(u)
        cur_w += w
        if not u.atomic and _is_cjk(u.disp):
            breaks.append(len(cur))
    if cur:
        lines.append(cur)

    out = []
    for i, ln in enumerate(lines):
        s = "".join(u.raw for u in ln)
        out.append(s if i == len(lines) - 1 else s.rstrip(" "))
    return out


def line_width(s, font_size):
    return sum(u.width(font_size) for u in tokenize(s))


def autosize(line):
    """Largest size in [28,42] at which the wrapped message fits the box."""
    size = FONT_MAX
    while size >= FONT_MIN:
        lines = wrap(line, size)
        if block_height(len(lines), size) <= BOX_H:
            return size, lines
        size -= 0.5
    return FONT_MIN, wrap(line, FONT_MIN)


def fits(hard_lines):
    """Largest size at which an already-wrapped message needs no re-wrapping."""
    size = FONT_MAX
    while size >= FONT_MIN:
        if (max(line_width(l, size) for l in hard_lines) <= BOX_W
                and block_height(len(hard_lines), size) <= BOX_H):
            return size
        size -= 0.5
    return None
