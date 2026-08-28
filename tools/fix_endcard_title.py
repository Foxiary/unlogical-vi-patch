"""Thẻ THE END — tiêu đề ending còn nguyên tiếng Nhật.

Sau mỗi BAD END game hiện một thẻ toàn màn 1920x1080 với `THE END` và dòng
`#017　くらい、つめたい`. Dòng đó **là tranh vẽ**, không phải chuỗi ký tự: 32 texture
trong bundle `StreamingAssets/cg/cg_end`, gọi qua 4 macro `エンドカード_*` trong
`resources.assets` (`macro`). Trang Ending List đã dịch từ `SceneReplayData`
nhưng thẻ thì không đổi theo.

Tiêu đề lấy đúng từ `SceneReplayData` của bản build (`#recollection_NN` ->
ending `NNN`), nên thẻ và danh sách luôn khớp từng chữ.

Bốn kiểu thẻ, mỗi kiểu một bố cục riêng:

```
a_bad_001  (9 thẻ)  nền xanh navy + lưới ô vuông, chữ điểm ảnh sáng, canh giữa 959.5
a_bad_002  (7 thẻ)  nền đen + lưới phối cảnh, chữ điểm ảnh trắng, canh giữa 959.5
a_bad_003  (11 thẻ) nền trắng bản vẽ, chữ điểm ảnh xám đá, canh giữa 960
b_bad_sad  (5 thẻ)  nền hoa/lông vũ, chữ gothic mảnh **nghiêng**, canh giữa 1566.5
```

Ba kiểu đầu dùng `FOT-DotGothic12Std-M` — mà bản dịch đã thay bằng `ULPixel`
(dựng từ GNU Unifont) trong `ui_jp`, nên thẻ cũng vẽ bằng `ULPixel` cho đồng bộ
với chữ điểm ảnh trong game. Lưới thiết kế của `ULPixel` là **16 px/em**: chỉ cỡ
bội số của 16 (32/48/64) mới sắc nét, cỡ khác bị khử răng cưa thành nhoè.

Kiểu `b_bad_sad` không phải chữ điểm ảnh — gothic mảnh nghiêng ~0.18 shear, phần
`#NN` đậm hơn và đứng thẳng. Vẽ bằng `FOT-DNPShueiMGoStd-L` / `-B` của chính bản
dịch (đã có dấu tiếng Việt).

Xoá chữ cũ: dựng mask nét trong đúng khung chữ gốc, nở 3 px, rồi **nội suy dọc**
từng cột giữa hàng sạch trên và dưới. Nền của cả bốn kiểu chỉ có vạch dọc hoặc
dải màu mượt trong khoảng đó nên nội suy dọc dựng lại đúng nguyên trạng — đã
kiểm: không hàng lưới ngang nào cắt qua khung chữ, và với `a_bad_002` vùng đen
liền mạch từ x 412 đến 1507 (vạch phối cảnh nằm ngoài).

Dùng:
    python tools\\fix_endcard_title.py --check      # đo, xuất preview, không ghi
    python tools\\fix_endcard_title.py --apply      # ghi romfs\\...\\cg\\cg_end
"""

import io
import json
import os
import shutil
import sys
import tempfile

import numpy as np
import UnityPy
from PIL import Image, ImageDraw, ImageFont

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PATCH = os.path.join(ROOT, "romfs", "Data")
STOCK = "D:/Downloads/UNLOGICAL_v2/Data"
BACKUP = os.path.join(ROOT, "_backup")
PREVIEW = os.path.join(ROOT, "_endcard")

REL = os.path.join("StreamingAssets", "cg", "cg_end")
UI_REL = os.path.join("StreamingAssets", "ui", "ui_jp")
JSON_REL = os.path.join("StreamingAssets", "json", "json")

# Font nhúng trong ui_jp của bản dịch (đã có dấu tiếng Việt).
FONT_PIXEL = "FOT-DotGothic12Std-M"      # = ULPixel.ttf
FONT_LIGHT = "FOT-DNPShueiMGoStd-L"
FONT_BOLD = "FOT-DNPShueiMGoStd-B"

