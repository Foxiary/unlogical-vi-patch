"""Dịch nhãn `選択肢` của dòng lựa chọn trong BACKLOG.

Màn BACKLOG dựng mỗi dòng từ một template nằm sẵn trong
`ui_jp` → `assets/assetbundleresources/ui/ローカライズ/jp/adv/backlog/backlog_scrollview.prefab`
dưới `Scroll View/Viewport/Content`:

    Log_Base              BackName_TMP = 「矢代」      ← placeholder, code ghi đè
    Log_Base_Chat         BackName_TMP = 「Suzuno」    ← placeholder, code ghi đè
    Log_Base_Chat_Select  BackName_TMP = 「Suzuno」    ← placeholder, code ghi đè
    Log_Base_SELECT       BackName_TMP = 「選択肢」    ← **nhãn cố định, hiện thẳng**

Ba template kia mang tên nhân vật giả (`矢代`, `Suzuno`, `ダミーテキスト`) vì code
ghi đè lúc chạy. `Log_Base_SELECT` thì không có người nói — chuỗi trong prefab
chính là chữ chạy trên máy, nên nó là chỗ duy nhất phải sửa.

Ô chữ 120×50, cỡ 32, `characterSpacing` 4, pivot x=0, canh trái, `overflowMode`
= Overflow:

    選択肢    102.6 px      Choice   138.6 px

Tràn 19 px sang phải là **vô hại** — bên phải nhãn là khoảng trống trên nóc khung
trắng, và ba template kia vốn đã tràn nhiều hơn thế (`Suzuno Kanna` ≈ 250 px
trong đúng ô 120 px). Quan trọng hơn: `Choice` là **một từ**, không có chỗ ngắt,
nên `m_TextWrappingMode = 1` không thể đẩy nó xuống dòng hai. Nhãn hai từ
(`Lựa chọn`, `SKIP CHOICES`…) thì có thể — đừng đặt vào đây.

`Choice` bám theo cách gọi sẵn có của bản vá: ô `SKIP CHOICES` ở màn CONFIG
(tranh vẽ trong atlas) đã dịch 選択肢 thành "choices".

Không đụng `uiGroups[0].groupName = 「選択肢テキスト」` trong `genebark.prefab` —
đó là tên nhóm animation, khóa tra cứu, không hiện ra màn hình.

    python tools\fix_backlog_select_label.py [--apply]
"""

import io
import os
import shutil
import sys

import UnityPy

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BACKUP = os.path.join(ROOT, "_backup", "ui_jp.prebacklogselect")

PATH_ID = 3166427734803632352      # Log_Base_SELECT/BackName_TMP
OLD = "選択肢"
NEW = "Choice"


def find(env):
    for o in env.objects:
        if o.type.name == "MonoBehaviour" and o.path_id == PATH_ID:
            return o
    return None


def main():
    apply = "--apply" in sys.argv

    UnityPy.config.FALLBACK_UNITY_VERSION = "2021.3.0f1"
    env = UnityPy.load(BUNDLE)
    obj = find(env)
    if obj is None:
        print(f"KHÔNG thấy MonoBehaviour {PATH_ID} trong ui_jp"); return 1

    tree = obj.read_typetree()
    cur = tree["m_text"]
    print(f"Log_Base_SELECT/BackName_TMP  m_text = {cur!r}")

    if cur == NEW:
        print("Đã dịch rồi — không cần làm gì."); return 0
    if cur != OLD:
        print(f"Chuỗi lạ (chờ {OLD!r}) — dừng, kiểm tra tay."); return 1

    if not apply:
        print(f"--apply để đổi thành {NEW!r} (ô 120 px, tràn 19 px sang phải, một từ nên không xuống dòng)")
        return 0

    if not os.path.exists(BACKUP):
        shutil.copy(BUNDLE, BACKUP)
        print(f"backup → {BACKUP}")

    tree["m_text"] = NEW
    obj.save_typetree(tree)
    blob = env.file.save(packer="lz4")
    del env
    with open(BUNDLE, "wb") as fh:
        fh.write(blob)
    print(f"đã ghi {BUNDLE} ({len(blob):,} byte)")

    # đọc lại từ đĩa, đừng tin giá trị trong bộ nhớ
    chk = UnityPy.load(BUNDLE)
    got = find(chk).read_typetree()["m_text"]
    print(f"đọc lại từ đĩa: m_text = {got!r}  →  {'OK' if got == NEW else 'HỎNG'}")
    return 0 if got == NEW else 1


if __name__ == "__main__":
    sys.exit(main())
