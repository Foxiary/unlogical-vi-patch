# -*- coding: utf-8 -*-
r"""Dựng một slot save chỉ để soi lỗi ngắt dòng của tin nhắn chat trong BACKLOG.

Vì sao cần: backlog trong save **lưu nguyên văn lúc bấm save**, nên 36 slot sẵn có của
máy này đều mang chữ Nhật (lưu từ trước khi dịch) — mở BACKLOG lên không thấy được câu
tiếng Việt nào. Muốn so thì phải chơi tới đúng đoạn chat, mà mấy câu đáng xem lại nằm rải
rác ở nhiều chương.

Script chép slot `game_data20` (DATA 021) sang slot đích rồi ghi vào sáu dòng cuối của
backlog sáu tin nhắn chat thật, xếp theo bề ngang tăng dần.

**Máy này chốt đúng 36 slot** — thử dựng `game_data36` (DATA 037) thì màn LOAD không hiện,
nên phải ghi đè một slot có sẵn: `--slot=20` ghi đè chính DATA 021, tức vị trí truyện, cờ
và ảnh thu nhỏ đều giữ nguyên, chỉ sáu dòng cuối backlog là khác. Bản gốc nằm trong
`_backup\save-<ngày>\`.

Sáu dòng, đo ở font chat, ô 1210 px:

    #1  ~900 px @40    vừa ở cả hai cỡ                      ← đối chứng
    #2  1240 px @40 →   992 px @32    cỡ 40 ngắt, cỡ 32 vừa
    #3  1357 px @40 →  1085 px @32    cỡ 40 ngắt, cỡ 32 vừa
    #4  1425 px @40 →  1140 px @32    cỡ 40 ngắt, cỡ 32 vừa
    #5  1737 px @40 →  1390 px @32    ngắt ở CẢ HAI cỡ      ← cần vá dữ liệu
    #6  2832 px @40 →  2266 px @32    ngắt ở cả hai cỡ, nặng nhất

Ba dòng giữa là phần cỡ chữ chữa được; hai dòng cuối là phần chỉ ngắt dòng cứng trong
`ScenarioData` mới chữa được. Dòng đầu để biết trạng thái "đúng" trông ra sao.

So A/B: đổi qua lại hai bản `ui_jp` rồi khởi động lại game.

    copy _backup\ui_jp.prebacklogadvscale  romfs\Data\StreamingAssets\ui\ui_jp   (cỡ 40, trước khi vá)
    python tools\fix_backlog_adv_scale.py --apply                                (cỡ 32, sau khi vá)

Bố cục file save: gzip, bên trong là varint độ dài rồi JSON UTF-8, phần còn lại đệm 0x00.
Mỗi slot gồm `game_dataN` (dữ liệu, có `m_backLogData`) và `summary_dataN` (thẻ ở màn LOAD:
ngày giờ, playtime, ảnh thu nhỏ). Phải chép cả hai, và giữ đúng kích thước đệm của file gốc
(raw 4 MiB, file 251.658 byte) chứ không dùng hằng số 524288 của `fix_save_playername`.

    python tools\make_chatwrap_save.py            # xem trước, không ghi
    python tools\make_chatwrap_save.py --apply

Backup: cả thư mục save chép sang `_backup\save-<ngày>\` trước khi ghi.
"""
import gzip
import io
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_save_playername as S   # noqa: E402  (read/varint + đường dẫn save)

if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SAVE = S.SAVE
BASE = 20          # game_data20 = DATA 021, route Kai, ngay trước một đoạn chat
NEW = 36           # mặc định: slot mới = DATA 037 (đổi bằng --slot=N)
APPLY = "--apply" in sys.argv
for _a in sys.argv[1:]:
    if _a.startswith("--slot="):
        NEW = int(_a.split("=", 1)[1])

# (nhãn người gửi, chuỗi) — lấy nguyên văn từ ScenarioData
ROWS = [
    ("Suzuno@Sz_36iii", "Ừ tôi biết rồi."),
    ("RAN@ran_n_rea4", "Sợ bị hack lắm nên cậu cứ sao lưu dữ liệu cho chắc ăn nhé"),
    ("Unknown@73w35vq", "Tôi xin kiên quyết từ chối! Tôi sẽ rút lui nên nhờ các người đấy!"),
    ("Unknown@73w35vq", "Chúng tôi đã chuẩn bị tiền thù lao cho công việc Operator lần này."),
    ("RAN@ran_n_rea4", "Về cái email kỳ lạ tôi bảo hôm qua ấy. "
                      "Tôi vẫn chẳng nhớ là có liên quan gì không"),
    ("Kai Munakata@k_munakata2150", None),   # None = tự tìm dòng chat dài nhất trong ScenarioData
]


