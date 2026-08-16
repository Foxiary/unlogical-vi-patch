# -*- coding: utf-8 -*-
"""Tách ExeFS (`main`, `main.npdm`) từ file NSP cập nhật, rồi giải nén NSO.

Không có hactool/LibHac trên máy nên tự làm, chỉ cần `pycryptodome` + `lz4`:

    NSP (PFS0) ─┬─ *.tik      -> titlekey đã mã hoá
                └─ *.nca      -> header AES-XTS(header_key)
                                 section AES-CTR(titlekey)
                                 section = PFS0 chứa `main`
    main (NSO0) -> 3 segment nén LZ4-block -> ảnh phẳng theo memory offset

Đọc `prod.keys` của Ryujinx. Chỉ giải mã đúng những đoạn cần, không đụng tới
177 MB còn lại của NCA.

    python tools\\extract_exefs.py "<đường dẫn .nsp>" [thư mục ra]
"""
import io
import os
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from Crypto.Cipher import AES          # noqa: E402
import lz4.block                        # noqa: E402

KEYS_PATH = os.path.join(os.environ["APPDATA"], "Ryujinx", "system", "prod.keys")


# ----------------------------------------------------------------- khoá
def load_keys(path=KEYS_PATH):
    keys = {}
    for line in open(path, encoding="utf-8"):
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip().lower(), v.strip()
        try:
            keys[k] = bytes.fromhex(v)
        except ValueError:
            pass
    return keys


# ----------------------------------------------------------------- AES-XTS
def _mul_alpha(t):
    carry = 0
    for i in range(16):
        b = t[i]
        t[i] = ((b << 1) & 0xFF) | carry
        carry = b >> 7
    if carry:
        t[0] ^= 0x87


