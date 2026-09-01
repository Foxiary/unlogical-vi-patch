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

## Nameplate nhân vật chính: HỌ + TÊN là mặc định bắt buộc

`【player】` vẽ họ + tên như bản Nhật (`涼乃環無` → `Suzuno Kanna`) và **phải giữ
như vậy**. Chỉ khi chuỗi đó không vừa khung 500 px mới được đổi sang
`【player_firstname】` để bỏ họ — đó là ngoại lệ vì tràn, không phải một cách viết
thay thế được chọn tuỳ ý.

Hiện có đúng ba chỗ dùng ngoại lệ, đều là plate ghép hai người:

    【player＆Kai】   522 px  →  【player_firstname＆Kai】   302 px
    【Kai＆player】   522 px  →  【Kai＆player_firstname】   302 px
    【player＆Ran】   545 px  →  【player_firstname＆Ran】   325 px

`Suzuno Kanna` một mình đã 390 px nên phần còn lại chỉ được 110, mà `＆Kai` cần
132 — đổi dấu nối cũng không cứu được (`&` 516, `+` 505, `, ` 503).

Luật này được canh **hai chiều**:

- `RENAMES` ép ba chỗ trên phải ở dạng đã đổi; merge sheet trả về `player` thì
  `--check` báo "chờ đổi" và `--apply` sửa lại.
- `surname_required()` bắt chiều ngược: plate nào dùng `player_firstname` mà dựng
  lại bằng `player` vẫn vừa khung thì là bỏ họ vô cớ, `--check` trả 1.

9.802 plate `【player】` còn lại giữ nguyên họ + tên: 390/500 px, và ngân sách cho
phần tên là 280,3 px nên mọi tên 6 ký tự thật đều lọt (`WILLOW` 226,3 rộng nhất
thử được). Cận trên `Suzuno WWWWWW` 519 px chỉ được **báo**, không chặn — xem
`worst_only()`.

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
    # Họ + tên không vừa khung 500 dù rút cách nào — `Suzuno Kanna` một mình đã
    # 390 px, phần còn lại chỉ được 110 mà `＆Kai` cần 132 (đổi ＆→& còn 516,
    # →+ còn 505, →", " còn 503). Nên bỏ họ, giữ tên: `player_firstname`.
    ("player＆Kai",                  "player_firstname＆Kai", 7, 7),
    ("Kai＆player",                  "Kai＆player_firstname", 2, 2),
    ("player＆Ran",                  "player_firstname＆Ran", 2, 2),
]
FIELDS = ("scriptText", "talkName")     # scriptText_Line là bản thô, KHÔNG đụng

CHAT = re.compile(r"\[chat (start|restart|stop|end)\]")
# `【player】` vẽ HỌ + TÊN, không phải mỗi tên: ảnh máy thật trong
# `fix_backlog_autosize` / `fix_backlog_select_label` đọc ra `Suzuno Kanna`.
# Đo bằng `Kanna` (170,6 px) là bỏ mất cả họ, 219,7 px.
#
# Tên lại do người chơi đặt, tối đa 6 ký tự Latin, nên có hai mốc, dùng vào hai việc:
#
#     Suzuno Kanna    390,3 px  vừa   <- mặc định; CHẶN gate, vì đây là cái chắc chắn
#                                        xảy ra với người chơi không đổi tên
#     Suzuno WWWWWW   518,7 px  GÃY   <- cận trên; chỉ BÁO. Ngân sách cho phần tên là
#                                        500 − 219,7 = 280,3 px và mọi tên 6 ký tự thật
#                                        đều lọt (`WILLOW` 226,3 là rộng nhất thử được);
#                                        chỉ tên toàn chữ rộng mới chạm. Bề rộng đó do
#                                        người chơi gõ, không sửa được ở phía dữ liệu.
PLAYER_NAME = adv_layout.PLAYER_SURNAME + " " + adv_layout.DEFAULT_PLAYER_NAME
PLAYER_NAME_WORST = adv_layout.PLAYER_FULL_MEASURE

# Khoá nameplate thứ hai: `【player_firstname】` vẽ MỖI TÊN RIÊNG, bỏ họ.
# Bằng chứng: literal `player_firstname` / `player_lastname` nằm ngay cạnh
# `player` trong `global-metadata.dat`, và `resources.assets` có đúng một
# `【player_firstname】` đứng ở vị trí nameplate trong một script của tổ viết.
# Dùng cho những plate mà họ + tên không vừa khung — xem bảng RENAMES.
GIVEN_KEY = "player_firstname"
PLAYER_GIVEN = adv_layout.DEFAULT_PLAYER_NAME
PLAYER_GIVEN_WORST = adv_layout.PLAYER_MEASURE


def width(s):
    """Bề rộng nameplate, px màn hình."""
    sc = NAME_SIZE / POINT_SIZE
    return sum(adv_layout.glyph_advance(c) * sc + NAME_CS for c in s)


