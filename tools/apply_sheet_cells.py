# -*- coding: utf-8 -*-
"""Pull a specific set of cells down from a new sheet snapshot, three-way and guarded.

For the common round: "I fixed a term on the sheet, here is the export."  Not a full
merge — `--match` narrows it to the cells you actually mean, so a terminology pass
does not drag every other unrelated edit along with it.

Three-way, because the user edits the packed game too (see the merge memory):

    new == build                 -> đã có, bỏ qua
    new != build, base == build  -> áp
    new != build, base != build  -> hai bên đều đổi, BÁO rồi bỏ qua

Ids come from the sheet's own ID column:

    76/txt/0011                      -> ScenarioData scenarioID 76, text[11]
    TerminalHomeAlertData/alert/id71 -> json bundle, that asset, field, entry id

Guards on every cell before it is written:

- `[...]` tag multiset must match, so a cell cannot rewrite a lookup key
- `[主人公]` must be present on both sides or neither
- quotes must balance (`"` even, 「」/『』 counts equal)
- **hard line breaks are carried from the build**, never taken from the sheet: the
  `sd_*` Vietnamese column is one flat line, so writing it verbatim flattens the
  layout (1 530 breaks were destroyed that way once).  difflib maps the old break
  positions onto the new wording.

    python tools\\apply_sheet_cells.py --match mainframe
    python tools\\apply_sheet_cells.py --match mainframe --apply
    python tools\\apply_sheet_cells.py --new "…(23).xlsx" --base "…(22).xlsx" --match X
"""
import difflib
import glob
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
from openpyxl import load_workbook   # noqa: E402

SCENARIO = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
JSONB = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
SNAPSHOTS = r"D:\Downloads\UNLOGICAL_v2*.xlsx"

APPLY = "--apply" in sys.argv


def arg(name, default=None):
    for a in sys.argv:
        if a.startswith("--%s=" % name):
            return a.split("=", 1)[1]
    return default


MATCH = arg("match")
TAG = re.compile(r"\[[^\[\]\n]*\]")
SD_ID = re.compile(r"^(\d+)/txt/(\d+)$")
DATA_ID = re.compile(r"^([A-Za-z&]+Data)/([A-Za-z_]+)/id(\d+)$")


def newest_two():
    cands = sorted(glob.glob(SNAPSHOTS), key=os.path.getmtime, reverse=True)
    if len(cands) < 2:
        raise SystemExit("cần ít nhất hai snapshot khớp " + SNAPSHOTS)
    return cands[0], cands[1]


def read_sheet(path):
    """{id: (tiếng Việt, tiếng Nhật)} — sd_* dịch ở cột D, Nhật ở cột C; tab *Data
    dịch ở cột C, Nhật ở cột B."""
    wb = load_workbook(path, read_only=True, data_only=True)
    out = {}
    for ws in wb.worksheets:
        vcol, jcol = (3, 2) if ws.title.startswith("sd_") else (2, 1)
        for row in ws.iter_rows(values_only=True):
            if not row or not isinstance(row[0], str):
                continue
            key = row[0].strip()
            if not (SD_ID.match(key) or DATA_ID.match(key)):
                continue
            val = row[vcol] if len(row) > vcol and isinstance(row[vcol], str) else ""
            jp = row[jcol] if len(row) > jcol and isinstance(row[jcol], str) else ""
            out[key] = (val, jp)
    wb.close()
    return out


RULE_ID = re.compile(r"^([A-Za-z&]+Data)/rule_body/id(\d+)$")


