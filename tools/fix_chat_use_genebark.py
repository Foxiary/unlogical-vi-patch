# -*- coding: utf-8 -*-
"""Chat rendered in the ADV scene takes the Genebark app's wording.

Nội dung chat Genebark nằm ở **hai asset**, mỗi bên dịch độc lập:

    GenebarkChatMainData.data[N].content   app chat trong Genebark
    ScenarioData.text[j]                   cùng tin nhắn đó, hiện trong cảnh ADV

Trong 184 cặp có bản Nhật **duy nhất ở cả hai bên**, 177 cặp hai bản dịch khác nhau
(15 cặp viết lại hẳn, 156 khác chữ, 6 chỉ khác dấu). Sheet cũng lệch đúng 177/7 nên
đây là chuyện dịch upstream, không phải merge. Người dùng chốt: **lấy bản Genebark**.

## Vì sao bản Genebark là bản đúng

Cả 177 ô ADV đều có nameplate dạng tài khoản (`【Kai Munakata@k_munakata2150】`,
`【Suzuno@Sz_36iii】`, …) — **177/177 có `@`** — nên chúng là tin nhắn chat, không phải
lời nói. Và **0/177 ô bản Nhật có 「」**. Bản Genebark viết giọng chat (ngắn hơn ở
119/171 cặp, thường không dấu chấm cuối); bản ADV viết đầy đủ có dấu câu, tức lệch khỏi
chính thứ nó đang mô phỏng.

Ba ô mà chốt chặn thông thường sẽ chặn, và cả ba đều cho thấy bản ADV mới là bản sai:

| ô | bản ADV | bản Nhật |
|---|---|---|
| `15/txt/0081` | làm rơi token `[主人公]`, thay bằng "em" | `俺が直接[主人公]の家に行こうか？` **có** token |
| `115/txt/0253` | tự thêm `「」` | `怪我はだいぶ良くなってきたよ` không có ngoặc |
| `115/txt/0254` | tự thêm `「」` | không có ngoặc |

Nên chốt chặn ở đây **cho phép bản mới THÊM tag/token**, chỉ chặn khi nó *làm mất* thứ
bản cũ đang có. Và ngoặc `「」` chỉ bị đòi khi bản Nhật có.

## Ngắt dòng: ghi PHẲNG rồi để `fix_adv_wrap` lo

Không dùng `carry_breaks` ở đây. 15 cặp viết lại hẳn (giống nhau < 50%), mà difflib đặt
lại ngắt dòng theo *offset ký tự cũ* — vô nghĩa khi câu đã khác hẳn (đúng lớp lỗi đã làm
note id9 gãy thành `Tổng hợp lời / nhạc ・ Đặt phòng…`). Ngắt dòng của bản Genebark thì
cũng bỏ, nhưng **không phải vì hai khung khác nhau** — bản đầu của docstring này viết
"nó ngắt cho bong bóng chat, không phải cho khung ADV 1280", và đó là SAI: ghép 1:1 theo
bản Nhật đã làm phẳng ra 184 cặp, **cả 184 ngắt dòng giống hệt nhau, 0 cặp khác** (đo lại
28/08/2026). Bản Nhật dùng đúng một bố cục ngắt dòng cho cả `Message_TMP` rộng 1210 lẫn ô
thoại ADV rộng 1280. Lý do thật để ghi phẳng chỉ còn là **quyền sở hữu**: việc đặt ngắt
dòng thuộc `fix_jp_sentence_break.py` (soi theo ranh giới câu bản Nhật) và `fix_adv_wrap`
— hai tool cùng ghi một ô là nguồn lỗi. `fix_jp_sentence_break.py` cũng đã thêm chốt bỏ
qua ô chat (nhận diện bằng `talkName` có `@`, 289 ô) đúng vì lẽ đó.

Nên: ghi chữ phẳng, rồi chạy `python tools\\fix_adv_wrap.py --apply` — nó đã hiệu chỉnh
sẵn cho khung ADV (`CAPS` từng dòng, `BOX_H`) và tự mirror sang `scriptText`.
`check_layout_breaks` sẽ báo mất ngắt dòng ở bước giữa; đó là đúng, đo lại sau khi wrap.

    python tools\\fix_chat_use_genebark.py [--apply] [--report]
    python tools\\fix_adv_wrap.py --apply        # bước 2, bắt buộc
"""
import collections
import io
import json
import os
import re
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402

