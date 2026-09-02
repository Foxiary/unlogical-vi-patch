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

**Tầng hai, thêm 02/09/2026: mệnh đề tự nó quá lề thì ngắt tiếp theo từ.** Ba ô không có
dấu câu nào nằm đúng chỗ — `85/txt/0767` là một mệnh đề liền 2556 px, `99/txt/0214` 2088
px, `99/txt/0215` còn 1954 px sau khi đã tách ở dấu phẩy. Dấu câu không với tới thì lựa
chọn còn lại là ngắt theo từ, chứ không phải bỏ mặc: rect rộng 1920 nên TMP vẫn wrap các
ô này, chỉ là wrap ở **1920** — tức dòng chạy hết mép màn, đè qua watermark, đúng cái lỗi
tool này sinh ra để chặn. Ngắt theo từ ở 1764 chỉ đổi *chỗ* ngắt, không thêm dòng nào mà
TMP đã không tự thêm. Tầng một vẫn chạy trước, nên ô nào dấu câu lo được thì tầng hai
không đụng tới.

Tầng hai **cân độ dài**, ngược với tầng một, và có lý do: ở đây không còn dấu câu nào để
trùng nhịp bản gốc, nên thứ duy nhất còn chọn được là chỗ gãy đỡ chướng nhất. Gom tham
lam đã thử và bỏ — nó dồn hết chữ lên dòng đầu rồi để lại dòng cụt, và cắt đúng giữa từ
ghép: `99/txt/0214` ra 1707 px + 365 px với `địa` / `điểm` nằm hai dòng. Cân bằng chia
2088 px thành hai dòng ~1044 px, dôi chỗ nên mối ngắt tự rơi ra ranh giới thoáng hơn.
Không có bảng từ ghép nào ở đây — cân bằng chỉ làm xác suất cắt trúng thấp đi, nên **ô
nào rơi vào tầng hai vẫn nên liếc mắt đọc lại một lượt**.

**Tự dò lại chỗ ngắt từ câu chữ hiện tại**, nên chạy lại được sau mỗi merge (sheet làm
phẳng `\\n` mỗi vòng) — tool không ghi chuỗi đích ở đâu cả.

**Quét cả chế độ, bỏ danh sách ô viết tay (02/09/2026).** Câu hỏi bỏ ngỏ ở đây trước đó
— "engine reset `textmode` ở lệnh nào" — có đáp án: **`[ノベルモード…終了…]`**, đúng họ lệnh
mà `fix_novel_list_wrap.py` đang dùng. Thấy rõ ở `sID 92` line 168..178: khối mở bằng
`[textmode=5]`, đóng bằng `[ノベルモード1終了]`, không hề có `[textmode=0]`. Lấy nó làm điểm
kết khối thì **cả 26 khối `[textmode=5]` đều đóng gọn trong 6–28 dòng script**; hai khối
từng dài 1905 và 3774 dòng (`sID 71` line 1319, `sID 92` line 168) biến mất, cùng với ca
"cách 2593 dòng" từng ghi ở đây.

Khối = từ `[textmode=5]` tới `[textmode=N]` **hoặc** `[ノベルモード…終了…]` kế tiếp; ô nào có
`loadLine` rơi vào khoảng đó là caption. Ra **41 ô** trên toàn build, thay cho `PLAN` 3 ô.
Chỉ nhận dòng lệnh thật (`strip()` mở đầu bằng `[`) — script có cả `;//[ノベルモード…]` là
comment.

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
BACKUP = os.path.join(ROOT, "_backup", "scenario01.centercaption2")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

FONT_SIZE = 39.0
CHAR_SPACING = 3.8
BOX_W = 1920.0
SAFE_W = 1764.0            # 1920 - 2 x 78, lề tam giác UL đo trên ảnh Ryujinx

# Khối caption: `[textmode=5]` … tới `[textmode=N]` hoặc `[ノベルモード…終了…]` kế tiếp.
TEXTMODE = re.compile(r"^\[textmode[=\s]*([0-9]+)\]")
NOVEL_OFF = re.compile(r"^\[ノベルモード[^\]]*終了")


NBLOCK = [0]


def caption_cells(t):
    """Chỉ số mọi tin nhắn của một target nằm dưới `[textmode=5]`."""
    L = t["scriptText_Line"]
    by_line = {}
    for j, ln in enumerate(t["loadLine"]):
        by_line.setdefault(ln, []).append(j)
    out = []
    for i, ln in enumerate(L):
        m = TEXTMODE.match(ln.strip())
        if not m or m.group(1) != "5":
            continue
        NBLOCK[0] += 1
        end = len(L)
        for k in range(i + 1, len(L)):
            s = L[k].strip()
            if TEXTMODE.match(s) or NOVEL_OFF.match(s):
                end = k
                break
        out += [j for line, js in by_line.items() if i <= line < end for j in js]
    return sorted(set(out))