def read_rule_rows(path):
    """{(id, trang): tiếng Việt} cho tab TerminalRuleData.

    **Giữ thứ tự hàng**: mỗi id lặp lại một hàng cho mỗi trang, hàng thứ k là
    `content[k]`. Nhét vào dict theo id là gộp 39 hàng thành 21 và tab trông như
    không map được (memory `unlogical-sheet-merge`).
    """
    wb = load_workbook(path, read_only=True, data_only=True)
    out, seen = {}, {}
    for ws in wb.worksheets:
        if not ws.title.startswith("TerminalRuleData"):
            continue
        for row in ws.iter_rows(values_only=True):
            if not row or not isinstance(row[0], str):
                continue
            m = RULE_ID.match(row[0].strip())
            if not m:
                continue
            i = int(m.group(2))
            k = seen.get(i, -1) + 1
            seen[i] = k
            out[(i, k)] = row[2] if len(row) > 2 and isinstance(row[2], str) else ""
    wb.close()
    return out


def merge_rule_text(build, sheet):
    """Lấy CÂU CHỮ của sheet, giữ KHOẢNG TRẮNG ĐẦU DÒNG của build.

    Sheet đã rã hết `　` thành một space ASCII và biến dòng trắng thành một dấu
    cách, nên áp nguyên văn là ép thụt lề còn 1/3 và phá cả bậc bullet của trang
    RULE. None nếu số dòng hai bên khác nhau — chỗ đó cần người xem.
    """
    b, s = build.split("\n"), sheet.split("\n")
    if len(b) != len(s):
        return None
    out = []
    for bl, sl in zip(b, s):
        if not bl.strip():                 # dòng trắng của build giữ nguyên
            out.append(bl)
            continue
        lead = bl[:len(bl) - len(bl.lstrip("　 "))]
        out.append(lead + sl.strip())
    return "\n".join(out)


def duplicate_paste(todo):
    """Bắt lỗi "bản dịch rơi vào sai ô": hai ô đổi trong cùng vòng mà bản dịch mới
    giống nhau từng chữ trong khi bản Nhật của chúng khác nhau — dấu hiệu dán đè.

    Đã bắt được thật ở snapshot (24): `71/txt/0379` mang bản dịch của `71/txt/0377`.
    """
    by_val = {}
    for key, bv, nv, jp in todo:
        by_val.setdefault(nv, []).append((key, jp, bv))
    bad = set()
    for nv, rows in by_val.items():
        if len(rows) < 2 or len({jp for _, jp, _ in rows}) < 2:
            continue
        # Ô nào bị dán đè thì bản mới của nó KHÁC XA bản cũ của chính nó; ô lành chỉ
        # sửa nhẹ. Nhờ vậy không chặn oan ô lành trong cùng nhóm.
        ratio = {key: difflib.SequenceMatcher(None, bv, nv).ratio() for key, _, bv in rows}
        keep = max(ratio, key=ratio.get)
        for key in ratio:
            if key != keep or ratio[keep] < 0.6:
                bad.add(key)
    return bad


def load_text(path, name):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name == "TextAsset" and o.read().m_Name == name:
            d = o.read()
            raw = d.m_Script
            if not isinstance(raw, str):
                raw = bytes(raw).decode("utf-8")
            return env, d, raw
    raise SystemExit("không thấy %s trong %s" % (name, path))


def carry_breaks(old, new):
    """Đặt lại các `\\n` của bản build lên câu chữ mới, theo vị trí ký tự đã khớp."""
    if "\n" not in old:
        return new
    flat = old.replace("\n", " ")
    sm = difflib.SequenceMatcher(None, flat, new, autojunk=False)
    mapping = {}
    for a, b, n in sm.get_matching_blocks():
        for i in range(n):
            mapping[a + i] = b + i
    out = list(new)
    marks = []
    for i, c in enumerate(flat):
        if c == " " and old[i] == "\n":
            j = mapping.get(i)
            if j is not None and j < len(out) and out[j] == " ":
                marks.append(j)
    for j in marks:
        out[j] = "\n"
    got = "".join(out)
    if got.count("\n") != old.count("\n"):
        return None            # không đặt lại đủ -> để người xem quyết
    return got


RUBY = re.compile(r"\[([^\[\]\n']*?)'([^\[\]\n]*?)\]")
DIC = re.compile(r"\[dic\s+no=(\d+)\s+text=([^\[\]\n]*)\]")


