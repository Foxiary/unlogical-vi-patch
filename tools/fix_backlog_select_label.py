r"""Dịch nhãn `選択肢` của dòng lựa chọn trong BACKLOG — và nới ô cho khỏi rớt chữ.

ĐÍNH CHÍNH 28/08/2026: **bản vá chuỗi này không đủ.** Máy thật chạy release v1.2.6 vẫn
hiện `選択肢` dù `ui_jp` trong zip đã mang `Choice`. Code ghi đè cả ô `Log_Base_SELECT`
chứ không riêng ba template kia — chuỗi thật là literal IL2CPP #15084, đã vá bằng
`fix_sound_tab_name.py` (backup `_backup\global-metadata.dat.presoundnames`).
Giữ bản vá prefab vì nó là placeholder, để cho khớp.

ĐÍNH CHÍNH 29/08/2026: chuỗi đã lên hình, nhưng **rớt chữ `e` xuống dòng hai**
(`Choic` / `e`). Ghi chú cũ ở đây nói sai:

> `Choice` là một từ, không có chỗ ngắt, nên `m_TextWrappingMode = 1` không thể
> đẩy nó xuống dòng hai.

Sai. Khi **một từ** đã dài hơn bề ngang ô, TMP không còn chỗ ngắt hợp lệ nào nên
nó rơi xuống ngắt **giữa từ**, từng ký tự một. `overflowMode = Overflow` không cứu
được: Overflow chỉ cho chữ tràn *xuống dưới* sau khi đã ngắt dòng, chứ không tắt ngắt.
Chỉ `m_TextWrappingMode = 0` (NoWrap) mới cho chữ chạy ngang ra ngoài ô.

Màn BACKLOG dựng mỗi dòng từ một template nằm sẵn trong
`ui_jp` → `assets/assetbundleresources/ui/ローカライズ/jp/adv/backlog/backlog_scrollview.prefab`
dưới `Scroll View/Viewport/Content`:

    Log_Base              BackName_TMP  ô 1010x50  = 「矢代」    ← placeholder, code ghi đè
    Log_Base_Chat         BackName_TMP  ô  120x50  = 「Suzuno」  ← placeholder, code ghi đè
    Log_Base_Chat_Select  BackName_TMP  ô  120x50  = 「Suzuno」  ← placeholder, code ghi đè
    Log_Base_SELECT       BackName_TMP  ô  120x50  = 「選択肢」  ← nhãn cố định, hiện thẳng

Dòng thoại thường (`Log_Base`) không hề rớt chữ vì ô của nó rộng 1010 px —
`Suzuno Kanna` (285.9 px) thoải mái. Chỉ ba template kia giữ ô 120 px.

Đo bằng `adv_layout` (`FOT-NewRodinProN-DB SDF-Dynamic`, cỡ 32, `characterSpacing` 4):

    選択肢    102.6 px   ← vừa ô 120
    Choice    138.6 px   ← quá 18.6 px  →  TMP ngắt giữa từ

Chỗ trống bên phải nhãn là bao nhiêu, đo từ chính prefab: `BackName_TMP` neo giữa,
`pivot.x = 0`, `anchoredPosition.x = -821`; `BasePanel` (khung trắng, 1220 px) ở
`x = -280` nên mép phải khung là `+330`. Từ mép trái nhãn tới mép phải khung còn
**1151 px** — nới ô không chạm gì.

    m_SizeDelta.x        120 -> 240     đủ cho cả nhãn hai từ (`Lựa chọn` 185.8 px)
    m_TextWrappingMode     1 -> 0       NoWrap: không bao giờ có dòng thứ hai

`pivot.x = 0` + canh trái nên nới ô **ghim mép trái, chỉ đẩy mép phải ra** — chữ
không nhúc nhích. Ba anh em `log` / `Image` / `Voice` trong template SELECT đều
`m_IsActive = False`, mà `BackName_TMP` lại là con của chính `Log_Base_SELECT`
(nơi gắn `EventTriggerButton`), nên ô chữ tuy `m_RaycastTarget = 1` cũng không
cướp được click của ai.

`Choice` bám theo cách gọi sẵn có của bản vá: ô `SKIP CHOICES` ở màn CONFIG
(tranh vẽ trong atlas) đã dịch 選択肢 thành "choices".

Không đụng `uiGroups[0].groupName = 「選択肢テキスト」` trong `genebark.prefab` —
đó là tên nhóm animation, khóa tra cứu, không hiện ra màn hình.

    python tools\fix_backlog_select_label.py [--apply]

Backup: `_backup\ui_jp.prebacklogselectrect`.
Chạy lại vô hại: phần nào đã đúng thì bỏ qua.
"""

