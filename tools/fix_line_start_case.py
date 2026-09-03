# -*- coding: utf-8 -*-
"""Viết hoa chữ cái mở đầu mỗi dòng nằm sau một chỗ ngắt cứng kết câu.

Yêu cầu 03/09/2026, kèm ảnh `IMG_7248` (màn BACKLOG):

    Suzuno Kanna
    Mấy lời như lời nguyền đó...
    cứ bị rót vào tai suốt bấy lâu thì ai mà chẳng      <- chữ thường ở đầu dòng
    phát điên cơ chứ.

Ô đó là `sID 92 text[144]`, trong dữ liệu có `\\n` cứng ngay sau `...`, mirror theo
bản Nhật (`「あんな呪いの言葉みたいの……\\n　ずっと傍で言われてたら…」`). Ô ngay phía trên
trong cùng ảnh (`sID 92 text[143]`, Munakata Kai) **không có ngắt nào trong dữ liệu** —
`anh như mọi khi thôi.` là TMP tự wrap — nên chỗ ấy không tool nào với tới được. Đó là
lý do luật ở đây gắn vào **ngắt cứng**, không phải vào "dòng hiển thị".

## Quy ước sẵn có trong build

Đo trên `ScenarioData.text[]` (bỏ script test sID 0–12, bỏ câu còn kana):

    7.390 chỗ ngắt cứng
    6.860 chỗ dòng sau đã viết HOA  <- quy ước sẵn có, ngắt ở cuối câu
      526 chỗ dòng sau là chữ thường:
            426  ngay sau `...`   <- tool này sửa
             54  sau dấu phẩy      \\
             41  giữa cụm từ        > không đụng (viết hoa ở đây chắc chắn sai)
              5  sau `―`, `;`, `"` /
              1  sau dấu chấm thật <- tool này sửa

Tức 93% chỗ ngắt đã viết hoa sẵn; 427 chỗ tool này sửa là phần còn thiếu của chính
quy ước ấy.

## Luật (chủ sở hữu chốt 03/09/2026: luật phẳng, không trừ liên từ)

Ngắt được xét khi vế trái kết thúc bằng **dấu kết câu**: một chuỗi ≥2 dấu chấm (hoặc
`…`), hoặc một `.` / `!` / `?` đơn. Ngắt sau dấu phẩy, sau `―`, sau `;` hay giữa cụm
từ **không** được xét — ở đó câu chưa dứt, viết hoa là lỗi chính tả chứ không phải
lựa chọn phong cách. Mấy chỗ ấy là việc của `fix_midphrase_break.py`.

Đã hỏi và đã chốt: 120 trong 426 dòng mở đầu bằng liên từ (`nhưng` 74, `và`, `thì`,
`dù`…) **vẫn viết hoa**, chấp nhận dạng

    (Dù biết là thế giới game...
     Nhưng mình cũng chẳng có cảm giác chân thực gì cả.)

Không tự ý lọc lại danh sách liên từ: phương án "trừ liên từ ra" đã được đưa ra và bị
loại, và nó cũng **không sửa được đúng ô trong ảnh** — `cứ` nằm trong danh sách ấy.

## Ký tự đầu dòng không phải lúc nào cũng là chữ cái

Phải bóc đúng thứ engine vẽ ra trước khi hỏi "chữ này có thường không":

- `「』（(“"` mở ngoặc — bỏ qua, viết hoa chữ ngay sau nó.
- `[主人公]` — token tên người chơi, runtime thay bằng tên riêng nên đã hoa sẵn:
  **bỏ qua cả chỗ ngắt đó**. Đây là nguồn dương tính giả lớn nhất: đếm thô mà bóc
  hết `[...]` thì 10 trong 11 chỗ "sau dấu chấm mà viết thường" là giả.
- `[dic no=N text=X]` — chỉ `X` là chữ hiển thị, viết hoa bên trong tag, `N` là khoá
  tra cứu và không được đụng tới (xem `apply_sheet_cells.py`).
- `[gốc'ruby]` — cả hai nửa đều là chữ hiển thị; viết hoa nửa **gốc**.
- tag khác (`[command …]`) — bỏ qua chỗ ngắt, không đoán.
- dòng mở đầu bằng URL (`https://…`) — bỏ qua; 2 chỗ, đều là tin nhắn chat.

## Không đụng tới

- Câu còn kana — bản Nhật chưa dịch, viết hoa vô nghĩa.
- Script test của nhà phát triển, sID 0–12 (xem `CLAUDE.md`, mục "The translation
  source"): không màn nào tới được.
- `scriptText_Line`, `loadLine`, `selLine` — cặp chỉ mục của script gốc.
- `selText[]` được quét nhưng **không có chỗ nào** dính luật (đo 03/09/2026).
- `resources.assets`, `scenario_aoc01`, `scenario_aoc02`: 0 chỗ.

Bong bóng chat trong `json` (`GenebarkChatMainData.content`, 31 ô / 29 chuỗi) cũng đúng
dạng này và làm bằng `--json`. **Chỉ bảng đó**, xem `JSON_ALLOW` — mọi bảng khác trong
bundle ngắt dòng theo bố cục chứ không theo câu.

## Chạy lại sau mỗi vòng merge sheet

Sheet lưu mỗi ô thành một dòng phẳng và `apply_sheet_cells.py` lấy **chữ từ sheet**,
nên một vòng merge có thể trả chữ hoa về lại chữ thường. Tool này idempotent và có
`--check` (exit 1 nếu còn sót), nên nó thuộc nhóm chốt sau merge cùng
`fix_adv_wrap.py` / `fix_novel_list_wrap.py` / `fix_dictionary_wrap.py` /
`fix_ellipsis_break.py`.

Cách chạy:

    python tools\\fix_line_start_case.py            # chạy thử, không ghi
    python tools\\fix_line_start_case.py --apply
    python tools\\fix_line_start_case.py --check    # chốt sau merge, lỗi -> exit 1
    python tools\\fix_line_start_case.py --json     # gộp cả bong bóng chat
"""
import io
import json
import os
import re
import shutil
import sys