# ---------------------------------------------------------------------------
# Bố cục từng kiểu thẻ. `band` là khung dò nét chữ gốc (y0, y1, x0, x1);
# `baseline` đo từ đáy mực của chữ số trong tranh gốc (đáy + 1).
VARIANTS = {
    "a_bad_001": dict(
        band=(714, 778, 560, 1370), mode="light", thr=260,
        center=959.5, baseline=764, size=48, safe=(180, 1740),
    ),
    "a_bad_002": dict(
        band=(588, 640, 412, 1508), mode="light", thr=380,
        center=959.5, baseline=625, size=48, safe=(412, 1508),
    ),
    "a_bad_003": dict(
        band=(612, 656, 560, 1370), mode="dark", thr=560,
        center=960.0, baseline=647, size=48, safe=(180, 1740),
    ),
    "b_bad_sad": dict(
        band=(604, 652, 1250, 1880), mode="dark", thr=600,
        center=1566.5, baseline=641, size=37, shear=0.18,
        prefix_size=23, prefix_baseline=636, safe=(1180, 1900),
    ),
}


def variant_of(name):
    for key in VARIANTS:
        if key in name:
            return key
    raise KeyError(name)


def ending_no(name):
    return int(name.rsplit("_", 1)[1])


# ---------------------------------------------------------------------------
# Nguồn dữ liệu


def _text_asset(path, want):
    env = UnityPy.load(path)
    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        data = obj.read()
        if data.m_Name == want:
            raw = data.m_Script
            raw = raw.encode("utf-8", "surrogateescape") if isinstance(raw, str) else bytes(raw)
            return raw
    raise KeyError(want)


def titles():
    """#recollection_NN -> tiêu đề đã dịch, khoá theo số ending."""
    doc = json.loads(_text_asset(os.path.join(PATCH, JSON_REL), "SceneReplayData").decode("utf-8-sig"))
    out = {}
    for group in doc["list"]:
        for item in group["items"]:
            out[int(item["label"].rsplit("_", 1)[1])] = item["title"]["jp"]
    return out


def fonts(cache):
    """Rút TTF nhúng trong ui_jp của bản dịch ra đĩa cho PIL dùng."""
    os.makedirs(cache, exist_ok=True)
    want = {FONT_PIXEL, FONT_LIGHT, FONT_BOLD}
    out = {}
    env = UnityPy.load(os.path.join(PATCH, UI_REL))
    for obj in env.objects:
        if obj.type.name != "Font":
            continue
        data = obj.read()
        if data.m_Name not in want:
            continue
        path = os.path.join(cache, data.m_Name + ".ttf")
        blob = bytes(data.m_FontData)
        if not os.path.exists(path) or open(path, "rb").read() != blob:
            open(path, "wb").write(blob)
        out[data.m_Name] = path
    missing = want - set(out)
    if missing:
        raise SystemExit(f"thiếu font trong ui_jp: {sorted(missing)}")
    return out


# ---------------------------------------------------------------------------
# Xoá chữ cũ


def ink_mask(arr, band, mode, thr):
    y0, y1, x0, x1 = band
    mask = np.zeros(arr.shape[:2], bool)
    lum = arr[y0:y1, x0:x1, :3].sum(2)
    mask[y0:y1, x0:x1] = lum > thr if mode == "light" else lum < thr
    return mask


def _grow(mask, radius, op):
    out = mask.copy()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            shifted = np.roll(np.roll(mask, dy, 0), dx, 1)
            out = out | shifted if op == "dilate" else out & shifted
    return out


def core_color(arr, mask, radius=2):
    core = _grow(mask, radius, "erode")
    if not core.any():
        core = mask
    return tuple(int(v) for v in np.median(arr[core][:, :3], 0))


def erase(arr, mask, band):
    """Nội suy dọc từng cột: pixel trong mask lấy từ hàng sạch trên/dưới."""
    y0, y1 = band[0], band[1]
    out = arr.astype(float)
    height = arr.shape[0]
    for x in np.where(mask.any(0))[0]:
        rows = np.where(mask[:, x])[0]
        rows = rows[(rows >= y0) & (rows < y1)]
        if not len(rows):
            continue
        runs, start, prev = [], rows[0], rows[0]
        for y in rows[1:]:
            if y == prev + 1:
                prev = y
            else:
                runs.append((start, prev))
                start = prev = y
        runs.append((start, prev))
        for lo, hi in runs:
            top, bot = lo - 1, hi + 1
            if top < 0 or bot >= height:
                continue
            c0, c1 = out[top, x], out[bot, x]
            span = hi - lo + 2
            for step, y in enumerate(range(lo, hi + 1), 1):
                out[y, x] = c0 + (c1 - c0) * step / span
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Vẽ chữ mới


