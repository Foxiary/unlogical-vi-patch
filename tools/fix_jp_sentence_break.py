# -*- coding: utf-8 -*-
"""Soi ngắt dòng ở ranh giới câu của bản Nhật sang bản Việt.

Yêu cầu 27/08/2026: chỗ nào bản Nhật cho câu sau xuống hàng riêng thì bản Việt
cũng xuống hàng — **miễn là câu tiếng Việt vẫn gọn trong một hàng**; không gọn
thì cứ để phẳng, mặc TMP tự ngắt.

    JP: 「はは、おおげさ。⏎　一緒にスーパー寄ってから帰ろう」
    VN: 「Haha, em nói quá rồi. Cùng ghé siêu thị rồi về nhé.」
    ->  「Haha, em nói quá rồi.
         Cùng ghé siêu thị rồi về nhé.」

> ### Phần lớn ngắt dòng của bản Nhật KHÔNG soi sang được
>
> Trong 26 969 ngắt của bản gốc chỉ 9 107 nằm sau `。`; 9 444 nằm sau dấu phẩy
> `、` và hơn 5 000 nằm giữa chừng câu (`…て`, `…は`, `…に`). Đó là các tác giả tự
> canh dòng cho vừa khung chứ không phải ý đồ ngắt câu, và tiếng Việt không có vị
> trí tương ứng:
>
>     JP: 瞬間、自分がまだ夢の中にいるのか、⏎これが現実なのか判断がつかなかった。
>     VN: Trong khoảnh khắc, tôi chẳng thể phân biệt được ... hay đây chính là hiện thực.
>
> Nên tool chỉ nhận ngắt **đúng ở ranh giới câu**, và ánh xạ theo **thứ tự câu**:
> ngắt sau câu thứ k của bản Nhật -> ngắt sau câu thứ k của bản Việt.

Bốn chốt trước khi ghi, thiếu một cái là bỏ qua cả tin nhắn:

0. **Không phải tin nhắn chat.** `talkName` có `@` (`【Kai Munakata@k_munakata2150】`)
   thì bố cục ô đó do `fix_chat_wrap.py --only=adv` sở hữu — bỏ qua, không giành.
   289 ô, 137 ô trong đó có ngắt bên bản Nhật.

   **Đã BỎ `unplan()` (02/09/2026).** Nó ra đời 28/08 với tiền đề "ô chat luôn
   phẳng vì `fix_chat_use_genebark` ghi phẳng" — tiền đề đó hết đúng từ 30/08, khi
   `fix_chat_wrap` nhận phần bố cục chat và CỐ Ý ngắt lại. Từ đó hai tool giằng
   nhau đúng **47/47 ô**, vòng nào chạy sau thì thắng, và không ai thấy vì cả hai
   đều cho ra kết quả hợp lệ.

   Chỗ trùng khít 47/47 không phải vì hai luật giống nhau — chúng khác hẳn:

   | | `fix_chat_wrap` | tool này |
   |---|---|---|
   | ngắt ở đâu | MỌI dấu kết câu, thêm dấu phẩy khi dòng quá 1220 px | chỉ chỗ bản NHẬT ngắt |
   | phủ được | 1194/1194 tin nhắn | 218/1194 (976 ô không đủ chốt) |
   | khung/phông | chat 1220 px, `FOT-DNPShueiMGoStd-B` | ô thoại ADV, `FOT-NewRodinProN-DB` |

   Đo trên 1194 tin nhắn: giống nhau 198, khác nhau 20, còn lại tool này bó tay.
   `unplan()` chỉ nổ đúng ở phần giao đó — theo định nghĩa, vì nó chỉ gỡ ngắt nào
   `plan()` dựng lại được y hệt. Nên nó luôn gỡ đúng những chỗ `fix_chat_wrap` sẽ
   đặt lại nguyên xi: churn thuần tuý, không ai được gì.
1. Bản Việt phải **phẳng hoàn toàn** (không có `\\n` nào). Ô đã có ngắt là của
   fixer khác (`fix_ellipsis_break`, danh sách novel…) — không giành.
2. Số câu hai bên phải **bằng nhau**, nếu không thứ tự câu lệch nhau (318/10 489
   ô rơi vào đây: người dịch gộp hoặc tách câu).
3. Chỗ cắt trong bản Việt phải đang là một **dấu cách** — thay đúng space đó bằng
   `\\n`, không thêm bớt ký tự nào.
4. **Mọi đoạn trừ đoạn cuối phải gọn trong một hàng**, đo ở đúng cỡ chữ tin nhắn
   ĐANG hiện (xem dưới).
5. Ngắt xong **cỡ chữ không được co**, và không dòng nào được chạm hoạ tiết góc ô
   thoại. Chốt cỡ chữ là cần: đoạn CUỐI vẫn tự do tràn sang hàng hai, đẩy tin
   nhắn quá khung và auto-size co chữ — đúng 468/6 900 tin rơi vào đó. Còn đòi cả
   đoạn cuối gọn một hàng thì quá tay: còn 3 326 tin, loại oan 3 106 tin có đoạn
   cuối hai hàng mà tổng vẫn ba hàng, tức không tốn gì.

> ### "Vừa một hàng" đo ở cỡ chữ nào
>
> Ở **cỡ 42**, cỡ mặc định. Nhưng tin nhắn nào dài tới mức dù để phẳng vẫn quá ba
> hàng thì auto-size đã co nó nhỏ lại rồi, nên đo ở **cỡ đã co** đó. Nói gọn: đo ở
> cỡ mà tin nhắn **đang** hiện, tức `render(bản phẳng)` — không phải cỡ sau khi
> ngắt. Đo ở cỡ sau khi ngắt thì thành lý luận vòng: ngắt làm chữ co lại, chữ co
> lại làm câu vừa một hàng, rồi lấy đó biện minh cho chính cái ngắt.

> ### Chỗ ngắt hình dấu lửng nhường cho `fix_ellipsis_break.py`
>
> Hai luật cùng nhắm chỗ `. ⏎ …` nhưng chốt khác nhau nên gỡ qua ngắt lại vô tận:
> luật kia gỡ 85 ô vì thêm dòng, luật này đòi lại đúng 67 ô trong số đó. Nên `plan()`
> bỏ mọi chỗ cắt mà vế sau mở đầu bằng dấu lửng — một chủ sở hữu cho một hình, đúng
> nguyên tắc đã dùng cho ô chat. Sau chốt chỉ còn 3 ô thật sự thuộc luật này.

Không thụt `　` ở dòng sau như bản Nhật: bản Việt hiện có 1 151 dòng sau ngắt
không thụt so với 71 dòng có thụt, đây theo lệ số đông.

**Không gỡ lại được.** Tool chỉ quyết định trên ô phẳng, nên chạy lại là no-op.
Điều đó ổn vì merge sheet làm phẳng sạch mọi `\\n`, và quy trình sau merge vốn là
chạy lại toàn bộ fixer — lúc đó nó quyết định lại từ đầu.

    python tools\\fix_jp_sentence_break.py           # chạy thử, in thống kê
    python tools\\fix_jp_sentence_break.py --apply
    python tools\\fix_jp_sentence_break.py --check   # chốt sau merge, lỗi -> exit 1
"""
import io
import json
import os
import re
import shutil
import sys

