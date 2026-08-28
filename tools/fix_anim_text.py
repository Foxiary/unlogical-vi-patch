"""Chữ Nhật nướng trong tranh sub-graphic (`StreamingAssets/anim/*`).

Kịch bản ADV gọi tranh bằng `[anim slot=0 file=NN seqno=MM …]`, trong đó `NN`
**chính là tên Texture2D** trong bundle (`file=22` -> texture `22` của `anim02`).
Nhiều tranh trong đó là ảnh chụp giao diện của chính game (trang Terminal, System
Message, màn Question…), nên một trang có thể trông như chưa dịch trong khi dữ
liệu đằng sau nó đã dịch xong từ lâu — kiểm tranh trước khi đi tìm dữ liệu.

Bundle chia theo chương: `anim02` mở màn/Stage 1, `anim03` Stage 2, `anim04`
Stage 3+, `anim06` tranh vật phẩm.

Script này **không** ghim toạ độ trong mã. Mỗi texture một file spec JSON ở
`tools/_anim_specs/<bundle>_<texture>.json`, gồm một danh sách `ops` chạy tuần tự:

```json
{
  "bundle": "anim04", "texture": "101",
  "note": "System Message — nguồn dịch: ScenarioData sID …",
  "ops": [
    {"op": "erase", "rect": [640, 415, 1280, 445],
     "detect": {"mode": "magenta"}, "how": "interp_h", "grow": 2},
    {"op": "text", "text": "Đã chia vai xong cho toàn bộ Player",
     "font": "B", "size": 26, "color": "auto",
     "align": "center", "x": 960, "y": 430, "yref": "mid", "max_width": 620}
  ]
}
```

`op` hỗ trợ:

- `erase`  — xoá chữ cũ trong `rect`.
  `detect.mode`: `magenta` (R−G ≥ `rg`, G ≤ `gmax`) | `dark` (tổng RGB ≤ `lum`) |
  `light` (tổng RGB ≥ `lum`) | `delta` (lệch màu `ref` quá `tol`) | `all` (cả khung) |
  `lowchroma` (|R−G| ≤ `rg`: chữ trung tính trên nền có màu).
  `how`: `interp_h` nội suy ngang từng hàng (mặc định) | `interp_v` nội suy dọc
  từng cột | `fill` tô phẳng bằng màu nền lấy ở mép khung.
  Chọn trục theo **hướng chuyển màu của nền**: nền chuyển dọc thì nội suy ngang,
  và ngược lại. Chọn sai để lại vệt sọc thấy rõ.
- `text`   — vẽ chữ mới. `color: "auto"` lấy trung vị lõi nét của `erase` ngay trước.
  `blur` làm mềm nét để khớp những chỗ tranh gốc vốn đã vẽ nhoè; `alpha` ghim độ đục.
  `yref`: `mid` canh giữa hộp mực cả khối | `top` mép trên hộp mực | `baseline`
  đường chân chữ dòng đầu. Canh theo `mid` gần như luôn đúng khi thay chữ Nhật
  bằng chữ Latin: dấu thanh đội lên và dấu nặng thò xuống làm hộp mực lệch hẳn.
- `copy`   — chép một khung nền sạch đè lên chỗ khác (`src` -> `dst`).

Font rút thẳng từ `ui_jp` của bản dịch (đã có dấu tiếng Việt), khoá đặt tên:
`B` đậm, `L` mảnh, `DB` gothic giao diện, `pixel` chữ điểm ảnh, `pop`, `sans`.
Riêng `elephant` là font NGOÀI (đường dẫn tuyệt đối), kiểu tít báo rất nặng.

Dùng:
    python tools\\fix_anim_text.py --list
    python tools\\fix_anim_text.py --probe anim04_101 --rect 600 400 1300 460
    python tools\\fix_anim_text.py --measure "Đã chia vai xong" --font B --size 26
    python tools\\fix_anim_text.py --preview anim04_101 [anim04_102 …]
    python tools\\fix_anim_text.py --check
    python tools\\fix_anim_text.py --apply [--bundle anim04]

`--probe` và `--preview` đọc PNG đã xuất sẵn ở thư mục làm việc nên chạy tức thì;
chỉ `--apply` mới mở bundle. Cũng như `fix_endcard_title.py`, `--apply` **luôn
dựng lại từ bản gốc `UNLOGICAL_v2`** chứ không đọc `romfs`, nên chạy lại bao
nhiêu lần cũng ra cùng kết quả.
"""

import gc
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile

import numpy as np
import UnityPy
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PATCH = os.path.join(ROOT, "romfs", "Data")
STOCK = "D:/Downloads/UNLOGICAL_v2/Data"
BACKUP = os.path.join(ROOT, "_backup")
SPECS = os.path.join(ROOT, "tools", "_anim_specs")
PREVIEW = os.path.join(ROOT, "_parked", "anim_text")
EDIT = os.path.join(ROOT, "_parked", "anim_edit")        # ảnh sửa tay (đè lên spec)
EDIT_REF = os.path.join(EDIT, "goc")                     # bản gốc để đối chiếu, không đọc lại
WORK = r"C:\Users\ADMIN\AppData\Local\Temp\claude\D--Downloads-010068501ff9a000\anim_work"
TEXDIR = os.path.join(WORK, "tex")

