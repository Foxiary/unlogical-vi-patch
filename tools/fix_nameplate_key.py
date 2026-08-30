# -*- coding: utf-8 -*-
"""Sửa 6 nameplate hỏng trong ScenarioData — khoá bị pass thay chữ đụng vào,
và tên nhân vật chính bị viết cứng.

## ScenarioData giữ nameplate ở ba trường

    scriptText_Line   bản THÔ, khớp từng byte với bản gốc — không bao giờ sửa
    scriptText        bản dịch
    talkName          bản dịch, một ô cho mỗi tin nhắn

Mọi lỗi dưới đây nằm ở hai trường dịch; `scriptText_Line` vẫn sạch. Đó cũng là
cách phát hiện: so nửa khoá của `【khoá/hiển thị】` giữa build và bản gốc theo
từng vị trí, chỗ nào lệch mà không phải một bản dịch cố ý thì là lỗi.

## Sáu chỗ

1. `【Phía Đông堂 伊槻/姫嶋 恭介】` ×60 — `東` bị đổi thành "Phía Đông" giữa khoá.
   423 chỗ cùng loại khác đã đúng là `【東堂 伊槻/Himejima Kyosuke】`; 60 chỗ này
   vừa hỏng khoá vừa chưa dịch nửa hiển thị.
2. `【Miyabi/瑠璃】` ×3 — ngược đời: nửa KHOÁ bị La-tinh hoá, nửa HIỂN THỊ còn
   tiếng Nhật. `雅火` là một trong 6 khoá mà `ADVManager$$GetNameColor` so để
   chọn màu tên, nên mất khoá là mất màu. talkName tương ứng đã đúng `雅火/Ruri`.
3. `【Quán cà phêの店員】` ×1 — `カフェ` bị đổi giữa chuỗi, bỏ lại `の店員`.
   25 chỗ cùng loại đã là `【NV quán café】`.
4-6. `【Kanna＆Kai】` ×14, `【Kai＆Kanna】` ×4, `【Kanna＆Ran】` ×4 — token `player`
   bị thay bằng tên mặc định. CLAUDE.md cấm đúng việc này: ai đặt tên khác
   `Kanna` sẽ thấy sai tên, và một lượt chơi bằng tên mặc định thì trông hoàn
   hảo nên không lộ. `player` là literal mà `ADVManager$$CharaNameConvert` /
   `$$ShowCharaNameUpdate` / `$$GetNameColor` thay thế, và bản gốc cũng ghép
   `【player＆戒】` y như vậy, nên giữ token trong chuỗi ghép là đúng.

Không chỗ nào đổi số dòng, nên `loadLine` / `selLine` vẫn trỏ đúng.

    python tools\\fix_nameplate_key.py            # chạy thử / --check
    python tools\\fix_nameplate_key.py --apply
"""
import io
import json
import os
import re
import shutil
import sys

import UnityPy

if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "scenario01.nameplatekey")
APPLY = "--apply" in sys.argv

# (nameplate hỏng, nameplate đúng, số chỗ chờ ở scriptText, số chỗ chờ ở talkName)
FIXES = [
    ("Phía Đông堂 伊槻/姫嶋 恭介", "東堂 伊槻/Himejima Kyosuke", 60, 0),
    ("Miyabi/瑠璃",              "雅火/Ruri",                  3, 0),
    ("Quán cà phêの店員",         "NV quán café",              1, 0),
    ("Kanna＆Kai",              "player＆Kai",                7, 7),
    ("Kai＆Kanna",              "Kai＆player",                2, 2),
    ("Kanna＆Ran",              "player＆Ran",                2, 2),
]
FIELDS = ("scriptText", "talkName")     # scriptText_Line là bản thô, KHÔNG đụng


def load(path):
    env = UnityPy.load(path)
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            if data.m_Name == "ScenarioData":
                raw = data.m_Script
                if not isinstance(raw, str):
                    raw = bytes(raw).decode("utf-8")
                return env, data, raw
    raise SystemExit("không thấy ScenarioData trong %s" % path)


