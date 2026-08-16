# -*- coding: utf-8 -*-
"""Nới rộng ô tiêu đề trong danh sách SHORT STORY (màn "SS LIST").

Hàng danh sách là prefab `SS_Button` trong `sharedassets17.assets`:

    SS_Button            628 x 64   (Image kiểu Sliced — nền hồng của dòng đang chọn)
      New                48 x 20    @ x=-343   (nhãn NEW, nằm ngoài mép trái)
      OFF / ON           Num + Mail @ x=-246 / -186
      Text (TMP)         căng hết khung, m_margin = (181, 0, 30, 0)

nên bề rộng chữ thật sự chỉ có 628 - 181 - 30 = **417 px**, ở cỡ 32 /
characterSpacing 4. Sáu tiêu đề tiếng Việt vượt quá con số đó và bị xuống hàng
(hàng cao 64 px, overflowMode = Overflow nên chữ tràn ra cả trên lẫn dưới).

Bên phải danh sách còn trống: mép phải nền hồng ở x=1321.5, thanh cuộn
(`Slider` của `level17`) bắt đầu ở x=1372, cột 1320..1374 hoàn toàn trống trên
ảnh chụp 1920x1080.

`Buttons` (level17 pid 39) có `VerticalLayoutGroup` với `m_ChildControlWidth=0`
và `m_ChildAlignment=UpperCenter`, nên hàng được đặt bằng

    mép trái = 960 + m_Padding.m_Left/2 - W/2

Tăng W mà không đụng padding thì nền hồng nở đều sang **cả hai bên** và nuốt
mất nhãn NEW. Vì vậy phải tăng padding kèm theo để giữ nguyên mép trái, rồi dời
các con của prefab (neo theo tâm) ngược lại đúng nửa phần nở thêm.

Kết quả: chỉ mép phải của nền hồng dịch ra, mọi thứ khác đứng yên từng pixel,
bề rộng chữ 417 -> 483 px — đủ cho cả 20 tiêu đề nằm một dòng
(dài nhất là "Chiếc tai nghe bỏ quên", 467 px).
"""
import os
import shutil
import sys

import UnityPy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ROMFS = os.path.join(ROOT, "romfs", "Data")
STOCK = r"D:\Downloads\UNLOGICAL_v2\Data"
BACKUP = os.path.join(ROOT, "_backup")
UI_JP = os.path.join(ROMFS, "StreamingAssets", "ui", "ui_jp")

SUFFIX = "presswidth"

OLD_W = 628.0
NEW_W = 676.0
SHIFT = (NEW_W - OLD_W) / 2.0          # 24 — tâm hàng dịch sang phải bấy nhiêu
OLD_PAD_LEFT = 95
NEW_PAD_LEFT = int(round(OLD_PAD_LEFT + (NEW_W - OLD_W)))   # 143
NEW_MARGIN_RIGHT = 12.0

# sharedassets17.assets
RT_BUTTON = 114        # SS_Button
RT_NEW = 119           # New
RT_OFF = 115           # OFF
RT_ON = 111            # ON
MB_TEXT = 134          # Text (TMP) — TextMeshProUGUI
# level17
MB_LAYOUT = 222        # Buttons — VerticalLayoutGroup


def borrow_nodes(*required):
    """TMP/uGUI không nhúng type tree trong các file .assets này — mượn của ui_jp."""
    env = UnityPy.load(UI_JP)
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            tt = o.read_typetree()
        except Exception:
            continue
        if all(k in tt for k in required):
            return o.serialized_type.node
    raise SystemExit("khong tim thay type tree cho %s trong ui_jp" % (required,))


def stage(name):
    """Đưa file gốc 1.0.2 vào romfs nếu bản vá chưa có, và lưu backup."""
    dst = os.path.join(ROMFS, name)
    bak = os.path.join(BACKUP, name + "." + SUFFIX)
    if not os.path.exists(dst):
        src = os.path.join(STOCK, name)
        if not os.path.exists(src):
            raise SystemExit("khong thay %s trong ban goc 1.0.2" % name)
        print("  + chep tu ban goc 1.0.2: %s" % name)
        shutil.copy2(src, dst)
    if not os.path.exists(bak):
        shutil.copy2(dst, bak)
        print("  + backup: _backup\\%s" % os.path.basename(bak))
    return dst


