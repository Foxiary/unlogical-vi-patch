# -*- coding: utf-8 -*-
"""Gỡ những chỗ ngắt dòng cứng nằm GIỮA CỤM TỪ trong thoại ADV.

## Ngắt cứng chỉ đáng giữ khi nó mang nghĩa hoặc engine cần nó

Cùng một chuỗi `ScenarioData.text[]` được **ba widget bề rộng khác nhau** vẽ:

    ô thoại ADV        1280 px   (`level10` pid 886/887, auto-size 28–42)
    BACKLOG            1210 px   (`Log_Base`, xem `fix_backlog_autosize.py`)
    preview thẻ SAVE   hẹp hơn nữa (`sharedassets19.assets`)

Nên một chỗ ngắt canh cho ADV là **sai ở hai chỗ kia** — không cách nào canh vừa
cả ba. Widget nào cũng bật word-wrap, ngắt lại được hết; cái ngắt cứng thật sự
mua được chỉ có hai:

- **ruby** — `Ruby_Text.AdjustRubyPositions` đặt chú thích theo mảng `\\n` của
  chính câu, không biết gì về wrap của TMP (xem mục ruby trong `tools/README.md`).
- **chế độ novel** — engine tự thụt 1 em cho mỗi dòng CÓ TRONG DỮ LIỆU nhưng
  không thụt cho dòng TMP ngắt ra, nên dòng nối tiếp thò sang trái (xem
  `fix_novel_list_wrap.py`). Tool này không đụng vùng novel.

Cộng thêm một cái không phải kỹ thuật mà là dịch thuật: **ngắt ở ranh giới câu**,
mirror theo bản Nhật (`fix_jp_sentence_break.py`, `fix_ellipsis_break.py`). Chỗ
đó giữ.

Còn lại là ngắt để lấp cho vừa bề rộng. Nó không mang nghĩa gì, và nó **sinh ra
lỗi**: khi đoạn phía trước dài quá khung, TMP ngắt lại, và mẩu còn thừa rơi
xuống đứng lẻ một hàng ngay trước chỗ `\\n` viết tay kế tiếp — chính là chữ
`không` trong ảnh `IMG_7232`.

## Số đo (đo trên build, đã lọc script test)

Ký tự cuối của 7.222 chỗ ngắt cứng trong thoại ADV:

    .  5794 (80,2%)    ?  783 (10,8%)    !  281 (3,9%)    ,  14    ―  3
    còn lại: chữ cái thường, tổng ~347 chỗ (4,8%)

Tức quy ước sẵn có đã rất rõ: **ngắt ở dấu kết câu**. 347 chỗ giữa cụm từ là
ngoại lệ, và đó đúng là những chỗ tool này gỡ.

## Không đụng tới

- tin nhắn có tag ruby — TRỪ KHI nối xong ruby vẫn đứng đúng chỗ. `Ruby_Text` đặt
  chú thích theo (chỉ số dòng DATA, x trong dòng đó) và không biết TMP wrap, nên
  nối lại chỉ an toàn khi mọi dòng data đứng trước dòng có ruby vẽ đúng một hàng
  và phần đầu dòng cho tới hết tag ruby cũng nằm trọn hàng vẽ đầu — đo ở cỡ chữ
  auto-size thật (`fix_adv_wrap.render`), xem `ruby_safe()`. `72/txt/0380` (ảnh
  IMG_7232, mẩu `không` đứng lẻ) đúng ca này: engine co xuống 32 pt, tag
  `[dic … text=tinh chỉnh'tuning]` nằm gọn hàng 1 dù nối cả ba dòng làm một. Bốn
  ô ruby còn lại không đạt điều kiện nên giữ nguyên; sheet đã bỏ ruby, chờ
  snapshot mới hơn (87) rồi merge là hết.
- vùng novel (`fix_adv_wrap.adv_messages()` đã loại sẵn)
- script test của nhà phát triển: `sample1`, `UL_test`, `UL_Live2d_test_sample`,
  `01_test_live2d_0*` — sID 0–8, toàn tiếng Nhật, không có trong `ChapterData`,
  không màn nào tới được. Lọc bằng tỉ lệ ký tự CJK: nối tiếng Nhật bằng dấu cách
  là hỏng, mà chúng cũng không phải phần dịch.
- `scriptText_Line` (bản thô), `loadLine`, `selLine`

## Chạy sau tool này

`fix_adv_wrap.py --apply` — nối hai đoạn lại thì câu dài ra, và một số ít câu
tràn xuống dòng 4 chạm hoạ tiết góc. Tool đó sinh ra để xử đúng chuyện ấy.

`check_layout_breaks.py` sẽ báo **mất** ngắt dòng sau đợt này — đúng dự kiến,
giống trường hợp `fix_ellipsis_break.py` gỡ ngắt theo luật dòng cụt.

    python tools\\fix_midphrase_break.py            # chạy thử
    python tools\\fix_midphrase_break.py --apply
    python tools\\fix_midphrase_break.py --check    # chốt sau merge, lỗi -> exit 1
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

_argv = sys.argv
sys.argv = [_argv[0]]
import fix_adv_wrap as A   # noqa: E402  (mượn shown/adv_messages/render/offenders)
sys.argv = _argv

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "scenario01.midphrase")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

# Dấu được coi là "chỗ ngắt có nghĩa". Ba cái đầu chiếm 94,9% số chỗ ngắt đang có;
# `,` `;` `:` và các dấu đóng gộp vào cho đủ, tổng thêm chưa tới 0,3%.
KEEP_AFTER = set(".?!…,;:―—」』）)》>”’\"'")
RUBY = re.compile(r"\[([^\[\]\n']*?)'([^\[\]\n]*?)\]")
CJK = re.compile(r"[一-鿿぀-ゟ゠-ヺー-ヿ]")
CJK_MAX = 0.15


def is_dev_japanese(txt):
    """Ô của script test: gần như toàn chữ Nhật. Nối bằng dấu cách là hỏng."""
    body = A.shown(txt)
    return bool(body) and len(CJK.findall(body)) / len(body) > CJK_MAX


def merged(txt):
    """Nối lại những dòng mà dòng TRƯỚC không kết ở dấu câu."""
    segs = txt.split("\n")
    out = [segs[0]]
    for s in segs[1:]:
        prev = A.shown(out[-1]).rstrip()
        if not prev or prev[-1] in KEEP_AFTER or not s.strip():
            out.append(s)
        else:
            out[-1] = out[-1].rstrip() + " " + s.lstrip("　 ")
    return "\n".join(out)


# Khối caption giữa màn: `[textmode=5]` … tới `[textmode=N]` hoặc `[ノベルモード…終了…]`
# kế tiếp. Chép logic từ `fix_center_caption_wrap.py` chứ không import — file đó gọi
# `main()` ngay ở cuối, import vào là nó chạy luôn.
TEXTMODE = re.compile(r"^\[textmode[=\s]*([0-9]+)\]")
CAPTION_END = re.compile(r"^\[ノベルモード[^\]]*終了")


def caption_owned(data):
    """Ô caption giữa màn — `fix_center_caption_wrap.py` sở hữu, đừng đụng.

    Khung caption rộng 1920 nhưng lề an toàn chỉ 1764 (watermark góc), nên tool đó
    **cố ý** ngắt giữa cụm từ khi mệnh đề không có dấu câu nào nằm đúng chỗ — nó
    còn cân độ dài hai vế nữa. Không miễn cho nó thì tool này gỡ đúng những chỗ ấy
    ra: đã xảy ra thật với `85/txt/0767`, `99/txt/0214`, `99/txt/0215`.
    """
    out = set()
    for ti, t in enumerate(data["target"]):
        lines = t["scriptText_Line"]
        by_line = {}
        for j, ln in enumerate(t["loadLine"]):
            by_line.setdefault(ln, []).append(j)
        for i, ln in enumerate(lines):
            m = TEXTMODE.match(ln.strip())
            if not m or m.group(1) != "5":
                continue
            end = len(lines)
            for k in range(i + 1, len(lines)):
                s = lines[k].strip()
                if TEXTMODE.match(s) or CAPTION_END.match(s):
                    end = k
                    break
            for line, js in by_line.items():
                if i <= line < end:
                    out.update((ti, j) for j in js)
    return out


def candidates(data):
    """(ti, sID, j, cũ, mới) cho mọi ô còn ngắt giữa cụm từ ĐÁNG gỡ.

    Bỏ qua ô mà nối lại xong sẽ chạm hoạ tiết góc: ở đó `fix_adv_wrap.py` **cố ý**
    ngắt giữa cụm từ để đẩy chữ lên khỏi phần vát chéo, tức chỗ ngắt ấy đang làm
    việc chứ không phải rác. Không có nhánh này thì hai tool giằng nhau — cái này
    nối, cái kia ngắt lại, và `--check` đỏ vĩnh viễn.
    """
    owned = caption_owned(data)
    out = []
    for ti, sid, j in A.adv_messages(data):
        txt = data["target"][ti]["text"][j]
        if not isinstance(txt, str) or "\n" not in txt:
            continue
        if (ti, j) in owned or is_dev_japanese(txt):
            continue
        new = merged(txt)
        if new == txt or A.offenders(new)[0]:
            continue
        if RUBY.search(txt) and not ruby_safe(new):
            continue
        out.append((ti, sid, j, txt, new))
    return out


def ruby_safe(new):
    """Nối xong, mọi chú thích ruby vẫn được vẽ đúng chỗ.

    `Ruby_Text` đặt chú thích theo (chỉ số dòng DATA, x trong dòng đó), không biết
    TMP wrap. Nên cần hai điều: mọi dòng data đứng TRƯỚC dòng cuối có ruby vẽ đúng
    một hàng, và trên mỗi dòng có ruby thì phần đầu dòng cho tới hết tag ruby cuối
    nằm trọn hàng vẽ đầu. Đo ở cỡ chữ auto-size thật của tin nhắn
    (`fix_adv_wrap.render`), quy về thang `w42`.
    """
    size = A.render(new)[0]
    limit = (A.RECT_W - A.SAFETY) * 42.0 / size
    lines = new.split("\n")
    last = max(k for k, l in enumerate(lines) if RUBY.search(l))
    if any(A.w42(l) > limit for l in lines[:last]):
        return False
    for l in lines[:last + 1]:
        ms = list(RUBY.finditer(l))
        if ms and A.w42(l[:ms[-1].end()]) > limit:
            return False
    return True


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
    """Đổi khối dòng tương ứng trong bản sao `scriptText`. None nếu không chắc."""
    lines, old_l, new_l = script.split("\n"), old.split("\n"), new.split("\n")
    hits = [k for k in range(len(lines) - len(old_l) + 1) if lines[k:k + len(old_l)] == old_l]
    if len(hits) != 1:
        return None
    k = hits[0]
    lines[k:k + len(old_l)] = new_l
    return "\n".join(lines)


def main():
    env, asset, raw = load(BUNDLE)
    bom = "﻿" if raw.startswith("﻿") else ""
    data = json.loads(raw.lstrip("﻿"))
    cand = candidates(data)
    nbreaks = sum(len(o.split("\n")) - len(n.split("\n")) for _t, _s, _j, o, n in cand)
    print("thoại ADV: %d tin nhắn còn ngắt giữa cụm từ, tổng %d chỗ ngắt"
          % (len(cand), nbreaks))

    if CHECK:
        if cand:
            for ti, sid, j, old, _new in cand[:10]:
                bad = [l for l in old.split("\n")[:-1]
                       if A.shown(l).rstrip() and A.shown(l).rstrip()[-1] not in KEEP_AFTER]
                print("  FAIL sID=%-4s text[%-5d] dòng kết ở %r"
                      % (sid, j, A.shown(bad[0]).rstrip()[-14:]))
            print("\n%d tin nhắn — chạy `python tools\\fix_midphrase_break.py --apply`"
                  % len(cand))
            raise SystemExit(1)
        print("PASS không tin nhắn nào còn ngắt giữa cụm từ")
        return 0

    # Chuỗi trùng: `text[]` có những câu y hệt nhau ở nhiều ô (cặp nhánh tên, lời
    # lặp). Thay chuỗi mù thì đụng cả ô KHÔNG phải ứng viên, nên chỉ thay hàng loạt
    # khi mọi ô mang đúng chuỗi đó đều là ứng viên; còn lại bỏ qua cho an toàn.
    holders = {}
    for t in data["target"]:
        for v in t["text"] or []:
            if isinstance(v, str):
                holders[v] = holders.get(v, 0) + 1
    picked = {}
    for _ti, _sid, _j, old, _new in cand:
        picked[old] = picked.get(old, 0) + 1

    out, plan, skipped = raw, [], []
    scripts = {}
    done = set()
    for ti, sid, j, old, new in cand:
        old_j = json.dumps(old, ensure_ascii=False)
        new_j = json.dumps(new, ensure_ascii=False)
        if out.count(old_j) != 1:
            if holders.get(old, 0) != picked.get(old, 0):
                skipped.append((sid, j, "chuỗi trùng %d ô, có ô không phải ứng viên"
                                % holders.get(old, 0)))
                continue
            if old in done:
                plan.append((ti, sid, j, old, new))
                scripts.setdefault(ti, []).append((old, new))
                continue
            done.add(old)
        out = out.replace(old_j, new_j)
        scripts.setdefault(ti, []).append((old, new))
        plan.append((ti, sid, j, old, new))

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

    for ti, sid, j, old, new in plan[:8]:
        print("\n=== sID=%s text[%d]  %d -> %d dòng"
              % (sid, j, len(old.split("\n")), len(new.split("\n"))))
        for l in old.split("\n"):
            print("   cũ  | %s" % A.shown(l)[:88])
        for l in new.split("\n"):
            print("   mới | %s" % A.shown(l)[:88])
    if len(plan) > 8:
        print("\n… và %d tin nhắn nữa" % (len(plan) - 8))
    for sid, j, why in skipped:
        print("\n! bỏ qua sID=%s text[%d]: %s" % (sid, j, why))
    print("\nsửa %d tin nhắn, mirror vào scriptText %d (thất bại %d), bỏ qua %d"
          % (len(plan), mirrored, mirror_failed, len(skipped)))
    if not plan:
        return 0

    after = json.loads(out.lstrip("﻿"))
    changed = {(ti, j) for ti, _s, j, _o, _n in plan}
    for ti, t in enumerate(data["target"]):
        ta = after["target"][ti]
        assert ta["scriptText_Line"] == t["scriptText_Line"], "scriptText_Line đổi ở target[%d]" % ti
        assert ta["loadLine"] == t["loadLine"], "loadLine đổi ở target[%d]" % ti
        assert ta["selLine"] == t["selLine"], "selLine đổi ở target[%d]" % ti
        assert len(ta["text"]) == len(t["text"])
        for j in range(len(t["text"])):
            if (ti, j) not in changed:
                assert ta["text"][j] == t["text"][j], "text[%d] target[%d] đổi ngoài dự kiến" % (j, ti)
    flat = lambda s: " ".join(x.strip("　 ") for x in s.split("\n"))     # noqa: E731
    for ti, sid, j, old, new in plan:
        assert after["target"][ti]["text"][j] == new
        assert flat(new) == flat(old), "chữ đổi ở sID=%s text[%d]" % (sid, j)
    orn = [(sid, j) for _t, sid, j, _o, n in plan if A.offenders(n)[0]]
    print("kiểm tra: loadLine/scriptText_Line/selLine nguyên vẹn, chỉ %d tin nhắn đổi, chữ không đổi"
          % len(plan))
    if orn:
        print("  %d tin nhắn sau khi nối sẽ chạm hoạ tiết — chạy `fix_adv_wrap.py --apply` ngay sau: %s"
              % (len(orn), ", ".join("%s/%d" % x for x in orn[:6])))

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return 0

    if not os.path.exists(BACKUP):
        shutil.copy2(BUNDLE, BACKUP)
        print("backup ->", BACKUP)
    asset.m_Script = bom + out.lstrip("﻿")
    asset.save()
    with open(BUNDLE, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi %s %d" % (BUNDLE, os.path.getsize(BUNDLE)))

    _e, _a, raw2 = load(BUNDLE)
    rd = json.loads(raw2.lstrip("﻿"))
    for ti, sid, j, _old, new in plan:
        assert rd["target"][ti]["text"][j] == new, "đọc lại lệch ở sID=%s text[%d]" % (sid, j)
        assert rd["target"][ti]["scriptText_Line"] == data["target"][ti]["scriptText_Line"]
    print("  đọc lại: %d tin nhắn khớp, bản thô nguyên vẹn" % len(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
