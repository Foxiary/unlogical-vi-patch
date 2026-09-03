# -*- coding: utf-8 -*-
"""Tiêu đề section ở màn SECTION SELECT: căn giữa khi vừa, chạy chữ khi dài hơn khung.

Prefab trong `ui_jp`: `ChapterSelect/Story/SynopsisTitle/Mask_Title/Title (TMP)` —
`Mask_Title` 527×58 đã có `RectMask2D`, `Title` stretch kín mask, TMP căn giữa, NoWrap,
overflow, cỡ 31.25, charSpacing 6, margin.x −5. Tiêu đề dài (33 ký tự) tràn đều hai bên
và bị mask cắt cả đầu lẫn đuôi.

Cùng cơ chế với ô MUSIC (`fix_music_title_marquee.py`, đọc kỹ docstring đó):

    Mask_Title   [RectTransform, RectMask2D (sẵn), CanvasGroup, + AutoScrollText → Title TMP]
      Title      [RectTransform: neo+pivot mép trái, cao kín mask, rộng 527,
                  + ContentSizeFitter (ngang = PreferredSize), + LayoutElement (minWidth 527)]
                  TMP: giữ căn GIỮA, margin.x −5 → 0

Tên ngắn: rect = 527 = mask, chữ căn giữa. Tên dài: rect = đúng bề rộng chữ, lấp đầy từ mép
trái, `AutoScrollText` trôi tới khi lộ đuôi rồi quay về. margin.x −5 phải về 0 vì với rect
neo trái, lề âm đẩy chữ ra ngoài mask 5 px và bị cắt.

`ui_jp` là bundle **có type tree**, MonoScript nằm trong CAB: `AutoScrollText` và
`LayoutElement` chưa có → thêm 2 MonoScript object (chép từ MonoScript sẵn có, đổi tên/hash)
và 2 type entry với node ghép từ node sẵn có (xem `marquee_lib`). `ContentSizeFitter` đã có
cả MonoScript lẫn type entry. Không đổi cây (Title vẫn là con trực tiếp của Mask_Title) nên
`Transform.Find` theo đường dẫn, nếu có, vẫn đúng.

Kiểm tra: nạp lại bundle, so byte 7 9xx object — chỉ 4 object được khác (GO Mask_Title,
GO Title, RT Title, TMP Title; TMP đúng 1 trường margin.x). Lưu `packer="lz4"`.

    python tools\\fix_section_title_marquee.py [--apply] [--mode restart|loop] [--delay 0.5] [--speed 60] [--pause 2]
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

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BACKUP = os.path.join(ROOT, "_backup", "ui_jp.presectionmarquee")
SCRATCH = os.path.join(HERE, "_preview", "ui_jp.sectionmarquee")

GO_MASK = -1384392502661351133      # Mask_Title
GO_TITLE = -3917260525872031589     # Title (TMP)
RT_TITLE = -2309845555105920795
TMP_TITLE = -3543147944068614811
MASK_W = 527.0
# pid mới: bundle dùng pid 64-bit ngẫu nhiên, chọn dải riêng dễ nhận
PID_MS_SCROLL, PID_MS_LE = 0x4D51_0000_0000_0001, 0x4D51_0000_0000_0002
PID_SCROLL, PID_CSF, PID_LE = 0x4D51_0000_0000_0011, 0x4D51_0000_0000_0012, 0x4D51_0000_0000_0013


def cab_of(env):
    return [f for f in env.file.files.values() if hasattr(f, "objects")][0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--mode", choices=M.MODES, default="restart")
    ap.add_argument("--delay", type=float, default=0.5)   # 1,5 lúc dựng; hạ 0,5 cho cả bốn marquee 03/09/2026 (set_marquee_delay.py)
    ap.add_argument("--speed", type=float, default=60.0)
    ap.add_argument("--pause", type=float, default=2.0)
    args = ap.parse_args()

    ggm = M.load_ggm_scripts()
    le_hash = M.hash128(ggm[M.MS_LE].m_PropertiesHash)
    scroll_hash = M.hash128(ggm[M.MS_AUTOSCROLL].m_PropertiesHash)
    assert ggm[M.MS_LE].m_ClassName == "LayoutElement" and ggm[M.MS_AUTOSCROLL].m_ClassName == "AutoScrollText"

    src_size = os.path.getsize(BUNDLE)
    print("ui_jp: %d byte" % src_size)
    env = UnityPy.load(BUNDLE)
    cab = cab_of(env)
    assert cab._enable_type_tree
    objs = cab.objects
    for p in (PID_MS_SCROLL, PID_MS_LE, PID_SCROLL, PID_CSF, PID_LE):
        if p in objs:
            raise SystemExit("pid %x đã có — bundle đã vá rồi; chép %s đè lại rồi chạy lại" % (p, BACKUP))
    scripts = {o.read().m_ClassName: o for o in objs.values() if o.type.name == "MonoScript"}
    assert "AutoScrollText" not in scripts and "LayoutElement" not in scripts
    ms_csf, ms_etb, ms_mask = scripts["ContentSizeFitter"], scripts["EventTriggerButton"], scripts["RectMask2D"]
    tid_csf, t_csf = M.find_script_type(cab, 0, ms_csf.path_id)
    tid_etb, t_etb = M.find_script_type(cab, 0, ms_etb.path_id)
    assert tid_csf is not None and tid_etb is not None
    # đối chiếu công thức hash trên vài entry sẵn có của CAB
    for ms, tid in ((ms_csf, tid_csf), (ms_etb, tid_etb)):
        d = ms.read_typetree()
        assert cab.types[tid].script_id == M.script_id_of(d["m_ClassName"], d["m_Namespace"], d["m_AssemblyName"]), d["m_ClassName"]
        assert cab.types[tid].old_type_hash == M.hash128(d["m_PropertiesHash"]), d["m_ClassName"]
    print("công thức hash khớp entry ContentSizeFitter, EventTriggerButton trong CAB")
    orig_raw = {pid: o.get_raw_data() for pid, o in objs.items()}

    go_mask = objs[GO_MASK].read_typetree()
    go_title = objs[GO_TITLE].read_typetree()
    rt = objs[RT_TITLE].read_typetree()
    tmp = objs[TMP_TITLE].read_typetree()
    assert go_mask["m_Name"] == "Mask_Title" and go_title["m_Name"] == "Title (TMP)"
    comps_mask = [c["component"]["m_PathID"] for c in go_mask["m_Component"]]
    comps_title = [c["component"]["m_PathID"] for c in go_title["m_Component"]]
    assert RT_TITLE in comps_title and TMP_TITLE in comps_title
    has_mask = any(objs[p].type.name == "MonoBehaviour" and objs[p].read_typetree()["m_Script"]["m_PathID"] == ms_mask.path_id for p in comps_mask)
    assert has_mask, "Mask_Title không có RectMask2D"
    rt_mask = objs[rt["m_Father"]["m_PathID"]].read_typetree()
    assert rt_mask["m_GameObject"]["m_PathID"] == GO_MASK and rt_mask["m_SizeDelta"]["x"] == MASK_W
    assert rt["m_AnchorMin"] == {"x": 0.0, "y": 0.0} and rt["m_AnchorMax"] == {"x": 1.0, "y": 1.0}
    assert tmp["m_HorizontalAlignment"] == M.TMP_CENTER and tmp["m_TextWrappingMode"] == 0 and tmp["m_overflowMode"] == 0 and tmp["m_Maskable"] == 1
    print("Mask_Title %gx%g | Title TMP size=%g cspace=%g margin=(%g,%g,%g,%g) hAlign=%d"
          % (rt_mask["m_SizeDelta"]["x"], rt_mask["m_SizeDelta"]["y"], tmp["m_fontSize"], tmp["m_characterSpacing"],
             tmp["m_margin"]["x"], tmp["m_margin"]["y"], tmp["m_margin"]["z"], tmp["m_margin"]["w"], tmp["m_HorizontalAlignment"]))

    # --- MonoScript mới (chép từ MonoScript sẵn có, đổi tên/hash) ------------------
    d = ms_etb.read_typetree()
    assert d["m_Namespace"] == "" and d["m_AssemblyName"].startswith("Assembly-CSharp"), d
    d.update(m_Name="AutoScrollText", m_ClassName="AutoScrollText", m_ExecutionOrder=0,
             m_PropertiesHash={"bytes[%d]" % i: scroll_hash[i] for i in range(16)})
    M.new_object(cab, ms_etb.path_id, PID_MS_SCROLL, b"").save_typetree(d)
    d2 = ms_mask.read_typetree()
    assert d2["m_Namespace"] == "UnityEngine.UI"
    d2.update(m_Name="LayoutElement", m_ClassName="LayoutElement", m_ExecutionOrder=0,
              m_PropertiesHash={"bytes[%d]" % i: le_hash[i] for i in range(16)})
    M.new_object(cab, ms_mask.path_id, PID_MS_LE, b"").save_typetree(d2)
    asm_cs, asm_ui = d["m_AssemblyName"], d2["m_AssemblyName"]

    # --- type entry + node ------------------------------------------------------------
    pptr_tmp = next(c for c in t_etb.node.m_Children if c.m_Name == "textMeshPro")
    bool_node = next(c for c in t_etb.node.m_Children if c.m_Name == "useTextColor")
    node_scroll = M.build_autoscroll_node(t_csf.node, pptr_tmp)
    node_le = M.build_layoutelement_node(t_csf.node, bool_node)
    tid_scroll, t_scroll = M.add_script_type(cab, 0, PID_MS_SCROLL, "AutoScrollText", "", asm_cs, scroll_hash, node_scroll)
    tid_le, t_le = M.add_script_type(cab, 0, PID_MS_LE, "LayoutElement", "UnityEngine.UI", asm_ui, le_hash, node_le)
    print("type entry mới: AutoScrollText -> %d, LayoutElement -> %d; ContentSizeFitter dùng lại %d" % (tid_scroll, tid_le, tid_csf))

    # --- component mới ----------------------------------------------------------------
    scroll_data = M.autoscroll_data(GO_MASK, 0, PID_MS_SCROLL, 0, TMP_TITLE, args.mode, args.delay, args.speed, args.pause)
    csf_data = M.csf_data(GO_TITLE, 0, ms_csf.path_id)
    le_data = M.layoutelement_data(GO_TITLE, 0, PID_MS_LE, MASK_W)
    proto_mb = next(p for p in comps_mask if objs[p].type.name == "MonoBehaviour")
    M.new_object(cab, proto_mb, PID_SCROLL, scroll_data, tid_scroll, t_scroll)
    M.new_object(cab, proto_mb, PID_CSF, csf_data, tid_csf, t_csf)
    M.new_object(cab, proto_mb, PID_LE, le_data, tid_le, t_le)
    go_mask["m_Component"].append({"component": {"m_FileID": 0, "m_PathID": PID_SCROLL}})
    objs[GO_MASK].save_typetree(go_mask)
    go_title["m_Component"] += [{"component": {"m_FileID": 0, "m_PathID": p}} for p in (PID_CSF, PID_LE)]
    objs[GO_TITLE].save_typetree(go_title)

    # --- bảng preload của AssetBundle ----------------------------------------------------
    # Mỗi asset trong bundle có một dải `m_PreloadTable` nạp TRƯỚC asset đó; trong dải của
    # chapterselect.prefab mọi MonoScript đều đứng trước MonoBehaviour dùng nó (15/15). Object
    # mới không nằm trong dải thì MonoScript chưa nạp lúc deserialize → component thành
    # "missing script" (bản vá đầu: LayoutElement/AutoScrollText chết, ContentSizeFitter sống
    # nhờ MonoScript đã nạp từ prefab khác → rect co bằng chữ, tiêu đề dạt trái). Chèn vào đầu
    # dải, MonoScript trước component, tăng preloadSize và dời preloadIndex các container sau.
    ab_obj = next(o for o in objs.values() if o.type.name == "AssetBundle")
    ab = ab_obj.read_typetree()
    pre = ab["m_PreloadTable"]
    hit = [(k, v) for k, v in ab["m_Container"]
           if GO_MASK in {p["m_PathID"] for p in pre[v["preloadIndex"]:v["preloadIndex"] + v["preloadSize"]]}]
    assert len(hit) == 1, [k for k, _ in hit]
    ckey, cv = hit[0]
    start, size = cv["preloadIndex"], cv["preloadSize"]
    assert all(v["preloadIndex"] != start for k, v in ab["m_Container"] if k != ckey)
    in_range = {p["m_PathID"] for p in pre[start:start + size]}
    ins = [p for p in (ms_csf.path_id, PID_MS_SCROLL, PID_MS_LE, PID_SCROLL, PID_CSF, PID_LE) if p not in in_range]
    pre[start:start] = [{"m_FileID": 0, "m_PathID": p} for p in ins]
    cv["preloadSize"] = size + len(ins)
    shifted = 0
    for k, v in ab["m_Container"]:
        if k != ckey and v["preloadIndex"] > start:
            v["preloadIndex"] += len(ins); shifted += 1
    ab_obj.save_typetree(ab)
    print("preload: %s dải %d+%d -> +%d entry (%s); dời %d container sau"
          % (ckey.split("/")[-1], start, size, len(ins), ", ".join(hex(p) if p > 0 else str(p) for p in ins), shifted))
    pre_ins, pre_start, pre_size = list(ins), start, size

    # --- Title: neo + pivot mép trái, cao kín mask, rộng = mask (CSF nới khi chữ dài hơn)
    rt["m_AnchorMin"] = {"x": 0.0, "y": 0.0}
    rt["m_AnchorMax"] = {"x": 0.0, "y": 1.0}
    rt["m_Pivot"] = {"x": 0.0, "y": 0.5}
    rt["m_AnchoredPosition"] = {"x": 0.0, "y": 0.0}
    rt["m_SizeDelta"] = {"x": MASK_W, "y": 0.0}
    objs[RT_TITLE].save_typetree(rt)
    assert objs[TMP_TITLE].save_typetree(tmp) == orig_raw[TMP_TITLE], "TMP không round-trip"
    pad = tmp["m_margin"]["x"]
    tmp["m_margin"]["x"] = 0.0
    tmp_data = objs[TMP_TITLE].save_typetree(tmp)
    fields = M.changed_fields(orig_raw[TMP_TITLE], tmp_data)
    assert len(fields) == 1, fields
    print("TMP: m_margin.x %g -> 0 (1 trường @%s); giữ căn giữa" % (pad, fields))
    print("AutoScrollText: mode=%s startDelay=%g speed=%g pauseDuration=%g | LayoutElement minWidth=%g" % (args.mode, args.delay, args.speed, args.pause, MASK_W))

    # --- save bundle + nạp lại đối chiếu ------------------------------------------------
    blob = env.file.save(packer="lz4")
    os.makedirs(os.path.dirname(SCRATCH), exist_ok=True)
    open(SCRATCH, "wb").write(blob)
    chk = cab_of(UnityPy.load(SCRATCH))
    changed = {GO_MASK, GO_TITLE, RT_TITLE, TMP_TITLE, ab_obj.path_id}
    new_pids = (PID_MS_SCROLL, PID_MS_LE, PID_SCROLL, PID_CSF, PID_LE)
    M.verify_untouched(orig_raw, chk, changed, new_pids)
    ab2 = next(o for o in chk.objects.values() if o.type.name == "AssetBundle").read_typetree()
    pre2 = [p["m_PathID"] for p in ab2["m_PreloadTable"]]
    cv2 = dict(ab2["m_Container"])[ckey]
    assert len(pre2) == len(pre) and cv2["preloadIndex"] == pre_start and cv2["preloadSize"] == pre_size + len(pre_ins)
    assert pre2[pre_start:pre_start + len(pre_ins)] == pre_ins
    rng2 = pre2[pre_start:pre_start + cv2["preloadSize"]]
    for p in (PID_MS_SCROLL, PID_MS_LE, PID_SCROLL, PID_CSF, PID_LE, ms_csf.path_id):
        assert p in rng2, p
    assert rng2.index(PID_MS_SCROLL) < rng2.index(PID_SCROLL) and rng2.index(PID_MS_LE) < rng2.index(PID_LE) and rng2.index(ms_csf.path_id) < rng2.index(PID_CSF)
    ends = sorted((v["preloadIndex"], v["preloadIndex"] + v["preloadSize"]) for _, v in ab2["m_Container"])
    assert all(b <= c for (_, b), (c, _) in zip(ends, ends[1:])) and ends[-1][1] == len(pre2), "dải preload chồng/lệch"
    print("preload đọc lại: dải %d..%d, %d container liền mạch tới %d" % (pre_start, pre_start + cv2["preloadSize"], len(ends), len(pre2)))
    assert chk.objects[TMP_TITLE].get_raw_data() == tmp_data
    for pid, data in ((PID_SCROLL, scroll_data), (PID_CSF, csf_data), (PID_LE, le_data)):
        assert chk.objects[pid].get_raw_data() == data and chk.objects[pid].type.name == "MonoBehaviour"
    s = chk.objects[PID_SCROLL].read_typetree()        # đọc bằng node mới — kiểm tra node khớp byte
    assert s["targetText"]["m_PathID"] == TMP_TITLE and s["scrollMode"] == M.MODES[args.mode] and abs(s["speed"] - args.speed) < 1e-6
    assert s["m_Script"]["m_PathID"] == PID_MS_SCROLL and chk.objects[PID_MS_SCROLL].read_typetree()["m_ClassName"] == "AutoScrollText"
    le = chk.objects[PID_LE].read_typetree()
    assert le["m_MinWidth"] == MASK_W and le["m_LayoutPriority"] == 1 and le["m_IgnoreLayout"] == 0 and le["m_PreferredWidth"] == -1.0
    assert chk.objects[PID_MS_LE].read_typetree()["m_ClassName"] == "LayoutElement"
    c = chk.objects[PID_CSF].read_typetree()
    assert c["m_HorizontalFit"] == M.CSF_PREFERRED and c["m_VerticalFit"] == M.CSF_NONE and c["m_Script"]["m_PathID"] == ms_csf.path_id
    gm = chk.objects[GO_MASK].read_typetree(); gt = chk.objects[GO_TITLE].read_typetree()
    assert [x["component"]["m_PathID"] for x in gm["m_Component"]] == comps_mask + [PID_SCROLL]
    assert [x["component"]["m_PathID"] for x in gt["m_Component"]] == comps_title + [PID_CSF, PID_LE]
    r0 = chk.objects[RT_TITLE].read_typetree()
    assert r0["m_Pivot"]["x"] == 0.0 and r0["m_AnchorMax"] == {"x": 0.0, "y": 1.0} and r0["m_SizeDelta"] == {"x": MASK_W, "y": 0.0}
    assert chk.objects[TMP_TITLE].read_typetree()["m_margin"]["x"] == 0.0
    print("đối chiếu: %d object gốc giữ nguyên byte, %d sửa, %d mới (2 MonoScript + 3 component); bundle %d -> %d byte"
          % (len(orig_raw) - len(changed), len(changed), len(new_pids), src_size, len(blob)))

    if not args.apply:
        print("\nCHẠY THỬ — bản nháp ở %s; thêm --apply để ghi" % SCRATCH)
        return
    M.backup_once(BUNDLE, BACKUP)
    open(BUNDLE, "wb").write(blob)
    print("đã ghi %s (%d byte, md5 %s)" % (BUNDLE, len(blob), hashlib.md5(blob).hexdigest()))


main()