def count(doc, needle):
    """{trường: số lần '【needle】' xuất hiện}."""
    tag = "【" + needle + "】"
    out = {}
    for field in ("scriptText", "scriptText_Line", "talkName"):
        n = 0
        for target in doc["target"]:
            value = target[field]
            if isinstance(value, str):
                n += value.count(tag)
            else:
                n += sum(s.count(tag) for s in value)
        out[field] = n
    return out


def main():
    env, asset, raw = load(BUNDLE)
    bom = "﻿" if raw.startswith("﻿") else ""
    doc = json.loads(raw.lstrip("﻿"))
    print("%s  %d target, %d ký tự" % (os.path.relpath(BUNDLE, ROOT), len(doc["target"]), len(raw)))

    print("\n%-30s %-28s %s" % ("hỏng", "đúng", "scriptText / _Line / talkName"))
    ok = True
    for bad, good, want_st, want_tn in FIXES:
        c = count(doc, bad)
        mark = ""
        if c["scriptText"] != want_st or c["talkName"] != want_tn:
            mark = "   <<< SỐ CHỖ KHÔNG KHỚP (chờ %d/%d)" % (want_st, want_tn)
            ok = False
        if c["scriptText_Line"]:
            mark = "   <<< CÓ Ở BẢN THÔ — không dám sửa"
            ok = False
        print("  %-28s %-28s %5d %6d %8d%s"
              % (bad, good, c["scriptText"], c["scriptText_Line"], c["talkName"], mark))
    if not ok:
        raise SystemExit("\ntình trạng file không như mong đợi — đã sửa rồi, hoặc bản gốc đã đổi")

    total = sum(st + tn for _b, _g, st, tn in FIXES)
    print("\ntổng %d chỗ sẽ đổi" % total)
    if not APPLY:
        print("CHẠY THỬ — thêm --apply để ghi")
        return

    # --- sửa -------------------------------------------------------------------
    done = 0
    for target in doc["target"]:
        for field in FIELDS:
            value = target[field]
            if isinstance(value, str):
                new = value
                for bad, good, _s, _t in FIXES:
                    new = new.replace("【" + bad + "】", "【" + good + "】")
                if new != value:
                    done += sum(value.count("【" + b + "】") for b, _g, _s, _t in FIXES)
                    target[field] = new
            else:
                for i, s in enumerate(value):
                    new = s
                    for bad, good, _s2, _t2 in FIXES:
                        new = new.replace("【" + bad + "】", "【" + good + "】")
                    if new != s:
                        done += sum(s.count("【" + b + "】") for b, _g, _s2, _t2 in FIXES)
                        value[i] = new
    print("đã thay %d chỗ" % done)
    if done != total:
        raise SystemExit("thay %d chỗ, chờ %d — dừng, không ghi" % (done, total))

    out = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    if not os.path.exists(BACKUP):
        shutil.copy2(BUNDLE, BACKUP)
        print("backup ->", os.path.relpath(BACKUP, ROOT))
    asset.m_Script = bom + out
    asset.save()
    with open(BUNDLE, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi", os.path.relpath(BUNDLE, ROOT), os.path.getsize(BUNDLE), "byte")

    # --- đọc lại từ đĩa ---------------------------------------------------------
    _env2, _a2, back = load(BUNDLE)
    doc2 = json.loads(back.lstrip("﻿"))
    for bad, good, want_st, want_tn in FIXES:
        cb = count(doc2, bad)
        cg = count(doc2, good)
        if cb["scriptText"] or cb["talkName"]:
            raise SystemExit("còn %r sau khi ghi" % bad)
        print("  %-28s -> %-28s  scriptText %d, talkName %d" % (bad, good, cg["scriptText"], cg["talkName"]))

    old_lines = [s for t in doc["target"] for s in t["scriptText_Line"]]
    new_lines = [s for t in doc2["target"] for s in t["scriptText_Line"]]
    if old_lines != new_lines:
        raise SystemExit("bản thô scriptText_Line bị đổi — khôi phục từ backup")
    print("  bản thô scriptText_Line: %d dòng, nguyên vẹn" % len(new_lines))
    for field in ("loadLine", "selLine"):
        a = [v for t in doc["target"] for v in t[field]]
        b = [v for t in doc2["target"] for v in t[field]]
        if a != b:
            raise SystemExit("%s bị đổi" % field)
    print("  loadLine / selLine: nguyên vẹn")


if __name__ == "__main__":
    main()
