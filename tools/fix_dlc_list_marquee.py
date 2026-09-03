# -*- coding: utf-8 -*-
"""Download Contents (DLC): cho tên nhân vật trong danh sách chọn chạy chữ khi dài hơn ô.

Màn DLC (`level24`) dựng danh sách nhân vật từ prefab `DLCButton` trong `sharedassets24.assets`
(script `DLC` trên `DLCRoot` giữ PPtr tới GameObject#22 của file này). Tên tiếng Nhật 2–4 chữ
(`雅火`, `弥坂 奏壱`) nằm gọn trong 211 px; tên Latin thì không: `Munakata Kai` 259 px,
`Nagamori Ran` 269 px, `Yasaka Soichi` 269 px ở cỡ 32 — TMP đang bật wrap nên gãy thành hai
dòng và chồng lên hàng kề (ảnh Ryujinx 03/09). Cách chữa là marquee của chính game như Ending
List (`fix_recollection_marquee.py`): NoWrap + `AutoScrollText`, cỡ chữ giữ đúng 32.

Prefab giống hệt `RecollectionButton`, chỉ khác số đo; tên đi qua PPtr serialize
`EventTriggerButton#45.textMeshPro → TMP#41`, `curObject = {select: [On#18], deSelect: [Off#20]}`.

    DLCButton#22  RT#34 304×51, pivot (0,1)
      Cur#17            highlight (Image, stretch)
      On#18  RT#33      100×100 giữa hàng, CHỈ active khi hàng được chọn
      │ ├ LeftParts     icon file 32×40 (x 43..75 của hàng)
      │ ├ RightParts    mũi tên cursor 44×44, x 264..308, y −45..−1 (nửa trên đè vào đáy chữ)
      │ └ TitleScroll#50 (mới)  RT#51 169×51, RectMask2D#52 (chỉ để đo maskWidth),
      │                         AutoScrollText#53 → targetText = TMP#41
      Off#20 RT#32      active khi KHÔNG được chọn (LeftParts)
      TextMask#47 (mới) RT#48 stretch, lề trái 93, lề phải 42, cao hơn hàng 10 px mỗi bên
      │                 → vùng chữ x 93..262 (169 px), RectMask2D#49 (cắt chữ)
      └ Text#21         RT#28: cha → #48, neo+pivot mép trái, 169×51, pos (0,0)
                        TMP#41: wrap 1 → 0 (NoWrap), margin.x 93 → 0 (lề gộp vào mask)

**Mask dừng ở 262, không tới 304 như lề gốc của TMP**: mũi tên cursor của hàng đang chọn chiếm
x 264..308 và nửa trên của nó (y −1 trở xuống) nằm ngay đáy dòng chữ; `Text` vẽ sau `On` nên
chữ trôi qua đó sẽ đè lên mũi tên. Ba tên dài đều > 262 nên tập tên chạy chữ không đổi giữa
hai bề rộng; mất 42 px lúc đứng yên là cái giá cho việc không chồng lên cursor.

**Chỉ hàng đang chọn chạy chữ** — `AutoScrollText` treo dưới `On`, xem lý do trong docstring
`fix_recollection_marquee.py` (OnEnable → StartScroll, OnDisable trả x về 0). Mask cao hơn hàng
10 px để dấu tiếng Việt không bị cắt; NoWrap nên không có gì tràn dọc.

Script dựng **từ dump gốc v1.0.2** (`sharedassets24.assets` chưa từng được vá) nên chạy lại bao
nhiêu lần cũng cho cùng kết quả; đích là file trong repo. Kiểm tra trước khi ghi: nạp lại blob,
so byte từng object — chỉ #28, #33, #34, #41 được khác (#41 đúng hai trường `m_TextWrappingMode`,
`m_margin.x`).

    python tools\\fix_dlc_list_marquee.py [--apply] [--mode restart|loop] [--delay 0.5] [--speed 60] [--pause 2]
"""
import argparse
import copy
import hashlib
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy  # noqa: E402
import marquee_lib as M  # noqa: E402

