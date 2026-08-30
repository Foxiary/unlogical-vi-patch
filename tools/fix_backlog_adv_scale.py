# -*- coding: utf-8 -*-
r"""BACKLOG ngắt dòng khác ADV — hạ trần cỡ chữ cho khớp khung nguồn.

Nối tiếp `fix_backlog_autosize.py` (29/08/2026). Bản vá đó chống **tràn đè hàng dưới**:
khai đúng chiều cao thật của hàng (213 / 184) rồi bật tự thu chữ. Nó **cố ý** không đụng
tới chuyện ngắt lại — docstring của nó viết thẳng "hẹp hơn 70 px nên dòng đã vừa ADV bị
ngắt lại". Đây là phần còn lại đó. **Hình học của bản vá kia giữ nguyên**, ở đây chỉ đổi
cỡ chữ và `characterSpacing`.

## Triệu chứng

Ảnh máy thật `_2026-08-29_23-12-50.png`, hàng `Áo đen`:

    Đã hết 30 phút. Thời gian thảo luận kết thúc
    tại
    đây.

Đo mực dòng 1 trên ảnh: x 169 → 1301 = **1133 px**. Thêm ` tại` là **1213 px** theo model,
mà ô tin nhắn backlog rộng **1210** ⇒ hụt **3 px** nên TMP đẩy `tại` xuống dòng, còn `đây.`
vốn là ngắt cứng của bản dịch nên thành dòng ba.

## Vì sao: cùng chuỗi, cùng font, khác khung

| | khung nguồn | BACKLOG (trước bản vá này) |
|---|---|---|
| `Log_Base` ← ADV `Message/Text` (`level10`) | 1280×186, cỡ 42 | 1210×213, cỡ **42** |
| `Log_Base_Chat` ← `genebark` `Message_TMP` | 1210×80, cỡ **32**, `charSpacing` **5** | 1210×184, cỡ **40**, `charSpacing` **8.5** |

**Hai widget vẽ chữ Việt bằng cùng một font.** Asset khai khác nhau — ô backlog trỏ
`FOT-iroha21popuraStdN-R SDF-Dynamic`, còn `adv_layout` ghi khung ADV là
`FOT-NewRodinProN-DB` — nhưng `level10` không có type tree nên không đọc thẳng được, và
trên màn hình thì chữ giống hệt. Đo tỉ lệ **bất biến theo cỡ chữ** `bề ngang "Se" / chiều
cao chữ "S"` trên hai ảnh thật:

    ADV      _2026-08-29_15-47-23.png  "Sekigawa"   1,765
    BACKLOG  _2026-08-29_23-14-19.png  "Selector"   1,759      lệch 0,3%

Cả hai font asset đều là **Dynamic**, glyph chữ Việt nạp lúc chạy, nên hai widget dùng
chung một font dự phòng. Hệ quả cho bản vá: **chỉ bề rộng khung là khác**, và tiêu chí
thành phép chia đơn giản.

## Cách chữa

`42 × 1210/1280 = 39,7`. Hạ trần cỡ chữ xuống **39,5** thì mọi dòng vừa khung ADV chắc
chắn vừa khung backlog — vì `39,5/42 × 1280 = 1204 px < 1210`, còn dư 6 px biên. Không cần
mô hình advance nào cả, chỉ là tỉ lệ hai khung.

Kiểm trên ca của ảnh: dòng `「Đã hết 30 phút. …kết thúc tại` ở cỡ 42 đo được **1213 px**
(quá ô 1210 đúng 3 px ⇒ rớt chữ), ở cỡ 39,5 còn **1141 px** ⇒ vừa. Trên toàn bộ
`ScenarioData`, **1.437 tin nhắn** có dòng lọt khoảng 1210–1280 px, tức đúng nhóm bị
backlog ngắt lại.

## Ô chat: GIỮ CỠ 40, THU Ô 1210 → 872 (30/08/2026)

Chốt cuối: **không đụng cỡ chữ, sửa bề rộng ô.** Lý do là lỗi thật ở ô chat không phải
ngắt dòng lệch màn chat mà là **chữ chạy ra ngoài khung tối** — ô khai 1210 px trong khi
khung chỉ cho 1107 px kể từ mép trái chữ, nên 68/457 dòng vẽ đè lên nền sáng, và dòng dài
còn xuyên qua nhãn `CHAT` dọc (x 1234–1249 trên màn).

Luật do người dùng đặt: **lề phải bằng lề trái**. Đo trên ảnh `_2026-08-30_01-56-18.png`:

    khung tối        x   60 → 1276
    mực chữ bắt đầu  x  232            ⇒ lề trái 172 px
    lề phải = 172    ⇒ chữ dừng ở 1104 ⇒ bề rộng ô = 1104 − 232 = 872

`pivot.x = 0` nên thu `m_SizeDelta.x` **ghim mép trái, chỉ kéo mép phải vào** — không phải
bù toạ độ. 872 còn cách nhãn `CHAT` 130 px.

Giá phải trả, đo trên 289 tin / 457 dòng cứng (spacing 5,0 theo máy thật):

    ô 1210 cỡ 40 (cũ)   45 dòng ngắt · 68 dòng ra ngoài khung · 9 tin thu chữ
    ô  872 cỡ 40 (mới) 157 dòng ngắt ·  0 dòng ra ngoài khung · 32 tin thu chữ
    ô  872 cỡ 34       85 dòng ngắt ·  0 ·  1 tin thu chữ      ← đã cân nhắc, không chọn

Không cấu hình nào tràn dọc: hàng cao 184 px cộng tự thu chữ 40→26 lo phần đó.

`Log_Base_Chat_Select` (ô 1220×280, cỡ 42) **không đụng** — chỉ 4 lựa chọn chat trong cả
game, và `fix_backlog_autosize.py` cũng đã bỏ qua nó vì khung vốn đủ rộng.

## Lịch sử: đã thử hạ cỡ chữ rồi bỏ

Phần dưới đây mô tả bản vá cho `Log_Base_Chat` (cỡ 40 → 32, `charSpacing` 8,5 → 5,0). Bản
vá đó **đã ghi, đã hoàn tác, và người dùng chốt giữ nguyên cỡ 40 của nhà phát triển** —
chấp nhận 45/457 dòng chat trong backlog ngắt khác màn chat. `TARGETS` vì thế đặt đích ô
chat đúng bằng số gốc **40 / 40 / 8,5**: chạy tool sẽ gỡ bản 32 nếu nó còn trên đĩa và giữ
ô chat ở nguyên trạng mãi về sau. **Đừng vá lại chỗ này nếu không có quyết định mới.**
Chỉ ô thoại ADV (`Log_Base`, cỡ 39,5) là còn hiệu lực.

Ô chat trong BACKLOG là **object riêng** (`BackMessage_TMP` pid -8296035291137428729, ô
1210×184), không dùng chung với `Message_TMP` của màn chat (pid -8722983982811664953, ô
1210×80, cỡ 32/5). Hai bên chỉ chung font asset. Nên sửa cỡ ở backlog chưa bao giờ động
tới màn chat — đo lại nếu có ai nghi ngờ: diff bundle của đợt vá ra đúng 2 object.

Giữ nguyên phần phân tích bên dưới vì số đo vẫn đúng và cần cho việc chọn phương án thay
thế. Ảnh máy thật `_2026-08-30_01-56-18.png` (backlog, cỡ 40) so với
`_2026-08-30_01-40-43.png` (màn chat, cỡ 32) cho thấy đúng hiện tượng: cùng câu
`Sợ bị hack lắm nên cậu cứ sao lưu dữ liệu cho chắc ăn nhé`, màn chat một dòng, backlog
rớt chữ `nhé` xuống dòng hai.

Các phương án còn để ngỏ, kèm số đo trên 457 dòng chat sau đợt ngắt dòng dữ liệu:

    cỡ 40 (đang dùng)             45 dòng gãy khác màn chat
    cỡ 38                         32 dòng
    cỡ 36                         20 dòng
    cỡ 34                         12 dòng
    cỡ 32                          0 dòng  ← bản vừa hoàn tác
    ngắt dòng cứng cho cỡ 40       0 dòng, nhưng phải ép mọi dòng ≤ 968 px ở cỡ 32
                                   (thay vì 1205 như hiện nay) — 45/457 dòng phải cắt
                                   ngắn thêm, và màn chat sẽ gãy sớm hơn cần thiết
    nới ô backlog                  bất khả: dòng rộng nhất ở cỡ 40 là 1502 px, mà ô chỉ
                                   nới được tới mép khung tối (~1210) trước khi chui
                                   xuống dưới nhãn CHAT

## Vì sao ô chat lệch

Chat thì tỉ lệ là `1210/1210 = 1,0` — cùng bề rộng ô, nên backlog chỉ việc vẽ đúng cỡ chữ
của khung chat. Trước bản vá nó vẽ **to hơn 25%**: đo chiều cao chữ hoa trên hai ảnh thật,
`_2026-08-29_22-49-21.png` (backlog, chữ `A`) cao **30 px**, `_2026-08-28_13-17-14.png`
(màn chat, chữ `K`) cao **24 px** — tỉ lệ đúng **1,250 = 40/32**.

Hậu quả: cùng một câu mà hai màn ngắt dòng khác nhau. Trong **289 tin nhắn chat của
`ScenarioData`** (xem mục dưới — đó mới là thứ hiện ở backlog), số tin có dòng vượt ô 1210:

    cỡ 40 (backlog cũ)   90/289          cỡ 32 (bằng màn chat)   50/289

50 tin kia dài thật, màn chat cũng ngắt — nhưng nay ngắt **đúng cùng chỗ**. Ví dụ
`Sợ bị hack lắm nên cậu cứ sao lưu dữ liệu cho chắc ăn nhé`: 1240 px ở cỡ 40 (rớt chữ),
992 px ở cỡ 32 (một dòng, y như màn chat).

**Nguồn dữ liệu — đính chính.** Bản đầu của mục này đo `GenebarkChatMainData` (1194 tin
của app Genebark) và ghi "301/1194 → 0". Sai tập: dòng chat trong BACKLOG đến từ các khối
`[chat start]` của `ScenarioData`, không phải timeline của app — kiểm bằng chính file save
(`m_backLogData.name = "Suzuno@Sz_36iii"`, text khớp `ScenarioData`). Widget hiển thị thì
đúng là một: `genebark.prefab` › `Message_TMP` 1210×80, cỡ 32, spacing 5.

`characterSpacing` 8,5 → 5,0 đi kèm cho khớp khung chat. Đo mực dòng
`Anh đã liên lạc được với Himejima chưa ạ?` trong ảnh backlog: **899 px**, mà model ở
40/spacing-5 cho 910 px còn ở 40/spacing-8,5 cho 1007 px ⇒ máy vốn đã vẽ như spacing 5;
đổi số này chỉ là cho asset khớp thực tế, không đổi hình:

    Log_Base       m_fontSize 42 -> 39.5     m_fontSizeMax 42 -> 39.5     sàn 28 giữ nguyên
    Log_Base_Chat  m_fontSize 40 -> 32       m_fontSizeMax 40 -> 32       charSpacing 8.5 -> 5.0

**Trần tự thu phải hạ theo.** `m_enableAutoSizing = 1` nghĩa là TMP lấy cỡ **lớn nhất còn
vừa khung**, nên để `m_fontSizeMax` ở 42/40 thì nó phóng chữ về cũ ngay, đặt `m_fontSize`
bao nhiêu cũng vô nghĩa.

## Vì sao KHÔNG đụng chiều cao ô

Bản đầu của tool này thu ô `Log_Base` còn `186 × 0,945 = 176` px cho "khớp tỉ lệ ADV". Vô
ích: chiều cao không quyết định chỗ ngắt dòng, chỉ quyết định khi nào TMP thu chữ. Kiểm
trên 39.574 tin nhắn: cả hai chiều cao 213 và
176 đều ra **0 tin tràn** và **cùng 1.169 tin (3,0%) phải thu chữ** — khác nhau chỉ ở chỗ ô
176 thu sâu hơn (tới ~30) trong khi ô 213 dừng ở ~36,5. Nên giữ **213** của
`fix_backlog_autosize.py`: chữ to hơn, và hình học của bản vá kia không bị hai tool giành
nhau.

    python tools\fix_backlog_adv_scale.py            # đo, so trước/sau
    python tools\fix_backlog_adv_scale.py --check    # thoát 1 nếu chưa vá
    python tools\fix_backlog_adv_scale.py --apply

Backup: `_backup\ui_jp.prebacklogadvscale`.
Chạy lại vô hại: phần nào đã đúng thì bỏ qua. Chấp nhận cả trạng thái của
`fix_backlog_autosize.py` lẫn trạng thái của bản đầu (ô 176) và đưa cả hai về đích.

> **Cảnh báo hai tool giẫm chân.** `fix_backlog_autosize.py --apply` sẽ ghi lại cỡ 42/40
> và xoá bản vá này (nó dựng số từ `TARGETS` của chính nó). Chạy nó **trước**, rồi mới chạy
> tool này. `--check` của nó cũng sẽ báo "CHƯA VÁ" vì rect/cỡ chữ không còn khớp hằng số
> của nó — đó là bình thường, đừng chạy `--apply` để "chữa".
"""
import io
import os
import shutil
import sys

