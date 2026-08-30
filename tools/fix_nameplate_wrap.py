# -*- coding: utf-8 -*-
"""Rút gọn nameplate ADV dài quá khung, làm tên xuống 2 hàng và tràn ra ngoài ô.

## Khung nameplate ADV

`level10` pid 650 / 699 (`Message(Normal|Highest)/Name`), rect **500 x 70**:

    m_fontSize           42       m_enableAutoSizing  0
    m_characterSpacing   5.5      m_lineSpacing       0
    m_enableWordWrapping 1        m_overflowMode      Overflow (0)

Auto-size TẮT, word-wrap BẬT, overflow để tràn — nên tên quá dài **không bị hạ cỡ
chữ**, nó xuống hàng rồi đổ ra ngoài ô, đè lên tranh nền. Mod chưa từng sửa hai
object này (byte khớp `UNLOGICAL_v2`); đây là hành vi sẵn có của game, bản dịch chỉ
là thứ chạm phải nó.

## Cỡ chữ đo từ máy thật, không lấy từ scene

Game chỉnh lại nameplate lúc chạy: ảnh `_2026-08-30_03-17-51.png` cho cỡ **~47,5 px**
chứ không phải 42, và gốc chữ nằm lệch trái 25 px so với rect. Nên mô hình ở đây hiệu
chuẩn thẳng từ ảnh — khớp vị trí 12 glyph của `Người quen của` với rms 0,6 px:

    bề rộng(px) = tổng(advance_glyph * 47.5/58 + 0.44)
    bước dòng   = 47.5 * 116/58 = 95 px    (đúng khoảng cách 2 hàng đo được)

Hai mốc cứng từ chính ảnh đó: `Người quen của Yuri` = 553 px **gãy**,
`Người quen của ` = 442 px **vừa**. `Himejima Kyosuke` = 495 px xuất hiện 423 lần và
chưa bao giờ gãy khi chơi → khung thật nằm trong [495, 553), tức đúng 500 của rect.

## Nameplate trong [chat] KHÔNG dùng ô này

289 ô có nameplate dạng tài khoản (`【Kai Munakata@k_munakata2150】` 893 px…) nằm trong
khối `[chat start] … [chat end]` và được vẽ bằng widget chat Genebark — khung rộng hơn
nhiều, cỡ chữ nhỏ hơn. Chơi thật không cái nào gãy. 15 ô trông như "ngoài chat" thực ra
nằm trong nhánh lựa chọn của một phiên chat mở từ trước lệnh `[next target=…]`, máy quét
tuyến tính không thấy `[chat start]`. Vì vậy `--check` phân loại chat/ADV và **chỉ chặn
vì tên trên nameplate ADV**.

## Mười tên đã rút gọn

| cũ | px | mới | px | n |
|---|---|---|---|---|
| `Giọng từ màn hình ngoài phố` | 778 | `Giọng từ màn hình` | 494 | 1 |
| `Người nước ngoài bí ẩn`      | 620 | `Người nước ngoài`  | 472 | 1 |
| `Đồng nghiệp của Yuri`        | 587 | `Đồng nghiệp`       | 343 | 2 |
| `Thanh niên đi đường`         | 555 | `Người đi đường`    | 408 | 2 |
| `Người quen của Yuri`         | 553 | `Người quen Yuri`   | 436 | 5 |
| `Sinh viên khoa khác`         | 545 | `SV khoa khác`      | 375 | 3 |
| `Màn hình ngoài phố`          | 530 | `Màn hình LED`      | 376 | 2 |
| `Munakata Kai＆Yuri`           | 527 | `Kai＆Yuri`          | 242 | 1 |
| `Các người tham gia`          | 525 | `Người tham gia`    | 408 | 6 |
| `Phụ nữ hàng xóm`             | 473 | `Nữ hàng xóm`       | 357 | 2 |

`街頭ビジョン` (84/128-129, chính màn hình phát bản tin) và `ナレーション/街頭ビジョンの声`
(117/0, lời dẫn trailer phát ra *từ* màn hình) là hai chuỗi khác nhau trong bản Nhật —
cặp `X` / `Giọng ... X`. Rút gọn vẫn giữ phân biệt đó. `Phụ nữ hàng xóm` 473 px vốn
chưa gãy, rút cho có biên.

`Giọng từ màn hình` 494 px chỉ dưới khung 6 px — mỏng ngang `Himejima Kyosuke`. Nếu
sau này thấy nó gãy trên máy thật thì hạ tiếp xuống `Giọng màn hình` (420 px).

Sau khi chạy: **0 nameplate ADV vượt khung**, rộng nhất còn lại là `Himejima Kyosuke`
495 px — chính cái đã chơi qua 423 lần không gãy, tức biên đo được xác nhận lại.

Ba chỗ mất sắc thái so với bản Nhật, cố ý đánh đổi lấy bề rộng — nếu sau này muốn
lấy lại thì phải nghĩ chữ ngắn hơn, đừng chỉ nối lại chữ cũ:

- `通行人の若者` (thanh niên) → `Người đi đường`, mất "trẻ", và gần trùng
  `Người qua đường` (`通りすがりの人`, 461 px, ×4) vốn là một nhân vật khác.
- `ユーリの同僚` → `Đồng nghiệp`, mất "của Yuri"; cùng chương còn
  `ユーリの仲間` → `Đồng đội của Yuri` (485 px) giữ nguyên, nên hai vai vẫn phân biệt được.
- `宗像 戒＆ユーリ` → `Kai＆Yuri`, bỏ họ. Các nameplate ghép khác đã dùng tên trơ
  (`Yuri＆Kai＆Soichi`, `Tobari＆Awayuki`) nên đây lại là nhất quán hơn.

    python tools\\fix_nameplate_wrap.py            # chạy thử / --check
    python tools\\fix_nameplate_wrap.py --apply
"""
import io
import json
import os
import re
import shutil
import sys

