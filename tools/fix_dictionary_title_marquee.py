# -*- coding: utf-8 -*-
"""Tiêu đề mục từ điển: căn giữa khi vừa ô, chạy chữ (marquee) khi dài hơn ô.

Báo 05/09/2026 kèm ảnh `IMG_7262` (máy Switch thật): mục `no=209`
`Hội chứng nhân vật chính` bị cắt **cả hai đầu** — mất non nửa chữ `H` đầu và
chữ `h` cuối. Tiêu đề căn GIỮA trong một `RectMask2D`, NoWrap, auto-size TẮT,
nên tràn bao nhiêu thì cắt đều hai bên bấy nhiêu.

Từ điển có HAI màn, cùng một chuỗi `DictionaryData.title`, hai bộ số đo:

    level10  DictionaryLayer/ViewRoot/Mask_Title (588×64) / Title (TMP)#897
             cỡ 40, charSpacing 5   — hộp bật lên khi đang đọc truyện (ảnh báo)
    level22  RenderCanvas/Note/Title/Mask_Title (500×40) / Title (TMP)#330
             cỡ 32, charSpacing 3.5 — màn DICTIONARY mở từ terminal

Đo bằng mô hình bề rộng của `fix_dictionary_wrap.py`
(`Σadvance × fontSize/pointSize + (n−1) × charSpacing × fontSize/100`):
**7/80 tiêu đề tràn ô 588 px** của hộp ADV (`no=357` 735,6 px là dài nhất, rồi
351 / 213 / 209 / 350 / 214 / 504), và **2/80 tràn ô 500 px** của màn terminal
(`no=357` 575,1 · `no=351` 514,9). Cỡ chữ 40 và 32 là cố định, auto-size tắt cả
hai nơi, nên không có gì tự co lại.

Cách chữa vẫn là marquee của chính game — `AutoScrollText`, xem docstring
`fix_music_title_marquee.py` cho hành vi đọc từ disassembly (Awake lấy
`mask = GetComponent<RectMask2D>()`, OnEnable móc `TMPro_EventManager.TEXT_CHANGED`
rồi `StartScroll`, chỉ chạy khi `targetText.preferredWidth > mask.rect.width`).

**Ở đây không phải dựng GameObject mới.** Ba marquee trước phải chèn một
`TextMask`/`TitleScroll` vào giữa cây vì chỗ đó chưa có mask; từ điển thì đã có
sẵn `Mask_Title` mang đúng `RectMask2D` bao đúng vùng chữ, và `Title (TMP)` là
con duy nhất của nó. Nên bản vá chỉ **thêm ba component**:

    Mask_Title   + AutoScrollText     → targetText = Title (TMP)
    Title (TMP)  + ContentSizeFitter  (ngang = PreferredSize)
                 + LayoutElement      (minWidth = bề rộng mask, priority 1)

`ContentSizeFitter` + `LayoutElement.minWidth` là cách duy nhất giữ được
"ngắn thì căn giữa, dài thì bắt đầu từ mép trái": `StartScroll` ép
`anchoredPosition.x = 0`, nên nếu để rect cố định bằng mask thì chữ dài căn giữa
đã thò ra hai bên ngay lúc đứng yên, marquee chỉ làm nó tệ hơn. Với CSF, rect
rộng `max(maskWidth, preferredWidth)`, neo + pivot ở mép TRÁI mask:

    tên ngắn  rect = mask  → TMP căn giữa trong đó, y như trước bản vá
    tên dài   rect = đúng bề rộng chữ → chữ lấp đầy rect từ mép trái, tức đúng
              vị trí x = 0 mà scroller lấy làm điểm nghỉ

Ngưỡng chạy chữ `preferredWidth > maskWidth` trùng đúng ngưỡng "bị cắt" cũ, nên
73/80 mục ở hộp ADV (78/80 ở màn terminal) không đổi một pixel nào.

`level10` (RT#788) đã neo + pivot mép trái sẵn, đúng 588×64 = mask → không đụng
tới. `level22` (RT#199) đang stretch 4 góc, `sizeDelta` 0×0, pivot x = 0; về
hình học thì tương đương (CSF vẫn nở sang phải, mép trái đứng yên) nhưng script
vẫn đổi sang dạng neo trái 500×40 cho giống hệt `level10` và ba marquee kia —
một cấu hình duy nhất để về sau còn suy luận được.

Cả hai file không nhúng type tree, MonoScript nằm ở `globalgamemanagers.assets`,
nên type entry mới chỉ cần hai hash (`marquee_lib.add_script_type`).
`ContentSizeFitter` đã có type entry sẵn trong `level22` (Word/Buttons dùng);
`level10` thì chưa, phải thêm.

Trước khi ghi: nạp lại blob, so byte từng object — chỉ hai GameObject đổi (thêm
component vào `m_Component`) cộng RT#199 ở `level22`; `Title (TMP)` và
`RectMask2D` sẵn có giữ nguyên từng byte. Script từ chối file đã vá; muốn đổi
tham số thì chép `_backup\\levelNN.predicmarquee` đè lại rồi chạy lại — riêng
`startDelay` thì dùng `tools\\set_marquee_delay.py`.

    python tools\\fix_dictionary_title_marquee.py [--apply] [--only adv|terminal]
        [--mode restart|loop] [--delay 0.5] [--speed 60] [--pause 2]
"""
import argparse
import hashlib
import io
import json
import os
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy  # noqa: E402
import marquee_lib as M  # noqa: E402

