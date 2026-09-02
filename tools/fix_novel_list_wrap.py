# -*- coding: utf-8 -*-
"""Hard-wrap every numbered / bulleted list block in novel mode, JP hanging indent.

**Re-runnable, and meant to be re-run after every sheet merge** — a merge writes
`text[]` from the sheet, and the sheet cannot carry either the hard breaks or the
indents (see the README section), so it flattens this work every time.  Nothing
here is keyed to a message index: the blocks are found from the JAPANESE side,
which never changes.

The bug being fixed: the novel box (`level10` pid 894 `Message(Novel)/NovelText`,
rect 1400x720, size 42, charSpacing 6, wrap ON, auto-size OFF) draws every line
that exists **in the data** one em to the right — the engine's own paragraph
indent — and gives a line **TMP** wrapped nothing.  So an over-long data line
comes back with its tail jutting one em to the LEFT:

    5. Không được tiết lộ thông tin làm ảnh hưởng đến
thắng bại của trò chơi cho Player.          <- 1 em further left

Measured on a photo of the real screen (adjacent lines, so the perspective
cancels): 41 canvas px = 0.98 em.  The JP data never hits it — every rule is
hard-wrapped and its continuations start with two full-width spaces, so 1 em
(engine) + 2 em (data) puts the body of every line on one column.

Detection, all from the untranslated script (`scriptText_Line`, indexed by
`loadLine`, both of which this tool never writes):

    message j is a list item  <=>  scriptText_Line[loadLine[j]] starts with
                                   １．…９． or ・ ※ ＊ *
                              and  that line sits between
                                   [ノベルモード…開始…] and [ノベルモード…終了…]

The hanging prefix is chosen per item so it matches the marker the translation
actually uses (`5. ` is 64.6 px, `・` is 44.5, `* ` is 38.3 — full-width digits
would be 89), out of `　`, `　 `, `　　`, and runs of spaces.

Width model — advance scales by fontSize/pointSize, characterSpacing by
fontSize/100, trailing spacing does not count (see `unlogical-text-overflow`):

    W = sum(advance) * 42/58 + (n-1) * 6 * 42/100

and the wrap limit is `(1400 - 42) * 0.99`: minus the engine indent because it is
inserted into the string and therefore eats wrap width, times 0.99 because the
model's error against a real screen is under 2% and 7 px of headroom is thinner
than that.

**Where the break falls also matters in the SAVE/LOAD summary box (2026-09-02).**
`SaveDataDetail/Text (TMP)` draws the same string in 731.5 px at 27 pt, spacing
8.4, three lines then `…` (see `fix_save_summary_clip.py`).  A greedy first line
tuned to 1344 px wraps there and leaves its last word alone on a line right
before our hard break (IMG_7244: `3. Cả Suzuno Kanna và Munakata Kai sẽ` /
`cùng` / `　 nhau loại bỏ …`).  So `reflow()` now enumerates every split into the
same minimal number of lines that fits 1344 and picks by: fewest summary lines
with the name measured at its upper bound, then fewest with the default name,
then the greediest (longest first line, then second, …).  Two guards on every
candidate: no line may leave a quote or bracket open, and no break may fall
between the two halves of a pair in `NO_SPLIT` — a hand-curated list built from
the 445 adjacent-word pairs these 29 items contain (`trò chơi`, `đăng xuất`,
`Game Master`, …).  The old greedy pass had been splitting `đăng / xuất`,
`kẻ / thù`, `Game / Master`.  The line count of each item does not change, so
`check_layout_breaks` sees no loss.

    python tools\\fix_novel_list_wrap.py            # chạy thử
    python tools\\fix_novel_list_wrap.py --apply
    python tools\\fix_novel_list_wrap.py --check    # chốt sau merge, lỗi -> exit 1

`--check` fails on real overflow (`W + 42 > 1400`) or on a continuation line with
no indent, so it belongs next to `check_scripts.py` in the post-merge gate.
"""
import io
import itertools
import json
import math
import os
import re
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402
import adv_layout as A   # noqa: E402
from adv_layout import ADV   # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "scenario01.novellist")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

POINT_SIZE, FONT_SIZE, CHAR_SPACING = 58.0, 42.0, 6.0
BOX, ENGINE_INDENT, SAFETY = 1400.0, 42.0, 0.99
LIMIT = (BOX - ENGINE_INDENT) * SAFETY

