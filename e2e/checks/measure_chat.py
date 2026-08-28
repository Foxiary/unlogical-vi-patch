# -*- coding: utf-8 -*-
"""Đo bề rộng từng dòng chat Genebark trên ảnh chụp máy thật, so với khung 1210.

Dùng sau khi đưa game tới màn CHAT của app Genebark:

    python e2e\\checks\\measure_chat.py <anh.png>
    python e2e\\checks\\measure_chat.py            # tự lấy ảnh Ryujinx mới nhất

Cách đo, và vì sao không đo thẳng bằng pixel màn hình:

1. **Tỉ lệ canvas→màn hình lấy từ vạch `UnderLine`.** Panel Genebark không chiếm hết
   canvas: vạch ngăn giữa các tin nhắn rộng đúng **1388** canvas px theo prefab
   (`GenebarkChatContentItem/Message_TMP/UnderLine`), đo được trên ảnh 14/08 là 1283 px
   ⇒ tỉ lệ 0,9243. Tool tự đo lại vạch trên chính ảnh bạn đưa, không hardcode.
2. Rồi quy mọi bề rộng mực về canvas px để so với `LIMIT = 1210` — cùng đơn vị mà
   `tools\\fix_chat_wrap.py` dùng.

Lưu ý bề rộng **mực** luôn nhỏ hơn bề rộng **advance** một chút (side bearing hai đầu
và advance của ký tự cuối không có mực). Trên 10 dòng của ảnh 14/08, model advance của
`fix_chat_wrap` cao hơn mực trung bình 1,0% — nên coi hai số lệch dưới ~2% là khớp.
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PIL import Image   # noqa: E402

PREFAB_UNDERLINE = 1388.0
LIMIT = 1210.0
SHOT_DIR = os.path.join(os.environ.get("APPDATA", ""), "Ryujinx", "screenshots")


def newest_shot():
    if not os.path.isdir(SHOT_DIR):
        raise SystemExit("không thấy %s" % SHOT_DIR)
    pngs = [os.path.join(SHOT_DIR, f) for f in os.listdir(SHOT_DIR) if f.lower().endswith(".png")]
    if not pngs:
        raise SystemExit("chưa có ảnh nào trong %s" % SHOT_DIR)
    return max(pngs, key=os.path.getmtime)


def separators(px, W, H, th=90, minlen=900):
    """Các hàng là vạch ngăn giữa tin nhắn: một dải sáng dài liên tục."""
    out = []
    for y in range(int(H * 0.15), int(H * 0.90)):
        run = best = 0
        x0 = b0 = None
        for x in range(int(W * 0.15), int(W * 0.90)):
            if px[x, y] > th:
                if run == 0:
                    x0 = x
                run += 1
                if run > best:
                    best, b0 = run, x0
            else:
                run = 0
        if best > minlen:
            if out and y - out[-1][0] < 4:
                continue
            out.append((y, best, b0))
    return out


def ink_lines(px, x0, x1, y0, y1, th=140, gap=6):
    """Các dải mực theo hàng trong vùng chữ -> (y0, y1, xmin, xmax)."""
    rows = []
    for y in range(y0, y1):
        xs = [x for x in range(x0, x1) if px[x, y] > th]
        rows.append((y, xs))
    out, cur, blank = [], None, 0
    for y, xs in rows:
        if len(xs) > 2:
            blank = 0
            a, b = min(xs), max(xs)
            cur = [y, y, a, b] if cur is None else [cur[0], y, min(cur[2], a), max(cur[3], b)]
        else:
            blank += 1
            if cur and blank >= gap:
                if cur[1] - cur[0] >= 10:
                    out.append(tuple(cur))
                cur = None
    if cur and cur[1] - cur[0] >= 10:
        out.append(tuple(cur))
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else newest_shot()
    im = Image.open(path).convert("L")
    W, H = im.size
    px = im.load()
    print("ảnh   : %s  (%dx%d)" % (path, W, H))

    seps = separators(px, W, H)
    if not seps:
        raise SystemExit("không thấy vạch ngăn nào — ảnh này có phải màn CHAT Genebark không?")
    width_px = max(s[1] for s in seps)
    scale = width_px / PREFAB_UNDERLINE
    left = min(s[2] for s in seps)
    print("vạch ngăn: %d vạch, dài nhất %d px, x bắt đầu %d" % (len(seps), width_px, left))
    print("tỉ lệ canvas→màn hình = %d / %.0f = %.4f" % (width_px, PREFAB_UNDERLINE, scale))
    print("giới hạn %.0f canvas px  ->  %.0f px trên ảnh này\n" % (LIMIT, LIMIT * scale))

    # vùng chữ: bên phải cột icon, bên trái mép phải vạch
    tx0 = left + int(120 * scale)
    tx1 = left + int(width_px * 0.98)
    lines = ink_lines(px, tx0, tx1, int(H * 0.08), int(H * 0.88))
    lim_screen = LIMIT * scale
    print("%-4s %-16s %10s %10s  %s" % ("#", "y", "rộng ảnh", "-> canvas", "so với 1210"))
    over = 0
    for i, (y0, y1, a, b) in enumerate(lines, 1):
        w = b - a + 1
        cw = w / scale
        flag = "OK" if w <= lim_screen else "VƯỢT +%.0f" % (cw - LIMIT)
        if w > lim_screen:
            over += 1
        print("%-4d %-16s %10d %10.0f  %s" % (i, "%d..%d" % (y0, y1), w, cw, flag))
    print("\n%d dòng đo được, %d dòng vượt %0.f canvas px" % (len(lines), over, LIMIT))
    print("Dòng vượt là bình thường NẾU đó là một mệnh đề liền — `fix_chat_wrap.py` cố ý")
    print("để TMP tự ngắt những dòng đó (chạy `--check` để biết còn dòng nào cắt được mà vượt).")


main()
