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

Narrowed again 2026-08-27 at the user's call — a **runt-line guard** on the `. ...` half.
Breaking is only worth a line when the left part ends near a line end.  If the left part
already wraps (2+ lines) and its **last** line fills less than 3/4 of the box, the break
would strand a stub and push the answer down a whole line, so the break is refused and
the text stays flat:

    ... nắm lấy cánh tay của Ran định bỏ chạy.        <- dòng 1 đầy
    ...                                               <- dòng 2 chỉ 103/960 px  -> KHÔNG ngắt
    ...Thế nhưng, chẳng hiểu sao ...

A left part that fits on **one** line is always allowed, however short — that is the
two-utterances look the rule exists for.  The rule generalises to any depth (3 lines,
4 lines): what matters is the last line of the left part.

Extended to the `... ...` half the same day, at the user's call — the guard now applies to
both.  It refuses 5 of 33 places there, the docstring's own opening example among them.

Because the guard can also *retract* breaks a previous run made, the tool now normalises
first — it flattens `… ⏎ …` (which this rule owns outright) and every `. ⏎ …` its JP gate
owns, then re-decides.  That makes it idempotent in both directions.  It never touches a
`. ⏎ …` the gate does not own (measured: 0 such places, all 631 in the build came from
this tool).  `PAT_DOT` grew a `(?<![.…])` lookbehind so it cannot bite the last dot of an
ellipsis run that the other half has just refused and left flat.

Layout cost of the extension, ADV model: **0** lines under the corner art in any group.
Across all 699 it was 160 messages gaining a line and 130 dropping a size step (worst
42 → 29.75); the gated 627 are a subset of that.  No abbreviation false positives —
every short token before the stop is a Vietnamese final particle (`rồi`, `đấy`, `nữa`,
`mà`, `nhỉ`), never an initialism.

A second guard, 2026-08-28: **a break may not add a line.**  The runt rule filters on the
left part; the tail is still free to spill, which pushes the message past the box and makes
auto-size shrink it.  `RUNT_FILL` cannot separate those cases — the two the user flagged sit
at 61 % and 71 % fill while `86/txt/0315`, which they kept, sits between them at 68 % — and
neither can "must not shrink", since that one shrinks too (42 → 40.5).  Line count does:
85 messages retracted, all 85 lose a line, 77 keep their size and **8 get bigger type**.

Chat messages are skipped entirely (`talkName` carries an `@`): their wording belongs
to `fix_chat_use_genebark.py`, which writes them flat on purpose.  Measured 0 chat
cells matching either half today — the guard is there so a later merge cannot let one
through.

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

# Bọc một lần thôi: bọc chồng lên nhau thì lớp cũ bị thu gom và ĐÓNG luôn buffer,
# và mọi print sau đó ném ValueError (đúng lỗi này khi hai script cùng bọc).
if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402
import fix_adv_wrap as LAY   # noqa: E402  — mô hình bố cục ô thoại đã hiệu chuẩn

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
# Mỗi lần đổi LUẬT thì đổi tên backup — một file cho một đợt sửa, để lùi từng bước.
# .ellipsisbreak = đợt 17-18/08/2026 (thêm ngắt); .ellipsisrunt = 27/08 (dòng cụt,
# nửa `. ...`); .ellipsisruntell = 27/08 (mở rộng sang nửa `... ...`);
# .runtfill50 = 27/08 (hạ ngưỡng dòng cụt 0,75 -> 0,50);
# .noextraline = 28/08 (chốt: ngắt không được làm tăng số dòng).
BACKUP = os.path.join(ROOT, "_backup", "scenario01.noextraline")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

STOCK = r"D:\Downloads\UNLOGICAL_v2\Data\StreamingAssets\scenario\scenario01"

# Vế trái là một CHUỖI dấu lửng: luật gốc, không phụ thuộc bản Nhật.
PAT_ELL = re.compile(r"(\.{2,}|…+) (\.{2,}|…+)")
# Vế trái là MỘT dấu chấm: chỉ ngắt khi bản Nhật cũng xuống hàng ở đúng chỗ đó.
PAT_DOT = re.compile(r"(?<![.…])(\.) (\.{2,}|…+)")
# Đã ngắt rồi: dùng để làm phẳng lại trước khi quyết định lần nữa.
ELL_BRK = re.compile(r"(\.{2,}|…+)\n(\.{2,}|…+)")
DOT_BRK = re.compile(r"(?<!\.)(\.)\n(\.{2,}|…+)")
# Bản Nhật: dấu kết câu, xuống hàng, thụt lề tuỳ ý, rồi dấu lửng.
JP_BRK = re.compile(r"[。！？]\s*\n\s*[　]*(?:…|\.{2,})")

# Dòng cuối của vế trái phải đầy ít nhất chừng này thì ngắt mới đáng một dòng.
RUNT_FILL = 0.50


def brk(m):
    return m.group(1) + "\n" + m.group(2)


def _lines_at(seg, F):
    """Bề rộng (px canvas) từng dòng TMP sẽ ngắt cho `seg` khi vẽ ở cỡ F."""
    words = [LAY.measure(w) for w in LAY.words_of(seg)]
    got = LAY.wrap_words(words, LAY.RECT_W * LAY.FMAX / F)
    return [w * F / LAY.FMAX for w, _ in got]