import UnityPy

if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import adv_layout                                        # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
BACKUP = os.path.join(ROOT, "_backup", "scenario01.nameplatewrap")
APPLY = "--apply" in sys.argv

# hình học đo từ ảnh máy thật, xem docstring
NAME_SIZE = 47.5
NAME_CS = 0.44
NAME_BOX = 500.0
POINT_SIZE = 58.0

# (nửa hiển thị cũ, mới, số chỗ chờ ở scriptText, ở talkName)
RENAMES = [
    ("Giọng từ màn hình ngoài phố", "Giọng từ màn hình", 1, 1),
    ("Người nước ngoài bí ẩn",      "Người nước ngoài",  1, 1),
    ("Màn hình ngoài phố",          "Màn hình LED",      2, 2),
    ("Các người tham gia",          "Người tham gia",    6, 6),
    ("Phụ nữ hàng xóm",             "Nữ hàng xóm",       2, 2),
    ("Đồng nghiệp của Yuri",        "Đồng nghiệp",       2, 2),
    ("Thanh niên đi đường",         "Người đi đường",    2, 2),
    ("Người quen của Yuri",         "Người quen Yuri",   5, 5),
    ("Sinh viên khoa khác",         "SV khoa khác",      3, 3),
    ("Munakata Kai＆Yuri",           "Kai＆Yuri",          1, 1),
]
FIELDS = ("scriptText", "talkName")     # scriptText_Line là bản thô, KHÔNG đụng

CHAT = re.compile(r"\[chat (start|restart|stop|end)\]")
PLAYER_NAME = "Kanna"                   # chỉ để ước lượng bề rộng của token player


def width(s):
    """Bề rộng nameplate, px màn hình."""
    sc = NAME_SIZE / POINT_SIZE
    return sum(adv_layout.glyph_advance(c) * sc + NAME_CS for c in s)


def shown(tag):
    """Nửa được VẼ của 【khoá/hiển thị】; không có '/' thì vẽ cả chuỗi."""
    inner = tag.strip("【】")
    return (inner.split("/", 1)[1] if "/" in inner else inner).replace("player", PLAYER_NAME)


