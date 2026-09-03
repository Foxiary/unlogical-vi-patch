# -*- coding: utf-8 -*-
"""Tên bài hát ở màn MUSIC: căn giữa khi vừa ô, chạy chữ (marquee) khi dài hơn ô.

Sau `fix_music_title.py` (bỏ charSpacing), 16/21 tên vẫn tràn khỏi ô 400 px và
chui xuống dưới icon bên phải. Game **có sẵn** class `AutoScrollText`
(`Assets/Scripts/Auto/AutoScrollText.cs`, MonoScript `globalgamemanagers.assets`
pid 1187) nhưng không gắn vào object nào — 0 instance trong toàn bộ scene/prefab.
Đọc disassembly (`dump.cs` + capstone trên `main.flat`):

    Awake        textRect = targetText.rectTransform; mask = GetComponent<RectMask2D>()
    OnEnable     TMPro_EventManager.TEXT_CHANGED += OnTMPTextChanged; StartScroll()
    StartScroll  anchoredPosition.x = 0; CalculateWidths();
                 chỉ chạy khi targetText.preferredWidth > mask.rect.width
    ScrollMode   Loop = 0  : trôi sang trái, ra hết thì vòng lại từ mép phải (x = maskWidth)
                 Restart = 1: trôi tới x = -(textWidth - maskWidth), dừng pauseDuration,
                              nhảy về 0, chờ startDelay, lặp
    .ctor        startDelay 1.0, speed 50 px/s, pauseDuration 1.0

Không cần vá code, chỉ thêm dữ liệu vào `level13`:

    MusicRoom#63
      └ TrackTitleMask#380  [RectTransform#381 386×100 tại (-188,-228),
        │                    RectMask2D#382, AutoScrollText#383 → targetText = TMP#244]
        └ TrackTitle#66     [RectTransform#180: cha → #381, neo+pivot mép TRÁI mask, pos (0,0)
                             CanvasRenderer#115, TMP#244: margin.x 14→0, căn GIỮA,
                             + ContentSizeFitter#384 (ngang = PreferredSize),
                             + LayoutElement#385 (minWidth = 386, priority 1)]

Ba điểm phải đúng cùng lúc, vì `StartScroll` ép `anchoredPosition.x = 0`:

1. **Mask không phủ lề trái.** Rect cũ 400 px tại canvas 565..965, TMP lề trái 14 → chữ
   nghỉ ở 579. Bản vá đầu để mask trùng rect cũ, chữ đang trôi chui vào 14 px lề và dí
   sát icon ♫. Nên mask = đúng vùng chữ 579..965 (386 px), lề TMP gộp vào vị trí mask.
2. **Tên ngắn căn giữa, tên dài bắt đầu từ mép trái.** TMP căn giữa trong rect cố định
   thì tên dài tràn đều hai bên → đầu bị mask cắt ngay lúc nghỉ. Giải: rect con rộng
   `max(386, preferredWidth)` nhờ ContentSizeFitter + LayoutElement.minWidth, neo và
   pivot ở mép trái mask. Tên ngắn: rect = 386 = mask, chữ căn giữa trong đó. Tên dài:
   rect = đúng bề rộng chữ, chữ lấp đầy rect từ mép trái — chính là vị trí x = 0 mà
   scroller cần, và `-(textWidth - maskWidth)` đưa đuôi chữ tới đúng mép phải.
   `LayoutUtility` lấy minWidth từ LayoutElement (priority 1 > TMP 0) và preferredWidth
   từ TMP (LayoutElement để -1), ContentSizeFitter PreferredSize = max(min, preferred).
3. Ngưỡng so `preferredWidth > 386` = ngưỡng tràn cũ (400 − 14), nên tập tên chạy chữ
   không đổi so với trước khi vá.

Type entry mới (file không nhúng type tree, chỉ cần hash):
    script_id     = MD4(className + namespace + assemblyName)   — đối chiếu khớp 23/23 entry sẵn có
    old_type_hash = MonoScript.m_PropertiesHash
ContentSizeFitter đã có type entry trong file (2 instance ở Buttons/Left, Right) — dùng lại.

Kích thước file đổi nên phải `env.file.save()`. Trước khi ghi, script nạp lại blob và
**so byte từng object với bản gốc** — chỉ #66, #180, #199, #244 được khác (#244: đúng hai
trường `m_margin.x`, `m_HorizontalAlignment`; type tree TMP mượn từ `ui_jp`, có kiểm tra
round-trip). Script từ chối file đã vá (pid ≥ 380) — muốn đổi tham số thì chép
`_backup\\level13.premarquee` đè lại rồi chạy lại.

    python tools\\fix_music_title_marquee.py [--apply] [--mode restart|loop]
                                            [--delay 0.5] [--speed 60] [--pause 2] [--softness 0]
"""
import argparse
import copy
import hashlib
import io
import os
import shutil
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

