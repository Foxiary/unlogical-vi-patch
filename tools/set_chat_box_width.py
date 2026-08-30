# -*- coding: utf-8 -*-
"""Thu vùng chữ chat **mà không đụng vạch ngăn** — chỉnh `m_margin`, không chỉnh rect.

    python tools\\set_chat_box_width.py                        # xem giá trị hiện tại
    python tools\\set_chat_box_width.py --margin=45 --apply    # thu vùng chữ 45 px bên phải
    python tools\\set_chat_box_width.py --restore              # về stock (1210 / margin 0)

## Vì sao KHÔNG được thu `sizeDelta`

`UnderLine` — cái vạch ngăn giữa các tin — là **con của `Message_TMP`**. Thu rect thì vạch
dịch và đổi cả độ dài, đo được trên máy thật:

| sizeDelta.x | vạch ngăn (px ảnh) | dài |
|---|---|---|
| 1210 (stock) | 318..1600 | 1283 |
| 900 (probe) | 268..1445 | 1178 |

Hai mép dịch **không bằng nhau** (+50 và +155) và độ dài đổi 105 px, dù `UnderLine` khai
cứng 1388 — tức `ChatItemUI` bố trí lại cả hàng, không chỉ ô chữ. Yêu cầu người dùng
30/08/2026: *"vạch phải giống bản Nhật gốc, không chấp nhận bất kì thay đổi vị trí và độ
dài vạch, chỉ tác động phần text box thôi"*. Nên đường `sizeDelta` bị loại.

## `m_margin` làm đúng việc đó

`m_margin` (trái, trên, **phải**, dưới) thu vùng vẽ chữ **bên trong** rect. RectTransform
không đổi ⇒ `UnderLine` đứng yên tuyệt đối, mà TMP vẫn ngắt sớm hơn.

## Con số

Đo ở stock (`_2026-08-30_14-35-09.png`, sizeDelta 1210, margin 0):

    vạch ngăn kết thúc   x = 1600
    chữ chạm tới         x = 1623      -> **lố 23 px ảnh**
    vùng chữ 1210 canvas vẽ ra 1178 px -> tỉ lệ 0,9736

Đây là tỉ lệ của **chính thứ đang chỉnh**, nên dùng nó chứ không dùng tỉ lệ suy từ vạch
ngăn (0,9244) hay từ icon (~0,91) — ba con số đó đá nhau vì `ChatItemUI` vẽ vạch và icon
không theo kích thước khai báo.

`margin.phải = 45` ⇒ vùng chữ còn 1165 canvas = 1134 px ảnh ⇒ chữ dừng ở 445+1134 = **1579**,
tức nằm trong vạch **21 px**.

## Kéo theo: `LIMIT` của `fix_chat_wrap.py`

TMP ngắt đúng ở bề rộng vùng chữ, nhưng **model đo cao hơn TMP ~5%** (kẹp từ cặp A/B:
`W_model/box ∈ [1,049; 1,109)`). Nên `LIMIT` phải là `1165 × 1,049 ≈ 1222`, làm tròn xuống
**1220**. Đặt cao hơn thì ngắt cứng dài hơn khung, TMP ngắt lại giữa mệnh đề.

LayeredFS chỉ đọc `ui_jp` lúc boot ⇒ **phải tắt game rồi mở lại** mới thấy.
"""
import io
import os
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

import UnityPy   # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BACKUP = os.path.join(ROOT, "_backup", "ui_jp.chatboxwidth")
STOCK_WIDTH, STOCK_MARGIN = 1210.0, 0.0

APPLY = "--apply" in sys.argv
RESTORE = "--restore" in sys.argv


def arg(name):
    for a in sys.argv:
        if a.startswith("--%s=" % name):
            return float(a.split("=")[1])
    return None


WIDTH = arg("width")
MARGIN = arg("margin")
if RESTORE:
    WIDTH, MARGIN = STOCK_WIDTH, STOCK_MARGIN


def locate(env):
    """(rect_obj, rect_tt, tmp_obj, tmp_tt) của `GenebarkChatContentItem › Message_TMP`."""
    GO, OBJ = {}, {}
    for o in env.objects:
        OBJ[o.path_id] = o
        if o.type.name == "GameObject":
            try:
                GO[o.path_id] = o.read()
            except Exception:
                pass

    def nm(pid):
        g = GO.get(pid)
        return getattr(g, "m_Name", "") if g else ""

    for o in env.objects:
        if o.type.name != "RectTransform":
            continue
        try:
            tt = o.read_typetree()
        except Exception:
            continue
        pid = tt.get("m_GameObject", {}).get("m_PathID")
        if nm(pid) != "Message_TMP":
            continue
        try:
            par = o.read().m_Father.read()
            if nm(par.m_GameObject.path_id) != "GenebarkChatContentItem":
                continue
        except Exception:
            continue
        for cp in GO[pid].m_Component:
            c = OBJ.get(cp.component.path_id)
            if c is None or c.type.name != "MonoBehaviour":
                continue
            try:
                ct = c.read_typetree()
            except Exception:
                continue
            if "m_margin" in ct:
                return o, tt, c, ct
        raise SystemExit("không thấy component TMP trên Message_TMP")
    raise SystemExit("không thấy GenebarkChatContentItem › Message_TMP")


def show(tt, ct, tag):
    m = ct["m_margin"]
    print("%-10s sizeDelta.x = %7.1f | m_margin = (trái %.1f, trên %.1f, PHẢI %.1f, dưới %.1f)"
          % (tag, tt["m_SizeDelta"]["x"], m["x"], m["y"], m["z"], m["w"]))


def main():
    env = UnityPy.load(BUNDLE)
    ro, rt, to, ct = locate(env)
    show(rt, ct, "hiện tại")
    if WIDTH is None and MARGIN is None:
        print("\nthêm --margin=N --apply để thu vùng chữ (KHÔNG đụng vạch),")
        print("hoặc --restore để về stock (%.0f / margin %.0f)" % (STOCK_WIDTH, STOCK_MARGIN))
        return

    w = rt["m_SizeDelta"]["x"] if WIDTH is None else WIDTH
    mg = ct["m_margin"]["z"] if MARGIN is None else MARGIN
    if w != STOCK_WIDTH:
        print("\n!! sizeDelta.x = %.1f khác stock %.0f — vạch ngăn SẼ dịch. Xem docstring."
              % (w, STOCK_WIDTH))
    if rt["m_SizeDelta"]["x"] == w and ct["m_margin"]["z"] == mg:
        print("đã đúng giá trị đó, không cần ghi")
        return
    print("sẽ đặt     sizeDelta.x = %7.1f | m_margin.PHẢI = %.1f" % (w, mg))
    if not APPLY and not RESTORE:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    rt["m_SizeDelta"]["x"] = w
    ro.save_typetree(rt)
    ct["m_margin"]["z"] = mg
    to.save_typetree(ct)

    bak, i = BACKUP, 2
    while os.path.exists(bak):
        bak = "%s-%d" % (BACKUP, i)
        i += 1
    shutil.copy2(BUNDLE, bak)
    print("backup ->", bak)
    with open(BUNDLE, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi", BUNDLE, os.path.getsize(BUNDLE))

    _, rt2, _, ct2 = locate(UnityPy.load(BUNDLE))
    show(rt2, ct2, "đọc lại")
    assert rt2["m_SizeDelta"]["x"] == w and ct2["m_margin"]["z"] == mg, "đọc lại không khớp"
    print("\nPHẢI TẮT GAME RỒI MỞ LẠI — LayeredFS chỉ đọc ui_jp lúc boot.")


main()
