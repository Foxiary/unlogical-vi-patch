# -*- coding: utf-8 -*-
r"""Soi ô sheet MẤT DẤU CÂU CUỐI — lớp lỗi của `90/txt/0433` (`「えっ」` -> `「Hả」`).

Bản Nhật bỏ `。` trước `」` là **quy ước của tiếng Nhật**, không phải tín hiệu. Quy ước
của bản dịch thì ngược lại, và đo được: trong 15.132 ô mà bản Nhật kết trần,
**13.796 ô (91,2%) bản Việt vẫn thêm `.` / `?` / `!`**. 1.336 ô còn lại là ngoại lệ —
đúng lớp lỗi cần bắt. Chiều ngược lại gần như tuyệt đối: bản Nhật kết bằng `。！？` thì
22.740/22.743 ô bản Việt cũng có dấu.

Vì vậy tool KHÔNG so với bản Nhật. Nó chỉ hỏi một câu: chữ cuối của ô tiếng Việt, sau khi
gỡ tag và gỡ ngoặc đóng, có phải dấu kết câu không.

**Chỉ soi `sd_*` hàng `N/txt/NNNN`.** Mọi field nhãn/tiêu đề đều kết trần 100% theo thiết
kế — `dic_title` 80/80, `ss_title` 20/20, `rule_title` 21/21, `prof_name` 14/14,
`skill_name` 10/10, `qa_title` 45/50, `alert` 84/86, `rule_body` (mục tiêu vòng chơi,
dạng gạch đầu dòng) 14/39 — đưa vào là chôn 1.339 ô thật dưới ~2.500 ô nhiễu. Hàng
`/cmd/` và `/sel/` cũng là nhãn UI ("New　Chat", "Xác thực thành công"), cùng lý do.

`GenebarkChatMainData/chat` để riêng sau cờ `--chat`: 489/1194 ô kết trần (41%) — tin
nhắn SNS bỏ dấu chấm là văn phong, không phải lỗi, nên đừng trộn vào danh sách chính.

    python tools\check_sheet_end_punct.py
    python tools\check_sheet_end_punct.py --csv=out.csv
    python tools\check_sheet_end_punct.py --sheet="D:\Downloads\UNLOGICAL_v2 (53).xlsx"
    python tools\check_sheet_end_punct.py --chat
"""
import collections
import csv
import glob
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from openpyxl import load_workbook   # noqa: E402

SNAPSHOTS = r"D:\Downloads\UNLOGICAL_v2*.xlsx"
TAG = re.compile(r"\[[^\[\]\n]*\]")
SD_ID = re.compile(r"^(\d+)/txt/(\d+)$")
URL = re.compile(r"https?://\S*$")

# Ngoặc đóng thì gỡ trước khi xét chữ cuối: dấu câu đứng TRONG ngoặc (`…rồi.」`), nên
# xét thẳng ký tự cuối chuỗi là mọi ô thoại đều "có dấu" vì `」`.
CLOSE = "」』\"'）)>》〉»” 　\n\t"

# `―` và `~ ～ ー` là kết câu hợp lệ (câu bỏ lửng / kéo dài) — xem memory
# `unlogical-punctuation-conventions`: 1.289 ô kết bằng `―`, 89 ô bằng `~ ～`.
# `▽` là mũi tên "còn tiếp" của màn hình. `、。！？` lọt vào đây là lỗi KHÁC (dấu Nhật
# còn sót), đã có pass riêng — ở tool này chỉ coi là "có dấu" để khỏi báo trùng.
END_OK = set(".?!―—~～ー…、。！？▽◆▼:;,*")


def arg(name, default=None):
    for a in sys.argv:
        if a.startswith("--%s=" % name):
            return a.split("=", 1)[1]
    return default


def newest():
    c = sorted(glob.glob(SNAPSHOTS), key=os.path.getmtime, reverse=True)
    if not c:
        raise SystemExit("không thấy snapshot nào khớp " + SNAPSHOTS)
    return c[0]