def runt(text, pos):
    """Ngắt ở `pos` có để lại một dòng cụt không?

    `pos` là chỉ số của `\n` vừa chèn. Vế trái tính từ lần xuống dòng cứng ngay
    trước đó — đó mới là "hàng" người chơi nhìn thấy. Vế trái gọn trong **một**
    dòng thì luôn cho ngắt, ngắn tới đâu cũng vậy: đó chính là dáng hai lượt nói
    mà luật này sinh ra để có.
    """
    F = LAY.render(text)[0]
    left = LAY.shown(text[text.rfind("\n", 0, pos) + 1:pos])
    lines = _lines_at(left, F)
    return len(lines) >= 2 and lines[-1] < RUNT_FILL * LAY.RECT_W


def break_all(s, pat):
    """Ngắt mọi chỗ khớp `pat` mà không để lại dòng cụt, quét từ trái sang.

    Thay space bằng xuống dòng nên chuỗi KHÔNG đổi độ dài — chỉ số của các match
    sau vẫn đúng, không phải dò lại từ đầu.

    Hai chốt, và chốt thứ hai mới là chốt tách được ca khó: **ngắt không được làm
    tăng số dòng**. Thêm một dòng thì auto-size co chữ, mà dòng cụt thì đã lọc rồi
    nên phần còn lại chỉ là lỗ thuần."""
    pos = 0
    base = len(LAY.render(s)[1])
    while True:
        m = pat.search(s, pos)
        if not m:
            return s
        cut = m.start() + len(m.group(1))
        cand = s[:m.start()] + brk(m) + s[m.end():]
        n = len(LAY.render(cand)[1])
        if n > base or runt(cand, cut):
            pos = m.end()          # để phẳng chỗ này, tìm chỗ kế
        else:
            s, pos, base = cand, cut + 1, n


def fix(s, jp=None, chat=False):
    """`jp` là chuỗi bản gốc cùng ô; None = không biết, khi đó chỉ áp luật dấu lửng.

    **Làm phẳng trước rồi mới quyết định**, cho cả hai nửa. Luật dòng cụt có thể thu
    lại một ngắt do lần chạy trước tạo ra, mà chỉ biết chèn thêm thì không bao giờ
    gỡ được. Nửa `... ...` do chính tool này sở hữu trọn vẹn (luật cũ ngắt mọi chỗ),
    còn nửa `. ...` chỉ làm phẳng đúng những chỗ cổng JP sở hữu.

    Vẫn chạy PAT_ELL trước PAT_DOT, và PAT_DOT có thêm lookbehind `(?<![.…])` để
    không cắn vào dấu cuối của một chuỗi dấu lửng mà luật kia vừa từ chối.
    """
    if chat:
        # Tin nhắn chat (bảng tên có @) do fix_chat_use_genebark.py sở hữu, nó cố ý
        # ghi phẳng. Hiện đo được 0 ô dính luật này; chốt để merge sau không lọt.
        return s
    s = ELL_BRK.sub(r"\1 \2", s)
    gated = bool(jp and JP_BRK.search(jp))
    if gated:
        s = DOT_BRK.sub(r"\1 \2", s)
    s = break_all(s, PAT_ELL)
    if gated:
        s = break_all(s, PAT_DOT)
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
    hits, no_jp, runt_ell, runt_dot = [], 0, 0, 0
    for ti, t in enumerate(data["target"]):
        sid = t["scenarioID"]
        names = t.get("talkName") or []
        for j, s in enumerate(t["text"]):
            jp = stock.get((sid, j))
            new = fix(s, jp, chat=(j < len(names) and "@" in (names[j] or "")))
            if new != s:
                hits.append((ti, sid, j, s, new))
                continue
            # Còn phẳng mà không đổi: hoặc luật dòng cụt chặn, hoặc bản Nhật không ngắt.
            runt_ell += len(PAT_ELL.findall(s))
            if PAT_DOT.search(s):
                if jp and JP_BRK.search(jp):
                    runt_dot += 1
                else:
                    no_jp += 1

    added = sum(1 for h in hits if h[4].count("\n") > h[3].count("\n"))
    dropped = len(hits) - added

    if CHECK:
        print("chỗ text[] còn lệch: %d  (thêm ngắt %d, gỡ ngắt %d)"
              % (len(hits), added, dropped))
        print("  bỏ qua: %d chỗ `. ...` bản Nhật không xuống hàng; luật dòng cụt "
              "<%.0f%% chặn %d chỗ `... ...` và %d chỗ `. ...`"
              % (no_jp, RUNT_FILL * 100, runt_ell, runt_dot))
        for ti, sid, j, old, new in hits[:10]:
            print("  FAIL sID=%-4s text[%-5d] %s" % (sid, j, new[:96].replace("\n", "⏎")))
        if hits:
            print("\nchạy `python tools\fix_ellipsis_break.py --apply`")
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
    print("%s%d tin nhắn đổi (thêm ngắt %d, gỡ ngắt %d); mirror vào scriptText %d "
          "(không khớp verbatim %d)"
          % (chr(10), len(hits), added, dropped, mirrored, failed))

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
        # Luật dòng cụt gỡ ngắt được, nên số xuống dòng có thể GIẢM — chỉ đòi nó ĐỔI.
        assert new.count(chr(10)) != old.count(chr(10)), (
            "không đổi ngắt dòng nào ở sID=%s text[%d]" % (sid, j))
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
