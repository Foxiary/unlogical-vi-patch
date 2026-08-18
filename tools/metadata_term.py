# -*- coding: utf-8 -*-
"""Thay một literal IL2CPP trong `global-metadata.dat`, vá tại chỗ.

Vài chuỗi UI không nằm trong bundle nào mà là hằng chuỗi trong code — alert của
TERMINAL, tên mặc định của nhân vật chính… Grep trong `romfs` không ra, phải sửa
ở bảng `stringLiteral` của metadata.

Bố cục (metadata v31): header ở offset 0, cặp (offset, size) của bảng literal ở
0x08/0x0C và của khối dữ liệu literal ở 0x10/0x14. Mỗi mục trong bảng là
`{uint32 length; uint32 dataIndex}`, dữ liệu **xếp khít nhau, không có đệm**.

Nên bản dịch phải **ngắn hơn hoặc bằng** bản gốc tính theo byte UTF-8: script ghi
đè tại chỗ, số byte dư điền `\\x00`, rồi hạ `length` trong bảng. Kích thước file
không đổi, mọi offset khác giữ nguyên. Nới dài ra thì phải dời toàn bộ các khối
sau đó và viết lại header — không làm ở đây.

    python tools\\metadata_term.py "現在使用できません" "Chưa thể sử dụng"
    python tools\\metadata_term.py "現在使用できません" "Chưa thể sử dụng" --apply
"""
import io
import os
import shutil
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

META = os.path.join(ROOT, "romfs", "Data", "Managed", "Metadata", "global-metadata.dat")
ORIG = r"D:\Downloads\UNLOGICAL_v2\Data\Managed\Metadata\global-metadata.dat"
BACKUP = os.path.join(ROOT, "_backup", "global-metadata.dat.prelitterm")

SANITY = 0xFAB11BAF

args = [a for a in sys.argv[1:] if not a.startswith("--")]
APPLY = "--apply" in sys.argv
if len(args) < 2:
    raise SystemExit(__doc__)
OLD, NEW = args[0], args[1]


def header(blob):
    sanity, version = struct.unpack_from("<Ii", blob, 0)
    if sanity != SANITY:
        raise SystemExit("không phải global-metadata (sanity %08X)" % sanity)
    lit_off, lit_size, data_off, data_size = struct.unpack_from("<IIII", blob, 8)
    return version, lit_off, lit_size, data_off, data_size


def literals(blob):
    """[(index, length, dataIndex)] xếp theo thứ tự trong khối dữ liệu."""
    _, lit_off, lit_size, _, _ = header(blob)
    out = [(i,) + struct.unpack_from("<II", blob, lit_off + i * 8)
           for i in range(lit_size // 8)]
    return sorted(out, key=lambda e: e[2])


def find(blob, text):
    _, lit_off, _, data_off, data_size = header(blob)
    want = text.encode("utf-8")
    ents = literals(blob)
    hits = []
    for k, (i, length, di) in enumerate(ents):
        if blob[data_off + di:data_off + di + length] == want:
            nxt = ents[k + 1][2] if k + 1 < len(ents) else data_size
            hits.append((i, length, di, nxt - (di + length)))
    return hits


def main():
    blob = bytearray(open(META, "rb").read())
    version, lit_off, lit_size, data_off, data_size = header(blob)
    print("%s  %d byte, metadata v%d, %d literal" %
          (os.path.relpath(META, ROOT), len(blob), version, lit_size // 8))

    hits = find(blob, OLD)
    if not hits:
        raise SystemExit("không có literal nào bằng đúng %r" % OLD)
    if len(hits) > 1:
        raise SystemExit("%r trùng %d literal, không dám đoán" % (OLD, len(hits)))
    idx, length, di, slack = hits[0]

    new = NEW.encode("utf-8")
    print("literal %d  @dataIdx=%d (file offset %d)  len=%d, trống sau=%d"
          % (idx, di, data_off + di, length, slack))
    print("   cũ  %2d byte  %r" % (length, OLD))
    print("   mới %2d byte  %r" % (len(new), NEW))
    if len(new) > length:
        raise SystemExit("dài hơn %d byte, không vá tại chỗ được — chọn câu ngắn hơn"
                         % length)
    if len(new) < length:
        print("   thừa %d byte, điền \\x00 và hạ length" % (length - len(new)))

    if os.path.exists(ORIG):
        base = open(ORIG, "rb").read()
        cur = bytes(blob)
        runs = []
        i = 0
        while i < len(base):
            if base[i] != cur[i]:
                j = i
                while j < len(base) and base[j] != cur[j]:
                    j += 1
                runs.append((i, j))
                i = j
            else:
                i += 1
        print("so với bản 1.0.2 gốc: %d vùng đã vá từ trước" % len(runs))

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    # Không bao giờ **bỏ qua** backup vì tên đã tồn tại: mỗi literal là một đợt riêng, và
    # `.prelitterm` đã có từ vòng 現在使用できません. Bỏ qua là mất mốc lùi của vòng này —
    # cùng lớp lỗi đã vá trong `apply_sheet_cells.py`.
    bak = BACKUP
    i = 2
    while os.path.exists(bak):
        bak = "%s%d" % (BACKUP, i)
        i += 1
    shutil.copy2(META, bak)
    print("backup ->", os.path.relpath(bak, ROOT))

    at = data_off + di
    blob[at:at + length] = new + b"\x00" * (length - len(new))
    struct.pack_into("<I", blob, lit_off + idx * 8, len(new))
    with open(META, "wb") as f:
        f.write(blob)

    # đọc lại từ disk, đừng tin bộ đệm trong bộ nhớ
    back = bytearray(open(META, "rb").read())
    if len(back) != len(blob):
        raise SystemExit("kích thước file đổi: %d -> %d" % (len(blob), len(back)))
    v2, lo2, ls2, do2, ds2 = header(back)
    if (v2, lo2, ls2, do2, ds2) != (version, lit_off, lit_size, data_off, data_size):
        raise SystemExit("header đổi")
    L, D = struct.unpack_from("<II", back, lit_off + idx * 8)
    got = back[data_off + D:data_off + D + L].decode("utf-8")
    if (L, D, got) != (len(new), di, NEW):
        raise SystemExit("đọc lại không khớp: len=%d dataIdx=%d %r" % (L, D, got))
    if find(back, OLD):
        raise SystemExit("chuỗi cũ vẫn còn trong bảng literal")

    pre = bytearray(open(bak, "rb").read())
    diff = [i for i in range(len(pre)) if pre[i] != back[i]]
    lo, hi = min(diff), max(diff) + 1
    inside = all(at <= i < at + length or
                 lit_off + idx * 8 <= i < lit_off + idx * 8 + 4 for i in diff)
    print("khác backup ở %d byte, dải %d..%d — %s"
          % (len(diff), lo, hi, "đúng chỗ" if inside else "CÓ BYTE LẠ"))
    if not inside:
        raise SystemExit("vá chạm chỗ khác, hãy khôi phục từ backup")
    print("đã ghi", os.path.relpath(META, ROOT), len(back), "byte")


main()