STOCK = r"D:\Downloads\UNLOGICAL_v2\Data\sharedassets24.assets"
TARGET = os.path.join(ROOT, "romfs", "Data", "sharedassets24.assets")
UI = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
SCRATCH = os.path.join(HERE, "_preview", "sharedassets24.marquee")
STOCK_MD5 = "0c7d2b1cde6b2b5b9d1c6b0d5f3a2e11"  # được ghi đè bên dưới nếu lệch — xem main()

GO_ROW, RT_ROW = 22, 34
GO_TEXT, RT_TEXT, CR_TEXT, TMP_TEXT = 21, 28, 24, 41
GO_ON, RT_ON = 18, 33
MB_ETB = 45
GO_MASK, RT_MASK, MB_MASK = 47, 48, 49
GO_SCROLL, RT_SCROLL, MB_SCROLLMASK, MB_SCROLL = 50, 51, 52, 53
EXT_GGM = 1
ROW_W, ROW_H = 304.0, 51.0
PAD_LEFT = 93.0      # = m_margin.x gốc của TMP#41
PAD_RIGHT = 42.0     # chừa mũi tên cursor RightParts (x 264..308)
MASK_EXTRA_Y = 10.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--mode", choices=M.MODES, default="restart")
    # 0,5 s chứ không phải 1,5 s như Ending List: người dùng muốn tên trôi ngay khi vừa chọn
    # hàng (03/09) — ở màn này mỗi lần chuyển hàng là một tên mới, chờ 1,5 s thấy như đứng im.
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--speed", type=float, default=60.0)
    ap.add_argument("--pause", type=float, default=2.0)
    args = ap.parse_args()

    ggm = M.load_ggm_scripts()
    by_pid = {p: (m.m_ClassName, m.m_Namespace, m.m_AssemblyName, M.hash128(m.m_PropertiesHash)) for p, m in ggm.items()}
    assert by_pid[M.MS_RECTMASK2D][0] == "RectMask2D" and by_pid[M.MS_AUTOSCROLL][0] == "AutoScrollText"

    src = open(STOCK, "rb").read()
    print("gốc sharedassets24.assets: %d byte  md5 %s" % (len(src), hashlib.md5(src).hexdigest()))
    env = UnityPy.load(STOCK)
    sf = env.file
    assert sf.externals[EXT_GGM - 1].path == "globalgamemanagers.assets" and not sf._enable_type_tree
    if max(sf.objects) >= GO_MASK:
        raise SystemExit("dump gốc có pid ≥ %d — không phải file stock" % GO_MASK)
    print("công thức hash khớp %d type entry sẵn có" % M.check_hashes(sf, by_pid, EXT_GGM))
    objs = sf.objects
    orig_raw = {pid: o.get_raw_data() for pid, o in objs.items()}

    go_row = objs[GO_ROW].read_typetree()
    assert go_row["m_Name"] == "DLCButton" and MB_ETB in [c["component"]["m_PathID"] for c in go_row["m_Component"]]
    go = objs[GO_TEXT].read_typetree()
    assert go["m_Name"] == "Text" and [c["component"]["m_PathID"] for c in go["m_Component"]] == [RT_TEXT, CR_TEXT, TMP_TEXT]
    rt = objs[RT_TEXT].read_typetree()
    assert rt["m_Father"]["m_PathID"] == RT_ROW and rt["m_AnchorMin"] == {"x": 0.0, "y": 0.0} and rt["m_AnchorMax"] == {"x": 1.0, "y": 1.0}
    assert rt["m_SizeDelta"] == {"x": 0.0, "y": 0.0} and rt["m_AnchoredPosition"] == {"x": 0.0, "y": 0.0}
    row_rt = objs[RT_ROW].read_typetree()
    assert row_rt["m_SizeDelta"] == {"x": ROW_W, "y": ROW_H}
    kids = [c["m_PathID"] for c in row_rt["m_Children"]]
    assert RT_TEXT in kids
    go_on = objs[GO_ON].read_typetree()
    rt_on = objs[RT_ON].read_typetree()
    assert go_on["m_Name"] == "On" and rt_on["m_GameObject"]["m_PathID"] == GO_ON and rt_on["m_Father"]["m_PathID"] == RT_ROW
    on_kids = [c["m_PathID"] for c in rt_on["m_Children"]]
    # EventTriggerButton#45: textMeshPro → TMP#41, select → On#18 (đọc thô: PPtr là (fileID:int32, pathID:int64))
    import struct
    etb = orig_raw[MB_ETB]
    pptrs = {struct.unpack_from("<iq", etb, off) for off in range(28, len(etb) - 11, 4)}
    assert (0, TMP_TEXT) in pptrs and (0, GO_ON) in pptrs, "EventTriggerButton#45 không trỏ TMP#41 / On#18"
    tmp_nodes = M.borrowed_tmp_nodes(UI)
    tmp = objs[TMP_TEXT].read_typetree(tmp_nodes)
    assert tmp["m_TextWrappingMode"] == 1 and tmp["m_overflowMode"] == 0 and tmp["m_HorizontalAlignment"] == M.TMP_LEFT
    assert tmp["m_enableAutoSizing"] == 0 and tmp["m_margin"]["x"] == PAD_LEFT and tmp["m_Maskable"] == 1
    text_w = ROW_W - PAD_LEFT - PAD_RIGHT
    print("Text#%d TMP#%d: text=%r size=%g wrap=%d margin=(%g,%g,%g,%g) | hàng %gx%g, vùng chữ x %g..%g (%g px)"
          % (GO_TEXT, TMP_TEXT, tmp["m_text"], tmp["m_fontSize"], tmp["m_TextWrappingMode"],
             tmp["m_margin"]["x"], tmp["m_margin"]["y"], tmp["m_margin"]["z"], tmp["m_margin"]["w"],
             ROW_W, ROW_H, PAD_LEFT, ROW_W - PAD_RIGHT, text_w))

    tid_mask, st_mask = M.add_script_type(sf, EXT_GGM, M.MS_RECTMASK2D, *by_pid[M.MS_RECTMASK2D])
    tid_scroll, st_scroll = M.add_script_type(sf, EXT_GGM, M.MS_AUTOSCROLL, *by_pid[M.MS_AUTOSCROLL])

    # TextMask: stretch theo hàng, thụt trái PAD_LEFT, chừa phải PAD_RIGHT, nới dọc MASK_EXTRA_Y
    go_mask = copy.deepcopy(go)
    go_mask["m_Name"] = "TextMask"
    go_mask["m_Component"] = [{"component": {"m_FileID": 0, "m_PathID": p}} for p in (RT_MASK, MB_MASK)]
    rt_mask = copy.deepcopy(rt)
    rt_mask["m_GameObject"] = {"m_FileID": 0, "m_PathID": GO_MASK}
    rt_mask["m_Children"] = [{"m_FileID": 0, "m_PathID": RT_TEXT}]
    rt_mask["m_Father"] = {"m_FileID": 0, "m_PathID": RT_ROW}
    rt_mask["m_AnchorMin"] = {"x": 0.0, "y": 0.0}
    rt_mask["m_AnchorMax"] = {"x": 1.0, "y": 1.0}
    rt_mask["m_Pivot"] = {"x": 0.5, "y": 0.5}
    rt_mask["m_AnchoredPosition"] = {"x": (PAD_LEFT - PAD_RIGHT) / 2.0, "y": 0.0}
    rt_mask["m_SizeDelta"] = {"x": -(PAD_LEFT + PAD_RIGHT), "y": 2 * MASK_EXTRA_Y}
    M.new_object(sf, GO_TEXT, GO_MASK, b"").save_typetree(go_mask)
    M.new_object(sf, RT_TEXT, RT_MASK, b"").save_typetree(rt_mask)
    mask_data = M.rectmask2d_data(GO_MASK, EXT_GGM, M.MS_RECTMASK2D)
    M.new_object(sf, GO_TEXT, MB_MASK, mask_data, tid_mask, st_mask)

    # TitleScroll dưới On: chỉ sống khi hàng được chọn. RectMask2D ở đây chỉ để AutoScrollText đo maskWidth.
    go_scroll = copy.deepcopy(go)
    go_scroll["m_Name"] = "TitleScroll"
    go_scroll["m_Component"] = [{"component": {"m_FileID": 0, "m_PathID": p}} for p in (RT_SCROLL, MB_SCROLLMASK, MB_SCROLL)]
    rt_scroll = copy.deepcopy(rt)
    rt_scroll["m_GameObject"] = {"m_FileID": 0, "m_PathID": GO_SCROLL}
    rt_scroll["m_Children"] = []
    rt_scroll["m_Father"] = {"m_FileID": 0, "m_PathID": RT_ON}
    rt_scroll["m_AnchorMin"] = {"x": 0.5, "y": 0.5}
    rt_scroll["m_AnchorMax"] = {"x": 0.5, "y": 0.5}
    rt_scroll["m_Pivot"] = {"x": 0.5, "y": 0.5}
    rt_scroll["m_AnchoredPosition"] = {"x": 0.0, "y": 0.0}
    rt_scroll["m_SizeDelta"] = {"x": text_w, "y": ROW_H}
    M.new_object(sf, GO_TEXT, GO_SCROLL, b"").save_typetree(go_scroll)
    M.new_object(sf, RT_TEXT, RT_SCROLL, b"").save_typetree(rt_scroll)
    scrollmask_data = M.rectmask2d_data(GO_SCROLL, EXT_GGM, M.MS_RECTMASK2D)
    M.new_object(sf, GO_TEXT, MB_SCROLLMASK, scrollmask_data, tid_mask, st_mask)
    scroll_data = M.autoscroll_data(GO_SCROLL, EXT_GGM, M.MS_AUTOSCROLL, 0, TMP_TEXT, args.mode, args.delay, args.speed, args.pause)
    M.new_object(sf, GO_TEXT, MB_SCROLL, scroll_data, tid_scroll, st_scroll)
    rt_on["m_Children"] = [{"m_FileID": 0, "m_PathID": p} for p in on_kids + [RT_SCROLL]]
    objs[RT_ON].save_typetree(rt_on)

    # Text: con của mask, neo + pivot mép trái, đúng bề rộng vùng chữ, cao bằng hàng
    rt["m_Father"] = {"m_FileID": 0, "m_PathID": RT_MASK}
    rt["m_AnchorMin"] = {"x": 0.0, "y": 0.5}
    rt["m_AnchorMax"] = {"x": 0.0, "y": 0.5}
    rt["m_Pivot"] = {"x": 0.0, "y": 0.5}
    rt["m_AnchoredPosition"] = {"x": 0.0, "y": 0.0}
    rt["m_SizeDelta"] = {"x": text_w, "y": ROW_H}
    objs[RT_TEXT].save_typetree(rt)
    row_rt["m_Children"] = [{"m_FileID": 0, "m_PathID": RT_MASK if p == RT_TEXT else p} for p in kids]
    objs[RT_ROW].save_typetree(row_rt)
    assert objs[TMP_TEXT].save_typetree(tmp, tmp_nodes) == orig_raw[TMP_TEXT], "cây TMP mượn không round-trip"
    tmp["m_TextWrappingMode"] = 0
    tmp["m_margin"]["x"] = 0.0
    tmp_data = objs[TMP_TEXT].save_typetree(tmp, tmp_nodes)
    fields = M.changed_fields(orig_raw[TMP_TEXT], tmp_data)
    assert len(fields) == 2, fields
    print("TMP#%d: wrap 1 -> 0 (NoWrap), m_margin.x %g -> 0 (2 trường @%s); cỡ chữ cố định %g" % (TMP_TEXT, PAD_LEFT, fields, tmp["m_fontSize"]))
    print("AutoScrollText: mode=%s startDelay=%g speed=%g pauseDuration=%g" % (args.mode, args.delay, args.speed, args.pause))

    blob = env.file.save()
    os.makedirs(os.path.dirname(SCRATCH), exist_ok=True)
    open(SCRATCH, "wb").write(blob)
    chk = UnityPy.load(SCRATCH).file
    changed = {RT_TEXT, RT_ROW, TMP_TEXT, RT_ON}
    new_pids = (GO_MASK, RT_MASK, MB_MASK, GO_SCROLL, RT_SCROLL, MB_SCROLLMASK, MB_SCROLL)
    M.verify_untouched(orig_raw, chk, changed, new_pids)
    assert chk.objects[TMP_TEXT].get_raw_data() == tmp_data
    assert chk.objects[MB_MASK].get_raw_data() == mask_data and chk.objects[MB_SCROLL].get_raw_data() == scroll_data
    assert chk.objects[MB_SCROLLMASK].get_raw_data() == scrollmask_data
    for pid, ms in ((MB_MASK, M.MS_RECTMASK2D), (MB_SCROLLMASK, M.MS_RECTMASK2D), (MB_SCROLL, M.MS_AUTOSCROLL)):
        t = chk.types[chk.objects[pid].type_id]
        assert chk.objects[pid].type.name == "MonoBehaviour" and chk.script_types[t.script_type_index].local_identifier_in_file == ms
    gs = chk.objects[GO_SCROLL].read_typetree(); rs = chk.objects[RT_SCROLL].read_typetree()
    assert gs["m_Name"] == "TitleScroll" and [c["component"]["m_PathID"] for c in gs["m_Component"]] == [RT_SCROLL, MB_SCROLLMASK, MB_SCROLL]
    assert rs["m_Father"]["m_PathID"] == RT_ON and rs["m_SizeDelta"] == {"x": text_w, "y": ROW_H} and rs["m_Children"] == []
    assert [c["m_PathID"] for c in chk.objects[RT_ON].read_typetree()["m_Children"]] == on_kids + [RT_SCROLL]
    assert [c["component"]["m_PathID"] for c in chk.objects[GO_MASK].read_typetree()["m_Component"]] == [RT_MASK, MB_MASK]
    r = chk.objects[RT_MASK].read_typetree()
    r0 = chk.objects[RT_TEXT].read_typetree()
    assert chk.objects[GO_MASK].read_typetree()["m_Name"] == "TextMask" and r["m_Father"]["m_PathID"] == RT_ROW
    assert [c["m_PathID"] for c in r["m_Children"]] == [RT_TEXT] and r0["m_Father"]["m_PathID"] == RT_MASK
    assert [c["m_PathID"] for c in chk.objects[RT_ROW].read_typetree()["m_Children"]] == [RT_MASK if p == RT_TEXT else p for p in kids]
    assert r0["m_SizeDelta"] == {"x": text_w, "y": ROW_H} and r0["m_Pivot"]["x"] == 0.0 and r0["m_AnchoredPosition"] == {"x": 0.0, "y": 0.0}
    assert r["m_SizeDelta"] == {"x": -(PAD_LEFT + PAD_RIGHT), "y": 2 * MASK_EXTRA_Y} and r["m_AnchoredPosition"]["x"] == (PAD_LEFT - PAD_RIGHT) / 2.0
    tmp2 = chk.objects[TMP_TEXT].read_typetree(tmp_nodes)
    assert tmp2["m_TextWrappingMode"] == 0 and tmp2["m_margin"]["x"] == 0.0 and tmp2["m_fontSize"] == tmp["m_fontSize"]
    print("đối chiếu: %d object gốc giữ nguyên byte, %d sửa (#%s), %d mới; %d -> %d byte"
          % (len(orig_raw) - len(changed), len(changed), " #".join(map(str, sorted(changed))), len(new_pids), len(src), len(blob)))
    print("mask: x %g..%g của hàng, cao %g (+%g mỗi bên); Text neo trái %gx%g; AutoScrollText trên TitleScroll#%d dưới On#%d (chỉ chạy khi hàng được chọn)"
          % (PAD_LEFT, ROW_W - PAD_RIGHT, ROW_H + 2 * MASK_EXTRA_Y, MASK_EXTRA_Y, text_w, ROW_H, GO_SCROLL, GO_ON))

    if not args.apply:
        print("\nCHẠY THỬ — bản nháp ở %s; thêm --apply để ghi" % SCRATCH)
        return
    os.makedirs(os.path.dirname(TARGET), exist_ok=True)
    open(TARGET, "wb").write(blob)
    print("đã ghi %s (%d byte, md5 %s)" % (TARGET, len(blob), hashlib.md5(blob).hexdigest()))


main()
