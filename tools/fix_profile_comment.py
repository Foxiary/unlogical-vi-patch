# -*- coding: utf-8 -*-
"""Popup Profile: nới ô Comment ra sát hai icon bên phải rồi ngắt lại dòng.

Ô chữ là `Pop/Common/Comment・Property` trong prefab `Terminal_Profile` (`ui_jp`) —
một `TextMeshProUGUI` dùng chung cho cả tab Player (trường `comment`) lẫn tab
Spirit. Toạ độ đọc từ prefab, tính theo gốc `Pop` (1056x624, tâm màn hình ở
x = 1122 trên ảnh 1920):

    Comment・Property   rect 880 x 150 tại (3, -142)   -> mép trái -437, mép phải 443
    icon thư / điện thoại  64 x 64 tại (417, -89) và (417, -158)  -> mép trái 385

Nghĩa là **rect vốn đã thừa**: nó chạy xuyên qua cả hai icon (443 > 385). Cái
thật sự bó chữ lại là `\\n` cứng trong `TerminalProfileData.comment` — dòng dài
nhất chỉ 584 px, dừng cách icon hơn 250 px. Bản gốc Nhật ngắt tay ở 20–21 chữ
kanji (~675 px) và **không mục nào quá 3 dòng**; bản dịch ngắt hẹp hơn nên phình
thành 4–6 dòng, tràn xuống dưới khung 150 px.

Nên phải làm hai việc cùng lúc:

    1. rect  880 -> 800,  pos.x  3 -> -37     mép trái đứng yên ở -437 (thẳng
       hàng với nhãn "Comment"), mép phải về 363 — cách mép icon thấy được
       (387) đúng 24 px, và TMP không bao giờ vẽ được xuống dưới icon nữa
    2. ngắt lại 14 chuỗi `comment` cho vừa 792 px (= 800 x 0.99)

Kết quả: 9 mục Player đều còn <= 3 dòng như bản gốc; 5 mục Spirit còn 3–4 dòng
(trước đó tới 6).

**Mô hình bề rộng hiệu chuẩn từ ảnh chụp, không tin thông số trong asset.**
Advance lấy từ TTF nhúng trong `ui_jp` (Font `FOT-iroha21popuraStdN-R`, pid
2079251334914095402, unitsPerEm 1000 — chính bản mod đã thay để có chữ Việt;
font asset trỏ tới nó là Dynamic, bảng glyph nhúng chỉ 84 mục nên không dùng
được):

    W(dòng) = tổng(advance) * 31 / 1000 + (số ký tự - 1) * 1.25

`m_characterSpacing` trong asset là **-3.3**, nhưng game vẽ *rộng ra* chứ không
bó lại: đo 25 bước chữ liên tiếp trên `_2026-08-18_03-12-37.png` (dòng 2 của
Kyosuke, 26 chữ ứng 26 vệt mực) ra +1.19 ± 0.10 px mỗi khe, không phụ thuộc độ
rộng chữ (nên là hằng số mỗi khe, không phải sai số tỉ lệ). Lấy 1.25 cho chắc.
Với mô hình này gốc bút của cả ba dòng rơi đúng x = 685 (= mép trái rect), và
bề rộng dự đoán luôn nhích hơn thực tế ~5 px — lệch về phía an toàn.

    python tools\\fix_profile_comment.py             # chạy thử
    python tools\\fix_profile_comment.py --check      # cổng kiểm: rect + không dòng nào tràn
    python tools\\fix_profile_comment.py --apply      # backup, vá cả ui_jp lẫn json

Backup: `_backup\\ui_jp.preprofcomment`, `_backup\\json.preprofcomment`.
Chạy lại vô hại: rect đúng đích thì bỏ qua, chuỗi ngắt lại y cũ thì bỏ qua.

> **`check_layout_breaks.py --json` sẽ báo MẤT NGẮT DÒNG cho 14 khoá
> `TerminalProfileData/info[*]/comment`.** Đó là chủ ý: cột rộng hơn thì ít dòng
> hơn. Cổng đó so với backup *trước khi merge sheet*, nên đừng chỉa nó vào
> `_backup\\json.preprofcomment`. Sau mỗi lần merge phải chạy lại tool này —
> sheet không mang được `\\n` nào.
"""
import gc
import io
import json
import os
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