UI_REL = os.path.join("StreamingAssets", "ui", "ui_jp")
FONTS = {
    "B": "FOT-DNPShueiMGoStd-B",
    "L": "FOT-DNPShueiMGoStd-L",
    "DB": "FOT-NewRodinProN-DB",
    "pixel": "FOT-DotGothic12Std-M",
    "pop": "FOT-iroha21popuraStdN-R",
    "sans": "LiberationSans",
    # Font NGOÀI (không nằm trong ui_jp): đường dẫn tuyệt đối. Dùng cho những chỗ
    # bản Nhật vẽ bằng kiểu chữ tít báo rất nặng mà font trong game không có.
    "elephant": r"D:\OneDrive - vlylm\Font\Font Việt hóa\Font-Teddy-Gear-VietHoa_VnUnikey.com_\CCElephantmenTall.ttf",
}
_FONT_CACHE = {}


# ---------------------------------------------------------------------------
# font


def font_path(key):
    if key not in FONTS:
        raise SystemExit(f"font key lạ: {key!r} (có: {sorted(FONTS)})")
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    if os.path.isabs(FONTS[key]):
        if not os.path.exists(FONTS[key]):
            raise SystemExit(f"không thấy font ngoài: {FONTS[key]}")
        _FONT_CACHE[key] = FONTS[key]
        return FONTS[key]
    cache = os.path.join(tempfile.gettempdir(), "unlogical-anim-fonts")
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, FONTS[key] + ".ttf")
    if not os.path.exists(path):
        env = UnityPy.load(os.path.join(PATCH, UI_REL))
        for obj in env.objects:
            if obj.type.name != "Font":
                continue
            data = obj.read()
            if data.m_Name in FONTS.values():
                p = os.path.join(cache, data.m_Name + ".ttf")
                if not os.path.exists(p):
                    open(p, "wb").write(bytes(data.m_FontData))
    if not os.path.exists(path):
        raise SystemExit(f"thiếu font {FONTS[key]} trong ui_jp")
    _FONT_CACHE[key] = path
    return path


def load_font(key, size):
    return ImageFont.truetype(font_path(key), size)


# ---------------------------------------------------------------------------
# đo


def detect(arr, rect, spec):
    """Mask nét chữ trong `rect` theo kiểu dò đã chọn."""
    x0, y0, x1, y1 = rect
    sub = arr[y0:y1 + 1, x0:x1 + 1].astype(int)
    mode = (spec or {}).get("mode", "magenta")
    if mode == "all":
        m = np.ones(sub.shape[:2], bool)
    elif mode == "magenta":
        m = ((sub[..., 0] - sub[..., 1] >= spec.get("rg", 90))
             & (sub[..., 1] <= spec.get("gmax", 150)))
    elif mode == "dark":
        m = sub[..., :3].sum(2) <= spec.get("lum", 400)
    elif mode == "light":
        m = sub[..., :3].sum(2) >= spec.get("lum", 600)
    elif mode == "lowchroma":
        # Chữ TRUNG TÍNH (trắng/đen/vàng nhạt) trên nền CÓ MÀU. Tách bằng hiệu R−G
        # chứ không bằng độ sáng: ở dải đỏ của anim04_123, nền đỏ có R−G ≈ 100..120
        # còn chữ trắng/viền đen/chữ vàng đều ≤ 5, trong khi dải sáng của nền
        # (189..414) chồng hẳn lên dải sáng của viền đen nên `dark` bắt nhầm nền.
        m = np.abs(sub[..., 0] - sub[..., 1]) <= spec.get("rg", 40)
    elif mode == "delta":
        ref = np.array(spec["ref"], int)
        m = np.abs(sub[..., :3] - ref).sum(2) >= spec.get("tol", 90)
    else:
        raise SystemExit(f"detect.mode lạ: {mode!r}")
    if spec and spec.get("opaque", True):
        m &= sub[..., 3] > spec.get("amin", 40)
    out = np.zeros(arr.shape[:2], bool)
    out[y0:y1 + 1, x0:x1 + 1] = m
    return out


def grow_mask(mask, radius, rect=None):
    out = mask.copy()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            out |= np.roll(np.roll(mask, dy, 0), dx, 1)
    if rect is not None:
        x0, y0, x1, y1 = rect
        keep = np.zeros_like(out)
        keep[y0:y1 + 1, x0:x1 + 1] = True
        out &= keep
    return out


def ink_core(mask):
    core = mask.copy()
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        core &= np.roll(np.roll(mask, dy, 0), dx, 1)
    return core if core.any() else mask


