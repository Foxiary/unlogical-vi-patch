# -*- coding: utf-8 -*-
"""Chốt một cách gọi duy nhất cho ターミナル: **Terminal**.

Vòng sheet (32) đã đổi 118 ô `text[]` từ "thiết bị đầu cuối" sang "Terminal" nhưng
không với tới ba chỗ, vì tab `sd_*` của sheet không mang chúng:

- `selText[]` — nhãn lựa chọn, sheet không có cột cho nó (2 chỗ)
- `scriptText` — bản mirror của script, `apply_sheet_cells.py` bỏ qua khi chuỗi cũ
  khớp nhiều lần trong script (28 chỗ)
- `TerminalRuleData` — sheet ghi "terminal" chữ thường ở 3 dòng, và một dòng nữa
  (id46) bị bỏ qua vì lệch số dòng nên vẫn còn "thiết bị"

Ba luật, chỉ chạy trên chữ HIỂN THỊ:

1. `thiết bị đầu cuối` / `Thiết bị đầu cuối` -> `Terminal`
2. `terminal` đứng riêng (không phải một phần của từ Latin dài hơn) -> `Terminal`
3. bảng `PLAN` — mấy chỗ một lần, gọi là "thiết bị" mà bản Nhật là ターミナル

**Không** quét `thiết bị` đứng một mình: 85 chỗ trong `text[]` và hơn nửa là thiết bị
thật (`thiết bị y tế`, `thiết bị điện tử`, `thiết bị nghe lén`, `thiết bị VR`), phải
xem từng câu mới biết. Xem `--report` để có danh sách.

`scriptText_Line` là cột script gốc để đối chiếu — không đụng, `check_scripts.py`
và `apply_sheet_cells.py` đều dựa vào nó.

    python tools\\fix_terminal_term.py            # chạy thử
    python tools\\fix_terminal_term.py --apply
    python tools\\fix_terminal_term.py --check    # chốt sau merge, còn sót -> exit 1
    python tools\\fix_terminal_term.py --report   # liệt kê `thiết bị` cần người xem
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

SCEN = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
JSONB = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
BAK_SCEN = os.path.join(ROOT, "_backup", "scenario01.terminalterm")
BAK_JSON = os.path.join(ROOT, "_backup", "json.terminalterm")

APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv
REPORT = "--report" in sys.argv

PHRASE = re.compile(r"[Tt]hiết bị đầu cuối")
LOWER = re.compile(r"(?<![0-9A-Za-zÀ-ỹ])terminal(?![0-9A-Za-zÀ-ỹ])")

# Chỗ gọi là "thiết bị" mà bản Nhật là ターミナル — sửa từng chỗ, không quét.
# (asset, id, trang, chuỗi cũ, chuỗi mới)
PLAN = [
    ("TerminalRuleData", 46, 1,
     '　Có thể tiến hành "Bỏ phiếu tìm hung thủ" qua thiết bị.',
     '　Có thể tiến hành "Bỏ phiếu tìm hung thủ" qua Terminal.'),
]

# Câu chứa `thiết bị` mà KHÔNG phải Terminal — để --report khỏi kêu oan.
NOT_TERMINAL = re.compile(
    r"thiết bị (y tế|điện tử|mạng|VR|GPS|định vị|nghe lén|phát tín hiệu|giải trí|mới|gì)"
)


def norm(s):
    return LOWER.sub("Terminal", PHRASE.sub("Terminal", s))


def load(path, name):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name == "TextAsset":
            d = o.read()
            if d.m_Name == name:
                raw = d.m_Script
                if not isinstance(raw, str):
                    raw = bytes(raw).decode("utf-8")
                return env, d, raw
    raise SystemExit("không thấy %s trong %s" % (name, path))


def enc(x):
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))


def sub1(blob, old, new, what):
    """Thay đúng một lần, không thì dừng — chuỗi khớp nhiều lần là dấu hiệu bắt sai chỗ."""
    n = blob.count(old)
    if n != 1:
        raise SystemExit("%s: chuỗi cũ khớp %d lần (cần 1)" % (what, n))
    return blob.replace(old, new)


# ---------------------------------------------------------------- ScenarioData
def scan_scen(data):
    """[(ti, sID, field, idx, cũ, mới)] cho text[] và selText[]; scriptText tính riêng."""
    hits = []
    for ti, t in enumerate(data["target"]):
        for field in ("text", "selText"):
            for i, s in enumerate(t.get(field) or []):
                if not isinstance(s, str):
                    continue
                v = norm(s)
                if v != s:
                    hits.append((ti, t["scenarioID"], field, i, s, v))
    return hits


def report(data, rule):
    print("=== `thiết bị` đứng một mình trong text[] — cần người xem từng câu ===")
    n = amb = 0
    for t in data["target"]:
        for i, s in enumerate(t["text"]):
            for m in re.finditer(r"thiết bị", s):
                if s[m.end():].startswith(" đầu cuối"):
                    continue
                n += 1
                seg = s[m.start():m.start() + 40]
                if NOT_TERMINAL.search(seg):
                    continue
                amb += 1
                print("  %d/txt/%04d  %s" % (t["scenarioID"], i,
                                             s[max(0, m.start() - 50):m.start() + 60]))
    print("\n  %d chỗ `thiết bị`, %d chỗ CÓ THỂ là Terminal (%d chỗ rõ là thiết bị khác)"
          % (n, amb, n - amb))
    print("\n=== `thiết bị Terminal` — thừa chữ sau khi đổi tên ===")
    for t in data["target"]:
        for i, s in enumerate(t["text"]):
            if "thiết bị Terminal" in s:
                print("  %d/txt/%04d  %r" % (t["scenarioID"], i, s[:110]))
    print("\n=== TerminalRuleData: dòng còn `thiết bị` ===")
    for g in rule["data"]:
        for it in g["items"]:
            for k, c in enumerate(it.get("content", [])):
                for ln in c["text"].split("\n"):
                    if "thiết bị" in ln:
                        print("  id%-4d trang%d  %r" % (it["id"], k, ln))


def main():
    env_s, d_s, raw_s = load(SCEN, "ScenarioData")
    bom_s = "﻿" if raw_s.startswith("﻿") else ""
    data = json.loads(raw_s.lstrip("﻿"))
    env_r, d_r, raw_r = load(JSONB, "TerminalRuleData")
    bom_r = "﻿" if raw_r.startswith("﻿") else ""
    rule = json.loads(raw_r.lstrip("﻿"))

    if REPORT:
        report(data, rule)
        return

    hits = scan_scen(data)
    # scriptText: mirror, gom riêng vì nó là một chuỗi to
    mirrors = [(ti, t["scenarioID"], t["scriptText"], norm(t["scriptText"]))
               for ti, t in enumerate(data["target"])
               if norm(t["scriptText"]) != t["scriptText"]]
    # TerminalRuleData
    items = {it["id"]: it for g in rule["data"] for it in g["items"]}
    rule_hits = []
    for i, it in sorted(items.items()):
        for k, c in enumerate(it.get("content", [])):
            cur = c["text"]
            new = norm(cur)
            for asset, pid, pk, po, pn in PLAN:
                if asset != "TerminalRuleData" or pid != i or pk != k:
                    continue
                if po in new:
                    new = new.replace(po, pn)
                elif pn not in new:      # đã áp rồi thì im; không thấy cả hai mới là lạ
                    print("!  PLAN id%d trang%d: không thấy chuỗi cũ lẫn chuỗi mới" % (i, k))
            if new != cur:
                rule_hits.append((i, k, cur, new))

    if CHECK:
        bad = len(hits) + len(mirrors) + len(rule_hits)
        for ti, sid, field, i, old, _new in hits:
            print("  FAIL %d/%s/%04d  %r" % (sid, field, i, old[:100]))
        for ti, sid, _o, _n in mirrors:
            print("  FAIL sID=%d scriptText còn cách gọi cũ" % sid)
        for i, k, _o, _n in rule_hits:
            print("  FAIL TerminalRuleData id%d trang%d" % (i, k))
        if bad:
            print("\n%d chỗ chưa chuẩn — chạy `python tools\\fix_terminal_term.py --apply`" % bad)
            raise SystemExit(1)
        print("PASS mọi chỗ hiển thị đều gọi là 'Terminal'")
        return

    if not (hits or mirrors or rule_hits):
        print("không có gì để sửa")
        return

    for ti, sid, field, i, old, new in hits:
        print("-> %d/%s/%04d" % (sid, field, i))
        print("      cũ : %r" % old[:100].replace("\n", "⏎"))
        print("      mới: %r" % new[:100].replace("\n", "⏎"))
    for i, k, old, new in rule_hits:
        for a, b in zip(old.split("\n"), new.split("\n")):
            if a != b:
                print("-> TerminalRuleData id%d trang%d" % (i, k))
                print("      cũ : %r" % a)
                print("      mới: %r" % b)
    print("\nselText/text: %d ô | scriptText mirror: %d script | rule_body: %d trang"
          % (len(hits), len(mirrors), len(rule_hits)))

    # ---- dựng ScenarioData mới
    out_s = raw_s
    for ti in sorted({h[0] for h in hits}):
        for field in ("text", "selText"):
            rows = [h for h in hits if h[0] == ti and h[2] == field]
            if not rows:
                continue
            arr_old = list(data["target"][ti][field])
            arr_new = list(arr_old)
            for _t, _sid, _f, i, old, new in rows:
                assert arr_new[i] == old, "%s[%d] không như đã đọc" % (field, i)
                arr_new[i] = new
            out_s = sub1(out_s, enc(arr_old), enc(arr_new),
                         "%s[] của target[%d]" % (field, ti))
    for ti, sid, old, new in mirrors:
        out_s = sub1(out_s, json.dumps(old, ensure_ascii=False),
                     json.dumps(new, ensure_ascii=False), "scriptText target[%d]" % ti)

    after = json.loads(out_s.lstrip("﻿"))
    changed = {(h[0], h[2], h[3]) for h in hits}
    for ti, t in enumerate(data["target"]):
        ta = after["target"][ti]
        assert ta["loadLine"] == t["loadLine"], "loadLine đổi ở target[%d]" % ti
        assert ta["selLine"] == t["selLine"], "selLine đổi ở target[%d]" % ti
        assert ta["scriptText_Line"] == t["scriptText_Line"], "scriptText_Line đổi"
        for field in ("text", "selText"):
            for i, s in enumerate(t.get(field) or []):
                if (ti, field, i) in changed:
                    continue
                assert ta[field][i] == s, "%s[%d] target[%d] đổi ngoài dự kiến" % (field, i, ti)
    for ti, sid, field, i, old, new in hits:
        assert after["target"][ti][field][i] == new
        assert PHRASE.search(new) is None and LOWER.search(new) is None
    print("kiểm tra: chỉ %d ô đổi, loadLine/selLine/scriptText_Line nguyên vẹn" % len(hits))

    # ---- dựng TerminalRuleData mới
    out_r = raw_r
    for i, k, old, new in rule_hits:
        out_r = sub1(out_r, json.dumps(old, ensure_ascii=False),
                     json.dumps(new, ensure_ascii=False),
                     "rule_body id%d trang%d" % (i, k))
    for i, k, old, new in rule_hits:
        assert old.count("\n") == new.count("\n"), "id%d trang%d đổi số dòng" % (i, k)
        assert old.count("　") == new.count("　"), "id%d trang%d đổi thụt lề" % (i, k)

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if hits or mirrors:
        if not os.path.exists(BAK_SCEN):
            shutil.copy2(SCEN, BAK_SCEN)
            print("backup ->", BAK_SCEN)
        d_s.m_Script = bom_s + out_s.lstrip("﻿")
        d_s.save()
        with open(SCEN, "wb") as f:
            f.write(env_s.file.save(packer="lz4"))
        print("đã ghi", SCEN, os.path.getsize(SCEN))
        _, _, back = load(SCEN, "ScenarioData")
        rd = json.loads(back.lstrip("﻿"))
        for ti, sid, field, i, old, new in hits:
            assert rd["target"][ti][field][i] == new, \
                "đọc lại %d/%s/%d sai" % (sid, field, i)
        for ti, sid, old, new in mirrors:
            assert rd["target"][ti]["scriptText"] == new, "đọc lại scriptText %d sai" % sid
        print("  đọc lại: %d ô + %d scriptText khớp" % (len(hits), len(mirrors)))

    if rule_hits:
        if not os.path.exists(BAK_JSON):
            shutil.copy2(JSONB, BAK_JSON)
            print("backup ->", BAK_JSON)
        env_r2, d_r2, _ = load(JSONB, "TerminalRuleData")
        d_r2.m_Script = bom_r + out_r.lstrip("﻿")
        d_r2.save()
        with open(JSONB, "wb") as f:
            f.write(env_r2.file.save(packer="lz4"))
        print("đã ghi", JSONB, os.path.getsize(JSONB))
        _, _, back = load(JSONB, "TerminalRuleData")
        tr = json.loads(back.lstrip("﻿"))
        items2 = {it["id"]: it for g in tr["data"] for it in g["items"]}
        for i, k, old, new in rule_hits:
            assert items2[i]["content"][k]["text"] == new, \
                "đọc lại rule_body id%d trang%d sai" % (i, k)
        print("  đọc lại: %d trang rule_body khớp" % len(rule_hits))


main()