# Bọc một lần thôi: bọc chồng lên nhau thì lớp cũ bị thu gom và ĐÓNG luôn buffer.
if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402
import fix_adv_wrap as LAY   # noqa: E402  — mô hình bố cục ô thoại đã hiệu chuẩn

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "scenario", "scenario01")
# .jpsentbreak = đợt soi ngắt 27/08; .chatnobreak = đợt thêm chốt @ (trả ô chat
# về phẳng, để fix_chat_use_genebark.py sở hữu); .ellcede = 28/08 (nhường chỗ ngắt
# hình dấu lửng cho fix_ellipsis_break.py).
BACKUP = os.path.join(ROOT, "_backup", "scenario01.ellcede")
STOCK = r"D:\Downloads\UNLOGICAL_v2\Data\StreamingAssets\scenario\scenario01"
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

JP_END = re.compile(r"(?:[。！？]|…+)+")
VN_END = re.compile(r"(?:[.!?]|…)+")
TAG = re.compile(r"\[[^\[\]\n]*\]")
ELL_AFTER = re.compile(r"(?:\.{2,}|…)")
OPEN = "　「『（(\"'"          # dấu mở, bỏ qua khi dò ngược
CLOSE = "」』）)\"'"           # dấu đóng cuối tin nhắn


def _enders(s, pat, need_space):
    """Vị trí NGAY SAU mỗi dấu kết câu thật sự."""
    out = []
    for m in pat.finditer(s):
        k = m.start() - 1
        while k >= 0 and s[k] in OPEN:
            k -= 1
        if k < 0 or s[k] == "\n":
            continue                       # dấu lửng MỞ ĐẦU dòng, không kết câu gì
        end = m.end()
        if need_space:
            t = end
            while t < len(s) and s[t] in CLOSE:
                t += 1
            if t < len(s) and s[t] not in " \n":
                continue                   # `3.5`, `v.v` … không phải kết câu
        out.append(end)
    return out