def patch_prefab(path, apply_):
    tmp_nodes = borrow_nodes("m_enableAutoSizing", "m_margin")
    env = UnityPy.load(path)
    objs = {o.path_id: o for o in env.objects}
    changed = False

    def set_rect(pid, label, **fields):
        nonlocal changed
        tt = objs[pid].read_typetree()
        for key, (sub, val) in fields.items():
            cur = tt[key][sub]
            if cur == val:
                print("    = %-10s %s.%s da la %g" % (label, key, sub, val))
                continue
            print("    * %-10s %s.%s %g -> %g" % (label, key, sub, cur, val))
            tt[key][sub] = val
            changed = True
        if apply_:
            objs[pid].save_typetree(tt)

    set_rect(RT_BUTTON, "SS_Button", m_SizeDelta=("x", NEW_W))
    set_rect(RT_NEW, "New", m_AnchoredPosition=("x", -343.0 - SHIFT))
    set_rect(RT_OFF, "OFF", m_AnchoredPosition=("x", -SHIFT))
    set_rect(RT_ON, "ON", m_AnchoredPosition=("x", -SHIFT))

    tt = objs[MB_TEXT].read_typetree(tmp_nodes)
    if tt["m_margin"]["z"] != NEW_MARGIN_RIGHT:
        print("    * %-10s m_margin.z %g -> %g"
              % ("Text (TMP)", tt["m_margin"]["z"], NEW_MARGIN_RIGHT))
        tt["m_margin"]["z"] = NEW_MARGIN_RIGHT
        changed = True
        if apply_:
            objs[MB_TEXT].save_typetree(tt, tmp_nodes)
    else:
        print("    = %-10s m_margin.z da la %g" % ("Text (TMP)", NEW_MARGIN_RIGHT))

    avail = NEW_W - tt["m_margin"]["x"] - NEW_MARGIN_RIGHT
    print("    -> be rong chu: %g px" % avail)
    return env, changed


def patch_scene(path, apply_):
    vlg_nodes = borrow_nodes("m_ChildForceExpandWidth", "m_Spacing")
    env = UnityPy.load(path)
    objs = {o.path_id: o for o in env.objects}
    tt = objs[MB_LAYOUT].read_typetree(vlg_nodes)
    changed = False
    cur = tt["m_Padding"]["m_Left"]
    if cur != NEW_PAD_LEFT:
        print("    * %-10s m_Padding.m_Left %d -> %d" % ("Buttons", cur, NEW_PAD_LEFT))
        tt["m_Padding"]["m_Left"] = NEW_PAD_LEFT
        changed = True
        if apply_:
            objs[MB_LAYOUT].save_typetree(tt, vlg_nodes)
    else:
        print("    = %-10s m_Padding.m_Left da la %d" % ("Buttons", NEW_PAD_LEFT))
    left = 960 + tt["m_Padding"]["m_Left"] / 2.0 - NEW_W / 2.0
    print("    -> nen hong: x %g .. %g" % (left, left + NEW_W))
    return env, changed


def write(env, path):
    data = env.file.save()
    with open(path, "wb") as f:
        f.write(data)


def main():
    apply_ = "--apply" in sys.argv
    print("sharedassets17.assets (prefab SS_Button)")
    p1 = stage("sharedassets17.assets") if apply_ else os.path.join(
        ROMFS if os.path.exists(os.path.join(ROMFS, "sharedassets17.assets")) else STOCK,
        "sharedassets17.assets")
    env1, ch1 = patch_prefab(p1, apply_)

    print("level17 (VerticalLayoutGroup cua Buttons)")
    p2 = stage("level17") if apply_ else os.path.join(
        ROMFS if os.path.exists(os.path.join(ROMFS, "level17")) else STOCK, "level17")
    env2, ch2 = patch_scene(p2, apply_)

    if not apply_:
        print("\n(chay thu — them --apply de ghi)")
        return
    if ch1:
        write(env1, p1)
        print("da ghi %s" % p1)
    if ch2:
        write(env2, p2)
        print("da ghi %s" % p2)
    if not (ch1 or ch2):
        print("khong co gi thay doi")


if __name__ == "__main__":
    main()
