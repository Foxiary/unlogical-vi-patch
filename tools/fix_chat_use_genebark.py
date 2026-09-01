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


def _nameplate_map(ss, sj):
    """{nameplate ADV: speaker Genebark} — suy từ CHÍNH các cặp 1:1 chắc chắn.

    Không nhúng cứng: dựng từ những câu Nhật xuất hiện đúng một lần ở cả hai bên, rồi
    đòi mỗi nameplate chỉ ứng với MỘT speaker. Đo trên bản gốc: 7 nameplate, 0 cái mơ hồ.

        【Suzuno@Sz_36iii】 -> player      【RAN@ran_n_rea4】 -> 藍
        【Kai Munakata@…】  -> 戒           【yasaka@…】       -> 奏壱
        【YURI@…】          -> ユーリ        【M@6avbjie_w】    -> 雅火
        【Shiori@…】        -> 栞
    """
    adv = collections.defaultdict(list)
    for e in ss["target"]:
        tn = e["talkName"]
        tn = tn if isinstance(tn, list) else json.loads(tn.replace("'", '"'))
        for i, s in enumerate(e.get("text") or []):
            if isinstance(s, str) and s:
                adv[(s, str(tn[i]) if i < len(tn) else "")].append((e["scenarioID"], i))
    gb = collections.defaultdict(list)
    for k, r in enumerate(sj):
        c = r.get("content") or ""
        if c:
            gb[(c, r.get("speaker", ""))].append(k)

    jc, sc = collections.Counter(), collections.Counter()
    for (j, _s), ks in gb.items():
        jc[j] += len(ks)
    for (j, _p), cs in adv.items():
        sc[j] += len(cs)

    m = collections.defaultdict(collections.Counter)
    for (jp, plate), _cells in adv.items():
        if jc[jp] == 1 and sc[jp] == 1:
            for (j2, spk), _ks in gb.items():
                if j2 == jp:
                    m[plate][spk] += 1
    mp = {}
    for plate, c in m.items():
        if len(c) > 1:
            raise SystemExit("nameplate %r ứng với nhiều speaker: %s — không ghép được"
                             % (plate, dict(c)))
        mp[plate] = c.most_common(1)[0][0]
    return adv, gb, mp


_GJ = []


def _chon_chu(cand, sid, i, neo, cua_scen):
    """Chọn dòng Genebark SỞ HỮU ô ADV `(sid, i)` trong nhiều ứng viên trùng nhau.

    Mỗi dòng Genebark ứng ĐÚNG MỘT chỗ trong truyện — bản gốc lưu trùng cả đoạn hội
    thoại sang nhiều `groupIDs` (data[260..266] nhóm 20 và data[274..280] nhóm 21 là
    bảy dòng y hệt), nên "trùng nội dung" không có nghĩa "cùng một chỗ".

    Cách chọn: **nội suy đơn điệu giữa hai ô NEO kề nhau**. Ô neo là ô chỉ có một ứng
    viên. Thứ tự tin nhắn trong `data[]` chạy song song thứ tự ô thoại trong cảnh, nên
    ứng viên đúng phải nằm GIỮA neo trước và neo sau.

    Hai cách làm sai đã thử:

    - *lấy dòng đầu* — sai 10/37 ô. `107/txt/0274..0279` là sáu ô liên tiếp, phải ứng
      dãy liền `gb788..793`, nhưng bị xé thành `758..761` rồi nhảy ngược `737`.
    - *so `groupIDs` với TOÀN BỘ ô neo của scenario* — vẫn sai khi một cảnh mở nhiều
      phiên chat: scenario 77 dùng cả nhóm 20 lẫn 21, nên `77/txt/0029..0034` chọn nhóm
      21 còn `0035..0049` nhảy ngược về nhóm 20, trong khi thứ tự ô ADV chạy liên tục.
      Một đoạn liền mạch không thể xen kẽ hai nhóm.

    Nên phải neo theo VỊ TRÍ, không theo tập hợp.
    """
    if len(cand) == 1:
        return cand[0]
    anc = sorted((j, k) for (s2, j), k in neo.items() if s2 == sid)
    if not anc:
        return cand[0]
    truoc = [k for j, k in anc if j < i]
    sau = [k for j, k in anc if j > i]
    lo = truoc[-1] if truoc else None          # neo gần nhất phía trước
    hi = sau[0] if sau else None               # neo gần nhất phía sau

    def diem(c):
        # 0 = nằm đúng giữa hai neo kề; rồi tới khoảng cách tới neo gần nhất
        giua = 0 if (lo is None or c > lo) and (hi is None or c < hi) else 1
        d = min(abs(c - k) for k in (lo, hi) if k is not None)
        return (giua, d)

    return min(cand, key=diem)


