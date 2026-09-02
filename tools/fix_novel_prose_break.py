# -*- coding: utf-8 -*-
"""Gỡ ngắt cứng GIỮA CỤM TỪ trong văn xuôi chế độ novel khi dòng đứng trước nó tràn khung.

## Lỗi (ảnh máy thật IMG_7238, 02/09/2026 — `sID=70 text[94]`)

    ―Hôm qua, những gì Kohaku đã dạy tôi là "Công          <- dòng DATA, engine thụt 1 em
    việc tối thiểu" của một Operator (Điều hành viên) và   <- dòng DATA, 1547 px > 1400
  "Kiến                                                    <- TMP ngắt xuống, KHÔNG thụt
    thức cơ bản" về Unlogical.                             <- dòng DATA, lại thụt

Ô novel (`level10` pid 894 `Message(Novel)/NovelText`, rect 1400×720, cỡ 42,
charSpacing 6, wrap BẬT, auto-size TẮT) thụt 1 em cho mỗi dòng CÓ TRONG DỮ LIỆU và
không thụt cho dòng TMP tự ngắt (đo trong `fix_novel_list_wrap.py`). Nên một chỗ
`\\n` viết tay đặt giữa cụm từ chỉ vô hại khi dòng đứng trước nó **vừa khung**:
dòng đó dài quá thì TMP ngắt lại, mẩu thừa (`"Kiến`) rơi xuống đứng lẻ một hàng
thụt ngược, rồi `\\n` kế tiếp lại thụt vào — chữ `Kiến thức` bị xé làm hai hàng lệch
nhau. Đây đúng là lớp lỗi `fix_midphrase_break.py` đã dọn ở thoại ADV, nhưng tool
đó **miễn vùng novel** vì cái thụt lề, và cái thụt lề lại chính là thứ làm lỗi này
lộ rõ hơn ADV.

## Sửa thế nào

Trong tin nhắn nào có (một dòng tràn khung) + (ngắt giữa cụm từ ngay sau nó) thì
**gỡ MỌI chỗ ngắt giữa cụm từ của tin nhắn đó** — nối bằng một dấu cách — và **giữ
ngắt ở ranh giới câu** (`.` `?` `!` `」` `…` `―`). Tin nhắn ấy đằng nào cũng bị TMP
wrap; để lẫn ngắt kiểu khối Nhật (mỗi vế một dòng thụt) với wrap của TMP trong
cùng một đoạn thì không có cách nào cho ra hàng thẳng. Sau khi nối, TMP vẽ nó như
một đoạn văn: dòng đầu thụt 1 em, các dòng sau sát lề — đúng dáng của 803 tin
nhắn một dòng đã quá 1400 px trong cùng chế độ, nên không lạ mắt.

Không nối lại các tin nhắn chỉ có ngắt ở **ranh giới câu** dù câu đầu có tràn:
đuôi câu rơi xuống rồi câu sau thụt vào đọc như hai đoạn văn, là dáng bình thường.
Khảo sát 02/09/2026: 104 tin nhắn novel nhiều dòng có dòng tràn 1400; 13 có dòng
tràn đứng trước một `\\n`; **3** trong số đó ngắt giữa cụm từ — tool này sửa đúng 3.

## Dò từ phía Nhật, chạy lại được sau mỗi lần merge

    tin nhắn j thuộc vùng novel  <=>  loadLine[j] nằm giữa [ノベルモードN開始…] và …終了…
    N = 1 -> Message(Novel) 1400 px ; N = 2 -> Message(Novel2) 1600 px ; N khác: bỏ qua

Bỏ qua mục liệt kê (`fix_novel_list_wrap.py` lo), tin nhắn có ruby (ngắt dòng là
neo cho `Ruby_Text`), tin nhắn còn kana (script test `sID` 0–12). Không đụng
`scriptText_Line` / `loadLine`; `scriptText` được soi theo (`mirror`).

    python tools\\fix_novel_prose_break.py            # chạy thử
    python tools\\fix_novel_prose_break.py --apply
    python tools\\fix_novel_prose_break.py --check    # chốt sau merge, lỗi -> exit 1

`check_layout_breaks.py` sẽ báo MẤT ngắt dòng ở 3 ô này — đúng dự kiến, giống
`fix_midphrase_break.py`.  Backup: `_backup\\scenario01.novelprose`.
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

import UnityPy   # noqa: E402
from adv_layout import ADV, PLAYER_MEASURE   # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "scenario01.novelprose")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

# cùng mô hình với fix_novel_list_wrap.py — đã đo trên ảnh máy thật
POINT_SIZE, FONT_SIZE, CHAR_SPACING = 58.0, 42.0, 6.0
ENGINE_INDENT = 42.0
BOX_BY_MODE = {"1": 1400.0, "2": 1600.0}     # Message(Novel) / Message(Novel2)

NOVEL_ON = re.compile(r"^\[ノベルモード([^\]]*?)開始")
NOVEL_OFF = re.compile(r"^\[ノベルモード[^\]]*終了")
JP_MARKER = re.compile(r"^(?:[０-９]+[．.]|[・※＊*])")
KANA = re.compile(r"[ぁ-ゖァ-ヺ]")
TAG = re.compile(r"\[[^\[\]\n]*\]")
RUBY = re.compile(r"\[([^\[\]\n']*?)'([^\[\]\n]*?)\]")
DIC = re.compile(r"\[dic\b[^\[\]\n]*?text=([^\[\]\n]*?)\]")

END_PUNCT = ".?!。？！」』…―—"
CLOSERS = "\"”)）'』」"


def shown(s):
    """Chữ thật hiện trên màn: ruby vẽ phần gốc, [dic] vẽ phần text=, lệnh khác không vẽ."""
    def rep(m):
        tag = m.group(0)
        d = DIC.fullmatch(tag)
        if d:
            inner = d.group(1)
            r = RUBY.fullmatch("[" + inner + "]")
            return r.group(1) if r else inner
        r = RUBY.fullmatch(tag)
        if r:
            return r.group(1)
        return PLAYER_MEASURE if tag == "[主人公]" else ""
    return TAG.sub(rep, s)


def width(s):
    d = shown(s)
    adv = sum(ADV.get(ord(c), 58.0) for c in d) * FONT_SIZE / POINT_SIZE
    return adv + max(len(d) - 1, 0) * CHAR_SPACING * FONT_SIZE / 100.0


def sentence_end(line):
    """Ngắt sau dòng này là ngắt ở ranh giới câu (giữ), không phải giữa cụm từ (gỡ)."""
    s = line.rstrip()
    if not s:
        return True
    if s[-1] in END_PUNCT:
        return True
    return s[-1] in CLOSERS and len(s) > 1 and s[-2] in END_PUNCT


def offenders(lines, box):
    """Chỉ số các dòng tràn khung mà chỗ ngắt ngay sau nó nằm giữa cụm từ."""
    return [k for k, l in enumerate(lines[:-1])
            if width(l) + ENGINE_INDENT > box and not sentence_end(l)]


def join_midphrase(lines):
    out = [lines[0]]
    for l in lines[1:]:
        if sentence_end(out[-1]):
            out.append(l)
        else:
            out[-1] = out[-1].rstrip() + " " + l.lstrip("　 ")
    return out


def tmp_preview(par, box):
    """Dự đoán TMP wrap một đoạn: dòng đầu mất 1 em cho thụt engine, dòng sau trọn khung."""
    rows, cur, limit = [], "", box - ENGINE_INDENT
    for w in par.split(" "):
        cand = w if not cur else cur + " " + w
        if cur and width(cand) > limit:
            rows.append(cur)
            cur, limit = w, box
        else:
            cur = cand
    if cur:
        rows.append(cur)
    return rows


def novel_mode_of(SL):
    """Với mỗi dòng script: N của khối [ノベルモードN開始…] đang mở, hoặc None."""
    cur, modes = None, []
    for l in SL:
        s = l.strip()
        m = NOVEL_ON.match(s)
        if m:
            cur = m.group(1)
        elif NOVEL_OFF.match(s):
            cur = None
        modes.append(cur)
    return modes


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


def mirror(script, old, new, expect=1):
    """Soi sang bản sao `scriptText`; `expect` = số ô mang đúng chuỗi này đang cùng sửa."""
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

    hits, seen, skipped_mode, n_multi = [], {}, {}, 0
    for ti, t in enumerate(data["target"]):
        SL, LL, TX = t["scriptText_Line"], t["loadLine"], t["text"]
        modes = novel_mode_of(SL)
        for j, ln in enumerate(LL):
            if j >= len(TX) or ln >= len(SL) or modes[ln] is None:
                continue
            if JP_MARKER.match(SL[ln]):
                continue                       # mục liệt kê — fix_novel_list_wrap.py
            cur = TX[j]
            lines = cur.split("\n")
            if len(lines) < 2:
                continue
            n_multi += 1
            box = BOX_BY_MODE.get(modes[ln])
            if box is None:
                skipped_mode[modes[ln]] = skipped_mode.get(modes[ln], 0) + 1
                continue
            if KANA.search(shown(cur)) or RUBY.search(cur):
                continue
            bad = offenders(lines, box)
            if not bad:
                continue
            new_lines = join_midphrase(lines)
            val = "\n".join(new_lines)
            assert val != cur
            assert not offenders(new_lines, box), "sau khi nối vẫn còn dòng tràn trước ngắt giữa cụm từ"
            assert all(s.count("[") == s.count("]") for s in new_lines)
            hits.append((ti, t["scenarioID"], j, ln, modes[ln], box, cur, val, bad))
            seen.setdefault(cur, []).append((ti, j))

    print("tin nhắn novel nhiều dòng (không phải mục liệt kê): %d — %d ô có dòng tràn khung đứng"
          " trước một chỗ ngắt giữa cụm từ" % (n_multi, len(hits)))
    if skipped_mode:
        print("  bỏ qua vì chưa đo widget: %s" % ", ".join(
            "ノベルモード%s: %d ô" % (k, v) for k, v in sorted(skipped_mode.items())))
    for ti, sid, j, ln, md, box, cur, val, bad in hits:
        print("\n=== sID=%s text[%d]  loadLine=%d  ノベルモード%s (khung %.0f)  %d -> %d dòng"
              % (sid, j, ln, md, box, len(cur.split("\n")), len(val.split("\n"))))
        for k, l in enumerate(cur.split("\n")):
            w = width(l) + ENGINE_INDENT
            print("   %s %6.0f  %s" % ("!!" if k in bad else "  ", w, l))
        print("   -> sau khi nối, TMP sẽ vẽ:")
        for par in val.split("\n"):
            for r, row in enumerate(tmp_preview(par, box)):
                print("      %s%s" % ("  " if r == 0 else "", row))

    if CHECK:
        if hits:
            print("\n%d ô lỗi — chạy `python tools\\fix_novel_prose_break.py --apply`" % len(hits))
            raise SystemExit(1)
        print("\nPASS không ô novel nào có dòng tràn khung đứng trước ngắt giữa cụm từ")
        return
    if not hits:
        print("\nkhông có gì để sửa")
        return

    # thay từng chuỗi; chuỗi trùng phải khớp ĐÚNG số ô đang cùng sửa
    out, done = raw, set()
    for ti, sid, j, ln, md, box, cur, val, bad in hits:
        if cur in done:
            continue
        old_j, new_j = json.dumps(cur, ensure_ascii=False), json.dumps(val, ensure_ascii=False)
        n = out.count(old_j)
        if n != len(seen[cur]):
            raise SystemExit("sID=%s text[%d]: chuỗi cũ khớp %d lần, đang sửa %d ô"
                             % (sid, j, n, len(seen[cur])))
        out = out.replace(old_j, new_j)
        done.add(cur)

    mirrored = failed = 0
    for ti in sorted({h[0] for h in hits}):
        script = cur_s = data["target"][ti]["scriptText"]
        groups = {}
        for h in [x for x in hits if x[0] == ti]:
            groups.setdefault(h[6], []).append(h)
        for cur, g in groups.items():
            nxt = mirror(cur_s, cur, g[0][7], expect=len(g))
            if nxt is None:
                failed += len(g)
            else:
                cur_s, mirrored = nxt, mirrored + len(g)
        if cur_s != script:
            oj, nj = json.dumps(script, ensure_ascii=False), json.dumps(cur_s, ensure_ascii=False)
            if out.count(oj) != 1:
                raise SystemExit("scriptText target[%d] khớp %d lần" % (ti, out.count(oj)))
            out = out.replace(oj, nj)
    print("\nmirror vào scriptText: %d (không khớp verbatim %d)" % (mirrored, failed))

    after = json.loads(out.lstrip("﻿"))
    changed = {(h[0], h[2]) for h in hits}
    for ti, t in enumerate(data["target"]):
        ta = after["target"][ti]
        assert ta["loadLine"] == t["loadLine"], "loadLine đổi ở target[%d]" % ti
        assert ta["scriptText_Line"] == t["scriptText_Line"], "scriptText_Line đổi ở target[%d]" % ti
        assert ta["selText"] == t["selText"], "selText đổi ở target[%d]" % ti
        assert len(ta["text"]) == len(t["text"])
        for j, s in enumerate(t["text"]):
            if (ti, j) in changed:
                continue
            assert ta["text"][j] == s, "text[%d] target[%d] đổi ngoài dự kiến" % (j, ti)
    flat = lambda s: " ".join(x.strip("　 ") for x in s.split("\n"))   # noqa: E731
    for ti, sid, j, ln, md, box, cur, val, bad in hits:
        assert after["target"][ti]["text"][j] == val
        assert flat(val) == flat(cur), "chữ đổi ở sID=%s text[%d]" % (sid, j)
    print("kiểm tra: chỉ %d tin nhắn đổi, chữ không đổi, loadLine/scriptText_Line/selText nguyên vẹn"
          % len(hits))

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
    for ti, sid, j, ln, md, box, cur, val, bad in hits:
        assert rd["target"][ti]["text"][j] == val, "đọc lại sID=%s text[%d] không khớp" % (sid, j)
    for ti, t in enumerate(data["target"]):
        assert rd["target"][ti]["loadLine"] == t["loadLine"]
        assert rd["target"][ti]["scriptText_Line"] == t["scriptText_Line"]
    print("  đọc lại: %d tin nhắn khớp, loadLine/scriptText_Line nguyên vẹn" % len(hits))


if __name__ == "__main__":
    main()