NOVEL_ON = re.compile(r"^\[ノベルモード[^\]]*開始")
NOVEL_OFF = re.compile(r"^\[ノベルモード[^\]]*終了")
JP_MARKER = re.compile(r"^(?:[０-９]+[．.]|[・※＊*])")
VN_MARKER = re.compile(r"^(?:\d+[.)]\s*|[・※＊*]\s*)")
# Chỉ tiền tố mở đầu bằng `　`: bản JP có 17.299 dòng như vậy và chúng hiển thị
# đúng, tức U+3000 chắc chắn không bị engine cắt. Space ASCII đầu dòng thì chưa
# có bằng chứng nào trong game này, đừng đánh cược. Sai số lớn nhất còn 5,6 px.
PREFIXES = ["　", "　 ", "　  ", "　　"]

TAG = re.compile(r"\[[^\[\]\n]*\]")
RUBY = re.compile(r"\[([^\[\]\n']*?)'([^\[\]\n]*?)\]")


# Bề rộng đo cho `[主人公]`. Đo tag thành 0 px là sai 161 px mỗi lần xuất hiện —
# đủ để đẩy một từ xuống dòng riêng mà `--check` vẫn báo PASS (khối
# `sID=89 text[6]` đã dính đúng lỗi này).
#
# Và đo theo tên mặc định `Kanna` (161,5 px) cũng chưa đủ: ô nhập tên cho tối đa
# **6 ký tự Latin**, mà `W` là glyph rộng nhất (60,3 adv — hơn cả kana toàn rộng
# 58), nên cận trên thật sự là `WWWWWW` = 277,2 px, tức +115,7 px so với `Kanna`.
# Dòng phải vừa khung với BẤT KỲ tên nào người chơi đặt, nên đo theo cận trên.
from adv_layout import PLAYER_MEASURE   # noqa: E402  (= "W" * 6)


def shown(s):
    """Chữ thật hiện trên màn: ruby chỉ vẽ phần gốc, lệnh khác không vẽ gì."""
    def rep(m):
        r = RUBY.fullmatch(m.group(0))
        if r:
            return r.group(1)
        return PLAYER_MEASURE if m.group(0) == "[主人公]" else ""
    return TAG.sub(rep, s)


def width(s):
    d = shown(s)
    adv = sum(ADV.get(ord(c), 58.0) for c in d) * FONT_SIZE / POINT_SIZE
    return adv + max(len(d) - 1, 0) * CHAR_SPACING * FONT_SIZE / 100.0


def contrib(s):
    """Bề rộng một đoạn đứng đầu dòng và còn chữ theo sau (mọi ký tự đều tính spacing)."""
    d = shown(s)
    return (sum(ADV.get(ord(c), 58.0) for c in d) * FONT_SIZE / POINT_SIZE
            + len(d) * CHAR_SPACING * FONT_SIZE / 100.0)


def pick_prefix(marker):
    """Tiền tố thụt treo sát nhất với bề rộng của dấu đầu mục."""
    want = contrib(marker)
    return min(PREFIXES, key=lambda p: abs(contrib(p) - want))