PUNCT = re.compile(r"(?<=[.!?,;:…])\s+")


def width(s):
    return sum(A.glyph_advance(c) + CHAR_SPACING for c in s) * FONT_SIZE / A.POINT_SIZE


def shown(s):
    """Chữ engine thật sự vẽ ở chế độ này: bỏ `「」`."""
    return s.replace("「", "").replace("」", "")


def _greedy(words, limit):
    out, cur = [], ""
    for w in words:
        cand = (cur + " " + w) if cur else w
        if cur and width(cand) > limit:
            out.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out


def wrap_words(s):
    """Dự phòng: mệnh đề tự nó đã quá lề -> chia theo từ, **cân độ dài**.

    Số dòng lấy bằng đúng số dòng tối thiểu (gom tham lam ở 1764), rồi dò nhị phân
    bề rộng nhỏ nhất vẫn giữ được ngần ấy dòng. Cùng số dòng, dòng ngắn hơn = mối
    ngắt cân hơn, không còn dòng cụt."""
    words = s.split(" ")
    k = len(_greedy(words, SAFE_W))
    if k <= 1:
        return [s]
    lo, hi = max(width(w) for w in words), SAFE_W
    while hi - lo > 1:
        mid = (lo + hi) / 2
        if len(_greedy(words, mid)) <= k:
            hi = mid
        else:
            lo = mid
    return _greedy(words, hi)


def split_punct(s):
    """Ngắt theo dấu câu, gom tới sát 1764 px. Không cân độ dài — cố ý.

    Mệnh đề nào một mình đã vượt lề thì chuyển sang `wrap_words`."""
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
    out = []
    for ln in lines:
        out += wrap_words(ln) if width(ln) > SAFE_W else [ln]
    return out


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


def mirror(script, old, new, expect=1):
    """Soi sang `scriptText`. `expect` = số ô y hệt nhau đang cùng được sửa: cảnh
    Angelica ở prologue lặp lại 3 lần với đúng một câu, đòi khớp đúng 1 lần thì bỏ cả ba."""
    lines, ol, nl = script.split("\n"), old.split("\n"), new.split("\n")
    hits = [k for k in range(len(lines) - len(ol) + 1) if lines[k:k + len(ol)] == ol]
    if len(hits) != expect:
        return None
    for k in reversed(hits):
        lines[k:k + len(ol)] = nl
    return "\n".join(lines)


def main():
    env, d, raw = load(BUNDLE)
    bom = "﻿" if raw.startswith("﻿") else ""
    data = json.loads(raw.lstrip("﻿"))

    hits, ok = [], []
    for ti, t in enumerate(data["target"]):
        sID = t["scenarioID"]
        for j in caption_cells(t):
            cur = t["text"][j]
            if not cur.strip():
                continue
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
            # ngắt không được rơi vào giữa `[...]`: một newline thật trong tham số lệnh
            # là kết thúc dòng lệnh (xem CLAUDE.md).
            if any(s.count("[") != s.count("]") for s in new_lines):
                print("!! %d/txt/%04d: chỗ ngắt rơi vào giữa `[...]` — bỏ qua" % (sID, j))
                continue
            pre = "「" if cur.startswith("「") else ""
            suf = "」" if cur.rstrip().endswith("」") else ""
            val = pre + "\n".join(new_lines) + suf
            hits.append((ti, sID, j, cur, val, new_lines))

    print("quét: %d ô caption trong %d khối — %d ô trong lề, %d ô cần ngắt"
          % (len(ok) + len(hits), NBLOCK[0], len(ok), len(hits)))
    for sID, j, n, worst in sorted(ok, key=lambda x: -x[3]):
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
        print("PASS cả %d ô caption đều trong lề an toàn %.0f px" % (len(ok), SAFE_W))
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
        groups = {}
        for h in [x for x in hits if x[0] == ti]:
            groups.setdefault(h[3], []).append(h)      # gom các ô có chuỗi cũ y hệt
        for cur, g in groups.items():
            nxt = mirror(cur_s, cur, g[0][4], expect=len(g))
            if nxt is None:
                failed += len(g)
            else:
                cur_s = nxt
                mirrored += len(g)
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