def in_chat(lines, line_no):
    """Ô này có nằm trong màn chat Genebark không.

    Lệnh chat gần nhất phía TRƯỚC là start/restart, hoặc gần nhất phía SAU là
    end/stop.  Điều kiện thứ hai bắt các nhánh lựa chọn: `[next target=*…]` nhảy vào
    giữa một phiên chat nên phía trước nhánh không có `[chat start]` nào.
    """
    for k in range(min(line_no, len(lines) - 1), -1, -1):
        m = CHAT.search(lines[k])
        if m:
            if m.group(1) in ("start", "restart"):
                return True
            break
    for k in range(line_no, len(lines)):
        m = CHAT.search(lines[k])
        if m:
            return m.group(1) in ("end", "stop")
    return False


def load(path):
    env = UnityPy.load(path)
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            if data.m_Name == "ScenarioData":
                raw = data.m_Script
                if not isinstance(raw, str):
                    raw = bytes(raw).decode("utf-8")
                return env, data, raw
    raise SystemExit("không thấy ScenarioData trong %s" % path)


def count(doc, needle):
    """Số lần `needle` là nửa HIỂN THỊ — cả 【needle】 lẫn 【khoá/needle】."""
    tags = ("【" + needle + "】", "/" + needle + "】")
    out = {}
    for field in ("scriptText", "scriptText_Line", "talkName"):
        n = 0
        for target in doc["target"]:
            value = target[field]
            strings = [value] if isinstance(value, str) else value
            n += sum(s.count(t) for s in strings for t in tags)
        out[field] = n
    return out


def audit(doc):
    """{nửa hiển thị: [số ô ADV, số ô chat, [chỗ…]]} cho mọi nameplate."""
    out = {}
    for target in doc["target"]:
        sid = target["scenarioID"]
        lines = target["scriptText_Line"]
        loads = target["loadLine"]
        for i, cell in enumerate(target["talkName"]):
            if not cell:
                continue
            chat = in_chat(lines, loads[i] if i < len(loads) else 0)
            for part in cell.split(";"):
                part = part.strip()
                if not part.startswith("【"):
                    continue
                rec = out.setdefault(shown(part), [0, 0, []])
                rec[1 if chat else 0] += 1
                if not chat and len(rec[2]) < 6:
                    rec[2].append("%d/%d" % (sid, i))
    return out


def report(doc, title):
    print("\n%s — khung %.0f px, cỡ chữ %.1f px" % (title, NAME_BOX, NAME_SIZE))
    rows = sorted(((width(k), k, v) for k, v in audit(doc).items()), reverse=True)
    bad = [(w, k, v) for w, k, v in rows if w > NAME_BOX and v[0]]
    if not bad:
        widest = max((r for r in rows if r[2][0]), default=None)
        print("  0 nameplate ADV vượt khung" +
              ("  (rộng nhất: %.0f px  %s)" % (widest[0], widest[1]) if widest else ""))
    for w, k, v in bad:
        print("  %6.0f px  x%-4d %-34s %s" % (w, v[0], k, ", ".join(v[2])))
    skipped = [(w, k, v) for w, k, v in rows if w > NAME_BOX and not v[0] and v[1]]
    if skipped:
        print("  (bỏ qua %d tên chỉ dùng trong [chat] — widget khác: %s)"
              % (len(skipped), ", ".join(k for _w, k, _v in skipped[:4])))
    return bad


