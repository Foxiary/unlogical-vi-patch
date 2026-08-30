# -*- coding: utf-8 -*-
"""Thống nhất cách gọi nhóm `黒服` — "Áo đen", và `黒い服の男` — "Người áo đen".

Nameplate có dạng `【khoá/tên hiện ra】`. **Chỉ phần sau dấu `/` được vẽ ra** — đã kiểm
bằng ảnh chụp máy thật: plate ghi đúng `Hắc phục`, không có `運営Ｃ`. Phần trước dấu `/`
là khoá tra cứu (sprite, voice) và không bao giờ được đổi.

## Giai đoạn 1 — `黒服` -> "Áo đen"

Build đang dịch CÙNG một chữ Nhật theo hai kiểu:

```
【運営Ａ/黒服】        60 lần  ->  Áo đen        <- đúng
【運営Ｂ~Ｇ/黒服】    216 lần  ->  Hắc phục      <- sửa
```

"Hắc phục" là đọc âm Hán-Việt từng chữ (黒=hắc, 服=phục); ngoài chuyện lệch với 60 chỗ
kia, nó còn dễ đọc nhầm thành "khắc phục". Ba link từ điển cùng trỏ mục no=160 mà ghi
ba kiểu (`Hắc Phục`, `黒服`, `Áo đen`) — dấu hiệu trôi dạt chứ không phải lựa chọn.

## Giai đoạn 2 — `黒い服の男` và `黒服の男` -> "Người áo đen"

`黒服` là tên gọi chung cho cả nhóm; hai dạng có `の男` là **một người cụ thể**. Giai
đoạn 1 gộp tất cả thành "Áo đen", giai đoạn 2 tách lại.

Không thay theo chuỗi được: `運営の手下Ｂ` mang **cả hai** dạng Nhật (`黒い服の男` 5 lần
và `黒服の男` 2 lần), sau giai đoạn 1 đều là "Áo đen" — thay theo khoá sẽ trúng cả hai.
Nên **ghép theo vị trí** với bản gốc 1.0.2: quét nameplate thứ i của hai chuỗi thô,
76 603 cái khớp 1:1.

Mỗi nameplate xuất hiện **ba lần** trong `ScenarioData` — `talkName`, `scriptText`,
`scriptText_Line`. Hai chỗ đầu đã dịch, `scriptText_Line` còn nguyên tiếng Nhật; giai
đoạn 2 chỉ đụng chỗ đang là "Áo đen", để `scriptText_Line` yên như phần còn lại của nó.

## Chỗ KHÔNG đụng

**143 script chương** là bản Nhật gốc (`【運営Ｂ/黒服】`, 303 chỗ). Game lấy nameplate từ
`ScenarioData`; chỉ *lệnh* mới chạy từ script chương. Khác `fix_stage_term.py` — lệnh
phải sửa cả hai nơi, nameplate thì không.

`no=` của `[dic …]` giữ nguyên; chỉ `text=` (nhãn hiện ra) đổi theo.

    python tools\\fix_black_suit_name.py            # chạy thử
    python tools\\fix_black_suit_name.py --apply
    python tools\\fix_black_suit_name.py --check    # còn chỗ nào -> exit 1
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
STOCK = r"D:\Downloads\UNLOGICAL_v2\Data\StreamingAssets\scenario\scenario01"
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

OLD = ["Hắc phục", "Hắc Phục"]
NEW = "Áo đen"
# Cả hai dạng đều là MỘT NGƯỜI cụ thể (`の男`), khác `黒服` là tên gọi chung cả nhóm.
# `運営の手下Ｂ` mang cả hai dạng, nên chúng chỉ phân biệt được từ phía bản GỐC.
MAN_JP = ("黒い服の男", "黒服の男")
MAN = "Người áo đen"
NP = re.compile(r"【[^【】]*】")
KEYS = ["運営Ｂ", "運営Ｃ", "運営Ｄ", "運営Ｆ", "運営Ｇ", "運営Ａ", "運営の手下"]
DIC_NO = re.compile(r"\[dic\b[^\]]*?\bno=(\d+)")


def load(path, name):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        if d.m_Name == name:
            r = d.m_Script
            return env, d, (r if isinstance(r, str) else bytes(r).decode("utf-8"))
    raise SystemExit("không thấy %s trong %s" % (name, path))


def stage1(s):
    for o in OLD:
        s = s.replace(o, NEW)
    return s


def stage2(raw_s, raw_o):
    """Đổi tại đúng những vị trí mà bản GỐC ghi `黒い服の男`."""
    na, nb = list(NP.finditer(raw_o)), list(NP.finditer(raw_s))
    if len(na) != len(nb):
        raise SystemExit("số nameplate lệch: gốc %d, build %d — không ghép theo vị trí được"
                         % (len(na), len(nb)))
    out, pos, done, jp_left, already = [], 0, 0, 0, 0
    for ma, mb in zip(na, nb):
        if not any(ma.group(0).endswith("/" + j + "】") for j in MAN_JP):
            continue
        key = ma.group(0).split("/")[0].lstrip("【")
        want = "【%s/%s】" % (key, NEW)
        if mb.group(0) == want:
            out.append(raw_s[pos:mb.start()])
            out.append("【%s/%s】" % (key, MAN))
            pos = mb.end()
            done += 1
        elif mb.group(0) == "【%s/%s】" % (key, MAN):
            # đã sửa từ lần chạy trước — hàm này phải LẶP LẠI ĐƯỢC, không thì chính bước
            # đọc-lại sau khi ghi sẽ báo "không rõ trạng thái" trên thứ nó vừa ghi ra.
            already += 1
        elif mb.group(0) == ma.group(0):
            # còn nguyên tiếng Nhật — `scriptText_Line` chưa bao giờ được dịch, để yên
            jp_left += 1
        else:
            raise SystemExit("vị trí %d: gốc %r, build %r — không rõ trạng thái"
                             % (mb.start(), ma.group(0), mb.group(0)))
    out.append(raw_s[pos:])
    return "".join(out), done, jp_left, already


def main():
    env_s, d_s, raw_s = load(SCENARIO, "ScenarioData")
    env_j, d_j, raw_j = load(JSONB, "DictionaryData")

    n1_s = sum(raw_s.count(o) for o in OLD)
    n1_j = sum(raw_j.count(o) for o in OLD)
    print("giai đoạn 1  %r -> %r : ScenarioData %d, DictionaryData %d"
          % (OLD[0], NEW, n1_s, n1_j))

    new_s = stage1(raw_s) if n1_s else raw_s
    new_j = stage1(raw_j) if n1_j else raw_j

    if not os.path.exists(STOCK):
        raise SystemExit("không thấy bản gốc %s — cần nó để ghép vị trí" % STOCK)
    _, _, raw_o = load(STOCK, "ScenarioData")
    new_s, n2, jp_left, done_before = stage2(new_s, raw_o)
    print("giai đoạn 2  %s -> %r : %d chỗ cần sửa, %d chỗ đã sửa trước đó, "
          "%d chỗ còn nguyên tiếng Nhật ở scriptText_Line (để yên)"
          % (" / ".join(MAN_JP), MAN, n2, done_before, jp_left))

    total = n1_s + n1_j + n2
    if CHECK:
        if total:
            print("\nchạy `python tools\\fix_black_suit_name.py --apply`")
            raise SystemExit(1)
        print("PASS: %r và %r đã thống nhất" % (NEW, MAN))
        return
    if not total:
        print("không có gì để sửa")
        return

    # --- chốt chặn -------------------------------------------------------------
    for name, old, new in (("ScenarioData", raw_s, new_s), ("DictionaryData", raw_j, new_j)):
        for k in KEYS:
            if old.count(k) != new.count(k):
                raise SystemExit("%s: khoá %r đổi số lần (%d -> %d)"
                                 % (name, k, old.count(k), new.count(k)))
        if DIC_NO.findall(old) != DIC_NO.findall(new):
            raise SystemExit("%s: danh sách `no=` của [dic …] đổi" % name)
    if len(NP.findall(new_s)) != len(NP.findall(raw_s)):
        raise SystemExit("số nameplate đổi sau khi sửa")
    sd, sd2 = json.loads(raw_s.lstrip("﻿")), json.loads(new_s.lstrip("﻿"))
    for a, b in zip(sd["target"], sd2["target"]):
        ta = a["talkName"] if isinstance(a["talkName"], list) else json.loads(a["talkName"])
        tb = b["talkName"] if isinstance(b["talkName"], list) else json.loads(b["talkName"])
        for x, y in zip(ta, tb):
            if str(x).split("/")[0] != str(y).split("/")[0]:
                raise SystemExit("nameplate đổi phần KHOÁ: %r -> %r" % (x, y))
        assert len(a["text"]) == len(b["text"]) and a["loadLine"] == b["loadLine"]
    print("kiểm tra: khoá nameplate, số nameplate, `no=` của [dic], loadLine, số ô — nguyên vẹn")

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    for path, bak in ((SCENARIO, "scenario01.blacksuit"), (JSONB, "json.blacksuit")):
        b = os.path.join(ROOT, "_backup", bak)
        if not os.path.exists(b):
            shutil.copy2(path, b)
            print("backup ->", b)

    if new_s != raw_s:
        d_s.m_Script = new_s
        d_s.save()
        with open(SCENARIO, "wb") as f:
            f.write(env_s.file.save(packer="lz4"))
        print("đã ghi", SCENARIO, os.path.getsize(SCENARIO))
    if new_j != raw_j:
        d_j.m_Script = new_j
        d_j.save()
        with open(JSONB, "wb") as f:
            f.write(env_j.file.save(packer="lz4"))
        print("đã ghi", JSONB, os.path.getsize(JSONB))

    # --- đọc lại từ đĩa --------------------------------------------------------
    _, _, back_s = load(SCENARIO, "ScenarioData")
    _, _, back_j = load(JSONB, "DictionaryData")
    left = sum(back_s.count(o) for o in OLD) + sum(back_j.count(o) for o in OLD)
    if left:
        raise SystemExit("đọc lại: còn %d chỗ %r" % (left, OLD[0]))
    _, n2b, _, _ = stage2(back_s, raw_o)
    if n2b:
        raise SystemExit("đọc lại: còn %d chỗ chưa đổi" % n2b)
    b = json.loads(back_s.lstrip("﻿"))
    for a, c in zip(sd["target"], b["target"]):
        assert a["loadLine"] == c["loadLine"] and len(a["text"]) == len(c["text"])
    print("  đọc lại: 0 chỗ sót, loadLine và số ô nguyên vẹn")


if __name__ == "__main__":
    main()