DATA = os.path.join(ROOT, "romfs", "Data")
UI = os.path.join(DATA, "StreamingAssets", "ui", "ui_jp")
JSON_BUNDLE = os.path.join(DATA, "StreamingAssets", "json", "json")
EXT_GGM = 1

# tên -> (file, GO/RT/MB sẵn có, pid mới, số đo mask)
SCREENS = {
    "adv": dict(
        label="hộp từ điển ADV (level10)",
        path=os.path.join(DATA, "level10"),
        backup=os.path.join(ROOT, "_backup", "level10.predicmarquee"),
        scratch=os.path.join(HERE, "_preview", "level10.dicmarquee"),
        go_mask=301, rt_mask=716, mb_rectmask=1191,
        go_text=258, rt_text=788, tmp=897,
        mb_scroll=1260, mb_csf=1261, mb_le=1262,
        mask_w=588.0, mask_h=64.0, font_size=40.0, char_spacing=5.0,
        relayout=False,
    ),
    "terminal": dict(
        label="màn DICTIONARY của terminal (level22)",
        path=os.path.join(DATA, "level22"),
        backup=os.path.join(ROOT, "_backup", "level22.predicmarquee"),
        scratch=os.path.join(HERE, "_preview", "level22.dicmarquee"),
        go_mask=24, rt_mask=213, mb_rectmask=353,
        go_text=9, rt_text=199, tmp=330,
        mb_scroll=493, mb_csf=494, mb_le=495,
        mask_w=500.0, mask_h=40.0, font_size=32.0, char_spacing=3.5,
        relayout=True,
    ),
}


def titles():
    """`DictionaryData.title.jp` — chỉ để in ra mục nào sẽ chạy chữ."""
    env = UnityPy.load(JSON_BUNDLE)
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        if d.m_Name != "DictionaryData":
            continue
        raw = bytes(d.m_Script.encode("utf-8", "surrogateescape")).decode("utf-8-sig")
        rows = json.loads(raw)
        rows = rows if isinstance(rows, list) else rows[list(rows)[0]]
        return [(r["no"], r["title"]["jp"]) for r in rows]
    raise SystemExit("không thấy DictionaryData trong " + JSON_BUNDLE)


def report_overflow(cfg, rows):
    """Mô hình bề rộng của fix_dictionary_wrap.py — advance và charSpacing KHÁC hệ số."""
    import adv_layout as A
    over = []
    for no, t in rows:
        w = (sum(A.glyph_advance(c) for c in t) * cfg["font_size"] / A.POINT_SIZE
             + max(len(t) - 1, 0) * cfg["char_spacing"] * cfg["font_size"] / 100.0)
        if w > cfg["mask_w"]:
            over.append((w, no, t))
    over.sort(reverse=True)
    print("   %d/%d tiêu đề rộng hơn ô %g px -> sẽ chạy chữ:" % (len(over), len(rows), cfg["mask_w"]))
    for w, no, t in over:
        print("      %6.1f px  no=%-5s %s" % (w, no, t))
    return over