def tag_key(t):
    """Khoá so sánh tag: phần nào là KHOÁ TRA CỨU thì so nguyên văn, phần nào chỉ để
    hiển thị thì bỏ qua.

    - `[gốc'ruby]`: cả hai nửa đều là chữ hiển thị, nên **cho phép đảo** (so theo tập
      hợp) — đó là đợt sửa `[Người lựa chọn'Selector]` -> `[Selector'Người lựa chọn]`.
      Đổi *nội dung* một nửa thì vẫn bị chặn.
    - `[dic no=N text=X]`: `no` là khoá, `text` là chữ hiển thị.
    - còn lại (lệnh diễn xuất, `[se file=…]`, `[主人公]`) so nguyên văn.
    """
    m = RUBY.fullmatch(t)
    if m and not t.startswith("[dic "):
        return "RUBY:" + "|".join(sorted([m.group(1), m.group(2)]))
    m = DIC.fullmatch(t)
    if m:
        return "DIC:" + m.group(1)
    return t


def is_ruby(t):
    return bool(RUBY.fullmatch(t)) and not t.startswith("[dic ")


def ruby_change_ok(old, new):
    """Tag ruby được phép đổi theo ba cách: giữ nguyên, **đảo hai nửa**, hoặc **bỏ tag
    mà giữ lại một nửa làm chữ thường** (vòng (28) bỏ gloss: `[Thiên thần tập sự'Spirit]`
    -> `Spirit`). Mất tag mà cả hai nửa cũng mất thì là xoá hụt — chặn."""
    for t in TAG.findall(old):
        if not is_ruby(t):
            continue
        if t in new:
            continue
        m = RUBY.fullmatch(t)
        if "[%s'%s]" % (m.group(2), m.group(1)) in new:
            continue
        if m.group(1) in new or m.group(2) in new:
            continue
        return "mất tag ruby %s mà không giữ lại nửa nào" % t
    return None


def guards(old, new):
    bad = []
    # Khoá tra cứu: lệnh diễn xuất, [主人公], [se file=…]… phải khớp từng cái.
    lookup = lambda s: sorted(t for t in TAG.findall(s)                      # noqa: E731
                              if not is_ruby(t) and not DIC.fullmatch(t))
    if lookup(old) != lookup(new):
        bad.append("tag khoá tra cứu bị đổi")
    # Link từ điển: `no=` không được đổi/mất (chữ hiển thị thì tuỳ).
    dic_nos = lambda s: sorted(m.group(1) for m in DIC.finditer(s))          # noqa: E731
    if dic_nos(old) != dic_nos(new):
        bad.append("link [dic no=…] bị đổi hoặc mất")
    r = ruby_change_ok(old, new)
    if r:
        bad.append(r)
    if ("[主人公]" in old) != ("[主人公]" in new):
        bad.append("token [主人公] chỉ có ở một bên")
    if new.count('"') % 2:
        bad.append("số dấu \" lẻ")
    for a, b in (("「", "」"), ("『", "』")):
        if new.count(a) != new.count(b):
            bad.append("ngoặc %s%s không cân" % (a, b))
    return bad


