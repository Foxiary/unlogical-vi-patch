# -*- coding: utf-8 -*-
"""Ba tab TERMINAL cùng một font mà giãn chữ khác nhau, nên trông không đồng bộ.

Ảnh chụp máy thật `_2026-09-02_00-42-11.png` (HOME), `_2026-09-02_00-44-48.png`
(RULE) và `_2026-09-02_00-45-17.png` (CONTROL): chữ thân bài của HOME và CONTROL
rời rạc hơn RULE rõ rệt, dù cả ba đều vẽ bằng `FOT-iroha21popuraStdN-R`
(pointSize 58, pathID -7493831502989913688).

## Vì sao

`m_characterSpacing` của bản gốc khác nhau giữa các tab:

| tab                                | component                            |    cs | cỡ chữ | giãn thực |
|------------------------------------|--------------------------------------|-------|--------|-----------|
| RULE — thân bài                    | `Terminal_Rule_Item/Text (TMP)`      | −9,80 |     33 | −3,23 px  |
| RULE — ruy-băng tiêu đề            | `RuleText/TitleText/Text (TMP)`      | −8,00 |     33 | −2,64 px  |
| HOME — list Information            | `Terminal_Home_Item/Text (TMP)` ×7   |  0,00 |     31 |  0,00 px  |
| CONTROL — Request / Caption        | `Request_Mask` / `Caption_Mask`      |  0,00 |     31 |  0,00 px  |

Giãn thực = `cs × cỡ chữ / 100` (xem `docs/02-text-rendering.md`) — tức `cs`
chính là phần trăm cỡ chữ, nên **giữ nguyên trị số `cs` mới cho ra độ chặt
tương đối y hệt** giữa hai cỡ chữ khác nhau, không cần quy đổi theo px.

Đo lại trên hai ảnh chụp, lấy chữ `Stage` có ở cả hai màn (không dấu, không dấu
câu), tính từ mép trái `S` sang mép trái `e` — tức 4 bước chữ:

| màn                | S→t | t→a | a→g | g→e | tổng | bề rộng mực |
|--------------------|-----|-----|-----|-----|------|-------------|
| HOME  (fs 31, cs 0)|  22 |  16 |  19 |  20 |  77  |  92 px      |
| RULE  (fs 33, −9,8)|  20 |  13 |  18 |  18 |  69  |  85 px      |

Mô hình dự đoán RULE `77 × 33/31 − 4 × 9,8 × 0,33 = 69,03`, đo được 69 — khớp.
Font RULE **to hơn 6,45%** mà chữ vẫn **hẹp hơn 7 px**: toàn bộ là do −9,8.

## Vá gì

Đặt `cs = −9,80` cho 9 component thân bài của HOME và CONTROL. Ở cỡ 31 thì ra
−3,04 px mỗi khoảng, chặt bằng RULE theo tỉ lệ.

Không đụng bề rộng khung, cỡ chữ, chế độ ngắt dòng hay tự thu chữ. Chặt hơn thì
dòng chỉ ngắn lại, nên không có nguy cơ tràn:

- 7 ô HOME `autoSize = 0`, khung căng theo cha, `wrap = 1` — hẹp lại là an toàn.
- 2 ô CONTROL `autoSize = 1` khoảng [18, 31] — chặt hơn thì càng dễ giữ cỡ 31.

## Hai component cố tình bỏ qua

`Terminal_Control/TerminalBgBase/Infomation_Mask/InfoText (TMP)` (cs 0) và
`... InfoText (TMP) _old` (cs 2,2) đều nằm dưới `Infomation_Mask` có
`m_IsActive = False` — tắt, không vẽ ra màn nào. Sửa chúng chỉ làm nhiễu diff.

    python tools\\fix_terminal_char_spacing.py            # chạy thử, in trước/sau
    python tools\\fix_terminal_char_spacing.py --check    # thoát 1 nếu chưa vá
    python tools\\fix_terminal_char_spacing.py --apply
"""
import io
import os
import shutil
import sys

import UnityPy

if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

