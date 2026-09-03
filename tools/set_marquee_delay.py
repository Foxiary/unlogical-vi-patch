# -*- coding: utf-8 -*-
"""Đổi `startDelay` của mọi `AutoScrollText` đang ship — bốn marquee, một trường float mỗi cái.

Bốn hộp chạy chữ (MUSIC `level13`, Ending List `sharedassets21.assets`, tên section `ui_jp`,
danh sách DLC `sharedassets24.assets`) được dựng bởi bốn tool `fix_*_marquee.py`, mỗi tool từ
chối chạy lại trên file đã vá. Khi chỉ cần đổi độ trễ (03/09/2026: 1,5 s → 0,5 s cho cả bốn,
sau khi người dùng thấy 0,5 s ở màn DLC là vừa), dựng lại từ backup là quá tay và có thể kéo
mất sửa đổi nào đó đã ghi lên cùng file sau lượt marquee. Ở đây vá đúng 4 byte:

    AutoScrollText MonoBehaviour = 60 byte (marquee_lib.autoscroll_data):
      0  m_GameObject PPtr   12 m_Enabled+pad   16 m_Script PPtr   28 m_Name (rỗng)
     32  targetText PPtr     44 scrollMode i32  48 startDelay f32  52 speed f32   56 pauseDuration f32

Nhận diện AutoScrollText bằng PPtr `m_Script`: file `.assets` trỏ ra `globalgamemanagers.assets`
pid 1187; bundle `ui_jp` trỏ vào MonoScript cùng CAB (tra theo `m_ClassName`). `.assets` không
nén nên ghi thẳng 4 byte tại `byte_start + 48`, cỡ file không đổi; `ui_jp` nén LZ4 nên phải
`set_raw_data` rồi `save(packer="lz4")`, và đối chiếu lại từng object sau khi ghi.

    python tools\\set_marquee_delay.py                 # in độ trễ hiện tại
    python tools\\set_marquee_delay.py --set 0.5 --apply
"""
import argparse
import hashlib
import io
import os
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "romfs", "Data")

import UnityPy  # noqa: E402
from UnityPy.files import BundleFile, SerializedFile  # noqa: E402

MS_AUTOSCROLL = 1187          # pid MonoScript AutoScrollText trong globalgamemanagers.assets
OFF_DELAY = 48
TARGETS = [
    ("MUSIC track title", os.path.join(DATA, "level13")),
    ("Ending List rows", os.path.join(DATA, "sharedassets21.assets")),
    ("DLC character list", os.path.join(DATA, "sharedassets24.assets")),
    ("section title", os.path.join(DATA, "StreamingAssets", "ui", "ui_jp")),
]


def serialized_files(env):
    """Các SerializedFile trong env: chính nó (.assets) hoặc các CAB trong bundle."""
    if isinstance(env.file, SerializedFile):
        return [env.file]
    return [f for f in env.file.files.values() if isinstance(f, SerializedFile)]


