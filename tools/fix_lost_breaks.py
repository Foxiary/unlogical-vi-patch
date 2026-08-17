# -*- coding: utf-8 -*-
"""Restore what earlier merge rounds silently dropped: 3 line breaks, 2 whole lines.

Found 2026-08-17 by `check_layout_breaks.py` comparing the build against the
15 Aug backup (`_backup\\scenario01.prenamekey`) — the first time anything looked
at per-message `\\n` counts across rounds:

- Three chat messages lost their break when a pass expanded the abbreviations the
  characters text in (`E` -> `Em`, `a` -> `Anh`).  The wording is the newer one and
  stays; only the `\\n` at the sentence boundary comes back.
- Two `【player】` messages are **empty** where the JP has `「…………」`.  A round wrote a
  blank cell over them.  Those are the only two empty messages in all 39 803
  (checked against the JP build), and 300 of the 375 places where the JP says
  `「…………」` render `「......」` here, which is also the documented ellipsis rule
  (`……` -> `...`), so that is what goes back in.

Every entry states the text it expects to find, so a second run is a no-op and a
run against re-translated text refuses instead of guessing.

    python tools\\fix_lost_breaks.py [--apply]
"""
import io
import json
import os
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "scenario01.lostbreaks")
APPLY = "--apply" in sys.argv

# (scenarioID, chỉ số tin nhắn, phần trước ngắt dòng, phần sau) — nối lại bằng
# một space phải bằng đúng chuỗi đang có, nếu không thì dừng.
BREAKS = [
    (86, 49, "Em cũng định gặp để nói chuyện đây.",
             "Hẹn gặp nhau ở công viên Kirika được không?"),
    (86, 560, "Khi nào ra ngoài thì cứ gọi anh. Nhất là vào đêm muộn.",
              "Anh sẽ đến ngay lập tức."),
    (124, 161, "Cuộc điều tra của anh Yuri đang thuận lợi nhỉ.",
               "Anh cũng tò mò không biết Ban điều hành ra sao rồi nhưng mà..."),
]
# (scenarioID, chỉ số, bản Nhật phải khớp, chuỗi trả lại)
EMPTIES = [
    (107, 99, "「…………」", "「......」"),
    (107, 302, "「…………」", "「......」"),
]


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


def target_of(data, sid):
    hits = [i for i, t in enumerate(data["target"]) if t["scenarioID"] == sid]
    if len(hits) != 1:
        raise SystemExit("scenarioID %s khớp %d target" % (sid, len(hits)))
    return hits[0]


def mirror(script, old, new):
    """Đổi khối dòng tương ứng trong bản sao `scriptText`; None nếu không chắc."""
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

    jobs = []
    for sid, j, head, tail in BREAKS:
        ti = target_of(data, sid)
        cur = data["target"][ti]["text"][j]
        want_old, want_new = head + " " + tail, head + "\n" + tail
        if cur == want_new:
            print("sID=%s text[%d] đã có ngắt dòng, bỏ qua" % (sid, j))
            continue
        if cur != want_old:
            raise SystemExit("sID=%s text[%d] không như mong đợi:\n   có   %r\n   chờ  %r"
                             % (sid, j, cur, want_old))
        jobs.append((ti, sid, j, cur, want_new, "trả lại \\n"))

    for sid, j, jp_expect, new in EMPTIES:
        ti = target_of(data, sid)
        cur = data["target"][ti]["text"][j]
        if cur == new:
            print("sID=%s text[%d] đã có chữ, bỏ qua" % (sid, j))
            continue
        if cur.strip():
            raise SystemExit("sID=%s text[%d] không rỗng nữa: %r" % (sid, j, cur))
        jp = env and None
        jobs.append((ti, sid, j, cur, new, "trả lại dòng rỗng"))

    if not jobs:
        print("không có gì để sửa")
        return

    out = raw
    for ti, sid, j, old, new, what in jobs:
        # Tin nhắn rỗng: `""` xuất hiện khắp file, nên neo bằng hai phần tử kề nó
        # trong mảng `text[]` (mảng viết liền, không space sau dấu phẩy).
        if old == "":
            arr = data["target"][ti]["text"]
            assert 0 < j < len(arr) - 1, "phần tử rỗng ở đầu/cuối mảng, cần cách neo khác"
            enc = lambda s: json.dumps(s, ensure_ascii=False)      # noqa: E731
            key_old = ",".join([enc(arr[j - 1]), enc(""), enc(arr[j + 1])])
            key_new = ",".join([enc(arr[j - 1]), enc(new), enc(arr[j + 1])])
            if out.count(key_old) != 1:
                raise SystemExit("neo cho sID=%s text[%d] khớp %d lần"
                                 % (sid, j, out.count(key_old)))
            out = out.replace(key_old, key_new)
            arr[j] = new
        else:
            old_j, new_j = (json.dumps(old, ensure_ascii=False),
                            json.dumps(new, ensure_ascii=False))
            if out.count(old_j) != 1:
                raise SystemExit("sID=%s text[%d]: chuỗi cũ khớp %d lần"
                                 % (sid, j, out.count(old_j)))
            out = out.replace(old_j, new_j)
            script = data["target"][ti]["scriptText"]
            nxt = mirror(script, old, new)
            if nxt is None:
                print("   (scriptText của sID=%s không khớp verbatim, bỏ qua mirror)" % sid)
            else:
                sj_old, sj_new = (json.dumps(script, ensure_ascii=False),
                                  json.dumps(nxt, ensure_ascii=False))
                if out.count(sj_old) != 1:
                    raise SystemExit("scriptText sID=%s khớp %d lần" % (sid, out.count(sj_old)))
                out = out.replace(sj_old, sj_new)
                data["target"][ti]["scriptText"] = nxt
        print("%-18s sID=%-4s text[%-4d] %r -> %r" % (what, sid, j, old[:44], new[:52]))

    after = json.loads(out.lstrip("﻿"))
    base = json.loads(raw.lstrip("﻿"))
    changed = {(ti, j) for ti, _, j, _, _, _ in jobs}
    for ti, t in enumerate(base["target"]):
        ta = after["target"][ti]
        assert ta["scriptText_Line"] == t["scriptText_Line"], "scriptText_Line đổi"
        assert ta["loadLine"] == t["loadLine"], "loadLine đổi"
        assert len(ta["text"]) == len(t["text"])
        for j in range(len(t["text"])):
            if (ti, j) not in changed:
                assert ta["text"][j] == t["text"][j], "text[%d] target[%d] đổi ngoài dự kiến" % (j, ti)
    for ti, sid, j, old, new, _ in jobs:
        assert after["target"][ti]["text"][j] == new
        if old:
            assert new.replace("\n", " ") == old, "chữ đổi ở sID=%s" % sid
    print("\nkiểm tra: %d tin nhắn đổi, loadLine/scriptText_Line nguyên vẹn, chữ không đổi"
          % len(jobs))

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
    for ti, sid, j, old, new, _ in jobs:
        got = rd["target"][ti]["text"][j]
        assert got == new, "đọc lại sID=%s text[%d]: %r" % (sid, j, got)
    print("  đọc lại: %d tin nhắn khớp" % len(jobs))


main()
