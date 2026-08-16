# -*- coding: utf-8 -*-
"""Move the "(English)" gloss out of a dictionary title and into its `ruby`.

The detail title is drawn by `level10` pid 897 `Mask_Title/Title` — 588x64,
NoWrap, no auto-size, masked and centre-aligned — so a long title is clipped at
both ends.  Appending "(English)" to the Vietnamese name pushed 24 of the 80
titles past that width.  The `ruby` field above the title was freed up by
`fix_dictionary_ruby.py`, and moving the parenthetical into it clears 16 of them.

Entries that had no `ruby` key get one inserted in the same position the other
entries use, between `title` and `text`.

`no=255` keeps its existing ruby: the stock entry is 育成者 read トレーナー, so
"Trainer" is the reading and "(Breeder)" was the translator's own addition —
dropped, not promoted.

    python tools\\fix_dictionary_titles.py [--apply]
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

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
BACKUP = os.path.join(ROOT, "_backup", "json.predictitle")
APPLY = "--apply" in sys.argv

# KHÔNG thêm no=104 vào đây: "(Lần trước)" có sẵn trong bản gốc アンロジカル（前回）,
# là một phần của tên mục để phân biệt với no=103, không phải chú thích thêm.

# no -> (tiêu đề mới, ruby mới).  ruby None = giữ nguyên trường ruby đang có.
# Mục nào đã ở đúng trạng thái đích thì bị bỏ qua, nên chạy lại nhiều lần vô hại.
PLAN = {
    110: ("Mô phỏng", "EMULATION"),
    111: ("Quá liều", "OVERDOSE"),
    159: ("Thân chủ", "CLIENT"),
    163: ("Tư vấn viên", "CONSULTANT"),
    204: ("Tự học", "SELF-LEARNING"),
    211: ("Học sâu", "DEEP LEARNING"),
    250: ("DAW", ""),                       # ruby trùng tiêu đề, xoá
    252: ("Tinh chỉnh", "TUNING"),
    253: ("Luồng dữ liệu", "DATA STREAM"),
    255: ("Người nuôi dưỡng", None),        # giữ ruby "Trainer", bỏ "(Breeder)"
    256: ("Bài toán xe điện", "TROLLEY PROBLEM"),
    300: ("Dữ liệu thần kinh", "NEURAL DATA"),
    352: ("Dấu hiệu sinh tồn", "VITAL"),
    354: ("Lỗi", "BUG"),
    355: ("Rối loạn giấc ngủ", "PARASOMNIA"),
    356: ("Treo máy", "HANG-UP"),
    357: ("Tội khởi tố không cần yêu cầu", "NON-COMPLAINANT OFFENSE"),
    362: ("Tiện ích bổ sung", "PLUGIN"),
    363: ("Tạo nguyên mẫu", "PROTOTYPING"),
    401: ("Cố ý gián tiếp", "WILLFUL NEGLIGENCE"),
    402: ("Máy chủ chính", "MAINFRAME"),
    403: ("Người thử nghiệm", "MONITOR"),
    450: ("Việc làm đen", "YAMI BAITO"),
    502: ("Hòa ván", "RYUKYOKU"),
    505: ("Log", "NHẬT KÝ HỆ THỐNG"),
    550: ("Nghiện công việc", "WORKAHOLIC"),
}

# Khung THẬT là màn ARCHIVE trong terminal (level22), không phải popup level10.
BOX_W, SIZE, CSPACE = 500.0, 32.0, 3.5          # Mask_Title 500x40, pid 330
RUBY_BOX, RUBY_SIZE, RUBY_CSPACE = 500.0, 12.0, 0.0   # Mask_Ryby đã nới 180 -> 500


def q(s):
    return json.dumps(s, ensure_ascii=False)


def main():
    import adv_layout as L

    def w(s, size, cs):
        return sum((L.glyph_advance(c) + cs) for c in s) * size / L.POINT_SIZE

    env = UnityPy.load(BUNDLE)
    obj = next((o for o in env.objects
                if o.type.name == "TextAsset" and o.read().m_Name == "DictionaryData"), None)
    if obj is None:
        raise SystemExit("DictionaryData not found in " + BUNDLE)
    d = obj.read()
    raw = d.m_Script
    if not isinstance(raw, str):
        raw = bytes(raw).decode("utf-8")
    data = json.loads(raw.lstrip("﻿"))
    by_no = {i["no"]: i for i in data["data"]}

    out = raw
    added, changed, skipped = 0, 0, 0
    print("%-6s %-34s %-10s %-20s %s" % ("no", "tiêu đề mới", "rộng", "ruby", "rộng"))
    for no in sorted(PLAN):
        new_title, new_ruby = PLAN[no]
        it = by_no[no]
        old_title = it["title"]["jp"]
        has_ruby = "ruby" in it
        old_ruby = it["ruby"]["jp"] if has_ruby else None
        if new_ruby is None:
            new_ruby = old_ruby
        if old_title == new_title and (old_ruby or "") == new_ruby:
            skipped += 1
            continue

        if has_ruby:
            a = '"title":{"jp":%s},"ruby":{"jp":%s}' % (q(old_title), q(old_ruby))
            b = '"title":{"jp":%s},"ruby":{"jp":%s}' % (q(new_title), q(new_ruby))
        else:
            a = '"title":{"jp":%s},"text"' % q(old_title)
            b = '"title":{"jp":%s},"ruby":{"jp":%s},"text"' % (q(new_title), q(new_ruby))
            added += 1
        n = out.count(a)
        if n != 1:
            raise SystemExit("khớp %d lần (phải là 1) ở no=%s" % (n, no))
        out = out.replace(a, b)
        changed += 1

        tw, rw = w(new_title, SIZE, CSPACE), w(new_ruby, RUBY_SIZE, RUBY_CSPACE)
        flag = ("  << TIÊU ĐỀ TRÀN" if tw > BOX_W else "") + ("  << RUBY TRÀN" if rw > RUBY_BOX else "")
        print("%-6s %-34s %5.0f px  %-24s %5.0f px%s" % (no, new_title, tw, new_ruby or "—", rw, flag))

    after = json.loads(out.lstrip("﻿"))

    def walk(x, path=""):
        if isinstance(x, dict):
            for k, v in x.items():
                yield from walk(v, path + "/" + str(k))
        elif isinstance(x, list):
            for i, v in enumerate(x):
                yield from walk(v, path + "[%d]" % i)
        else:
            yield path, x

    b0, b1 = dict(walk(data)), dict(walk(after))
    new_keys = set(b1) - set(b0)
    gone = set(b0) - set(b1)
    diff = [k for k in b0 if k in b1 and b0[k] != b1[k]]
    print("\nmục sửa: %d   bỏ qua (đã đúng): %d   trường ruby thêm mới: %d   trường mất đi: %d"
          % (changed, skipped, len(new_keys), len(gone)))
    assert not gone, "mất trường: %s" % gone
    assert all(k.endswith("/ruby/jp") for k in new_keys)
    assert all(k.endswith("/title/jp") or k.endswith("/ruby/jp") for k in diff), diff
    assert len(new_keys) == added

    over = [(i["no"], i["title"]["jp"], w(i["title"]["jp"], SIZE, CSPACE))
            for i in after["data"] if w(i["title"]["jp"], SIZE, CSPACE) > BOX_W]
    print("tiêu đề còn tràn khung %d: %d" % (BOX_W, len(over)))
    for no, t, wd in sorted(over, key=lambda r: -r[2]):
        print("   no=%-4s %5.0f px  %s" % (no, wd, t))

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(BUNDLE, BACKUP)
        print("backup ->", BACKUP)
    d.m_Script = out
    d.save()
    blob = env.file.save(packer="lz4")
    with open(BUNDLE, "wb") as f:
        f.write(blob)
    print("đã ghi", BUNDLE, os.path.getsize(BUNDLE))


main()