def autoscroll_objects(env):
    """[(sf, obj, raw)] của mọi MonoBehaviour AutoScrollText trong env."""
    found = []
    for sf in serialized_files(env):
        ext = [e.path for e in (sf.externals or [])]
        ggm_fid = ext.index("globalgamemanagers.assets") + 1 if "globalgamemanagers.assets" in ext else None
        local_ms = {o.path_id for o in sf.objects.values() if o.type.name == "MonoScript" and o.read().m_ClassName == "AutoScrollText"}
        for o in sf.objects.values():
            if o.type.name != "MonoBehaviour":
                continue
            raw = o.get_raw_data()
            if len(raw) != 60:
                continue
            fid, spid = struct.unpack_from("<iq", raw, 16)
            if (fid == 0 and spid in local_ms) or (ggm_fid is not None and fid == ggm_fid and spid == MS_AUTOSCROLL):
                found.append((sf, o, raw))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", type=float, default=None, help="startDelay mới (giây)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    for label, path in TARGETS:
        env = UnityPy.load(path)
        hits = autoscroll_objects(env)
        if not hits:
            raise SystemExit("%s: không thấy AutoScrollText" % path)
        is_bundle = isinstance(env.file, BundleFile)
        blob = open(path, "rb").read()
        print("%-20s %-34s %d AutoScrollText" % (label, os.path.relpath(path, ROOT), len(hits)))
        patched_offsets = []
        for sf, o, raw in hits:
            mode, delay, speed, pause = struct.unpack_from("<i3f", raw, 44)
            tgt = struct.unpack_from("<iq", raw, 32)
            line = "   pid %-4d targetText %s mode=%d startDelay=%g speed=%g pause=%g" % (o.path_id, tgt, mode, delay, speed, pause)
            if args.set is not None and abs(delay - args.set) > 1e-6:
                line += "  -> %g" % args.set
                new = raw[:OFF_DELAY] + struct.pack("<f", args.set) + raw[OFF_DELAY + 4:]
                if is_bundle:
                    o.set_raw_data(new)
                else:
                    start = o.byte_start
                    if blob[start:start + 60] != raw:
                        start += sf.header.data_offset
                    assert blob[start:start + 60] == raw, "không định vị được object %d trong file" % o.path_id
                    patched_offsets.append((start + OFF_DELAY, struct.pack("<f", args.set)))
            print(line)
        if args.set is None or not args.apply:
            continue
        if not patched_offsets and not is_bundle:
            print("   (đã đúng, không ghi)")
            continue
        before = hashlib.md5(blob).hexdigest()
        if is_bundle:
            out = env.file.save(packer="lz4")
            # đối chiếu: nạp lại, mọi object trừ AutoScrollText phải y nguyên
            # Đối chiếu trên BYTES, không qua file .tmp: UnityPy giữ handle file đã nạp tới khi GC,
            # nên os.replace() lên file đang mở bị Windows chặn (WinError 32, lần đầu 03/09).
            chk = UnityPy.load(blob)
            ref = {(i, o.path_id): o.get_raw_data() for i, sf_ in enumerate(serialized_files(chk)) for o in sf_.objects.values()}
            new_env = UnityPy.load(out)
            cur = {(i, o.path_id): o.get_raw_data() for i, sf_ in enumerate(serialized_files(new_env)) for o in sf_.objects.values()}
            assert ref.keys() == cur.keys(), "số object đổi"
            diff = [k for k in ref if ref[k] != cur[k]]
            sfs = serialized_files(env)
            want = {(sfs.index(sf_), o.path_id) for sf_, o, _ in hits}
            assert all(k in want for k in diff), "object khác ngoài AutoScrollText: %s" % diff
            for k in diff:
                assert struct.unpack_from("<f", cur[k], OFF_DELAY)[0] == struct.unpack("<f", struct.pack("<f", args.set))[0]
            del env, chk, new_env, hits
            import gc, time
            gc.collect()
            for attempt in range(10):
                try:
                    with open(path, "wb") as fh:
                        fh.write(out)
                    break
                except PermissionError:
                    time.sleep(1.0)              # OneDrive vừa chộp file để đồng bộ
            else:
                raise SystemExit("không ghi được %s — file đang bị giữ" % path)
            assert open(path, "rb").read() == out
            print("   đã ghi bundle: %d -> %d byte, %d object đổi (%s)" % (len(blob), len(out), len(diff), [k[1] for k in diff]))
        else:
            b = bytearray(blob)
            for off, val in patched_offsets:
                b[off:off + 4] = val
            open(path, "wb").write(bytes(b))
            chk = UnityPy.load(path)
            for sf, o, raw in hits:
                r2 = None
                for sf2 in [chk.file]:
                    r2 = sf2.objects[o.path_id].get_raw_data()
                assert r2[:OFF_DELAY] == raw[:OFF_DELAY] and r2[OFF_DELAY + 4:] == raw[OFF_DELAY + 4:]
                assert abs(struct.unpack_from("<f", r2, OFF_DELAY)[0] - args.set) < 1e-6
            print("   đã ghi %d byte tại chỗ, cỡ file giữ nguyên %d; md5 %s -> %s" % (4 * len(patched_offsets), len(blob), before, hashlib.md5(bytes(b)).hexdigest()))


main()