def _with_tail(s, ends):
    """Cuối tin nhắn luôn là một ranh giới câu — bản Nhật hay bỏ `。` trước `」`."""
    t = len(s)
    while t > 0 and s[t - 1] in CLOSE:
        t -= 1
    return ends if (ends and ends[-1] >= t) else ends + [len(s)]


def jp_enders(s):
    return _with_tail(s, _enders(s, JP_END, False))


def vn_enders(s):
    return _with_tail(s, _enders(s, VN_END, True))


def seg_lines(seg, size):
    """Số hàng TMP sẽ ngắt cho một đoạn ở cỡ `size`."""
    words = [LAY.measure(w) for w in LAY.words_of(LAY.shown(seg))]
    return len(LAY.wrap_words(words, LAY.RECT_W * LAY.FMAX / size))


def plan(vn, jp):
    """Bản Việt sau khi soi ngắt, hoặc None nếu không đủ chốt. `vn` phải phẳng."""
    if "\n" in vn or not vn.strip() or "\n" not in jp:
        return None
    flat_jp = jp.replace("　", "")          # bỏ thụt để vị trí ngắt sạch
    je = jp_enders(flat_jp)
    order = [je.index(m.start()) for m in re.finditer("\n", flat_jp) if m.start() in je]
    if not order:
        return None                        # ngắt của bản Nhật toàn nằm giữa câu
    ve = vn_enders(vn)
    if len(je) != len(ve):
        return None                        # thứ tự câu không khớp -> không dám soi
    cuts = [ve[k] for k in order]
    if any(c >= len(vn) or vn[c] != " " for c in cuts):
        return None
    # Chỗ ngắt mà vế sau mở đầu bằng dấu lửng là địa phận của fix_ellipsis_break.py:
    # luật bên đó có chốt riêng (dòng cụt, không được thêm dòng). Hai tool cùng quyết
    # định một chỗ thì gỡ qua ngắt lại vô tận — đã đo được đúng 67 ô như thế.
    cuts = [c for c in cuts if not ELL_AFTER.match(vn[c + 1:])]
    if not cuts:
        return None

    tags = [(m.start(), m.end()) for m in TAG.finditer(vn)]
    if any(x < c < y for c in cuts for x, y in tags):
        return None                        # space nằm TRONG `[...]`: cắt là hỏng lệnh
    out = vn
    for c in cuts:
        out = out[:c] + "\n" + out[c + 1:]
    size = LAY.render(vn)[0]               # cỡ tin nhắn ĐANG hiện, không phải sau ngắt
    if any(seg_lines(x, size) != 1 for x in out.split("\n")[:-1]):
        return None
    if LAY.render(out)[0] < size:
        return None                        # ngắt làm auto-size co chữ -> không đáng
    if LAY.offenders(out)[0]:
        return None                        # dòng mới chạy dưới hoạ tiết góc ô
    return out


def load(path):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name == "TextAsset" and o.read().m_Name == "ScenarioData":
            d = o.read()
            raw = d.m_Script
            if not isinstance(raw, str):
                raw = bytes(raw).decode("utf-8")
            return env, d, raw
    raise SystemExit("không thấy ScenarioData")


def stock_text():
    if not os.path.exists(STOCK):
        raise SystemExit("không thấy bản gốc để đối chiếu: %s" % STOCK)
    _, _, raw = load(STOCK)
    data = json.loads(raw.lstrip("\ufeff"))
    return {(t["scenarioID"], j): s
            for t in data["target"] for j, s in enumerate(t["text"])}


def mirror(script, old, new):
    lines, ol, nl = script.split("\n"), old.split("\n"), new.split("\n")
    hits = [k for k in range(len(lines) - len(ol) + 1) if lines[k:k + len(ol)] == ol]
    if len(hits) != 1:
        return None
    lines[hits[0]:hits[0] + len(ol)] = nl
    return "\n".join(lines)


