# -*- coding: utf-8 -*-
"""Thống nhất chữ hoa của tên vật phẩm giữa `ScriptDialogData` và lời thoại.

`ScriptDialogData` là 18 dòng thông báo ngắn ("Đã nhận được 『…』") hiện lên khi
nhận vật phẩm. Nó **không có trên Google Sheet** — không tab nào, không id nào —
nên mọi vòng merge đều bỏ qua nó, và sai ở đây không bao giờ tự khỏi.

`check_term_consistency.py` bắt được một chỗ lệch:

```
ScenarioData      "Trái tim Thiên sứ"   18 lần
ScriptDialogData  "Trái tim thiên sứ"    1 lần   (mục id 11)
```

Người chơi thấy cả hai cạnh nhau: popup nhận vật phẩm nổi lên ngay trên khung
thoại đang gọi nó là "Trái tim Thiên sứ".

Chỉ đụng `ScriptDialogData`, chỉ đúng chuỗi trong DOI, và chỉ khi nó xuất hiện
đúng một lần. Các asset khác trong bundle `json` giữ nguyên, kiểm bằng cách so
độ dài và số mục trước/sau.

    python tools\\fix_item_name_case.py            # chạy thử
    python tools\\fix_item_name_case.py --apply
    python tools\\fix_item_name_case.py --check    # còn lệch -> exit 1
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

JSONB = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
SCENARIO = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "json.itemname")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

# (chuỗi sai, chuỗi đúng). Chuỗi đúng phải là dạng mà ScenarioData đang dùng —
# main() đối chiếu lại chứ không tin danh sách này.
DOI = [("Trái tim thiên sứ", "Trái tim Thiên sứ")]


def doc(path, name):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        if d.m_Name == name:
            r = d.m_Script
            return env, o, d, (r if isinstance(r, str) else bytes(r).decode("utf-8"))
    raise SystemExit("không thấy %s trong %s" % (name, path))


def main():
    _, _, _, raw_s = doc(SCENARIO, "ScenarioData")
    sd = json.loads(raw_s.lstrip("﻿"))
    loi_thoai = "\n".join(s for t in sd["target"] for s in (t.get("text") or [])
                          if isinstance(s, str))

    env, obj, d, raw = doc(JSONB, "ScriptDialogData")
    doc_j = json.loads(raw.lstrip("﻿"))
    so_muc = len(doc_j["data"])

    can_doi = []
    for sai, dung in DOI:
        n = raw.count(sai)
        # Dạng ĐÚNG phải là dạng lời thoại thật sự đang dùng, và phải áp đảo.
        # Không thì đây là chuyện phải quyết bằng mắt, không phải bằng script.
        n_dung, n_sai = loi_thoai.count(dung), loi_thoai.count(sai)
        print("%-22r -> %-22r  ScriptDialogData %d | lời thoại: đúng %d, sai %d"
              % (sai, dung, n, n_dung, n_sai))
        if n == 0:
            continue
        if n != 1:
            raise SystemExit("%r xuất hiện %d lần, chờ đúng 1 — dừng" % (sai, n))
        if n_dung <= n_sai:
            raise SystemExit("lời thoại KHÔNG nghiêng về %r (%d vs %d) — không tự quyết"
                             % (dung, n_dung, n_sai))
        can_doi.append((sai, dung))

    if CHECK:
        if can_doi:
            print("\nchạy `python tools\\fix_item_name_case.py --apply`")
            raise SystemExit(1)
        print("PASS: tên vật phẩm trong ScriptDialogData khớp lời thoại")
        return
    if not can_doi:
        print("không có gì để sửa")
        return

    moi = raw
    for sai, dung in can_doi:
        moi = moi.replace(sai, dung)

    # --- chốt chặn ---------------------------------------------------------
    j2 = json.loads(moi.lstrip("﻿"))
    if len(j2["data"]) != so_muc:
        raise SystemExit("số mục đổi: %d -> %d" % (so_muc, len(j2["data"])))
    if [x["id"] for x in j2["data"]] != [x["id"] for x in doc_j["data"]]:
        raise SystemExit("danh sách id đổi")
    khac = [(a["id"], a["text"], b["text"])
            for a, b in zip(doc_j["data"], j2["data"]) if a["text"] != b["text"]]
    if len(khac) != len(can_doi):
        raise SystemExit("số mục đổi chữ là %d, chờ %d" % (len(khac), len(can_doi)))
    for i, cu, mo in khac:
        print("   mục id=%s" % i)
        print("      cũ : %s" % cu)
        print("      mới: %s" % mo)

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(JSONB, BACKUP)
        print("backup ->", BACKUP)
    d.m_Script = moi
    d.save()
    # bundle `json` có type tree nhúng nên save() bình thường; KHÔNG áp dụng cho
    # level10/19/20 — xem CLAUDE.md.
    with open(JSONB, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi", JSONB, os.path.getsize(JSONB))

    # đọc lại TỪ DISK, không tin giá trị trong bộ nhớ
    _, _, _, lai = doc(JSONB, "ScriptDialogData")
    j3 = json.loads(lai.lstrip("﻿"))
    for sai, dung in can_doi:
        if lai.count(sai) or not lai.count(dung):
            raise SystemExit("đọc lại: chưa đổi được %r" % sai)
    if len(j3["data"]) != so_muc:
        raise SystemExit("đọc lại: số mục đổi")
    print("đọc lại: %d mục nguyên vẹn, %d chuỗi đã đổi" % (len(j3["data"]), len(can_doi)))


main()
