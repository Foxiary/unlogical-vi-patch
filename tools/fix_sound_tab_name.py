# -*- coding: utf-8 -*-
"""Dịch tên nhân vật ở dòng INFO đáy tab SOUND (`光希's volume settings`).

Tab SOUND có 21 thanh trượt. Nhãn thanh trượt lấy từ `ConfigVolumeData.label`
(dữ liệu — đã Latin hoá từ lâu), nhưng **dòng INFO ở đáy màn hình** thì không:
`Config.InfoTextInit()` (RVA 0x19BC090) dựng nó bằng

    String.Concat(<literal tên tiếng Nhật>, GetSystemText(76))

16 lần, mỗi lần một tên. `SystemTextID 76` đã dịch rồi, nên màn hình ra
`光希's volume settings` — nửa Anh nửa Nhật. Muốn chữa phải sửa literal.

## Chỉ vá được 1 trong 16

Trình biên dịch C# gộp chuỗi giống nhau thành **một** mục literal, nên literal
`蛍` mà `InfoTextInit` dùng cũng chính là literal mà `ADVManager` dùng. Tra xref
trên bản dump Il2CppDumper:

    恭介   -> Config$$InfoTextInit                                    ← chỉ một chỗ
    蛍     -> + ADVManager$$CutInPositionOffset, $$DigitalAnimationIdAdjust, Config$$.cctor
    栞     -> nt
    光希   -> nt

Hai hàm ADVManager là `switch` trên chuỗi: chúng nhận `chara` **lấy thẳng từ tag
lệnh trong kịch bản** (`[蛍 出 1111 M すまし slot=0]`) rồi so bằng
`String.op_Equality`. Tag lệnh thì không bao giờ được dịch (quy tắc `[...]` trong
CLAUDE.md), nên vế bên kia mãi mãi là tiếng Nhật. Đổi literal = phép so trượt.

`恭介` an toàn vì nhân vật đó **không có sprite riêng** — anh ta dùng sprite của
`伊槻` (cải trang). Trong ScenarioData: `[恭介 …]` xuất hiện **0 lần**.

## Bài học 涼乃 — vì sao script này tự quét kịch bản

Một bản trước đổi literal #15053 `涼乃` → `Suzuno` (họ của nhân vật chính, hiện
trên nameplate). Nhưng `涼乃` cũng là khoá sprite của chính cô: ScenarioData còn
**495** tag `[涼乃 …]`. Từ đó `CutInPositionOffset` và `DigitalAnimationIdAdjust`
không còn nhận ra nhân vật chính — hỏng lặng lẽ, không phép kiểm nào bắt được.
Mọi bản vá tên khác đều chọn biến thể có `・` (`戒・`, `藍・`, `雅火・`…) vốn 0 tag,
nên vô hại; `涼乃` là ngoại lệ duy nhất.

Nên phép chốt bắt buộc ở đây: **literal chỉ được đổi khi ScenarioData không còn
tag lệnh nào lấy nó làm khoá.**

## Chỗ ghi

`恭介` chiếm 6 byte, `Kyosuke` cần 7 — không ghi đè tại chỗ được, và ô kề nó
(`#15029 戒`) xếp khít, 0 byte dư. Nhưng bảng literal là cặp `(length, dataIndex)`
nên chuỗi mới ghi ở **đâu cũng được**, miễn không ai đang dùng vùng đó. Khối dữ
liệu có 33 byte mồ côi trong 8 khoảng; script tự dựng lại bản đồ byte từ cả
15.224 mục rồi cấp phát từ khoảng vừa nhất. Ô 6 byte cũ được trả về \\x00.

Kích thước file không đổi, không section nào dịch, header không đụng tới.

    python tools\\fix_sound_tab_name.py            # chạy thử / --check
    python tools\\fix_sound_tab_name.py --apply
"""
import io
import os
import re
import shutil
import struct
import sys

if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

META = os.path.join(ROOT, "romfs", "Data", "Managed", "Metadata", "global-metadata.dat")
SCENARIO = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "global-metadata.dat.presoundnames")
SANITY = 0xFAB11BAF
APPLY = "--apply" in sys.argv

