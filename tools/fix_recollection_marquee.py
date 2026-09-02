# -*- coding: utf-8 -*-
"""Ending List (Recollection): tắt auto-size của tiêu đề, cho chạy chữ khi dài hơn ô.

Kế tiếp `fix_recollection_list.py` (NoWrap + auto-size 17–32): tiêu đề dài co nhỏ rõ so với
hàng xóm (`#recollection_35` xuống cỡ 17). Thay bằng marquee của chính game (`AutoScrollText`,
xem `fix_music_title_marquee.py`), cỡ chữ về đúng 32 cho mọi hàng.

Prefab `RecollectionButton` trong `sharedassets21.assets` (bundle của `level21`), mỗi hàng là
một instance do `SceneReplayRoom.CreateReplayButtons` `Instantiate` rồi `GetComponent<EventTriggerButton>()`;
chữ đi qua PPtr serialize `EventTriggerButton.textMeshPro → TMP#169` — không có `Transform.Find`,
nên chèn một GameObject vào giữa hàng và `Text` là an toàn (đã quét disassembly).

    RecollectionButton#119  596×51, pivot (0,1)
      Cur                   highlight (Image, stretch)
      On#115                CHỈ active khi hàng được chọn — EventTriggerButton.curObject
      │                     = {select: [On], deSelect: [Off]}, CurObjectSetActive → GameObject.SetActive
      │ └ TitleScroll#178 (mới)  RT#179 502×51, RectMask2D#180 (chỉ để đo maskWidth),
      │                          AutoScrollText#181 → targetText = TMP#169
      Off#117               active khi KHÔNG được chọn
      TextMask#175 (mới)    RT#176 stretch, lề trái 94, cao hơn hàng 10 px mỗi bên
      │                     → vùng chữ x 94..596 (502 px), RectMask2D#177 (cắt chữ)
      └ Text#118            RT#125: cha → #176, neo+pivot mép trái, 502×51, pos (0,0)
                            TMP#169: auto-size TẮT (cỡ 32), margin.x 94 → 0 (lề gộp vào mask)

**Chỉ hàng đang chọn chạy chữ.** `AutoScrollText.OnEnable → StartScroll`, nên để nó trên
`TextMask` là mọi hàng cùng chạy (bản đầu, 02/09). Treo nó dưới `On`: chọn hàng → `On`
SetActive(true) → OnEnable → chờ startDelay rồi trôi; rời hàng → SetActive(false) →
OnDisable dừng coroutine và trả `anchoredPosition.x` về 0 (đọc từ disassembly). `mask` là
`GetComponent<RectMask2D>()` cùng GameObject nên `TitleScroll` phải có RectMask2D riêng, rộng
đúng 502 để `maskWidth` khớp vùng chữ; nó không có con nào là graphic nên không cắt gì.
`textRect = targetText.rectTransform` nên chữ vẫn bị `TextMask` cắt như cũ. Trong prefab `On`
đang active → lúc instantiate scroller bật rồi bị `CurImageReset` tắt ngay, trước khi hết
startDelay 1,5 s nên không thấy gì.

Ngưỡng chạy chữ `preferredWidth > 502` = đúng ngưỡng "tràn khung" của bản vá cũ. Danh sách căn
trái nên không cần ContentSizeFitter/LayoutElement như ô MUSIC. Mask cao hơn hàng 10 px để
dấu tiếng Việt không bị cắt trên/dưới; NoWrap nên không có gì tràn dọc.

Kiểm tra trước khi ghi: nạp lại blob, so byte từng object — chỉ #125, #130, #131, #169 được khác
(#169 đúng hai trường `m_enableAutoSizing`, `m_margin.x`). Script từ chối file đã vá (pid ≥ 175).

    python tools\\fix_recollection_marquee.py [--apply] [--mode restart|loop] [--delay 1.5] [--speed 60] [--pause 2]
"""
import argparse
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

TARGET = os.path.join(ROOT, "romfs", "Data", "sharedassets21.assets")
UI = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BACKUP = os.path.join(ROOT, "_backup", "sharedassets21.assets.premarquee")
SCRATCH = os.path.join(HERE, "_preview", "sharedassets21.marquee")

