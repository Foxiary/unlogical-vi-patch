# -*- coding: utf-8 -*-
"""Dịch nốt thẻ `[terinfo]` duy nhất còn tiếng Nhật — cái viết **không ngoặc kép**.

Băng-rôn TERMINAL do engine vẽ thẳng từ tham số `text=` của script chương. Cả 9 thẻ
`terinfo` khác trong `00_03` đã dịch từ lâu; đúng một thẻ còn nguyên tiếng Nhật:

```
dòng  744  [terinfo text="Xác nhận người thua cuộc:\\nKozumi Shota, Kasuya Yuzuha, …"]
dòng 1111  [terinfo text=敗北者が確定しました\\n小住祥太　粕谷柚葉　永守藍　柾衣沙　芳谷尚紀]
```

Hai dòng là **cùng một thông báo, cùng một danh sách tên**, chỉ khác chỗ dòng 1111
viết `text=` **không có ngoặc kép**. Đó chính là lý do nó sót: bên xuất sheet chỉ ăn
dạng `text="…"` (xem `tools/README.md`, mục *Đã mở đường ghi cho `cmd`*) — bản gốc có
đúng một lệnh không ngoặc, `sID 71` @12609, và **sheet không có hàng cho nó**. Nên
`apply_sheet_cells.py` không bao giờ với tới ô này: sửa tay ở đây là vĩnh viễn, cùng
lớp với `fix_item_name_case.py` và `fix_system_text_case.py`. Vì vòng merge có thể
chép đè `scriptText` nên `--check` vẫn nên nằm trong cổng sau merge.

Bản dịch **chép nguyên văn dòng 744** — cùng sự kiện, cùng màn hình, cùng năm cái tên
đã romanise (`Kozumi Shota` / `Kasuya Yuzuha` / `Nagamori Ran` / `Masaki Isa` /
`Yoshitani Naoki`), nên không phát minh chữ mới. Có thêm ngoặc kép: giá trị mới có
dấu cách, để trần thì bộ phân tích lệnh chỉ lấy tới khoảng trắng đầu tiên.

**Cùng một dòng nằm ở ba nơi**, bỏ sót một chỗ là vòng đối chiếu sau lại thấy lệch:

| nơi | dạng chuỗi | số lần |
|---|---|---|
| script chương `00_03` | nguyên văn | 1 |
| `ScenarioData.scriptText` (sID 71) | JSON-escape (`\\` → `\\\\`) | 1 |
| `ScenarioData.scriptText_Line` | JSON-escape | 1 |

Thay trên **văn bản thô** của asset, không parse rồi dump lại: dump lại là viết lại
toàn bộ JSON 17 MB (khoảng trắng, cách escape) và diff sẽ vô nghĩa.

    python tools\\fix_terinfo_unquoted.py            # chạy thử
    python tools\\fix_terinfo_unquoted.py --apply
    python tools\\fix_terinfo_unquoted.py --check    # còn sót -> exit 1

Backup: `_backup\\scenario01.terinfounquoted`
"""
import io
import json
import os
import shutil
import sys

if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "scenario01.terinfounquoted")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

OLD = ('[terinfo text=敗北者が確定しました\\n'
       '小住祥太\u3000粕谷柚葉\u3000永守藍\u3000柾衣沙\u3000芳谷尚紀]')
NEW = ('[terinfo text="Xác nhận người thua cuộc:\\n'
       'Kozumi Shota, Kasuya Yuzuha, Nagamori Ran, Masaki Isa, Yoshitani Naoki."]')