# (index literal, chuỗi phải thấy trước khi vá, chuỗi mới)
PLAN = [
    (15028, "恭介", "Kyosuke"),
    # Nhãn mục lựa chọn ở BACKLOG. `fix_backlog_select_label.py` đã vá prefab
    # `Log_Base_SELECT` trong ui_jp, nhưng `BackLog$$TextUpdate` GHI ĐÈ ô đó bằng
    # literal này lúc chạy, nên máy thật vẫn hiện tiếng Nhật. Đổi được vì cả bên
    # ghi (ADVManager$$SetSelectButton*, $$SelectBackLogAdd) lẫn bên đọc
    # (BackLog$$TextUpdate, BackLog_NovelScroll$$TextUpdate, BackLog$$PlayVoice)
    # đều dùng CHUNG literal này — đổi một phát là cả hai vế cùng đổi.
    (15084, "選択肢", "Choice"),
]

# Không vá — literal dùng chung với switch chuỗi của ADVManager, mà vế bên kia
# là tag lệnh tiếng Nhật trong kịch bản. Xem docstring.
REFUSED = [
    (15075, "蛍", "Hotaru", "1.354 tag [蛍 …]"),
    (15046, "栞", "Shiori", "1.570 tag [栞 …]"),
    (14989, "光希", "Mitsuki", "774 tag [光希 …]"),
]


def header(blob):
    sanity, version = struct.unpack_from("<Ii", blob, 0)
    if sanity != SANITY:
        raise SystemExit("không phải global-metadata (sanity %08X)" % sanity)
    lit_off, lit_size, data_off, data_size = struct.unpack_from("<IIII", blob, 8)
    return version, lit_off, lit_size, data_off, data_size


def entry(blob, lit_off, i):
    return struct.unpack_from("<II", blob, lit_off + i * 8)      # (length, dataIndex)


def scenario_data():
    """Chuỗi ScenarioData của build — nguồn duy nhất của tag lệnh đang sống."""
    import UnityPy
    env = UnityPy.load(SCENARIO)
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            if data.m_Name == "ScenarioData":
                return data.m_Script
    raise SystemExit("không thấy ScenarioData trong %s" % SCENARIO)


def tag_uses(text, name):
    """Số tag lệnh lấy `name` làm khoá: '[<name> ' hoặc '[<name>]'."""
    return len(re.findall(r"\[" + re.escape(name) + r"(?=[ \]])", text))