import UnityPy  # noqa: E402

LEVEL = os.path.join(ROOT, "romfs", "Data", "level13")
UI = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
GGM = r"D:\Downloads\UNLOGICAL_v2\Data\globalgamemanagers.assets"
BACKUP = os.path.join(ROOT, "_backup", "level13.premarquee")
SCRATCH = os.path.join(HERE, "_preview", "level13.marquee")

GO_TITLE, RT_TITLE, CR_TITLE, TMP_TITLE, RT_ROOM = 66, 180, 115, 244, 199
GO_MASK, RT_MASK, MB_MASK, MB_SCROLL, MB_CSF, MB_LE = 380, 381, 382, 383, 384, 385
EXT_GGM = 1                       # externals[0] = globalgamemanagers.assets
MS_RECTMASK2D, MS_AUTOSCROLL, MS_CSF, MS_LE = 407, 1187, 399, 385
MODES = {"loop": 0, "restart": 1}
TMP_CENTER = 2                    # HorizontalAlignmentOptions: Left 1, Center 2
CSF_PREFERRED, CSF_NONE = 2, 0    # ContentSizeFitter.FitMode


def md4(data):
    """MD4 thuần Python — OpenSSL 3 không còn bật md4."""
    def f(x, y, z): return (x & y) | (~x & z)
    def g(x, y, z): return (x & y) | (x & z) | (y & z)
    def h(x, y, z): return x ^ y ^ z
    def rol(x, n): return ((x << n) | (x >> (32 - n))) & 0xffffffff
    msg = bytearray(data) + b"\x80"
    while len(msg) % 64 != 56:
        msg.append(0)
    msg += struct.pack("<Q", len(data) * 8)
    a0, b0, c0, d0 = 0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476
    for i in range(0, len(msg), 64):
        x = struct.unpack("<16I", msg[i:i + 64])
        a, b, c, d = a0, b0, c0, d0
        for j in range(16):
            a, b, c, d = d, rol((a + f(b, c, d) + x[j]) & 0xffffffff, (3, 7, 11, 19)[j % 4]), b, c
        for j in range(16):
            k = (j % 4) * 4 + j // 4
            a, b, c, d = d, rol((a + g(b, c, d) + x[k] + 0x5a827999) & 0xffffffff, (3, 5, 9, 13)[j % 4]), b, c
        for j, k in enumerate((0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15)):
            a, b, c, d = d, rol((a + h(b, c, d) + x[k] + 0x6ed9eba1) & 0xffffffff, (3, 9, 11, 15)[j % 4]), b, c
        a0, b0, c0, d0 = [(u + v) & 0xffffffff for u, v in ((a0, a), (b0, b), (c0, c), (d0, d))]
    return struct.pack("<4I", a0, b0, c0, d0)


def hash128(h):
    return bytes(getattr(h, "bytes_%d_" % i) for i in range(16))


def pptr(fid, pid):
    return struct.pack("<iq", fid, pid)


def mb_head(go_pid, script_pid):
    """m_GameObject + m_Enabled(+pad) + m_Script + m_Name rỗng = 32 byte."""
    return pptr(0, go_pid) + struct.pack("<B3x", 1) + pptr(EXT_GGM, script_pid) + struct.pack("<i", 0)


def borrowed_tmp_nodes():
    """level13 không nhúng type tree; mượn node TextMeshProUGUI từ ui_jp (như fix_music_title.py)."""
    for o in UnityPy.load(UI).objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if isinstance(t, dict) and "m_enableAutoSizing" in t:
            return o.serialized_type.node
    raise SystemExit("không mượn được type tree TMP từ ui_jp")