import io
import os
import shutil
import sys

import UnityPy

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BACKUP = os.path.join(ROOT, "_backup", "ui_jp.prebacklogselectrect")

TEXT_PID = 3166427734803632352     # Log_Base_SELECT/BackName_TMP  (TextMeshProUGUI)
RECT_PID = -4634876419618557773    # RectTransform của chính ô đó
OLD = "選択肢"
NEW = "Choice"
OLD_W, NEW_W = 120.0, 240.0
NOWRAP = 0


def find(env, pid):
    for o in env.objects:
        if o.path_id == pid:
            return o
    return None


def main():
    apply = "--apply" in sys.argv

    UnityPy.config.FALLBACK_UNITY_VERSION = "2021.3.0f1"
    env = UnityPy.load(BUNDLE)
    tmp, rect = find(env, TEXT_PID), find(env, RECT_PID)
    if tmp is None or rect is None:
        print("KHÔNG thấy ô chữ / RectTransform của Log_Base_SELECT trong ui_jp")
        return 1

    tt, rt = tmp.read_typetree(), rect.read_typetree()
    cur, wrap, w = tt["m_text"], tt["m_TextWrappingMode"], rt["m_SizeDelta"]["x"]
    print("Log_Base_SELECT/BackName_TMP")
    print(f"  m_text             = {cur!r}")
    print(f"  m_SizeDelta.x      = {w:g}")
    print(f"  m_TextWrappingMode = {wrap}")

    if cur not in (OLD, NEW):
        print(f"Chuỗi lạ (chờ {OLD!r} hoặc {NEW!r}) — dừng, kiểm tra tay.")
        return 1
    if w not in (OLD_W, NEW_W):
        print(f"Bề rộng lạ: {w:g} (chờ {OLD_W:g} hoặc {NEW_W:g}) — dừng, kiểm tra tay.")
        return 1

    todo = []
    if cur != NEW:
        todo.append(f"m_text {cur!r} -> {NEW!r}")
    if w != NEW_W:
        todo.append(f"m_SizeDelta.x {w:g} -> {NEW_W:g}")
    if wrap != NOWRAP:
        todo.append(f"m_TextWrappingMode {wrap} -> {NOWRAP} (NoWrap)")

    if not todo:
        print("Đã đúng cả rồi — không cần làm gì.")
        return 0
    print("cần sửa: " + "; ".join(todo))
    if not apply:
        print("--apply để ghi")
        return 0

    if not os.path.exists(BACKUP):
        shutil.copy(BUNDLE, BACKUP)
        print(f"backup → {BACKUP}")

    tt["m_text"] = NEW
    tt["m_TextWrappingMode"] = NOWRAP
    tmp.save_typetree(tt)
    rt["m_SizeDelta"]["x"] = NEW_W
    rect.save_typetree(rt)

    blob = env.file.save(packer="lz4")
    del env
    with open(BUNDLE, "wb") as fh:
        fh.write(blob)
    print(f"đã ghi {BUNDLE} ({len(blob):,} byte)")

    # đọc lại từ đĩa, đừng tin giá trị trong bộ nhớ
    chk = UnityPy.load(BUNDLE)
    t2 = find(chk, TEXT_PID).read_typetree()
    r2 = find(chk, RECT_PID).read_typetree()
    got = (t2["m_text"], r2["m_SizeDelta"]["x"], t2["m_TextWrappingMode"])
    want = (NEW, NEW_W, NOWRAP)
    print(f"đọc lại từ đĩa: text={got[0]!r} w={got[1]:g} wrap={got[2]}  →  "
          f"{'OK' if got == want else 'HỎNG'}")
    return 0 if got == want else 1


if __name__ == "__main__":
    sys.exit(main())