def ink_color(arr, mask):
    core = ink_core(mask)
    if not core.any():
        return (0, 0, 0)
    return tuple(int(v) for v in np.median(arr[core][:, :3], 0))


def ink_alpha(arr, mask):
    """Alpha của lõi nét chữ gốc.

    Chữ nướng thường đục hẳn (255) trong khi tấm nền chỉ bán trong suốt (~182).
    Phải đo và dựng lại đúng mức này, nếu không chữ mới sẽ nhạt hơn chữ cũ."""
    core = ink_core(mask)
    if not core.any():
        return 255
    return int(np.median(arr[core][:, 3]))


def bbox(mask):
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def groups(idx, gap):
    if not len(idx):
        return []
    out, start, prev = [], idx[0], idx[0]
    for v in idx[1:]:
        if v > prev + gap:
            out.append((int(start), int(prev)))
            start = v
        prev = v
    out.append((int(start), int(prev)))
    return out


# ---------------------------------------------------------------------------
# ops


def op_erase(arr, op, state):
    rect = [int(v) for v in op["rect"]]
    mask = detect(arr, rect, op.get("detect"))
    state["ink"] = ink_color(arr, mask)
    state["alpha"] = ink_alpha(arr, mask)
    state["mask"] = mask
    state["mask_bbox"] = bbox(mask)
    wide = grow_mask(mask, int(op.get("grow", 2)), rect)
    how = op.get("how", "interp_h")
    x0, y0, x1, y1 = rect
    out = arr.astype(float)
    # Nội suy cả 4 kênh. Kênh ALPHA là chỗ bẫy: chữ nướng thường đục hẳn (255)
    # trên tấm nền bán trong suốt (~182), nên nếu chỉ sửa RGB thì HÌNH DẠNG chữ
    # Nhật vẫn nằm nguyên trong alpha — ghép lên cảnh sáng không thấy gì, ghép lên
    # cảnh tối là cả câu hiện lại thành chữ trắng.
    chans = range(4)
    if how == "fill":
        edge = op.get("fill_from", "edge")
        if isinstance(edge, (list, tuple)):
            col = np.array(list(edge) + [255] * (4 - len(edge)), float)[:4]
        else:
            ring = np.zeros(arr.shape[:2], bool)
            ring[y0:y1 + 1, x0:x1 + 1] = True
            ring[y0 + 1:y1, x0 + 1:x1] = False
            ring &= ~wide
            col = (np.median(arr[ring], 0).astype(float) if ring.any()
                   else np.array([255, 255, 255, 255.]))
        out[wide] = col
    elif how == "interp_h":
        for y in range(y0, y1 + 1):
            row = wide[y, x0:x1 + 1]
            if not row.any() or row.all():
                continue
            xs = np.arange(x0, x1 + 1)
            good = ~row
            for ch in chans:
                out[y, x0:x1 + 1, ch] = np.interp(xs, xs[good], out[y, x0:x1 + 1, ch][good])
    elif how == "interp_v":
        for x in range(x0, x1 + 1):
            col = wide[y0:y1 + 1, x]
            if not col.any() or col.all():
                continue
            ys = np.arange(y0, y1 + 1)
            good = ~col
            for ch in chans:
                out[y0:y1 + 1, x, ch] = np.interp(ys, ys[good], out[y0:y1 + 1, x, ch][good])
    else:
        raise SystemExit(f"erase.how lạ: {how!r}")

    # Lượt hai TUỲ CHỌN (alpha_pass), chỉ kênh alpha, bán kính rộng hơn — để dọn
    # viền khử răng cưa mà mặt nạ theo màu không bắt được. MẶC ĐỊNH TẮT: nới rộng
    # làm các nét dính thành một dải dài, và nếu nền có dốc alpha (viên thuốc
    # SELECT dốc từ 178 lên 255) thì nội suy bắc thẳng qua đỉnh dốc, cắt mất nó —
    # đo được là lật từ +17 sang −24. Chỉ bật khi nền phẳng alpha.
    if how in ("interp_h", "interp_v") and op.get("alpha_pass", False):
        halo = grow_mask(mask, int(op.get("alpha_grow", int(op.get("grow", 2)) + 3)), rect)
        if how == "interp_h":
            for y in range(y0, y1 + 1):
                row = halo[y, x0:x1 + 1]
                if not row.any() or row.all():
                    continue
                xs = np.arange(x0, x1 + 1)
                good = ~row
                out[y, x0:x1 + 1, 3] = np.interp(xs, xs[good], out[y, x0:x1 + 1, 3][good])
        else:
            for x in range(x0, x1 + 1):
                col = halo[y0:y1 + 1, x]
                if not col.any() or col.all():
                    continue
                ys = np.arange(y0, y1 + 1)
                good = ~col
                out[y0:y1 + 1, x, 3] = np.interp(ys, ys[good], out[y0:y1 + 1, x, 3][good])
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def op_copy(arr, op, state):
    x0, y0, x1, y1 = [int(v) for v in op["src"]]
    dx, dy = [int(v) for v in op["dst"]]
    patch = arr[y0:y1 + 1, x0:x1 + 1].copy()
    h, w = patch.shape[:2]
    arr[dy:dy + h, dx:dx + w] = patch
    return arr


