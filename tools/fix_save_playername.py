"""Đổi tên nhân vật chính đang lưu trong save Ryujinx sang tên đã dịch.

Vá `global-metadata.dat` chỉ đổi **giá trị mặc định** mà màn nhập tên gợi ý cho
một máy chưa từng chơi. Máy đã chơi rồi thì màn nhập tên lấy tên từ save
(`auto_data`), nên bấm New Game vẫn thấy `環無`. Đây là chỗ sửa cái đó.

Bố cục `auto_data` (524288 byte): một luồng gzip từ offset 0 rồi đệm 0. Giải nén
ra đúng 524288 byte gồm tiền tố độ dài kiểu .NET `BinaryWriter` (7-bit), rồi
JSON UTF-8, rồi đệm 0. Không có checksum ngoài CRC của chính gzip.

**Đóng Ryujinx trước khi chạy**, nếu không nó ghi đè lúc thoát.

    python tools\fix_save_playername.py            # chạy thử
    python tools\fix_save_playername.py --apply    # backup rồi sửa
"""

import gzip
import io
import json
import os
import shutil
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SAVE = os.path.expandvars(r"%APPDATA%\Ryujinx\bis\user\save\0000000000000001")
SLOTS = ["0", "1"]                      # hai khe nhật ký, phải giữ giống hệt nhau
BACKUP = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "_backup"))

# 涼乃環無 -> Suzuno Kanna, khớp với literal 15053/15063 trong global-metadata.dat
# và với 120 lần "Kanna" trong ScenarioData đã dịch.
RENAMES = {"環無": "Kanna"}
SIZE = 524288


def read(path):
    blob = open(path, "rb").read()
    raw = gzip.decompress(blob)
    n = shift = length = 0
    while True:
        b = raw[n]
        length |= (b & 0x7F) << shift
        n += 1
        shift += 7
        if not b & 0x80:
            break
    return blob, raw, n, json.loads(raw[n:n + length].decode("utf-8"))


def varint(n):
    out = bytearray()
    while n >= 0x80:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    out.append(n)
    return bytes(out)


def write(path, obj):
    body = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    raw = varint(len(body)) + body
    if len(raw) > SIZE:
        raise ValueError("JSON dài hơn bộ đệm 524288 byte")
    raw += b"\x00" * (SIZE - len(raw))
    blob = gzip.compress(raw, 9, mtime=0)
    if len(blob) > SIZE:
        raise ValueError("luồng gzip dài hơn file")
    blob += b"\x00" * (SIZE - len(blob))
    with open(path, "wb") as f:
        f.write(blob)


def rename(value):
    if isinstance(value, str):
        return RENAMES.get(value, value)
    if isinstance(value, list):
        return [rename(v) for v in value]
    return value


def main():
    apply = "--apply" in sys.argv
    if not os.path.isdir(SAVE):
        print("không thấy save:", SAVE)
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")

    for slot in SLOTS:
        path = os.path.join(SAVE, slot, "auto_data")
        if not os.path.exists(path):
            print(f"khe {slot}: không có auto_data")
            continue
        _, _, _, obj = read(path)

        changed = []
        for key in ("m_PlayerName", "m_NickName",
                    "m_LanguagePlayerName", "m_LanguageNickName"):
            if key not in obj:
                continue
            new = rename(obj[key])
            if new != obj[key]:
                changed.append(f"{key}: {json.dumps(obj[key], ensure_ascii=False)}"
                               f" -> {json.dumps(new, ensure_ascii=False)}")
                obj[key] = new

        print(f"khe {slot}: ngôn ngữ={obj.get('m_CurrentLanguage')} — "
              f"{len(changed)} trường đổi")
        for c in changed:
            print("   ", c)
        if not changed or not apply:
            continue

        os.makedirs(BACKUP, exist_ok=True)
        shutil.copy(path, os.path.join(BACKUP, f"auto_data.slot{slot}.prename-{stamp}"))
        write(path, obj)
        _, _, _, back = read(path)
        assert back == obj, "đọc lại không khớp"
        print(f"    đã ghi, đọc lại khớp — backup _backup\\auto_data.slot{slot}.prename-{stamp}")

    if not apply:
        print("\nChạy thử. Đóng Ryujinx rồi chạy lại với --apply.")


if __name__ == "__main__":
    main()
