# -*- coding: utf-8 -*-
"""Đồng bộ bản làm việc sang clone phát hành và dựng lại manifest.json.

Bản patch phát hành từ một clone riêng (xem memory unlogical-publish-repo):

    làm việc   D:\\Downloads\\010068501ff9a000        (KHÔNG phải git repo)
    clone      D:\\OneDrive - vlylm\\Game\\unlogical-vi-patch

`manifest.json` liệt kê path/bytes/md5 cho mọi file được ship, gắn nhãn
`"where": "repo"` hoặc `"release"`. **Phải dựng lại cùng commit với mọi thay đổi
nhị phân** — không có gì tự ép điều đó.

Bản `.ips` không nằm trong `romfs` mà ở thư mục mod của Ryujinx, cạnh junction —
nên nó rất dễ bị bỏ quên. Script lấy thẳng từ đó.

`tools/` và `e2e/` cũng được chép, dù chúng **không** nằm trong manifest — manifest
chỉ liệt kê dữ liệu game được ship. Trước đây phần này phải nhớ chép tay, và đã
quên thật: `make_release.py` với `sync_publish.py` nằm ngoài git suốt hai tiếng
dù chính chúng là công cụ phát hành. Cùng một lớp lỗi với việc bỏ sót `exefs/` ở
v1.1 — thứ gì nằm ngoài đường đi của script thì sớm muộn cũng bị quên.

    python tools\\sync_publish.py            # chạy thử, chỉ báo khác biệt
    python tools\\sync_publish.py --apply    # chép + dựng lại manifest
"""
import hashlib
import io
import json
import os
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CLONE = r"D:\OneDrive - vlylm\Game\unlogical-vi-patch"
MOD_EXEFS = os.path.join(os.environ["APPDATA"], "Ryujinx", "mods", "contents",
                         "010068501ff9a000", "vn-translation", "exefs")
MANIFEST = os.path.join(CLONE, "manifest.json")
APPLY = "--apply" in sys.argv

# file mới cần thêm vào manifest, kèm nhãn where
NEW_FILES = {
    "romfs/Data/level13": "repo",
}

# mã nguồn đi kèm repo nhưng KHÔNG thuộc manifest (manifest chỉ là dữ liệu game)
EXTRA_DIRS = ("tools", "e2e")
# khớp .gitignore của clone: thứ do máy sinh ra thì không chép
SKIP_DIRS = {"__pycache__", "_ext", "_preview", "out"}
SKIP_EXT = (".pyc", ".bak", ".tmp")


def src_of(rel):
    """Đường dẫn bản làm việc cho một entry của manifest."""
    if rel.startswith("exefs/"):
        return os.path.join(MOD_EXEFS, rel.split("/", 1)[1])
    return os.path.join(ROOT, rel.replace("/", os.sep))


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_extras():
    """(rel, src) cho mọi file mã nguồn đáng chép sang clone."""
    for top in EXTRA_DIRS:
        base = os.path.join(ROOT, top)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, files in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in files:
                if f.endswith(SKIP_EXT):
                    continue
                src = os.path.join(dirpath, f)
                yield os.path.relpath(src, ROOT).replace(os.sep, "/"), src


def sync_extras():
    """Chép tools/ và e2e/. Trả về số file đã (hoặc sẽ) chép."""
    copied, orphan = [], []
    for rel, src in walk_extras():
        dst = os.path.join(CLONE, rel.replace("/", os.sep))
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src) \
                and md5(dst) == md5(src):
            continue
        copied.append((rel, src, dst, os.path.getsize(src), os.path.exists(dst)))

    # file còn ở clone nhưng đã bỏ ở bản làm việc — chỉ báo, không tự xoá
    have = {rel for rel, _ in walk_extras()}
    for top in EXTRA_DIRS:
        base = os.path.join(CLONE, top)
        for dirpath, dirnames, files in os.walk(base) if os.path.isdir(base) else ():
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in files:
                if f.endswith(SKIP_EXT):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, f), CLONE).replace(os.sep, "/")
                if rel not in have:
                    orphan.append(rel)

    print("\n--- mã nguồn (%s) ---" % ", ".join(EXTRA_DIRS))
    for rel, _, _, size, existed in copied:
        print("  %-46s %10s  %s" % (rel, format(size, ","), "KHÁC" if existed else "MỚI"))
    if orphan:
        print("  chỉ có ở clone (đã bỏ ở bản làm việc?): %s" % ", ".join(orphan))
    if not copied:
        print("  không có gì để chép")

    if APPLY:
        for rel, src, dst, size, _ in copied:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        if copied:
            print("  đã chép %d file" % len(copied))
    return len(copied)


def main():
    man = json.load(open(MANIFEST, encoding="utf-8"))
    known = {e["path"]: e for e in man}
    for rel, where in NEW_FILES.items():
        if rel not in known:
            known[rel] = {"path": rel, "bytes": 0, "md5": "", "where": where}
            print("MỚI trong manifest: %s (%s)" % (rel, where))

    rows, missing, changed = [], [], []
    for rel in sorted(known, key=lambda r: (r.startswith("exefs/"), r)):
        e = known[rel]
        src = src_of(rel)
        dst = os.path.join(CLONE, rel.replace("/", os.sep))
        if not os.path.exists(src):
            missing.append(rel)
            continue
        size, digest = os.path.getsize(src), md5(src)
        same_clone = (os.path.exists(dst) and os.path.getsize(dst) == size
                      and md5(dst) == digest)
        state = "khớp" if same_clone else ("THIẾU Ở CLONE" if not os.path.exists(dst) else "KHÁC")
        if not same_clone:
            changed.append((rel, src, dst, size))
        stale = (e["bytes"] != size or e["md5"] != digest)
        rows.append((rel, e["where"], size, digest, state, stale))

    print("\n%-52s %-8s %12s  %-14s %s" % ("path", "where", "bytes", "clone", "manifest"))
    for rel, where, size, digest, state, stale in rows:
        print("%-52s %-8s %12s  %-14s %s"
              % (rel, where, format(size, ","), state, "CẦN CẬP NHẬT" if stale else "ok"))

    if missing:
        print("\nKHÔNG THẤY Ở BẢN LÀM VIỆC (%d): %s" % (len(missing), ", ".join(missing)))
    print("\nfile cần chép: %d   mục manifest cần cập nhật: %d"
          % (len(changed), sum(1 for r in rows if r[5])))

    n_extra = sync_extras()

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để chép và ghi manifest (%d nhị phân + %d mã nguồn)"
              % (len(changed), n_extra))
        return

    for rel, src, dst, size in changed:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print("chép %s (%s byte)" % (rel, format(size, ",")))

    out = []
    for rel, where, size, digest, _, _ in rows:
        out.append({"path": rel, "bytes": size, "md5": digest, "where": where})
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("\nđã ghi %s (%d mục)" % (MANIFEST, len(out)))

    bad = []
    for e in out:
        dst = os.path.join(CLONE, e["path"].replace("/", os.sep))
        if not os.path.exists(dst):
            bad.append((e["path"], "thiếu ở clone"))
        elif os.path.getsize(dst) != e["bytes"] or md5(dst) != e["md5"]:
            bad.append((e["path"], "lệch hash"))
    print("kiểm tra lại clone theo manifest: %s"
          % ("khớp hết" if not bad else "LỖI %s" % bad))


main()