if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402

SCENARIO = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
JSONB = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")

# Trong `json` chỉ bong bóng chat là chữ chảy tự do. Mọi bảng khác ngắt dòng theo
# BỐ CỤC chứ không theo câu, nên luật ở đây sai hẳn ở đó — quét cả bundle thì trúng
# ngay `ChapterData.list[0].items[5].synopsis.jp`, mà `\n` của tóm tắt chương là chỗ
# gói cứng ở 18 ký tự (`check_chapterdata.py`), rơi đúng sau `...` chỉ là trùng hợp.
# Cùng lớp: `TerminalRuleData.rule_body` / `DictionaryData` phân trang theo `\n`
# (`BuildNoteLines`) và được `fix_dictionary_wrap.py` gói theo bề rộng 586 px.
# `GenebarkChatMainData` là bảng chat duy nhất có nội dung; ba bảng `GenebarkChat*`
# còn lại chỉ là ánh xạ id/nhóm/người nói.
JSON_ALLOW = {"GenebarkChatMainData"}
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv
WITH_JSON = "--json" in sys.argv

KANA = re.compile(r"[ぁ-ゖァ-ヺ]")
SENT_END = re.compile(r"(?:\.{2,}|…+|[.!?])$")
OPENERS = " 　「『“‘\"'(（〈―—"
URL = re.compile(r"\s*https?://")
DIC = re.compile(r"\[dic no=(\d+) text=([^\]]*)\]")
RUBY = re.compile(r"\[([^\]'\[]*)'([^\]\[]*)\]")
PLAYER = "[主人公]"


def capitalise_line(line):
    """Viết hoa chữ cái hiển thị đầu tiên của `line`, hoặc None nếu không phải việc.

    None có nghĩa "bỏ qua chỗ ngắt này" — đã hoa sẵn, không có chữ cái nào, hoặc
    mở đầu bằng thứ tool không được phép đoán (token tên người chơi, tag lạ, URL).
    """
    if URL.match(line):
        return None
    i = 0
    while i < len(line) and line[i] in OPENERS:
        i += 1
    rest = line[i:]
    if rest.startswith(PLAYER):          # runtime thay bằng tên riêng -> đã hoa
        return None
    m = DIC.match(rest)
    if m:
        inner = m.group(2)
        j = 0
        while j < len(inner) and inner[j] in OPENERS:
            j += 1
        if j >= len(inner) or not inner[j].isalpha() or not inner[j].islower():
            return None
        inner = inner[:j] + inner[j].upper() + inner[j + 1:]
        return line[:i] + "[dic no=%s text=%s]" % (m.group(1), inner) + rest[m.end():]
    m = RUBY.match(rest)
    if m:
        base = m.group(1)
        j = 0
        while j < len(base) and base[j] in OPENERS:
            j += 1
        if j >= len(base) or not base[j].isalpha() or not base[j].islower():
            return None
        newbase = base[:j] + base[j].upper() + base[j + 1:]
        return line[:i] + "[" + newbase + "'" + m.group(2) + "]" + rest[m.end():]
    if rest.startswith("["):             # tag khác — không đoán
        return None
    if not rest or not rest[0].isalpha() or not rest[0].islower():
        return None
    return line[:i] + rest[0].upper() + rest[1:]