# Ô tóm tắt thẻ SAVE/LOAD (`level19` SaveDataDetail/Text (TMP), xem fix_save_summary_clip.py)
# vẽ CÙNG chuỗi này trong 731,5 px, cỡ 27, charSpacing 8,4, 3 dòng rồi cắt `…`. Dòng đầu
# gom tham lam tới 1344 px wrap ở đó và để chữ cuối đứng lẻ một hàng ngay trước chỗ ngắt
# thụt treo (ảnh IMG_7244). Nên trong mọi cách chia ra cùng số dòng, chọn cách ít tốn dòng
# ở ô tóm tắt nhất — đo tên theo cận trên trước, tên mặc định sau — rồi mới tham lam.
SAVE_FS, SAVE_CS, SAVE_W = 27.0, 8.4, 738.0 - 6.5
MAX_COMBOS = 200000
BRACKETS = [("“", "”"), ("「", "」"), ("『", "』"), ("(", ")"), ("（", "）")]
# Từ ghép / tên riêng không được tách hai dòng — soát tay từ 445 cặp từ liền nhau của 29
# khối luật (02/09/2026). Không có bảng này thì tối ưu theo ô tóm tắt sẵn sàng cắt
# `trò / chơi`, `hoàn / toàn`, `bất / kỳ`; tham lam cũ cũng đã cắt `đăng / xuất`, `kẻ / thù`,
# `Game / Master`. Thêm mục mới thì thêm vào đây, viết thường, bỏ dấu câu và ngoặc kép.
NO_SPLIT = {
    ("ảnh", "hưởng"), ("bất", "kỳ"), ("bắt", "đầu"), ("bốc", "cháy"), ("buộc", "phải"),
    ("cá", "tính"), ("câu", "hỏi"), ("chiến", "thắng"), ("chỉ", "định"), ("chỉ", "số"),
    ("cho", "đến"), ("còn", "lại"), ("cùng", "nhau"), ("dân", "thường"), ("duy", "nhất"), ("đăng", "xuất"),
    ("địa", "điểm"), ("điều", "khiển"), ("điểm", "số"), ("đóng", "vai"), ("đối", "đầu"),
    ("đối", "tượng"), ("đòn", "đánh"), ("đã", "định"), ("giao", "lưu"), ("giải", "trí"),
    ("giới", "hạn"), ("hiển", "thị"), ("hiệu", "quả"), ("hoàn", "thành"), ("hoàn", "toàn"),
    ("học", "hỏi"), ("học", "tập"), ("hỏa", "lực"), ("hung", "thủ"), ("hệ", "thống"),
    ("kết", "thúc"), ("kẻ", "thua"), ("kẻ", "thù"), ("khoang", "treo"), ("kỹ", "năng"),
    ("loại", "bỏ"), ("màn", "hình"), ("mệnh", "lệnh"), ("mục", "tiêu"), ("năng", "lực"),
    ("ngưng", "đọng"), ("người", "chơi"), ("nhà", "vua"), ("nhanh", "chóng"), ("nội", "dung"),
    ("phân", "định"), ("phát", "sinh"), ("phản", "ánh"), ("phòng", "giải"), ("quy", "tắc"),
    ("quyết", "định"), ("riêng", "biệt"), ("sai", "sót"), ("sát", "hại"), ("sát", "thương"),
    ("sân", "khấu"), ("số", "hiệu"), ("số", "lần"), ("số", "điểm"), ("sống", "sót"),
    ("sử", "dụng"), ("sự", "cố"), ("tham", "gia"), ("thay", "đổi"), ("theo", "dõi"),
    ("thoát", "khỏi"), ("thông", "tin"), ("thời", "gian"), ("thắng", "bại"), ("thần", "ẩn"),
    ("thực", "hiện"), ("thực", "tế"), ("thường", "dân"), ("tiến", "độ"), ("tiến", "trình"),
    ("tiết", "lộ"), ("tiềm", "thức"), ("tích", "lũy"), ("tình", "trạng"), ("tìm", "kiếm"),
    ("tối", "đa"), ("tổng", "số"), ("trở", "nên"), ("trở", "thành"), ("trở", "xuống"),
    ("trưởng", "thành"), ("trả", "lời"), ("trò", "chơi"), ("tuyển", "chọn"), ("tuyệt", "đối"),
    ("tương", "thích"), ("tương", "ứng"), ("tấn", "công"), ("tăng", "lên"), ("tử", "vong"),
    ("vô", "hiệu"), ("xem", "xét"), ("xâm", "nhập"), ("xúc", "xắc"), ("xử", "thua"),
    ("ý", "thức"),
    # tên riêng, số kèm đơn vị
    ("game", "master"), ("munakata", "kai"), ("nagamori", "ran"), ("suzuno", "[主人公]"),
    ("round", "3"), ("10", "giây"), ("3", "người"), ("6", "người"), ("con", "xúc"),
}


def norm(w):
    return w.strip("\"“”「」『』()（）,.;:!?―…").lower()


def split_ok(parts):
    """Hai chốt: không dòng nào để ngoặc / ngoặc kép mở dở, không tách cặp trong NO_SPLIT."""
    for p in parts:
        if p.count('"') % 2:
            return False
        for o, c in BRACKETS:
            if p.count(o) != p.count(c):
                return False
    for a, b in zip(parts, parts[1:]):
        last = norm(a.split(" ")[-1])
        first = norm(b.lstrip("　 ").split(" ")[0])
        if (last, first) in NO_SPLIT:
            return False
    return True


def save_lines(parts, upper):
    """Số dòng các phần này chiếm trong ô tóm tắt thẻ SAVE (mô hình adv_layout).

    `upper=True` đo `[主人公]` theo cận trên `WWWWWW` (luật chung của repo), `False`
    theo tên mặc định — dùng làm tiêu chí phụ, để một cách chia tốt hơn cho tên
    mặc định vẫn được chọn khi cận trên hoà nhau."""
    old_cs, old_pm = A.CHAR_SPACING, A.PLAYER_MEASURE
    A.CHAR_SPACING = SAVE_CS * A.POINT_SIZE / 100.0
    A.PLAYER_MEASURE = PLAYER_MEASURE if upper else A.DEFAULT_PLAYER_NAME
    try:
        return sum(max(1, len(A.wrap(p, SAVE_FS, limit=SAVE_W))) for p in parts)
    finally:
        A.CHAR_SPACING, A.PLAYER_MEASURE = old_cs, old_pm


