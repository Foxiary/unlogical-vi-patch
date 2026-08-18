# -*- coding: utf-8 -*-
"""Bắt tin nhắn bị **cắt mất đầu câu**: bản dịch còn dấu `）` mà mất dấu `（`.

Lớp lỗi này vô hình khi đọc bản dịch — câu vẫn đọc trôi, chỉ thiếu chủ ngữ hoặc mệnh đề
đầu, và dấu đóng ngoặc lẻ là thứ duy nhất tố giác. Chốt `guards()` của
`apply_sheet_cells.py` chỉ cân `"`, `「」`, `『』` nên không thấy.

Cách nhận diện chính xác, không kêu oan:

    bản dịch có số `）` > số `（`   (hoặc `)` > `(`)
    VÀ bản Nhật của đúng tin nhắn đó có **một cặp đầy đủ**

Điều kiện thứ hai là thứ loại được emoticon: `75/txt/0044` = "Gì vậy, tự dưng hỏi thế =))"
dịch từ `なに、いきなり笑` — bản Nhật không có ngoặc nào, nên `=))` không bị bắt.

Đo 18/08/2026 trên toàn bộ 39.803 tin nhắn: **5 ô lệch ngoặc, 4 là lỗi thật**, cả 4 đều
lệch theo cùng một kiểu (mất `（` mở) và **cả 4 đều bị cắt sẵn trên sheet** — cột Nhật của
sheet vẫn nguyên, chỉ cột dịch mất cụm đầu. Nên chữa gốc là chữa trên sheet.

`--apply` chỉ chữa những ô mà **câu chữ đã đủ**, chỉ thiếu dấu và ngắt dòng — liệt kê
tường minh trong `PLAN`. Ô còn thiếu chữ thì phải dịch, tool không đoán.

    python tools\fix_paren_balance.py            # liệt kê
    python tools\fix_paren_balance.py --apply
    python tools\fix_paren_balance.py --check    # gate, còn lỗi -> exit 1
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
STOCK = r"D:\Downloads\UNLOGICAL_v2\Data\StreamingAssets\scenario\scenario01"
BACKUP = os.path.join(ROOT, "_backup", "scenario01.parenbalance")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

# Gộp hai độ rộng: bản dịch quen dùng `(` nửa rộng ở chỗ bản Nhật dùng `（` toàn rộng
# (memory `unlogical-punctuation-conventions`), nên đếm tách theo từng cặp là bỏ sót
# đúng 3/4 ô lỗi.
OPEN, CLOSE = "（(", "）)"

# Ô mà bản dịch ĐÃ ĐỦ CHỮ, chỉ thiếu dấu mở + ngắt dòng/thụt lề theo bản Nhật.
# (scenarioID, index, chuỗi cũ, chuỗi mới)
# Ô thiếu CHỮ, phải dịch trên sheet — tool không đoán. Ghi ra đây để gate chỉ đỏ khi có
# ô MỚI xuất hiện; ba ô này đã cắt sẵn trong cả snapshot (31) và (32), cột Nhật vẫn nguyên.
KNOWN = {
    (85, 1353): "thiếu `このひとは` — bản dịch mở đầu bằng 'lúc nào trông cũng…'",
    (85, 1429): "thiếu `……なんで、` — bản dịch mở đầu bằng 'Kai lại…'",
    (85, 1431): "thiếu vế `わかってるのに？` (dù biết rõ) — bản dịch chỉ còn vế đầu",
}

PLAN = [
    (126, 269,
     "Nhưng giờ Yuri đang bận, nếu mình giữ anh ấy lại muộn quá, "
     "có lẽ sẽ làm phiền anh ấy mất...）",
     "（Nhưng giờ Yuri đang bận,\n　nếu mình giữ anh ấy lại muộn quá, "
     "có lẽ sẽ làm phiền anh ấy mất...）"),
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
    raise SystemExit("không thấy ScenarioData trong " + path)


def jp_message(jt, ln):
    """Bản Nhật của tin nhắn bắt đầu ở dòng `ln`: tới trước dòng trắng kế tiếp."""
    L = jt["scriptText_Line"]
    out, k = [], ln
    while k < len(L) and L[k].strip():
        out.append(L[k])
        k += 1
    return "\n".join(out)


def paren_counts(s):
    return (sum(s.count(c) for c in OPEN), sum(s.count(c) for c in CLOSE))


def orphan_closers(s):
    o, c = paren_counts(s)
    return c > o


def scan(data, jp):
    hits = []
    for ti, t in enumerate(data["target"]):
        jt = jp["target"][ti]
        for j, s in enumerate(t["text"]):
            if not orphan_closers(s):
                continue
            msg = jp_message(jt, t["loadLine"][j])
            # bản Nhật phải có một cặp đầy đủ mới tính là lỗi — điều kiện này loại
            # emoticon `=))` (bản Nhật của nó không có ngoặc nào).
            jo, jc = paren_counts(msg)
            if not (jo and jo == jc):
                continue
            hits.append((ti, t["scenarioID"], j, s, msg))
    return hits


def main():
    env, d, raw = load(BUNDLE)
    bom = "﻿" if raw.startswith("﻿") else ""
    data = json.loads(raw.lstrip("﻿"))
    _, _, jraw = load(STOCK)
    jp = json.loads(jraw.lstrip("﻿"))

    hits = scan(data, jp)
    planned = {(sid, j): (old, new) for sid, j, old, new in PLAN}
    todo, left = [], []
    for ti, sid, j, s, msg in hits:
        p = planned.get((sid, j))
        if p and s == p[0]:
            todo.append((ti, sid, j, p[0], p[1]))
        else:
            left.append((sid, j, s, msg))

    print("tin nhắn mất dấu `（` mở (bản Nhật có cặp đủ): %d" % len(hits))
    for sid, j, s, msg in left:
        tag = "TỒN " if (sid, j) in KNOWN else "FAIL"
        print()
        print("%s %d/txt/%04d  — thiếu CHỮ, phải dịch trên sheet" % (tag, sid, j))
        print("       VN: %r" % s[:120].replace("\n", "⏎"))
        print("       JP: %r" % msg[:120].replace("\n", "⏎"))
    for ti, sid, j, old, new in todo:
        print("\n  -> %d/txt/%04d  chữ đã đủ, thêm dấu + ngắt dòng theo bản Nhật" % (sid, j))
        print("       cũ : %r" % old.replace("\n", "⏎"))
        print("       mới: %r" % new.replace("\n", "⏎"))

    if CHECK:
        # Chỉ đỏ khi có ô MỚI. Ba ô trong KNOWN là lỗi cắt sẵn ở upstream, in ra mỗi lần
        # chạy để không bị quên, nhưng không chặn — build không tự chữa được.
        fresh = [r for r in left if (r[0], r[1]) not in KNOWN]
        if fresh:
            print()
            print("%d ô MỚI thiếu chữ — sửa trên sheet rồi merge lại" % len(fresh))
            raise SystemExit(1)
        if todo:
            print()
            print("%d ô vá được — chạy `--apply`" % len(todo))
            raise SystemExit(1)
        if left:
            print()
            print("PASS không có ô MỚI. %d ô tồn, phải dịch trên sheet:" % len(left))
            for sid, j, _s, _m in left:
                print("   %d/txt/%04d  %s" % (sid, j, KNOWN[(sid, j)]))
            return
        print()
        print("PASS không tin nhắn nào mất dấu ngoặc mở")
        return

    if not todo:
        print("\nkhông có ô nào trong PLAN cần vá")
        return

    out = raw

    def enc(x):
        return json.dumps(x, ensure_ascii=False, separators=(",", ":"))

    for ti in sorted({h[0] for h in todo}):
        arr_old = list(data["target"][ti]["text"])
        arr_new = list(arr_old)
        for t2, sid, j, old, new in [h for h in todo if h[0] == ti]:
            assert arr_new[j] == old, "text[%d] không như đã đọc" % j
            arr_new[j] = new
        oj, nj = enc(arr_old), enc(arr_new)
        if out.count(oj) != 1:
            raise SystemExit("mảng text[] của target[%d] khớp %d lần" % (ti, out.count(oj)))
        out = out.replace(oj, nj)

    after = json.loads(out.lstrip("﻿"))
    changed = {(h[0], h[2]) for h in todo}
    for ti, t in enumerate(data["target"]):
        ta = after["target"][ti]
        assert ta["loadLine"] == t["loadLine"], "loadLine đổi"
        assert ta["scriptText_Line"] == t["scriptText_Line"], "scriptText_Line đổi"
        for j, s in enumerate(t["text"]):
            if (ti, j) in changed:
                continue
            assert ta["text"][j] == s, "text[%d] target[%d] đổi ngoài dự kiến" % (j, ti)
    for ti, sid, j, old, new in todo:
        assert after["target"][ti]["text"][j] == new
        assert not orphan_closers(new), "%d/txt/%d vẫn lệch ngoặc" % (sid, j)
    print("\nkiểm tra: chỉ %d tin nhắn đổi, loadLine/scriptText_Line nguyên vẹn" % len(todo))

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
    for ti, sid, j, old, new in todo:
        assert rd["target"][ti]["text"][j] == new, "đọc lại %d/txt/%d sai" % (sid, j)
    print("  đọc lại: %d tin nhắn khớp" % len(todo))


main()