def patch(cfg, args, by_pid):
    src = open(cfg["path"], "rb").read()
    print("   %s: %d byte  md5 %s" % (os.path.relpath(cfg["path"], ROOT), len(src), hashlib.md5(src).hexdigest()))
    env = UnityPy.load(cfg["path"])
    sf = env.file
    assert sf.externals[EXT_GGM - 1].path == "globalgamemanagers.assets"
    assert not sf._enable_type_tree and sf.header.version == 22
    if max(sf.objects) >= cfg["mb_scroll"]:
        raise SystemExit("   đã có pid ≥ %d — file đã vá rồi; chép %s đè lại rồi chạy lại"
                         % (cfg["mb_scroll"], cfg["backup"]))
    print("   công thức hash khớp %d type entry MonoBehaviour sẵn có" % M.check_hashes(sf, by_pid, EXT_GGM))

    objs = sf.objects
    orig_raw = {pid: o.get_raw_data() for pid, o in objs.items()}

    # --- soi lại cây trước khi động vào ------------------------------------
    go_mask = objs[cfg["go_mask"]].read_typetree()
    mask_comps = [c["component"]["m_PathID"] for c in go_mask["m_Component"]]
    assert go_mask["m_Name"] == "Mask_Title", go_mask["m_Name"]
    assert cfg["mb_rectmask"] in mask_comps and mask_comps[0] == cfg["rt_mask"], mask_comps
    rt_mask = objs[cfg["rt_mask"]].read_typetree()
    assert rt_mask["m_SizeDelta"] == {"x": cfg["mask_w"], "y": cfg["mask_h"]}, rt_mask["m_SizeDelta"]
    assert [c["m_PathID"] for c in rt_mask["m_Children"]] == [cfg["rt_text"]], "Mask_Title có con khác Title (TMP)"

    go_text = objs[cfg["go_text"]].read_typetree()
    text_comps = [c["component"]["m_PathID"] for c in go_text["m_Component"]]
    assert go_text["m_Name"] == "Title (TMP)", go_text["m_Name"]
    assert text_comps[0] == cfg["rt_text"] and cfg["tmp"] in text_comps, text_comps
    rt_text = objs[cfg["rt_text"]].read_typetree()
    assert rt_text["m_Father"]["m_PathID"] == cfg["rt_mask"]
    assert rt_text["m_Pivot"]["x"] == 0.0 and rt_text["m_AnchoredPosition"] == {"x": 0.0, "y": 0.0}

    tmp_nodes = M.borrowed_tmp_nodes(UI)
    tmp = objs[cfg["tmp"]].read_typetree(tmp_nodes)
    assert objs[cfg["tmp"]].save_typetree(tmp, tmp_nodes) == orig_raw[cfg["tmp"]], "cây TMP mượn không round-trip"
    assert tmp["m_fontSize"] == cfg["font_size"] and tmp["m_characterSpacing"] == cfg["char_spacing"]
    assert tmp["m_TextWrappingMode"] == 0 and tmp["m_enableAutoSizing"] == 0, "tiêu đề không còn NoWrap / auto-size đã bật"
    assert tmp["m_HorizontalAlignment"] == M.TMP_CENTER, "tiêu đề không còn căn giữa"
    assert tmp["m_Maskable"] == 1 and tmp["m_margin"] == {"x": 0.0, "y": 0.0, "z": 0.0, "w": 0.0}
    print("   Mask_Title#%d %gx%g (RectMask2D#%d)  ->  Title (TMP)#%d cỡ %g charSpacing %g, NoWrap, căn giữa"
          % (cfg["go_mask"], cfg["mask_w"], cfg["mask_h"], cfg["mb_rectmask"],
             cfg["tmp"], tmp["m_fontSize"], tmp["m_characterSpacing"]))

    # --- type entry --------------------------------------------------------
    tid_scroll, st_scroll = M.add_script_type(sf, EXT_GGM, M.MS_AUTOSCROLL, *by_pid[M.MS_AUTOSCROLL])
    tid_le, st_le = M.add_script_type(sf, EXT_GGM, M.MS_LE, *by_pid[M.MS_LE])
    tid_csf, st_csf = M.find_script_type(sf, EXT_GGM, M.MS_CSF)
    if tid_csf is None:
        tid_csf, st_csf = M.add_script_type(sf, EXT_GGM, M.MS_CSF, *by_pid[M.MS_CSF])
        csf_where = "mới"
    else:
        csf_where = "sẵn có"
    print("   type entry: AutoScrollText -> %d (mới), LayoutElement -> %d (mới), ContentSizeFitter -> %d (%s)"
          % (tid_scroll, tid_le, tid_csf, csf_where))

    # --- component mới -----------------------------------------------------
    proto = cfg["mb_rectmask"]        # khung object chép từ một MonoBehaviour sẵn có
    scroll_data = M.autoscroll_data(cfg["go_mask"], EXT_GGM, M.MS_AUTOSCROLL, 0, cfg["tmp"],
                                    args.mode, args.delay, args.speed, args.pause)
    M.new_object(sf, proto, cfg["mb_scroll"], scroll_data, tid_scroll, st_scroll)
    csf_data = M.csf_data(cfg["go_text"], EXT_GGM, M.MS_CSF)
    M.new_object(sf, proto, cfg["mb_csf"], csf_data, tid_csf, st_csf)
    le_data = M.layoutelement_data(cfg["go_text"], EXT_GGM, M.MS_LE, cfg["mask_w"])
    M.new_object(sf, proto, cfg["mb_le"], le_data, tid_le, st_le)

    go_mask["m_Component"] = [{"component": {"m_FileID": 0, "m_PathID": p}} for p in mask_comps + [cfg["mb_scroll"]]]
    objs[cfg["go_mask"]].save_typetree(go_mask)
    go_text["m_Component"] = [{"component": {"m_FileID": 0, "m_PathID": p}}
                              for p in text_comps + [cfg["mb_csf"], cfg["mb_le"]]]
    objs[cfg["go_text"]].save_typetree(go_text)
    changed = {cfg["go_mask"], cfg["go_text"]}

    # --- level22: stretch -> neo trái, cùng dạng với level10 ----------------
    if cfg["relayout"]:
        assert rt_text["m_AnchorMin"] == {"x": 0.0, "y": 0.0} and rt_text["m_AnchorMax"] == {"x": 1.0, "y": 1.0}
        assert rt_text["m_SizeDelta"] == {"x": 0.0, "y": 0.0}
        rt_text["m_AnchorMin"] = {"x": 0.0, "y": 0.5}
        rt_text["m_AnchorMax"] = {"x": 0.0, "y": 0.5}
        rt_text["m_SizeDelta"] = {"x": cfg["mask_w"], "y": cfg["mask_h"]}
        objs[cfg["rt_text"]].save_typetree(rt_text)
        changed.add(cfg["rt_text"])
        print("   RT#%d: stretch 0x0 -> neo+pivot mép trái %gx%g tại (0,0) (cùng rect như trước)"
              % (cfg["rt_text"], cfg["mask_w"], cfg["mask_h"]))
    else:
        assert rt_text["m_AnchorMin"] == rt_text["m_AnchorMax"] == {"x": 0.0, "y": 0.5}
        assert rt_text["m_SizeDelta"] == {"x": cfg["mask_w"], "y": cfg["mask_h"]}
        print("   RT#%d: đã neo+pivot mép trái %gx%g — không đụng tới"
              % (cfg["rt_text"], cfg["mask_w"], cfg["mask_h"]))

    print("   AutoScrollText#%d trên Mask_Title (mode=%s startDelay=%g speed=%g pause=%g) · "
          "ContentSizeFitter#%d + LayoutElement#%d (minWidth %g) trên Title (TMP)"
          % (cfg["mb_scroll"], args.mode, args.delay, args.speed, args.pause,
             cfg["mb_csf"], cfg["mb_le"], cfg["mask_w"]))

    # --- lưu + nạp lại đối chiếu -------------------------------------------
    blob = env.file.save()
    os.makedirs(os.path.dirname(cfg["scratch"]), exist_ok=True)
    open(cfg["scratch"], "wb").write(blob)
    chk = UnityPy.load(cfg["scratch"]).file
    new_pids = (cfg["mb_scroll"], cfg["mb_csf"], cfg["mb_le"])
    M.verify_untouched(orig_raw, chk, changed, new_pids)
    assert len(chk.types) == len(sf.types) and len(chk.script_types) == len(sf.script_types)
    for pid, want, ms in ((cfg["mb_scroll"], scroll_data, M.MS_AUTOSCROLL),
                          (cfg["mb_csf"], csf_data, M.MS_CSF),
                          (cfg["mb_le"], le_data, M.MS_LE)):
        o = chk.objects[pid]
        assert o.get_raw_data() == want and o.type.name == "MonoBehaviour", pid
        t = chk.types[o.type_id]
        st = chk.script_types[t.script_type_index]
        assert st.local_serialized_file_index == EXT_GGM and st.local_identifier_in_file == ms, pid
    assert chk.objects[cfg["tmp"]].get_raw_data() == orig_raw[cfg["tmp"]]
    assert chk.objects[cfg["mb_rectmask"]].get_raw_data() == orig_raw[cfg["mb_rectmask"]]
    g = chk.objects[cfg["go_mask"]].read_typetree()
    assert [c["component"]["m_PathID"] for c in g["m_Component"]] == mask_comps + [cfg["mb_scroll"]]
    g = chk.objects[cfg["go_text"]].read_typetree()
    assert [c["component"]["m_PathID"] for c in g["m_Component"]] == text_comps + [cfg["mb_csf"], cfg["mb_le"]]
    r = chk.objects[cfg["rt_text"]].read_typetree()
    assert r["m_Father"]["m_PathID"] == cfg["rt_mask"] and r["m_AnchoredPosition"] == {"x": 0.0, "y": 0.0}
    assert r["m_AnchorMin"] == r["m_AnchorMax"] == {"x": 0.0, "y": 0.5} and r["m_Pivot"]["x"] == 0.0
    assert r["m_SizeDelta"] == {"x": cfg["mask_w"], "y": cfg["mask_h"]}
    assert chk.objects[cfg["rt_mask"]].read_typetree()["m_SizeDelta"] == {"x": cfg["mask_w"], "y": cfg["mask_h"]}
    print("   đối chiếu: %d object gốc giữ nguyên byte, %d sửa (#%s), %d mới; %d -> %d byte"
          % (len(orig_raw) - len(changed), len(changed), " #".join(map(str, sorted(changed))),
             len(new_pids), len(src), len(blob)))

    if not args.apply:
        print("   CHẠY THỬ — bản nháp ở %s; thêm --apply để ghi" % cfg["scratch"])
        return
    if not os.path.exists(cfg["backup"]):
        os.makedirs(os.path.dirname(cfg["backup"]), exist_ok=True)
        shutil.copy2(cfg["path"], cfg["backup"])
        print("   backup ->", cfg["backup"])
    open(cfg["path"], "wb").write(blob)
    print("   đã ghi %s (%d byte, md5 %s)" % (cfg["path"], len(blob), hashlib.md5(blob).hexdigest()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", choices=sorted(SCREENS), default=None, help="chỉ vá một màn")
    ap.add_argument("--mode", choices=M.MODES, default="restart")
    ap.add_argument("--delay", type=float, default=0.5, help="startDelay (s) — bằng bốn marquee kia")
    ap.add_argument("--speed", type=float, default=60.0, help="px/s trên canvas 1920")
    ap.add_argument("--pause", type=float, default=2.0, help="pauseDuration (s), chỉ Restart")
    args = ap.parse_args()

    ggm = M.load_ggm_scripts()
    by_pid = {p: (m.m_ClassName, m.m_Namespace, m.m_AssemblyName, M.hash128(m.m_PropertiesHash))
              for p, m in ggm.items()}
    for pid, name in ((M.MS_AUTOSCROLL, "AutoScrollText"), (M.MS_CSF, "ContentSizeFitter"),
                      (M.MS_LE, "LayoutElement"), (M.MS_RECTMASK2D, "RectMask2D")):
        assert by_pid[pid][0] == name, (pid, by_pid[pid][0])

    rows = titles()
    for key in ([args.only] if args.only else sorted(SCREENS)):
        cfg = SCREENS[key]
        print("== %s" % cfg["label"])
        report_overflow(cfg, rows)
        patch(cfg, args, by_pid)
        print()


main()