import UnityPy

if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UI = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BACKUP = os.path.join(ROOT, "_backup", "ui_jp.prebacklogadvscale")

APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

# field -> (các giá trị chấp nhận được lúc vào, giá trị đích)
TARGETS = [
    dict(
        name="Log_Base (tin nhan ADV)",
        rect=6699117019379991138, tmp=3933637203441546795,
        rect_fields={
            "h": ({213.0, 176.0}, 213.0),          # giữ hình học của fix_backlog_autosize
            "y": ({-61.5, -43.0}, -61.5),
        },
        tmp_fields={
            "m_fontSize": ({42.0, 39.5}, 39.5),
            "m_fontSizeMax": ({42.0, 39.5}, 39.5),
            "m_fontSizeMin": ({28.0, 26.5}, 28.0),
        },
    ),
    # HOÀN TÁC 30/08/2026 theo yêu cầu: giữ nguyên thông số gốc của ô chat.
    # Đích quay về 40 / 40 / 8.5 nên tool vừa hoàn tác được bản 32 đã ghi, vừa
    # giữ cho các lượt sau không đụng vào nữa. Xem "Ô chat: đã hoàn tác" ở docstring.
    dict(
        name="Log_Base_Chat (tin nhan Genebark)",
        rect=-4076919273405506282, tmp=-8296035291137428729,
        rect_fields={"w": ({1210.0, 872.0}, 872.0)},
        tmp_fields={
            "m_fontSize": ({40.0, 32.0}, 40.0),
            "m_fontSizeMax": ({40.0, 32.0}, 40.0),
            "m_characterSpacing": ({8.5, 5.0}, 8.5),
        },
    ),
]


