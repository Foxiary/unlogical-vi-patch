# -*- coding: utf-8 -*-
"""Dịch nhãn `マップ` của điểm lưu tại màn MAP (thẻ SAVE/LOAD, BACKLOG).

Thẻ SAVE hiện hai dòng: `Title` lấy từ `ChapterData.title` (đã dịch) và dưới nó
là **nhãn của điểm lưu**. Lưu ngay một lựa chọn thường thì dòng đó là `選択肢`
(đã đổi thành `Choice`, xem `fix_sound_tab_name.py`); lưu ở **màn MAP** —
kịch bản dùng lệnh `[select_map]` thay cho `[select]` — thì dòng đó là `マップ`
và vẫn còn tiếng Nhật.

Ảnh chụp máy thật 02/09/2026, save No.038 (`04_03_03`, `*SOU-03-50`,
`m_loadline=410` = đúng dòng `[select_map]`):

    Title  Ký ức đắng không nuốt trôi
           マップ                        ← đây

## Vì sao chắc chắn là literal IL2CPP

Chuỗi `マップ` **không có trong bất kỳ dữ liệu nào của game**: quét cả cây
`D:\\Downloads\\UNLOGICAL_v2\\Data` (2,9 GB, gồm `globalgamemanagers` nên loại
luôn khả năng tên scene) và cả bundle đã giải nén — `ui_jp`, `json`,
`sharedassets*`, `level*` đều **0**. Chỉ còn ba chỗ có nó, không chỗ nào hiện ra
màn hình:

| chỗ | nội dung | có hiện không |
|---|---|---|
| `resources.assets` | 28 lần, trong bản nháp kịch bản cũ (asset chết) | không |
| `scenario01` | 111 lần, **toàn bộ nằm trong chú thích** `;//マップパート` của `scriptText_Line` | không |
| `sprite01` | 1 lần, trong đường dẫn thư mục `12.マップパート/…` | không |
| `global-metadata.dat` | literal **#14912**, 9 byte | **có** |

Đúng bài học đã ghi hai lần trong README (nhãn route SAVE/LOAD, nhãn `選択肢`
của BACKLOG): dữ liệu đã dịch mà màn hình vẫn ra tiếng Nhật thì **tìm literal**.

## Vì sao đổi được

Chốt bắt buộc của mọi bản vá literal (bài học `涼乃`): literal chỉ được đổi khi
**không dữ liệu nào so sánh với nó**, vì vế dữ liệu là tag lệnh tiếng Nhật, vĩnh
viễn không dịch. Ở đây ScenarioData có **0** tag `[マップ …]` và **0** chuỗi hiển
thị (`text` / `talkName` / `selText`) chứa `マップ` — nên cả bên ghi lẫn bên đọc
đều dùng chung một literal, đổi một phát là cả hai cùng đổi.

`マップ` 9 byte, `Map` 3 byte — ghi đè tại chỗ, 6 byte dư điền `\\x00` và hạ
`length` trong bảng. Kích thước file không đổi, không offset nào dịch.

    python tools\\fix_map_select_label.py            # chạy thử
    python tools\\fix_map_select_label.py --check    # đã vá chưa
    python tools\\fix_map_select_label.py --apply
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
BACKUP = os.path.join(ROOT, "_backup", "global-metadata.dat.premaplabel")
SANITY = 0xFAB11BAF

APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

INDEX, OLD, NEW = 14912, "マップ", "Map"


def header(blob):
    sanity, version = struct.unpack_from("<Ii", blob, 0)
    if sanity != SANITY:
        raise SystemExit("không phải global-metadata (sanity %08X)" % sanity)
    lit_off, lit_size, data_off, data_size = struct.unpack_from("<IIII", blob, 8)
    return version, lit_off, lit_size, data_off, data_size


def entry(blob, lit_off, i):
    return struct.unpack_from("<II", blob, lit_off + i * 8)      # (length, dataIndex)


def literal(blob, lit_off, data_off, i):
    ln, di = entry(blob, lit_off, i)
    return blob[data_off + di:data_off + di + ln], ln, di


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


def main():
    blob = bytearray(open(META, "rb").read())
    version, lit_off, lit_size, data_off, data_size = header(blob)
    print("%s  %d byte, metadata v%d, %d literal"
          % (os.path.relpath(META, ROOT), len(blob), version, lit_size // 8))

    got, ln, di = literal(blob, lit_off, data_off, INDEX)

    if CHECK:
        ok = got == NEW.encode("utf-8")
        print("   #%-6d di=%-8d len=%-3d %r" % (INDEX, di, ln, got.decode("utf-8", "replace")))
        if not ok:
            raise SystemExit("literal #%d không phải %r — nhãn điểm lưu MAP còn tiếng Nhật, "
                             "chạy lại với --apply" % (INDEX, NEW))
        print("OK — nhãn điểm lưu ở màn MAP là %r" % NEW)
        return

    if got != OLD.encode("utf-8"):
        raise SystemExit("literal #%d là %r, không phải %r — đã vá rồi?"
                         % (INDEX, got.decode("utf-8", "replace"), OLD))
    print("   #%-6d di=%-8d len=%-3d %r  ->  %r (%d byte)"
          % (INDEX, di, ln, OLD, NEW, len(NEW.encode("utf-8"))))

    # --- chốt 1: chỉ đúng MỘT literal mang chuỗi này --------------------------
    same = [i for i in range(lit_size // 8)
            if literal(blob, lit_off, data_off, i)[0] == OLD.encode("utf-8")]
    print("\nliteral trùng %r: %s" % (OLD, same))
    if same != [INDEX]:
        raise SystemExit("chuỗi %r nằm ở %d literal — đổi một cái là màn hình vẫn có thể "
                         "lấy cái kia" % (OLD, len(same)))

    # --- chốt 2: không dữ liệu nào so sánh với chuỗi này (bài học 涼乃) --------
    print("quét ScenarioData…")
    text = scenario_data()
    tags = len(re.findall(r"\[" + re.escape(OLD) + r"(?=[ \]])", text))
    print("   tag lệnh [%s …]      %d" % (OLD, tags))
    if tags:
        raise SystemExit("%r còn %d tag lệnh dùng làm khoá — đổi literal sẽ làm trượt phép so. "
                         "Không vá." % (OLD, tags))

    import json
    j = json.loads(bytes(text.encode("utf-8", "surrogateescape")).decode("utf-8-sig", "replace"))
    live = [(e.get("scenarioID"), fld, s)
            for e in j["target"] for fld in ("text", "talkName", "selText")
            for s in (e.get(fld) or []) if isinstance(s, str) and OLD in s]
    print("   chuỗi hiển thị chứa %r  %d" % (OLD, len(live)))
    if live:
        raise SystemExit("còn %d chuỗi hiển thị mang %r — dịch dữ liệu trước, đừng vá literal: %s"
                         % (len(live), OLD, live[:3]))
    maps = sum(e.get("scriptText", "").count("[select_map]") for e in j["target"])
    print("   lệnh [select_map]      %d  (bấy nhiêu điểm lưu sẽ đổi nhãn)" % maps)

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
    data = NEW.encode("utf-8")
    blob[data_off + di:data_off + di + ln] = b"\x00" * ln
    blob[data_off + di:data_off + di + len(data)] = data
    struct.pack_into("<II", blob, lit_off + INDEX * 8, len(data), di)
    touched = set(range(data_off + di, data_off + di + ln))
    touched.update(range(lit_off + INDEX * 8, lit_off + INDEX * 8 + 8))

    if len(blob) != len(before):
        raise SystemExit("kích thước file đổi — dừng")
    open(META, "wb").write(bytes(blob))
    print("đã ghi", os.path.relpath(META, ROOT), len(blob), "byte")

    # --- đọc lại từ đĩa ---------------------------------------------------------
    back = open(META, "rb").read()
    _, lo2, ls2, do2, ds2 = header(back)
    got2, ln2, di2 = literal(back, lo2, do2, INDEX)
    if got2 != data:
        raise SystemExit("đọc lại #%d ra %r, chờ %r" % (INDEX, got2, NEW))
    print("  đọc lại: #%d len=%d %r" % (INDEX, ln2, got2.decode("utf-8")))

    bad = 0
    for i in range(ls2 // 8):
        ln3, di3 = entry(back, lo2, i)
        if di3 + ln3 > ds2:
            bad += 1
            continue
        try:
            back[do2 + di3:do2 + di3 + ln3].decode("utf-8")
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
