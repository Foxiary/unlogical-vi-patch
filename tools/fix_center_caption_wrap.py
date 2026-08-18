# -*- coding: utf-8 -*-
"""Ngắt dòng cho ô caption giữa màn (`[textmode=5]`) — **ngắt theo dấu câu**.

Widget: `level10` pid 898 `RenderCanvas_Final/EXTRALayer/EXTRAText`, rect **1920×720**,
cỡ 39, charSpacing 3,8, canh giữa cả hai chiều, `m_TextWrappingMode=1` (wrap BẬT),
`m_overflowMode=0` (Overflow). Engine **không vẽ `「」`** ở chế độ này — xác nhận trên ảnh
chụp máy thật, hai đầu dòng sạch.

**Khung không phải giới hạn thật.** Rect rộng 1920 = đúng bằng cả canvas (pivot giữa,
anchoredPosition 0), nên "vừa khung" không bảo vệ gì: chữ chạy sát mép màn vẫn tính là vừa.
Giới hạn thật là **lề an toàn**, lấy từ watermark tam giác UL ở góc dưới-phải:

    tam giác UL: x 1725..1842, y 930..1050  ->  lề phải 78 px
    vùng an toàn = 1920 - 2 x 78 = 1764 px

Số 78 px đo trên **ảnh chụp Ryujinx** (`_2026-08-18_18-00-52.png`), pixel chính xác.

> **Sai số cũ, ghi lại để không lặp:** lần đầu tôi suy lề này từ ảnh chụp điện thoại và ra
> **184 px** (vùng an toàn 1552). Sai vì mép LCD tối, lẫn với bezel và ốp, nên chỗ tôi nhận
> là "mép màn" thực ra là mép ốp — lề bị phóng lên hơn hai lần. Ảnh chụp bằng emulator thay
> thế hẳn phép đo trên ảnh điện thoại; đừng suy lề tuyệt đối từ ảnh chụp tay nữa. Điều mà
> ảnh điện thoại *vẫn* nói đúng là phần **tương đối**: chữ lấn qua tam giác ~22 px, khớp với
> ảnh Ryujinx.

Quy tắc ngắt: **ưu tiên dấu câu**, không cân độ dài. Gom các mệnh đề tách bởi
`. ! ? , ; : …` cho tới khi thêm nữa thì vượt 1764 px. Cân bằng độ dài cho ra chỗ ngắt
giữa câu, đọc gãy; ngắt theo dấu câu thì trùng nhịp bản gốc — kiểm được: `71/txt/0345`
ngắt ra **đúng chỗ bản Nhật tự ngắt** (`…でしょ？` / `　こんな風に…`).

**Tự dò lại chỗ ngắt từ câu chữ hiện tại**, nên chạy lại được sau mỗi merge (sheet làm
phẳng `\\n` mỗi vòng). `PLAN` chỉ ghi *id ô*, không ghi chuỗi đích.

Vì sao chỉ có danh sách ô mà không quét cả chế độ: chưa xác định được engine reset
`textmode` ở lệnh nào. Dò ngược tới `[textmode=5]` gần nhất cho ra ca cách **2593 dòng
script**, tức mode đã bị reset bởi thứ gì đó không phải `[textmode=N]`. Ô nào xác định
chắc chắn thuộc `textmode=5` thì thêm vào `PLAN`.

    python tools\\fix_center_caption_wrap.py            # chạy thử
    python tools\\fix_center_caption_wrap.py --apply
    python tools\\fix_center_caption_wrap.py --check    # gate, còn dòng quá lề -> exit 1
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

import UnityPy          # noqa: E402
import adv_layout as A  # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "scenario01.centercaption")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

FONT_SIZE = 39.0
CHAR_SPACING = 3.8
BOX_W = 1920.0
SAFE_W = 1764.0            # 1920 - 2 x 78, lề tam giác UL đo trên ảnh Ryujinx

# Ô xác định chắc chắn chạy dưới `[textmode=5]` (đo khoảng cách tới lệnh, không suy diễn).
PLAN = [(71, 344), (71, 345), (71, 346)]

PUNCT = re.compile(r"(?<=[.!?,;:…])\s+")


def width(s):
    return sum(A.glyph_advance(c) + CHAR_SPACING for c in s) * FONT_SIZE / A.POINT_SIZE


def shown(s):
    """Chữ engine thật sự vẽ ở chế độ này: bỏ `「」`."""
    return s.replace("「", "").replace("」", "")


def split_punct(s):
    """Ngắt theo dấu câu, gom tới sát 1764 px. Không cân độ dài — cố ý."""
    lines, cur = [], ""
    for part in PUNCT.split(s):
        cand = (cur + " " + part) if cur else part
        if cur and width(cand) > SAFE_W:
            lines.append(cur)
            cur = part
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def load(path):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name == "TextAsset" and o.read().m_Name == "ScenarioData":
            d = o.read()
            raw = d.m_Script
            if not isinstance(raw, str):
                raw = bytes(raw).decode("utf-8")
            return env, d, raw
    raise SystemExit("không thấy ScenarioData")


def mirror(script, old, new):
    lines, ol, nl = script.split("\n"), old.split("\n"), new.split("\n")
    hits = [k for k in range(len(lines) - len(ol) + 1) if lines[k:k + len(ol)] == ol]
    if len(hits) != 1:
        return None
    lines[hits[0]:hits[0] + len(ol)] = nl
    return "\n".join(lines)


def main():
    env, d, raw = load(BUNDLE)
    bom = "﻿" if raw.startswith("﻿") else ""
    data = json.loads(raw.lstrip("﻿"))
    sid_map = {t["scenarioID"]: i for i, t in enumerate(data["target"])}

    hits, ok = [], []
    for sID, j in PLAN:
        ti = sid_map.get(sID)
        if ti is None:
            print("! không có scenarioID %d" % sID)
            continue
        cur = data["target"][ti]["text"][j]
        segs = shown(cur).split("\n")
        worst = max(width(s) for s in segs)
        if worst <= SAFE_W:
            ok.append((sID, j, len(segs), worst))
            continue
        # dựng lại từ bản đã làm phẳng, để chạy lại sau merge cũng cho cùng kết quả
        flat = " ".join(x.strip() for x in shown(cur).split("\n"))
        new_lines = split_punct(flat)
        if max(width(s) for s in new_lines) > SAFE_W:
            print("!! %d/txt/%04d: ngắt theo dấu câu vẫn còn dòng %.0f px > %.0f — cần rút chữ"
                  % (sID, j, max(width(s) for s in new_lines), SAFE_W))
            for s in new_lines:
                print("      %7.0f px %4.0f%%  %r" % (width(s), 100 * width(s) / SAFE_W, s))
            continue
        pre = "「" if cur.startswith("「") else ""
        suf = "」" if cur.rstrip().endswith("」") else ""
        val = pre + "\n".join(new_lines) + suf
        hits.append((ti, sID, j, cur, val, new_lines))

    for sID, j, n, worst in ok:
        print("=  %d/txt/%04d  %d dòng, rộng nhất %.0f px (%.0f%%) — đạt"
              % (sID, j, n, worst, 100 * worst / SAFE_W))
    for ti, sID, j, cur, val, new_lines in hits:
        flat_w = width(shown(cur).replace("\n", " "))
        print("-> %d/txt/%04d  %.0f px (%.0f%% lề an toàn) -> %d dòng"
              % (sID, j, flat_w, 100 * flat_w / SAFE_W, len(new_lines)))
        for s in new_lines:
            print("      %7.0f px %4.0f%%  %r" % (width(s), 100 * width(s) / SAFE_W, s))

    if CHECK:
        if hits:
            print()
            print("%d ô còn dòng quá lề an toàn %.0f px — chạy `--apply`" % (len(hits), SAFE_W))
            raise SystemExit(1)
        print()
        print("PASS mọi ô trong PLAN đều trong lề an toàn %.0f px" % SAFE_W)
        return

    if not hits:
        print()
        print("không có gì để sửa")
        return

    out = raw

    def enc(x):
        return json.dumps(x, ensure_ascii=False, separators=(",", ":"))

    for ti in sorted({h[0] for h in hits}):
        arr_old = list(data["target"][ti]["text"])
        arr_new = list(arr_old)
        for t2, sID, j, cur, val, _ in [h for h in hits if h[0] == ti]:
            assert arr_new[j] == cur, "text[%d] không như đã đọc" % j
            arr_new[j] = val
        oj, nj = enc(arr_old), enc(arr_new)
        if out.count(oj) != 1:
            raise SystemExit("mảng text[] của target[%d] khớp %d lần" % (ti, out.count(oj)))
        out = out.replace(oj, nj)

    mirrored = failed = 0
    for ti in sorted({h[0] for h in hits}):
        script = cur_s = data["target"][ti]["scriptText"]
        for t2, sID, j, cur, val, _ in [h for h in hits if h[0] == ti]:
            nxt = mirror(cur_s, cur, val)
            if nxt is None:
                failed += 1
            else:
                cur_s = nxt
                mirrored += 1
        if cur_s != script:
            oj, nj = (json.dumps(script, ensure_ascii=False),
                      json.dumps(cur_s, ensure_ascii=False))
            if out.count(oj) != 1:
                raise SystemExit("scriptText target[%d] khớp %d lần" % (ti, out.count(oj)))
            out = out.replace(oj, nj)
    print()
    print("mirror vào scriptText: %d (không khớp verbatim %d)" % (mirrored, failed))

    after = json.loads(out.lstrip("﻿"))
    changed = {(h[0], h[2]) for h in hits}
    for ti, t in enumerate(data["target"]):
        ta = after["target"][ti]
        assert ta["loadLine"] == t["loadLine"], "loadLine đổi"
        assert ta["scriptText_Line"] == t["scriptText_Line"], "scriptText_Line đổi"
        for j, s in enumerate(t["text"]):
            if (ti, j) in changed:
                continue
            assert ta["text"][j] == s, "text[%d] target[%d] đổi ngoài dự kiến" % (j, ti)
    for ti, sID, j, cur, val, _ in hits:
        assert after["target"][ti]["text"][j] == val
        # chỉ được thêm ngắt dòng, chữ không được đổi
        assert re.sub(r"\s+", " ", val).strip() == re.sub(r"\s+", " ", cur).strip(), \
            "chữ đổi ở %d/txt/%d" % (sID, j)
    print("kiểm tra: %d ô đổi, chữ không đổi, loadLine/scriptText_Line nguyên vẹn" % len(hits))

    if not APPLY:
        print()
        print("CHẠY THỬ — thêm --apply để ghi")
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
    for ti, sID, j, cur, val, _ in hits:
        assert rd["target"][ti]["text"][j] == val, "đọc lại %d/txt/%d sai" % (sID, j)
    print("  đọc lại: %d ô khớp" % len(hits))


main()