GO_ROW, RT_ROW = 119, 131
GO_TEXT, RT_TEXT, CR_TEXT, TMP_TEXT = 118, 125, 121, 169
GO_ON, RT_ON = 115, 130
GO_MASK, RT_MASK, MB_MASK = 175, 176, 177
GO_SCROLL, RT_SCROLL, MB_SCROLLMASK, MB_SCROLL = 178, 179, 180, 181
EXT_GGM = 1
ROW_W, ROW_H, PAD_LEFT = 596.0, 51.0, 94.0
MASK_EXTRA_Y = 10.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--mode", choices=M.MODES, default="restart")
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--speed", type=float, default=60.0)
    ap.add_argument("--pause", type=float, default=2.0)
    args = ap.parse_args()

    ggm = M.load_ggm_scripts()
    by_pid = {p: (m.m_ClassName, m.m_Namespace, m.m_AssemblyName, M.hash128(m.m_PropertiesHash)) for p, m in ggm.items()}
    assert by_pid[M.MS_RECTMASK2D][0] == "RectMask2D" and by_pid[M.MS_AUTOSCROLL][0] == "AutoScrollText"

    src = open(TARGET, "rb").read()
    print("sharedassets21.assets: %d byte  md5 %s" % (len(src), hashlib.md5(src).hexdigest()))
    env = UnityPy.load(TARGET)
    sf = env.file
    assert sf.externals[EXT_GGM - 1].path == "globalgamemanagers.assets" and not sf._enable_type_tree
    if max(sf.objects) >= GO_MASK:
        raise SystemExit("đã có pid ≥ %d — file đã vá rồi; chép %s đè lại rồi chạy lại" % (GO_MASK, BACKUP))
    print("công thức hash khớp %d type entry sẵn có" % M.check_hashes(sf, by_pid, EXT_GGM))
    objs = sf.objects
    orig_raw = {pid: o.get_raw_data() for pid, o in objs.items()}

    go = objs[GO_TEXT].read_typetree()
    assert go["m_Name"] == "Text" and [c["component"]["m_PathID"] for c in go["m_Component"]] == [RT_TEXT, CR_TEXT, TMP_TEXT]
    rt = objs[RT_TEXT].read_typetree()
    assert rt["m_Father"]["m_PathID"] == RT_ROW and rt["m_AnchorMin"] == {"x": 0.0, "y": 0.0} and rt["m_AnchorMax"] == {"x": 1.0, "y": 1.0}
    row_rt = objs[RT_ROW].read_typetree()
    assert row_rt["m_SizeDelta"] == {"x": ROW_W, "y": ROW_H}
    kids = [c["m_PathID"] for c in row_rt["m_Children"]]
    assert RT_TEXT in kids
    go_on = objs[GO_ON].read_typetree()
    rt_on = objs[RT_ON].read_typetree()
    assert go_on["m_Name"] == "On" and rt_on["m_GameObject"]["m_PathID"] == GO_ON and rt_on["m_Father"]["m_PathID"] == RT_ROW
    on_kids = [c["m_PathID"] for c in rt_on["m_Children"]]
    tmp_nodes = M.borrowed_tmp_nodes(UI)
    tmp = objs[TMP_TEXT].read_typetree(tmp_nodes)
    assert tmp["m_TextWrappingMode"] == 0 and tmp["m_overflowMode"] == 0 and tmp["m_HorizontalAlignment"] == M.TMP_LEFT
    assert tmp["m_margin"]["x"] == PAD_LEFT and tmp["m_Maskable"] == 1
    print("Text#%d TMP#%d: size=%g auto=%d[%g..%g] margin=(%g,%g,%g,%g) | hàng %gx%g, vùng chữ x %g..%g (%g px)"
          % (GO_TEXT, TMP_TEXT, tmp["m_fontSize"], tmp["m_enableAutoSizing"], tmp["m_fontSizeMin"], tmp["m_fontSizeMax"],
             tmp["m_margin"]["x"], tmp["m_margin"]["y"], tmp["m_margin"]["z"], tmp["m_margin"]["w"], ROW_W, ROW_H, PAD_LEFT, ROW_W, ROW_W - PAD_LEFT))
    text_w = ROW_W - PAD_LEFT

    tid_mask, st_mask = M.add_script_type(sf, EXT_GGM, M.MS_RECTMASK2D, *by_pid[M.MS_RECTMASK2D])
    tid_scroll, st_scroll = M.add_script_type(sf, EXT_GGM, M.MS_AUTOSCROLL, *by_pid[M.MS_AUTOSCROLL])

    # GameObject mask + RectTransform: stretch theo hàng, thụt trái PAD_LEFT, nới dọc MASK_EXTRA_Y
    import copy
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
    rt_mask["m_AnchoredPosition"] = {"x": PAD_LEFT / 2.0, "y": 0.0}
    rt_mask["m_SizeDelta"] = {"x": -PAD_LEFT, "y": 2 * MASK_EXTRA_Y}
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
    tmp["m_enableAutoSizing"] = 0
    tmp["m_margin"]["x"] = 0.0
    tmp_data = objs[TMP_TEXT].save_typetree(tmp, tmp_nodes)
    fields = M.changed_fields(orig_raw[TMP_TEXT], tmp_data)
    assert len(fields) == 2, fields
    print("TMP#%d: auto-size 1 -> 0, m_margin.x %g -> 0 (2 trường @%s); cỡ chữ cố định %g" % (TMP_TEXT, PAD_LEFT, fields, tmp["m_fontSize"]))
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
    tmp2 = chk.objects[TMP_TEXT].read_typetree(tmp_nodes)
    assert tmp2["m_enableAutoSizing"] == 0 and tmp2["m_margin"]["x"] == 0.0 and tmp2["m_fontSize"] == tmp["m_fontSize"]
    print("đối chiếu: %d object gốc giữ nguyên byte, %d sửa (#%s), %d mới; %d -> %d byte"
          % (len(orig_raw) - len(changed), len(changed), " #".join(map(str, sorted(changed))), len(new_pids), len(src), len(blob)))
    print("mask: x %g..%g của hàng, cao %g (+%g mỗi bên); Text neo trái %gx%g; AutoScrollText trên TitleScroll#%d dưới On#%d (chỉ chạy khi hàng được chọn)"
          % (PAD_LEFT, ROW_W, ROW_H + 2 * MASK_EXTRA_Y, MASK_EXTRA_Y, text_w, ROW_H, GO_SCROLL, GO_ON))

    if not args.apply:
        print("\nCHẠY THỬ — bản nháp ở %s; thêm --apply để ghi" % SCRATCH)
        return
    M.backup_once(TARGET, BACKUP)
    open(TARGET, "wb").write(blob)
    print("đã ghi %s (%d byte, md5 %s)" % (TARGET, len(blob), hashlib.md5(blob).hexdigest()))


main()