def main():
    env, asset, raw = load(BUNDLE)
    bom = "﻿" if raw.startswith("﻿") else ""
    doc = json.loads(raw.lstrip("﻿"))
    print("%s  %d target, %d ký tự" % (os.path.relpath(BUNDLE, ROOT), len(doc["target"]), len(raw)))

    print("\n%-30s %6s   %-22s %6s  %s"
          % ("cũ", "px", "mới", "px", "tình trạng"))
    ok = True
    total = 0
    for old, new, want_st, want_tn in RENAMES:
        co, cn = count(doc, old), count(doc, new)
        if co["scriptText"] == want_st and co["talkName"] == want_tn and not cn["talkName"]:
            state = "chờ đổi (%d+%d chỗ)" % (want_st, want_tn)
            total += want_st + want_tn
        elif not co["scriptText"] and not co["talkName"] \
                and cn["scriptText"] == want_st and cn["talkName"] == want_tn:
            state = "đã đổi"
        else:
            state = ("LỆCH — cũ %d/%d, mới %d/%d, chờ %d/%d"
                     % (co["scriptText"], co["talkName"],
                        cn["scriptText"], cn["talkName"], want_st, want_tn))
            ok = False
        if co["scriptText_Line"]:
            state = "CÓ Ở BẢN THÔ — không dám sửa"
            ok = False
        if width(new) > NAME_BOX:
            state = "TÊN MỚI VẪN TRÀN"
            ok = False
        print("%-30s %6.0f   %-22s %6.0f  %s"
              % (old, width(old), new, width(new), state))
    if not ok:
        print("\ntình trạng file không như mong đợi — sheet vừa merge đè lên, hoặc bảng RENAMES sai")
        return 2

    before = report(doc, "SAU khi sửa" if not total else "TRƯỚC khi sửa")
    if not total:
        print("\nkhông còn gì để đổi")
        return 1 if before else 0
    print("\ntổng %d chỗ sẽ đổi" % total)
    if not APPLY:
        print("CHẠY THỬ — thêm --apply để ghi")
        return 1 if before else 0

    done = 0
    for target in doc["target"]:
        for field in FIELDS:
            value = target[field]
            strings = [value] if isinstance(value, str) else value
            for i, s in enumerate(strings):
                new_s = s
                hits = 0
                for old, new, _st, _tn in RENAMES:
                    hits += new_s.count("【" + old + "】") + new_s.count("/" + old + "】")
                    new_s = new_s.replace("【" + old + "】", "【" + new + "】")
                    new_s = new_s.replace("/" + old + "】", "/" + new + "】")
                if new_s != s:
                    done += hits
                    if isinstance(value, str):
                        target[field] = new_s
                    else:
                        value[i] = new_s
    print("đã thay %d chỗ" % done)
    if done != total:
        raise SystemExit("thay %d chỗ, chờ %d — dừng, không ghi" % (done, total))

    out = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    if not os.path.exists(BACKUP):
        shutil.copy2(BUNDLE, BACKUP)
        print("backup ->", os.path.relpath(BACKUP, ROOT))
    asset.m_Script = bom + out
    asset.save()
    with open(BUNDLE, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi", os.path.relpath(BUNDLE, ROOT), os.path.getsize(BUNDLE), "byte")

    # --- đọc lại từ đĩa ---------------------------------------------------------
    _env2, _a2, back = load(BUNDLE)
    doc2 = json.loads(back.lstrip("﻿"))
    for old, new, _st, _tn in RENAMES:
        co, cn = count(doc2, old), count(doc2, new)
        if co["scriptText"] or co["talkName"]:
            raise SystemExit("còn %r sau khi ghi" % old)
        print("  %-30s -> %-22s scriptText %d, talkName %d"
              % (old, new, cn["scriptText"], cn["talkName"]))

    old_lines = [s for t in doc["target"] for s in t["scriptText_Line"]]
    new_lines = [s for t in doc2["target"] for s in t["scriptText_Line"]]
    if old_lines != new_lines:
        raise SystemExit("bản thô scriptText_Line bị đổi — khôi phục từ backup")
    print("  bản thô scriptText_Line: %d dòng, nguyên vẹn" % len(new_lines))
    for field in ("loadLine", "selLine"):
        a = [v for t in doc["target"] for v in t[field]]
        b = [v for t in doc2["target"] for v in t[field]]
        if a != b:
            raise SystemExit("%s bị đổi" % field)
    print("  loadLine / selLine: nguyên vẹn")
    report(doc2, "SAU khi sửa")
    return 0


if __name__ == "__main__":
    sys.exit(main())