def greedy(words, prefix):
    out, cur = [], ""
    for w in words:
        cand = w if not cur else cur + " " + w
        if cur and width(cand) > LIMIT:
            out.append(cur)
            cur = prefix + w
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out


def reflow(text):
    """Cùng số dòng với gom tham lam; trong các cách chia hợp lệ, chọn theo thứ tự:
    ít dòng nhất ở ô tóm tắt (tên cận trên), ít dòng nhất ở ô tóm tắt (tên mặc định),
    rồi tham lam nhất (dòng 1 dài nhất, rồi dòng 2, …). Không cách nào qua hai chốt
    thì quay về tham lam như cũ."""
    first = text.split("\n")[0]
    m = VN_MARKER.match(first)
    if not m:
        return None, None
    prefix = pick_prefix(m.group(0))
    flat = " ".join(l.lstrip("　 ") for l in text.split("\n"))
    words = [w for w in flat.split(" ") if w]
    base = greedy(words, prefix)
    k = len(base)
    if k >= 2 and math.comb(len(words) - 1, k - 1) <= MAX_COMBOS:
        best = None
        for cuts in itertools.combinations(range(1, len(words)), k - 1):
            b = (0,) + cuts + (len(words),)
            parts = [" ".join(words[x:y]) for x, y in zip(b, b[1:])]
            parts = [parts[0]] + [prefix + p for p in parts[1:]]
            if any(width(p) > LIMIT for p in parts) or not split_ok(parts):
                continue
            key = (save_lines(parts, True), save_lines(parts, False),
                   tuple(-width(p) for p in parts))
            if best is None or key < best[0]:
                best = (key, parts)
        if best is not None:
            return "\n".join(best[1]), prefix
    return "\n".join(base), prefix


def find_blocks(data):
    """Mọi tin nhắn liệt kê trong vùng novel, dò bằng script Nhật."""
    blocks = []
    for ti, t in enumerate(data["target"]):
        SL, LL = t["scriptText_Line"], t["loadLine"]
        inside, novel = False, []
        for l in SL:
            if NOVEL_ON.match(l):
                inside = True
            elif NOVEL_OFF.match(l):
                inside = False
            novel.append(inside)
        for j, ln in enumerate(LL):
            if ln < len(SL) and novel[ln] and JP_MARKER.match(SL[ln]):
                blocks.append((ti, t["scenarioID"], j))
    return blocks


def violations(text):
    lines = text.split("\n")
    bad = []
    for k, l in enumerate(lines):
        if width(l) + ENGINE_INDENT > BOX:
            bad.append("dòng %d tràn khung (%.0f > %.0f)" % (k + 1, width(l) + ENGINE_INDENT, BOX))
        if k and not l.startswith(("　", " ")):
            bad.append("dòng %d thiếu thụt treo" % (k + 1))
    return bad


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


def mirror_scripttext(script, old, new):
    """Đổi khối dòng tương ứng trong bản sao `scriptText`. None nếu không khớp chắc chắn."""
    lines, old_l, new_l = script.split("\n"), old.split("\n"), new.split("\n")
    hits = [k for k in range(len(lines) - len(old_l) + 1) if lines[k:k + len(old_l)] == old_l]
    if len(hits) != 1:
        return None
    k = hits[0]
    lines[k:k + len(old_l)] = new_l
    return "\n".join(lines)


