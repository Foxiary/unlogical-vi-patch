# -*- coding: utf-8 -*-
"""Sửa cách viết hoa/thường trong `SystemTextData` (`resources.assets`), vá byte tại chỗ.

Báo 04/09/2026 kèm ảnh `IMG_7250` (chụp máy Switch thật): hộp thông báo tím sau khi game
nhận ra DLC ghi `Downloadable Content has been downloaded.` — chủ sở hữu muốn `content`
viết thường.

`SystemTextData` là bảng chuỗi hệ thống, và ba mục 5/6/7 theo **luật ô JP** (xem CLAUDE.md):
bản gốc để tiếng Nhật ở JP, bản patch chép **nguyên văn tiếng Anh chính thức** của hãng sang
JP vì engine chỉ đọc ô JP. Nên chữ trên màn hình là chuỗi tiếng Anh, và sửa nó là sửa ô JP.

    id 5  `Content has not been unlocked.`            <- `Content` đứng ĐẦU CÂU, giữ hoa
    id 6  `Full game version required to unlock content.`   <- vốn đã thường
    id 7  `Downloadable Content \\nhas been downloaded.`     <- sửa ở đây

## Vì sao sửa tay được mà không sợ vòng merge nuốt mất

`apply_sheet_cells.py` chỉ ghi `scenario01` và bundle `json`; nó **không đụng**
`resources.assets` (grep: 0 chỗ). `SystemTextData` cũng không có tab nào trên sheet. Nên đây
là chỗ sheet không với tới được — cùng loại với `ScriptDialogData` của `fix_item_name_case.py`,
nhưng ngược lại về hệ quả: sửa tay ở đây là vĩnh viễn, không cần chốt sau merge.

## Vá byte tại chỗ, không đóng gói lại

Chuỗi mới **dài đúng bằng** chuỗi cũ (chỉ đổi hoa/thường), nên không cần cho UnityPy ghi lại
cả `resources.assets` 13,4 MB — vốn sẽ dồn lại mọi object ở mốc 8 byte và đổi hàng loạt offset
không liên quan. Thay vào đó tool sửa đúng vài byte:

1. lấy chuỗi JSON thô của TextAsset qua UnityPy, khẳng định nó xuất hiện **đúng 1 lần** trong file
2. trong chuỗi JSON, neo bằng `"JP": ` + `json.dumps(cũ)` — mẫu này khớp **đúng 1 lần**, khác với
   bản thân chuỗi cũ (2 lần: một ở ô JP, một ở ô EN, và ô EN thì **không được đụng**)
3. ghi đè đúng khoảng byte ấy

Kích thước file không đổi, không object nào dịch chỗ. Tool đọc lại bằng UnityPy để khẳng định
số mục không đổi, chỉ đúng ô JP của đúng id đó khác đi, EN/CN nguyên vẹn, và **mọi byte khác
của file giống hệt** bản trước khi ghi.

    python tools\\fix_system_text_case.py            # chạy thử
    python tools\\fix_system_text_case.py --apply
    python tools\\fix_system_text_case.py --check    # exit 1 nếu còn việc
"""
import io
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import UnityPy   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TARGET = os.path.join(ROOT, "romfs", "Data", "resources.assets")
BACKUP = os.path.join(ROOT, "_backup", "resources.assets.presystextcase")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

# (id, ô JP cũ, ô JP mới) — phải dài bằng nhau tính theo byte UTF-8
JOBS = [
    (7, "Downloadable Content \nhas been downloaded.",
        "Downloadable content \nhas been downloaded."),
]


def system_text(path):
    """(TextAsset, chuỗi JSON thô) của `SystemTextData`."""
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        if d.m_Name != "SystemTextData":
            continue
        raw = d.m_Script
        if not isinstance(raw, str):
            raw = bytes(raw).decode("utf-8")
        return d, raw
    raise SystemExit("không thấy SystemTextData trong " + path)


def entry(data, eid):
    hit = [e for e in data["entries"] if e["id"] == eid]
    if len(hit) != 1:
        raise SystemExit("id %s xuất hiện %d lần" % (eid, len(hit)))
    return hit[0]


