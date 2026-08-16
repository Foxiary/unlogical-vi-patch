# -*- coding: utf-8 -*-
"""Tạo bản vá IPS32 cho `main` và cài vào thư mục mod của Ryujinx.

Bản vá đầu tiên: tắt ngắt dòng 18 ký tự của màn chọn chương.

    Chapter.get_DefaultMaxCharsPerLine   RVA 0x1998AC0
        52800240   MOVZ W0, #18      ->   2A1F03E0   MOV W0, WZR

Lớp cha khai báo thuộc tính này kèm tooltip
「非EN言語での1行あたり最大文字数。0以下で折り返し無効。」 — số ký tự tối đa mỗi
dòng cho ngôn ngữ không phải EN, **0 hoặc nhỏ hơn thì tắt ngắt dòng**. Hai màn
khác trong game đã trả về 0 sẵn (`MOV W0, WZR` tại 0x1A16930 và 0x1AB6B60), nên
đây là cấu hình được hỗ trợ chứ không phải mẹo.

Offset trong file vá = RVA + 0x100: bản vá áp lên NSO **đã giải nén** tính cả
header 0x100 byte, và `.text` có mem_off = 0. Dùng IPS32 (magic `IPS32`, offset
4 byte, kết thúc `EEOF`) vì IPS thường chỉ địa chỉ được 3 byte = 16 MB, không
với tới 0x1998AC0.

    python tools\\make_ips.py            # chạy thử, chỉ kiểm tra
    python tools\\make_ips.py --apply    # ghi vào thư mục mod
"""
import io
import os
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BUILD_ID = "669EA2FE0282C2C0EFEA4DA183419FB7"
NSO_HEADER = 0x100
MOD_EXEFS = os.path.join(os.environ["APPDATA"], "Ryujinx", "mods", "contents",
                         "010068501ff9a000", "vn-translation", "exefs")
APPLY = "--apply" in sys.argv

# (nhãn, RVA, byte cũ, byte mới)
PATCHES = [
    # KHÔNG dùng 0: trả 0 thì `SetNoteTextFromString` bỏ luôn bước ngắt dòng, mà
    # chính nó cũng là chỗ đếm số dòng để chia trang — thanh cuộn thấy 1 dòng =
    # 1 trang và chết cứng.
    #
    # Cũng không dùng 24: engine cắt CỨNG đúng N ký tự, không nhìn khoảng trắng,
    # nên ra `…một nh / à sáng tạo…`. Nhưng nó tôn trọng `\n` có sẵn, nên việc
    # ngắt theo từ giao cho `wrap_synopsis.py` làm ở phía dữ liệu (dòng dài nhất
    # 30 ký tự), còn hằng số này chỉ cần cao hơn con số đó để engine đừng cắt nữa.
    ("Chapter.get_DefaultMaxCharsPerLine  18 -> 40 (cao hơn dòng dài nhất 30)",
     0x1998AC0,
     bytes.fromhex("40028052"),      # MOVZ W0, #18
     bytes.fromhex("00058052")),     # MOVZ W0, #40
]


def build(flat_path):
    out = bytearray(b"IPS32")
    for label, rva, old, new in PATCHES:
        if flat_path:
            with open(flat_path, "rb") as f:
                f.seek(rva)
                cur = f.read(len(old))
            if cur != old:
                raise SystemExit("byte tại RVA 0x%X là %s, chờ %s — sai bản build?"
                                 % (rva, cur.hex(), old.hex()))
        off = rva + NSO_HEADER
        assert len(new) == len(old)
        out += struct.pack(">IH", off, len(new)) + new
        print("  %-52s RVA 0x%X -> offset 0x%X" % (label, rva, off))
        print("     %s  ->  %s" % (old.hex().upper(), new.hex().upper()))
    out += b"EEOF"
    return bytes(out)


def main():
    flat = os.path.join(ROOT, "tools", "_ext", "main.flat")
    if not os.path.exists(flat):
        flat = None
        print("(không thấy main.flat để đối chiếu — bỏ qua bước kiểm tra byte cũ)")
    print("build id: %s" % BUILD_ID)
    blob = build(flat)
    print("\nIPS32 %d byte, %d bản vá" % (len(blob), len(PATCHES)))

    dest = os.path.join(MOD_EXEFS, BUILD_ID + ".ips")
    if not APPLY:
        print("\nsẽ ghi vào: %s" % dest)
        print("CHẠY THỬ — thêm --apply để cài")
        return
    os.makedirs(MOD_EXEFS, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(blob)
    print("\nđã cài: %s" % dest)
    print("gỡ bằng cách xoá đúng file đó.")


main()