import UnityPy   # noqa: E402

JSON_B = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
UI_JP = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BK_JSON = os.path.join(ROOT, "_backup", "json.preprofcomment")
BK_UI = os.path.join(ROOT, "_backup", "ui_jp.preprofcomment")
CACHE = os.path.join(HERE, "_iroha_ui_advances.json")

ASSET = "TerminalProfileData"
FONT_PID = 2079251334914095402          # Font FOT-iroha21popuraStdN-R (TTF nhúng)
RECT_PID = -6189876832534220432         # Comment・Property / RectTransform
TMP_PID = 1053535555780865634           # Comment・Property / TextMeshProUGUI
GO_NAME = "Comment・Property"

OLD_W, OLD_X = 880.0, 3.0
NEW_W, NEW_X = 800.0, -37.0             # mép trái -437 đứng yên, mép phải 443 -> 363
LIMIT = NEW_W * 0.99                    # 792 px
WIDOW = 0.20 * LIMIT                    # dòng cuối trơ một chữ thì kéo chữ xuống

UPEM = 1000.0
SIZE = 31.0                             # m_fontSize, auto-size tắt
SPACING = 1.25                          # px mỗi khe, đo từ ảnh (1.19) rồi làm tròn lên
POINT = 58.0
BOX_H = 150.0
PITCH = SIZE * (116.0 / POINT - 58.0 / 100.0)          # 44.0 px
FIRST = SIZE * (51.04 + 6.96) / POINT                  # 31.0 px

APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv


# ------------------------------------------------------------------ font
def advances():
    """{codepoint: advance (đơn vị font, upem 1000)} của TTF trong ui_jp."""
    if os.path.exists(CACHE):
        return {int(k): v for k, v in json.load(open(CACHE)).items()}
    from fontTools.ttLib import TTFont
    env = UnityPy.load(UI_JP)
    for o in env.objects:
        if o.type.name != "Font" or o.path_id != FONT_PID:
            continue
        f = TTFont(io.BytesIO(bytes(o.read().m_FontData)), fontNumber=0)
        assert f["head"].unitsPerEm == UPEM, "unitsPerEm đổi"
        cmap, hmtx = f.getBestCmap(), f["hmtx"]
        adv = {cp: hmtx[gn][0] for cp, gn in cmap.items() if gn in hmtx.metrics}
        json.dump({str(k): v for k, v in adv.items()}, open(CACHE, "w"))
        return adv
    raise SystemExit("không thấy Font pid=%d trong %s" % (FONT_PID, UI_JP))


ADV = advances()


def width(s):
    miss = sorted({c for c in s if ord(c) not in ADV})
    if miss:
        raise SystemExit("font không có ký tự %s trong %r" % (miss, s))
    a = sum(ADV[ord(c)] for c in s) * SIZE / UPEM
    return a + max(len(s) - 1, 0) * SPACING


def block_height(n):
    return FIRST + (n - 1) * PITCH


# ------------------------------------------------------------------ ngắt dòng
def wrap(text, limit=LIMIT):
    """Ngắt tham lam ở dấu cách; chữ nào một mình đã quá khung thì cho riêng một dòng."""
    out, cur = [], ""
    for w in text.split(" "):
        cand = w if not cur else cur + " " + w
        if cur and width(cand) > limit:
            out.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        out.append(cur)

    # dòng cuối trơ đúng một chữ ngắn trông y như lỗi tràn: kéo chữ từ dòng trên
    # xuống cho đủ dài. Ngưỡng 0.20 chứ không phải 0.40 như fix_dictionary_wrap —
    # ở đây dòng dài gấp rưỡi, 0.40 sẽ xáo lại cả những mục vốn đã gọn.
    while len(out) >= 2 and width(out[-1]) < WIDOW:
        head = out[-2].split(" ")
        if len(head) < 2:
            break
        moved = head[-1] + " " + out[-1]
        if width(moved) > limit:
            break
        out[-2], out[-1] = " ".join(head[:-1]), moved
    return out