def main():
    env, d, raw = load(BUNDLE)
    bom = "\ufeff" if raw.startswith("\ufeff") else ""
    data = json.loads(raw.lstrip("\ufeff"))
    stock = stock_text()

    hits, skipped, chat_n = [], 0, 0
    for ti, t in enumerate(data["target"]):
        sid = t["scenarioID"]
        names = t.get("talkName") or []
        for j, s in enumerate(t["text"]):
            jp = stock.get((sid, j))
            if not jp or chr(10) not in jp or not s.strip():
                continue
            if j < len(names) and "@" in (names[j] or ""):
                # Tin nhắn chat: bảng tên dạng tài khoản (【Kai Munakata@k_munakata2150】).
                # Bố cục do fix_chat_wrap.py --only=adv sở hữu — xem chốt 0 ở đầu file.
                chat_n += 1
                continue
            if chr(10) in s:
                continue                   # ô của fixer khác, không giành
            new = plan(s, jp)
            if new is None:
                skipped += 1
            else:
                hits.append((ti, sid, j, s, new))

    n_brk = sum(h[4].count(chr(10)) - h[3].count(chr(10)) for h in hits)
    if CHECK:
        print("còn lệch: %d tin nhắn, %+d chỗ ngắt  (bỏ qua %d ô không đủ chốt, "
              "%d ô chat để cho fix_chat_wrap --only=adv)"
              % (len(hits), n_brk, skipped, chat_n))
        for ti, sid, j, old, new in hits[:8]:
            print("  FAIL sID=%-4s text[%-5d] %s" % (sid, j, new[:96].replace("\n", "⏎")))
        if hits:
            print("\nchạy `python tools\\fix_jp_sentence_break.py --apply`")
            raise SystemExit(1)
        print("PASS không còn chỗ nào")
        return

    if not hits:
        print("không có gì để sửa")
        return

    grew = sum(1 for _, _, _, o, n in hits if len(LAY.render(n)[1]) > len(LAY.render(o)[1]))
    shrank = sum(1 for _, _, _, o, n in hits if LAY.render(n)[0] < LAY.render(o)[0])
    for ti, sid, j, old, new in hits[:8]:
        print("-> sID=%-4s text[%-5d] %s" % (sid, j, new[:92].replace("\n", "⏎")))
    print("%s%d tin nhắn đổi, %+d chỗ ngắt; cao thêm một dòng %d, co cỡ chữ %d"
          % (chr(10), len(hits), n_brk, grew, shrank))
    print("bỏ qua %d ô không đủ chốt, %d ô chat (fix_chat_wrap --only=adv sở hữu)"
          % (skipped, chat_n))

    def enc(x):
        return json.dumps(x, ensure_ascii=False, separators=(",", ":"))

    out = raw
    for ti in sorted({h[0] for h in hits}):
        arr_old = list(data["target"][ti]["text"])
        arr_new = list(arr_old)
        for _, sid, j, old, new in [h for h in hits if h[0] == ti]:
            arr_new[j] = new
        oj, nj = enc(arr_old), enc(arr_new)
        if out.count(oj) != 1:
            raise SystemExit("mảng text[] của target[%d] khớp %d lần" % (ti, out.count(oj)))
        out = out.replace(oj, nj)

    mirrored = failed = 0
    for ti in sorted({h[0] for h in hits}):
        script = cur = data["target"][ti]["scriptText"]
        for _, sid, j, old, new in [h for h in hits if h[0] == ti]:
            nxt = mirror(cur, old, new)
            if nxt is None:
                failed += 1
            else:
                cur = nxt
                mirrored += 1
        if cur != script:
            oj, nj = json.dumps(script, ensure_ascii=False), json.dumps(cur, ensure_ascii=False)
            if out.count(oj) != 1:
                raise SystemExit("scriptText target[%d] khớp %d lần" % (ti, out.count(oj)))
            out = out.replace(oj, nj)
    print("mirror vào scriptText %d (không khớp verbatim %d)" % (mirrored, failed))

    after = json.loads(out.lstrip("\ufeff"))
    changed = {(h[0], h[2]) for h in hits}
    for ti, t in enumerate(data["target"]):
        ta = after["target"][ti]
        assert ta["loadLine"] == t["loadLine"], "loadLine đổi"
        assert ta["scriptText_Line"] == t["scriptText_Line"], "scriptText_Line đổi"
        for j in range(len(t["text"])):
            if (ti, j) not in changed:
                assert ta["text"][j] == t["text"][j], \
                    "text[%d] target[%d] đổi ngoài dự kiến" % (j, ti)
    for ti, sid, j, old, new in hits:
        assert after["target"][ti]["text"][j] == new
        assert new.replace(chr(10), " ") == old.replace(chr(10), " "), (
            "chữ đổi ở sID=%s text[%d]" % (sid, j))
        assert new.count(chr(10)) != old.count(chr(10))
    print("kiểm tra: chỉ %d tin nhắn đổi, chữ không đổi, loadLine nguyên vẹn" % len(hits))

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    if not os.path.exists(BACKUP):
        shutil.copy2(BUNDLE, BACKUP)
        print("backup ->", BACKUP)
    d.m_Script = bom + out.lstrip("\ufeff")
    d.save()
    with open(BUNDLE, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi", BUNDLE, os.path.getsize(BUNDLE))

    _, _, back = load(BUNDLE)
    rd = json.loads(back.lstrip("\ufeff"))
    for ti, sid, j, old, new in hits:
        assert rd["target"][ti]["text"][j] == new, "đọc lại sID=%s text[%d] sai" % (sid, j)
    print("  đọc lại: %d tin nhắn khớp" % len(hits))


if __name__ == "__main__":
    main()
