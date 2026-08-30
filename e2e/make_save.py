# -*- coding: utf-8 -*-
"""Dựng file save Ryujinx trỏ thẳng tới một nhãn trong script — để chụp ảnh thật.

Sinh ra vì muốn xem `[terinfo …]` hiện thế nào trên máy: chỗ đó nằm giữa chương 00_03,
chơi tay tới đó mất hàng giờ, mà cả 36 slot đều đang có save.

## Định dạng save

```
file 251 658 byte  =  luồng gzip  +  đệm \x00 tới hết
   gzip giải ra    =  varint(độ dài JSON) + JSON + đệm \x00
                      summary_data*: bộ đệm 32 768     game_data*: 1 048 576
```

`m_scenario` là **JSON lồng trong JSON** (chuỗi), giống `selText` của ScenarioData.

Vị trí phục hồi nằm ở ba chỗ phải khớp nhau, đặt lệch là game nhảy sai:

| trường | ý nghĩa |
|---|---|
| `m_scenario.file` / `.label` | script và nhãn |
| `m_loadblock` | **chỉ số** trong `ScenarioData.target[].loadLine` |
| `m_loadline` | chính là `loadLine[m_loadblock]` |

`loadLine` là danh sách dòng bắt đầu của từng "block" nạp được. Nhãn không tự nó là block,
nên phải lấy block cuối cùng **nằm trước hoặc bằng** dòng của nhãn.

    python e2e\\make_save.py --slot=3 --label=*PRO-03-15-02 --file=00_03.txt [--apply]

Luôn `--backup` trước khi ghi đè; script tự chụp cả thư mục save vào scratchpad.
"""
import gzip
import io
import json
import os
import re
import shutil
import sys
import zlib

if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import UnityPy   # noqa: E402

SCENARIO = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
JSONB = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
SAVE_ROOT = os.path.join(os.environ["APPDATA"], "Ryujinx", "bis", "user", "save",
                         "0000000000000001")
# PHẢI ghi cả `0` lẫn `1`. Đây là `DirectorySaveDataFileSystem` của LibHac: `0` là bản
# ĐÃ COMMIT, `1` là bản làm việc. Lúc mở save game chép `0` -> `1`, nên ghi mỗi `1` thì
# bản sửa bị bản cũ đè ngay khi vào game — trông y như "không thấy save đâu".
SAVE_DIRS = [os.path.join(SAVE_ROOT, d) for d in ("0", "1")]
BACKUP = os.path.join(os.environ.get("TEMP", "."), "unlogical-save-backup")


def arg(name, default=None):
    for a in sys.argv:
        if a.startswith("--%s=" % name):
            return a.split("=", 1)[1]
    return default


APPLY = "--apply" in sys.argv


def unpack(path):
    """file -> (dict, kích thước bộ đệm giải nén, kích thước file)"""
    raw = open(path, "rb").read()
    buf = zlib.decompressobj(31).decompress(raw)
    i, n, sh = 0, 0, 0
    while True:
        b = buf[i]
        n |= (b & 0x7F) << sh
        i += 1
        sh += 7
        if not b & 0x80:
            break
    return json.loads(buf[i:i + n].decode("utf-8")), len(buf), len(raw)


def varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def pack(doc, buf_size, file_size):
    """dict -> byte đúng kích thước file gốc.

    Giữ nguyên cả hai kích thước cố định: bộ đệm giải nén và độ dài file. Game cấp phát
    sẵn theo hằng số, ghi khác đi là nó đọc trượt.
    """
    body = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    inner = varint(len(body)) + body
    if len(inner) > buf_size:
        raise SystemExit("JSON %d byte > bộ đệm %d" % (len(inner), buf_size))
    inner += b"\x00" * (buf_size - len(inner))
    out = gzip.compress(inner, 9, mtime=0)
    if len(out) > file_size:
        raise SystemExit("gzip %d byte > kích thước file %d" % (len(out), file_size))
    return out + b"\x00" * (file_size - len(out))


