# -*- coding: utf-8 -*-
"""Ô tóm tắt của thẻ SAVE/LOAD: cắt chữ thừa thay vì cho tràn ra ngoài khung.

Bảng chi tiết bên trái màn SAVE (`level19`, `Load/Normal/SaveDataDetail`) hiện
`Title` rồi tới **đoạn thoại tại điểm lưu** — chính là `m_saveText` trong file
save, tức nguyên câu thoại đang hiện lúc bấm save.

```
SaveDataDetail        rect 828 x 364
  Text (TMP)  pid 193 stretch, sizeDelta (-90,-200), pos (5,20)  ->  738 x 164
                      margin (6.5, 24, 0, 0)  ->  731,5 x 140 dùng được
                      cỡ 27, charSpacing 8.4, lineSpacing -39, wrap = Normal
                      m_overflowMode = 0 (Overflow)  <- chỗ hỏng
```

Chuỗi mẫu của bản gốc là **3 dòng × 24 chữ toàn rộng**, đúng bằng chỗ trống:

    pitch      = 27 × (116/58 + (−39)/100)                = 43,47 px
    cao 3 dòng = 2 × 43,47 + 27 × (51,04 + 6,96)/58        = 113,9 ≤ 140  ✓
    cao 4 dòng = 3 × 43,47 + 27                            = 157,4 >  140  ✗

`m_overflowMode = 0` nghĩa là TMP **vẫn vẽ** dòng thứ tư, chỉ là vẽ ra ngoài ô —
nó rơi thẳng xuống hàng `Date / Time / Playtime` (ảnh `_2026-09-02_00-51-50.png`,
save No.039). Tiếng Nhật không bao giờ chạm vào chuyện này vì câu thoại đã ngắt
sẵn cho khung ADV; tiếng Việt dài hơn, và ô này chỉ rộng 731,5 px trong khi ô ADV
rộng 1280 px, nên mỗi dòng cứng của kịch bản thường tách làm hai ở đây.

Đo trên `ScenarioData` (mô hình `adv_layout` với công thức đúng
`adv·fs/point + cs·fs/100`): **5.561 / 39.574 câu thoại (14,1%)** cần hơn 3 dòng
trong ô này — tệ nhất 8 dòng.

Sửa: đổi `m_overflowMode` sang **Ellipsis (1)** — TMP cắt đúng ở mép ô và đặt dấu
lửng vào cuối dòng cuối cùng còn thấy được. Không đụng cỡ chữ: auto-size sẽ cho
mỗi save một cỡ khác nhau, mà yêu cầu là cắt chứ không phải thu nhỏ.

**Ellipsis chỉ dùng được cùng `fix_ellipsis_glyph.py` — chạy cái đó trước.** TMP
luôn lấy `…` U+2026 làm dấu cắt và không cho đổi ký tự ở mức component; trong font
Nhật `FOT-NewRodinProN-DB` glyph đó có **ba chấm nằm giữa dòng**, nên lượt đầu
(02/09/2026) chữ cắt ra lơ lửng giữa hàng, sai kiểu chữ Việt. Ký tự thì cố định
nhưng **glyph thì không**: font là Dynamic, rasterize lúc chạy từ TTF trong romfs,
nên `fix_ellipsis_glyph.py` hạ ba chấm xuống chân chữ. Không chạy bản vá glyph thì
dùng `--truncate` (cắt trơn, không dấu) — cả hai chỉ khác nhau 1 byte.

**`level19` không nhúng type tree** nên không được `env.file.save()` (UnityPy sẽ
ghi rỗng phần lớn object). Script mượn `nodes` TMP của bundle `ui_jp`, serialize
lại **một** object rồi ghi đè đúng dải byte của nó trong file:

- serialize lại y nguyên cây đã đọc phải ra **đúng từng byte** như cũ (chốt 1),
- bản có sửa phải **cùng độ dài** và chỉ lệch **1 byte** (chốt 2),
- dải byte cũ phải khớp và **duy nhất** trong file (chốt 3).

    python tools\\fix_save_summary_clip.py             # chạy thử
    python tools\\fix_save_summary_clip.py --check     # đang ở chế độ nào
    python tools\\fix_save_summary_clip.py --stats     # đo lại tỉ lệ tràn
    python tools\\fix_save_summary_clip.py --apply [--truncate]
"""
import io
import os
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402

