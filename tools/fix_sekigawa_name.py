# -*- coding: utf-8 -*-
"""赤川夏音 = **Sekigawa Kanon** — sửa họ sai và ba cách viết tên riêng.

Nguồn duy nhất là chú thích của chính người viết game:

    00_04, dòng 9019:   ;//読み：赤川夏音（せきがわ かのん）

赤 đọc **せき** chứ không phải あか — đó là lý do chú thích tồn tại. Build đang sai
100%: `Sekigawa` xuất hiện **0 lần**, và tên riêng có ba cách viết (`Kanon`, `Kano`,
`Kanane`) trong khi 夏音 = かのん = **Kanon**. Xem memory `unlogical-official-romanisation`.

Đã đối chiếu từng ô với bản Nhật (79 ô text/talkName): khớp 1:1, không ô nào tên bị
chèn vào chỗ bản Nhật không có, không ô nào bị rơi. Cả game chỉ có **một** người họ
赤川 — luôn đi với 夏音 hoặc さん — nên không có thân nhân nào để lẫn.

## Vì sao KHÔNG thay trên raw JSON

`\\bKano\\b` chạy trên raw bỏ sót **2 chỗ**: `Kano` đứng ngay sau một ngắt dòng cứng
thì raw là `\\nKano`, chữ `n` của escape là ký tự từ nên ranh giới `\\b` biến mất
(sID 106 `scriptText`, hai chỗ). Nên tool sửa trên **dữ liệu đã parse** rồi ghi lại
bằng cách thay giá trị đã mã hoá — đúng lối `apply_sheet_cells.py` dùng.

Đã đo: mảng `text[]` của cả 6 target cần sửa (70, 72, 106, 107, 108, 115) mã hoá lại
khớp **đúng 1 lần** trong raw. Bốn target khớp != 1 lần (sID 3/4/5/12) là mảng rỗng/nhỏ
và **không** chứa tên.

## Những chỗ được sửa, và một chỗ tưởng là cấm

| chỗ | vì sao |
|---|---|
| `ScenarioData.text[]` | thoại được vẽ |
| `ScenarioData.talkName[]` | dạng `【参加者の女性Ｅ/Akagawa Kanon】` — chỉ nửa PHẢI được vẽ, nửa trái là khoá sprite/voice, giữ nguyên |
| `ScenarioData.scriptText` | bản sao không được vẽ, sửa để hai bản khỏi lệch thêm |
| `ScenarioData.scriptText_Line` sID 70 dòng 2722 | **có** sửa — xem dưới |
| script chương `00_02` dòng 2723 | cùng dòng `[terinfo]` đó |
| `json`: GenebarkChatMainData, TerminalHomeAlertData, GenebarkNoteData, ChapterData | 11 lần |

`scriptText_Line` vốn là chỗ "không được đụng" vì `loadLine[j]` index vào nó. Nhưng
luật đó là về **số dòng**, và dòng 2722 chỉ đổi ký tự bên trong `[terinfo text="…"]`
nên số dòng không đổi — tool assert lại điều đó sau khi ghi. Dòng này cũng đã được
dịch sẵn từ một pass trước, không còn tiếng Nhật để giữ.

## Chốt chặn

- Không sửa gì trong `[...]` **trừ** `[terinfo …]` (chỉ có `text=` là chữ hiển thị).
  Mọi tag khác đổi là dừng.
- Thay chuỗi DÀI trước chuỗi ngắn, không thì `Akagawa` ăn trước và `Akagawa Kano`
  thành `Sekigawa Kano`.
- Sau khi ghi: đọc lại từ disk, đòi **0** lần `Akagawa`/`Kano`/`Kanane` còn lại, số
  dòng `scriptText_Line` không đổi, độ dài mọi mảng không đổi.

    python tools\\fix_sekigawa_name.py [--apply] [--report]

`--report` xuất danh sách ô sheet cần sửa upstream ra .xlsx (sheet là bản gốc; chỉ
sửa build thì mọi vòng merge sau sẽ báo "cả hai bên đổi" ở những ô đó mãi).
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

SCENARIO = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
JSONB = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
SHEET = r"D:\Downloads\UNLOGICAL_v2 (42).xlsx"
REPORT_OUT = r"D:\Downloads\Sekigawa_sheet_todo.xlsx"

APPLY = "--apply" in sys.argv
REPORT = "--report" in sys.argv

# DÀI trước NGẮN.  (regex, thay bằng)
RULES = [
    (r"Akagawa\s+Kanane", "Sekigawa Kanon"),
    (r"Akagawa\s+Kanon",  "Sekigawa Kanon"),
    (r"Akagawa\s+Kano\b", "Sekigawa Kanon"),
    (r"Akagawa",          "Sekigawa"),
    (r"\bKanane\b",       "Kanon"),
    (r"\bKano\b",         "Kanon"),
]
OLD = re.compile(r"Akagawa|\bKanane\b|\bKano\b")
TAG = re.compile(r"\[[^\[\]\n]*\]")
JSON_ASSETS = ("GenebarkChatMainData", "TerminalHomeAlertData",
               "GenebarkNoteData", "ChapterData")


def fix(s):
    out = s
    for pat, rep in RULES:
        out = re.sub(pat, rep, out)
    return out


def tag_guard(old, new, where):
    """Tag chỉ được đổi nếu là `[terinfo …]`."""
    a, b = TAG.findall(old), TAG.findall(new)
    if len(a) != len(b):
        raise SystemExit("%s: số tag đổi %d -> %d" % (where, len(a), len(b)))
    for x, y in zip(a, b):
        if x != y and not x.startswith("[terinfo"):
            raise SystemExit("%s: tag đổi mà không phải terinfo:\n  %r\n  %r"
                             % (where, x, y))


def load_text(path, name):
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


def all_texts(path):
    env = UnityPy.load(path)
    out = {}
    for o in env.objects:
        if o.type.name == "TextAsset":
            d = o.read()
            raw = d.m_Script
            if not isinstance(raw, str):
                raw = bytes(raw).decode("utf-8")
            out[d.m_Name] = raw
    return out


def enc_arr(x):
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))


def enc_str(x):
    return json.dumps(x, ensure_ascii=False)


def do_scenario():
    env, d, raw = load_text(SCENARIO, "ScenarioData")
    data = json.loads(raw.lstrip("\ufeff"))
    out, hits = raw, []

    for e in data["target"]:
        sid = e["scenarioID"]
        for fld in ("text", "talkName", "selText", "scriptText_Line"):
            arr = e.get(fld)
            if not isinstance(arr, list):
                continue
            new = list(arr)
            n = 0
            for j, s in enumerate(arr):
                if isinstance(s, str) and OLD.search(s):
                    v = fix(s)
                    tag_guard(s, v, "%s/%s/%d" % (sid, fld, j))
                    new[j] = v
                    n += 1
                    hits.append((sid, fld, j))
            if not n:
                continue
            oj, nj = enc_arr(arr), enc_arr(new)
            c = out.count(oj)
            if c != 1:
                raise SystemExit("sID %s %s: mảng mã hoá khớp %d lần" % (sid, fld, c))
            out = out.replace(oj, nj)
            print("-> sID %-4s %-18s %d ô" % (sid, fld, n))

        st = e.get("scriptText")
        if isinstance(st, str) and OLD.search(st):
            v = fix(st)
            tag_guard(st, v, "%s/scriptText" % sid)
            oj, nj = enc_str(st), enc_str(v)
            c = out.count(oj)
            if c != 1:
                raise SystemExit("sID %s scriptText: khớp %d lần" % (sid, c))
            out = out.replace(oj, nj)
            print("-> sID %-4s %-18s %d lần" % (sid, "scriptText", len(OLD.findall(st))))
    return env, d, raw, out, hits


def do_plain(path, names):
    """Script chương — text thuần cú pháp game, soát tag theo từng DÒNG."""
    env = UnityPy.load(path)
    edits = []
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        if d.m_Name not in names:
            continue
        raw = d.m_Script
        if not isinstance(raw, str):
            raw = bytes(raw).decode("utf-8")
        if not OLD.search(raw):
            continue
        new = raw
        for line in set(l for l in raw.split("\n") if OLD.search(l)):
            v = fix(line)
            tag_guard(line, v, "%s: %r" % (d.m_Name, line[:60]))
            new = new.replace(line, v)
        if new != raw:
            edits.append((d, raw, new, len(OLD.findall(raw))))
            print("-> %-26s %d lần" % (d.m_Name, len(OLD.findall(raw))))
    return env, edits


def walk_strings(node, out):
    """Gom mọi giá trị chuỗi cần sửa trong một cây JSON.

    KHÔNG soát tag theo dòng ở đây: asset json là một dòng duy nhất, cặp `[...]` của
    cú pháp JSON sẽ bị regex tag ăn và báo oan (TerminalHomeAlertData: cả mảng 86 mục
    nằm trên một dòng). Soát theo từng giá trị chuỗi mới đúng đơn vị.
    """
    if isinstance(node, dict):
        for k, v in node.items():
            walk_strings(v, out)
    elif isinstance(node, list):
        for v in node:
            walk_strings(v, out)
    elif isinstance(node, str) and OLD.search(node):
        out.add(node)


def do_json_assets(names):
    """Bundle json — sửa theo từng giá trị chuỗi, không theo dòng."""
    env = UnityPy.load(JSONB)
    edits = []
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        if d.m_Name not in names:
            continue
        raw = d.m_Script
        if not isinstance(raw, str):
            raw = bytes(raw).decode("utf-8")
        if not OLD.search(raw):
            continue
        found = set()
        walk_strings(json.loads(raw.lstrip("﻿")), found)
        new = raw
        for s in sorted(found, key=len, reverse=True):
            v = fix(s)
            tag_guard(s, v, "%s: %r" % (d.m_Name, s[:60]))
            oj, nj = enc_str(s), enc_str(v)
            c = new.count(oj)
            if not c:
                raise SystemExit("%s: không thấy chuỗi đã mã hoá %r" % (d.m_Name, oj[:70]))
            # Thay HẾT: cùng một câu xuất hiện nhiều lần là hợp lệ (GenebarkChatMainData
            # có cùng tin nhắn ở groupIDs 53 và 54), và bản thay là như nhau.
            new = new.replace(oj, nj)
        if new != raw:
            edits.append((d, raw, new, len(OLD.findall(raw))))
            print("-> %-26s %d lần, %d chuỗi" % (d.m_Name, len(OLD.findall(raw)), len(found)))
    return env, edits


def do_report():
    from openpyxl import load_workbook, Workbook
    from openpyxl.styles import Font, Alignment
    print("\n== ô sheet cần sửa upstream ==")
    wb = load_workbook(SHEET, read_only=True, data_only=True)
    rows = []
    for ws in wb.worksheets:
        vcol = 3 if ws.title.startswith("sd_") else 2
        for r in ws.iter_rows(values_only=True):
            if not r or not isinstance(r[0], str):
                continue
            v = r[vcol] if len(r) > vcol and isinstance(r[vcol], str) else ""
            if not OLD.search(v):
                continue
            rows.append((ws.title, r[0].strip(), v, fix(v)))
    wb.close()
    ob = Workbook()
    o = ob.active
    o.title = "sekigawa"
    o.append(["tab", "ID", "đang là", "sửa thành"])
    for c in o[1]:
        c.font = Font(bold=True)
    for x in rows:
        o.append(list(x))
    for col, w in (("A", 16), ("B", 22), ("C", 62), ("D", 62)):
        o.column_dimensions[col].width = w
    for row in o.iter_rows(min_row=2, min_col=3, max_col=4):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    o.freeze_panes = "A2"
    ob.save(REPORT_OUT)
    print("%d ô, đã ghi %s" % (len(rows), REPORT_OUT))
    for t, i, a, b in rows[:6]:
        print("   [%s] %s\n      - %s\n      + %s" % (t, i, a[:86], b[:86]))
    if len(rows) > 6:
        print("   … còn %d ô nữa trong file" % (len(rows) - 6))


def verify(raw_before):
    print("\n== đọc lại từ disk ==")
    before = json.loads(raw_before.lstrip("\ufeff"))
    sc = all_texts(SCENARIO)
    js = all_texts(JSONB)
    bad = 0
    for lab, blob in list(sc.items()) + list(js.items()):
        left = OLD.findall(blob)
        if left:
            bad += len(left)
            print("!! %s còn %d lần: %s" % (lab, len(left), set(left)))
    print("còn sót Akagawa/Kano/Kanane:", bad)
    d = json.loads(sc["ScenarioData"].lstrip("\ufeff"))
    B = {e["scenarioID"]: e for e in before["target"]}
    for e in d["target"]:
        b = B[e["scenarioID"]]
        for fld in ("text", "talkName", "selText", "scriptText_Line",
                    "loadLine", "selLine"):
            x, y = e.get(fld), b.get(fld)
            if isinstance(y, list) and len(x) != len(y):
                raise SystemExit("sID %s %s: độ dài mảng %d -> %d"
                                 % (e["scenarioID"], fld, len(y), len(x)))
        if e.get("loadLine") != b.get("loadLine"):
            raise SystemExit("sID %s: loadLine bị đổi" % e["scenarioID"])
    print("độ dài mọi mảng + loadLine: không đổi")
    blobs = list(sc.values()) + list(js.values())
    print("Sekigawa: %d lần   Kanon: %d lần"
          % (sum(len(re.findall(r"Sekigawa", b)) for b in blobs),
             sum(len(re.findall(r"\bKanon\b", b)) for b in blobs)))
    if bad:
        raise SystemExit(1)


def main():
    print("== ScenarioData ==")
    env_s, d_s, raw_s, out_s, hits = do_scenario()
    print("\n== script chương ==")
    _, ed_c = do_plain(SCENARIO, {"00_02"})
    print("\n== bundle json ==")
    env_j, ed_j = do_json_assets(set(JSON_ASSETS))
    print("\ntổng: %d ô ScenarioData, %d script chương, %d asset json"
          % (len(hits), len(ed_c), len(ed_j)))

    if REPORT:
        do_report()
    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    bak = os.path.join(ROOT, "_backup", "scenario01.sekigawa")
    shutil.copy2(SCENARIO, bak)
    print("\nbackup ->", bak)
    d_s.m_Script = ("\ufeff" if raw_s.startswith("\ufeff") else "") + out_s.lstrip("\ufeff")
    d_s.save()
    with open(SCENARIO, "wb") as f:
        f.write(env_s.file.save(packer="lz4"))
    # Script chương phải mở LẠI bundle vừa ghi — dùng env cũ là đè mất ScenarioData.
    env_c, ed_c2 = do_plain(SCENARIO, {"00_02"})
    for d, old, new, n in ed_c2:
        d.m_Script = new
        d.save()
    if ed_c2:
        with open(SCENARIO, "wb") as f:
            f.write(env_c.file.save(packer="lz4"))
    print("đã ghi", SCENARIO, os.path.getsize(SCENARIO))

    if ed_j:
        bakj = os.path.join(ROOT, "_backup", "json.sekigawa")
        shutil.copy2(JSONB, bakj)
        print("backup ->", bakj)
        for d, old, new, n in ed_j:
            d.m_Script = new
            d.save()
        with open(JSONB, "wb") as f:
            f.write(env_j.file.save(packer="lz4"))
        print("đã ghi", JSONB, os.path.getsize(JSONB))

    verify(raw_s)


main()
