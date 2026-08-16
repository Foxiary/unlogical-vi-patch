# -*- coding: utf-8 -*-
"""Popup Profile: bỏ tên tiếng Nhật, chỉ để romaji.

Màn Profile vẽ tên bằng **hai** ô chữ lồng nhau (`ui_jp`, prefab
`Terminal_Profile`):

    BG/Pop/Common/Name                 Image `UL_term_c_popup_prof_moji_name` 540x36
      Text (TMP)          pid 6645790041897977147   ô  66x40, cỡ 31  <- `name`
        Eizi(TMP)         pid 1526125385128713001   ô 226x40, cỡ 20  <- `ruby`

`Eizi` = 英字 ("chữ Latin"). Bản gốc 1.0.2 **vốn đã** mang romaji của nhà phát
hành trong `TerminalProfileData.ruby`, nên màn hình xưa nay hiện `琥珀 Kohaku`.
Vì thế 14 dòng `prof_name` trên sheet chưa bao giờ được merge — đổ thẳng bản dịch
vào `name` sẽ ra "Kohaku Kohaku" và tràn ô 66 px.

Script làm đúng một phép biến đổi, **không đổi một ký tự nào đang hiện trên màn
hình**, chỉ đổi chỗ và cỡ:

    name = ruby     ruby = ""

Ô 66 px vốn vừa khít 2 chữ kanji (`m_TextWrappingMode = 1`, tức là chữ Latin sẽ
bị **wrap** chứ không tràn), nên phải nới. Đo từ chính tranh nền: caption "Name"
nằm bên trái, gạch chân chạy hết 540 px, mép trái ô Text cách mép trái khung
131 px → còn **409 px** dùng được.

    m_SizeDelta.x        66 -> 400      (chừa 9 px)
    m_TextWrappingMode    1 -> 0        NoWrap: không bao giờ xuống dòng thứ hai
    m_enableAutoSizing    0 -> 1        20..31, max ghim đúng cỡ gốc

NoWrap + auto-size là cách đã dùng ở `fix_recollection_list.py`: chỉ co theo bề
ngang, luôn một dòng, không bao giờ chạm dòng dưới.

> **Vì sao auto-size chứ không tin vào số đo.** Font `FOT-iroha21popuraStdN-R
> SDF-Dynamic` là font **Dynamic** — bảng glyph nhúng chỉ có 84 mục và **thiếu 21
> chữ cái Latin** (game nạp thêm lúc chạy từ TTF nguồn). Mọi phép tính bề rộng ở
> đây đều phải thay thế advance, nên chỉ là ước lượng (~279 px cho tên dài nhất
> `Himejima Kyosuke`, còn dư 130 px). Auto-size biến sai số đó thành vô hại.

    python tools\\fix_profile_name.py            # chạy thử
    python tools\\fix_profile_name.py --apply    # backup, vá cả json lẫn ui_jp

Backup: `_backup\\json.preprofname`, `_backup\\ui_jp.preprofname`.
Chạy lại vô hại: dòng nào `ruby` đã rỗng thì bỏ qua, ô chữ đã đúng thì bỏ qua.
"""
import gc
import json
import os
import shutil
import sys

import UnityPy

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
JSON_B = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
UI_JP = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BK_JSON = os.path.join(ROOT, "_backup", "json.preprofname")
BK_UI = os.path.join(ROOT, "_backup", "ui_jp.preprofname")

TEXT_PID = 6645790041897977147          # Name/Text (TMP)  <- name
NEW_W = 400.0
OLD_W = 66.0
SIZE_MIN, SIZE_MAX = 20.0, 31.0

APPLY = "--apply" in sys.argv


