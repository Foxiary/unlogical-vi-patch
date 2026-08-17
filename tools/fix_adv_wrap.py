# -*- coding: utf-8 -*-
"""Hard-wrap ADV dialogue so no line runs under the message box's corner art.

The box rect is 1400 px wide, but the art is cut diagonally at the bottom right,
so the lower a line sits the less room it really has.  Measured off a real
1280x720 capture (`IMG_7139`, dark-pixel edge of the cut, canvas px from the
text's left margin at canvas 310):

    line 1   art at 1430  ->  rect is the limit, 1400
    line 2   art at 1364
    line 3   art at 1301
    line 4   art at ~1240   (only reachable once auto-size has shrunk the text)

TMP wraps at the rect, knows nothing about the art, so a long third line ends up
sitting on the dark diagonal and its tail becomes unreadable.  That was **3 992 of
37 951 ADV messages (10.5%)** before `fix_adv_box_width.py` narrowed the rect to
1280 — which is the real fix, one float per component, and needs no data pass.

**So this script is primarily the CHECK.**  `--check` measures every ADV message
the way the game lays it out (existing `\\n`, TMP wrap at the rect read live from
`level10`, then auto-size) and fails if any line crosses the art.  Run it after a
sheet merge, next to `check_scripts.py`.

`--apply` remains for the leftovers a narrower rect cannot reach (a 4th line, only
possible once auto-size has already shrunk the text).  It picks the largest size
that still fits the box height **first**, then wraps to the art limits measured at
*that* size: wrapping to size-42 limits a message that renders at 28 shatters it
into six lines and overflows the box vertically — tried, reverted, don't repeat it.

The JP data never had the problem: the writers hard-wrapped every message, and 99%
of their lines are under ~1100 px, far inside the rect.

Width model — advance scales by fontSize/pointSize, characterSpacing by
fontSize/100, trailing spacing does not count.  Validated against both captures to
0.5-1%: the good one renders at 42 and the overflowing one at 41, and the model
reproduces every break point and line width in both.  `「」` are **not drawn** by
this box (proven by those same measurements) so they are excluded from the width.

    python tools\\fix_adv_wrap.py               # chạy thử, liệt kê thống kê
    python tools\\fix_adv_wrap.py --apply
    python tools\\fix_adv_wrap.py --check       # chốt sau merge, lỗi -> exit 1
    python tools\\fix_adv_wrap.py --limit 200   # chỉ xử lý 200 tin nhắn đầu (thử)
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

import UnityPy   # noqa: E402
from adv_layout import ADV   # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "scenario01.advwrap")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv
LIMIT_N = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--limit=")), 0)

POINT_SIZE, CHAR_SPACING, LINE_SPACING = 58.0, 5.3, -42.0
BOX_H = 186.0


def rect_width(default=1280.0):
    """Đọc bề rộng khung thật từ `level10` — `fix_adv_box_width.py` đã thu nó lại,
    nên đừng viết cứng con số ở đây."""
    lvl = os.path.join(ROOT, "romfs", "Data", "level10")
    try:
        for o in UnityPy.load(lvl).objects:
            if o.path_id == 564 and o.type.name == "RectTransform":
                return o.read_typetree()["m_SizeDelta"]["x"]
    except Exception as e:
        print("(không đọc được khung từ level10: %s — dùng %.0f)" % (e, default))
    return default


RECT_W = rect_width()
FMAX, FMIN, FSTEP = 42.0, 28.0, 0.25
SAFETY = 20.0                      # mô hình đúng 0,5-1%, chừa ~1,5%
CAPS = [1400.0, 1364.0 - SAFETY, 1301.0 - SAFETY, 1240.0 - SAFETY]
NOT_DRAWN = "「」"

NOVEL_ON = re.compile(r"^\[ノベルモード[^\]]*開始")
NOVEL_OFF = re.compile(r"^\[ノベルモード[^\]]*終了")
TAG = re.compile(r"\[[^\[\]\n]*\]")
RUBY = re.compile(r"\[([^\[\]\n']*?)'([^\[\]\n]*?)\]")


def shown(s):
    """Chữ thật hiện trên màn: ruby vẽ phần gốc, lệnh khác không vẽ, 「」 không vẽ."""
    def rep(m):
        r = RUBY.fullmatch(m.group(0))
        if r:
            return r.group(1)
        return "Kanna" if m.group(0) == "[主人公]" else ""
    return "".join(c for c in TAG.sub(rep, s) if c not in NOT_DRAWN)


def words_of(seg):
    """Tách từ theo dấu cách NHƯNG không cắt vào trong `[...]`.

    `[Cherish'Châu ngọc]` có dấu cách bên trong; cắt đôi nó thì hai nửa không còn
    khớp regex tag nữa và bị đo cả phần ruby lẫn dấu ngoặc — sai rất nhiều và làm
    câu bị ngắt vụn ra 5-6 dòng.
    """
    out, cur, depth = [], "", 0
    for c in seg:
        if c == "[":
            depth += 1
        elif c == "]":
            depth = max(depth - 1, 0)
        if c == " " and depth == 0:
            if cur:
                out.append(cur)
            cur = ""
        else:
            cur += c
    if cur:
        out.append(cur)
    return out


def measure(s):
    """(tổng advance thô, số ký tự hiển thị) — cộng dồn được mà không sai số."""
    d = shown(s)
    return sum(ADV.get(ord(c), 58.0) for c in d), len(d)


def wd(adv, chars, F=FMAX):
    """Bề rộng px canvas: advance nhân F/pointSize, charSpacing nhân F/100,
    và khoảng cách sau ký tự cuối không tính."""
    return adv * F / POINT_SIZE + max(chars - 1, 0) * CHAR_SPACING * F / 100.0


def w42(s):
    a, c = measure(s)
    return wd(a, c)


SPACE = measure(" ")


def cap(k):
    return CAPS[k] if k < len(CAPS) else CAPS[-1]


def block_h(n, F):
    return (n - 1) * F * (2 + LINE_SPACING / 100.0) + F


def wrap_words(words, limit, start_index=0, per_line_caps=False, scale=1.0):
    """Ngắt tham lam ở cỡ 42; `words` là list (advance, số ký tự).
    `scale` = 42/F khi muốn giới hạn tính ở cỡ F. Trả list (bề rộng, số từ)."""
    out, adv, chars, cnt, k = [], 0.0, 0, 0, start_index
    for wa, wc in words:
        lim = min(cap(k), RECT_W) * scale if per_line_caps else limit
        if cnt:
            nadv, nchars = adv + SPACE[0] + wa, chars + SPACE[1] + wc
        else:
            nadv, nchars = wa, wc
        if cnt and wd(nadv, nchars) > lim:
            out.append((wd(adv, chars), cnt))
            adv, chars, cnt, k = wa, wc, 1, k + 1
        else:
            adv, chars, cnt = nadv, nchars, cnt + 1
    if cnt:
        out.append((wd(adv, chars), cnt))
    return out


def render(text):
    """Cỡ auto-size sẽ chọn và bề rộng từng dòng ở cỡ đó (px canvas)."""
    segs = [shown(x) for x in text.split("\n")]
    wordss = [[measure(w) for w in words_of(seg)] for seg in segs]
    F = FMAX
    while F >= FMIN:
        lines = []
        for words in wordss:
            got = wrap_words(words, RECT_W * FMAX / F)
            lines.extend([g[0] for g in got] or [0.0])
        if block_h(len(lines), F) <= BOX_H:
            return F, [x * F / FMAX for x in lines]
        F -= FSTEP
    lines = []
    for words in wordss:
        got = wrap_words(words, RECT_W * FMAX / FMIN)
        lines.extend([g[0] for g in got] or [0.0])
    return FMIN, [x * FMIN / FMAX for x in lines]


# Mép hoạ tiết ở dòng 4 là con số SUY RA, không đo được (ảnh chụp chỉ có 3 dòng),
# và câu nào xuống tới dòng 4 thì đã bị auto-size thu nhỏ nên chữ mảnh hơn mô hình.
# Nới 40 px cho dòng 4 trở đi; dòng 1-3 vẫn chặn đúng số đo.
TOL_LATE_LINE = 40.0


def offenders(text):
    """Dòng nào chạm hoạ tiết khi game vẽ hiện tại."""
    F, lines = render(text)
    bad = []
    for k, w in enumerate(lines):
        lim = cap(k) + (TOL_LATE_LINE if k >= 3 else 0.0)
        if w > lim:
            bad.append((k + 1, w, lim))
    return bad, F, len(lines)


def _wrap_caps(text, scale):
    """Ngắt theo giới hạn hoạ tiết tính ở cỡ F (scale = 42/F); giữ `\\n` sẵn có."""
    out, k = [], 0
    for seg in text.split("\n"):
        toks = words_of(seg)
        if not toks:
            out.append("")
            k += 1
            continue
        got = wrap_words([measure(t) for t in toks], None,
                         start_index=k, per_line_caps=True, scale=scale)
        i = 0
        for _, n in got:
            out.append(" ".join(toks[i:i + n]))
            i += n
        k += len(got)
    return out


def rewrap(text):
    """Ngắt lại theo giới hạn hoạ tiết — nhưng **tính ở cỡ mà câu sẽ được vẽ**.

    Ngắt theo giới hạn ở cỡ 42 cho một câu vốn render ở cỡ 28 thì vụn ra 6 dòng và
    tràn chiều cao (đã thử và phải trả lại). Chọn cỡ lớn nhất còn vừa khung trước,
    rồi mới ngắt theo giới hạn ở cỡ đó.
    """
    F, last = FMAX, None
    while F >= FMIN:
        lines = _wrap_caps(text, FMAX / F)
        if block_h(len(lines), F) <= BOX_H:
            return "\n".join(lines)
        last = lines
        F -= FSTEP
    return "\n".join(last or _wrap_caps(text, FMAX / FMIN))


def novel_flags(t):
    ins, flags = False, []
    for l in t["scriptText_Line"]:
        if NOVEL_ON.match(l):
            ins = True
        elif NOVEL_OFF.match(l):
            ins = False
        flags.append(ins)
    return flags


def adv_messages(data):
    """(ti, sid, j) cho tin nhắn vẽ ở ô thoại ADV — bỏ chế độ novel."""
    out = []
    for ti, t in enumerate(data["target"]):
        flags, LL, SL = novel_flags(t), t["loadLine"], t["scriptText_Line"]
        for j, s in enumerate(t["text"]):
            if not s.strip():
                continue
            if j < len(LL) and LL[j] < len(SL) and flags[LL[j]]:
                continue
            out.append((ti, t["scenarioID"], j))
    return out


def load(path):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name == "TextAsset" and o.read().m_Name == "ScenarioData":
            d = o.read()
            raw = d.m_Script
            if not isinstance(raw, str):
                raw = bytes(raw).decode("utf-8")
            return env, d, raw
    raise SystemExit("không thấy ScenarioData")


def mirror(script, old, new):
    lines, ol, nl = script.split("\n"), old.split("\n"), new.split("\n")
    hits = [k for k in range(len(lines) - len(ol) + 1) if lines[k:k + len(ol)] == ol]
    if len(hits) != 1:
        return None
    lines[hits[0]:hits[0] + len(ol)] = nl
    return "\n".join(lines)


def main():
    env, d, raw = load(BUNDLE)
    bom = "﻿" if raw.startswith("﻿") else ""
    data = json.loads(raw.lstrip("﻿"))
    msgs = adv_messages(data)
    if LIMIT_N:
        msgs = msgs[:LIMIT_N]
    print("tin nhắn ở ô thoại ADV: %d   (khung %.0f, giới hạn từng dòng %s)"
          % (len(msgs), RECT_W, [int(c) for c in CAPS]))

    bad = []
    for ti, sid, j in msgs:
        hits, F, n = offenders(data["target"][ti]["text"][j])
        if hits:
            bad.append((ti, sid, j, hits, F, n))

    if CHECK:
        print("dòng chạm hoạ tiết: %d tin nhắn" % len(bad))
        for ti, sid, j, hits, F, n in bad[:10]:
            k, w, c = hits[0]
            print("  FAIL sID=%-4s text[%-5d] dòng %d/%d ở cỡ %.2f: %.0f > %.0f  %r"
                  % (sid, j, k, n, F, w, c, shown(data["target"][ti]["text"][j])[:52]))
        if bad:
            print("\nchạy `python tools\\fix_adv_wrap.py --apply`")
            raise SystemExit(1)
        print("PASS không dòng nào chạm hoạ tiết")
        return

    out, plan, skipped = raw, [], 0
    scripts = {}
    for ti, sid, j, hits, F, n in bad:
        old = data["target"][ti]["text"][j]
        new = rewrap(old)
        if new == old:
            skipped += 1
            continue
        after, _, _ = offenders(new)
        if after:
            skipped += 1
            continue
        old_j, new_j = json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False)
        if out.count(old_j) != 1:
            skipped += 1
            continue
        out = out.replace(old_j, new_j)
        scripts.setdefault(ti, []).append((old, new))
        plan.append((ti, sid, j, old, new, F, n))

    mirrored = mirror_failed = 0
    for ti, pairs in scripts.items():
        script = cur = data["target"][ti]["scriptText"]
        for old, new in pairs:
            nxt = mirror(cur, old, new)
            if nxt is None:
                mirror_failed += 1
            else:
                cur = nxt
                mirrored += 1
        if cur != script:
            oj, nj = (json.dumps(script, ensure_ascii=False), json.dumps(cur, ensure_ascii=False))
            if out.count(oj) != 1:
                raise SystemExit("scriptText target[%d] khớp %d lần" % (ti, out.count(oj)))
            out = out.replace(oj, nj)

    print("chạm hoạ tiết: %d tin nhắn  ->  ngắt lại %d, bỏ qua %d"
          % (len(bad), len(plan), skipped))
    print("mirror vào scriptText: %d (không khớp verbatim: %d)" % (mirrored, mirror_failed))
    grew = sum(1 for _, _, _, old, new, _, _ in plan
               if len(new.split("\n")) > len(old.split("\n")))
    print("số tin nhắn có thêm dòng: %d" % grew)

    # giá phải trả: câu nào sau khi ngắt lại sẽ bị auto-size thu nhỏ hơn trước
    import collections as _c
    delta = _c.Counter()
    worse = []
    for ti, sid, j, old, new, F_old, n_old in plan:
        F_new, lines_new = render(new)
        delta[(round(F_old * 4) / 4, round(F_new * 4) / 4)] += 1
        if F_new < F_old - 1e-6:
            worse.append((F_old - F_new, sid, j, F_old, F_new, len(lines_new)))
    same = sum(v for (a, b), v in delta.items() if b >= a)
    print("cỡ chữ sau khi sửa: giữ nguyên hoặc to hơn %d, nhỏ hơn %d" % (same, len(worse)))
    if worse:
        worse.sort(reverse=True)
        buck = _c.Counter(round(w[4]) for w in worse)
        print("   phân bố cỡ mới của nhóm bị nhỏ đi: "
              + "  ".join("%d:%d" % (k, buck[k]) for k in sorted(buck, reverse=True)))
        for dd, sid, j, fo, fn, n in worse[:5]:
            print("   sID=%-4s text[%-5d] %.2f -> %.2f (%d dòng)" % (sid, j, fo, fn, n))
    if skipped:
        print("bỏ qua %d câu (ngắt lại vẫn chạm, hoặc chuỗi không khớp duy nhất)" % skipped)
    for ti, sid, j, old, new, F, n in plan[:6]:
        print("\n=== sID=%s text[%d]  cỡ %.2f, %d dòng -> ngắt cứng %d dòng"
              % (sid, j, F, n, len(new.split("\n"))))
        for l in new.split("\n"):
            print("   %6.1f  %s" % (w42(shown(l)), shown(l)[:70]))

    if not plan:
        return

    after_all = json.loads(out.lstrip("﻿"))
    changed = {(ti, j) for ti, _, j, _, _, _, _ in plan}
    for ti, t in enumerate(data["target"]):
        ta = after_all["target"][ti]
        assert ta["scriptText_Line"] == t["scriptText_Line"], "scriptText_Line đổi"
        assert ta["loadLine"] == t["loadLine"], "loadLine đổi"
        assert len(ta["text"]) == len(t["text"])
        for j in range(len(t["text"])):
            if (ti, j) not in changed:
                assert ta["text"][j] == t["text"][j], "text[%d] target[%d] đổi ngoài dự kiến" % (j, ti)
    for ti, sid, j, old, new, F, n in plan:
        assert after_all["target"][ti]["text"][j] == new
        assert new.replace("\n", " ") == old.replace("\n", " "), "chữ đổi ở sID=%s text[%d]" % (sid, j)
    print("\nkiểm tra: %d tin nhắn đổi, loadLine/scriptText_Line nguyên vẹn, chữ không đổi"
          % len(plan))

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(BUNDLE, BACKUP)
        print("backup ->", BACKUP)
    d.m_Script = bom + out.lstrip("﻿")
    d.save()
    with open(BUNDLE, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi", BUNDLE, os.path.getsize(BUNDLE))

    _, _, back = load(BUNDLE)
    rd = json.loads(back.lstrip("﻿"))
    for ti, sid, j, old, new, F, n in plan:
        assert rd["target"][ti]["text"][j] == new, "đọc lại sID=%s text[%d] không khớp" % (sid, j)
    for ti, t in enumerate(data["target"]):
        assert rd["target"][ti]["loadLine"] == t["loadLine"]
        assert rd["target"][ti]["scriptText_Line"] == t["scriptText_Line"]
    print("  đọc lại: %d tin nhắn khớp, loadLine/scriptText_Line nguyên vẹn" % len(plan))


main()