def load_scenario():
    env = UnityPy.load(SCENARIO)
    sd = chap = None
    chaps = {}
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        r = d.m_Script
        s = r if isinstance(r, str) else bytes(r).decode("utf-8", "replace")
        if d.m_Name == "ScenarioData":
            sd = json.loads(s.lstrip("\ufeff"))
        else:
            chaps[d.m_Name] = s
    return sd, chaps


def locate(sd, chaps, fname, label, want_line=None):
    """(scenarioID, dòng nhãn, chỉ số block, dòng block) cho `label` trong `fname`.

    `want_line` cho phép nhắm sát hơn nhãn: nhãn gần nhất có thể cách lệnh cần xem hàng
    trăm dòng (`*PRO-03-14-02` cách `[terinfo]` 160 dòng ≈ 16 lượt bấm), trong khi
    `loadLine` có block dày hơn nhiều. Đặt block theo dòng thì vào gần như ngay lệnh.
    `label` vẫn ghi vào save — chưa rõ game phục hồi theo cái nào, đặt cả hai cho chắc.
    """
    name = fname[:-4] if fname.endswith(".txt") else fname
    if name not in chaps:
        raise SystemExit("không có asset chương %r" % name)
    lines = chaps[name].split("\n")
    hit = [i for i, l in enumerate(lines) if l.startswith(label)
           and re.match(re.escape(label) + r"[|\s]*$", l)]
    if not hit:
        raise SystemExit("không thấy nhãn %r trong %s" % (label, name))
    ln = hit[0]
    # target khớp theo SỐ DÒNG của scriptText_Line — asset chương có thêm dòng cuối rỗng.
    tgt = [t for t in sd["target"]
           if len(t.get("scriptText_Line") or []) in (len(lines), len(lines) - 1)]
    tgt = [t for t in tgt if label in t["scriptText"]]
    if len(tgt) != 1:
        raise SystemExit("khớp %d target cho %s (cần đúng 1)" % (len(tgt), name))
    t = tgt[0]
    ll = t["loadLine"] if isinstance(t["loadLine"], list) else json.loads(t["loadLine"])
    aim = ln if want_line is None else want_line
    if want_line is not None and want_line < ln:
        raise SystemExit("--line=%d nằm TRƯỚC nhãn (dòng %d)" % (want_line, ln))
    cand = [(i, v) for i, v in enumerate(ll) if v <= aim]
    if not cand:
        raise SystemExit("dòng %d nằm trước block đầu tiên (%d)" % (aim, ll[0]))
    bi, bl = cand[-1]
    return int(t["scenarioID"]), ln, bi, bl


def chapter_of(chaps, fname, label):
    """(chapter, routeNo, extraRouteNo) lấy từ ChapterData — KHÔNG chép từ save cũ.

    `00_02` có HAI mục ChapterData (`extraRouteNo` 0 và 1) còn `00_03` chỉ có một
    (extra=0). Dựng save cho 00_03 bằng cách chép slot 00_02 thì `extraRouteNo=1`
    theo sang, thành tổ hợp (chapter 3, route 0, extra 1) KHÔNG TỒN TẠI — game nạp ra
    cảnh khác hẳn. Nên phải tra lại, và chọn mục có nhãn muộn nhất còn đứng trước
    nhãn đích trong chính file script.
    """
    env = UnityPy.load(JSONB)
    cd = None
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        if d.m_Name == "ChapterData":
            r = d.m_Script
            cd = json.loads((r if isinstance(r, str) else bytes(r).decode("utf-8")).lstrip("\ufeff"))
            break
    name = fname[:-4] if fname.endswith(".txt") else fname
    rows = [it for g in cd["list"] for it in g["items"] if it["file"] == name]
    if not rows:
        raise SystemExit("ChapterData không có mục nào cho %r" % name)
    lines = chaps[name].split("\n")

    def line_of(lab):
        for i, l in enumerate(lines):
            if l.startswith(lab) and re.match(re.escape(lab) + r"[|\s]*$", l):
                return i
        return -1

    aim = line_of(label)
    cand = [(line_of(it["label"]), it) for it in rows]
    cand = [(ln, it) for ln, it in cand if 0 <= ln <= aim]
    if not cand:
        raise SystemExit("không mục ChapterData nào của %s đứng trước %s" % (name, label))
    ln, it = max(cand, key=lambda x: x[0])
    print("   ChapterData: %d mục cho %s, chọn mục nhãn %s (dòng %d)  -> chapter=%s "
          "route=%s extra=%s" % (len(rows), name, it["label"], ln,
                                 it["chapterNo"], it["routeNo"], it["extraRouteNo"]))
    return it["chapterNo"], it["routeNo"], it["extraRouteNo"]