SCENARIO = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
JSONB = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "json", "json")
STOCK = r"D:\Downloads\UNLOGICAL_v2\Data\StreamingAssets"
BACKUP = os.path.join(ROOT, "_backup", "scenario01.chatgenebark")

APPLY = "--apply" in sys.argv
REPORT = "--report" in sys.argv

TAG = re.compile(r"\[[^\[\]\n]*\]")


def flat(s):
    return re.sub(r"[ \t\u3000]*\n[ \t\u3000]*", " ", s or "").strip()


def load_text(path, name):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name == "TextAsset":
            d = o.read()
            if d.m_Name == name:
                raw = d.m_Script
                if not isinstance(raw, str):
                    raw = bytes(raw).decode("utf-8")
                return env, d, raw
    raise SystemExit("không thấy %s trong %s" % (name, path))


def guards(old, new, jp):
    """Cho phép THÊM tag/token, chỉ chặn khi làm MẤT."""
    bad = []
    if not new.strip():
        bad.append("bản mới trống")
    lost = collections.Counter(TAG.findall(old)) - collections.Counter(TAG.findall(new))
    if lost:
        bad.append("mất tag %s" % sorted(lost.elements()))
    for a, b in (("\u300c", "\u300d"), ("\u300e", "\u300f")):
        # Chặn khi bản Nhật CÓ, bản cũ CÓ, mà bản mới mất — ba điều kiện cùng lúc, vì
        # hai hướng sai ngược nhau đều thật:
        #  - 115/txt/0253-0254: bản ADV tự THÊM ngoặc mà bản Nhật không có -> bỏ là đúng.
        #  - 86/txt/0021, 110/txt/0215: bản Nhật có ngoặc kép Nhật nhưng CẢ HAI bản dịch
        #    đều dùng dấu " theo quy ước dấu câu -> không mất gì, chặn là chặn oan.
        if a in jp and a in old and a not in new:
            bad.append("mất ngoặc %s mà bản Nhật lẫn bản cũ đều có" % a)
        if new.count(a) != new.count(b):
            bad.append("ngoặc %s%s không cân" % (a, b))
    if new.count('"') % 2:
        bad.append('số dấu " lẻ')
    return bad


def pairs():
    """Cặp 1:1 theo bản Nhật, và chỉ nhận tin nhắn chat thật."""
    _, _, sj_raw = load_text(os.path.join(STOCK, "json", "json"), "GenebarkChatMainData")
    _, _, ss_raw = load_text(os.path.join(STOCK, "scenario", "scenario01"), "ScenarioData")
    sj = json.loads(sj_raw.lstrip("\ufeff"))["data"]
    ss = json.loads(ss_raw.lstrip("\ufeff"))

    jcnt = collections.Counter((r.get("content") or "") for r in sj)
    scnt = collections.Counter()
    pos = {}
    for e in ss["target"]:
        for i, s in enumerate(e.get("text") or []):
            if isinstance(s, str) and s:
                scnt[s] += 1
                pos.setdefault(s, (e["scenarioID"], i))
    out = []
    for k, r in enumerate(sj):
        jp = r.get("content") or ""
        if jcnt[jp] != 1 or scnt.get(jp) != 1:
            continue
        sid, i = pos[jp]
        out.append((k, sid, i, jp))
    return out


