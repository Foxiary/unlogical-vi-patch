# -*- coding: utf-8 -*-
"""Dịch hậu tố mùa của route EXTRA trên thẻ SAVE/LOAD (`雅火・夏`).

Bốn literal IL2CPP kề nhau, cộng dấu `・` đứng ngay trước, chiếm đúng **37 byte
liền mạch** và không literal nào khác chen vào:

```
#14953 di=373480 len= 3  '・'
#14954 di=373483 len=10  '・EXTRA\\n\\r'
#14955 di=373493 len= 8  '・夏\\n\\r'
#14956 di=373501 len= 8  '・春\\n\\r'
#14957 di=373509 len= 8  '・秋\\n\\r'
```

`metadata_term.py` vá **tại chỗ từng literal một**, nên nó bó tay ở đây: `・Xuân`
cần 10 byte trong ô 8 byte. Nhưng bảng literal là cặp `(length, dataIndex)` — cả
vùng 37 byte là của riêng năm cái này, nên **xếp lại toàn vùng** thì thoải mái:

```
373480  ・EXTRA\\n\\r   10      <- #14954, và #14953 trỏ vào 3 byte đầu
373490  ・Hè\\n\\r       8      <- #14955
373498  ・Xuân\\n\\r    10      <- #14956
373508  ・Thu\\n\\r      8      <- #14957
373516  \\x00            1      thừa
```

> **`・` (#14953) trỏ chồng lên 3 byte đầu của `・EXTRA\\n\\r`.** Literal chỉ là
> `(offset, length)`, chồng lấn khi ĐỌC là vô hại, và nội dung nó nhận vẫn đúng
> bằng `・` như cũ. Không có mẹo này thì thiếu đúng 2 byte.

Giữ nguyên dấu `・` để khớp với nhãn SECTION (`Miyabi・SECTION 1`, xem
`metadata_term.py` và mục cùng tên trong `tools/README.md`). `・EXTRA` vốn đã Latin
nên để nguyên.

Kích thước file không đổi, mọi byte ngoài vùng 37 và ngoài 5 mục bảng đều nguyên vẹn.

    python tools\\fix_extra_season_label.py            # chạy thử
    python tools\\fix_extra_season_label.py --apply
"""
import io
import os
import shutil
import struct
import sys

if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

META = os.path.join(ROOT, "romfs", "Data", "Managed", "Metadata", "global-metadata.dat")
BACKUP = os.path.join(ROOT, "_backup", "global-metadata.dat.preseason")
SANITY = 0xFAB11BAF
APPLY = "--apply" in sys.argv

# (index literal, chuỗi phải thấy trước khi vá, chuỗi mới)
PLAN = [
    (14953, "・",            "・"),            # giữ nguyên, chỉ dời chỗ (trỏ chồng)
    (14954, "・EXTRA\n\r",   "・EXTRA\n\r"),   # vốn đã Latin
    (14955, "・夏\n\r",       "・Hè\n\r"),
    (14956, "・春\n\r",       "・Xuân\n\r"),
    (14957, "・秋\n\r",       "・Thu\n\r"),
]
# #14953 không tự chiếm byte: nó mượn 3 byte đầu của #14954.
BORROWS = {14953: 14954}


def header(blob):
    sanity, version = struct.unpack_from("<Ii", blob, 0)
    if sanity != SANITY:
        raise SystemExit("không phải global-metadata (sanity %08X)" % sanity)
    lit_off, lit_size, data_off, data_size = struct.unpack_from("<IIII", blob, 8)
    return version, lit_off, lit_size, data_off, data_size


def entry(blob, lit_off, i):
    return struct.unpack_from("<II", blob, lit_off + i * 8)      # (length, dataIndex)