def main():
    slot = int(arg("slot", "3"))
    fname = arg("file", "00_03.txt")
    label = arg("label")
    chapter = arg("chapter")
    if not label:
        raise SystemExit("thiếu --label=*PRO-03-15-02")

    want = arg("line")
    sd, chaps = load_scenario()
    sid, ln, bi, bl = locate(sd, chaps, fname, label, int(want) if want else None)
    print("%s %s  ->  sID %d, dòng nhãn %d, block[%d] = dòng %d%s"
          % (fname, label, sid, ln, bi, bl,
             ("  (nhắm dòng %s, cách %d dòng)" % (want, int(want) - bl)) if want else ""))

    ch, rt, ex = chapter_of(chaps, fname, label)

    if not os.path.isdir(BACKUP):
        shutil.copytree(SAVE_ROOT, BACKUP)
        print("backup toàn bộ save -> %s" % BACKUP)
    else:
        print("backup đã có -> %s" % BACKUP)

    for sdir in SAVE_DIRS:
        print("\n--- %s" % sdir)
        edit_slot(sdir, slot, fname, label, (ch, rt, ex), bl, bi)


def edit_slot(sdir, slot, fname, label, chrt, bl, bi):
    for kind in ("game_data", "summary_data"):
        p = os.path.join(sdir, "%s%d" % (kind, slot))
        if not os.path.exists(p):
            print("   %s%d không có — bỏ qua" % (kind, slot))
            continue
        doc, buf, fsz = unpack(p)
        sc = json.loads(doc["m_scenario"])
        print("\n%s%d  hiện: %s %s (chapter %s)  loadline=%s block=%s"
              % (kind, slot, sc["file"], sc["label"], sc.get("chapter"),
                 doc.get("m_loadline"), doc.get("m_loadblock")))
        sc["file"] = fname
        sc["label"] = label
        sc["prevLabel"] = ""
        sc["chapter"], sc["scenarioRoute"], sc["extraRouteNo"] = chrt
        # nhãn đích phải nằm trong danh sách đã đi qua, không thì game coi là chưa mở
        vis = sc.get("visitedLabels")
        if isinstance(vis, list) and label not in vis:
            vis.append(label)
        doc["m_scenario"] = json.dumps(sc, ensure_ascii=False, separators=(",", ":"))
        doc["m_loadline"] = bl
        doc["m_loadblock"] = bi
        doc["m_isSelect"] = False
        doc["m_SelectType"] = -1
        doc["m_saveText"] = label
        print("   %s%d mới : %s %s  loadline=%d block=%d"
              % (kind, slot, sc["file"], sc["label"], bl, bi))
        if APPLY:
            blob = pack(doc, buf, fsz)
            open(p, "wb").write(blob)
            back, _, _ = unpack(p)
            assert json.loads(back["m_scenario"])["label"] == label
            assert back["m_loadblock"] == bi
            print("      đã ghi %d byte, đọc lại khớp" % len(blob))

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")


if __name__ == "__main__":
    main()