def render_block(text, key, size, leading, tracking, align):
    """Vẽ khối chữ ra ảnh L; trả (ảnh, hộp mực, bề rộng từng dòng)."""
    font = load_font(key, size)
    lines = text.split("\n")
    widths = []
    for ln in lines:
        w = font.getlength(ln) + tracking * max(0, len(ln) - 1)
        widths.append(w)
    pad = size * 2
    W = int(max(widths) if widths else 0) + 2 * pad
    H = int(leading * max(0, len(lines) - 1)) + size * 4
    img = Image.new("L", (max(W, 8), max(H, 8)), 0)
    d = ImageDraw.Draw(img)
    base = size * 2
    for i, ln in enumerate(lines):
        if align == "center":
            ax = pad + (max(widths) - widths[i]) / 2
        elif align == "right":
            ax = pad + (max(widths) - widths[i])
        else:
            ax = pad
        y = base + i * leading
        if tracking:
            cx = ax
            for ch in ln:
                d.text((cx, y), ch, font=font, fill=255, anchor="ls")
                cx += font.getlength(ch) + tracking
        else:
            d.text((ax, y), ln, font=font, fill=255, anchor="ls")
    a = np.asarray(img)
    ys, xs = np.nonzero(a > 8)
    if not len(xs):
        return img, (0, 0, 0, 0), widths, base
    return img, (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())), widths, base


def op_text(arr, op, state, report):
    key = op.get("font", "B")
    size = int(op["size"])
    leading = op.get("leading")
    leading = int(round(size * 1.45)) if leading is None else int(leading)
    tracking = float(op.get("tracking", 0))
    align = op.get("align", "center")
    img, box, widths, base = render_block(
        op["text"], key, size, leading, tracking, align)
    bw = box[2] - box[0] + 1
    bh = box[3] - box[1] + 1

    # x/y giữ nguyên số thực: tâm viên/khung thường rơi vào .5, cắt về int lệch 1 px.
    x = float(op["x"])
    if align == "center":
        left = int(round(x - bw / 2))
    elif align == "right":
        left = int(round(x)) - bw + 1
    else:
        left = int(round(x))

    y = float(op["y"])
    yref = op.get("yref", "mid")
    if yref == "mid":
        top = int(round(y - bh / 2))
    elif yref == "top":
        top = int(round(y))
    elif yref == "baseline":
        top = int(round(y)) - (base - box[1])
    else:
        raise SystemExit(f"text.yref lạ: {yref!r}")

    color = op.get("color", "auto")
    if color == "auto":
        color = state.get("ink", (0, 0, 0))
    color = tuple(int(v) for v in color)

    # Alpha đích của nét chữ mới: mặc định lấy đúng alpha lõi nét chữ Nhật vừa xoá.
    # Không nâng alpha thì chữ mới chỉ đậm bằng tấm nền (~182/255) trong khi chữ
    # gốc đục hẳn — nhạt hơn thấy rõ khi tranh chồng lên cảnh.
    want_a = op.get("alpha", "auto")
    want_a = state.get("alpha", 255) if want_a == "auto" else int(want_a)

    # Làm mềm nét: một số chỗ trong tranh gốc vốn đã bị vẽ NHOÈ (dải tin mờ, hậu
    # cảnh out nét). Vẽ chữ sắc lên đó thì lộ ra như dán vào, nên cho phép khớp
    # độ nhoè bằng cách làm mờ chính lớp phủ của nét chữ.
    if op.get("blur"):
        img = img.filter(ImageFilter.GaussianBlur(float(op["blur"])))

    alpha = np.asarray(img).astype(float) / 255.0
    ox, oy = left - box[0], top - box[1]
    sh, sw = alpha.shape
    xs0, xs1 = max(0, -ox), min(sw, arr.shape[1] - ox)
    ys0, ys1 = max(0, -oy), min(sh, arr.shape[0] - oy)
    if xs0 < xs1 and ys0 < ys1:
        sub = alpha[ys0:ys1, xs0:xs1][:, :, None]
        drawn = state.get("drawn")
        if drawn is not None:
            drawn[oy + ys0:oy + ys1, ox + xs0:ox + xs1] |= sub[..., 0] > 0.15
        dst = arr[oy + ys0:oy + ys1, ox + xs0:ox + xs1]
        view = dst[..., :3].astype(float)
        dst[..., :3] = np.clip(
            view * (1 - sub) + np.array(color, float) * sub + 0.5, 0, 255).astype(np.uint8)
        av = dst[..., 3:4].astype(float)
        dst[..., 3:4] = np.clip(
            np.maximum(av, av * (1 - sub) + want_a * sub) + 0.5, 0, 255).astype(np.uint8)

    limit = op.get("max_width")
    report.append(dict(text=op["text"].replace("\n", " ⏎ "), font=key, size=size,
                       box=(left, top, left + bw - 1, top + bh - 1),
                       width=bw, height=bh, limit=limit, color=color, alpha=want_a,
                       over=bool(limit and bw > limit)))
    return arr