def free_map(blob, lit_off, lit_size, data_off, data_size):
    """(danh sách khoảng trống, tập byte có chủ) — dựng từ CẢ 15.224 mục."""
    owned = bytearray(data_size)
    for i in range(lit_size // 8):
        ln, di = entry(blob, lit_off, i)
        if di + ln > data_size:
            raise SystemExit("literal #%d trỏ ra ngoài khối dữ liệu" % i)
        for k in range(di, di + ln):
            owned[k] = 1
    gaps, k = [], 0
    while k < data_size:
        if owned[k]:
            k += 1
            continue
        j = k
        while j < data_size and not owned[j]:
            j += 1
        gaps.append((k, j - k))
        k = j
    return gaps, owned


def main():
    blob = bytearray(open(META, "rb").read())
    version, lit_off, lit_size, data_off, data_size = header(blob)
    print("%s  %d byte, metadata v%d, %d literal"
          % (os.path.relpath(META, ROOT), len(blob), version, lit_size // 8))

    # --- chốt 1: literal đang đúng như mong đợi -------------------------------
    cur = {}
    for idx, old, _new in PLAN:
        ln, di = entry(blob, lit_off, idx)
        got = bytes(blob[data_off + di:data_off + di + ln]).decode("utf-8")
        if got != old:
            raise SystemExit("literal #%d là %r, không phải %r — đã vá rồi?" % (idx, got, old))
        cur[idx] = (ln, di)
        print("   #%-6d di=%-8d len=%-3d %r" % (idx, di, ln, got))

    # --- chốt 2: không tag lệnh nào còn dùng chuỗi này làm khoá ---------------
    print("\nquét tag lệnh trong ScenarioData (bài học 涼乃)…")
    text = scenario_data()
    for idx, old, _new in PLAN:
        n = tag_uses(text, old)
        print("   [%s …]  %d tag" % (old, n))
        if n:
            raise SystemExit(
                "%r còn %d tag lệnh dùng làm khoá — đổi literal sẽ làm trượt phép so "
                "trong ADVManager. Không vá." % (old, n))
    for idx, old, new, why in REFUSED:
        n = tag_uses(text, old)
        print("   [%s …]  %d tag   -> KHÔNG vá %r (%s)" % (old, n, new, why))

    # --- chốt 3: tìm chỗ trống -------------------------------------------------
    gaps, owned = free_map(blob, lit_off, lit_size, data_off, data_size)
    print("\nkhoảng trống trong khối dữ liệu: %d byte / %d khoảng"
          % (sum(n for _o, n in gaps), len(gaps)))
    layout = {}
    for idx, _old, new in PLAN:
        need = len(new.encode("utf-8"))
        ln, di = cur[idx]
        if need <= ln:                       # vừa ô cũ: ghi tại chỗ, khỏi tiêu chỗ trống
            layout[idx] = di
            print("   %r %d byte -> @%d tại chỗ  (ô cũ %d byte, trả lại %d)"
                  % (new, need, di, ln, ln - need))
            continue
        fit = sorted((n, o) for o, n in gaps if n >= need)
        if not fit:
            raise SystemExit("không khoảng trống nào chứa nổi %r (%d byte)" % (new, need))
        n, off = fit[0]
        gaps = [(o, m) for o, m in gaps if o != off] + ([(off + need, n - need)] if n > need else [])
        layout[idx] = off
        print("   %r %d byte -> @%d  (khoảng %d byte, thừa %d)" % (new, need, off, n, n - need))

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    # --- backup ---------------------------------------------------------------
    bak = BACKUP
    if os.path.exists(bak) and open(bak, "rb").read() != bytes(blob):
        k = 2
        while os.path.exists("%s%d" % (BACKUP, k)):
            k += 1
        bak = "%s%d" % (BACKUP, k)
    if not os.path.exists(bak):
        shutil.copy2(META, bak)
        print("\nbackup ->", os.path.relpath(bak, ROOT))
    else:
        print("\nbackup đã có và trùng khớp ->", os.path.relpath(bak, ROOT))
    before = bytes(blob)

    # --- ghi -------------------------------------------------------------------
    touched = set()
    for idx, _old, new in PLAN:
        data = new.encode("utf-8")
        off = layout[idx]
        ln, di = cur[idx]
        blob[data_off + di:data_off + di + ln] = b"\x00" * ln            # trả ô cũ
        blob[data_off + off:data_off + off + len(data)] = data
        struct.pack_into("<II", blob, lit_off + idx * 8, len(data), off)
        touched.update(range(data_off + di, data_off + di + ln))
        touched.update(range(data_off + off, data_off + off + len(data)))
        touched.update(range(lit_off + idx * 8, lit_off + idx * 8 + 8))

    if len(blob) != len(before):
        raise SystemExit("kích thước file đổi — dừng")
    open(META, "wb").write(bytes(blob))
    print("đã ghi", os.path.relpath(META, ROOT), len(blob), "byte")

    # --- đọc lại từ đĩa ---------------------------------------------------------
    back = open(META, "rb").read()
    _, lo2, ls2, do2, ds2 = header(back)
    for idx, _old, new in PLAN:
        ln, di = entry(back, lo2, idx)
        got = back[do2 + di:do2 + di + ln].decode("utf-8")
        if got != new:
            raise SystemExit("đọc lại #%d ra %r, chờ %r" % (idx, got, new))
    print("  đọc lại: %d literal đúng như dự kiến" % len(PLAN))

    bad = 0
    for i in range(ls2 // 8):
        ln, di = entry(back, lo2, i)
        if di + ln > ds2:
            bad += 1
            continue
        try:
            back[do2 + di:do2 + di + ln].decode("utf-8")
        except UnicodeDecodeError:
            bad += 1
    print("  %d literal, %d mục hỏng (tràn khối hoặc không giải mã được)" % (ls2 // 8, bad))
    if bad:
        raise SystemExit("bảng literal hỏng — khôi phục từ backup")

    changed = [k for k in range(len(before)) if before[k] != back[k]]
    stray = [k for k in changed if k not in touched]
    print("  %d byte đổi, %d ngoài dự kiến" % (len(changed), len(stray)))
    if stray:
        raise SystemExit("có byte đổi ngoài dự kiến: %s" % stray[:8])


if __name__ == "__main__":
    main()
