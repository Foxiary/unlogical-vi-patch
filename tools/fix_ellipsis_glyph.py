# -*- coding: utf-8 -*-
"""Hạ ba chấm của `…` U+2026 xuống chân chữ, để Ellipsis của TMP ra đúng kiểu Việt.

`FOT-NewRodinProN-DB` là font Nhật, nên glyph `…` của nó là dấu lửng **toàn rộng
với ba chấm nằm giữa dòng** — đúng chuẩn nhà in Nhật, sai với tiếng Việt (ba chấm
phải nằm trên đường chân chữ như `...`). Đo trên TTF đang nhúng:

    …  ellipsis   x  84..916 (tâm chấm 166 / 499,5 / 834)   y 300..464   advance 1000
    .  period     x  49..201 (tâm 125)                      y −17..130   advance  256

Chỗ này thành vấn đề vì `fix_save_summary_clip.py` cần chế độ **Ellipsis** cho ô
tóm tắt thẻ SAVE, mà TMP **luôn** dùng U+2026 cho dấu cắt và không cho đổi ký tự
ở mức component. Nhưng ký tự thì cố định, **glyph thì không**: font asset là
`SDF-Dynamic` (`m_AtlasPopulationMode = 1`), atlas dựng lúc chạy từ TTF nhúng
trong `Font` object — mà TTF đó nằm trong romfs của bản mod. Sửa glyph là xong.

Bản vá dời từng contour, không vẽ lại gì:

    dời y  −317      đáy chấm 300 → −17, ngang đáy dấu `.`
    dời x  −41 / −118 / −197     tâm chấm → 125 / 381 / 637 = ba dấu `.` liền nhau
    advance 1000 → 768 = 3 × 256, cũng bằng ba dấu `.`

Phạm vi ảnh hưởng: mọi chỗ vẽ `…` bằng font này = dấu cắt của TMP + **53/39.574
câu thoại (0,13%)** trong `ScenarioData` còn dùng `…`; bundle `json` **0** chỗ.
Bản dịch viết dấu lửng bằng ba chấm ASCII (memory `unlogical-punctuation-conventions`),
nên 53 câu đó chuyển sang chân chữ là **thống nhất hơn**, không phải hồi quy.
Bản sao TTF thứ hai nằm trong `ui_jp` (cùng 3.837.584 byte) — không đụng tới, các
widget đọc bản đó gần như không bao giờ hiện `…`.

Cách ghi: `fontTools` dựng lại TTF (lưu no-op ra **đúng từng byte** như bản gốc,
đã kiểm — nên chênh lệch kích thước chỉ do bảng `glyf` được nén lại chặt hơn),
rồi ghi vào `m_FontData` và lưu `sharedassets7.assets` như thường lệ. Trước khi
ghi, script so **từng glyph một**: mọi glyph khác `ellipsis` phải giữ nguyên
contour, cờ điểm, mã hint và advance; `cmap` phải khớp từng mã.

    python tools\\fix_ellipsis_glyph.py             # chạy thử + đối chiếu từng glyph
    python tools\\fix_ellipsis_glyph.py --check     # đã hạ chấm chưa
    python tools\\fix_ellipsis_glyph.py --preview   # xuất ảnh so `...` với `…`
    python tools\\fix_ellipsis_glyph.py --apply

Lùi lại: chép `_backup\\sharedassets7.assets.preellipsis` đè lên
`romfs\\Data\\sharedassets7.assets`.
"""
import io
import os
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy                                   # noqa: E402
from fontTools.ttLib import TTFont               # noqa: E402
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates   # noqa: E402

TARGET = os.path.join(ROOT, "romfs", "Data", "sharedassets7.assets")
UI_JP = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BACKUP = os.path.join(ROOT, "_backup", "sharedassets7.assets.preellipsis")
PREVIEW = os.path.join(HERE, "_preview", "ellipsis_baseline.png")

FONT_PID = 7            # Font  "FOT-NewRodinProN-DB"
TMP_PID = 85            # TMP_FontAsset "FOT-NewRodinProN-DB SDF-Dynamic"
GLYPH = "ellipsis"

DY = -317                                 # 300 -> -17, ngang đáy dấu `.`
CENTERS_OLD = (834.0, 499.5, 166.0)       # contour 0,1,2 (phải -> trái)
CENTERS_NEW = (637.0, 381.0, 125.0)       # = ba dấu `.` advance 256
ADVANCE_NEW = 768

APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv
PREV = "--preview" in sys.argv


def font_bytes(path):
    env = UnityPy.load(path)
    objs = {o.path_id: o for o in env.objects}
    o = objs.get(FONT_PID)
    if o is None or o.type.name != "Font":
        raise SystemExit("pid %d trong %s không phải Font" % (FONT_PID, path))
    d = o.read()
    if d.m_Name != "FOT-NewRodinProN-DB":
        raise SystemExit("pid %d tên %r, không phải font mong đợi" % (FONT_PID, d.m_Name))
    return env, objs, bytes(d.m_FontData)


