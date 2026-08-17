# -*- coding: utf-8 -*-
"""Hard-wrap every numbered / bulleted list block in novel mode, JP hanging indent.

**Re-runnable, and meant to be re-run after every sheet merge** — a merge writes
`text[]` from the sheet, and the sheet cannot carry either the hard breaks or the
indents (see the README section), so it flattens this work every time.  Nothing
here is keyed to a message index: the blocks are found from the JAPANESE side,
which never changes.

The bug being fixed: the novel box (`level10` pid 894 `Message(Novel)/NovelText`,
rect 1400x720, size 42, charSpacing 6, wrap ON, auto-size OFF) draws every line
that exists **in the data** one em to the right — the engine's own paragraph
indent — and gives a line **TMP** wrapped nothing.  So an over-long data line
comes back with its tail jutting one em to the LEFT:

    5. Không được tiết lộ thông tin làm ảnh hưởng đến
thắng bại của trò chơi cho Player.          <- 1 em further left

Measured on a photo of the real screen (adjacent lines, so the perspective
cancels): 41 canvas px = 0.98 em.  The JP data never hits it — every rule is
hard-wrapped and its continuations start with two full-width spaces, so 1 em
(engine) + 2 em (data) puts the body of every line on one column.

Detection, all from the untranslated script (`scriptText_Line`, indexed by
`loadLine`, both of which this tool never writes):

    message j is a list item  <=>  scriptText_Line[loadLine[j]] starts with
                                   １．…９． or ・ ※ ＊ *
                              and  that line sits between
                                   [ノベルモード…開始…] and [ノベルモード…終了…]

The hanging prefix is chosen per item so it matches the marker the translation
actually uses (`5. ` is 64.6 px, `・` is 44.5, `* ` is 38.3 — full-width digits
would be 89), out of `　`, `　 `, `　　`, and runs of spaces.

Width model — advance scales by fontSize/pointSize, characterSpacing by
fontSize/100, trailing spacing does not count (see `unlogical-text-overflow`):

    W = sum(advance) * 42/58 + (n-1) * 6 * 42/100

and the wrap limit is `(1400 - 42) * 0.99`: minus the engine indent because it is
inserted into the string and therefore eats wrap width, times 0.99 because the
model's error against a real screen is under 2% and 7 px of headroom is thinner
than that.

    python tools\\fix_novel_list_wrap.py            # chạy thử
    python tools\\fix_novel_list_wrap.py --apply
    python tools\\fix_novel_list_wrap.py --check    # chốt sau merge, lỗi -> exit 1

`--check` fails on real overflow (`W + 42 > 1400`) or on a continuation line with
no indent, so it belongs next to `check_scripts.py` in the post-merge gate.
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
BACKUP = os.path.join(ROOT, "_backup", "scenario01.novellist")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

POINT_SIZE, FONT_SIZE, CHAR_SPACING = 58.0, 42.0, 6.0
BOX, ENGINE_INDENT, SAFETY = 1400.0, 42.0, 0.99
LIMIT = (BOX - ENGINE_INDENT) * SAFETY

NOVEL_ON = re.compile(r"^\[ノベルモード[^\]]*開始")
NOVEL_OFF = re.compile(r"^\[ノベルモード[^\]]*終了")
JP_MARKER = re.compile(r"^(?:[０-９]+[．.]|[・※＊*])")
VN_MARKER = re.compile(r"^(?:\d+[.)]\s*|[・※＊*]\s*)")
# Chỉ tiền tố mở đầu bằng `　`: bản JP có 17.299 dòng như vậy và chúng hiển thị
# đúng, tức U+3000 chắc chắn không bị engine cắt. Space ASCII đầu dòng thì chưa
# có bằng chứng nào trong game này, đừng đánh cược. Sai số lớn nhất còn 5,6 px.
PREFIXES = ["　", "　 ", "　  ", "　　"]

TAG = re.compile(r"\[[^\[\]\n]*\]")
RUBY = re.compile(r"\[([^\[\]\n']*?)'([^\[\]\n]*?)\]")


def shown(s):
    """Chữ thật hiện trên màn: ruby chỉ vẽ phần gốc, lệnh khác không vẽ gì."""
    def rep(m):
        r = RUBY.fullmatch(m.group(0))
        return r.group(1) if r else ""
    return TAG.sub(rep, s)


def width(s):
    d = shown(s)
    adv = sum(ADV.get(ord(c), 58.0) for c in d) * FONT_SIZE / POINT_SIZE
    return adv + max(len(d) - 1, 0) * CHAR_SPACING * FONT_SIZE / 100.0


def contrib(s):
    """Bề rộng một đoạn đứng đầu dòng và còn chữ theo sau (mọi ký tự đều tính spacing)."""
    d = shown(s)
    return (sum(ADV.get(ord(c), 58.0) for c in d) * FONT_SIZE / POINT_SIZE
            + len(d) * CHAR_SPACING * FONT_SIZE / 100.0)


def pick_prefix(marker):
    """Tiền tố thụt treo sát nhất với bề rộng của dấu đầu mục."""
    want = contrib(marker)
    return min(PREFIXES, key=lambda p: abs(contrib(p) - want))


def reflow(text):
    first = text.split("\n")[0]
    m = VN_MARKER.match(first)
    if not m:
        return None, None
    prefix = pick_prefix(m.group(0))
    flat = " ".join(l.lstrip("　 ") for l in text.split("\n"))
    out, cur = [], ""
    for w in flat.split(" "):
        if not w:
            continue
        cand = w if not cur else cur + " " + w
        if cur and width(cand) > LIMIT:
            out.append(cur)
            cur = prefix + w
        else:
            cur = cand
    if cur:
        out.append(cur)
    return "\n".join(out), prefix


def find_blocks(data):
    """Mọi tin nhắn liệt kê trong vùng novel, dò bằng script Nhật."""
    blocks = []
    for ti, t in enumerate(data["target"]):
        SL, LL = t["scriptText_Line"], t["loadLine"]
        inside, novel = False, []
        for l in SL:
            if NOVEL_ON.match(l):
                inside = True
            elif NOVEL_OFF.match(l):
                inside = False
            novel.append(inside)
        for j, ln in enumerate(LL):
            if ln < len(SL) and novel[ln] and JP_MARKER.match(SL[ln]):
                blocks.append((ti, t["scenarioID"], j))
    return blocks


def violations(text):
    lines = text.split("\n")
    bad = []
    for k, l in enumerate(lines):
        if width(l) + ENGINE_INDENT > BOX:
            bad.append("dòng %d tràn khung (%.0f > %.0f)" % (k + 1, width(l) + ENGINE_INDENT, BOX))
        if k and not l.startswith(("　", " ")):
            bad.append("dòng %d thiếu thụt treo" % (k + 1))
    return bad


def load(path):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name == "TextAsset" and o.read().m_Name == "ScenarioData":
            d = o.read()
            raw = d.m_Script
            if not isinstance(raw, str):
                raw = bytes(raw).decode("utf-8")
            return env, d, raw
    raise SystemExit("không thấy ScenarioData trong " + path)


def mirror_scripttext(script, old, new):
    """Đổi khối dòng tương ứng trong bản sao `scriptText`. None nếu không khớp chắc chắn."""
    lines, old_l, new_l = script.split("\n"), old.split("\n"), new.split("\n")
    hits = [k for k in range(len(lines) - len(old_l) + 1) if lines[k:k + len(old_l)] == old_l]
    if len(hits) != 1:
        return None
    k = hits[0]
    lines[k:k + len(old_l)] = new_l
    return "\n".join(lines)


def main():
    env, d, raw = load(BUNDLE)
    bom = "﻿" if raw.startswith("﻿") else ""
    data = json.loads(raw.lstrip("﻿"))
    blocks = find_blocks(data)
    print("khối liệt kê trong chế độ novel: %d  (khung %.0f, thụt engine %.0f, giới hạn %.0f)"
          % (len(blocks), BOX, ENGINE_INDENT, LIMIT))

    if CHECK:
        bad = 0
        for ti, sid, j in blocks:
            v = violations(data["target"][ti]["text"][j])
            if v:
                bad += 1
                print("  FAIL sID=%s text[%d]: %s" % (sid, j, "; ".join(v)))
                print("        %r" % data["target"][ti]["text"][j].split("\n")[0][:60])
        if bad:
            print("\n%d/%d khối sai — chạy `python tools\\fix_novel_list_wrap.py --apply`"
                  % (bad, len(blocks)))
            raise SystemExit(1)
        print("PASS cả %d khối đều vừa khung và có thụt treo" % len(blocks))
        return

    out, plan, skipped = raw, [], []
    scripts = {}
    for ti, sid, j in blocks:
        old = data["target"][ti]["text"][j]
        new, prefix = reflow(old)
        if new is None:
            skipped.append((sid, j, "không nhận ra dấu đầu mục"))
            continue
        if new == old:
            continue
        old_j, new_j = json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False)
        if out.count(old_j) != 1:
            skipped.append((sid, j, "chuỗi cũ khớp %d lần" % out.count(old_j)))
            continue
        out = out.replace(old_j, new_j)
        scripts.setdefault(ti, []).append((old, new))
        plan.append((ti, sid, j, old, new, prefix))

    # bản sao `scriptText` — không ai index tới nó, nhưng để lệch là để lại bẫy
    mirrored = mirror_failed = 0
    for ti, pairs in scripts.items():
        script = data["target"][ti]["scriptText"]
        cur = script
        for old, new in pairs:
            nxt = mirror_scripttext(cur, old, new)
            if nxt is None:
                mirror_failed += 1
            else:
                cur = nxt
                mirrored += 1
        if cur != script:
            old_j, new_j = (json.dumps(script, ensure_ascii=False),
                            json.dumps(cur, ensure_ascii=False))
            if out.count(old_j) != 1:
                raise SystemExit("scriptText target[%d] khớp %d lần" % (ti, out.count(old_j)))
            out = out.replace(old_j, new_j)

    for ti, sid, j, old, new, prefix in plan:
        print("\n=== sID=%s text[%d]  %d -> %d dòng  tiền tố %r (%.1f px, dấu đầu mục %.1f px)"
              % (sid, j, len(old.split("\n")), len(new.split("\n")), prefix,
                 contrib(prefix), contrib(VN_MARKER.match(old.split("\n")[0]).group(0))))
        for l in new.split("\n"):
            print("   %6.1f + %.0f = %6.1f  %s" % (width(l), ENGINE_INDENT,
                                                   width(l) + ENGINE_INDENT, l[:74]))
    for sid, j, why in skipped:
        print("\n! bỏ qua sID=%s text[%d]: %s" % (sid, j, why))
    print("\nsửa %d khối, mirror vào scriptText %d (thất bại %d), bỏ qua %d"
          % (len(plan), mirrored, mirror_failed, len(skipped)))
    if not plan:
        return

    after = json.loads(out.lstrip("﻿"))
    changed = {(ti, j) for ti, _, j, _, _, _ in plan}
    for ti, t in enumerate(data["target"]):
        ta = after["target"][ti]
        assert ta["scriptText_Line"] == t["scriptText_Line"], "scriptText_Line đổi ở target[%d]" % ti
        assert ta["loadLine"] == t["loadLine"], "loadLine đổi ở target[%d]" % ti
        assert len(ta["text"]) == len(t["text"])
        for j in range(len(t["text"])):
            if (ti, j) in changed:
                continue
            assert ta["text"][j] == t["text"][j], "text[%d] target[%d] đổi ngoài dự kiến" % (j, ti)
    for ti, sid, j, old, new, prefix in plan:
        assert after["target"][ti]["text"][j] == new
        strip = lambda s: " ".join(x.lstrip("　 ") for x in s.split("\n"))   # noqa: E731
        assert strip(new) == strip(old), "chữ đổi ở sID=%s text[%d]" % (sid, j)
        assert not violations(new), "sau khi sửa vẫn sai: %s" % violations(new)
    print("kiểm tra: loadLine/scriptText_Line nguyên vẹn, chỉ %d tin nhắn đổi, chữ không đổi"
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
    for ti, sid, j, old, new, prefix in plan:
        assert rd["target"][ti]["text"][j] == new, "đọc lại sID=%s text[%d] không khớp" % (sid, j)
    for ti, t in enumerate(data["target"]):
        assert rd["target"][ti]["loadLine"] == t["loadLine"]
        assert rd["target"][ti]["scriptText_Line"] == t["scriptText_Line"]
    print("  đọc lại: %d tin nhắn khớp, loadLine/scriptText_Line nguyên vẹn" % len(plan))


main()