OPS = {"erase": op_erase, "copy": op_copy}


def apply_spec(arr, spec, report, state=None):
    state = {} if state is None else state
    state.setdefault("drawn", np.zeros(arr.shape[:2], bool))
    for op in spec["ops"]:
        kind = op["op"]
        if kind == "text":
            arr = op_text(arr, op, state, report)
        elif kind in OPS:
            arr = OPS[kind](arr, op, state)
        else:
            raise SystemExit(f"op lạ: {kind!r}")
    return arr


# ---------------------------------------------------------------------------
# vào/ra


def edits():
    """Ảnh sửa tay: `_parked/anim_edit/<bundle>_<texture>.png`.

    Có file thì `--apply` dùng NGUYÊN XI ảnh đó và BỎ QUA spec của texture ấy —
    dùng khi cần chỉnh bằng tay những chỗ công cụ không dựng nổi (hiệu ứng, quầng
    sáng, chữ uốn theo phối cảnh). Thư mục con `goc/` chỉ để đối chiếu, không đọc.
    """
    out = {}
    if not os.path.isdir(EDIT):
        return out
    for f in sorted(os.listdir(EDIT)):
        if not f.endswith(".png"):
            continue
        stem = f[:-4]
        if "_" not in stem:
            raise SystemExit(f"{EDIT}\{f}: tên phải là <bundle>_<texture>.png")
        bundle, texture = stem.split("_", 1)
        out[(bundle, texture)] = os.path.join(EDIT, f)
    return out


def load_edit(path, bundle, texture):
    """Đọc ảnh sửa tay, kiểm cho khớp texture gốc trước khi cho ghi vào bundle."""
    want = stock_png(bundle, texture)
    img = Image.open(path)
    if img.size != (want.shape[1], want.shape[0]):
        raise SystemExit(f"{path}: cỡ {img.size[0]}x{img.size[1]} khác texture gốc "
                         f"{want.shape[1]}x{want.shape[0]} — phải giữ đúng kích thước")
    arr = np.asarray(img.convert("RGBA")).astype(np.uint8).copy()
    if want[..., 3].min() < 255 and arr[..., 3].min() == 255:
        print(f"     CẢNH BÁO: texture gốc có vùng trong suốt (alpha nhỏ nhất "
              f"{want[..., 3].min()}) mà ảnh sửa tay lại đục hoàn toàn — có phải bạn "
              f"đã làm phẳng kênh alpha không?")
    same = int((np.abs(arr.astype(int) - want.astype(int)).max(axis=2) > 4).sum())
    print(f"     ảnh sửa tay {os.path.basename(path)}: {same:,} px khác bản gốc")
    return arr


def spec_files():
    if not os.path.isdir(SPECS):
        return []
    return sorted(f for f in os.listdir(SPECS) if f.endswith(".json"))


def load_spec(name):
    path = os.path.join(SPECS, name if name.endswith(".json") else name + ".json")
    if not os.path.exists(path):
        raise SystemExit(f"không thấy spec {path}")
    spec = json.load(open(path, encoding="utf-8"))
    for k in ("bundle", "texture", "ops"):
        if k not in spec:
            raise SystemExit(f"{path}: thiếu khoá {k!r}")
    stem = os.path.basename(path)[:-5]
    if stem != f'{spec["bundle"]}_{spec["texture"]}':
        raise SystemExit(f"{path}: tên file phải là <bundle>_<texture>.json")
    return spec


def stock_png(bundle, texture):
    p = os.path.join(TEXDIR, f"{bundle}_{texture}.png")
    if not os.path.exists(p):
        raise SystemExit(f"chưa xuất {p} — chạy lại bước xuất texture")
    return np.asarray(Image.open(p).convert("RGBA")).astype(np.uint8).copy()


DARK = (24, 20, 40, 255)


def on_bg(arr, col):
    img = Image.fromarray(arr, "RGBA")
    bg = Image.new("RGBA", img.size, col)
    bg.alpha_composite(img)
    return bg.convert("RGB")


def on_white(arr):
    return on_bg(arr, (255, 255, 255, 255))