def tmp_nodes(field):
    env = UnityPy.load(UI_JP)
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            tt = o.read_typetree()
        except Exception:
            continue
        if isinstance(tt, dict) and field in tt:
            return o.serialized_type.nodes
    raise SystemExit("không tìm được type tree có %r trong ui_jp" % field)


def dots(f, name=GLYPH):
    """[(xmin,xmax,ymin,ymax)] cho từng contour + advance."""
    glyf = f["glyf"]
    g = glyf[name]
    co, ends, _ = g.getCoordinates(glyf)
    out, start = [], 0
    for e in ends:
        pts = list(co)[start:e + 1]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        out.append((min(xs), max(xs), min(ys), max(ys)))
        start = e + 1
    return out, f["hmtx"][name][0]


def patched(f):
    d, adv = dots(f)
    return all(c[2] < 100 for c in d) and adv == ADVANCE_NEW


def build(blob):
    """TTF mới + báo cáo đối chiếu từng glyph."""
    f = TTFont(io.BytesIO(blob))
    glyf = f["glyf"]
    g = glyf[GLYPH]
    co, ends, _ = g.getCoordinates(glyf)
    coords = list(co)
    start = 0
    for i, e in enumerate(ends):
        dx = int(round(CENTERS_NEW[i] - CENTERS_OLD[i]))
        for k in range(start, e + 1):
            x, y = coords[k]
            coords[k] = (x + dx, y + DY)
        start = e + 1
    g.coordinates = GlyphCoordinates(coords)
    g.recalcBounds(glyf)
    f["hmtx"][GLYPH] = (ADVANCE_NEW, g.xMin)
    out = io.BytesIO()
    f.save(out)
    return out.getvalue()


def verify(old_blob, new_blob):
    """Mọi glyph trừ `ellipsis` phải y nguyên; cmap phải khớp từng mã."""
    a, b = TTFont(io.BytesIO(old_blob)), TTFont(io.BytesIO(new_blob))
    ga, gb = a.getGlyphOrder(), b.getGlyphOrder()
    if ga != gb:
        raise SystemExit("thứ tự glyph đổi (%d -> %d)" % (len(ga), len(gb)))
    ca, cb = {}, {}
    for t in a["cmap"].tables:
        ca.update(t.cmap)
    for t in b["cmap"].tables:
        cb.update(t.cmap)
    if ca != cb:
        raise SystemExit("cmap đổi (%d -> %d mã)" % (len(ca), len(cb)))
    fa, fb = a["glyf"], b["glyf"]
    bad = []
    for n in ga:
        if n == GLYPH:
            continue
        x, y = fa[n], fb[n]
        if x.numberOfContours != y.numberOfContours:
            bad.append((n, "contour"))
            continue
        if x.numberOfContours == 0:
            continue
        if x.isComposite() != y.isComposite():
            bad.append((n, "composite"))
            continue
        if x.isComposite():
            if [(c.glyphName, c.x, c.y, c.flags) for c in x.components] != \
               [(c.glyphName, c.x, c.y, c.flags) for c in y.components]:
                bad.append((n, "components"))
            continue
        xa, ea, la = x.getCoordinates(fa)
        xb, eb, lb = y.getCoordinates(fb)
        if list(xa) != list(xb) or ea != eb or list(la) != list(lb):
            bad.append((n, "outline"))
            continue
        if getattr(x, "program", None) is not None or getattr(y, "program", None) is not None:
            pa = x.program.getBytecode() if getattr(x, "program", None) else b""
            pb = y.program.getBytecode() if getattr(y, "program", None) else b""
            if pa != pb:
                bad.append((n, "hint"))
    if bad:
        raise SystemExit("%d glyph bị đổi ngoài dự kiến: %s" % (len(bad), bad[:8]))
    ma, mb = a["hmtx"].metrics, b["hmtx"].metrics
    diff = [n for n in ma if ma[n] != mb.get(n)]
    if diff != [GLYPH]:
        raise SystemExit("hmtx lệch ở %s, chờ chỉ %r" % (diff[:8], GLYPH))
    print("   %d glyph, %d mã cmap: chỉ %r đổi (outline + hint + advance đều khớp phần còn lại)"
          % (len(ga), len(ca), GLYPH))


