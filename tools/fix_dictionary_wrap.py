# -*- coding: utf-8 -*-
"""Re-wrap dictionary body text so TextMeshPro finds nothing left to wrap.

`DictionaryData.text` is hard-wrapped in the data — one `\\n` per rendered line,
the way the JP writers left it.  The box also has `m_TextWrappingMode = 1`, so a
hard line that is a hair too wide gets broken a SECOND time by TMP and the tail
lands on a line of its own:

    phối viên nhưng phạm vi   ->   phối viên nhưng phạm
                                   vi                     <- orphan
    quyền hạn sẽ khác nhau,   ->   quyền hạn sẽ khác
                                   nhau,                   <- orphan

Câu chữ không sai gì; chỉ là dòng cứng rộng quá khung. Sửa bằng cách ghép cả mục
lại rồi ngắt lại cho mỗi dòng nằm trong khung — TMP không còn gì để ngắt nữa.

The tighter of the two dictionary screens is the ADV popup (the one the player
opens while reading), not the terminal ARCHIVE page:

    level10 pid 895  DictionaryLayer/ViewRoot/uch_dictionary_note_field/
                     MainText (TMP)      rect 586 x 758, size 40, charSpacing 5
    level22 pid 331  Note/NoteTextArea/Mask/MainText (TMP)
                                         rect 497 x 476, size 32, charSpacing 3.5

Per line that is 586/40 = 14.65 em against 497/32 = 15.5 em, so wrapping for the
popup covers the ARCHIVE page as well.

Width model — **advance and characterSpacing do NOT share a scale factor**: TMP
scales the glyph advance by `fontSize / pointSize` but characterSpacing by
`fontSize / 100`, and the wrap test measures to the last glyph's right edge, so
the trailing spacing does not count:

    W(line) = sum(advance) * fontSize/pointSize + (n-1) * charSpacing * fontSize/100

(`adv_layout.wrap` still uses the older `(advance + spacing) * fontSize/pointSize`
form, which over-counts spacing by 1.4 px per character at size 40 — 7% on a full
line.  Don't borrow it for a tight box; only its glyph table is reused here.)

With the right form the limit is **exactly the rect width, 586 px**, no fudge
factor.  `OBSERVED` below holds the break points read off a photo of the real
popup (entry `no=112` before this fix); the tool refuses to run unless the model
puts every one of them on the correct side of 586:

    việc can thiệp hệ thống   577.6 px  -> game draws ONE line
    phối viên nhưng phạm vi   590.1 px  -> TMP breaks it

    python tools\\fix_dictionary_wrap.py [--all] [--apply]

Default: only entries containing a line wider than the box are re-wrapped
(`--all` re-wraps all 80).  Content is never changed — the tool asserts that the
text with the newlines removed is identical before and after.

**Never answer this by deleting the newlines instead.**  The engine paginates the
note by counting `\\n` in the DATA (`MyUICompornentBase.BuildNoteLines` RVA
0x19B3490 = `raw.Replace(…).Split('\\n')`) and shows `NOTE_TEXT_LINE` of them per
page — 11 for this popup (RVA 0x1A17880), 8 for the terminal ARCHIVE page.  It
never looks at what TMP actually drew, so one long paragraph = one page = the tail
is unreachable.  See the README section for the proof out of the same two photos.
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
from adv_layout import ADV   # noqa: E402  (glyph advances, pointSize 58)

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
BACKUP = os.path.join(ROOT, "_backup", "json.predicwrap")
ASSET = "DictionaryData"

APPLY = "--apply" in sys.argv
ALL = "--all" in sys.argv
# --only=NN: ngắt lại đúng một mục dù nó chưa tràn — dùng sau khi sửa câu chữ trong
# mục đó, vì sửa chữ xong thì các dòng cũ không còn xếp gọn nữa.
ONLY = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--only=")), None)

# level10 pid 895 — ô chật hơn trong hai màn từ điển
POINT_SIZE = 58.0
FONT_SIZE = 40.0
CHAR_SPACING = 5.0
BOX = 586.0               # = bề rộng rect, không cần hệ số bù
SAFETY = 0.99             # kẹp đo được là 577,6 / 590,1 nên chừa 1%
THRESHOLD = BOX
TARGET = BOX * SAFETY
# Dòng cuối trơ một chữ trông y như đúng cái lỗi đang sửa, nên kéo chữ từ dòng
# trên xuống cho tới khi nó đủ dài. Chỉ chạm vào dòng cuối, không lan lên trên.
WIDOW = 0.40 * TARGET
FALLBACK_ADV = 58.0

# Mốc ngắt dòng đọc từ ảnh chụp popup thật (mục 112 trước khi sửa). Mô hình nào
# xếp sai một mốc trong đây là mô hình sai — không vá bằng nó.
OBSERVED_FITS = [
    "việc can thiệp hệ thống", "cáo lỗi. Dù cùng là điều", "bị hạn chế trừ khi được",
    "các Hắc phục và Spirit.", "người được đăng ký là", "Họ đảm nhận các công",
]
OBSERVED_BREAKS = [
    "Tên gọi chung cho những", "phối viên nhưng phạm vi", "quyền hạn sẽ khác nhau,",
    "người quản trị cho phép.",
]


def width(s, size=FONT_SIZE, cs=CHAR_SPACING):
    """Bề rộng TMP vẽ ra, tính bằng px canvas."""
    adv = sum(ADV.get(ord(c), FALLBACK_ADV) for c in s) * size / POINT_SIZE
    return adv + max(len(s) - 1, 0) * cs * size / 100.0


def check_model():
    worst_fit = max(width(s) for s in OBSERVED_FITS)
    best_break = min(width(s) for s in OBSERVED_BREAKS)
    print("mô hình: rộng nhất còn vừa %.1f  <  khung %.0f  <  hẹp nhất bị ngắt %.1f"
          % (worst_fit, BOX, best_break))
    assert worst_fit < BOX < best_break, "mô hình xếp sai mốc đo được — dừng"


def wrap(text, limit=TARGET):
    """Greedy wrap on spaces.  A single word wider than `limit` gets its own line."""
    out, cur = [], ""
    for word in text.split(" "):
        cand = word if not cur else cur + " " + word
        if cur and width(cand) > limit:
            out.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        out.append(cur)

    while len(out) >= 2 and width(out[-1]) < WIDOW:
        head = out[-2].split(" ")
        if len(head) < 2:
            break
        moved = head[-1] + " " + out[-1]
        if width(moved) > limit:
            break
        out[-2], out[-1] = " ".join(head[:-1]), moved
    return out


def load_asset(path):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name == "TextAsset" and o.read().m_Name == ASSET:
            d = o.read()
            raw = d.m_Script
            if not isinstance(raw, str):
                raw = bytes(raw).decode("utf-8")
            return env, d, raw
    raise SystemExit("%s không có trong %s" % (ASSET, path))


def main():
    check_model()
    env, d, raw = load_asset(BUNDLE)
    bom = "﻿" if raw.startswith("﻿") else ""
    data = json.loads(raw.lstrip("﻿"))["data"]

    out = raw
    changed = []
    for e in data:
        old = e["text"]["jp"]
        lines = old.split("\n")
        worst = max(width(l) for l in lines)
        if ONLY is not None:
            if e["no"] != ONLY:
                continue
        elif not ALL and worst <= THRESHOLD:
            continue
        joined = " ".join(lines)
        new = "\n".join(wrap(joined))
        assert new.replace("\n", " ") == joined, "nội dung đổi ở no=%s" % e["no"]
        if new == old:
            continue

        old_j = json.dumps(old, ensure_ascii=False)
        new_j = json.dumps(new, ensure_ascii=False)
        n = out.count(old_j)
        if n != 1:
            raise SystemExit("no=%s: chuỗi gốc khớp %d lần (phải là 1)" % (e["no"], n))
        out = out.replace(old_j, new_j)
        changed.append((e["no"], e["title"]["jp"], lines, new.split("\n"), worst))

    if not changed:
        print("không mục nào có dòng rộng hơn %.0f — không cần sửa" % THRESHOLD)
        return

    for no, title, before, after, worst in changed:
        print("=== no=%s  %s   %d -> %d dòng   rộng nhất %.0f -> %.0f"
              % (no, title, len(before), len(after), worst,
                 max(width(l) for l in after)))
        for l in after:
            print("   %6.1f  %s" % (width(l), l))

    # so lại toàn bộ cây JSON: chỉ được đổi đúng những trường `text` kể trên
    before_all = json.loads(raw.lstrip("﻿"))
    after_all = json.loads(out.lstrip("﻿"))

    def walk(x, path=""):
        if isinstance(x, dict):
            for k, v in x.items():
                yield from walk(v, path + "/" + str(k))
        elif isinstance(x, list):
            for i, v in enumerate(x):
                yield from walk(v, path + "[%d]" % i)
        else:
            yield path, x

    b, a = dict(walk(before_all)), dict(walk(after_all))
    assert b.keys() == a.keys(), "cấu trúc JSON đổi"
    diffs = [k for k in b if b[k] != a[k]]
    print("\nsố trường thay đổi: %d (mục sửa: %d)" % (len(diffs), len(changed)))
    assert len(diffs) == len(changed), "có trường ngoài dự kiến bị đổi"
    for k in diffs:
        assert k.endswith("/text/jp") and b[k].replace("\n", " ") == a[k].replace("\n", " ")

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(BUNDLE, BACKUP)
        print("backup ->", BACKUP)
    d.m_Script = bom + out.lstrip("﻿")
    d.save()
    blob = env.file.save(packer="lz4")
    with open(BUNDLE, "wb") as f:
        f.write(blob)
    print("đã ghi", BUNDLE, os.path.getsize(BUNDLE))

    # đọc lại từ disk, đừng tin giá trị trong bộ nhớ
    _, _, back = load_asset(BUNDLE)
    reread = {e["no"]: e["text"]["jp"] for e in json.loads(back.lstrip("﻿"))["data"]}
    worst = 0.0
    for no, _, _, after, _ in changed:
        got = reread[no].split("\n")
        assert got == after, "no=%s đọc lại không khớp" % no
        worst = max(worst, max(width(l) for l in got))
    print("  đọc lại: %d mục khớp, dòng rộng nhất %.1f" % (len(changed), worst))
    allworst = max(width(l) for t in reread.values() for l in t.split("\n"))
    print("  cả 80 mục: dòng rộng nhất %.1f (ngưỡng %.0f)" % (allworst, THRESHOLD))


main()