def widest_chat_line():
    """Tin nhắn chat rộng nhất trong ScenarioData, để làm ca nặng nhất."""
    import re
    import UnityPy
    UnityPy.config.FALLBACK_UNITY_VERSION = "2021.3.0f1"
    path = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
    sd = None
    for o in UnityPy.load(path).objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        if d.m_Name == "ScenarioData":
            x = d.m_Script
            sd = x if isinstance(x, str) else bytes(x).decode("utf-8", "ignore")
            break
    adv = {int(k): v for k, v in json.load(
        open(os.path.join(HERE, "_chat_advances.json"), encoding="utf-8")).items()}

    def w(s):
        return (sum(adv.get(ord(c), 58.0) for c in s) + 5.0 * len(s)) * 40.0 / 58.0

    def strip(s):
        s = re.sub(r"\[([^\[\]']*)'[^\[\]]*\]", r"\1", s)
        return re.sub(r"\[dic [^\]]*text=([^\]]*)\]", r"\1", s)

    best = ("", 0.0, "")
    for r in json.loads(sd.lstrip("﻿"))["target"]:
        tn, tx = r.get("talkName", []), r.get("text", [])
        for i, t in enumerate(tx):
            if not isinstance(t, str) or not t or i >= len(tn):
                continue
            nm = tn[i]
            if not (isinstance(nm, str) and "@" in nm):
                continue
            for line in strip(t).split("\n"):
                if w(line) > best[1]:
                    best = (line, w(line), nm.strip("【】"))
    return best


def write_like(path, obj, blob_len, raw_len):
    """Ghi lại đúng hình dạng file gốc: raw đệm tới raw_len, file đệm tới blob_len."""
    body = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    raw = S.varint(len(body)) + body
    if len(raw) > raw_len:
        raise ValueError("JSON dài hơn bộ đệm gốc")
    raw += b"\x00" * (raw_len - len(raw))
    blob = gzip.compress(raw, 9, mtime=0)
    if len(blob) > blob_len:
        raise ValueError("luồng gzip dài hơn file gốc")
    blob += b"\x00" * (blob_len - len(blob))
    with open(path, "wb") as f:
        f.write(blob)


def main():
    line, wide, who = widest_chat_line()
    rows = [(n, t if t is not None else line) for n, t in ROWS]
    rows[-1] = (who or rows[-1][0], line)

    print("Sáu dòng sẽ ghi vào cuối backlog của slot mới:")
    for i, (n, t) in enumerate(rows, 1):
        print("  #%d  %-28s %s" % (i, n, (t[:58] + "…") if len(t) > 58 else t))
    print("      (ca nặng nhất đo được %.0f px ở cỡ 40)" % wide)

    src_g = os.path.join(SAVE, "0", "game_data%d" % BASE)
    if not os.path.exists(src_g):
        print("không thấy", src_g)
        return 1
    blob, raw, off, obj = S.read(src_g)
    bl = json.loads(obj["m_backLogData"])
    used = [i for i in range(len(bl["text"])) if bl["text"][i] or bl["name"][i]]
    chat_idx = [i for i in used if bl["chat"][i]]
    print("\nslot nguồn: game_data%d — %d dòng backlog, %d dòng chat"
          % (BASE, len(used), len(chat_idx)))
    if not chat_idx:
        print("slot nguồn không có dòng chat nào để lấy mẫu — dừng")
        return 1
    tgt = used[-len(rows):]
    print("sẽ ghi đè các dòng %d–%d (sáu dòng cuối) trong bản CHÉP, slot gốc không đụng"
          % (tgt[0], tgt[-1]))

    if not APPLY:
        print("\n--apply để dựng slot DATA %03d (game_data%d + summary_data%d)"
              % (NEW + 1, NEW, NEW))
        return 0

    stamp = time.strftime("%Y%m%d")
    bak = os.path.join(ROOT, "_backup", "save-" + stamp)
    if not os.path.exists(bak):
        shutil.copytree(SAVE, bak)
        print("\nbackup cả thư mục save →", bak)

    src = chat_idx[-1]          # mẫu: một dòng chat có sẵn, chỉ thay text/name
    for sub in ("0", "1"):
        d = os.path.join(SAVE, sub)
        if not os.path.isdir(d):
            continue
        g_src, g_dst = os.path.join(d, "game_data%d" % BASE), os.path.join(d, "game_data%d" % NEW)
        s_src, s_dst = os.path.join(d, "summary_data%d" % BASE), os.path.join(d, "summary_data%d" % NEW)
        gb, graw, _, gobj = S.read(g_src)
        sb, sraw, _, sobj = S.read(s_src)

        j = json.loads(gobj["m_backLogData"])
        u = [i for i in range(len(j["text"])) if j["text"][i] or j["name"][i]]
        dst = u[-len(rows):]
        for slot, (nm, tx) in zip(dst, rows):
            for key in j:
                if isinstance(j[key], list) and len(j[key]) > max(slot, src):
                    j[key][slot] = j[key][src]
            j["text"][slot] = tx
            j["name"][slot] = nm
            j["chat"][slot] = True
            j["select"][slot] = False
            j["voice"][slot] = ""
        gobj["m_backLogData"] = json.dumps(j, ensure_ascii=False, separators=(",", ":"))
        gobj["m_saveText"] = "TEST ngat dong chat"
        sobj["m_saveText"] = "TEST ngat dong chat"

        write_like(g_dst, gobj, len(gb), len(graw))
        write_like(s_dst, sobj, len(sb), len(sraw))
        print("  [%s] đã ghi game_data%d + summary_data%d" % (sub, NEW, NEW))

    # đọc lại từ đĩa, đừng tin giá trị trong bộ nhớ
    _, _, _, chk = S.read(os.path.join(SAVE, "0", "game_data%d" % NEW))
    k = json.loads(chk["m_backLogData"])
    uu = [i for i in range(len(k["text"])) if k["text"][i] or k["name"][i]]
    print("\nđọc lại slot mới, sáu dòng cuối:")
    for i in uu[-len(rows):]:
        print("   chat=%s  %-28s %s" % (k["chat"][i], k["name"][i], k["text"][i][:56]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