def load_scripts():
    env = UnityPy.load(GGM)
    return {o.path_id: o.read() for o in env.objects if o.type.name == "MonoScript"}


def find_type(sf, script_pid):
    for i, t in enumerate(sf.types):
        if t.class_id == 114:
            st = sf.script_types[t.script_type_index]
            if st.local_serialized_file_index == EXT_GGM and st.local_identifier_in_file == script_pid:
                return i, t
    return None, None


def script_type_entry(sf, ms, pid):
    """Type entry (class 114) + script_types entry cho một MonoScript chưa có trong file."""
    assert find_type(sf, pid)[0] is None, "script %d đã có trong file" % pid
    proto = next(t for t in sf.types if t.class_id == 114)
    st = copy.copy(sf.script_types[0])
    st.local_serialized_file_index = EXT_GGM
    st.local_identifier_in_file = pid
    sf.script_types.append(st)
    t = copy.copy(proto)
    t.class_id = 114
    t.is_stripped_type = False
    t.script_type_index = len(sf.script_types) - 1
    t.script_id = md4((ms.m_ClassName + ms.m_Namespace + ms.m_AssemblyName).encode())
    t.old_type_hash = hash128(ms.m_PropertiesHash)
    sf.types.append(t)
    return len(sf.types) - 1, t


def new_object(sf, proto_pid, pid, data, type_id=None, stype=None):
    o = copy.copy(sf.objects[proto_pid])
    o.path_id = pid
    o.byte_start = 0
    o.byte_size = len(data)
    o.data = bytes(data)
    if type_id is not None:
        o.type_id, o.serialized_type = type_id, stype
    assert pid not in sf.objects
    sf.objects[pid] = o
    return o


def check_hashes(sf, scripts):
    """Đối chiếu công thức hash với các entry MonoBehaviour sẵn có trong file."""
    n = 0
    for t in sf.types:
        if t.class_id != 114:
            continue
        ms = scripts[sf.script_types[t.script_type_index].local_identifier_in_file]
        assert t.script_id == md4((ms.m_ClassName + ms.m_Namespace + ms.m_AssemblyName).encode()), ms.m_ClassName
        assert t.old_type_hash == hash128(ms.m_PropertiesHash), ms.m_ClassName
        n += 1
    print("công thức hash khớp %d/%d type entry MonoBehaviour sẵn có" % (n, n))