def plan(raw):
    """[(id, cũ, mới, neo)] cho những việc còn phải làm."""
    data = json.loads(raw.lstrip("﻿"))
    todo = []
    for eid, old, new in JOBS:
        e = entry(data, eid)
        cur = e["data"]["JP"]
        if cur == new:
            continue
        if cur != old:
            raise SystemExit("id %s: ô JP đang là %r, không khớp chuỗi cũ đã khai" % (eid, cur))
        if len(old.encode("utf-8")) != len(new.encode("utf-8")):
            raise SystemExit("id %s: chuỗi mới khác độ dài, không vá tại chỗ được" % eid)
        anchor = '"JP": ' + json.dumps(old, ensure_ascii=False)
        if raw.count(anchor) != 1:
            raise SystemExit("id %s: neo khớp %d lần, phải đúng 1" % (eid, raw.count(anchor)))
        todo.append((eid, old, new, anchor))
    return data, todo


def main():
    d, raw = system_text(TARGET)
    data, todo = plan(raw)
    print("%s — SystemTextData %d mục" % (os.path.basename(TARGET), len(data["entries"])))
    for eid, old, new, _a in todo:
        print("  id %-3s %r" % (eid, old))
        print("      -> %r" % new)
    if CHECK:
        if todo:
            print("\nchạy `python tools\\fix_system_text_case.py --apply`")
            raise SystemExit(1)
        print("PASS mọi mục đã đúng cách viết")
        return
    if not todo:
        print("không có gì để sửa")
        return

    before = open(TARGET, "rb").read()
    blob = raw.encode("utf-8")
    if before.count(blob) != 1:
        raise SystemExit("chuỗi JSON xuất hiện %d lần trong file" % before.count(blob))
    base = before.index(blob)
    out = bytearray(before)
    spans = []
    for eid, old, new, anchor in todo:
        # Trong file, chuỗi nằm ở dạng ĐÃ ESCAPE của JSON: xuống dòng là hai ký tự `\` `n`
        # chứ không phải 0x0A. So byte bằng chính chuỗi Python là hụt mất 1 byte mỗi dòng.
        old_lit = json.dumps(old, ensure_ascii=False)[1:-1].encode("utf-8")
        new_lit = json.dumps(new, ensure_ascii=False)[1:-1].encode("utf-8")
        if len(old_lit) != len(new_lit):
            raise SystemExit("id %s: dạng escape khác độ dài" % eid)
        # `raw.index` đếm KÝ TỰ, còn file thì tính BYTE — trước chỗ này có đầy chữ Nhật/Hoa
        # nhiều byte, nên phải quy đổi qua UTF-8 chứ không cộng thẳng chỉ số ký tự
        off = base + len(raw[:raw.index(anchor)].encode("utf-8")) + len('"JP": "')
        n = len(old_lit)
        if bytes(out[off:off + n]) != old_lit:
            raise SystemExit("id %s: byte tại %d là %r, không phải chuỗi cũ"
                             % (eid, off, bytes(out[off:off + n])))
        out[off:off + n] = new_lit
        spans.append((off, off + n))
    out = bytes(out)
    if len(out) != len(before):
        raise SystemExit("kích thước file đổi")
    diff = [i for i in range(len(out)) if out[i] != before[i]]
    outside = [i for i in diff if not any(a <= i < b for a, b in spans)]
    print("byte đổi: %d, đều nằm trong %d khoảng đã khai (ngoài khoảng: %d)"
          % (len(diff), len(spans), len(outside)))
    if outside:
        raise SystemExit("có byte đổi ngoài khoảng dự kiến")

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return
    os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
    if not os.path.exists(BACKUP):
        shutil.copy2(TARGET, BACKUP)
        print("backup ->", BACKUP)
    with open(TARGET, "wb") as f:
        f.write(out)
    print("đã ghi %s (%d B, không đổi cỡ)" % (TARGET, len(out)))

    _d2, raw2 = system_text(TARGET)
    after = json.loads(raw2.lstrip("﻿"))
    assert len(after["entries"]) == len(data["entries"]), "số mục đổi"
    want = {eid: new for eid, _o, new, _a in todo}
    for e0, e1 in zip(data["entries"], after["entries"]):
        assert e0["id"] == e1["id"], "id đổi"
        for slot in ("EN", "CN"):
            assert e0["data"][slot] == e1["data"][slot], "ô %s của id %s đổi" % (slot, e0["id"])
        exp = want.get(e0["id"], e0["data"]["JP"])
        assert e1["data"]["JP"] == exp, "ô JP của id %s không như dự kiến" % e0["id"]
    print("  đọc lại: %d mục nguyên vẹn, chỉ %d ô JP đổi, EN/CN không đụng"
          % (len(after["entries"]), len(todo)))


if __name__ == "__main__":
    main()