def main():
    blob = bytearray(open(META, "rb").read())
    version, lit_off, lit_size, data_off, data_size = header(blob)
    print("%s  %d byte, metadata v%d, %d literal"
          % (os.path.relpath(META, ROOT), len(blob), version, lit_size // 8))

    # --- chốt: vùng đúng như mong đợi và không ai khác dùng chung -------------
    cur = {}
    for idx, old, _new in PLAN:
        ln, di = entry(blob, lit_off, idx)
        got = bytes(blob[data_off + di:data_off + di + ln]).decode("utf-8")
        if got != old:
            raise SystemExit("literal #%d là %r, không phải %r — đã vá rồi?" % (idx, got, old))
        cur[idx] = (ln, di)
    lo = min(di for ln, di in cur.values())
    hi = max(di + ln for ln, di in cur.values())
    print("vùng dữ liệu %d..%d  (%d byte)" % (lo, hi, hi - lo))

    for i in range(lit_size // 8):
        if i in cur:
            continue
        ln, di = entry(blob, lit_off, i)
        if di < hi and di + ln > lo:
            raise SystemExit("literal #%d (%d..%d) chồng vào vùng — không dám xếp lại"
                             % (i, di, di + ln))
    print("không literal nào khác chồng vào vùng")

    # --- xếp lại --------------------------------------------------------------
    layout, pos = {}, lo
    for idx, _old, new in PLAN:
        if idx in BORROWS:
            continue
        data = new.encode("utf-8")
        layout[idx] = (pos, data)
        pos += len(data)
    for idx, host in BORROWS.items():
        new = dict((i, n) for i, _o, n in PLAN)[idx].encode("utf-8")
        host_pos, host_data = layout[host]
        if not host_data.startswith(new):
            raise SystemExit("#%d (%r) không phải tiền tố của #%d" % (idx, new, host))
        layout[idx] = (host_pos, new)
    used = pos - lo
    print("cần %d byte / có %d byte  (thừa %d)" % (used, hi - lo, hi - lo - used))
    if used > hi - lo:
        raise SystemExit("không đủ chỗ")

    for idx, _old, new in PLAN:
        p, data = layout[idx]
        print("   #%-6d di=%-8d len=%-3d %r" % (idx, p, len(data), new))

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(META, BACKUP)
        print("backup ->", os.path.relpath(BACKUP, ROOT))
    before = bytes(blob)

    blob[data_off + lo:data_off + hi] = b"\x00" * (hi - lo)
    for idx, _old, _new in PLAN:
        if idx in BORROWS:
            continue
        p, data = layout[idx]
        blob[data_off + p:data_off + p + len(data)] = data
    for idx, _old, _new in PLAN:
        p, data = layout[idx]
        struct.pack_into("<II", blob, lit_off + idx * 8, len(data), p)

    if len(blob) != len(before):
        raise SystemExit("kích thước file đổi — dừng")
    open(META, "wb").write(bytes(blob))
    print("đã ghi", os.path.relpath(META, ROOT), len(blob), "byte")

    # --- đọc lại từ đĩa --------------------------------------------------------
    back = open(META, "rb").read()
    _, lo2, ls2, do2, _ = header(back)
    for idx, _old, new in PLAN:
        ln, di = entry(back, lo2, idx)
        got = back[do2 + di:do2 + di + ln].decode("utf-8")
        if got != new:
            raise SystemExit("đọc lại #%d ra %r, chờ %r" % (idx, got, new))
    print("  đọc lại: %d literal đúng như dự kiến" % len(PLAN))

    changed = [k for k in range(len(before)) if before[k] != back[k]]
    region = set(range(data_off + lo, data_off + hi))
    table = set()
    for idx, _o, _n in PLAN:
        table.update(range(lit_off + idx * 8, lit_off + idx * 8 + 8))
    stray = [k for k in changed if k not in region and k not in table]
    print("  %d byte đổi: %d trong vùng dữ liệu, %d trong bảng literal, %d chỗ khác"
          % (len(changed), sum(1 for k in changed if k in region),
             sum(1 for k in changed if k in table), len(stray)))
    if stray:
        raise SystemExit("có byte đổi ngoài dự kiến: %s" % stray[:8])


if __name__ == "__main__":
    main()
