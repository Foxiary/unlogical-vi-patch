# -*- coding: utf-8 -*-
r"""Nhét sáu tin nhắn chat DÀI NHẤT vào cuối backlog của một save có sẵn, để soi bố cục.

Vì sao cần: backlog trong save lưu **nguyên văn lúc bấm save**, nên muốn xem một tin cụ
thể hiện ra sao thì hoặc phải chơi tới đúng chỗ, hoặc thay chữ trong save. Sáu tin nặng
nhất nằm rải rác ở bốn chương khác nhau, chơi tới đủ cả sáu là quá lâu.

## Bài học từ lần hỏng trước

Bản đầu (`make_chatwrap_save.py`) chép **nguyên một dòng mẫu** vào sáu ô rồi mới thay chữ,
nên sáu dòng mang cùng `scenario` / `line` / `block`. Game treo ở "Loading save data…" —
nhiều khả năng backlog dựng chỉ mục theo mấy trường đó và gặp khoá trùng. Tool này **chỉ
ghi đúng trường `text`** của những dòng vốn đã là dòng chat, mọi trường khác giữ nguyên,
nên không sinh khoá trùng.

## Ryujinx phải tắt hẳn

Emulator giữ cả thư mục save trong bộ nhớ và **ghi đè toàn bộ khi thoát** — đo được
30/08/2026: xoá `game_data36` lúc game đang chạy, tắt game xong file hiện về nguyên vẹn,
mọi file đóng dấu cùng một giây. Nên tool từ chối chạy nếu thấy tiến trình Ryujinx.

    python tools\make_longchat_save.py            # xem trước
    python tools\make_longchat_save.py --apply

Backup: `_backup\game_data<N>.prelongchat` (và bản trong thư mục `1`).
"""
import io
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_save_playername as S   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SLOT = 36                      # DATA 037 — save thật của người dùng ở đoạn chat PROLOGUE
APPLY = "--apply" in sys.argv
for a in sys.argv[1:]:
    if a.startswith("--slot="):
        SLOT = int(a.split("=", 1)[1])

MSGS = [
    ("RAN@ran_n_rea4",
     "Nghe bảo là bắt phụ giúp việc hậu trường gì đấy, bắt tôi đi sửa lỗi bug"),
    ("Unknown@73w35vq",
     "Đây là thông báo nhắc nhở về lời mời tham gia Stage 2 của Unlogical.\n"
     "Tin nhắn này được gửi đến những người\nchưa xác nhận đồng ý tham gia Stage 2."),
    ("yasaka@eggsand_yaa",
     "Rau củ hay nấm nói chung thì dù không thích nhưng tôi vẫn ăn được,\n"
     "riêng nấm lá sen thì chịu chết"),
    ("Suzuno@Sz_36iii",
     "Nhắc mới nhớ, do công việc nên em đang làm một cuộc khảo sát nhỏ"),
    ("Kai Munakata@k_munakata2150",
     "Nhưng mà nhắn tin cho em nhiều quá chắc anh Yuri mắng anh chết."),
    ("Unknown@73w35vq",
     "Cảm ơn bạn đã luôn hợp tác với Unlogical trong suốt thời gian qua."),
]


def ryujinx_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Ryujinx.exe"],
                             capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return False
    return "Ryujinx" in out


def write_like(path, obj, blob_len, raw_len):
    body = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    raw = S.varint(len(body)) + body
    if len(raw) > raw_len:
        raise ValueError("JSON dài hơn bộ đệm gốc")
    raw += b"\x00" * (raw_len - len(raw))
    import gzip
    blob = gzip.compress(raw, 9, mtime=0)
    if len(blob) > blob_len:
        raise ValueError("luồng gzip dài hơn file gốc")
    blob += b"\x00" * (blob_len - len(blob))
    with open(path, "wb") as f:
        f.write(blob)


def main():
    src = os.path.join(S.SAVE, "0", "game_data%d" % SLOT)
    if not os.path.exists(src):
        print("không thấy", src)
        return 1
    _, _, _, obj = S.read(src)
    j = json.loads(obj["m_backLogData"])
    tx, nm, ch = j["text"], j["name"], j["chat"]
    used = [i for i in range(len(tx)) if tx[i] or nm[i]]
    chat_rows = [i for i in used if ch[i]]
    print("slot DATA %03d: %d dòng backlog, %d dòng chat" % (SLOT + 1, len(used), len(chat_rows)))
    if len(chat_rows) < len(MSGS):
        print("slot này chỉ có %d dòng chat, cần %d — chọn slot khác bằng --slot=N"
              % (len(chat_rows), len(MSGS)))
        return 1
    target = chat_rows[-len(MSGS):]
    print("sẽ thay CHỮ của %d dòng chat cuối (chỉ trường text, giữ nguyên mọi trường khác):"
          % len(target))
    for i, (who, msg) in zip(target, MSGS):
        print("   [%d] %s  ->  %s" % (i, nm[i][:22], msg.split("\n")[0][:52]))

    if not APPLY:
        print("\n--apply để ghi")
        return 0
    if ryujinx_running():
        print("\nRyujinx ĐANG CHẠY — tắt hẳn rồi chạy lại.")
        print("Emulator giữ thư mục save trong bộ nhớ và ghi đè toàn bộ khi thoát,")
        print("ghi lúc này là mất trắng.")
        return 1

    for sub in ("0", "1"):
        p = os.path.join(S.SAVE, sub, "game_data%d" % SLOT)
        if not os.path.exists(p):
            continue
        bak = os.path.join(ROOT, "_backup", "game_data%d.prelongchat%s" % (SLOT, "" if sub == "0" else ".1"))
        if not os.path.exists(bak):
            shutil.copy(p, bak)
            print("backup ->", os.path.basename(bak))
        blob, raw, _, o = S.read(p)
        jj = json.loads(o["m_backLogData"])
        rows = [i for i in range(len(jj["text"])) if jj["text"][i] or jj["name"][i]]
        cr = [i for i in rows if jj["chat"][i]][-len(MSGS):]
        for i, (who, msg) in zip(cr, MSGS):
            jj["text"][i] = msg          # CHỈ trường này
        o["m_backLogData"] = json.dumps(jj, ensure_ascii=False, separators=(",", ":"))
        write_like(p, o, len(blob), len(raw))
        print("  [%s] đã ghi game_data%d" % (sub, SLOT))

    _, _, _, chk = S.read(os.path.join(S.SAVE, "0", "game_data%d" % SLOT))
    k = json.loads(chk["m_backLogData"])
    rows = [i for i in range(len(k["text"])) if k["text"][i] or k["name"][i]]
    print("\nđọc lại từ đĩa, sáu dòng cuối:")
    for i in rows[-len(MSGS):]:
        print("   chat=%s %-26s %s" % (k["chat"][i], k["name"][i][:24], k["text"][i].split("\n")[0][:50]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
