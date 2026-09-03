# -*- coding: utf-8 -*-
"""Bóc RomFS của mọi NCA trong một NSP — dùng cho AOC/DLC. Mượn crypto của `extract_exefs.py`.

DLC 1 của UNLOGICAL là title AOC riêng `010068501FF9B001` (NSP 2,25 MB đăng ký trong
`%APPDATA%\\Ryujinx\\games\\010068501ff9a000\\dlc.json`). Romfs của nó có 5 file:

    assetlist_aoc01
    json/json_aoc01            DLCData_01 — 5 charaName + tên sprite của màn Download Contents
    scenario/scenario_aoc01    ScenarioData riêng (scenario 1005..1009, script 09_01..09_05),
                               scenariolist, ChapterAlready
    sprite/sprite_jp_aoc01     16 ảnh (bảng tên, thumbnail, tiêu đề, màn Caution)
    texture/texture_aoc01      nền

LayeredFS áp theo title nên mod của game gốc không chạm được gì ở đây — xem
`apply_dlc_sheet.py`. Đầu ra mặc định là `D:\\Downloads\\UNLOGICAL_DLC1\\romfs`, đóng vai
dump gốc của AOC (song song với `D:\\Downloads\\UNLOGICAL_v2\\Data` của game chính).

RomFS đọc theo IVFC: FS header của section có magic `IVFC` ở +0x08, level dữ liệu là level
cuối có size > 0; RomFS header 0x50 byte (10 u64), bảng dir/file entry rồi vùng dữ liệu.
Section mã hoá AES-CTR bằng titlekey lấy từ .tik trong NSP, đọc qua `ctr_read()`.

    python tools\\extract_dlc_romfs.py "<đường dẫn .nsp>" <thư mục ra> [--dry]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_exefs as X   # noqa: E402  (module này tự bọc sys.stdout sang UTF-8, không bọc lại)

CONTENT = {0: "Program", 1: "Meta", 2: "Control", 3: "Manual", 4: "Data", 5: "PublicData"}


def romfs_walk(read, out_root, dry):
    """`read(off, size)` đọc trong section đã giải mã; trả về danh sách (path, size)."""
    hdr = read(0, 0x50)
    (hsize, dh_off, dh_size, dm_off, dm_size, fh_off, fh_size, fm_off, fm_size,
     data_off) = struct.unpack_from("<10Q", hdr, 0)
    if hsize != 0x50:
        raise ValueError("không phải RomFS (header size %d)" % hsize)
    dirs = read(dm_off, dm_size)
    files = read(fm_off, fm_size)
    out = []

    def fname(blob, off, n):
        return blob[off:off + n].decode("utf-8", "replace")

    def walk_dir(doff, path):
        parent, sibling, child, first_file, _hash, nlen = struct.unpack_from("<6I", dirs, doff)
        name = fname(dirs, doff + 0x18, nlen)
        here = path + ("/" + name if name else "")
        foff = first_file
        while foff != 0xFFFFFFFF:
            fparent, fsib, fdata_off, fdata_size, _fh, fnlen = struct.unpack_from("<IIQQII", files, foff)
            fn = fname(files, foff + 0x20, fnlen)
            rel = (here + "/" + fn).lstrip("/")
            out.append((rel, fdata_size))
            if not dry:
                p = os.path.join(out_root, rel.replace("/", os.sep))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "wb") as w:
                    pos = 0
                    while pos < fdata_size:
                        n = min(1 << 22, fdata_size - pos)
                        w.write(read(data_off + fdata_off + pos, n))
                        pos += n
            foff = fsib
        c = child
        while c != 0xFFFFFFFF:
            walk_dir(c, here)
            c = struct.unpack_from("<I", dirs, c + 4)[0]

    walk_dir(0, "")
    return out


def main(nsp, outdir, dry):
    keys = X.load_keys()
    f = open(nsp, "rb")
    head = f.read(0x10)
    n = struct.unpack_from("<I", head, 4)[0]
    f.seek(0)
    entries = X.parse_pfs0(f.read(0x10 + n * 24 + struct.unpack_from("<I", head, 8)[0]))
    print("NSP: %d mục: %s" % (len(entries), ", ".join("%s(%d)" % (e[0], e[2]) for e in entries)))
    tik = next((e for e in entries if e[0].endswith(".tik")), None)
    title_key = None
    if tik:
        f.seek(tik[1])
        rights_id, mkey_rev, title_key = X.ticket_titlekey(f.read(tik[2]), keys)
        print("rights id %s, mkey rev %d" % (rights_id.hex(), mkey_rev))
    for name, off, size in entries:
        if not name.endswith(".nca"):
            continue
        f.seek(off)
        hdr = X.xts_decrypt(keys["header_key"], f.read(0xC00))
        if hdr[0x200:0x204] not in (b"NCA3", b"NCA2"):
            print("%s: header không giải mã được" % name)
            continue
        ctype = hdr[0x205]
        title_id = struct.unpack_from("<Q", hdr, 0x210)[0]
        print("\n%s  %.2f MB  content=%s  titleId=%016X" % (name, size / 1e6, CONTENT.get(ctype, ctype), title_id))
        for i in range(4):
            start, end = struct.unpack_from("<II", hdr, 0x240 + i * 0x10)
            if start == end == 0:
                continue
            fsh = hdr[0x400 + i * 0x200: 0x400 + (i + 1) * 0x200]
            fs_type, hash_type, enc_type = fsh[0x02], fsh[0x03], fsh[0x04]
            print("   section %d: fs_type=%d (%s) hash=%d enc=%d" % (
                i, fs_type, "RomFS" if fs_type == 0 else "PFS0", hash_type, enc_type))
            if fs_type != 0:
                continue
            if enc_type == 1:
                key = None
            elif enc_type == 3 and title_key is not None:
                key = title_key
            else:
                print("      enc=%d chưa hỗ trợ" % enc_type)
                continue
            nca_base = start * 0x200
            file_base = off + nca_base
            ctr8 = fsh[0x140:0x148]
            magic = fsh[0x08:0x0C]
            nlev = struct.unpack_from("<I", fsh, 0x14)[0]
            levels = [struct.unpack_from("<QQ", fsh, 0x18 + k * 0x18) for k in range(6)]
            data_lvl = [l for l in levels if l[1] > 0][-1]
            print("      IVFC %r levels=%d, data level @0x%X size %d" % (magic, nlev, data_lvl[0], data_lvl[1]))

            def read(o, s, _fb=file_base, _nb=nca_base, _c=ctr8, _k=key, _lo=data_lvl[0]):
                if _k is None:
                    f.seek(_fb + _lo + o)
                    return f.read(s)
                return X.ctr_read(f, _fb, _nb, _c, _lo + o, s, _k)

            try:
                listing = romfs_walk(read, os.path.join(outdir, "romfs"), dry)
            except ValueError as e:
                print("      ", e)
                continue
            print("      RomFS: %d file, %.2f MB" % (len(listing), sum(s for _, s in listing) / 1e6))
            for rel, s in listing:
                print("        %10d  %s" % (s, rel))
    f.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit("cần: python tools\\extract_dlc_romfs.py <nsp> <thư mục ra> [--dry]")
    main(sys.argv[1], sys.argv[2], "--dry" in sys.argv)