UI = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BACKUP = os.path.join(ROOT, "_backup", "ui_jp.precharspacing")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

# Trị số của `Terminal_Rule_Item/Text (TMP)`, tab RULE — cái đang lấy làm chuẩn.
WANT = -9.8
RULE_BODY = -8732120151617823771

# 7 ô HOME: 6 thực thể đặt sẵn trong scene + 1 prefab để sinh lúc chạy. Phải vá
# cả prefab, không thì mục sinh thêm vẫn giãn 0.
TARGETS = [
    (8503704623889298203, "Terminal_Home/BG/Information/Content/Item_-01/Text (TMP)"),
    (4190942317839026408, "Terminal_Home/BG/Information/Content/Item_00/Text (TMP)"),
    (1281219418852516960, "Terminal_Home/BG/Information/Content/Item_01/Text (TMP)"),
    (-3403318670424453259, "Terminal_Home/BG/Information/Content/Item_02/Text (TMP)"),
    (-6151564287456425605, "Terminal_Home/BG/Information/Content/Item_03/Text (TMP)"),
    (-6639743317130076003, "Terminal_Home/BG/Information/Content/Item_04/Text (TMP)"),
    (1039395467938190513, "Terminal_Home_Item/Text (TMP)"),
    (6739595937050545782, "Terminal_Control/.../Request_Mask/Request/RequestText (TMP)"),
    (-5430722347680546159, "Terminal_Control/.../Caption_Mask/Caption/CaptionText (TMP) (1)"),
]


def load_ui():
    env = UnityPy.load(UI)
    objs = {o.path_id: o for o in env.objects if o.type.name == "MonoBehaviour"}
    return env, objs


def main():
    env, objs = load_ui()

    ref = objs[RULE_BODY].read_typetree()
    print("chuẩn: Terminal_Rule_Item/Text (TMP)  cs=%.2f  cỡ %.0f  ->  %.2f px/khoảng"
          % (ref["m_characterSpacing"], ref["m_fontSize"],
             ref["m_characterSpacing"] * ref["m_fontSize"] / 100.0))
    if abs(ref["m_characterSpacing"] - WANT) > 0.001:
        print("DỪNG: tab RULE không còn là %.2f, xem lại chuẩn" % WANT)
        sys.exit(2)
    print()

    print("%-60s %7s %7s %6s %10s" % ("component", "cs cũ", "cs mới", "cỡ", "px/khoảng"))
    plans, ok = [], True
    for pid, name in TARGETS:
        o = objs[pid]
        d = o.read_typetree()
        cs, fs = d["m_characterSpacing"], d["m_fontSize"]
        done = abs(cs - WANT) < 0.001
        ok = ok and done
        print("%-60s %7.2f %7.2f %6.0f %10.2f%s"
              % (name, cs, WANT, fs, WANT * fs / 100.0, "" if not done else "   (đã vá)"))
        plans.append((o, d, name))

    if CHECK:
        print("\n%s" % ("khớp: cả %d ô đã ở %.2f" % (len(TARGETS), WANT) if ok else "CHƯA VÁ"))
        sys.exit(0 if ok else 1)
    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return
    if ok:
        print("\nkhông có gì để làm")
        return

    if not os.path.exists(BACKUP):
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        shutil.copy2(UI, BACKUP)
        print("\nbackup ->", os.path.relpath(BACKUP, ROOT))
    for o, d, name in plans:
        d["m_characterSpacing"] = WANT
        o.save_typetree(d)
    with open(UI, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi %s  %d byte" % (os.path.relpath(UI, ROOT), os.path.getsize(UI)))

    # đọc lại từ đĩa
    env2, objs2 = load_ui()
    for pid, name in TARGETS:
        d = objs2[pid].read_typetree()
        assert abs(d["m_characterSpacing"] - WANT) < 0.001, name
    print("  đọc lại: %d/%d ô ở cs=%.2f  OK" % (len(TARGETS), len(TARGETS), WANT))
    print("  %d object trong bundle" % sum(1 for _ in env2.objects))


if __name__ == "__main__":
    main()
