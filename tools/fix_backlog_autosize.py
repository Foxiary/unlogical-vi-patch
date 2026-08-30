# -*- coding: utf-8 -*-
"""Chữ trong BACKLOG tràn ra ngoài hàng và đè lên mục kế tiếp.

Ảnh chụp máy thật `_2026-08-29_15-46-29.png`: một tin nhắn 3 dòng cứng của ADV
nở thành 5 dòng trong BACKLOG, hai từ `là` / `lại` rơi mồ côi, và dòng cuối
`Ran.` vẽ đè lên tên `Suzuno Kanna` của mục bên dưới.

## Vì sao

BACKLOG đọc **đúng chuỗi `ScenarioData.text[]`** mà ADV đọc, kể cả ngắt dòng
cứng — nhưng khung thì khác:

|            | ADV                    | BACKLOG `Log_Base`        |
|------------|------------------------|---------------------------|
| bề rộng    | 1280                   | **1210**                  |
| cỡ chữ     | 42, **tự thu tới 28**  | 42, **`autoSize = 0`**    |
| chiều cao  | khung co theo cỡ chữ   | hàng **1556×336 cố định** |
| tràn       | —                      | `overflowMode = Overflow` → **không cắt, vẽ đè hàng dưới** |

Hẹp hơn 70 px nên dòng đã vừa ADV bị ngắt lại; không tự thu chữ nên không có gì
bù. Bản Nhật không lộ ra vì nó ngắt cứng sẵn cho vừa: 66.543 dòng cứng, chỉ 54
tin nhắn (0,14%) vượt 3 dòng. Bản Việt vượt **4.323 (10,9%)**.

## Chỗ trống vốn đã có sẵn

Ô chữ khai `1210×50` nhưng thật ra đang vẽ tràn ra ngoài ô đó — `overflowMode`
Overflow che chuyện ấy. Đo trên hàng: mép trên chữ ở `y=+45`, đáy hàng `y=-168`
⇒ **213 px**. Đo lại trên ảnh máy thật: từ mép trên mực dòng 1 xuống đáy khung
trắng là **227 px** — mô hình còn chặt hơn thực tế 14 px, giữ 213 cho an toàn.

Nên bản vá chỉ **khai đúng** phần chỗ mà chữ vốn đã chiếm, rồi bật tự thu chữ y
như ADV. Pivot dọc là 0,50 nên phải dời tâm xuống để giữ nguyên mép trên.

## Không đụng một chữ nào của bản dịch

Chỉ sửa `ui_jp`. `ScenarioData`, `GenebarkChatMainData` và khung ADV giữ nguyên
tuyệt đối — bỏ ngắt dòng cứng cũng chỉ gỡ được 26% số ca (4.323 → 3.185) mà lại
đổi luôn ADV, nên không đi đường đó.

    python tools\\fix_backlog_autosize.py            # đo, so trước/sau
    python tools\\fix_backlog_autosize.py --check    # thoát 1 nếu chưa vá hoặc còn tràn
    python tools\\fix_backlog_autosize.py --apply
"""
import io
import json
import os
import shutil
import sys

import UnityPy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_layout as A                                            # noqa: E402

if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

UI = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
SCENARIO = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
JSON_B = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
BACKUP = os.path.join(ROOT, "_backup", "ui_jp.prebacklogautosize")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

ROW_BOTTOM = -168.0        # đáy hàng Log_Base (1556×336, tâm 0)
# Sàn tự thu chữ. Log_Base lấy 28 cho khớp sàn của khung ADV; ô chat cần 27 mới
# hết tràn nên để 26, chừa biên cho sai số ~1% của mô hình.

# Hai template hiển thị chữ dài. Hai cái còn lại (Log_Base_Chat_Select,
# Log_Base_SELECT) khai sẵn 1220×280 nên đã đủ chỗ — không đụng.
TARGETS = [
    dict(name="Log_Base", src="scenario",
         rect=6699117019379991138, tmp=3933637203441546795,
         width=1210.0, font=42.0, char_sp=5.3, line_sp=-40.0, x=-781.0, top=45.0, size_min=28.0),
    dict(name="Log_Base_Chat", src="chat",
         rect=-4076919273405506282, tmp=-8296035291137428729,
         width=1210.0, font=40.0, char_sp=8.5, line_sp=-55.0, x=-720.0, top=16.0, size_min=26.0),
]


def load_ui():
    env = UnityPy.load(UI)
    objs = {o.path_id: o for o in env.objects}
    return env, objs


def messages(src):
    """Các chuỗi mà template này sẽ phải vẽ."""
    if src == "scenario":
        env = UnityPy.load(SCENARIO)
        for o in env.objects:
            if o.type.name == "TextAsset":
                d = o.read()
                if d.m_Name == "ScenarioData":
                    doc = json.loads(d.m_Script.lstrip("﻿"))
                    return [s for t in doc["target"] for s in t["text"] if s]
        raise SystemExit("không thấy ScenarioData")
    env = UnityPy.load(JSON_B)
    for o in env.objects:
        if o.type.name == "TextAsset":
            d = o.read()
            if d.m_Name == "GenebarkChatMainData":
                rows = json.loads(d.m_Script.lstrip("﻿"))["data"]
                return [r["content"] for r in rows if r.get("content")]
    raise SystemExit("không thấy GenebarkChatMainData")


def pitch(font, line_sp):
    return font * (A.UNITS_LINE_HEIGHT / A.POINT_SIZE + line_sp / 100.0)


def block(n, font, line_sp):
    return (n - 1) * pitch(font, line_sp) + font * (A.UNITS_ASC - A.UNITS_DESC) / A.POINT_SIZE