def load():
    UnityPy.config.FALLBACK_UNITY_VERSION = "2021.3.0f1"
    env = UnityPy.load(UI)
    return env, {o.path_id: o for o in env.objects}


def near(a, b):
    return abs(float(a) - float(b)) < 0.05


def cur_rect(rt, key):
    if key == "w":
        return rt["m_SizeDelta"]["x"]
    if key == "h":
        return rt["m_SizeDelta"]["y"]
    return rt["m_AnchoredPosition"]["y"]


def diff(t, rt, spec):
    """[(nhãn, hiện tại, đích)] cho các trường còn lệch; None nếu gặp giá trị lạ."""
    out = []
    for key, (ok_vals, want) in spec["rect_fields"].items():
        cur = cur_rect(rt, key)
        if not any(near(cur, v) for v in ok_vals | {want}):
            return None
        if not near(cur, want):
            out.append(("rect." + key, cur, want))
    for key, (ok_vals, want) in spec["tmp_fields"].items():
        cur = t[key]
        if not any(near(cur, v) for v in ok_vals | {want}):
            return None
        if not near(cur, want):
            out.append((key, cur, want))
    return out


def show(t, rt, spec):
    print("  %-34s o %.0fx%.0f  y %.1f  co %.1f [%.1f..%.1f]  charSp %.2f"
          % (spec["name"], rt["m_SizeDelta"]["x"], rt["m_SizeDelta"]["y"],
             rt["m_AnchoredPosition"]["y"], t["m_fontSize"],
             t["m_fontSizeMin"], t["m_fontSizeMax"], t["m_characterSpacing"]))