def _stamp(size, draw_fn, baseline_y, shear=0.0):
    """Vẽ chữ ra ảnh L rồi (tuỳ chọn) làm nghiêng **quanh đường chân chữ**.

    Nghiêng quanh tâm ảnh sẽ đẩy cả dòng sang ngang vài pixel — lấy baseline làm
    trục thì chân chữ đứng yên, đúng như font nghiêng thật."""
    pad = 200
    canvas = Image.new("L", (size[0] + 2 * pad, size[1] + 2 * pad), 0)
    draw_fn(ImageDraw.Draw(canvas), pad)
    if shear:
        pivot = pad + baseline_y
        canvas = canvas.transform(
            canvas.size, Image.AFFINE, (1, shear, -shear * pivot, 0, 1, 0), Image.BICUBIC)
    return canvas, pad


def render_pixel(text, font_path, size):
    """Chữ điểm ảnh: cỡ phải là bội số 16 để không bị khử răng cưa."""
    if size % 16:
        raise ValueError(f"cỡ {size} lệch lưới 16 px/em của ULPixel")
    font = ImageFont.truetype(font_path, size)
    width = int(round(font.getlength(text)))
    img, pad = _stamp((width, size * 2),
                      lambda d, p: d.text((p, p + size), text, font=font, fill=255, anchor="ls"), size)
    return img, pad, pad + size, width


def composite(arr, stamp, origin, baseline, color):
    """Dán chữ (ảnh L làm alpha) lên ảnh nền."""
    alpha = np.asarray(stamp).astype(float) / 255.0
    sh, sw = alpha.shape
    x0 = origin[0]
    y0 = baseline - origin[1]
    xs0, xs1 = max(0, -x0), min(sw, arr.shape[1] - x0)
    ys0, ys1 = max(0, -y0), min(sh, arr.shape[0] - y0)
    if xs0 >= xs1 or ys0 >= ys1:
        return arr
    sub = alpha[ys0:ys1, xs0:xs1][:, :, None]
    dst = arr[y0 + ys0:y0 + ys1, x0 + xs0:x0 + xs1, :3].astype(float)
    arr[y0 + ys0:y0 + ys1, x0 + xs0:x0 + xs1, :3] = np.clip(
        dst * (1 - sub) + np.array(color, float) * sub + 0.5, 0, 255).astype(np.uint8)
    return arr


# ---------------------------------------------------------------------------


def build(arr, name, title, spec, font_files, report):
    variant = variant_of(name)
    no = ending_no(name)
    mask = ink_mask(arr, spec["band"], spec["mode"], spec["thr"])
    if not mask.any():
        raise SystemExit(f"{name}: không tìm thấy nét chữ trong khung {spec['band']}")
    ys, xs = np.where(mask)
    old = (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()))
    color = core_color(arr, mask)
    arr = erase(arr, _grow(mask, 3, "dilate"), spec["band"])

    if variant == "b_bad_sad":
        arr, new = _draw_sad(arr, no, title, spec, font_files, color)
    else:
        arr, new = _draw_pixel(arr, no, title, spec, font_files, color)

    lo, hi = spec["safe"]
    report.append(dict(name=name, no=no, title=title, color=color,
                       old=old, new=new, over=new[0] < lo or new[1] > hi))
    return arr


def _draw_pixel(arr, no, title, spec, font_files, color):
    text = f"#{no:03d}  {title}"
    stamp, ox, oy, width = render_pixel(text, font_files[FONT_PIXEL], spec["size"])
    x0 = int(round(spec["center"] - width / 2))
    arr = composite(arr, stamp, (x0 - ox, oy), spec["baseline"], color)
    ink = np.asarray(stamp) > 0
    iy, ix = np.where(ink)
    return arr, (x0 - ox + int(ix.min()), x0 - ox + int(ix.max()),
                 spec["baseline"] - oy + int(iy.min()), spec["baseline"] - oy + int(iy.max()))


