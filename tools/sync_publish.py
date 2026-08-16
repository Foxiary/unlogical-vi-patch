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

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để chép và ghi manifest")
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