LEVEL = os.path.join(ROOT, "romfs", "Data", "level19")
UI_JP = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
SCENARIO = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "level19.presaveclip")

APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv
STATS = "--stats" in sys.argv
MODE = 3 if "--truncate" in sys.argv else 1          # 1 Ellipsis (mặc định), 3 Truncate
MODES = {0: "Overflow", 1: "Ellipsis", 2: "Masking", 3: "Truncate"}

TEXT_PID = 193          # TextMeshProUGUI trên GameObject 13 ("Text (TMP)")
GO_PID = 13

# hình học của chính component, để in ra và để --stats đo
BOX_W, BOX_H = 738.0, 164.0
MARGIN_L, MARGIN_T = 6.5, 24.0
FONT_SIZE, CHAR_SPACING, LINE_SPACING = 27.0, 8.4, -39.0
POINT, LINE_H, ASC, DESC = 58.0, 116.0, 51.04, -6.96


def tmp_nodes():
    """`level19` không nhúng type tree — mượn của một TMP trong bundle ui_jp."""
    env = UnityPy.load(UI_JP)
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            tt = o.read_typetree()
        except Exception:
            continue
        if isinstance(tt, dict) and "m_enableAutoSizing" in tt:
            return o.serialized_type.nodes
    raise SystemExit("không tìm được type tree của TMP trong " + UI_JP)


def geometry():
    usable_w = BOX_W - MARGIN_L
    usable_h = BOX_H - MARGIN_T
    pitch = FONT_SIZE * (LINE_H / POINT + LINE_SPACING / 100.0)
    fit = 0
    while (fit) * pitch + FONT_SIZE * (ASC - DESC) / POINT <= usable_h:
        fit += 1
    print("ô chữ %.0f x %.0f, margin (%.1f, %.0f) -> dùng được %.1f x %.0f px"
          % (BOX_W, BOX_H, MARGIN_L, MARGIN_T, usable_w, usable_h))
    print("cỡ %.0f, pitch %.2f px -> vừa **%d dòng** (dòng thứ %d cần %.1f px)"
          % (FONT_SIZE, pitch, fit, fit + 1,
             fit * pitch + FONT_SIZE * (ASC - DESC) / POINT))
    return usable_w, fit


def stats(usable_w, fit):
    """Bao nhiêu câu thoại cần hơn `fit` dòng trong ô này."""
    import json
    from collections import Counter
    import adv_layout as A
    A.CHAR_SPACING = CHAR_SPACING * POINT / 100.0    # mô hình đúng: cs*fs/100

    env = UnityPy.load(SCENARIO)
    data = None
    for o in env.objects:
        if o.type.name == "TextAsset":
            d = o.read()
            if d.m_Name == "ScenarioData":
                data = json.loads(bytes(d.m_Script.encode("utf-8", "surrogateescape"))
                                  .decode("utf-8-sig", "replace"))
                break
    if data is None:
        raise SystemExit("không thấy ScenarioData")

    cnt, tot = Counter(), 0
    for e in data["target"]:
        for t in (e.get("text") or []):
            if not isinstance(t, str) or not t.strip():
                continue
            tot += 1
            cnt[sum(max(1, len(A.wrap(h, FONT_SIZE, limit=usable_w)))
                    for h in t.split("\n"))] += 1
    over = sum(v for k, v in cnt.items() if k > fit)
    print("\n%d câu thoại trong ScenarioData:" % tot)
    for k in sorted(cnt):
        print("   %d dòng %7d  (%4.1f%%)%s" % (k, cnt[k], 100.0 * cnt[k] / tot,
                                               "   <- bị cắt" if k > fit else ""))
    print("   quá %d dòng: %d (%.1f%%)" % (fit, over, 100.0 * over / tot))