def n_lines(text, font, width):
    return sum(len(A.wrap(part, font, limit=width)) or 1 for part in text.split("\n"))


def overflow(msgs, t, budget, auto):
    """Số tin nhắn cao quá `budget`. auto=True thì thu chữ dần như TMP."""
    A.CHAR_SPACING = t["char_sp"]
    bad = 0
    sizes = {}
    for s in msgs:
        font = t["font"]
        while True:
            h = block(n_lines(s, font, t["width"]), font, t["line_sp"])
            if h <= budget or not auto or font <= t["size_min"]:
                break
            font -= 0.5
        sizes[font] = sizes.get(font, 0) + 1
        if h > budget:
            bad += 1
    A.CHAR_SPACING = 5.3
    return bad, sizes


def main():
    env, objs = load_ui()
    ok = True
    print("%-16s %-22s %-22s %s" % ("template", "rect hiện tại", "rect mong muốn", "tự thu chữ"))
    plans = []
    for t in TARGETS:
        rect = objs[t["rect"]]
        rd = rect.read_typetree()
        tmp = objs[t["tmp"]]
        td = tmp.read_typetree()
        budget = t["top"] - ROW_BOTTOM
        want_y = t["top"] - budget / 2.0
        cur = "%.0f×%.0f @(%.0f,%.1f)" % (rd["m_SizeDelta"]["x"], rd["m_SizeDelta"]["y"],
                                          rd["m_AnchoredPosition"]["x"], rd["m_AnchoredPosition"]["y"])
        want = "%.0f×%.0f @(%.0f,%.1f)" % (t["width"], budget, t["x"], want_y)
        done = (abs(rd["m_SizeDelta"]["y"] - budget) < 0.5
                and abs(rd["m_AnchoredPosition"]["y"] - want_y) < 0.5
                and td.get("m_enableAutoSizing") in (1, True))
        print("%-16s %-22s %-22s %s" % (t["name"], cur, want,
                                        "BẬT RỒI" if done else "chưa (autoSize=%s)" % td.get("m_enableAutoSizing")))
        if not done:
            ok = False
        plans.append((t, rect, rd, tmp, td, budget, want_y))

    print()
    for t, rect, rd, tmp, td, budget, want_y in plans:
        msgs = messages(t["src"])
        before, _ = overflow(msgs, t, budget, auto=False)
        after, sizes = overflow(msgs, t, budget, auto=True)
        keep = sizes.get(t["font"], 0)
        print("%-16s %5d tin nhắn | chỗ trống %.0f px, bước dòng %.1f px"
              % (t["name"], len(msgs), budget, pitch(t["font"], t["line_sp"])))
        print("%16s   cỡ %.0f cố định (hiện nay) : tràn %5d  (%.2f%%)"
              % ("", t["font"], before, 100.0 * before / len(msgs)))
        print("%16s   tự thu %.0f→%.0f             : tràn %5d  (%.2f%%), %d tin nhắn (%.0f%%) giữ nguyên cỡ %.0f"
              % ("", t["font"], t["size_min"], after, 100.0 * after / len(msgs),
                 keep, 100.0 * keep / len(msgs), t["font"]))

    if CHECK:
        print("\n%s" % ("khớp: đã vá và không còn tràn" if ok else "CHƯA VÁ"))
        sys.exit(0 if ok else 1)
    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(UI, BACKUP)
        print("\nbackup ->", os.path.relpath(BACKUP, ROOT))
    for t, rect, rd, tmp, td, budget, want_y in plans:
        rd["m_SizeDelta"]["x"] = t["width"]
        rd["m_SizeDelta"]["y"] = budget
        rd["m_AnchoredPosition"]["x"] = t["x"]
        rd["m_AnchoredPosition"]["y"] = want_y
        rect.save_typetree(rd)
        td["m_enableAutoSizing"] = 1
        td["m_fontSizeMin"] = t["size_min"]
        td["m_fontSizeMax"] = t["font"]
        td["m_fontSize"] = t["font"]
        tmp.save_typetree(td)
        print("  %s: rect %.0f×%.0f @(%.0f,%.1f), tự thu %.0f→%.0f"
              % (t["name"], t["width"], budget, t["x"], want_y, t["font"], t["size_min"]))
    with open(UI, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi %s  %d byte" % (os.path.relpath(UI, ROOT), os.path.getsize(UI)))

    # đọc lại từ đĩa
    env2, objs2 = load_ui()
    for t, _r, _rd, _tmp, _td, budget, want_y in plans:
        rd = objs2[t["rect"]].read_typetree()
        td = objs2[t["tmp"]].read_typetree()
        assert abs(rd["m_SizeDelta"]["y"] - budget) < 0.01, t["name"]
        assert abs(rd["m_AnchoredPosition"]["y"] - want_y) < 0.01, t["name"]
        assert td["m_enableAutoSizing"] in (1, True), t["name"]
        assert td["m_fontSizeMin"] == t["size_min"] and td["m_fontSizeMax"] == t["font"], t["name"]
        print("  đọc lại %-16s rect %.0f×%.0f @(%.0f,%.1f)  autoSize %s  %.0f→%.0f  OK"
              % (t["name"], rd["m_SizeDelta"]["x"], rd["m_SizeDelta"]["y"],
                 rd["m_AnchoredPosition"]["x"], rd["m_AnchoredPosition"]["y"],
                 td["m_enableAutoSizing"], td["m_fontSizeMax"], td["m_fontSizeMin"]))
    n = sum(1 for _ in env2.objects)
    print("  %d object trong bundle" % n)


if __name__ == "__main__":
    main()
