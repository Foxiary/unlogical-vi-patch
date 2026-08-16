# -*- coding: utf-8 -*-
"""Thu hẹp khoảng cách chữ của các nút màn Q&A.

Nút là prefab `Q&A_Button` trong `ui_jp` — cùng một `Text (TMP)` lặp lại **11 lần**
(`Q&A_Button` mẫu + `Q&A_Button01..10` nướng sẵn trong prefab `Q&A`, lẻ ở cột
`Left`, chẵn ở cột `Right`):

    rect            532 x 96, m_margin (24, 9, 21, 18)  ->  bề rộng chữ 487
    font            FOT-DotGothic12Std-M SDF-Dynamic (pointSize 58, lineHeight 116)
    fontSize 33     căn giữa, wrap Normal, overflow Overflow, auto-size TẮT
    m_characterSpacing 7

Font này **đơn cách**: TTF nhúng trong `ui_jp` cho mọi glyph advance đúng
512/1024 em. Chuỗi mẫu của bản gốc `あいうえ五あいうえ十あい` chỉ có 12 chữ toàn
rộng, nên `characterSpacing 7` gần như không thấy; chữ Latin nửa rộng phải trả
đúng khoảng đó cho **từng chữ cái**, thành ra tiếng Việt trông giãn hẳn ra.

**Hai phần của bước chữ KHÔNG cùng một hệ số tỉ lệ.** TMP nhân advance của glyph
với `fontSize / pointSize`, nhưng nhân `characterSpacing` với `fontSize / 100`
(đơn vị phần trăm em, `currentEmScale`, không phải `currentElementScale`):

    bước chữ = 29 * fontSize/58  +  characterSpacing * fontSize/100
             = 16.50             +  0.33 * cs

`29` là advance nửa rộng của font, đọc thẳng từ `m_FaceInfo.m_TabWidth`
(= 512/1024 em, khớp `hmtx` của TTF nhúng).

TMP ngắt dòng theo **mép phải của glyph**, khoảng cách đuôi không tính, nên chuỗi
`n` chữ cần:

    W(n) = (n-1) * bước chữ + 16.50   <=   487

Hiệu chuẩn với hai ảnh chụp thật (15:57 và 16:49 ngày 16/08/2026), sáu điểm ngắt
dòng, **đúng cả sáu**:

    cs=7  W(26)=486.8 vừa khít, W(27)=505.6 ngắt, W(28)=524.2 ngắt
    cs=3  W(27)=471.2 vừa,      W(28)=488.7 ngắt (thiếu đúng 1.7 px!)

> Lần một đặt `cs = 3` vì tưởng cả hai phần cùng nhân `fontSize/58`; mô hình đó
> ra bước chữ nhỏ hơn thật và hứa nhầm rằng 28 chữ vừa một dòng. Sai đúng ở hệ số
> `100` vs `58`. `adv_layout.py` cũng dùng công thức cũ — chính vì thế nó **luôn
> lệch về phía rộng hơn**, và `SAFETY = 0.985` che mất sai số đó.

    cs=7 -> 18.81 px/chữ     cs=3 -> 17.49     cs=2 -> 17.16     cs=0 -> 16.50

Đặt **3.0**: mật độ chữ Latin (3/29.0 = 10.3%) khớp với mật độ chữ Nhật của bản
gốc (7/59.1 = 11.8%), và đủ để "Người hợp cạ trong Unlogical" (28 chữ) về lại
một dòng.
"""
import os
import shutil
import sys

import UnityPy

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UI_JP = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BACKUP = os.path.join(ROOT, "_backup", "ui_jp.preqaspacing")

FONT_ASSET_PID = -8228475448987565529      # FOT-DotGothic12Std-M SDF-Dynamic
STOCK_SPACING = 7.0                         # giá trị của bản gốc
NEW_SPACING = 2.0
FONT_SIZE = 33.0
POINT_SIZE = 58.0
GLYPH_ADVANCE = 29.0                        # m_FaceInfo.m_TabWidth = nửa rộng
BOX_W = 532.0
MARGIN_L, MARGIN_R = 24.0, 21.0
AVAIL = BOX_W - MARGIN_L - MARGIN_R         # 487
GLYPH_PX = GLYPH_ADVANCE * FONT_SIZE / POINT_SIZE       # 16.50

TITLES = [
    "Thông tin cá nhân", "Chuyện gia đình", "Thích gì, ghét gì",
    "Gu bạn gái lý tưởng", "Người hợp cạ trong Unlogical", "Bí mật bật mí",
    "Thích làm nũng hay thích được người yêu nuông chiều?",
    "Ấn tượng đầu tiên về cô ấy", "Điểm thích nhất ở cô ấy",
    "Đôi lời gửi đến cô ấy",
]