def esc(s):
    """Dạng chuỗi nằm trong nguồn JSON của ScenarioData."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def replace_spans(raw, pairs):
    """Thay theo VỊ TRÍ, trả về (văn bản mới, danh sách chỗ đã thay).

    Không dùng str.replace cho khâu nghiệm thu được: chuỗi mới **đã có sẵn** trong
    file (dòng 744 dịch từ trước), nên phép đổi nghịch bằng replace sẽ đụng luôn
    chỗ vốn đã đúng. Ghi lại vị trí thì dựng ngược được chính xác.
    """
    hits = []
    for old, new in pairs:
        i = raw.find(old)
        while i >= 0:
            hits.append((i, old, new))
            i = raw.find(old, i + len(old))
    hits.sort()
    out, pos = [], 0
    for i, old, new in hits:
        if i < pos:
            raise SystemExit("hai chỗ thay chồng lấn nhau")
        out.append(raw[pos:i])
        out.append(new)
        pos = i + len(old)
    out.append(raw[pos:])
    return "".join(out), hits


def undo(text, hits, raw):
    """Dựng ngược văn bản mới về bản cũ, chỉ tại đúng những chỗ đã thay."""
    out, pos, shift = [], 0, 0
    for i, old, new in hits:
        start = i + shift
        if text[start:start + len(new)] != new:
            return False
        out.append(text[pos:start])
        out.append(old)
        pos = start + len(new)
        shift += len(new) - len(old)
    out.append(text[pos:])
    return "".join(out) == raw


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
        n_plain = raw.count(OLD)
        n_esc = raw.count(esc(OLD))
        if not (n_plain or n_esc):
            continue
        new, hits = replace_spans(raw, [(OLD, NEW), (esc(OLD), esc(NEW))])
        plan.append((d, raw, new, n_plain, n_esc, hits))
        print("   %-16s nguyên văn %d, JSON-escape %d" % (d.m_Name, n_plain, n_esc))

    tot = sum(p[3] + p[4] for p in plan)
    print("thẻ [terinfo] còn tiếng Nhật: %d chỗ trong %d asset" % (tot, len(plan)))

    if CHECK:
        if plan:
            print("\nchạy `python tools\\fix_terinfo_unquoted.py --apply`")
            raise SystemExit(1)
        print("PASS không còn chỗ nào")
        return
    if not plan:
        print("không có gì để sửa")
        return

    # Chốt: dựng ngược tại đúng những chỗ đã thay phải ra bản cũ.
    for d, raw, new, _, _, hits in plan:
        if not undo(new, hits, raw):
            raise SystemExit("%s: đổi ngoài dự kiến" % d.m_Name)
    print("kiểm tra: dựng ngược đúng bằng bản gốc trên mọi asset")

    before = None
    for d, raw, _, _, _, _ in plan:
        if d.m_Name == "ScenarioData":
            before = json.loads(raw.lstrip("\ufeff"))

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(BUNDLE, BACKUP)
        print("backup ->", os.path.relpath(BACKUP, ROOT))
    for d, _raw, new, _, _, _ in plan:
        d.m_Script = new
        d.save()
    with open(BUNDLE, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi", os.path.relpath(BUNDLE, ROOT), os.path.getsize(BUNDLE), "byte")

    # đọc lại từ disk, đừng tin bộ đệm trong bộ nhớ
    _, after = load()
    got = {d.m_Name: raw for d, raw in after}
    for d, _raw, new, _, _, _ in plan:
        if got[d.m_Name] != new:
            raise SystemExit("đọc lại %s không khớp" % d.m_Name)
    if any(OLD in raw or esc(OLD) in raw for _d, raw in after):
        raise SystemExit("chuỗi cũ vẫn còn")
    if before is not None:
        now = json.loads(got["ScenarioData"].lstrip("\ufeff"))
        a, b = before["target"], now["target"]
        assert len(a) == len(b), "số scenario đổi"
        for x, y in zip(a, b):
            assert x["loadLine"] == y["loadLine"], "loadLine đổi"
            assert x["selLine"] == y["selLine"], "selLine đổi"
            assert x["text"] == y["text"], "text[] đổi"
            assert x["selText"] == y["selText"], "selText đổi"
            assert x["talkName"] == y["talkName"], "talkName đổi"
            assert len(x["scriptText_Line"]) == len(y["scriptText_Line"]), (
                "số dòng scriptText_Line đổi")
        print("  ScenarioData: loadLine / selLine / text / selText / talkName nguyên vẹn")
    print("  đọc lại: %d asset khớp" % len(plan))


if __name__ == "__main__":
    main()
