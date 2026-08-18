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

Extended 2026-08-18 at the user's call: **a full stop also counts as the left run**
(`tham gia. ...Nói đúng hơn` -> two lines) — but **only where stock breaks the line at
that same spot**, which is the user's condition (asked and answered the same day: "nếu
bản jp cũng xuống hàng với `. ...` thì mới làm, còn không thì giữ nguyên").  So this
half of the rule is NOT a pure text rule: it reads the untouched 1.0.2 bundle at
`STOCK` and requires `。/！/？` + newline + optional `　` + ellipsis in the same message.

Of 699 candidate places, 627 pass that gate.  The 72 refused are 68 where stock keeps
the ellipsis on the same line (`「なーんだ、残念。……ま、いいけどさ」`) and 4 with no
matching shape at all.  Every candidate message holds exactly **one** match, so gating
per message is positionally exact — no need to pair up match offsets.

Only `.` was added, not `!`/`?`: those exist too (41 and 118 places) and are left alone
until asked for.  The old ellipsis-to-ellipsis half stays ungated — it was ratified on
its own and does not depend on stock.

Layout cost of the extension, ADV model: **0** lines under the corner art in any group.
Across all 699 it was 160 messages gaining a line and 130 dropping a size step (worst
42 → 29.75); the gated 627 are a subset of that.  No abbreviation false positives —
every short token before the stop is a Vietnamese final particle (`rồi`, `đấy`, `nữa`,
`mà`, `nhỉ`), never an initialism.

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

STOCK = r"D:\Downloads\UNLOGICAL_v2\Data\StreamingAssets\scenario\scenario01"

# Vế trái là một CHUỖI dấu lửng: luật gốc, không phụ thuộc bản Nhật.
PAT_ELL = re.compile(r"(\.{2,}|…+) (\.{2,}|…+)")
# Vế trái là MỘT dấu chấm: chỉ ngắt khi bản Nhật cũng xuống hàng ở đúng chỗ đó.
PAT_DOT = re.compile(r"(\.) (\.{2,}|…+)")
# Bản Nhật: dấu kết câu, xuống hàng, thụt lề tuỳ ý, rồi dấu lửng.
JP_BRK = re.compile(r"[。！？]\s*\n\s*[\u3000]*(?:…|\.{2,})")
# Dùng cho `--check`: chỗ nào ĐÁNG LẼ phải ngắt mà chưa ngắt.
PAT = PAT_ELL


def brk(m):
    return m.group(1) + "\n" + m.group(2)


def fix(s, jp=None):
    """`jp` là chuỗi bản gốc cùng ô; None = không biết, khi đó chỉ áp luật dấu lửng.

    Chạy PAT_ELL trước rồi mới PAT_DOT: sau bước đầu không còn `... ...` nào, nên
    PAT_DOT không thể cắn vào dấu cuối của một chuỗi dấu lửng.
    """
    s = PAT_ELL.sub(brk, s)
    if jp and JP_BRK.search(jp):
        s = PAT_DOT.sub(brk, s)
    return s


def stock_text():
    """{(scenarioID, j): chuỗi} của bản 1.0.2 chưa sửa."""
    if not os.path.exists(STOCK):
        raise SystemExit("không thấy bản gốc để đối chiếu: %s" % STOCK)
    _, _, raw = load(STOCK)
    data = json.loads(raw.lstrip("﻿"))
    return {(t["scenarioID"], j): s
            for t in data["target"] for j, s in enumerate(t["text"])}


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

    stock = stock_text()
    hits, refused = [], 0
    for ti, t in enumerate(data["target"]):
        sid = t["scenarioID"]
        for j, s in enumerate(t["text"]):
            new = fix(s, stock.get((sid, j)))
            if new != s:
                hits.append((ti, sid, j, s, new))
            elif PAT_DOT.search(s):
                refused += 1          # có `. ...` nhưng bản Nhật không xuống hàng

    if CHECK:
        print("chỗ còn phải ngắt trong text[]: %d   (bỏ qua %d chỗ `. ...` "
              "vì bản Nhật không xuống hàng)" % (len(hits), refused))
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
        # Phải làm phẳng CẢ HAI bên: từ khi dấu chấm cũng tính là vế trái, luật đụng
        # cả những ô vốn đã có `\n` sẵn, nên so `new` phẳng với `old` nguyên văn là sai.
        assert new.replace("\n", " ") == old.replace("\n", " "), \
            "chữ đổi ở sID=%s text[%d]" % (sid, j)
        assert new.count("\n") > old.count("\n"), "không thêm ngắt dòng nào ở sID=%s text[%d]" % (sid, j)
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
