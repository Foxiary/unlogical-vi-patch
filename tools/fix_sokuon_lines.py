# -*- coding: utf-8 -*-
"""Đồng bộ bản sao `scriptText` của 3 dòng thoại còn sót ký tự `っ`.

Ba dòng này là chỗ người dịch giữ nguyên dấu nghẹn (sokuon) của tiếng Nhật —
`っ` cuối câu là tiếng hụt hơi, không phải chữ có nghĩa. **Sheet đã sửa cả ba
rồi** (bản xuất `UNLOGICAL_v2 (5).xlsx`, 16/08/2026 20:39: 0 ô tiếng Việt nào
còn `っ`/`ッ`), và `text[]` trong romfs **cũng đã merge xong** (scenario01 sửa
lúc 20:41). Còn sót lại đúng **bản sao trong `scriptText`**:

| id sheet      | entry | `text[]` (đã đúng) | `scriptText` (còn cũ)   |
|---------------|-------|--------------------|-------------------------|
| `89/txt/0047` | 30    | `「Kogasaki...!?」`  | `「Kogasaki? ―...っ!?」` |
| `95/txt/0579` | 36    | `「......」`         | `「...っ」`              |
| `125/txt/0133`| 66    | `「...Ờ.」`          | `「...っ, Ờ.」`          |

Sheet đổi nhiều hơn là chỉ bỏ `っ`: dòng 30 bỏ luôn `? ―`, dòng 66 bỏ dấu phẩy.
Lấy nguyên văn của `text[]`, không tự chỉnh thêm.

> **Mỗi dòng nằm ở HAI chỗ** — `text[]` và bản sao trong `scriptText` — và một
> pass chỉ sửa `text[]` sẽ để lại hai bản lệch nhau, không có kiểm tra thường
> ngày nào bắt được. Entry 36 còn lệch sẵn từ trước: `text[579]` 6 chấm còn
> `scriptText` 3 chấm. Đây là lý do script khai báo **chuỗi cũ theo đúng dạng
> trong `scriptText`**, không suy ra từ `text[]`.
>
> Ba dòng `「っ！？」` ở entry 3/4/5 **giữ nguyên**: đó là khối tiếng Nhật chưa
> dịch (96,8% số dòng của entry vẫn là kana/kanji), không phải chữ sót.

Thay thẳng trên văn bản JSON, đếm số lần khớp trước khi ghi, rồi parse lại và so
từng trường để chắc không có gì khác trôi theo.

    python tools\\fix_sokuon_lines.py            # chạy thử
    python tools\\fix_sokuon_lines.py --apply    # backup, vá, đóng gói lại

Backup: `_backup\\scenario01.presokuon`.
Chạy lại vô hại: dòng nào đã đúng thì đếm được 0 lần và bị bỏ qua.
"""
import io
import json
import os
import shutil
import sys

import UnityPy

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "scenario01.presokuon")

SOKUON = "っッ"

# (mô tả, chuỗi cũ, chuỗi mới) — biến thể dài đặt trước để không bị chuỗi ngắn
# nuốt mất (`「...っ」` là hậu tố của `「......っ」`).
PLAN = [
    ("89/txt/0047  entry 30",  "「Kogasaki? ―...っ!?」", "「Kogasaki...!?」"),
    ("95/txt/0579  entry 36",  "「......っ」",           "「......」"),
    ("95/txt/0579  entry 36",  "「...っ」",              "「......」"),
    ("125/txt/0133 entry 66",  "「...っ, Ờ.」",          "「...Ờ.」"),
]

# `text[]` phải khớp đúng cái ta ghi vào `scriptText` — nếu không, hai bản lại lệch.
EXPECT = {(30, 47): "「Kogasaki...!?」",
          (36, 579): "「......」",
          (66, 133): "「...Ờ.」"}