def main():
    new_f, base_f = arg("new"), arg("base")
    if not new_f or not base_f:
        n, b = newest_two()
        new_f, base_f = new_f or n, base_f or b
    print("sheet mới : %s" % new_f)
    print("sheet nền : %s" % base_f)
    print("lọc       : %s" % (MATCH or "(không lọc — mọi ô đã đổi)"))
    new, base = read_sheet(new_f), read_sheet(base_f)

    pat = re.compile(MATCH, re.I) if MATCH else None
    todo = []
    for key, (nv, jp) in new.items():
        b = base.get(key)
        if b is None or nv == b[0]:
            continue
        if pat and not (pat.search(nv) or pat.search(b[0])):
            continue
        todo.append((key, b[0], nv, jp))
    print("ô đã đổi trên sheet và khớp bộ lọc: %d" % len(todo))
    dup = duplicate_paste(todo)
    if dup:
        print("\n!! %d ô có DẤU HIỆU DÁN ĐÈ trên sheet "
              "(bản dịch mới trùng nhau mà bản Nhật khác nhau)" % len(dup))
        for key in sorted(dup):
            jp = next(j for k, _, _, j in todo if k == key)
            print("   %-14s JP: %r" % (key, jp[:64].replace("\n", "⏎")))
        print("   -> bỏ qua những ô này; sửa trên sheet rồi chạy lại")
        todo = [t for t in todo if t[0] not in dup]
    print()
    if not todo:
        return

    env_s, d_s, raw_s = load_text(SCENARIO, "ScenarioData")
    data_s = json.loads(raw_s.lstrip("﻿"))
    sid_map = {t["scenarioID"]: ti for ti, t in enumerate(data_s["target"])}
    out_s, changed_s = raw_s, []
    json_edits = []

    for key, bv, nv, _jp in sorted(todo):
        m = SD_ID.match(key)
        if m:
            sid, idx = int(m.group(1)), int(m.group(2))
            ti = sid_map.get(sid)
            if ti is None:
                print("! %s: không có scenarioID %d" % (key, sid)); continue
            cur = data_s["target"][ti]["text"][idx]
            kind = "ScenarioData"
        elif RULE_ID.match(key):
            continue                     # xử lý riêng ở nhánh rule_body bên dưới
        else:
            m = DATA_ID.match(key)
            if not m:
                print("! %s: id lạ" % key); continue
            asset, field, eid = m.group(1), m.group(2), int(m.group(3))
            _, _, raw_j = load_text(JSONB, asset)
            dj = json.loads(raw_j.lstrip("﻿"))
            rows = dj.get("data", dj)
            ent = next((e for e in rows if e.get("id") == eid), None)
            if ent is None:
                print("! %s: không có id %d trong %s" % (key, eid, asset)); continue
            cur = ent.get(field, "")
            kind = asset

        # So ba chiều trên bản ĐÃ LÀM PHẲNG: build giữ `\n` mà sheet thì không, nên
        # so nguyên văn sẽ báo "cả hai bên đổi" cho cả những ô build vốn đã đúng.
        flat_cur = cur.replace("\n", " ")
        if flat_cur == nv:
            print("=  %-34s đã có bản mới" % key); continue
        if flat_cur != bv:
            print("!! %-34s CẢ HAI BÊN ĐỔI — bỏ qua" % key)
            print("      nền   : %r" % bv[:88])
            print("      build : %r" % flat_cur[:88])
            print("      sheet : %r" % nv[:88])
            continue
        bad = guards(cur, nv)
        if bad:
            print("!! %-34s chốt chặn: %s" % (key, "; ".join(bad))); continue
        val = carry_breaks(cur, nv)
        if val is None:
            print("!! %-34s không đặt lại được %d ngắt dòng — bỏ qua"
                  % (key, cur.count("\n"))); continue

        print("-> %-34s %s" % (key, kind))
        print("      cũ : %r" % cur[:88].replace("\n", "⏎"))
        print("      mới: %r" % val[:88].replace("\n", "⏎"))
        if kind == "ScenarioData":
            changed_s.append((ti, sid, idx, cur, val))
        else:
            json_edits.append((kind, field, eid, cur, val))

    # ---- ScenarioData: text[] + bản sao scriptText
    # Vá theo CẢ MẢNG `text[]` của từng target, không theo từng chuỗi: có những câu
    # trùng nhau từng chữ (70/txt/1216 và 1218), thay theo chuỗi sẽ đụng cả hai.
    if changed_s:
        def enc(x):
            return json.dumps(x, ensure_ascii=False, separators=(",", ":"))
        for ti in sorted({c[0] for c in changed_s}):
            arr_old = list(data_s["target"][ti]["text"])
            arr_new = list(arr_old)
            for t2, sid, idx, cur, val in [c for c in changed_s if c[0] == ti]:
                assert arr_new[idx] == cur, "text[%d] không như đã đọc" % idx
                arr_new[idx] = val
            oj, nj = enc(arr_old), enc(arr_new)
            if out_s.count(oj) != 1:
                raise SystemExit("mảng text[] của target[%d] khớp %d lần" % (ti, out_s.count(oj)))
            out_s = out_s.replace(oj, nj)
        for ti in sorted({c[0] for c in changed_s}):
            script = cur_script = data_s["target"][ti]["scriptText"]
            for t2, sid, idx, cur, val in [c for c in changed_s if c[0] == ti]:
                lines = cur_script.split("\n")
                ol = cur.split("\n")
                hits = [k for k in range(len(lines) - len(ol) + 1) if lines[k:k + len(ol)] == ol]
                if len(hits) == 1:
                    lines[hits[0]:hits[0] + len(ol)] = val.split("\n")
                    cur_script = "\n".join(lines)
                else:
                    print("   (scriptText sID=%s text[%d]: khớp %d lần, bỏ qua mirror)"
                          % (sid, idx, len(hits)))
            if cur_script != script:
                oj, nj = (json.dumps(script, ensure_ascii=False),
                          json.dumps(cur_script, ensure_ascii=False))
                if out_s.count(oj) != 1:
                    raise SystemExit("scriptText target[%d] khớp %d lần" % (ti, out_s.count(oj)))
                out_s = out_s.replace(oj, nj)

    # ---- nhánh rule_body: map theo (id, trang), giữ khoảng trắng đầu dòng của build
    rule_edits = []
    rn, rb = read_rule_rows(new_f), read_rule_rows(base_f)
    rkeys = [k for k in rn if k in rb and rn[k] != rb[k]]
    if rkeys:
        _, _, raw_r = load_text(JSONB, "TerminalRuleData")
        tr = json.loads(raw_r.lstrip("﻿"))
        items = {it["id"]: it for g in tr["data"] for it in g["items"]}
        print("hàng rule_body đổi trên sheet: %d" % len(rkeys))
        for (i, k) in sorted(rkeys):
            it = items.get(i)
            if it is None or k >= len(it.get("content", [])):
                print("!! rule_body id%d trang %d: không có trong asset" % (i, k))
                continue
            cur = it["content"][k]["text"]
            val = merge_rule_text(cur, rn[(i, k)])
            if val is None:
                print("!! rule_body id%d trang %d: số dòng lệch (build %d / sheet %d) — bỏ qua"
                      % (i, k, cur.count("\n") + 1, rn[(i, k)].count("\n") + 1))
                continue
            if val == cur:
                print("=  rule_body id%d trang %d: đã có bản mới" % (i, k))
                continue
            if val.count("　") < cur.count("　"):
                print("!! rule_body id%d trang %d: mất %d thụt lề `　` — bỏ qua"
                      % (i, k, cur.count("　") - val.count("　")))
                continue
            bad = guards(cur, val)
            if bad:
                print("!! rule_body id%d trang %d: %s" % (i, k, "; ".join(bad)))
                continue
            diff = [l for l in difflib.unified_diff(cur.split("\n"), val.split("\n"),
                                                    lineterm="", n=0)
                    if l[:1] in "+-" and l[:3] not in ("+++", "---")]
            print("-> rule_body id%d trang %d  (%d dòng đổi)" % (i, k, len(diff) // 2))
            for l in diff[:4]:
                print("      %s" % l[:96])
            rule_edits.append((i, k, cur, val))

    print("\náp được: %d ô ScenarioData, %d ô bundle json, %d trang rule_body"
          % (len(changed_s), len(json_edits), len(rule_edits)))
    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    tag = os.path.splitext(os.path.basename(new_f))[0].replace(" ", "")
    if changed_s:
        bak = os.path.join(ROOT, "_backup", "scenario01.%s" % tag)
        if not os.path.exists(bak):
            shutil.copy2(SCENARIO, bak); print("backup ->", bak)
        d_s.m_Script = ("﻿" if raw_s.startswith("﻿") else "") + out_s.lstrip("﻿")
        d_s.save()
        with open(SCENARIO, "wb") as f:
            f.write(env_s.file.save(packer="lz4"))
        print("đã ghi", SCENARIO, os.path.getsize(SCENARIO))
        _, _, back = load_text(SCENARIO, "ScenarioData")
        rd = json.loads(back.lstrip("﻿"))
        for ti, sid, idx, cur, val in changed_s:
            assert rd["target"][ti]["text"][idx] == val, "đọc lại %s text[%d] sai" % (sid, idx)
            assert rd["target"][ti]["loadLine"] == data_s["target"][ti]["loadLine"]
        print("  đọc lại: %d ô khớp, loadLine nguyên vẹn" % len(changed_s))

    if rule_edits:
        bak = os.path.join(ROOT, "_backup", "json.%s" % tag)
        if not os.path.exists(bak):
            shutil.copy2(JSONB, bak); print("backup ->", bak)
        env_r, d_r, raw_r = load_text(JSONB, "TerminalRuleData")
        out_r = raw_r
        for i, k, cur, val in rule_edits:
            oj, nj = json.dumps(cur, ensure_ascii=False), json.dumps(val, ensure_ascii=False)
            if out_r.count(oj) != 1:
                raise SystemExit("rule_body id%d trang %d khớp %d lần" % (i, k, out_r.count(oj)))
            out_r = out_r.replace(oj, nj)
        d_r.m_Script = ("﻿" if raw_r.startswith("﻿") else "") + out_r.lstrip("﻿")
        d_r.save()
        with open(JSONB, "wb") as f:
            f.write(env_r.file.save(packer="lz4"))
        print("đã ghi", JSONB, os.path.getsize(JSONB))
        _, _, back = load_text(JSONB, "TerminalRuleData")
        tr2 = json.loads(back.lstrip("﻿"))
        items2 = {it["id"]: it for g in tr2["data"] for it in g["items"]}
        for i, k, cur, val in rule_edits:
            assert items2[i]["content"][k]["text"] == val, \
                "đọc lại rule_body id%d trang %d sai" % (i, k)
        print("  đọc lại: %d trang rule_body khớp" % len(rule_edits))

    if json_edits:
        bak = os.path.join(ROOT, "_backup", "json.%s" % tag)
        if not os.path.exists(bak):
            shutil.copy2(JSONB, bak); print("backup ->", bak)
        for asset in sorted({e[0] for e in json_edits}):
            env_j, d_j, raw_j = load_text(JSONB, asset)
            out_j = raw_j
            for a, field, eid, cur, val in [e for e in json_edits if e[0] == asset]:
                oj, nj = (json.dumps(cur, ensure_ascii=False), json.dumps(val, ensure_ascii=False))
                if out_j.count(oj) != 1:
                    raise SystemExit("%s id%d: chuỗi cũ khớp %d lần" % (asset, eid, out_j.count(oj)))
                out_j = out_j.replace(oj, nj)
            d_j.m_Script = ("﻿" if raw_j.startswith("﻿") else "") + out_j.lstrip("﻿")
            d_j.save()
            with open(JSONB, "wb") as f:
                f.write(env_j.file.save(packer="lz4"))
            print("đã ghi", JSONB, os.path.getsize(JSONB))
            _, _, back = load_text(JSONB, asset)
            rows = json.loads(back.lstrip("﻿"))
            rows = rows.get("data", rows)
            for a, field, eid, cur, val in [e for e in json_edits if e[0] == asset]:
                ent = next(e for e in rows if e.get("id") == eid)
                assert ent[field] == val, "đọc lại %s id%d sai" % (asset, eid)
            print("  đọc lại: %s khớp" % asset)


main()