def alpha_ghost(before, after, spec, drawn, win=10):
    """Nét chữ cũ còn sót lại trong kênh ALPHA không?

    Trả về (rect, lệch, số px). Trên nền trắng lỗi này hoàn toàn vô hình — chữ
    nướng đục hơn tấm nền, nên xoá xong mà chỉ sửa RGB thì HÌNH DẠNG chữ Nhật vẫn
    nằm trong alpha và hiện lại khi tranh chồng lên cảnh tối.

    Nền so sánh phải lấy CỤC BỘ: mỗi pixel nét so với trung vị alpha của các pixel
    không-nét trong cùng hàng, trong khoảng ±win. Lấy nền trung bình cả khung là
    sai — viên thuốc SELECT có dốc alpha 178..255 ngang khung, nền trung bình nuốt
    luôn độ dốc và báo lệch +17 trong khi bóng ma thật chỉ ~5.

    `drawn` là chỗ đã vẽ chữ mới, phải loại ra: ở đó alpha cao là ĐÚNG. Không suy
    ra chỗ đó bằng cách so RGB — chữ mới cũng đậm như chữ cũ nên sẽ bỏ sót."""
    out = []
    skip = grow_mask(drawn, 2) if drawn is not None and drawn.any() else np.zeros(
        before.shape[:2], bool)
    for op in spec["ops"]:
        if op["op"] != "erase":
            continue
        rect = [int(v) for v in op["rect"]]
        mask = detect(before, rect, op.get("detect"))
        core = ink_core(mask) & ~skip
        near = grow_mask(mask, 3, rect)
        x0, y0, x1, y1 = rect
        diffs = []
        for y in range(y0, y1 + 1):
            ink_x = np.nonzero(core[y, x0:x1 + 1])[0]
            if not len(ink_x):
                continue
            bg_x = np.nonzero(~near[y, x0:x1 + 1] & ~skip[y, x0:x1 + 1])[0]
            if len(bg_x) < 4:
                continue
            a = after[y, x0:x1 + 1, 3].astype(float)
            # Đường nền = nội suy alpha của các pixel SẠCH dọc theo hàng. Lấy trung
            # vị trong cửa sổ ±win thì trong dòng chữ dày quanh mỗi nét không đủ
            # pixel sạch, cả hàng bị bỏ và bộ dò im lặng ngay cả khi lỗi rất to.
            base = np.interp(np.arange(len(a)), bg_x, a[bg_x])
            diffs.extend((a[ink_x] - base[ink_x]).tolist())
        if len(diffs) < 20:
            continue
        gap = int(np.median(diffs))
        if abs(gap) > 10:
            out.append((tuple(rect), gap, len(diffs)))
    return out


def op_union(spec, arr_shape, margin=30):
    boxes = [o["rect"] for o in spec["ops"] if o["op"] == "erase"]
    boxes += [[o["x"] - 400, o["y"] - 60, o["x"] + 400, o["y"] + 60]
              for o in spec["ops"] if o["op"] == "text"]
    if not boxes:
        return (0, 0, arr_shape[1], arr_shape[0])
    x0 = max(0, min(b[0] for b in boxes) - margin)
    y0 = max(0, min(b[1] for b in boxes) - margin)
    x1 = min(arr_shape[1], max(b[2] for b in boxes) + margin)
    y1 = min(arr_shape[0], max(b[3] for b in boxes) + margin)
    return (int(x0), int(y0), int(x1), int(y1))


def preview(names):
    os.makedirs(PREVIEW, exist_ok=True)
    bad = 0
    for name in names:
        spec = load_spec(name)
        stem = f'{spec["bundle"]}_{spec["texture"]}'
        before = stock_png(spec["bundle"], spec["texture"])
        report, state = [], {}
        # Texture đã bị ảnh sửa tay ĐÈ LÊN thì spec không còn hiệu lực — preview phải
        # dùng ảnh đó, nếu không báo cáo sẽ nói về chữ mà game không hề hiện.
        ov = edits().get((spec["bundle"], spec["texture"]))
        if ov:
            after = load_edit(ov, spec["bundle"], spec["texture"])
        else:
            after = apply_spec(before.copy(), spec, report, state)
        on_white(after).save(os.path.join(PREVIEW, stem + ".png"))
        box = op_union(spec, before.shape)
        # Bốn ô: gốc/mới trên nền sáng, gốc/mới trên nền TỐI. Bóng ma alpha chỉ
        # hiện ở hàng dưới — trên nền trắng nó vô hình.
        tiles = [on_white(before).crop(box), on_white(after).crop(box),
                 on_bg(before, DARK).crop(box), on_bg(after, DARK).crop(box)]
        w, h = tiles[0].size
        cmp = Image.new("RGB", (w, h * 4 + 36), (40, 40, 40))
        for i, t in enumerate(tiles):
            cmp.paste(t, (0, i * (h + 12)))
        cmp.save(os.path.join(PREVIEW, stem + "_cmp.png"))
        tag = "  [ẢNH SỬA TAY — spec bị bỏ qua]" if ov else ""
        print(f'== {stem}{tag}  {spec.get("note", "")[:90]}')
        for r in report:
            flag = "  <-- TRÀN KHUNG" if r["over"] else ""
            lim = r["limit"] if r["limit"] is not None else "-"
            print(f'   [{r["font"]}/{r["size"]}] x{r["box"][0]}..{r["box"][2]} '
                  f'y{r["box"][1]}..{r["box"][3]} rộng {r["width"]}/{lim} '
                  f'mực {r["color"]} a{r["alpha"]}  {r["text"][:60]}{flag}')
            bad += r["over"]
        for rect, gap, n in ([] if ov else alpha_ghost(before, after, spec, state.get("drawn"))):
            print(f'   <-- BÓNG MA ALPHA ở {rect}: lệch {gap:+d}/255 trên {n} px '
                  f'(chữ cũ còn nguyên hình trong kênh alpha)')
            bad += 1
        print(f'   preview: {os.path.join(PREVIEW, stem + "_cmp.png")}')
    return bad