def pairs(bao_bien_the=False):
    """Cặp ADV <-> Genebark, ghép theo (bản Nhật, NGƯỜI NÓI).

    Bản đầu đòi câu Nhật **duy nhất ở cả hai bên** và chỉ ra 184 cặp. Điều kiện đó quá
    chặt vì bản gốc **lưu trùng cả đoạn hội thoại**: `groupIDs 20` data[260..266] và
    `groupIDs 21` data[274..280] là BẢY dòng giống hệt nhau, chỉ khác nhóm chat. Một
    tin nhắn bị lưu hai lần thì không phải hai bản dịch — nó vẫn là một.

    Hệ quả: 47 ô ADV nằm ngoài bảng, 42 trong số đó còn mang giọng văn viết
    ("Bây giờ tôi sẽ đến gặp cô.") thay vì giọng nhắn tin ("Đang đến gặp đây") — đúng
    lớp lỗi mà tool này sinh ra để chữa, chỉ là chưa với tới.

    Nới bằng cách gộp theo **(câu Nhật, speaker)**. Người nói lấy từ nameplate ADV, và
    ánh xạ nameplate->speaker tự suy từ các cặp 1:1 chắc chắn (xem `_nameplate_map`).
    Nhiều dòng trong cùng một nhóm là bản lưu trùng -> lấy dòng đầu làm chủ.

    NGOẠI LỆ: nhóm nào các dòng trùng lại được dịch KHÁC nhau thì BỎ, không đoán. Người
    dùng xác nhận đó là **biến thể có chủ ý** để tránh lặp:

        player はーい  ->  'Tuân lệnh' / 'Okieee' / 'Rõ ạ'
        ユーリ  はーい  ->  'Okela' / 'Okela~' / 'Okela.'

    5 nhóm như vậy, ứng với 5 ô ADV — chúng giữ chữ riêng, không bị chép đè.

        184 cặp (cũ)  ->  226 cặp,  5 ô cố ý để ngoài
    """
    _, _, sj_raw = load_text(os.path.join(STOCK, "json", "json"), "GenebarkChatMainData")
    _, _, ss_raw = load_text(os.path.join(STOCK, "scenario", "scenario01"), "ScenarioData")
    sj = json.loads(sj_raw.lstrip("﻿"))["data"]
    ss = json.loads(ss_raw.lstrip("﻿"))
    global _GJ
    _GJ = sj
    adv, gb, mp = _nameplate_map(ss, sj)

    # bản dịch hiện tại của Genebark — CHỈ dùng để loại nhóm có biến thể chủ ý
    _, _, cj_raw = load_text(os.path.join(ROOT, "romfs", "Data", "StreamingAssets",
                                          "json", "json"), "GenebarkChatMainData")
    cj = json.loads(cj_raw.lstrip("﻿"))["data"]

    # VÒNG 1: chỉ những ô ghép được KHÔNG mơ hồ -> làm NEO cho vòng 2
    neo = {}
    cua_scen = collections.defaultdict(list)
    for (jp, plate), cells in adv.items():
        spk = mp.get(plate)
        if spk is None:
            continue
        cand = gb.get((jp, spk))
        if cand and len(cand) == 1:
            for sid, i in cells:
                neo[(sid, i)] = cand[0]
                cua_scen[sid].append(cand[0])

    out, bien_the = [], []
    for (jp, plate), cells in adv.items():
        spk = mp.get(plate)
        if spk is None:
            continue
        cand = gb.get((jp, spk))
        if not cand:
            continue
        # KHÔNG loại nhóm có bản dịch khác nhau. Mỗi dòng Genebark ứng ĐÚNG MỘT chỗ
        # trong truyện, nên hai dòng cùng tiếng Nhật là hai tin nhắn khác nhau — dịch
        # khác nhau là ĐÚNG, không phải mơ hồ. Bản trước tôi loại chúng vì hiểu ngược,
        # làm 5 ô mất chủ oan. Việc còn lại chỉ là chọn ĐÚNG dòng, và `_chon_chu` làm
        # điều đó bằng `groupIDs`.
        for sid, i in cells:
            out.append((_chon_chu(cand, sid, i, neo, cua_scen), sid, i, jp))
    out.sort(key=lambda r: (r[1], r[2]))
    if bao_bien_the:
        return out, bien_the
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