def fix(text):
    """Trả về chuỗi đã sửa (hoặc chính nó nếu không có gì để sửa)."""
    if not text or "\n" not in text or KANA.search(text):
        return text
    parts = text.split("\n")
    out = [parts[0]]
    for k in range(1, len(parts)):
        left, right = parts[k - 1].rstrip(), parts[k]
        new = None
        if left and right.strip() and SENT_END.search(left):
            new = capitalise_line(right)
        out.append(new if new is not None else right)
    return "\n".join(out)


def load(path):
    env = UnityPy.load(path)
    hits = []
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        raw = d.m_Script
        if not isinstance(raw, str):
            raw = bytes(raw).decode("utf-8")
        hits.append((d, raw))
    return env, hits


def scenario_plan(raw):
    """{chuỗi cũ: chuỗi mới} + danh sách ô để in ra và để kiểm tra lại."""
    data = json.loads(raw.lstrip("﻿"))
    plan, cells = {}, []
    for ti, t in enumerate(data["target"]):
        sid = t["scenarioID"]
        if sid <= 12:
            continue
        names = t.get("talkName") or []
        for fld in ("text", "selText"):
            for j, s in enumerate(t.get(fld) or []):
                new = fix(s)
                if new == s:
                    continue
                plan[s] = new
                cells.append((ti, sid, fld, j, names[j] if fld == "text" and j < len(names) else "", s, new))
    return data, plan, cells


def mirror(script, old, new):
    lines, ol, nl = script.split("\n"), old.split("\n"), new.split("\n")
    hits = [k for k in range(len(lines) - len(ol) + 1) if lines[k:k + len(ol)] == ol]
    if len(hits) != 1:
        return None
    lines[hits[0]:hits[0] + len(ol)] = nl
    return "\n".join(lines)


def show(cells, n=8):
    for ti, sid, fld, j, name, old, new in cells[:n]:
        ol, nl = old.split("\n"), new.split("\n")
        k = next(i for i in range(len(ol)) if ol[i] != nl[i])
        print("  sID=%-4s %s[%-5d] %s" % (sid, fld, j, name))
        print("       %s" % ol[k - 1][-58:])
        print("     - %s" % ol[k][:64])
        print("     + %s" % nl[k][:64])


def do_scenario():
    env, hits = load(SCENARIO)
    d, raw = next((d, r) for d, r in hits if d.m_Name == "ScenarioData")
    bom = "﻿" if raw.startswith("﻿") else ""
    data, plan, cells = scenario_plan(raw)

    print("scenario01: %d ô cần viết hoa đầu dòng (%d chuỗi phân biệt)"
          % (len(cells), len(plan)))
    if cells:
        show(cells)
    if CHECK:
        if cells:
            print("\nchạy `python tools\\fix_line_start_case.py --apply`")
            raise SystemExit(1)
        print("PASS không dòng nào sau dấu kết câu còn mở đầu bằng chữ thường")
        return
    if not cells:
        return

    out = raw
    for old, new in plan.items():
        oj, nj = json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False)
        n = out.count(oj)
        if n == 0:
            raise SystemExit("không tìm thấy chuỗi trong JSON thô: %r" % old[:60])
        out = out.replace(oj, nj)

    # mirror sang scriptText (bản sao thứ hai, không widget nào đánh chỉ mục nhưng
    # quy ước của repo là mọi sửa đổi phải vào cả hai — xem CLAUDE.md)
    by_target = {}
    for ti, sid, fld, j, name, old, new in cells:
        by_target.setdefault(ti, []).append((old, new))
    mirrored = failed = 0
    for ti, pairs in by_target.items():
        script = cur = data["target"][ti]["scriptText"]
        for old, new in pairs:
            nxt = mirror(cur, old, new)
            if nxt is None:
                failed += 1
            else:
                cur, mirrored = nxt, mirrored + 1
        if cur != script:
            oj, nj = json.dumps(script, ensure_ascii=False), json.dumps(cur, ensure_ascii=False)
            if out.count(oj) != 1:
                raise SystemExit("scriptText target[%d] khớp %d lần" % (ti, out.count(oj)))
            out = out.replace(oj, nj)
    print("mirror vào scriptText: %d (không khớp verbatim: %d)" % (mirrored, failed))

    after = json.loads(out.lstrip("﻿"))
    changed = 0
    for ti, t in enumerate(data["target"]):
        ta = after["target"][ti]
        assert ta["scriptText_Line"] == t["scriptText_Line"], "scriptText_Line đổi"
        assert ta["loadLine"] == t["loadLine"], "loadLine đổi"
        assert ta.get("selLine") == t.get("selLine"), "selLine đổi"
        for fld in ("text", "selText"):
            a, b = ta.get(fld) or [], t.get(fld) or []
            assert len(a) == len(b), "%s đổi độ dài" % fld
            for j in range(len(b)):
                if a[j] == b[j]:
                    continue
                changed += 1
                assert plan.get(b[j]) == a[j], "ô đổi ngoài dự kiến: %s[%d]" % (fld, j)
                assert a[j].lower() == b[j].lower(), "đổi hơn cả hoa/thường"
                assert a[j].count("\n") == b[j].count("\n"), "đổi số dòng"
    print("kiểm tra: %d ô đổi, chỉ khác hoa/thường, loadLine/scriptText_Line nguyên vẹn"
          % changed)
    for t in after["target"]:
        if t["scenarioID"] <= 12:
            continue
        for fld in ("text", "selText"):
            for s in t.get(fld) or []:
                assert fix(s) == s, "chạy lại vẫn còn việc — không idempotent"
    print("kiểm tra: chạy lại lần hai không còn chỗ nào (idempotent)")

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return
    backup = os.path.join(ROOT, "_backup", "scenario01.prelinecase")
    if not os.path.exists(backup):
        shutil.copy2(SCENARIO, backup)
        print("backup ->", backup)
    d.m_Script = bom + out.lstrip("﻿")
    d.save()
    with open(SCENARIO, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi", SCENARIO, os.path.getsize(SCENARIO))

    _, hits2 = load(SCENARIO)
    back = next(r for dd, r in hits2 if dd.m_Name == "ScenarioData")
    rd = json.loads(back.lstrip("﻿"))
    for ti, sid, fld, j, name, old, new in cells:
        assert rd["target"][ti][fld][j] == new, "đọc lại sID=%s %s[%d]" % (sid, fld, j)
    for ti, t in enumerate(data["target"]):
        assert rd["target"][ti]["loadLine"] == t["loadLine"]
        assert rd["target"][ti]["scriptText_Line"] == t["scriptText_Line"]
    print("  đọc lại: %d ô khớp, loadLine/scriptText_Line nguyên vẹn" % len(cells))


def walk(node, path, sink):
    if isinstance(node, str):
        new = fix(node)
        if new != node:
            sink.append((path, node, new))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, "%s[%d]" % (path, i), sink)
    elif isinstance(node, dict):
        for k, v in node.items():
            walk(v, "%s.%s" % (path, k), sink)