def main():
    env_s, d_s, raw_s = load_text(SCENARIO, "ScenarioData")
    data = json.loads(raw_s.lstrip("\ufeff"))
    ti_of = {t["scenarioID"]: n for n, t in enumerate(data["target"])}
    _, _, bj_raw = load_text(JSONB, "GenebarkChatMainData")
    bj = json.loads(bj_raw.lstrip("\ufeff"))["data"]

    todo, stat = [], collections.Counter()
    for k, sid, i, jp in pairs():
        ti = ti_of[sid]
        e = data["target"][ti]
        old = (e["text"] or [])[i] or ""
        gen = bj[k].get("content") or ""
        new = flat(gen)
        if flat(old) == new:
            stat["đã giống"] += 1
            continue
        nm = ((e.get("talkName") or [""] * (i + 1))[i] or "")
        if "@" not in nm:
            stat["BỎ: nameplate không phải tài khoản chat"] += 1
            continue
        if jp.lstrip().startswith("\u300c"):
            stat["BỎ: bản Nhật là lời nói (có 「)"] += 1
            continue
        bad = guards(old, new, jp)
        if bad:
            stat["BỎ: chốt chặn"] += 1
            print("!! %d/txt/%04d  %s" % (sid, i, "; ".join(bad)))
            print("      cũ : %r" % old[:88])
            print("      mới: %r" % new[:88])
            continue
        todo.append((ti, sid, i, old, new))
        stat["sẽ đổi"] += 1

    print("cặp 1:1 theo bản Nhật: %d" % len(pairs()))
    for key in sorted(stat):
        print("   %-40s %d" % (key, stat[key]))
    nl_before = sum(old.count("\n") for _, _, _, old, _ in todo)
    print("\nngắt dòng cứng trong %d ô sẽ bị bỏ ở bước này: %d  "
          "(fix_adv_wrap dựng lại ở bước 2)" % (len(todo), nl_before))

    if REPORT:
        for ti, sid, i, old, new in todo[:200]:
            print("\n-> %d/txt/%04d" % (sid, i))
            print("   cũ : %r" % old.replace("\n", "\u23ce")[:96])
            print("   mới: %r" % new[:96])
    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return
    if not todo:
        return

    out = raw_s
    enc_a = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))  # noqa: E731
    enc_s = lambda x: json.dumps(x, ensure_ascii=False)                        # noqa: E731

    # text[]: vá theo CẢ MẢNG, không theo chuỗi — có tin nhắn trùng nhau từng chữ.
    for ti in sorted({t[0] for t in todo}):
        arr_old = list(data["target"][ti]["text"])
        arr_new = list(arr_old)
        for t2, sid, i, old, new in [t for t in todo if t[0] == ti]:
            assert arr_new[i] == old, "text[%d] không như đã đọc" % i
            arr_new[i] = new
        oj, nj = enc_a(arr_old), enc_a(arr_new)
        if out.count(oj) != 1:
            raise SystemExit("mảng text[] của target[%d] khớp %d lần" % (ti, out.count(oj)))
        out = out.replace(oj, nj)

    # scriptText: bản sao không được vẽ, nhưng giữ đồng bộ để khỏi lệch thêm.
    mirrored = failed = 0
    for ti in sorted({t[0] for t in todo}):
        script = cur = data["target"][ti]["scriptText"]
        for t2, sid, i, old, new in [t for t in todo if t[0] == ti]:
            lines, ol = cur.split("\n"), old.split("\n")
            hits = [k for k in range(len(lines) - len(ol) + 1) if lines[k:k + len(ol)] == ol]
            if len(hits) == 1:
                lines[hits[0]:hits[0] + len(ol)] = new.split("\n")
                cur = "\n".join(lines)
                mirrored += 1
            else:
                failed += 1
        if cur != script:
            oj, nj = enc_s(script), enc_s(cur)
            if out.count(oj) != 1:
                raise SystemExit("scriptText target[%d] khớp %d lần" % (ti, out.count(oj)))
            out = out.replace(oj, nj)
    print("scriptText: mirror %d, bỏ %d (khớp != 1 lần)" % (mirrored, failed))

    bak = BACKUP
    n = 2
    while os.path.exists(bak):
        bak = "%s-%d" % (BACKUP, n)
        n += 1
    shutil.copy2(SCENARIO, bak)
    print("backup ->", bak)
    d_s.m_Script = ("\ufeff" if raw_s.startswith("\ufeff") else "") + out.lstrip("\ufeff")
    d_s.save()
    with open(SCENARIO, "wb") as f:
        f.write(env_s.file.save(packer="lz4"))
    print("đã ghi", SCENARIO, os.path.getsize(SCENARIO))

    # đọc lại từ disk
    _, _, back = load_text(SCENARIO, "ScenarioData")
    db = json.loads(back.lstrip("\ufeff"))
    for ti, sid, i, old, new in todo:
        got = db["target"][ti]["text"][i]
        assert got == new, "đọc lại %d/txt/%d sai: %r" % (sid, i, got)
    for a, b in zip(data["target"], db["target"]):
        for fld in ("text", "talkName", "selText", "scriptText_Line", "loadLine"):
            x, y = a.get(fld), b.get(fld)
            if isinstance(x, list) and len(x) != len(y):
                raise SystemExit("sID %s %s: độ dài mảng đổi" % (a["scenarioID"], fld))
    print("đọc lại: %d ô khớp, độ dài mọi mảng không đổi" % len(todo))
    print("\nBƯỚC 2 bắt buộc: python tools\\fix_adv_wrap.py --apply")


main()
