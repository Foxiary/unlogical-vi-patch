# -*- coding: utf-8 -*-
"""Vẽ lại hai tấm biển `ＤＬＣ 第１弾` / `ＤＬＣ 第２弾` ở màn Download Contents.

Báo 04/09/2026 kèm ảnh `IMG_7249` (chụp máy Switch thật): màn chọn gói DLC vẫn còn tiếng
Nhật, trong khi dải phím dưới đã là `Select`/`Back` và tên nhân vật đã romanise — tức mod
gốc đang chạy đúng, chỉ là **thiếu hẳn một file**.

Chữ đó là TRANH, không phải chuỗi: 5 sprite trong atlas `DLC_TOP` của
`StreamingAssets/ui/ui01` — một bundle 1,26 MB **chưa từng có trong danh sách file ship**.
Đã dò cả bản dump: không TextAsset nào chứa `第1弾`, chỉ `SystemTextData` id 24 có hộp thoại
"chưa mua" (đã dịch từ trước, lấy nguyên văn tiếng Anh chính thức theo luật ô JP).

    UL_dlc_b_menu_1st_off / _on     534x160 / 534x190   `ＤＬＣ 第１弾`
    UL_dlc_b_menu_2nd_off / _on     534x160 / 534x190   `ＤＬＣ 第２弾`
    UL_dlc_b_menu_1st_notyet        652x210             cửa sổ 3 dòng "tải miễn phí…"

## Bốn tấm biển: xáo chữ có sẵn, KHÔNG vẽ lại bằng font

Chủ sở hữu chốt 04/09/2026: `ＤＬＣ 第Ｎ弾` -> **`DLC N`**, và canh giữa lại sau khi bỏ chữ.

Chuỗi mới là **tập con của chuỗi cũ** (`ＤＬＣ` và chữ số vẫn còn, chỉ bỏ `第` với `弾`), nên
tool không dựng chữ bằng font mà **bê nguyên pixel của game**: cắt cụm mực `ＤＬＣ` và cụm
chữ số ra, xoá cả dòng, dán lại ở chỗ mới. Không lệch cỡ, không lệch nét, không lệch màu —
ba thứ dễ sai nhất khi vẽ font điểm ảnh (xem `fix_dlc_art.py`).

Đo trên bản gốc, cả 4 sprite trùng khít nhau:

    Ｄ 161..182   Ｌ 197..213   Ｃ 229..249   第 276..305   １ 319..329 / ２ 315..333   弾 344..372

Bố cục mới = `ＤＬＣ` + khe + chữ số, canh giữa đúng tâm cũ (266,5). Khe lấy đúng khe
`Ｃ`→`第` của bản gốc (27 px) vì đó chính là dấu cách. Kết quả: `ＤＬＣ` dịch phải 43 px
(bản `1st`) / 39 px (`2nd`), còn **chữ số nằm nguyên chỗ cũ** — bố cục gốc canh giữa và hai
kanji bỏ đi nằm hai bên chữ số nên nó tự rơi đúng chỗ. Tool assert lại điều đó thay vì tin.

## Cửa sổ "chưa mua" thì phải vẽ bằng font

Ba dòng chữ Nhật nên không xáo được. Vẽ bằng ULPixel trích từ `ui_jp` (`fontcache.ttf`,
cùng font `fix_dlc_art.py` dùng — DotGothic gốc **không có** chữ Việt). Cỡ chọn theo chiều
cao chữ HOA La-tinh của chính bản gốc: dòng 1 vốn mở đầu bằng `DLC`, chữ `D` cao đúng
**20 px** (kanji thì 24), nên canh theo `D` chứ không theo kanji. Mực (107,41,148), trái
x=40, đỉnh chữ hoa y = 79 / 114 / 150 (bước dòng 35,5 px của bản gốc).

## Xoá thế nào cho không mất nền

Nền sau chữ **phẳng**: trắng (bản `off` và `notyet`), bạc hà (165,245,238) ở `1st_on`, hồng
(255,216,222) ở `2nd_on`. Lưới phối cảnh của hai bản `on` nằm ở mép trái và đáy, **không**
cắt qua dòng chữ — đã đo: trong hộp mực nới 2 px không có pixel trắng nào. Nên xoá =
"mọi pixel khác nền" trong hộp bao quanh chữ, tô thẳng bằng màu nền; cách này ăn luôn viền
khử răng cưa, thứ mà mặt nạ theo màu hay bỏ sót (bài học của `fix_dlc_art.py`). Hộp xoá bó
sát chữ (nới 8 px ngang, 4 px dọc) để không chạm khung, ngôi sao lấp lánh hay mũi tên.

Tool tự đếm và **từ chối chạy** nếu trong hộp xoá có pixel sáng hơn nền (kẻ lưới) — nếu bản
game đổi bố cục thì phải xem lại bằng mắt chứ không xoá mù.

## Ship thêm một file

`ui01` là file thứ 36 của title gốc. Nhớ ba chỗ: `manifest.json`, bảng "what each shipped
binary holds" trong `CLAUDE.md`, và cây thư mục trong `README.md`. `make_release.py` tự suy
thư mục zip từ đường dẫn nên không phải sửa.

Texture `DLC_TOP` vốn stream từ `.resS` **bên trong bundle**; UnityPy inline nó khi ghi ảnh
mới, nên file phình ra (như `sprite_jp_aoc01` 1,3 -> 2,5 MB). Năm texture còn lại vẫn stream
bình thường.

    python tools\\fix_dlc_top_menu.py            # chạy thử, xuất ảnh xem trước
    python tools\\fix_dlc_top_menu.py --apply
    python tools\\fix_dlc_top_menu.py --check    # file đã ghi: mesh quad + render khớp ô atlas
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# import trước mọi print: fix_dlc_art bọc sys.stdout thành UTF-8 (bọc chồng là hỏng buffer)
from fix_dlc_art import draw_text, match_size    # noqa: E402
from keyart import Container, render_check       # noqa: E402
from fontcache import ttf                        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

SRC = r"D:\Downloads\UNLOGICAL_v2\Data\StreamingAssets\ui\ui01"
DST = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui01")
PREVIEW = os.path.join(ROOT, "_preview", "dlc_top")
BACKUP = os.path.join(ROOT, "_backup")

PIXEL = "FOT-DotGothic12Std-M"      # ULPixel trong bản patch
INK_LUM = 450                       # mực tím (~107,41,148 = 296) tối hơn hẳn mọi thứ khác:
                                    # viền hoa cà 602, bạc hà 648, hồng 693, trắng 765
CAP_H = 20                          # chữ `D` của dòng 1 cửa sổ notyet cao 20 px
PAD_Y = 2                           # nới hộp xoá 2 px trên/dưới. 4 px là chạm kẻ lưới nằm
                                    # ngay y=145 của `1st_on` (cách chân chữ đúng 3 px)
LINE_MAX = 12                       # sáng hơn nền mà liền hơn ngần này trên một hàng/cột
                                    # thì là kẻ lưới, không phải đốm giải mã ASTC
NOTYET_X = 40                       # mép trái MỰC, đo trên bản gốc (chữ `D` dòng 1)
NOTYET_BASE = (99, 134, 170)        # đường chân chữ từng dòng: đỉnh chữ hoa 79/114/150 +
                                    # chiều cao chữ hoa 20 (bước dòng 35,5 px của bản gốc)
NOTYET = [
    "DLC 1 có thể tải về miễn phí.",          # ＤＬＣ第１弾は無料ダウンロードが可能です。
    "Nhấn nút xác nhận để chuyển",            # 決定ボタンを押すと、
    "sang màn hình Nintendo eShop.",          # ニンテンドーeショップ画面に遷移します。
]


def ink_mask(a):
    return (a[..., :3].sum(2) < INK_LUM) & (a[..., 3] > 100)


def col_groups(mask, gap=6):
    """Cụm cột liền nhau; khe < `gap` px coi như cùng một chữ (`弾` gốc đứt làm hai)."""
    cols = mask.any(0)
    runs, inr = [], False
    for x, v in enumerate(cols):
        if v and not inr:
            st, inr = x, True
        elif not v and inr:
            runs.append([st, x])
            inr = False
    if inr:
        runs.append([st, len(cols)])
    out = [runs[0]]
    for r in runs[1:]:
        if r[0] - out[-1][1] < gap:
            out[-1][1] = r[1]
        else:
            out.append(r)
    return [tuple(r) for r in out]


def flat_bg(a, box):
    """Màu nền của hộp xoá, và độ "có cấu trúc" của những pixel sáng hơn nền.

    Cần phân biệt hai thứ: **kẻ lưới** (một hàng/cột liền, xoá là mất nền) với **đốm lẻ**
    (vài pixel rải rác do giải mã ASTC, xoá vô hại). Nên chốt không phải tổng số pixel sáng
    mà là số pixel sáng nhiều nhất trên một hàng hoặc một cột.
    """
    x0, y0, x1, y1 = box
    sub = a[y0:y1, x0:x1]
    m = ~ink_mask(sub)
    cols, cnt = np.unique(sub[m].reshape(-1, 4), axis=0, return_counts=True)
    bg = cols[np.argmax(cnt)]
    bright = (sub[..., :3].sum(2) > int(bg[:3].sum()) + 45) & m
    line = max(int(bright.sum(0).max()), int(bright.sum(1).max())) if bright.any() else 0
    return bg, int(bright.sum()), line


def erase_box(a, box, bg):
    x0, y0, x1, y1 = box
    a[y0:y1, x0:x1] = bg
    return a


def menu(img, name, report):
    """`ＤＬＣ 第Ｎ弾` -> `DLC N`: cắt cụm mực có sẵn, xoá dòng, dán lại đã canh giữa."""
    a = np.array(img)
    ai = a.astype(int)
    m = ink_mask(ai)
    ys, xs = np.nonzero(m)
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    g = col_groups(m[y0:y1])
    if len(g) != 6:
        raise SystemExit("%s: thấy %d cụm chữ, chờ 6 (ＤＬＣ 第 số 弾)" % (name, len(g)))
    dlc = (g[0][0], g[2][1])
    kanji1, digit, kanji2 = g[3], g[4], g[5]
    space = kanji1[0] - dlc[1]
    centre = (int(xs.min()) + int(xs.max()) + 1) / 2

    box = (dlc[0] - 8, y0 - PAD_Y, kanji2[1] + 8, y1 + PAD_Y)
    bg, bright, line = flat_bg(ai, box)
    if line > LINE_MAX:
        raise SystemExit("%s: %d pixel sáng liền một hàng/cột trong hộp xoá — có kẻ lưới, "
                         "bó hộp lại rồi chạy lại" % (name, line))

    keep = {}
    for tag, (gx0, gx1) in (("dlc", dlc), ("digit", digit)):
        keep[tag] = a[box[1]:box[3], gx0:gx1].copy()
        keep[tag + "_m"] = np.any(a[box[1]:box[3], gx0:gx1] != bg, axis=2)

    total = (dlc[1] - dlc[0]) + space + (digit[1] - digit[0])
    start = int(round(centre - total / 2))
    new_dlc = start
    new_digit = start + (dlc[1] - dlc[0]) + space
    if new_digit != digit[0]:
        raise SystemExit("%s: chữ số phải nằm nguyên chỗ (tính ra %d, đang ở %d)"
                         % (name, new_digit, digit[0]))

    a = erase_box(a, box, bg)
    for tag, nx in (("dlc", new_dlc), ("digit", new_digit)):
        blk, bm = keep[tag], keep[tag + "_m"]
        dst = a[box[1]:box[3], nx:nx + blk.shape[1]]
        dst[bm] = blk[bm]

    out = Image.fromarray(a, "RGBA")
    chk = np.nonzero(ink_mask(np.array(out).astype(int)))[1]
    got = (int(chk.min()) + int(chk.max()) + 1) / 2
    if abs(got - centre) > 0.5:
        raise SystemExit("%s: tâm chữ mới %.1f != tâm cũ %.1f" % (name, got, centre))
    report.append("%-26s ＤＬＣ dịch phải %d px, chữ số giữ nguyên, tâm %.1f, nền %s, đốm lẻ %d"
                  % (name, new_dlc - dlc[0], got, tuple(int(v) for v in bg), bright))
    return out


def draw_line(img, text, font, ink, left, base):
    """Vẽ một dòng sao cho MỰC bắt đầu đúng `left` và chân chữ đúng `base`.

    Không dùng thẳng `x=` của `draw_text`: `textbbox` báo lề trái lệch 2 px so với pixel thật
    khi tắt khử răng cưa, nên dòng bị đẩy sang phải 2 px so với bản Nhật. Vẽ thử ở x=0, đo
    mực thật, rồi vẽ lại đúng chỗ. Canh dọc theo chân chữ (anchor `ls`) chứ không theo đỉnh
    hộp mực — dòng có dấu tiếng Việt thì đỉnh hộp là đỉnh dấu, không phải đỉnh chữ hoa.
    """
    probe = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(probe)
    d.fontmode = "1"
    d.text((0, base), text, font=font, fill=ink, anchor="ls")
    m = np.array(probe)[..., 3] > 0
    xs = np.nonzero(m.any(0))[0]
    ys = np.nonzero(m.any(1))[0]
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    d.text((left - int(xs.min()), base), text, font=font, fill=ink, anchor="ls")
    return left + int(xs.max() - xs.min()) + 1, int(ys.min()), int(ys.max()) + 1


def notyet(img, name, report):
    """Ba dòng chữ Nhật -> ba dòng tiếng Việt, vẽ bằng ULPixel."""
    a = np.array(img)
    ai = a.astype(int)
    m = ink_mask(ai)
    ys, xs = np.nonzero(m)
    # hộp rộng tay hơn bản menu: dấu tiếng Việt trèo lên trên đỉnh chữ hoa ~6 px, mà chữ
    # Nhật gốc thì không — bó sát hộp mực cũ là chữ mới thò ra ngoài vùng đã xoá. Nền quanh
    # đây là mảng trắng x 6..646 / y 10..203 nên nới thoải mái.
    box = (int(xs.min()) - 8, int(ys.min()) - 12, int(xs.max()) + 9, int(ys.max()) + 13)
    bg, bright, line = flat_bg(ai, box)
    if line > LINE_MAX:
        raise SystemExit("%s: %d pixel sáng liền một hàng/cột trong hộp xoá" % (name, line))
    core = (ai[..., :3].sum(2) < 380) & (ai[..., 3] > 200)
    cols, cnt = np.unique(a[core][:, :3].reshape(-1, 3), axis=0, return_counts=True)
    ink = tuple(int(v) for v in cols[np.argmax(cnt)]) + (255,)

    out = Image.fromarray(erase_box(a, box, bg), "RGBA")
    size, font = match_size(PIXEL, "D", CAP_H)
    right, top, bot = box[0], box[3], box[1]
    for text, base in zip(NOTYET, NOTYET_BASE):
        r, t, b = draw_line(out, text, font, ink, NOTYET_X, base)
        right, top, bot = max(right, r), min(top, t), max(bot, b)
    report.append("%-26s cỡ %d (chữ hoa %d px), mực %s, mực x %d..%d y %d..%d, hộp xoá %s"
                  % (name, size, CAP_H, ink[:3], NOTYET_X, right, top, bot, box))
    if right > box[2] or top < box[1] or bot > box[3]:
        raise SystemExit("%s: chữ mới tràn ra ngoài hộp đã xoá — rút chữ hoặc nới hộp" % name)
    return out


JOBS = [("UL_dlc_b_menu_1st_off", menu), ("UL_dlc_b_menu_1st_on", menu),
        ("UL_dlc_b_menu_2nd_off", menu), ("UL_dlc_b_menu_2nd_on", menu),
        ("UL_dlc_b_menu_1st_notyet", notyet)]


def main():
    os.makedirs(PREVIEW, exist_ok=True)
    if CHECK:
        if not os.path.exists(DST):
            raise SystemExit("THIẾU " + DST)
        c = Container(DST)
        bad = 0
        for n, _fn in JOBS:
            s = c.sprite(n)
            if s.vertex_count() != 4:
                print("FAIL %s: mesh %d đỉnh" % (n, s.vertex_count()))
                bad += 1
            r = np.array(render_check(DST, n).convert("RGBA"))
            o = np.array(s.crop())
            if r.shape != o.shape or not np.array_equal(r, o):
                print("FAIL %s: render qua mesh khác ô atlas" % n)
                bad += 1
            if ink_mask(o.astype(int)).sum() == 0:
                print("FAIL %s: không còn mực" % n)
                bad += 1
        if bad:
            raise SystemExit("%d lỗi" % bad)
        print("PASS %d sprite" % len(JOBS))
        return

    work = os.path.join(PREVIEW, "_work_ui01")
    shutil.copy(SRC, work)
    c = Container(work)
    report, pairs = [], []
    for n, fn in JOBS:
        s = c.sprite(n)
        before = s.crop()
        after = fn(before.copy(), n, report)
        s.paste(after)
        s.full_rect_mesh()
        pairs.append((n, before, after))
        after.save(os.path.join(PREVIEW, n + ".png"))
    for line in report:
        print("  " + line)

    rows = []
    for n, b, aft in pairs:
        pair = Image.new("RGBA", (b.width, b.height * 2 + 8), (60, 60, 60, 255))
        pair.alpha_composite(b, (0, 0))
        pair.alpha_composite(aft, (0, b.height + 8))
        rows.append((n, pair))
    W = max(p.width for _, p in rows)
    H = sum(p.height + 22 for _, p in rows)
    sheet = Image.new("RGB", (W, H), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    y = 0
    for n, p in rows:
        d.text((4, y + 4), n, fill=(255, 255, 0))
        sheet.paste(p.convert("RGB"), (0, y + 20))
        y += p.height + 22
    pv = os.path.join(PREVIEW, "ui01.png")
    sheet.save(pv)
    print("xem trước -> %s" % pv)

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    if os.path.exists(DST):
        os.makedirs(BACKUP, exist_ok=True)
        shutil.copy2(DST, os.path.join(BACKUP, "ui01.predlctop"))
    n = c.save(work + ".out", packer="lz4")
    shutil.move(work + ".out", DST)
    print("đã ghi %s (%d B, gốc %d B)" % (DST, n, os.path.getsize(SRC)))


if __name__ == "__main__":
    main()