def main():
    env, objs = load()
    todo = []
    for spec in TARGETS:
        tmp, rect = objs.get(spec["tmp"]), objs.get(spec["rect"])
        if tmp is None or rect is None:
            print("KHONG thay object cua", spec["name"])
            return 1
        t, rt = tmp.read_typetree(), rect.read_typetree()
        show(t, rt, spec)
        d = diff(t, rt, spec)
        if d is None:
            print("     gia tri la — dung, kiem tra tay")
            return 1
        if d:
            todo.append((spec, tmp, rect, t, rt, d))
            for k, cur, want in d:
                print("     -> %s: %.2f -> %.2f" % (k, cur, want))
        else:
            print("     -> da dung")

    if CHECK:
        if todo:
            print("CHUA va xong (%d muc)" % len(todo))
            return 1
        print("OK")
        return 0
    if not todo:
        print("Khong co gi de lam.")
        return 0
    if not APPLY:
        print("--apply de ghi")
        return 0

    if not os.path.exists(BACKUP):
        shutil.copy(UI, BACKUP)
        print("backup ->", BACKUP)

    for spec, tmp, rect, t, rt, d in todo:
        touched_rect = False
        for key, (_, want) in spec["rect_fields"].items():
            if key == "w":
                rt["m_SizeDelta"]["x"] = want
            elif key == "h":
                rt["m_SizeDelta"]["y"] = want
            else:
                rt["m_AnchoredPosition"]["y"] = want
            touched_rect = True
        if touched_rect:
            rect.save_typetree(rt)
        for key, (_, want) in spec["tmp_fields"].items():
            t[key] = want
        tmp.save_typetree(t)

    blob = env.file.save(packer="lz4")
    del env
    with open(UI, "wb") as fh:
        fh.write(blob)
    print("da ghi %s (%d byte)" % (UI, len(blob)))

    # doc lai tu dia, dung tin gia tri trong bo nho
    env2, objs2 = load()
    ok = True
    for spec in TARGETS:
        t = objs2[spec["tmp"]].read_typetree()
        rt = objs2[spec["rect"]].read_typetree()
        show(t, rt, spec)
        d = diff(t, rt, spec)
        print("     doc lai tu dia:", "OK" if d == [] else "HONG (%s)" % d)
        ok = ok and d == []
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
