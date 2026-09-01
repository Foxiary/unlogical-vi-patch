# -*- coding: utf-8 -*-
"""VIẾT HOA TOÀN BỘ tên bài hát (`MusicData.title`, bundle `json`).

`MusicData` là một trong bảy bảng của bundle `json` **không có tab trên sheet** (xem
`tools/README.md`, mục thuật ngữ bundle `json`), nên đây là chỗ sửa duy nhất và merge
sau này không đè lại được.

Quy tắc: `str.upper()` — `"Làn da của anh là giả sao?"` → `"LÀN DA CỦA ANH LÀ GIẢ SAO?"`,
`"Tune your nerves"` → `"TUNE YOUR NERVES"`. Chỉ đổi hoa/thường, độ dài và mọi ký tự
khác giữ nguyên (tiếng Việt không có ký tự nào nở ra khi upper như ß).

Font của ô này (`m_fontAsset` của `level13` TMP#244) phải có glyph cho mọi chữ hoa có
dấu xuất hiện — script kiểm tra bảng ký tự của bản `ui_jp` (bản có type tree) và dừng
nếu thiếu, vì thiếu glyph là ra ô vuông trong game.

Sửa thẳng trên văn bản JSON (thay từng `"title":"<cũ>"`, như `json_term.py`) để BOM
và định dạng còn nguyên; so cấu trúc trước/sau, chỉ trường `title` được khác.

    python tools\\fix_music_title_case.py [--apply]
"""
import io
import json
import os
import shutil
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

import UnityPy  # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
BACKUP = os.path.join(ROOT, "_backup", "json.premusiccase")
ASSET = "MusicData"
APPLY = "--apply" in sys.argv
LEVEL = os.path.join(ROOT, "romfs", "Data", "level13")
UI = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
TMP_TITLE = 244


def title_case(s):
    return s.upper()


def check_glyphs(titles):
    """Font của TrackTitle phải có glyph cho mọi ký tự sau khi upper — thiếu là ô vuông.

    Font này là TMP `SDF-Dynamic` (bảng ký tự rỗng, glyph sinh lúc chạy), nên phải soi
    cmap của file TTF nguồn: TMP#244.m_fontAsset → TMP_FontAsset.m_SourceFontFile →
    Font.m_FontData. Type tree TMP/TMP_FontAsset mượn từ ui_jp.
    """
    from fontTools.ttLib import TTFont
    ui = UnityPy.load(UI)
    tmp_nodes = fa_nodes = None
    for o in ui.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if not isinstance(t, dict):
            continue
        if tmp_nodes is None and "m_enableAutoSizing" in t:
            tmp_nodes = o.serialized_type.node
        if fa_nodes is None and "m_CharacterTable" in t:
            fa_nodes = o.serialized_type.node
        if tmp_nodes is not None and fa_nodes is not None:
            break
    lv = UnityPy.load(LEVEL).file
    fa = lv.objects[TMP_TITLE].read_typetree(tmp_nodes)["m_fontAsset"]
    fa_file = os.path.join(ROOT, "romfs", "Data", lv.externals[fa["m_FileID"] - 1].path)
    sf = UnityPy.load(fa_file).file
    fat = sf.objects[fa["m_PathID"]].read_typetree(fa_nodes)
    src = fat["m_SourceFontFile"]
    assert src["m_FileID"] == 0, "font nguồn nằm ở file khác: %s" % src
    font = sf.objects[src["m_PathID"]].read()
    tmp_path = os.path.join(HERE, "_preview", "tracktitle_font.bin")
    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
    open(tmp_path, "wb").write(bytes(font.m_FontData))
    cmap = TTFont(tmp_path).getBestCmap()
    need = sorted({c for t in titles for c in title_case(t) if not c.isspace()})
    missing = [c for c in need if ord(c) not in cmap]
    print("font %s (%s pid %d, dynamic, nguồn Font pid %d: %d glyph): cần %d ký tự, thiếu %d %s"
          % (fat["m_Name"], os.path.basename(fa_file), fa["m_PathID"], src["m_PathID"], len(cmap), len(need), len(missing), "".join(missing)))
    if missing:
        raise SystemExit("font thiếu glyph — không ghi")


def main():
    env = UnityPy.load(BUNDLE)
    obj = next((o for o in env.objects if o.type.name == "TextAsset" and o.read().m_Name == ASSET), None)
    if obj is None:
        raise SystemExit("không thấy TextAsset %s" % ASSET)
    d = obj.read()
    raw = d.m_Script if isinstance(d.m_Script, str) else bytes(d.m_Script).decode("utf-8")
    before = json.loads(raw.lstrip("﻿"))
    rows = before["data"]
    check_glyphs([r["title"] for r in rows])
    out = raw
    n_changed = 0
    for i, r in enumerate(rows):
        old = r["title"]
        new = title_case(old)
        assert old.lower() == new.lower() and len(old) == len(new), (old, new)
        needle = json.dumps(old, ensure_ascii=False)
        assert out.count('"title":' + needle) == 1, "title %r không xuất hiện đúng 1 lần" % old
        mark = "  " if old == new else "->"
        print("%2d  %s  %s" % (i + 1, mark, new if old == new else "%s  ->  %s" % (old, new)))
        if old != new:
            out = out.replace('"title":' + needle, '"title":' + json.dumps(new, ensure_ascii=False), 1)
            n_changed += 1
    after = json.loads(out.lstrip("﻿"))
    assert len(after["data"]) == len(rows)
    for a, b in zip(rows, after["data"]):
        assert a.keys() == b.keys() and all(a[k] == b[k] for k in a if k != "title"), "trường ngoài title bị đổi"
        assert title_case(a["title"]) == b["title"]
    assert out.startswith("﻿") == raw.startswith("﻿")
    print("đổi %d/%d tên" % (n_changed, len(rows)))
    if n_changed == 0:
        print("không có gì để làm")
        return
    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return
    if not os.path.exists(BACKUP):
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        shutil.copy2(BUNDLE, BACKUP)
        print("backup ->", BACKUP)
    d.m_Script = out
    d.save()
    blob = env.file.save(packer="lz4")
    with open(BUNDLE, "wb") as f:
        f.write(blob)
    print("đã ghi %s (%d byte)" % (BUNDLE, os.path.getsize(BUNDLE)))
    chk = next(o.read() for o in UnityPy.load(BUNDLE).objects if o.type.name == "TextAsset" and o.read().m_Name == ASSET)
    chk_raw = chk.m_Script if isinstance(chk.m_Script, str) else bytes(chk.m_Script).decode("utf-8")
    assert chk_raw == out, "đọc lại không khớp"
    print("đọc lại: khớp")


main()