def shown(tag, player=PLAYER_NAME, given=PLAYER_GIVEN):
    """Nửa được VẼ của 【khoá/hiển thị】; không có '/' thì vẽ cả chuỗi.

    `player_firstname` phải thay TRƯỚC `player`: nó chứa `player` làm tiền tố,
    thay ngược thứ tự thì ra `Suzuno Kanna_firstname`.
    """
    inner = tag.strip("【】")
    disp = inner.split("/", 1)[1] if "/" in inner else inner
    return disp.replace(GIVEN_KEY, given).replace("player", player)


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
    """{tag thô 【…】: [số ô ADV, số ô chat, [chỗ…]]} cho mọi nameplate.

    Khoá là tag THÔ chứ không phải chuỗi đã render: cùng một tag phải nhận dạng
    được qua nhiều mốc tên khác nhau, nếu không `worst_only` sẽ báo trùng lại
    đúng những tag mà `report` vừa chặn.
    """
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
                rec = out.setdefault(part, [0, 0, []])
                rec[1 if chat else 0] += 1
                if not chat and len(rec[2]) < 6:
                    rec[2].append("%d/%d" % (sid, i))
    return out


def surname_required(doc):
    """Luật: nameplate PHẢI là họ + tên như bản Nhật, chỉ bỏ họ khi tràn khung.

    Guard chiều ngược của `RENAMES`: bắt những plate đã đổi sang
    `player_firstname` mà đáng ra không cần — nếu dựng lại bằng `player` (họ +
    tên) vẫn vừa 500 px thì đó là bỏ họ vô cớ, phải trả về. Không có guard này
    thì `RENAMES` chỉ ép được một chiều: thêm bao nhiêu chỗ bỏ họ cũng lọt.
    """
    bad = []
    for tag, v in audit(doc).items():
        if GIVEN_KEY not in tag or not v[0]:
            continue
        full = tag.replace(GIVEN_KEY, "player")
        w = width(shown(full))
        if w <= NAME_BOX:
            bad.append((w, tag, v))
    if bad:
        print("")
        print("  BỎ HỌ VÔ CỚ — họ + tên vẫn vừa khung %.0f px, phải trả về `player`:"
              % NAME_BOX)
        for w, tag, v in sorted(bad, reverse=True):
            print("  %6.0f px  x%-4d %-34s %s"
                  % (w, v[0], shown(tag.replace(GIVEN_KEY, "player")), ", ".join(v[2])))
    return bad


def report(doc, title, player=PLAYER_NAME):
    print("\n%s — khung %.0f px, cỡ chữ %.1f px" % (title, NAME_BOX, NAME_SIZE))
    given = PLAYER_GIVEN_WORST if player is PLAYER_NAME_WORST else PLAYER_GIVEN
    rows = sorted(((width(shown(t, player, given)), t, v) for t, v in audit(doc).items()),
                  reverse=True)
    bad = [(w, k, v) for w, k, v in rows if w > NAME_BOX and v[0]]
    if not bad:
        widest = max((r for r in rows if r[2][0]), default=None)
        print("  0 nameplate ADV vượt khung" +
              ("  (rộng nhất: %.0f px  %s)" % (widest[0], shown(widest[1], player, given)) if widest else ""))
    for w, t, v in bad:
        print("  %6.0f px  x%-4d %-34s %s"
              % (w, v[0], shown(t, player, given), ", ".join(v[2])))
    skipped = [(w, k, v) for w, k, v in rows if w > NAME_BOX and not v[0] and v[1]]
    if skipped:
        print("  (bỏ qua %d tên chỉ dùng trong [chat] — widget khác: %s)"
              % (len(skipped), ", ".join(shown(t, player, given) for _w, t, _v in skipped[:4])))
    return bad


def worst_only(doc, blocking):
    """Nameplate chỉ tràn khi tên người chơi rộng bất thường — báo, KHÔNG chặn.

    Chặn ở đây thì gate đỏ vĩnh viễn mà không có gì sửa được: bề rộng ấy do người
    chơi gõ ra, nó không nằm trong `ScenarioData`. Cái chặn được là những nameplate
    đã tràn sẵn ở tên mặc định — `report()` lo phần đó.
    """
    seen = {t for _w, t, _v in blocking}
    rows = sorted(((width(shown(t, PLAYER_NAME_WORST, PLAYER_GIVEN_WORST)), t, v)
                    for t, v in audit(doc).items()),
                  reverse=True)
    extra = [(w, t, v) for w, t, v in rows if w > NAME_BOX and v[0] and t not in seen]
    if not extra:
        return
    print("")
    print("  chỉ tràn với tên rộng bất thường (%r — cận trên 6 ký tự) — không chặn:"
          % PLAYER_NAME_WORST)
    for w, t, v in extra:
        print("  %6.0f px  x%-4d %-34s %s"
              % (w, v[0], shown(t, PLAYER_NAME_WORST, PLAYER_GIVEN_WORST), ", ".join(v[2])))


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
        if width(shown("【%s】" % new)) > NAME_BOX:
            state = "TÊN MỚI VẪN TRÀN"
            ok = False
        print("%-30s %6.0f   %-22s %6.0f  %s"
              % (old, width(shown("【%s】" % old)), new,
                 width(shown("【%s】" % new)), state))
    if not ok:
        print("\ntình trạng file không như mong đợi — sheet vừa merge đè lên, hoặc bảng RENAMES sai")
        return 2

    before = report(doc, "SAU khi sửa" if not total else "TRƯỚC khi sửa")
    before = before + surname_required(doc)
    worst_only(doc, before)
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
    if report(doc2, "SAU khi sửa") or surname_required(doc2):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