# ------------------------------------------------------------------ dữ liệu
def patch_json(apply_):
    env = UnityPy.load(JSON_B)
    obj = next(o for o in env.objects
               if o.type.name == "TextAsset" and o.read().m_Name == "TerminalProfileData")
    d = obj.read()
    raw = d.m_Script
    rows = json.loads(raw.lstrip("﻿"))["info"]

    out, done, skipped = raw, 0, 0
    for r in rows:
        jp, rb = r.get("name"), r.get("ruby")
        if not rb:
            skipped += 1
            continue
        # JSON ở dạng nén (`"name":"…"`), nhưng vẫn dò cả biến thể có khoảng trắng
        sep = next((s for s in (":", ": ")
                    if out.count('"name":%s%s' % (s[1:], json.dumps(jp, ensure_ascii=False))) == 1),
                   None)
        if sep is None:
            raise SystemExit("id %s: không khớp duy nhất được trường name %r"
                             % (r.get("id"), jp))
        pad = sep[1:]
        old_n = '"name":%s%s' % (pad, json.dumps(jp, ensure_ascii=False))
        new_n = '"name":%s%s' % (pad, json.dumps(rb, ensure_ascii=False))
        old_r = '"ruby":%s%s' % (pad, json.dumps(rb, ensure_ascii=False))
        if out.count(old_r) != 1:
            raise SystemExit("id %s: %r xuất hiện %d lần" % (r.get("id"), old_r, out.count(old_r)))
        out = out.replace(old_n, new_n).replace(old_r, '"ruby":%s""' % pad)
        print("   id %-3s  %-16s -> %-20s  (ruby xoá trắng)" % (r.get("id"), jp, rb))
        done += 1

    print("   %d dòng đổi, %d dòng không có ruby (giữ nguyên)" % (done, skipped))
    if not done:
        return 0

    new_rows = json.loads(out.lstrip("﻿"))["info"]
    assert len(new_rows) == len(rows), "số dòng đổi"
    for a, b in zip(rows, new_rows):
        assert a.keys() == b.keys(), "đổi cấu trúc"
        for k in a:
            if k not in ("name", "ruby"):
                assert a[k] == b[k], "đụng trường %s ở id %s" % (k, a.get("id"))
        if a.get("ruby"):
            assert b["name"] == a["ruby"] and b["ruby"] == "", "id %s sai" % a.get("id")
        else:
            assert b["name"] == a["name"], "id %s bị đụng" % a.get("id")
    print("   kiểm tra: chỉ hai trường name/ruby thay đổi, 21/21 dòng còn nguyên khoá")

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
    return done


# --------------------------------------------------------------------- UI
def patch_ui(apply_):
    env = UnityPy.load(UI_JP)
    objs = {(o.assets_file, o.path_id): o for o in env.objects}

    tmp = next(o for o in env.objects
               if o.type.name == "MonoBehaviour" and o.path_id == TEXT_PID)
    t = tmp.read_typetree()
    go = objs[(tmp.assets_file, t["m_GameObject"]["m_PathID"])]
    gt = go.read_typetree()

    rt = rtt = None
    for c in gt["m_Component"]:
        pid = (c.get("component") or c.get("second") or {}).get("m_PathID")
        cand = objs.get((go.assets_file, pid))
        if cand is not None and cand.type.name == "RectTransform":
            rt = cand
            rtt = cand.read_typetree()
            break
    if rt is None:
        raise SystemExit("không tìm thấy RectTransform của ô tên")

    w = rtt["m_SizeDelta"]["x"]
    print("   ô chữ: %g x %g, wrap=%s, autoSize=%s, cỡ %g"
          % (w, rtt["m_SizeDelta"]["y"], t.get("m_TextWrappingMode"),
             t.get("m_enableAutoSizing"), t.get("m_fontSize")))
    if w not in (OLD_W, NEW_W):
        raise SystemExit("bề rộng %g lạ — dừng, có gì đó đã đổi" % w)

    changes = []
    if w != NEW_W:
        changes.append("bề rộng %g -> %g" % (w, NEW_W))
        rtt["m_SizeDelta"]["x"] = NEW_W
    if t.get("m_TextWrappingMode") != 0:
        changes.append("wrap %s -> 0 (NoWrap)" % t.get("m_TextWrappingMode"))
        t["m_TextWrappingMode"] = 0
    if not t.get("m_enableAutoSizing"):
        changes.append("auto-size bật %g..%g" % (SIZE_MIN, SIZE_MAX))
        t["m_enableAutoSizing"] = 1
    if t.get("m_fontSizeMin") != SIZE_MIN:
        t["m_fontSizeMin"] = SIZE_MIN
    if t.get("m_fontSizeMax") != SIZE_MAX:
        t["m_fontSizeMax"] = SIZE_MAX

    if not changes:
        print("   ô chữ đã ở trạng thái đích — bỏ qua")
        return 0
    for c in changes:
        print("   %s" % c)

    if apply_:
        rt.save_typetree(rtt)
        tmp.save_typetree(t)
        blob = env.file.save(packer="lz4")
        if not os.path.exists(BK_UI):
            shutil.copy2(UI_JP, BK_UI)
            print("   backup -> %s" % BK_UI)
        del env, objs, tmp, rt
        gc.collect()
        with open(UI_JP, "r+b") as f:          # ghi đè tại chỗ: Ryujinx chặn rename
            f.write(blob)
            f.truncate()
        print("   đã ghi %s (%s byte)" % (UI_JP, format(len(blob), ",")))
    return len(changes)


def main():
    print("1) TerminalProfileData — name = ruby, ruby = \"\"")
    patch_json(APPLY)
    print("\n2) ui_jp — nới ô tên, NoWrap, auto-size")
    patch_ui(APPLY)
    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")


if __name__ == "__main__":
    main()