# Ba entry này là khối tiếng Nhật chưa dịch — `「っ！？」` ở đó là bản gốc, giữ nguyên.
UNTRANSLATED = {3, 4, 5}

APPLY = "--apply" in sys.argv


def enc(s):
    """Chuỗi như nó nằm trong văn bản JSON."""
    return json.dumps(s, ensure_ascii=False)[1:-1]


def main():
    env = UnityPy.load(BUNDLE)
    obj = next((o for o in env.objects
                if o.type.name == "TextAsset" and o.read().m_Name == "ScenarioData"), None)
    if obj is None:
        raise SystemExit("không thấy ScenarioData trong " + BUNDLE)
    d = obj.read()
    raw = d.m_Script
    before = json.loads(raw.lstrip("﻿"))

    for (i, j), want in EXPECT.items():
        got = before["target"][i]["text"][j]
        if got != want:
            raise SystemExit("entry %d text[%d] = %r, mong đợi %r — dừng, "
                             "kiểm lại xem sheet đã merge chưa" % (i, j, got, want))
    print("   text[] của 3 slot đã khớp sheet — chỉ còn đồng bộ scriptText\n")

    out, total = raw, 0
    for label, old, new in PLAN:
        n = out.count(enc(old))
        print("   %-34s %-24r x%d -> %r" % (label, old, n, new))
        if n:
            out = out.replace(enc(old), enc(new))
            total += n
    print("   tổng %d chỗ thay" % total)
    if not total:
        print("   không còn gì để sửa")
        return

    after = json.loads(out.lstrip("﻿"))
    a, b = before["target"], after["target"]
    assert len(a) == len(b), "số entry đổi"
    changed = 0
    for x, y in zip(a, b):
        assert x.keys() == y.keys()
        for k in x:
            if k in ("text", "scriptText"):
                continue
            assert x[k] == y[k], "đụng trường %s" % k
        assert len(x["text"]) == len(y["text"])
        for p, q in zip(x["text"], y["text"]):
            if p != q:
                assert any(p == o and q == nw for _, o, nw in PLAN), "text[] đổi ngoài kế hoạch: %r" % p
                changed += 1
    print("   kiểm tra: %d ô text[] đổi, đều nằm trong kế hoạch; mọi trường khác nguyên vẹn" % changed)

    # sau khi vá: `text[]` và bản sao `scriptText` phải trùng nhau từng ký tự
    for (i, j), want in EXPECT.items():
        assert b[i]["text"][j] == want, "entry %d text[%d] trôi mất" % (i, j)
        assert want in b[i]["scriptText"], "entry %d: scriptText chưa có %r" % (i, want)
    print("   3 slot: text[] và scriptText đã trùng nhau")

    # Chỉ tính là "sót" khi ký tự Nhật DUY NHẤT của dòng là っ/ッ. Lỏng hơn thế thì
    # 96 dòng `にっこり` (từ khoá biểu cảm sprite, tham số lệnh) sẽ báo nhầm.
    def only_sokuon(s):
        k = [c for c in s if '぀' <= c <= 'ヿ' or '一' <= c <= '鿿']
        return k and all(c in SOKUON for c in k)

    stray = [(i, s.strip())
             for i, e in enumerate(b) if i not in UNTRANSLATED
             for s in e["scriptText"].split("\n")
             if s.strip() and not s.lstrip().startswith("[") and only_sokuon(s)]
    print("   scriptText của entry đã dịch, ký tự Nhật duy nhất là っ/ッ: %d" % len(stray))
    for i, s in stray[:5]:
        print("      entry %d  %r" % (i, s))

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(BUNDLE, BACKUP)
        print("   backup -> %s" % BACKUP)
    d.m_Script = out
    d.save()
    blob = env.file.save(packer="lz4")
    with open(BUNDLE, "wb") as f:
        f.write(blob)
    print("   đã ghi %s (%s byte)" % (BUNDLE, format(len(blob), ",")))


main()