def probe(name, rect, mode, extra):
    spec_arr = stock_png(*name.split("_", 1))
    x0, y0, x1, y1 = rect
    det = dict(mode=mode)
    det.update(extra)
    mask = detect(spec_arr, (x0, y0, x1, y1), det)
    bb = bbox(mask)
    print(f"khung x{x0}..{x1} y{y0}..{y1}  detect={det}")
    if bb is None:
        print("  không bắt được pixel nào")
        return
    print(f"  hộp mực x{bb[0]}..{bb[2]} (rộng {bb[2]-bb[0]+1}) "
          f"y{bb[1]}..{bb[3]} (cao {bb[3]-bb[1]+1})  tâm ({(bb[0]+bb[2])/2}, {(bb[1]+bb[3])/2})")
    print(f"  màu mực {ink_color(spec_arr, mask)}  px={int(mask.sum())}")
    rows = np.nonzero(mask.any(axis=1))[0]
    cols = np.nonzero(mask.any(axis=0))[0]
    print(f"  dải hàng (gap 4): {groups(rows, 4)}")
    print(f"  dải cột  (gap 12): {groups(cols, 12)}")
    sub = spec_arr[y0:y1 + 1, x0:x1 + 1]
    print(f"  alpha min/max trong khung: {sub[...,3].min()}/{sub[...,3].max()}")
    ring = ~mask[y0:y1 + 1, x0:x1 + 1]
    if ring.any():
        print(f"  màu nền (trung vị ngoài mực): "
              f"{tuple(int(v) for v in np.median(sub[ring][:, :3], 0))}")


def check():
    names = [f[:-5] for f in spec_files()]
    over = edits()
    if not names and not over:
        print("chưa có spec nào trong " + SPECS)
        return 0
    bad = preview(names) if names else 0
    if over:
        print()
        print("!" * 62)
        print("ẢNH SỬA TAY đang ĐÈ LÊN spec — --apply sẽ dùng nguyên xi các ảnh này,")
        print("mọi thay đổi trong spec của chúng sẽ BỊ BỎ QUA:")
        for (b, t), path in sorted(over.items()):
            has = " (có spec, spec bị bỏ qua)" if f"{b}_{t}" in names else " (không có spec)"
            print(f"   {b}_{t}{has}  <- {path}")
        print("Muốn quay lại dùng spec thì xoá file png tương ứng.")
        print("!" * 62)
    return bad


def write_bundle(bundle, specs, over=None):
    rel = os.path.join("StreamingAssets", "anim", bundle)
    src, dst = os.path.join(STOCK, rel), os.path.join(PATCH, rel)
    if not os.path.exists(src):
        raise SystemExit(f"không thấy bản gốc {src}")
    over = over or {}
    by_tex = {s["texture"]: s for s in specs}
    want = set(by_tex) | set(over)
    env = UnityPy.load(src)
    done, report = set(), []
    for obj in env.objects:
        if obj.type.name != "Texture2D":
            continue
        data = obj.read()
        name = data.m_Name
        if name not in want:
            continue
        if name in over:
            # Ảnh sửa tay THẮNG spec: ghi nguyên xi, không chạy op nào.
            note = " (ĐÈ LÊN spec)" if name in by_tex else ""
            print(f"   {bundle}/{name}: dùng ảnh sửa tay{note}")
            arr = load_edit(over[name], bundle, name)
        else:
            arr = np.asarray(data.image.convert("RGBA")).astype(np.uint8).copy()
            arr = apply_spec(arr, by_tex[name], report)
        data.image = Image.fromarray(arr, "RGBA")
        data.save()
        done.add(name)
    missing = want - done
    if missing:
        raise SystemExit(f"{bundle}: không thấy texture {sorted(missing)}")
    os.makedirs(BACKUP, exist_ok=True)
    keep = os.path.join(BACKUP, bundle + ".animtext")
    if not os.path.exists(keep):
        shutil.copy2(src, keep)
        print(f"  backup -> {keep}")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    blob = env.file.save(packer="lz4")
    # Ghi ĐÈ TẠI CHỖ, không os.replace: UnityPy (và Ryujinx nếu đang chạy) còn giữ
    # handle trên file, nên đổi tên báo WinError 5 trong khi ghi 'r+b' vẫn được.
    del env
    gc.collect()
    if os.path.exists(dst):
        with open(dst, "r+b") as f:
            f.write(blob)
            f.truncate()
    else:
        open(dst, "wb").write(blob)
    got = hashlib.sha256(open(dst, "rb").read()).hexdigest()
    if got != hashlib.sha256(blob).hexdigest():
        raise SystemExit(f"{bundle}: ghi xong nhưng sha256 không khớp")
    print(f"  ghi {dst}  {os.path.getsize(dst):,} byte "
          f"(gốc {os.path.getsize(src):,}), {len(done)} texture, sha {got[:12]}")
    return len(done)