def pitch(cs):
    return GLYPH_PX + cs * FONT_SIZE / 100.0


def width(n, cs):
    """Bề ngang chuỗi n chữ theo cách TMP đo khi ngắt dòng."""
    return (n - 1) * pitch(cs) + GLYPH_PX if n else 0.0


def max_chars(cs):
    return int((AVAIL - GLYPH_PX) / pitch(cs)) + 1


def wrap(text, cs):
    """Word-wrap tham lam như TMP; font đơn cách nên đếm chữ là đủ."""
    cap = max_chars(cs)
    lines, cur = [], ""
    for word in text.split(" "):
        cand = word if not cur else cur + " " + word
        if len(cand) <= cap or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def report(cs):
    print("  characterSpacing %-4s bước chữ %.2f px, tối đa %d chữ/dòng"
          % (cs, pitch(cs), max_chars(cs)))
    over = 0
    for t in TITLES:
        ls = wrap(t, cs)
        if len(ls) > 1:
            over += 1
            print("     %d dòng  %s" % (len(ls), " | ".join(ls)))
    print("     %d/%d mục một dòng" % (len(TITLES) - over, len(TITLES)))
    worst = max((t for t in TITLES if len(wrap(t, cs)) == 1), key=len)
    print("     mục 1 dòng dài nhất: %d chữ, %.1f/%g px (dư %.1f)"
          % (len(worst), width(len(worst), cs), AVAIL, AVAIL - width(len(worst), cs)))


def targets(env):
    out = []
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if t.get("m_fontAsset", {}).get("m_PathID") != FONT_ASSET_PID:
            continue
        if t.get("m_fontSize") != FONT_SIZE:
            continue
        out.append((o, t))
    return out


# (cs, số chữ, có vừa một dòng không) — đọc thẳng từ hai ảnh chụp trong game
CALIBRATION = [
    (7.0, 26, True),    # "Ấn tượng đầu tiên về cô ấy"            một dòng
    (7.0, 27, False),   # "được người yêu nuông chiều?"           bị ngắt
    (7.0, 28, False),   # "Người hợp cạ trong Unlogical"          bị ngắt
    (3.0, 27, True),    # "được người yêu nuông chiều?"           một dòng
    (3.0, 28, False),   # "Người hợp cạ trong Unlogical"          vẫn ngắt
    (3.0, 29, False),   # "Thích làm nũng hay thích được"         bị ngắt
]


def check_model():
    bad = 0
    for cs, n, fits in CALIBRATION:
        w = width(n, cs)
        ok = (w <= AVAIL) == fits
        bad += not ok
        print("   %s cs=%g n=%2d  W=%6.1f  %s (thật: %s)"
              % ("OK " if ok else "SAI", cs, n, w,
                 "vừa" if w <= AVAIL else "ngắt", "vừa" if fits else "ngắt"))
    if bad:
        raise SystemExit("mô hình sai %d/%d mốc — đừng vá cho tới khi khớp" % (bad, len(CALIBRATION)))


def main():
    apply_ = "--apply" in sys.argv
    print("Đối chiếu mô hình với ảnh chụp (khung %g px):" % AVAIL)
    check_model()
    print()
    env = UnityPy.load(UI_JP)
    hits = targets(env)
    print("Tìm thấy %d ô chữ nút Q&A (font DotGothic, cỡ %g)" % (len(hits), FONT_SIZE))
    if len(hits) != 11:
        raise SystemExit("mong đợi 11 ô — dừng lại, có gì đó đã đổi")

    KNOWN = {STOCK_SPACING, 3.0, NEW_SPACING}   # gốc, đợt 1, đích
    changed = 0
    current = None
    for o, t in hits:
        cur = t["m_characterSpacing"]
        current = cur if current is None else current
        if cur not in KNOWN:
            raise SystemExit("pid %d: characterSpacing %s lạ, dừng" % (o.path_id, cur))
        if cur == NEW_SPACING:
            continue
        t["m_characterSpacing"] = NEW_SPACING
        changed += 1
        if apply_:
            o.save_typetree(t)

    print("\nHiện tại (cs=%g):" % current)
    report(current)
    print("Đích (cs=%g):" % NEW_SPACING)
    report(NEW_SPACING)
    print("\n%d/%d ô cần đổi" % (changed, len(hits)))

    if not apply_:
        print("(chạy thử — thêm --apply để ghi)")
        return
    if not changed:
        print("không có gì thay đổi")
        return
    data = env.file.save(packer="lz4")
    if not os.path.exists(BACKUP):
        shutil.copy2(UI_JP, BACKUP)
        print("backup: _backup\\ui_jp.preqaspacing")
    with open(UI_JP, "wb") as f:
        f.write(data)
    print("đã ghi %s (%s byte)" % (UI_JP, format(len(data), ",")))


if __name__ == "__main__":
    main()
