# -*- coding: utf-8 -*-
"""Dựng file zip phát hành từ manifest và tạo release trên GitHub.

Zip được ghi **thẳng từ clone theo `manifest.json`**, không qua thư mục tạm —
nên không bao giờ dính `.resS` (LayeredFS lấy từ game gốc), rác `CAB-*`, hay
thiếu bản `.ips` ở `exefs/` vốn nằm ngoài `romfs/`.

Gốc zip là thư mục `vn-translation/` chứa cả `romfs/` lẫn `exefs/`, để người
chơi giải nén thẳng vào `%APPDATA%\\Ryujinx\\mods\\contents\\010068501ff9a000\\`.

    python tools\\make_release.py v1.2              # kiểm tra, in kế hoạch
    python tools\\make_release.py v1.2 --build      # + dựng zip
    python tools\\make_release.py v1.2 --publish    # + gh release create

Ba tầng cố ý tách nhau: kiểm tra thì nhanh, dựng zip mất vài phút, còn tạo
release là việc không rút lại được.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import zipfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CLONE = r"D:\OneDrive - vlylm\Game\unlogical-vi-patch"
REPO = "Foxiary/unlogical-vi-patch"
OUT_DIR = r"D:\Downloads"
ZIP_ROOT = "vn-translation"
IPS = "exefs/669EA2FE0282C2C0EFEA4DA183419FB7.ips"

args = [a for a in sys.argv[1:] if not a.startswith("--")]
BUILD = "--build" in sys.argv or "--publish" in sys.argv
PUBLISH = "--publish" in sys.argv
NOTES_FILE = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--notes-file=")), None)
if not args or not re.fullmatch(r"v\d+\.\d+(\.\d+)?", args[0]):
    raise SystemExit("cần số hiệu bản, ví dụ: python tools\\make_release.py v1.2 hoặc v1.2.1")
VER = args[0]
ZIP = os.path.join(OUT_DIR, "unlogical-vi-patch-%s-romfs.zip" % VER)


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*a):
    return subprocess.run(("git", "-C", CLONE) + a, capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()


def check():
    man = json.load(open(os.path.join(CLONE, "manifest.json"), encoding="utf-8"))
    print("manifest: %d mục" % len(man))
    bad = []
    total = 0
    for e in man:
        p = os.path.join(CLONE, e["path"].replace("/", os.sep))
        if not os.path.exists(p):
            bad.append((e["path"], "thiếu"))
        elif os.path.getsize(p) != e["bytes"]:
            bad.append((e["path"], "sai kích thước"))
        elif md5(p) != e["md5"]:
            bad.append((e["path"], "sai md5"))
        else:
            total += e["bytes"]
    for p, why in bad:
        print("  LỖI %-52s %s" % (p, why))
    if bad:
        raise SystemExit("clone lệch manifest — chạy tools\\sync_publish.py --apply trước")
    print("  mọi file khớp manifest, tổng %.1f MB" % (total / 1e6))

    if not any(e["path"] == IPS for e in man):
        raise SystemExit("manifest KHÔNG có bản .ips — đừng phát hành")
    print("  có bản .ips trong manifest")

    dirty = git("status", "--porcelain")
    print("  git status: %s" % ("sạch" if not dirty else "CÒN THAY ĐỔI CHƯA COMMIT"))
    if dirty:
        for line in dirty.splitlines()[:8]:
            print("     " + line)

    tags = git("tag", "--list").split()
    print("  tag đã có: %s" % ", ".join(tags))
    if VER in tags:
        raise SystemExit("tag %s đã tồn tại" % VER)

    readme = open(os.path.join(CLONE, "README.md"), encoding="utf-8").read()
    want = "unlogical-vi-patch-%s-romfs.zip" % VER
    if want not in readme:
        old = re.findall(r"unlogical-vi-patch-v[\d.]+-romfs\.zip", readme)
        raise SystemExit("README.md còn trỏ tới %s — sửa thành %s rồi commit"
                         % (", ".join(sorted(set(old))) or "(không thấy)", want))
    print("  README.md trỏ đúng %s" % want)
    return man


def build(man):
    if os.path.exists(ZIP):
        os.remove(ZIP)
    t0 = time.time()
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for i, e in enumerate(man, 1):
            src = os.path.join(CLONE, e["path"].replace("/", os.sep))
            z.write(src, "%s/%s" % (ZIP_ROOT, e["path"]))
            print("  [%2d/%d] %s" % (i, len(man), e["path"]))
    size = os.path.getsize(ZIP)
    print("\nđã dựng %s — %.1f MB trong %.0f giây" % (ZIP, size / 1e6, time.time() - t0))

    with zipfile.ZipFile(ZIP) as z:
        names = z.namelist()
    assert len(names) == len(man), "số file trong zip lệch"
    assert "%s/%s" % (ZIP_ROOT, IPS) in names, "zip thiếu bản .ips"
    assert not [n for n in names if n.endswith(".resS")], "zip dính .resS"
    assert not [n for n in names if "/CAB-" in n], "zip dính rác CAB-*"
    print("kiểm tra zip: %d file, có .ips, không .resS, không CAB-*" % len(names))


def publish(man):
    font = os.path.join(CLONE, "romfs", "Data", "StreamingAssets", "font", "font_jp")
    cmd = ["gh", "release", "create", VER, ZIP, font,
           "--repo", REPO,
           "--title", "Vietnamese patch %s (game v1.0.2)" % VER]
    if NOTES_FILE:
        # ghi chú lấy nguyên từ file — dùng khi muốn giữ đúng nội dung bản trước
        if not os.path.exists(NOTES_FILE):
            raise SystemExit("không thấy %s" % NOTES_FILE)
        cmd += ["--notes-file", NOTES_FILE]
    else:
        cmd += ["--notes", "Xem README để biết cách cài. Phải chép cả `romfs` lẫn `exefs`."]
    print("\n$ " + " ".join('"%s"' % c if " " in c else c for c in cmd))
    if not PUBLISH:
        return
    r = subprocess.run(cmd, text=True)
    if r.returncode:
        raise SystemExit("gh release create thất bại (%d)" % r.returncode)
    print("đã tạo release %s" % VER)


man = check()
if BUILD:
    build(man)
else:
    print("\n(thêm --build để dựng zip, --publish để tạo release)")
publish(man)