# --------------------------------------------------------------------- UI
def read_rect():
    env = UnityPy.load(UI_JP)
    objs = {(o.assets_file, o.path_id): o for o in env.objects}
    rt = next(o for k, o in objs.items() if k[1] == RECT_PID and o.type.name == "RectTransform")
    rtt = rt.read_typetree()
    go = objs[(rt.assets_file, rtt["m_GameObject"]["m_PathID"])]
    assert go.read_typetree()["m_Name"] == GO_NAME, "pid %d không còn là %s" % (RECT_PID, GO_NAME)
    tmp = objs[(rt.assets_file, TMP_PID)]
    t = tmp.read_typetree()
    assert t["m_fontSize"] == SIZE, "m_fontSize đổi thành %s" % t["m_fontSize"]
    return env, objs, rt, rtt, t


def patch_ui(apply_):
    env, objs, rt, rtt, t = read_rect()
    w, x = rtt["m_SizeDelta"]["x"], rtt["m_AnchoredPosition"]["x"]
    print("   ô chữ: %g x %g tại (%g, %g)  cỡ %g  wrap=%s  charSpacing=%.2f"
          % (w, rtt["m_SizeDelta"]["y"], x, rtt["m_AnchoredPosition"]["y"],
             t["m_fontSize"], t["m_TextWrappingMode"], t["m_characterSpacing"]))
    print("   mép trái %g, mép phải %g   (icon bắt đầu ở 385)" % (x - w / 2, x + w / 2))
    if (w, x) not in ((OLD_W, OLD_X), (NEW_W, NEW_X)):
        raise SystemExit("rect %g @ %g lạ — dừng, có gì đó đã đổi" % (w, x))
    if (w, x) == (NEW_W, NEW_X):
        print("   đã ở trạng thái đích — bỏ qua")
        return 0
    assert abs((x - w / 2) - (NEW_X - NEW_W / 2)) < 1e-6, "mép trái không đứng yên"
    print("   %g x -> %g,  pos.x %g -> %g   mép phải %g -> %g (cách icon %g px)"
          % (w, NEW_W, x, NEW_X, x + w / 2, NEW_X + NEW_W / 2,
             385.0 - (NEW_X + NEW_W / 2)))
    if not apply_:
        return 1

    rtt["m_SizeDelta"]["x"] = NEW_W
    rtt["m_AnchoredPosition"]["x"] = NEW_X
    rt.save_typetree(rtt)
    blob = env.file.save(packer="lz4")
    if not os.path.exists(BK_UI):
        shutil.copy2(UI_JP, BK_UI)
        print("   backup -> %s" % BK_UI)
    del env, objs, rt
    gc.collect()
    with open(UI_JP, "r+b") as f:          # ghi đè tại chỗ: Ryujinx chặn rename
        f.write(blob)
        f.truncate()
    print("   đã ghi %s (%s byte)" % (UI_JP, format(len(blob), ",")))
    return 1


# ------------------------------------------------------------------ dữ liệu
def load_json():
    env = UnityPy.load(JSON_B)
    obj = next(o for o in env.objects
               if o.type.name == "TextAsset" and o.read().m_Name == ASSET)
    d = obj.read()
    raw = d.m_Script
    if not isinstance(raw, str):
        raw = bytes(raw).decode("utf-8")
    return env, d, raw


