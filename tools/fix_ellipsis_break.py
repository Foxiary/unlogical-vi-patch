# -*- coding: utf-8 -*-
"""Break the line where one ellipsis is followed by another.

Requested 2026-08-17: a sentence that trails off and is answered by another that
opens the same way reads as two utterances, so it gets two lines:

    Terminal đang gặp trục trặc... ...Kohaku, cậu có đó không?
    ->
    Terminal đang gặp trục trặc...
    ...Kohaku, cậu có đó không?

Rule: a run of ≥2 dots (or `…`), a single space, another such run -> replace that
one space with `\\n`.  Nothing else is touched, so the tool is idempotent and safe
to re-run — which it must be, because the sheet stores every cell as one flat line
and a merge flattens this again (see `apply_sheet_cells.py` and the merge memory).

Measured over the build when first applied: 33 messages, all in dialogue and none
in the `json` bundle.  Layout cost, checked with the ADV model: 11 messages gain a
line, 2 drop a size step (`sID 74 text[561]` 42 → 37.75, `sID 91 text[135]`
42 → 40.75), and **0** end up with a line under the box's corner art.

    python tools\\fix_ellipsis_break.py           # chạy thử
    python tools\\fix_ellipsis_break.py --apply
    python tools\\fix_ellipsis_break.py --check   # chốt sau merge, lỗi -> exit 1
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

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "scenario01.ellipsisbreak")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

PAT = re.compile(r"(\.{2,}|…+) (\.{2,}|…+)")


def fix(s):
    return PAT.sub(lambda m: m.group(1) + "\n" + m.group(2), s)


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

    hits = []
    for ti, t in enumerate(data["target"]):
        for j, s in enumerate(t["text"]):
            if PAT.search(s):
                hits.append((ti, t["scenarioID"], j, s, fix(s)))

    if CHECK:
        print("chỗ còn 'dấu lửng + space + dấu lửng' trong text[]: %d" % len(hits))
        for ti, sid, j, old, new in hits[:10]:
            i = PAT.search(old).start()
            print("  FAIL sID=%-4s text[%-5d] …%s…" % (sid, j, old[max(0, i - 34):i + 30]))
        if hits:
            print("\nchạy `python tools\\fix_ellipsis_break.py --apply`")
            raise SystemExit(1)
        print("PASS không còn chỗ nào")
        return

    if not hits:
        print("không có gì để sửa")
        return

    out = raw
    # Vá theo cả mảng text[] của từng target: có câu trùng nhau từng chữ nên thay
    # theo chuỗi sẽ đụng nhiều chỗ.
    def enc(x):
        return json.dumps(x, ensure_ascii=False, separators=(",", ":"))

    for ti in sorted({h[0] for h in hits}):
        arr_old = list(data["target"][ti]["text"])
        arr_new = list(arr_old)
        for t2, sid, j, old, new in [h for h in hits if h[0] == ti]:
            arr_new[j] = new
        oj, nj = enc(arr_old), enc(arr_new)
        if out.count(oj) != 1:
            raise SystemExit("mảng text[] của target[%d] khớp %d lần" % (ti, out.count(oj)))
        out = out.replace(oj, nj)

    mirrored = failed = 0
    for ti in sorted({h[0] for h in hits}):
        script = cur = data["target"][ti]["scriptText"]
        for t2, sid, j, old, new in [h for h in hits if h[0] == ti]:
            nxt = mirror(cur, old, new)
            if nxt is None:
                failed += 1
            else:
                cur = nxt
                mirrored += 1
        if cur != script:
            oj, nj = json.dumps(script, ensure_ascii=False), json.dumps(cur, ensure_ascii=False)
            if out.count(oj) != 1:
                raise SystemExit("scriptText target[%d] khớp %d lần" % (ti, out.count(oj)))
            out = out.replace(oj, nj)

    for ti, sid, j, old, new in hits[:8]:
        print("-> sID=%-4s text[%-5d] %r" % (sid, j, new[:88].replace("\n", "⏎")))
    print("\nngắt %d chỗ; mirror vào scriptText %d (không khớp verbatim %d)"
          % (len(hits), mirrored, failed))

    after = json.loads(out.lstrip("﻿"))
    changed = {(h[0], h[2]) for h in hits}
    for ti, t in enumerate(data["target"]):
        ta = after["target"][ti]
        assert ta["loadLine"] == t["loadLine"], "loadLine đổi"
        assert ta["scriptText_Line"] == t["scriptText_Line"], "scriptText_Line đổi"
        for j in range(len(t["text"])):
            if (ti, j) in changed:
                continue
            assert ta["text"][j] == t["text"][j], "text[%d] target[%d] đổi ngoài dự kiến" % (j, ti)
    for ti, sid, j, old, new in hits:
        assert after["target"][ti]["text"][j] == new
        assert new.replace("\n", " ") == old, "chữ đổi ở sID=%s text[%d]" % (sid, j)
    print("kiểm tra: chỉ %d tin nhắn đổi, chữ không đổi, loadLine nguyên vẹn" % len(hits))

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
    for ti, sid, j, old, new in hits:
        assert rd["target"][ti]["text"][j] == new, "đọc lại sID=%s text[%d] sai" % (sid, j)
    print("  đọc lại: %d tin nhắn khớp" % len(hits))


main()