def main():
    env, d, raw = load(BUNDLE)
    bom = "﻿" if raw.startswith("﻿") else ""
    data = json.loads(raw.lstrip("﻿"))
    blocks = find_blocks(data)
    print("khối liệt kê trong chế độ novel: %d  (khung %.0f, thụt engine %.0f, giới hạn %.0f)"
          % (len(blocks), BOX, ENGINE_INDENT, LIMIT))

    if CHECK:
        bad = 0
        for ti, sid, j in blocks:
            v = violations(data["target"][ti]["text"][j])
            if v:
                bad += 1
                print("  FAIL sID=%s text[%d]: %s" % (sid, j, "; ".join(v)))
                print("        %r" % data["target"][ti]["text"][j].split("\n")[0][:60])
        if bad:
            print("\n%d/%d khối sai — chạy `python tools\\fix_novel_list_wrap.py --apply`"
                  % (bad, len(blocks)))
            raise SystemExit(1)
        print("PASS cả %d khối đều vừa khung và có thụt treo" % len(blocks))
        return

    out, plan, skipped = raw, [], []
    scripts = {}
    for ti, sid, j in blocks:
        old = data["target"][ti]["text"][j]
        new, prefix = reflow(old)
        if new is None:
            skipped.append((sid, j, "không nhận ra dấu đầu mục"))
            continue
        if new == old:
            continue
        old_j, new_j = json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False)
        if out.count(old_j) != 1:
            skipped.append((sid, j, "chuỗi cũ khớp %d lần" % out.count(old_j)))
            continue
        out = out.replace(old_j, new_j)
        scripts.setdefault(ti, []).append((old, new))
        plan.append((ti, sid, j, old, new, prefix))

    # bản sao `scriptText` — không ai index tới nó, nhưng để lệch là để lại bẫy
    mirrored = mirror_failed = 0
    for ti, pairs in scripts.items():
        script = data["target"][ti]["scriptText"]
        cur = script
        for old, new in pairs:
            nxt = mirror_scripttext(cur, old, new)
            if nxt is None:
                mirror_failed += 1
            else:
                cur = nxt
                mirrored += 1
        if cur != script:
            old_j, new_j = (json.dumps(script, ensure_ascii=False),
                            json.dumps(cur, ensure_ascii=False))
            if out.count(old_j) != 1:
                raise SystemExit("scriptText target[%d] khớp %d lần" % (ti, out.count(old_j)))
            out = out.replace(old_j, new_j)

    for ti, sid, j, old, new, prefix in plan:
        print("\n=== sID=%s text[%d]  %d -> %d dòng  tiền tố %r (%.1f px, dấu đầu mục %.1f px)"
              % (sid, j, len(old.split("\n")), len(new.split("\n")), prefix,
                 contrib(prefix), contrib(VN_MARKER.match(old.split("\n")[0]).group(0))))
        for l in new.split("\n"):
            print("   %6.1f + %.0f = %6.1f  %s" % (width(l), ENGINE_INDENT,
                                                   width(l) + ENGINE_INDENT, l[:74]))
    for sid, j, why in skipped:
        print("\n! bỏ qua sID=%s text[%d]: %s" % (sid, j, why))
    print("\nsửa %d khối, mirror vào scriptText %d (thất bại %d), bỏ qua %d"
          % (len(plan), mirrored, mirror_failed, len(skipped)))
    if not plan:
        return

    after = json.loads(out.lstrip("﻿"))
    changed = {(ti, j) for ti, _, j, _, _, _ in plan}
    for ti, t in enumerate(data["target"]):
        ta = after["target"][ti]
        assert ta["scriptText_Line"] == t["scriptText_Line"], "scriptText_Line đổi ở target[%d]" % ti
        assert ta["loadLine"] == t["loadLine"], "loadLine đổi ở target[%d]" % ti
        assert len(ta["text"]) == len(t["text"])
        for j in range(len(t["text"])):
            if (ti, j) in changed:
                continue
            assert ta["text"][j] == t["text"][j], "text[%d] target[%d] đổi ngoài dự kiến" % (j, ti)
    for ti, sid, j, old, new, prefix in plan:
        assert after["target"][ti]["text"][j] == new
        strip = lambda s: " ".join(x.lstrip("　 ") for x in s.split("\n"))   # noqa: E731
        assert strip(new) == strip(old), "chữ đổi ở sID=%s text[%d]" % (sid, j)
        assert not violations(new), "sau khi sửa vẫn sai: %s" % violations(new)
    print("kiểm tra: loadLine/scriptText_Line nguyên vẹn, chỉ %d tin nhắn đổi, chữ không đổi"
          % len(plan))

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
    for ti, sid, j, old, new, prefix in plan:
        assert rd["target"][ti]["text"][j] == new, "đọc lại sID=%s text[%d] không khớp" % (sid, j)
    for ti, t in enumerate(data["target"]):
        assert rd["target"][ti]["loadLine"] == t["loadLine"]
        assert rd["target"][ti]["scriptText_Line"] == t["scriptText_Line"]
    print("  đọc lại: %d tin nhắn khớp, loadLine/scriptText_Line nguyên vẹn" % len(plan))


main()