def changed_fields(a, b):
    """Các ô 4 byte khác nhau giữa hai blob cùng độ dài."""
    assert len(a) == len(b)
    return sorted({i // 4 * 4 for i in range(len(a)) if a[i] != b[i]})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--mode", choices=MODES, default="restart")
    ap.add_argument("--delay", type=float, default=0.5, help="startDelay (s) — 1,5 lúc dựng, hạ 0,5 cho cả bốn marquee 03/09/2026 (set_marquee_delay.py)")
    ap.add_argument("--speed", type=float, default=60.0, help="px/s trên canvas 1920")
    ap.add_argument("--pause", type=float, default=2.0, help="pauseDuration (s), chỉ Restart")
    ap.add_argument("--softness", type=int, default=0, help="RectMask2D m_Softness.x (px mờ mép)")
    args = ap.parse_args()

    scripts = load_scripts()
    for pid, name in ((MS_RECTMASK2D, "RectMask2D"), (MS_AUTOSCROLL, "AutoScrollText"),
                      (MS_CSF, "ContentSizeFitter"), (MS_LE, "LayoutElement")):
        assert scripts[pid].m_ClassName == name, (pid, scripts[pid].m_ClassName)

    src = open(LEVEL, "rb").read()
    print("level13: %d byte  md5 %s" % (len(src), hashlib.md5(src).hexdigest()))
    env = UnityPy.load(LEVEL)
    sf = env.file
    assert sf.externals[EXT_GGM - 1].path == "globalgamemanagers.assets"
    assert not sf._enable_type_tree and sf.header.version == 22
    if max(sf.objects) >= GO_MASK:
        raise SystemExit("đã có pid ≥ %d — file đã vá rồi; chép %s đè lại rồi chạy lại" % (GO_MASK, BACKUP))
    check_hashes(sf, scripts)

    objs = sf.objects
    go = objs[GO_TITLE].read_typetree()
    assert go["m_Name"] == "TrackTitle"
    assert [c["component"]["m_PathID"] for c in go["m_Component"]] == [RT_TITLE, CR_TITLE, TMP_TITLE]
    rt = objs[RT_TITLE].read_typetree()
    assert rt["m_Father"]["m_PathID"] == RT_ROOM and rt["m_SizeDelta"] == {"x": 400.0, "y": 100.0}
    assert rt["m_AnchorMin"] == rt["m_AnchorMax"] == rt["m_Pivot"] == {"x": 0.5, "y": 0.5}
    room = objs[RT_ROOM].read_typetree()
    kids = [c["m_PathID"] for c in room["m_Children"]]
    assert RT_TITLE in kids
    orig_raw = {pid: o.get_raw_data() for pid, o in objs.items()}
    tmp_nodes = borrowed_tmp_nodes()
    tmp = objs[TMP_TITLE].read_typetree(tmp_nodes)
    assert tmp["m_TextWrappingMode"] == 0 and tmp["m_HorizontalAlignment"] == 1, "TrackTitle không còn NoWrap/Left"
    assert tmp["m_margin"]["z"] == 0.0 and tmp["m_Maskable"] == 1
    pad = tmp["m_margin"]["x"]
    print("TrackTitle#%d  RT#%d pos(%g,%g) size(%gx%g) lề trái TMP %g  cha=#%d  con thứ %d/%d của MusicRoom"
          % (GO_TITLE, RT_TITLE, rt["m_AnchoredPosition"]["x"], rt["m_AnchoredPosition"]["y"],
             rt["m_SizeDelta"]["x"], rt["m_SizeDelta"]["y"], pad, RT_ROOM, kids.index(RT_TITLE) + 1, len(kids)))
    # vùng chữ thật = rect trừ lề trái; mask thu về đúng vùng đó
    text_w = rt["m_SizeDelta"]["x"] - pad
    text_cx = rt["m_AnchoredPosition"]["x"] + pad / 2.0
    print("vùng chữ: rộng %g, tâm x %g (canvas %g..%g)" % (text_w, text_cx, 960 + text_cx - text_w / 2, 960 + text_cx + text_w / 2))

    # --- type entries -------------------------------------------------------
    tid_mask, st_mask = script_type_entry(sf, scripts[MS_RECTMASK2D], MS_RECTMASK2D)
    tid_scroll, st_scroll = script_type_entry(sf, scripts[MS_AUTOSCROLL], MS_AUTOSCROLL)
    tid_le, st_le = script_type_entry(sf, scripts[MS_LE], MS_LE)
    tid_csf, st_csf = find_type(sf, MS_CSF)
    assert tid_csf is not None, "level13 không có type entry ContentSizeFitter"
    print("type entry: RectMask2D -> %d (mới), AutoScrollText -> %d (mới), LayoutElement -> %d (mới), ContentSizeFitter -> %d (sẵn có)"
          % (tid_mask, tid_scroll, tid_le, tid_csf))

    # --- GameObject cha + RectTransform mask ---------------------------------
    go_mask = copy.deepcopy(go)
    go_mask["m_Name"] = "TrackTitleMask"
    go_mask["m_Component"] = [{"component": {"m_FileID": 0, "m_PathID": p}} for p in (RT_MASK, MB_MASK, MB_SCROLL)]
    rt_mask = copy.deepcopy(rt)
    rt_mask["m_GameObject"] = {"m_FileID": 0, "m_PathID": GO_MASK}
    rt_mask["m_Children"] = [{"m_FileID": 0, "m_PathID": RT_TITLE}]
    rt_mask["m_AnchoredPosition"] = {"x": text_cx, "y": rt["m_AnchoredPosition"]["y"]}
    rt_mask["m_SizeDelta"] = {"x": text_w, "y": rt["m_SizeDelta"]["y"]}
    new_object(sf, GO_TITLE, GO_MASK, b"").save_typetree(go_mask)
    new_object(sf, RT_TITLE, RT_MASK, b"").save_typetree(rt_mask)

    # --- RectMask2D: m_Padding(4f) + m_Softness(2i) ---------------------------
    mask_data = mb_head(GO_MASK, MS_RECTMASK2D) + struct.pack("<4f", 0, 0, 0, 0) + struct.pack("<2i", args.softness, 0)
    assert len(mask_data) == 56
    new_object(sf, GO_TITLE, MB_MASK, mask_data, tid_mask, st_mask)

    # --- AutoScrollText: targetText + scrollMode + startDelay/speed/pauseDuration
    scroll_data = mb_head(GO_MASK, MS_AUTOSCROLL) + pptr(0, TMP_TITLE) \
        + struct.pack("<i3f", MODES[args.mode], args.delay, args.speed, args.pause)
    assert len(scroll_data) == 60
    new_object(sf, GO_TITLE, MB_SCROLL, scroll_data, tid_scroll, st_scroll)

    # --- trên TrackTitle: ContentSizeFitter(ngang PreferredSize) + LayoutElement(minWidth)
    csf_data = mb_head(GO_TITLE, MS_CSF) + struct.pack("<2i", CSF_PREFERRED, CSF_NONE)
    assert len(csf_data) == 40 and len(csf_data) == len(orig_raw[251])       # cùng cỡ 2 instance sẵn có
    new_object(sf, GO_TITLE, MB_CSF, csf_data, tid_csf, st_csf)
    # m_IgnoreLayout(0) · minW minH prefW prefH flexW flexH · m_LayoutPriority
    le_data = mb_head(GO_TITLE, MS_LE) + struct.pack("<i", 0) + struct.pack("<6f", text_w, -1, -1, -1, -1, -1) + struct.pack("<i", 1)
    assert len(le_data) == 64
    new_object(sf, GO_TITLE, MB_LE, le_data, tid_le, st_le)

    # --- móc lại cây --------------------------------------------------------
    go["m_Component"] = [{"component": {"m_FileID": 0, "m_PathID": p}} for p in (RT_TITLE, CR_TITLE, TMP_TITLE, MB_CSF, MB_LE)]
    objs[GO_TITLE].save_typetree(go)
    rt["m_Father"] = {"m_FileID": 0, "m_PathID": RT_MASK}
    rt["m_AnchorMin"] = {"x": 0.0, "y": 0.5}
    rt["m_AnchorMax"] = {"x": 0.0, "y": 0.5}
    rt["m_Pivot"] = {"x": 0.0, "y": 0.5}
    rt["m_AnchoredPosition"] = {"x": 0.0, "y": 0.0}
    rt["m_SizeDelta"] = {"x": text_w, "y": rt["m_SizeDelta"]["y"]}
    objs[RT_TITLE].save_typetree(rt)
    room["m_Children"] = [{"m_FileID": 0, "m_PathID": RT_MASK if p == RT_TITLE else p} for p in kids]
    objs[RT_ROOM].save_typetree(room)
    # TMP: lề trái gộp vào mask, căn giữa. Round-trip trước để chắc cây mượn tái tạo đúng byte.
    assert objs[TMP_TITLE].save_typetree(tmp, tmp_nodes) == orig_raw[TMP_TITLE], "cây TMP mượn không round-trip"
    tmp["m_margin"]["x"] = 0.0
    tmp["m_HorizontalAlignment"] = TMP_CENTER
    tmp_data = objs[TMP_TITLE].save_typetree(tmp, tmp_nodes)
    fields = changed_fields(orig_raw[TMP_TITLE], tmp_data)
    assert len(fields) == 2, fields
    print("TMP#%d m_margin.x %g -> 0, m_HorizontalAlignment Left -> Center  (2 trường @%s)" % (TMP_TITLE, pad, fields))
    print("AutoScrollText: mode=%s(%d) startDelay=%g speed=%g pauseDuration=%g | RectMask2D softness=%d"
          % (args.mode, MODES[args.mode], args.delay, args.speed, args.pause, args.softness))

    # --- save + nạp lại đối chiếu ------------------------------------------
    blob = env.file.save()
    os.makedirs(os.path.dirname(SCRATCH), exist_ok=True)
    open(SCRATCH, "wb").write(blob)
    chk = UnityPy.load(SCRATCH).file
    new_pids = (GO_MASK, RT_MASK, MB_MASK, MB_SCROLL, MB_CSF, MB_LE)
    assert len(chk.objects) == len(orig_raw) + len(new_pids), len(chk.objects)
    assert len(chk.types) == len(sf.types) and len(chk.script_types) == len(sf.script_types)
    changed = {GO_TITLE, RT_TITLE, RT_ROOM, TMP_TITLE}
    bad = [pid for pid, raw in orig_raw.items() if pid not in changed and chk.objects[pid].get_raw_data() != raw]
    if bad:
        raise SystemExit("save làm lệch %d object ngoài dự kiến: %s" % (len(bad), bad[:20]))
    for pid, want in ((MB_MASK, mask_data), (MB_SCROLL, scroll_data), (MB_CSF, csf_data), (MB_LE, le_data), (TMP_TITLE, tmp_data)):
        assert chk.objects[pid].get_raw_data() == want, pid
        assert chk.objects[pid].type.name == "MonoBehaviour"
    for pid, ms in ((MB_MASK, MS_RECTMASK2D), (MB_SCROLL, MS_AUTOSCROLL), (MB_CSF, MS_CSF), (MB_LE, MS_LE)):
        t = chk.types[chk.objects[pid].type_id]
        assert chk.script_types[t.script_type_index].local_identifier_in_file == ms, pid
    g = chk.objects[GO_MASK].read_typetree()
    g0 = chk.objects[GO_TITLE].read_typetree()
    r = chk.objects[RT_MASK].read_typetree()
    r0 = chk.objects[RT_TITLE].read_typetree()
    kids2 = [c["m_PathID"] for c in chk.objects[RT_ROOM].read_typetree()["m_Children"]]
    assert g["m_Name"] == "TrackTitleMask" and r["m_Father"]["m_PathID"] == RT_ROOM
    assert [c["component"]["m_PathID"] for c in g0["m_Component"]] == [RT_TITLE, CR_TITLE, TMP_TITLE, MB_CSF, MB_LE]
    assert [c["m_PathID"] for c in r["m_Children"]] == [RT_TITLE] and r0["m_Father"]["m_PathID"] == RT_MASK
    assert kids2 == [RT_MASK if p == RT_TITLE else p for p in kids]
    assert r["m_SizeDelta"]["x"] == text_w and r0["m_SizeDelta"]["x"] == text_w
    assert r0["m_AnchorMin"]["x"] == r0["m_AnchorMax"]["x"] == r0["m_Pivot"]["x"] == 0.0 and r0["m_AnchoredPosition"] == {"x": 0.0, "y": 0.0}
    tmp2 = chk.objects[TMP_TITLE].read_typetree(tmp_nodes)
    assert tmp2["m_margin"]["x"] == 0.0 and tmp2["m_HorizontalAlignment"] == TMP_CENTER
    assert tmp2["m_fontSize"] == tmp["m_fontSize"] and tmp2["m_characterSpacing"] == tmp["m_characterSpacing"]
    print("đối chiếu: %d object gốc giữ nguyên byte, %d sửa (#%s), %d mới; %d -> %d byte"
          % (len(orig_raw) - len(changed), len(changed), " #".join(map(str, sorted(changed))), len(new_pids), len(src), len(blob)))
    print("mask #%d: %gx%g tại (%g,%g) — canvas x %g..%g; rect con neo mép trái, rộng max(%g, preferredWidth)"
          % (RT_MASK, r["m_SizeDelta"]["x"], r["m_SizeDelta"]["y"], r["m_AnchoredPosition"]["x"], r["m_AnchoredPosition"]["y"],
             960 + r["m_AnchoredPosition"]["x"] - r["m_SizeDelta"]["x"] / 2, 960 + r["m_AnchoredPosition"]["x"] + r["m_SizeDelta"]["x"] / 2, text_w))

    if not args.apply:
        print("\nCHẠY THỬ — bản nháp ở %s; thêm --apply để ghi" % SCRATCH)
        return
    if not os.path.exists(BACKUP):
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        shutil.copy2(LEVEL, BACKUP)
        print("backup ->", BACKUP)
    open(LEVEL, "wb").write(blob)
    print("đã ghi %s (%d byte, md5 %s)" % (LEVEL, len(blob), hashlib.md5(blob).hexdigest()))


main()
