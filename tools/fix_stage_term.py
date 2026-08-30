# -*- coding: utf-8 -*-
"""Thống nhất tên màn `Stage N` và cụm thông báo `Cập nhật quy tắc`.

Người dùng chốt 28/08/2026: **ưu tiên sheet**. Sheet viết `Cập nhật quy tắc: Stage 1`,
bản build viết `Cập nhật luật: Giai đoạn 1`. Nhưng "ưu tiên sheet" chỉ nói bên nào
thắng, không nói phạm vi — nên vẫn phải đếm chữ chính văn như luật của dự án
(xem memory `unlogical-loanword-terms`), và số đo dựng ra đúng cùng một câu trả lời:

```
chữ VẼ RA (ScenarioData.text[], 39 574 ô)
    'Stage <số/EX>'       307
    'Giai đoạn <số/EX>'     5      <- lạc lõng, sửa
bundle json (UI/hệ thống)
    'Stage <số>'           26
    'Giai đoạn <số>'        0
```

Hai chỗ **không** được đụng, đây mới là phần khó:

- `giai đoạn` viết thường (36 lần) là văn xuôi — "giai đoạn chuẩn bị", "giai đoạn
  này". Nên mẫu phải neo vào **chữ số hoặc `EX`** ngay sau, không neo vào từ.
- `luật` trên chữ vẽ ra 89 lần **gần như toàn là từ thường**: "luật chơi",
  "pháp luật", "kỷ luật", "quy luật", "đổi luật". Thay đại trà là hỏng. Chỉ đổi
  đúng cụm thông báo cố định `Cập nhật luật` / `Bổ sung luật`, và chỉ **bên trong
  `[terinfo text="…"]`**.

`[terinfo text=…]` là chữ HIỆN RA, không phải khoá tra cứu — nó đã được dịch sang
tiếng Việt từ các đợt trước, nên sửa tiếp là hợp lệ. Khác với khoá trong `[...]`
mà `CLAUDE.md` cấm đụng.

> **Sửa cả `scriptText` lẫn 143 script chương.** Cùng một câu nằm ở ba nơi; bỏ sót
> một nơi là lần đối chiếu sau lại thấy lệch.

    python tools\\fix_stage_term.py            # chạy thử
    python tools\\fix_stage_term.py --apply
    python tools\\fix_stage_term.py --check    # chốt sau merge, lỗi -> exit 1
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

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "scenario01.stageterm")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

# Neo vào chữ số / EX nên "giai đoạn chuẩn bị" không dính.
STAGE = re.compile(r"Giai đoạn(\s*)(\d|EX)")
# Chỉ áp bên trong [terinfo text=…]
TERINFO = re.compile(r"\[terinfo text=")
RULE = [("Cập nhật luật", "Cập nhật quy tắc"), ("Bổ sung luật", "Bổ sung quy tắc")]


def fix_terinfo(s):
    """Đổi cụm thông báo, chỉ trong giá trị của [terinfo text=…]."""
    out, pos = [], 0
    for m in TERINFO.finditer(s):
        end = s.find("]", m.end())
        if end < 0:
            continue
        val = s[m.end():end]
        for a, b in RULE:
            val = val.replace(a, b)
        out.append(s[pos:m.end()]); out.append(val)
        pos = end
    out.append(s[pos:])
    return "".join(out)


def fix(s):
    return STAGE.sub(lambda m: "Stage" + m.group(1) + m.group(2), fix_terinfo(s))


def load():
    env = UnityPy.load(BUNDLE)
    out = []
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        raw = d.m_Script
        raw = raw if isinstance(raw, str) else bytes(raw).decode("utf-8")
        out.append((d, raw))
    return env, out


def main():
    env, assets = load()
    plan = []
    for d, raw in assets:
        new = fix(raw)
        if new != raw:
            n_stage = len(STAGE.findall(raw))
            n_rule = sum(raw.count(a) for a, _ in RULE)
            plan.append((d, raw, new, n_stage, n_rule))

    tot_s = sum(p[3] for p in plan)
    tot_r = sum(p[4] for p in plan)
    print("asset đổi: %d   'Giai đoạn <số>' -> 'Stage <số>': %d   cụm thông báo: %d"
          % (len(plan), tot_s, tot_r))
    for d, raw, new, ns, nr in plan:
        print("   %-16s Stage %-3d  thông báo %-3d" % (d.m_Name, ns, nr))

    if CHECK:
        if plan:
            print("\nchạy `python tools\\fix_stage_term.py --apply`")
            raise SystemExit(1)
        print("PASS không còn chỗ nào")
        return
    if not plan:
        print("không có gì để sửa")
        return

    # Chốt: chữ chỉ được đổi đúng hai phép trên, không gì khác.
    for d, raw, new, _, _ in plan:
        back = new.replace("Stage ", "Giai đoạn ")
        for a, b in RULE:
            back = back.replace(b, a)
        chk = raw.replace("Stage ", "Giai đoạn ")
        for a, b in RULE:
            chk = chk.replace(b, a)
        if back != chk:
            raise SystemExit("%s: đổi ngoài dự kiến" % d.m_Name)
        if len(new) - len(raw) != (len("Stage") - len("Giai đoạn")) * len(STAGE.findall(raw)) \
                + sum((len(b) - len(a)) * 0 for a, b in RULE) + \
                sum((len(b) - len(a)) * (raw.count(a) - new.count(a)) for a, b in RULE):
            pass    # độ dài không phải chốt chắc; chốt thật là phép nghịch ở trên
    print("kiểm tra: phép đổi nghịch lại đúng bằng bản gốc trên mọi asset")

    sd_before = None
    for d, raw, _, _, _ in plan:
        if d.m_Name == "ScenarioData":
            sd_before = json.loads(raw.lstrip("﻿"))

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(BUNDLE, BACKUP)
        print("backup ->", BACKUP)
    for d, _raw, new, _, _ in plan:
        d.m_Script = new
        d.save()
    with open(BUNDLE, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi", BUNDLE, os.path.getsize(BUNDLE))

    _, after = load()
    got = {d.m_Name: raw for d, raw in after}
    for d, _raw, new, _, _ in plan:
        if got[d.m_Name] != new:
            raise SystemExit("đọc lại %s không khớp" % d.m_Name)
    if sd_before is not None:
        sd_after = json.loads(got["ScenarioData"].lstrip("﻿"))
        assert len(sd_before["target"]) == len(sd_after["target"])
        for a, b in zip(sd_before["target"], sd_after["target"]):
            assert a["loadLine"] == b["loadLine"], "loadLine đổi"
            # scriptText_Line chứa CHÍNH các dòng script, đổi chữ trong đó là ĐÚNG —
            # chỉ số dòng mới là bất biến.
            assert len(a["scriptText_Line"]) == len(b["scriptText_Line"]), (
                "số dòng scriptText_Line đổi")
            assert len(a["text"]) == len(b["text"])
        print("  ScenarioData: loadLine / scriptText_Line / số ô nguyên vẹn")
    print("  đọc lại: %d asset khớp" % len(plan))


if __name__ == "__main__":
    main()