def do_json():
    env, hits = load(JSONB)
    total, edits = 0, []
    for d, raw in hits:
        if d.m_Name not in JSON_ALLOW:
            continue
        body = raw.lstrip("﻿")
        if not body.lstrip().startswith("{"):
            continue
        try:
            obj = json.loads(body)
        except ValueError:
            continue
        sink, seen = [], set()
        walk(obj, d.m_Name, sink)
        # cùng một chuỗi có thể nằm ở nhiều ô; `str.replace` đổi hết trong một lần
        # nên lượt thứ hai sẽ không tìm thấy nó nữa và tưởng là hỏng
        sink = [x for x in sink if not (x[1] in seen or seen.add(x[1]))]
        if sink:
            edits.append((d, raw, sink))
            total += len(sink)
    print("\njson: %d chuỗi cần viết hoa đầu dòng" % total)
    for d, raw, sink in edits:
        print("  %s: %d" % (d.m_Name, len(sink)))
        for path, old, new in sink[:3]:
            k = next(i for i, (a, b) in enumerate(zip(old.split("\n"), new.split("\n"))) if a != b)
            print("     %s" % path)
            print("     - %s" % old.split("\n")[k][:64])
            print("     + %s" % new.split("\n")[k][:64])
    if CHECK:
        if total:
            raise SystemExit(1)
        return
    if not total:
        return
    for d, raw, sink in edits:
        bom = "﻿" if raw.startswith("﻿") else ""
        out = raw
        for path, old, new in sink:
            oj, nj = json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False)
            if out.count(oj) == 0:
                raise SystemExit("không thấy %r trong %s" % (old[:50], d.m_Name))
            out = out.replace(oj, nj)
        again = []
        walk(json.loads(out.lstrip("﻿")), d.m_Name, again)
        assert not again, "chạy lại vẫn còn việc trong %s" % d.m_Name
        if APPLY:
            d.m_Script = bom + out.lstrip("﻿")
            d.save()
    if not APPLY:
        print("CHẠY THỬ — thêm --apply để ghi")
        return
    backup = os.path.join(ROOT, "_backup", "json.prelinecase")
    if not os.path.exists(backup):
        shutil.copy2(JSONB, backup)
        print("backup ->", backup)
    with open(JSONB, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi", JSONB, os.path.getsize(JSONB))


def main():
    do_scenario()
    if WITH_JSON:
        do_json()


if __name__ == "__main__":
    main()