def apply(only=None):
    specs = [load_spec(f) for f in spec_files()]
    over_all = edits()
    if only:
        specs = [s for s in specs if s["bundle"] == only]
        over_all = {k: v for k, v in over_all.items() if k[0] == only}
    if not specs and not over_all:
        raise SystemExit("không có spec nào để áp")
    by_bundle, over_bundle = {}, {}
    for s in specs:
        by_bundle.setdefault(s["bundle"], []).append(s)
    for (b, t), path in over_all.items():
        over_bundle.setdefault(b, {})[t] = path
        by_bundle.setdefault(b, [])
    total = 0
    for bundle in sorted(by_bundle):
        ov = over_bundle.get(bundle, {})
        n = len(set(x["texture"] for x in by_bundle[bundle]) | set(ov))
        extra = f", {len(ov)} ảnh sửa tay" if ov else ""
        print(f"== {bundle}  ({n} texture{extra})")
        total += write_bundle(bundle, by_bundle[bundle], ov)
    print(f"\nxong {total} texture / {len(by_bundle)} bundle")
    if over_all:
        print("ẢNH SỬA TAY dùng nguyên xi cho: "
              + ", ".join(sorted(f"{b}_{t}" for b, t in over_all)))
    return 0


def export(names):
    """Xuất PNG để sửa tay: bản hiện tại (đã vá) + bản gốc để đối chiếu."""
    os.makedirs(EDIT, exist_ok=True)
    os.makedirs(EDIT_REF, exist_ok=True)
    for name in names:
        bundle, texture = name.split("_", 1)
        stock = stock_png(bundle, texture)
        try:
            spec = load_spec(name)
            cur = apply_spec(stock.copy(), spec, [])
            src = "bản đã vá"
        except SystemExit:
            cur = stock.copy()
            src = "bản gốc (chưa có spec)"
        a = os.path.join(EDIT, name + ".png")
        b = os.path.join(EDIT_REF, name + ".png")
        Image.fromarray(cur, "RGBA").save(a)
        Image.fromarray(stock, "RGBA").save(b)
        print(f"  {name}  {cur.shape[1]}x{cur.shape[0]}  alpha "
              f"{stock[..., 3].min()}..{stock[..., 3].max()}  ({src})")
        print("     SỬA FILE NÀY -> " + a)
        print("     bản gốc      -> " + b)
    print("\nSửa xong chạy:  python tools\\fix_anim_text.py --apply")
    print("Ảnh trong " + EDIT + " được dùng NGUYÊN XI và ĐÈ LÊN spec của texture đó.")
    print("Muốn quay lại dùng spec thì xoá file png đó đi.")
    return 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--list" in argv:
        for f in spec_files():
            s = load_spec(f)
            n = sum(1 for o in s["ops"] if o["op"] == "text")
            print(f'  {f[:-5]:16s} {n:2d} khối chữ  {s.get("note","")[:80]}')
        raise SystemExit(0)
    if "--measure" in argv:
        i = argv.index("--measure")
        text = argv[i + 1]
        key = argv[argv.index("--font") + 1] if "--font" in argv else "B"
        size = int(argv[argv.index("--size") + 1]) if "--size" in argv else 22
        f = load_font(key, size)
        for ln in text.split("\\n"):
            print(f"  [{key}/{size}] rộng {f.getlength(ln):.0f} px  {ln}")
        raise SystemExit(0)
    if "--probe" in argv:
        i = argv.index("--probe")
        name = argv[i + 1]
        r = argv.index("--rect")
        rect = [int(v) for v in argv[r + 1:r + 5]]
        mode = argv[argv.index("--mode") + 1] if "--mode" in argv else "magenta"
        extra = json.loads(argv[argv.index("--det") + 1]) if "--det" in argv else {}
        probe(name, rect, mode, extra)
        raise SystemExit(0)
    if "--preview" in argv:
        i = argv.index("--preview")
        names = [a for a in argv[i + 1:] if not a.startswith("--")]
        raise SystemExit(1 if preview(names) else 0)
    if "--export" in argv:
        i = argv.index("--export")
        names = [a for a in argv[i + 1:] if not a.startswith("--")]
        if not names:
            raise SystemExit("cần tên texture, ví dụ: --export anim04_123 anim02_2")
        raise SystemExit(export(names))
    if "--check" in argv:
        raise SystemExit(1 if check() else 0)
    if "--apply" in argv:
        only = argv[argv.index("--bundle") + 1] if "--bundle" in argv else None
        raise SystemExit(apply(only))
    print(__doc__)
    raise SystemExit(2)