def patch_json(apply_):
    env, d, raw = load_json()
    rows = json.loads(raw.lstrip("﻿"))["info"]

    out, changed = raw, []
    for r in rows:
        old = r.get("comment")
        if not old:
            continue
        joined = " ".join(old.split("\n"))
        new = "\n".join(wrap(joined))
        assert new.replace("\n", " ") == joined, "nội dung đổi ở id %s" % r["id"]
        rec = (r["id"], r["name"], old.split("\n"), new.split("\n"))
        if new == old:
            print("   id %-3s %-16s %d dòng, rộng nhất %6.1f  — đã gọn, bỏ qua"
                  % (r["id"], r["name"], len(rec[2]), max(width(l) for l in rec[2])))
            continue
        old_j = json.dumps(old, ensure_ascii=False)
        new_j = json.dumps(new, ensure_ascii=False)
        n = out.count(old_j)
        if n != 1:
            raise SystemExit("id %s: chuỗi gốc khớp %d lần (phải là 1)" % (r["id"], n))
        out = out.replace(old_j, new_j)
        changed.append(rec)

    for cid, name, before, after in changed:
        print("   id %-3s %-16s %d -> %d dòng, rộng nhất %6.1f -> %6.1f%s"
              % (cid, name, len(before), len(after),
                 max(width(l) for l in before), max(width(l) for l in after),
                 "" if block_height(len(after)) <= BOX_H
                 else "   (cao %.0f > khung %.0f)" % (block_height(len(after)), BOX_H)))
        for l in after:
            print("        %6.1f  %s" % (width(l), l))

    if not changed:
        print("   không chuỗi nào cần ngắt lại")
        return 0

    # so lại toàn bộ cây JSON: chỉ được đổi đúng những trường `comment` kể trên
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
    diffs = sorted(k for k in b if b[k] != a[k])
    print("\n   số trường thay đổi: %d (mục sửa: %d)" % (len(diffs), len(changed)))
    assert len(diffs) == len(changed), "có trường ngoài dự kiến bị đổi: %s" % diffs
    for k in diffs:
        assert k.endswith("/comment"), "đổi trường lạ: %s" % k
        assert b[k].replace("\n", " ") == a[k].replace("\n", " "), "chữ đổi ở %s" % k

    if apply_:
        if not os.path.exists(BK_JSON):
            shutil.copy2(JSON_B, BK_JSON)
            print("   backup -> %s" % BK_JSON)
        d.m_Script = out
        d.save()
        blob = env.file.save(packer="lz4")
        with open(JSON_B, "wb") as f:
            f.write(blob)
        print("   đã ghi %s (%s byte)" % (JSON_B, format(len(blob), ",")))
    return len(changed)


# -------------------------------------------------------------------- check
def check():
    bad = 0
    _, _, _, rtt, _ = read_rect()
    w, x = rtt["m_SizeDelta"]["x"], rtt["m_AnchoredPosition"]["x"]
    if (w, x) != (NEW_W, NEW_X):
        print("FAIL rect %g @ %g — chưa nới (đích %g @ %g)" % (w, x, NEW_W, NEW_X))
        bad += 1
    else:
        print("ok   rect %g @ %g, mép phải %g, cách icon %g px"
              % (w, x, x + w / 2, 385.0 - (x + w / 2)))

    _, _, raw = load_json()
    tall = []
    for r in json.loads(raw.lstrip("﻿"))["info"]:
        c = r.get("comment")
        if not c:
            continue
        lines = c.split("\n")
        worst = max(width(l) for l in lines)
        if worst > NEW_W:
            print("FAIL id %s %s: dòng rộng %.1f > khung %g — TMP sẽ ngắt lại"
                  % (r["id"], r["name"], worst, NEW_W))
            bad += 1
        if block_height(len(lines)) > BOX_H:
            tall.append((r["id"], r["name"], len(lines)))
    if not bad:
        print("ok   14/14 comment không dòng nào rộng hơn %g" % NEW_W)
    if tall:
        print("chú thích: %d mục cao hơn khung 150 px (không cột nào <= 822 px cứu được):"
              % len(tall))
        for cid, name, n in tall:
            print("     id %-3s %-16s %d dòng = %.0f px" % (cid, name, n, block_height(n)))
    raise SystemExit(1 if bad else 0)


def main():
    if CHECK:
        check()
    print("1) ui_jp — nới ô Comment・Property tới sát icon")
    patch_ui(APPLY)
    print("\n2) TerminalProfileData — ngắt lại comment cho cột %g px" % LIMIT)
    patch_json(APPLY)
    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")


if __name__ == "__main__":
    main()