def main():
    nodes = tmp_nodes()
    env = UnityPy.load(LEVEL)
    obj = next((o for o in env.objects if o.path_id == TEXT_PID), None)
    if obj is None or obj.type.name != "MonoBehaviour":
        raise SystemExit("không thấy MonoBehaviour pid %d trong level19" % TEXT_PID)
    tt = obj.read_typetree(nodes=nodes)
    if tt["m_GameObject"]["m_PathID"] != GO_PID:
        raise SystemExit("pid %d không nằm trên GameObject %d" % (TEXT_PID, GO_PID))

    cur = tt["m_overflowMode"]
    print("%s  pid %d (SaveDataDetail/Text (TMP))" % (os.path.relpath(LEVEL, ROOT), TEXT_PID))
    print("   m_overflowMode = %d (%s), wrap = %d, cỡ = %s, auto-size = %d"
          % (cur, MODES.get(cur, "?"), tt["m_TextWrappingMode"], tt["m_fontSize"],
             tt["m_enableAutoSizing"]))
    usable_w, fit = geometry()

    if CHECK:
        if cur == 0:
            raise SystemExit("m_overflowMode = 0 (Overflow) — chữ tóm tắt vẫn tràn ra "
                             "ngoài ô, chạy lại với --apply")
        print("OK — chữ thừa bị cắt (%s)" % MODES.get(cur, cur))
        return
    if STATS:
        stats(usable_w, fit)
    if cur == MODE:
        print("\nđã ở %s, không có gì để làm" % MODES[MODE])
        return
    if cur != 0 and not APPLY:
        print("\n!! đang là %s, sẽ đổi sang %s" % (MODES.get(cur, cur), MODES[MODE]))
    print("\nm_overflowMode  %d (%s)  ->  %d (%s)"
          % (cur, MODES.get(cur, "?"), MODE, MODES[MODE]))

    # --- dựng byte mới cho ĐÚNG một object, không đụng phần còn lại của file ---
    raw_old = obj.get_raw_data()
    if bytes(obj.save_typetree(dict(tt), nodes)) != raw_old:
        raise SystemExit("serialize lại không ra đúng byte cũ — type tree mượn không khớp")
    tt2 = dict(tt)
    tt2["m_overflowMode"] = MODE
    raw_new = bytes(obj.save_typetree(tt2, nodes))
    if len(raw_new) != len(raw_old):
        raise SystemExit("độ dài object đổi %d -> %d" % (len(raw_old), len(raw_new)))
    diff = [i for i in range(len(raw_old)) if raw_old[i] != raw_new[i]]
    if len(diff) != 1:
        raise SystemExit("lệch %d byte, chờ đúng 1: %s" % (len(diff), diff[:8]))
    print("   1 byte đổi ở offset %d trong object (%d byte)" % (diff[0], len(raw_old)))

    blob = bytearray(open(LEVEL, "rb").read())
    n0 = len(blob)
    start = obj.byte_start
    if bytes(blob[start:start + len(raw_old)]) != raw_old:
        raise SystemExit("byte_start %d không khớp dữ liệu object" % start)
    if bytes(blob).count(raw_old) != 1:
        raise SystemExit("dải byte của object khớp %d chỗ trong file"
                         % bytes(blob).count(raw_old))
    blob[start:start + len(raw_new)] = raw_new
    if len(blob) != n0:
        raise SystemExit("kích thước file đổi")
    print("   file offset %d..%d" % (start, start + len(raw_new)))

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(LEVEL, BACKUP)
        print("\nbackup ->", os.path.relpath(BACKUP, ROOT))
    else:
        print("\nbackup đã có ->", os.path.relpath(BACKUP, ROOT))
    open(LEVEL, "wb").write(bytes(blob))
    print("đã ghi %s (%d byte)" % (os.path.relpath(LEVEL, ROOT), os.path.getsize(LEVEL)))

    # --- đọc lại từ đĩa ---------------------------------------------------------
    env2 = UnityPy.load(LEVEL)
    o2 = next(o for o in env2.objects if o.path_id == TEXT_PID)
    t2 = o2.read_typetree(nodes=nodes)
    if t2["m_overflowMode"] != MODE:
        raise SystemExit("đọc lại ra %r" % t2["m_overflowMode"])
    print("  đọc lại: m_overflowMode = %d (%s), cỡ %s, wrap %d — các trường khác giữ nguyên: %s"
          % (t2["m_overflowMode"], MODES[MODE], t2["m_fontSize"], t2["m_TextWrappingMode"],
             all(t2[k] == tt[k] for k in tt if k != "m_overflowMode")))
    print("  số object đọc được: %d (trước khi vá %d)" % (len(env2.objects), len(env.objects)))


main()