def xts_decrypt(key, data, sector_size=0x200, sector=0):
    """XTS kiểu Nintendo: tweak khởi tạo từ số sector dạng BIG-endian."""
    crypt = AES.new(key[:16], AES.MODE_ECB)
    tweaker = AES.new(key[16:], AES.MODE_ECB)
    out = bytearray()
    for s in range(len(data) // sector_size):
        tweak = bytearray(tweaker.encrypt((sector + s).to_bytes(16, "big")))
        chunk = data[s * sector_size:(s + 1) * sector_size]
        for b in range(0, sector_size, 16):
            blk = bytes(x ^ y for x, y in zip(chunk[b:b + 16], tweak))
            dec = crypt.decrypt(blk)
            out += bytes(x ^ y for x, y in zip(dec, tweak))
            _mul_alpha(tweak)
    return bytes(out)


def ctr_read(f, file_base, nca_base, ctr8, offset, size, key):
    """Đọc `size` byte tại `offset` (tương đối section) của một section AES-CTR.

    Bộ đếm tính theo offset tuyệt đối **trong NCA** (`nca_base + offset`), còn vị
    trí đọc thì theo offset trong file NSP (`file_base + offset`) — hai gốc khác
    nhau, lẫn là ra rác.
    """
    aligned = offset & ~0xF
    pad = offset - aligned
    total_aligned = (pad + size + 0xF) & ~0xF
    counter = bytearray(16)
    counter[0:8] = ctr8[::-1]
    counter[8:16] = ((nca_base + aligned) >> 4).to_bytes(8, "big")
    f.seek(file_base + aligned)
    raw = f.read(total_aligned)
    cipher = AES.new(key, AES.MODE_CTR, nonce=b"", initial_value=bytes(counter))
    return cipher.decrypt(raw)[pad:pad + size]


# ----------------------------------------------------------------- PFS0
def parse_pfs0(blob):
    magic, n, str_size, _ = struct.unpack_from("<4sIII", blob, 0)
    assert magic == b"PFS0", magic
    entries = []
    for i in range(n):
        off, size, name_off, _ = struct.unpack_from("<QQII", blob, 16 + i * 24)
        entries.append((off, size, name_off))
    strtab = blob[16 + n * 24: 16 + n * 24 + str_size]
    data_off = 16 + n * 24 + str_size
    out = []
    for off, size, name_off in entries:
        name = strtab[name_off:strtab.index(b"\0", name_off)].decode()
        out.append((name, data_off + off, size))
    return out


# ----------------------------------------------------------------- ticket
def ticket_titlekey(tik, keys):
    sig_type = struct.unpack_from("<I", tik, 0)[0]
    head = {0x10000: 0x240, 0x10001: 0x140, 0x10002: 0xC0,
            0x10003: 0x240, 0x10004: 0x140, 0x10005: 0xC0}[sig_type]
    enc_key = tik[head + 0x40:head + 0x50]
    rights_id = tik[head + 0x160:head + 0x170]
    mkey_rev = rights_id[15]
    idx = mkey_rev - 1 if mkey_rev > 0 else 0
    kek = keys.get("titlekek_%02x" % idx)
    if kek is None:
        raise SystemExit("thiếu titlekek_%02x trong prod.keys" % idx)
    title_key = AES.new(kek, AES.MODE_ECB).decrypt(enc_key)
    return rights_id, mkey_rev, title_key


# ----------------------------------------------------------------- NCA
def extract_exefs(nsp_path, outdir):
    keys = load_keys()
    os.makedirs(outdir, exist_ok=True)
    f = open(nsp_path, "rb")
    head = f.read(0x10)
    n = struct.unpack_from("<I", head, 4)[0]
    f.seek(0)
    files = parse_pfs0(f.read(0x10 + n * 24 + struct.unpack_from("<I", head, 8)[0]))

    tik = next((e for e in files if e[0].endswith(".tik")), None)
    if tik is None:
        raise SystemExit("NSP không có ticket — chưa hỗ trợ crypto tiêu chuẩn")
    f.seek(tik[1])
    rights_id, mkey_rev, title_key = ticket_titlekey(f.read(tik[2]), keys)
    print("rights id      : %s" % rights_id.hex())
    print("master key rev : %d  -> titlekek_%02x" % (mkey_rev, max(mkey_rev - 1, 0)))
    print("title key      : %s" % title_key.hex())

    ncas = [e for e in files if e[0].endswith(".nca") and not e[0].endswith(".cnmt.nca")]
    ncas.sort(key=lambda e: -e[2])
    for name, off, size in ncas:
        f.seek(off)
        hdr = xts_decrypt(keys["header_key"], f.read(0xC00))
        if hdr[0x200:0x204] not in (b"NCA3", b"NCA2"):
            print("%s: giải mã header thất bại (%r)" % (name, hdr[0x200:0x204]))
            continue
        content_type = hdr[0x205]
        print("\n%s  %.1f MB  content_type=%d" % (name, size / 1e6, content_type))
        if content_type != 0:
            continue                       # 0 = Program
        for i in range(4):
            start, end = struct.unpack_from("<II", hdr, 0x240 + i * 0x10)
            if start == end == 0:
                continue
            fsh = hdr[0x400 + i * 0x200: 0x400 + (i + 1) * 0x200]
            fs_type, hash_type, enc_type = fsh[0x02], fsh[0x03], fsh[0x04]
            nca_base = start * 0x200            # gốc của bộ đếm CTR
            file_base = off + nca_base          # gốc để seek trong NSP
            if fs_type != 1 or enc_type != 3:
                print("   section %d: fs_type=%d enc=%d (bỏ qua)" % (i, fs_type, enc_type))
                continue
            layer_count = struct.unpack_from("<I", fsh, 0x08 + 0x24)[0]
            l_off, l_size = struct.unpack_from("<QQ", fsh, 0x08 + 0x28 + (layer_count - 1) * 0x10)
            ctr8 = fsh[0x140:0x148]
            head_blob = ctr_read(f, file_base, nca_base, ctr8, l_off, 0x1000, title_key)
            if head_blob[:4] != b"PFS0":
                print("   section %d: layer_count=%d pfs0@0x%X size=%d -> %r"
                      % (i, layer_count, l_off, l_size, head_blob[:16]))
                continue
            cnt = struct.unpack_from("<I", head_blob, 4)[0]
            st = struct.unpack_from("<I", head_blob, 8)[0]
            need = 0x10 + cnt * 24 + st
            head_blob = ctr_read(f, file_base, nca_base, ctr8, l_off,
                                 (need + 0xFFF) & ~0xFFF, title_key)
            items = parse_pfs0(head_blob)
            print("   section %d: PFS0, %d file -> %s"
                  % (i, len(items), ", ".join(x[0] for x in items)))
            if not any(x[0] == "main" for x in items):
                continue
            for nm, foff, fsize in items:
                data = ctr_read(f, file_base, nca_base, ctr8, l_off + foff, fsize, title_key)
                p = os.path.join(outdir, nm)
                open(p, "wb").write(data)
                print("      -> %-14s %9d B" % (nm, len(data)))
            f.close()
            return outdir
    f.close()
    raise SystemExit("không tìm thấy ExeFS")


# ----------------------------------------------------------------- NSO
def decompress_nso(path, out_path):
    d = open(path, "rb").read()
    assert d[:4] == b"NSO0", d[:4]
    flags = struct.unpack_from("<I", d, 0x0C)[0]
    build_id = d[0x40:0x60]
    segs = []
    for i in range(3):
        f_off, m_off, size = struct.unpack_from("<III", d, 0x10 + i * 0x10)
        comp = struct.unpack_from("<I", d, 0x60 + i * 4)[0]
        raw = d[f_off:f_off + comp]
        if flags & (1 << i):
            raw = lz4.block.decompress(raw, uncompressed_size=size)
        assert len(raw) == size, (i, len(raw), size)
        segs.append((m_off, raw))
    total = max(m + len(r) for m, r in segs)
    img = bytearray(total)
    for m, r in segs:
        img[m:m + len(r)] = r
    open(out_path, "wb").write(img)
    print("\nNSO build id : %s" % build_id.hex().upper().rstrip("0"))
    for i, (m, r) in enumerate(segs):
        print("   segment %d  memory @0x%08X  %9d B  %s"
              % (i, m, len(r), "nén" if flags & (1 << i) else "thô"))
    print("ảnh phẳng    : %s  (%d B)" % (out_path, total))
    return build_id


if __name__ == "__main__":
    nsp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(nsp), "exefs")
    extract_exefs(nsp, out)
    decompress_nso(os.path.join(out, "main"), os.path.join(out, "main.flat"))