def _draw_sad(arr, no, title, spec, font_files, color):
    """`#NN` đứng thẳng, đậm hơn; tiêu đề mảnh và nghiêng — như tranh gốc."""
    prefix = f"#{no:02d}"
    fb = ImageFont.truetype(font_files[FONT_BOLD], spec["prefix_size"])
    fl = ImageFont.truetype(font_files[FONT_LIGHT], spec["size"])
    gap = int(round(spec["size"] * 0.55))
    wp = int(round(fb.getlength(prefix)))
    wt = int(round(fl.getlength(title)))
    width = wp + gap + wt
    x0 = int(round(spec["center"] - width / 2))

    sp, pad = _stamp((wp, spec["prefix_size"] * 3),
                     lambda d, p: d.text((p, p + spec["prefix_size"]), prefix, font=fb, fill=255, anchor="ls"),
                     spec["prefix_size"])
    arr = composite(arr, sp, (x0 - pad, pad + spec["prefix_size"]), spec["prefix_baseline"], PREFIX_COLOR)
    st, pad2 = _stamp((wt, spec["size"] * 3),
                      lambda d, p: d.text((p, p + spec["size"]), title, font=fl, fill=255, anchor="ls"),
                      spec["size"], shear=spec["shear"])
    arr = composite(arr, st, (x0 + wp + gap - pad2, pad2 + spec["size"]), spec["baseline"], color)
    return arr, (x0, x0 + width, spec["baseline"] - spec["size"], spec["baseline"] + spec["size"] // 3)


PREFIX_COLOR = (149, 149, 149)


# ---------------------------------------------------------------------------


def run(apply_it):
    src = os.path.join(STOCK, REL)
    dst = os.path.join(PATCH, REL)
    if not os.path.exists(src):
        raise SystemExit(f"không thấy bản gốc {src}")
    # Font rút ra chỗ tạm, không để trong repo — 8,6 MB nhị phân dựng lại được.
    font_files = fonts(os.path.join(tempfile.gettempdir(), "unlogical-endcard-fonts"))
    title_by_no = titles()

    env = UnityPy.load(src)
    report = []
    for obj in env.objects:
        if obj.type.name != "Texture2D":
            continue
        data = obj.read()
        name = data.m_Name
        spec = VARIANTS[variant_of(name)]
        arr = np.asarray(data.image.convert("RGB")).astype(np.uint8).copy()
        arr = build(arr, name, title_by_no[ending_no(name)], spec, font_files, report)
        img = Image.fromarray(arr)
        os.makedirs(PREVIEW, exist_ok=True)
        img.crop((spec["safe"][0] - 60, spec["band"][0] - 90,
                  spec["safe"][1] + 60, spec["band"][1] + 40)).save(
            os.path.join(PREVIEW, name + ".png"))
        if apply_it:
            data.image = img
            data.save()

    report.sort(key=lambda r: r["no"])
    for r in report:
        flag = "  <-- TRÀN LỀ" if r["over"] else ""
        print(f'  #{r["no"]:03d} {r["name"]:24s} cũ x{r["old"][0]}..{r["old"][1]} '
              f'-> mới x{r["new"][0]}..{r["new"][1]} y{r["new"][2]}..{r["new"][3]} '
              f'mực {r["color"]}  {r["title"]}{flag}')
    over = [r for r in report if r["over"]]
    print(f"\n{len(report)} thẻ, {len(over)} tràn lề, preview trong {PREVIEW}")

    if not apply_it:
        return len(over)

    os.makedirs(BACKUP, exist_ok=True)
    keep = os.path.join(BACKUP, "cg_end.endcard")
    if not os.path.exists(keep):
        shutil.copy2(src, keep)
        print(f"backup -> {keep}")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    blob = env.file.save(packer="lz4")
    tmp = dst + ".out"
    open(tmp, "wb").write(blob)
    os.replace(tmp, dst)
    print(f"ghi {dst}  {os.path.getsize(dst):,} byte (gốc {os.path.getsize(src):,})")
    return len(over)


if __name__ == "__main__":
    apply_it = "--apply" in sys.argv
    if not apply_it and "--check" not in sys.argv:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(1 if run(apply_it) else 0)