def tail(s):
    """Chữ cuối có nghĩa: gỡ tag, đổi U+3000 thành space, gỡ ngoặc đóng và khoảng trắng."""
    return TAG.sub("", s).replace("\u3000", " ").strip().rstrip(CLOSE)


def has_end(s):
    t = tail(s)
    return (not t) or t[-1] in END_OK or bool(URL.search(t))


def form(v, spk=""):
    """Ba nhóm, vì ba nhóm cần ba cách xử:

    - `thoại` / `độc thoại` — câu thoại trong `「」` hay `()`. **Lỗi thật**, 1.166 ô.
    - `SNS` — người nói có `@handle`: tin nhắn trong kịch bản. Bỏ dấu chấm là văn
      phong chat, giống `GenebarkChatMainData/chat` — người đọc quyết, 117 ô.
    - `dẫn truyện` — 56 ô còn lại, phần lớn là **nhãn chứ không phải câu**: tiêu đề tin
      tức, tên người trên tài liệu, `▽ Ngày thứ N`, dòng `☆☆ Phần thưởng ☆☆`. Xem
      bằng mắt, đừng sửa hàng loạt.
    """
    if "@" in (spk or ""):
        return "SNS"
    s = TAG.sub("", v).strip()
    if s.startswith("「"):
        return "thoại"
    if s.startswith(("(", "（")):
        return "độc thoại"
    return "dẫn truyện"


def main():
    path = arg("sheet") or newest()
    print("sheet: %s\n" % path)
    wb = load_workbook(path, read_only=True, data_only=True)

    hits, per = [], collections.defaultdict(lambda: [0, 0])
    chat_hits, chat_tot = [], 0
    for ws in wb.worksheets:
        sd = ws.title.startswith("sd_")
        is_chat = ws.title.startswith("GenebarkChatMainData")
        if not sd and not is_chat:
            continue
        vcol, jcol = (3, 2) if sd else (2, 1)
        for r in ws.iter_rows(values_only=True):
            if not r or not isinstance(r[0], str):
                continue
            key = r[0].strip()
            v = r[vcol] if len(r) > vcol and isinstance(r[vcol], str) else ""
            jp = r[jcol] if len(r) > jcol and isinstance(r[jcol], str) else ""
            if not v.strip():
                continue
            if is_chat:
                if not key.startswith("GenebarkChatMainData/chat/"):
                    continue     # `/spk/` là tên người gửi — nhãn, kết trần 1194/1194
                chat_tot += 1
                if not has_end(v):
                    chat_hits.append((key, "@chat", jp, v))
                continue
            if not SD_ID.match(key):
                continue         # `/cmd/`, `/sel/`: nhãn UI
            spk = r[1] if isinstance(r[1], str) else ""
            per[ws.title][0] += 1
            if has_end(v):
                continue
            per[ws.title][1] += 1
            hits.append((key, spk, jp, v))
    wb.close()

    tot = sum(a[0] for a in per.values())
    print("%-8s %7s %7s %7s" % ("tab", "tổng", "thiếu", "%"))
    for t in sorted(per):
        n, b = per[t]
        if b:
            print("%-8s %7d %7d %6.1f%%" % (t, n, b, 100.0 * b / n))
    print("%-8s %7d %7d %6.1f%%" % ("TỔNG", tot, len(hits), 100.0 * len(hits) / max(tot, 1)))

    kinds = collections.Counter(form(h[3], h[1]) for h in hits)
    print("\ndạng: " + ", ".join("%s %d" % (k, n) for k, n in kinds.most_common()))

    if "--chat" in sys.argv:
        print("\nGenebarkChatMainData/chat: %d/%d ô kết trần (%.0f%%) — VĂN PHONG SNS, "
              "không tính là lỗi" % (len(chat_hits), chat_tot,
                                     100.0 * len(chat_hits) / max(chat_tot, 1)))
        hits += chat_hits

    out = arg("csv")
    if out:
        with open(out, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ID", "Speaker", "Japanese", "Vietnamese", "Dạng"])
            for key, spk, jp, v in hits:
                w.writerow([key, spk, jp, v, form(v, spk)])
        print("\n-> %s (%d hàng)" % (out, len(hits)))

    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