def preview(blob_old, blob_new):
    from PIL import Image, ImageDraw, ImageFont
    txt_dot, txt_ell = "vậy thôi...", "vậy thôi…"
    W, H, size = 760, 210, 27 * 2          # vẽ gấp đôi cho dễ nhìn
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    rows = [("period  ...", blob_old, txt_dot),
            ("U+2026 cũ  …", blob_old, txt_ell),
            ("U+2026 mới …", blob_new, txt_ell)]
    for i, (lab, blob, s) in enumerate(rows):
        y = 20 + i * 60
        d.text((14, y + 14), lab, fill="gray",
               font=ImageFont.truetype(io.BytesIO(blob_old), 20))
        d.text((250, y), s, fill="black", font=ImageFont.truetype(io.BytesIO(blob), size))
        d.line((250, y + 44, W - 20, y + 44), fill="#d0d0d0")     # đường chân chữ
    os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)
    img.save(PREVIEW)
    print("   ảnh so sánh ->", os.path.relpath(PREVIEW, ROOT))


def main():
    env, objs, blob = font_bytes(TARGET)
    f = TTFont(io.BytesIO(blob))
    d, adv = dots(f)
    print("%s  Font pid %d, TTF %d byte" % (os.path.relpath(TARGET, ROOT), FONT_PID, len(blob)))
    for i, (x0, x1, y0, y1) in enumerate(d):
        print("   chấm %d: x %4d..%4d  y %4d..%4d" % (i, x0, x1, y0, y1))
    print("   advance %d" % adv)

    # font asset của ô chữ phải là bản Dynamic lấy nguồn từ đúng Font này
    tt = objs[TMP_PID].read_typetree(nodes=tmp_nodes("m_SourceFontFile"))
    src = tt["m_SourceFontFile"]
    if tt["m_AtlasPopulationMode"] != 1 or src["m_FileID"] != 0 or src["m_PathID"] != FONT_PID:
        raise SystemExit("TMP asset %d không rasterize từ Font pid %d (mode=%s, src=%s)"
                         % (TMP_PID, FONT_PID, tt["m_AtlasPopulationMode"], src))
    print("   %s: Dynamic, m_SourceFontFile -> pid %d  ✓" % (tt["m_Name"], FONT_PID))

    if CHECK:
        if not patched(f):
            raise SystemExit("… vẫn là dấu lửng giữa dòng kiểu Nhật — chạy lại với --apply")
        print("OK — ba chấm đã nằm ở chân chữ, advance %d" % adv)
        return
    if patched(f):
        print("\nđã hạ chấm rồi, không có gì để làm")
        if PREV:
            preview(blob, blob)
        return

    print("\ndựng TTF mới…")
    new = build(blob)
    print("   %d -> %d byte (%+d; bảng glyf được nén lại, no-op save của fontTools ra "
          "đúng byte cũ nên phần chênh không phải nội dung)" % (len(blob), len(new), len(new) - len(blob)))
    verify(blob, new)
    f2 = TTFont(io.BytesIO(new))
    d2, adv2 = dots(f2)
    for i, (x0, x1, y0, y1) in enumerate(d2):
        print("   chấm %d: x %4d..%4d  y %4d..%4d" % (i, x0, x1, y0, y1))
    print("   advance %d" % adv2)
    if PREV:
        preview(blob, new)

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    before = {o.path_id: (o.type.name, o.byte_size) for o in env.objects}
    if not os.path.exists(BACKUP):
        shutil.copy2(TARGET, BACKUP)
        print("\nbackup ->", os.path.relpath(BACKUP, ROOT))
    else:
        print("\nbackup đã có ->", os.path.relpath(BACKUP, ROOT))

    fo = objs[FONT_PID].read()
    fo.m_FontData = new
    fo.save()
    data = env.file.save()                      # dựng byte TRƯỚC khi mở file để ghi
    with open(TARGET, "wb") as fh:
        fh.write(data)
    print("đã ghi %s (%d byte)" % (os.path.relpath(TARGET, ROOT), os.path.getsize(TARGET)))

    # --- đọc lại từ đĩa ---------------------------------------------------------
    env2, objs2, blob2 = font_bytes(TARGET)
    after = {o.path_id: (o.type.name, o.byte_size) for o in env2.objects}
    if set(before) != set(after):
        raise SystemExit("số object đổi: %d -> %d" % (len(before), len(after)))
    moved = [p for p in before if before[p] != after[p]]
    if moved != [FONT_PID]:
        raise SystemExit("object đổi kích thước ngoài dự kiến: %s" % moved[:8])
    empty = [p for p, (t, s) in after.items() if s == 0]
    print("  %d object, chỉ pid %d đổi kích thước (%d -> %d), %d object rỗng"
          % (len(after), FONT_PID, before[FONT_PID][1], after[FONT_PID][1], len(empty)))
    if empty:
        raise SystemExit("có object bị ghi rỗng — khôi phục từ backup")
    if blob2 != new:
        raise SystemExit("TTF đọc lại khác bản vừa dựng")
    f3 = TTFont(io.BytesIO(blob2))
    if not patched(f3):
        raise SystemExit("đọc lại: glyph vẫn ở giữa dòng")
    d3, adv3 = dots(f3)
    print("  đọc lại: chấm y %d..%d, advance %d" % (d3[0][2], d3[0][3], adv3))


main()
