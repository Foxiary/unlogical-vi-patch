# tools — bố cục hộp thoại ADV

## Tách ExeFS (`extract_exefs.py`)

```powershell
python tools\extract_exefs.py "D:\Downloads\UNLOGICAL\UNLOGICAL [010068501FF9A800][v131072][Update].nsp" <thư mục ra>
```

Máy không có hactool/LibHac và Ryujinx đóng gói single-file nên không gọi được
DLL nào — script tự làm bằng `pycryptodome` + `lz4`: đọc `prod.keys` của
Ryujinx, giải ticket lấy titlekey, giải header NCA bằng AES-XTS (tweak kiểu
Nintendo: số sector **big-endian**), giải section bằng AES-CTR, đọc PFS0, rồi
giải nén NSO thành ảnh phẳng.

> **Bẫy:** 8 byte thấp của bộ đếm CTR tính theo offset **trong NCA**, không phải
> trong file NSP. Lẫn hai gốc thì ra rác trông rất hợp lý mà không có magic
> `PFS0`.

Kết quả (bản 1.0.2, đã kiểm 16/08/2026):

```
main 40.861.620 B · main.npdm · rtld · sdk · subsdk0
ảnh phẳng main.flat 82.207.152 B
NSO build id  669EA2FE0282C2C0EFEA4DA183419FB7
```

Bản vá code là `<build id>.ips` đặt ở
`%APPDATA%\Ryujinx\mods\contents\010068501ff9a000\vn-translation\exefs\` — ngang
hàng junction `romfs` sẵn có. Vá exefs gắn chặt với đúng build này.

## Vá code: tắt ngắt dòng 18 ký tự

```powershell
python tools\make_ips.py [--apply]        # tạo + cài IPS
python tools\fix_synopsis_box.py [--apply]   # giao việc wrap lại cho TMP
```

`Chapter.get_DefaultMaxCharsPerLine` là getter hằng số:

```
RVA 0x1998AC0   52800240  MOVZ W0, #18   ->   E0031F2A  MOV W0, WZR
```

Lớp cha `MyUICompornentBase` khai báo thuộc tính này kèm tooltip
「非EN言語での1行あたり最大文字数。0以下で折り返し無効。」 — **0 là tắt ngắt
dòng**, và hai màn khác trong game đã trả về 0 sẵn (`0x1A16930`, `0x1AB6B60`).

Ba điểm dễ sai:

- **Phải dùng IPS32**, không phải IPS. Offset của IPS thường chỉ 3 byte = 16 MB,
  không với tới `0x1998AC0`. IPS32: magic `IPS32`, offset 4 byte big-endian, kết
  thúc `EEOF`.
- **Offset trong file vá = RVA + 0x100**, vì bản vá áp lên NSO đã giải nén tính
  cả header 0x100 và `.text` có `mem_off = 0`. **Đừng** lấy cột `Offset:` trong
  `dump.cs` — cột đó là `RVA + 0x10D`, suy ra từ `.text file_off = 0x10D` của
  file **nén**, sai cho IPS.
- `make_ips.py` đối chiếu byte cũ với `main.flat` trước khi ghi — chính bước này
  bắt được sai build hoặc sai quy ước offset.

**Vá code chỉ là một phần ba.** Lần thử đầu báo "y hệt như cũ", và log Ryujinx
chứng minh bản vá không có lỗi:

```
ModLoader ApplyProgramPatches: Matching IPS patch '669E….ips' bid=669E…
ModLoader Patch: Patching address offset 1998ac0 <= E0 03 1F 2A len=4
```

Để ý dòng log: **Ryujinx tự trừ 0x100**, nên offset `0x1998BC0` trong file rơi
đúng vào RVA `0x1998AC0`. Thư mục `Logs\` của Ryujinx là cách nhanh nhất để phân
biệt "vá không ăn" với "vá ăn rồi mà không đổi gì" — xem đó trước khi sửa bản vá.

Không đổi gì là vì **cả 43 tóm tắt trong `ChapterData` đã được ngắt dòng tay ở
≤18 ký tự** để tuân đúng cái luật vừa bị tắt. Cần thêm hai bước:

```powershell
python tools\fix_synopsis_box.py [--apply]   # trả việc wrap cho TMP
python tools\unwrap_synopsis.py  [--apply]   # gỡ \n cứng trong dữ liệu
```

`MainText` vốn để `m_TextWrappingMode = 0` **đúng** vì code game ôm việc ngắt
dòng; tắt code mà không bật wrap thì cả đoạn thành một dòng dài rồi bị mask cắt.
**Không auto-size**: ô này có thanh cuộn riêng (`StorySlider` trong `ui_jp`) nên
phần dôi ra cuộn xuống, mọi mục giữ nguyên cỡ 31.25. Backup
`_backup\ui_jp.presynwrap2`.

Trường thứ hai phải sửa là **`m_margin.y` −1 → 6**. Dấu phụ chồng của tiếng Việt
(`ắ` = trăng + sắc) vươn cao hơn đường ascender của font, nên **dòng đầu tiên** bị
mask xén mất dấu sắc — báo lỗi là "chữ mắt bị ghi thành măt", nhưng dữ liệu vô
tội: `mắt` và `bắt` cùng là `U+1EAF`, chỉ khác chỗ `mắt` nằm ở dòng 1. Đo trên
ảnh 1920×1080: dòng 1 chỉ cao **27 px** trên baseline còn dấu sắc cần **32**; lề
trên gốc lại là −1, kéo chữ lên thêm 1 px nữa.

> Thiếu dấu là triệu chứng **bố cục** trước khi là lỗi chữ — so mã ký tự trước
> khi sửa chuỗi. Và hộp nào có dòng đầu sát mask thì tiếng Việt cần vài px lề trên.

`unwrap_synopsis.py` nối các dòng lại thành đoạn liền: 43/43 mục, không mục nào
có `\n\n` nên không mất ngắt đoạn thật. Mục dài nhất (`*MIYA-04-01`) cần cỡ
**19.25** — khớp đúng con số suy ra từ metric trước đây, và trên sàn 18. Backup
`_backup\json.presynunwrap`.

Gỡ bản vá code: xoá đúng file `.ips`.


## Lỗi nhảy chữ của chú thích (ruby)

`Ruby_Text` (IL2CPP, `Assets/Scripts/Util/Text/Ruby_Text.cs` — `textArray`,
`GetIndent`, `AdjustRubyPositions`) đặt chú thích dựa trên **mảng dòng của
chính câu thoại**, tức là chuỗi được cắt theo `\n`. Nó **không** biết gì về
word-wrap tự động của TextMeshPro.

Kịch bản gốc tiếng Nhật ngắt dòng thủ công ở mọi câu (dòng nối tiếp bắt đầu
bằng `　`), nên hai bên luôn khớp. Bản dịch tiếng Việt gộp mỗi câu thành **một
dòng dài duy nhất** rồi để TMP tự xuống dòng — thế là ngay khi từ gốc bị đẩy
sang dòng sau, chú thích vẫn nằm lại chỗ cũ: **cao hơn một dòng và lệch hẳn
sang phải**, đúng như ảnh chụp `[Cherish'Châu ngọc]`.

Cách sửa: ngắt dòng cứng cho những câu có ruby, đúng chỗ TMP sẽ ngắt, tính
bằng metric font thật và luôn chừa một chút mép để TMP không còn gì để ngắt
nữa.

```powershell
python tools\wrap_ruby_lines.py            # chạy thử + xuất rubywrap_report.txt
python tools\wrap_ruby_lines.py --apply    # backup, vá, đóng gói lại
```

Chạy lại nhiều lần vô hại: câu nào đã có `\n` thì bỏ qua, và dòng cuối báo số
câu ruby mà TMP vẫn sẽ ngắt lại (phải là 0).

Backup: `_backup\scenario01.prerubywrap`.

## Thẻ ruby sai cú pháp

`python tools\fix_ruby_syntax.py [--apply]` — sửa 5 thẻ, **chỉ dấu câu**, không
đổi một chữ dịch nào. Backup `_backup\scenario01.prerubysyntax`.

| id | trước | sau | JP gốc |
|---|---|---|---|
| 108/txt/0174 | `[Châu Ngọc 'Cherish]` | `[Châu Ngọc'Cherish]` | `[珠玉'チェリッシュ]` |
| 75/txt/1089 | `[Hỏa Thủ' kỹ năng]` | `[Hỏa Thủ'kỹ năng]` | `[火守'スキル]` |
| 72/txt/0380 | `[dic no=252 text=điều chỉnh'tuning']` | bỏ `'` thừa | `[dic no=252 text=チューニング]` |
| 106/txt/1045 | `[見習い天使'Spirit']` | bỏ `'` thừa | `[見習い天使'スピリット]` |
| 95/txt/0236 | `[dic no=361 text=Fallin' Gals]` | `Fallin’ Gals` (U+2019) | `[dic no=361 text=フォーリンギャルズ]` |

Cái cuối không phải ruby mà là tên ban nhạc. Engine tách thẻ theo `'`, nên nó
render thành "Fallin" với "Gals" lơ lửng bên trên. Đổi sang dấu nháy cong
U+2019 mà phần còn lại của bản dịch vẫn dùng thì giữ nguyên tên và mất ruby ma.

Sửa thẻ làm đổi bề rộng, nên script **ngắt dòng lại từ đầu** cho những câu đó.

## Ký tự `っ` sót trong dòng thoại đã dịch

`python tools\fix_sokuon_lines.py [--apply]` — `っ` cuối câu là dấu nghẹn của
tiếng Nhật (tiếng hụt hơi), không phải chữ có nghĩa; ba dòng bị giữ nguyên khi
dịch. Backup `_backup\scenario01.presokuon`.

| id sheet | entry | trước | sau |
|---|---|---|---|
| `89/txt/0047` | 30 | `「Kogasaki? ―...っ!?」` | `「Kogasaki...!?」` |
| `95/txt/0579` | 36 | `「......っ」` / `「...っ」` | `「......」` |
| `125/txt/0133` | 66 | `「...っ, Ờ.」` | `「...Ờ.」` |

Sheet đã sửa cả ba từ trước (`UNLOGICAL_v2 (5).xlsx`: **0 ô tiếng Việt nào còn
`っ`/`ッ`**), nên đây là merge xuôi chiều, không tự chế bản sửa. Sheet đổi nhiều
hơn là chỉ bỏ `っ`: dòng 30 bỏ luôn `? ―`, dòng 66 bỏ dấu phẩy.

> ### Merge chỉ chạm `text[]`, không chạm `scriptText`
>
> Đợt merge trước đã cập nhật `text[]` của cả ba slot nhưng **bỏ sót bản sao
> trong `scriptText`**, để lại hai bản lệch nhau. `check_scripts.py` không bắt
> được (nó soát 143 script chương, không soát `ScenarioData`), và đọc bản dịch
> cũng không thấy vì `text[]` đã đúng. Entry 36 còn lệch sẵn từ trước đó nữa:
> `text[579]` 6 chấm còn `scriptText` 3 chấm — thay theo kiểu tìm nguyên câu sẽ
> trượt một trong hai.
>
> Sau mỗi đợt merge, soát chéo `text[j]` với dòng tương ứng trong `scriptText`.

Script chặn trước khi ghi nếu `text[]` chưa khớp giá trị đích, và sau khi ghi thì
khẳng định hai bản trùng nhau từng ký tự.

> **Ba dòng `「っ！？」` ở entry 3/4/5 giữ nguyên** — đó là khối tiếng Nhật chưa
> dịch (96,8% số dòng vẫn là kana/kanji), không phải chữ sót. Tiêu chí lọc phải là
> "ký tự Nhật **duy nhất** của dòng là `っ`/`ッ`"; lỏng hơn thế thì 96 dòng
> `にっこり` (từ khoá biểu cảm sprite trong tham số lệnh) sẽ báo nhầm.

Đã chạy 16/08/2026, `check_scripts.py` và `check_chapterdata.py` đều PASS sau đó.

## Còn tồn (KHÔNG tự sửa)

23 thẻ vẫn còn tiếng Nhật ở vế gốc. Đã tra `UNLOGICAL_v2 (1).xlsx`: **cả 23
dòng đều có trong sheet và đều mang đúng thẻ hỏng đó** — lỗi nằm ở nguồn, phải
sửa trên sheet rồi merge xuống, không sửa ở romfs.

Danh sách in bằng script kiểm kê trong log phiên làm việc; nhóm chính:
`[見習い天使'スピリット]` ×7, `[停止'Kỹ năng]` ×2, `[調停'Kỹ năng]` ×2,
`[珠玉'Cherish]` ×2, `[運営'…]` ×2, `[交換手'…]` ×2, `[鏡界'リコレクション]`,
`[珠玉'チェリッシュ]`, `[仮想世界'thế giới bên kia]`, `[見習い天使'Spirit]`,
`[ＦＢ'Feedback]`, `[ＫｉＥＬ'Kiel]`.

## Kéo một nhóm ô từ sheet xuống (merge có lọc)

`python tools\apply_sheet_cells.py [--new=X.xlsx] [--base=Y.xlsx] --match=<regex> [--apply]`
— dùng cho vòng phổ biến nhất: "đã sửa một thuật ngữ trên sheet, đây là bản
export". Không phải merge toàn bộ; `--match` giới hạn đúng những ô muốn lấy nên một
đợt sửa thuật ngữ không kéo theo mọi thay đổi khác. Không truyền `--new/--base` thì
tự lấy hai snapshot mới nhất trong `D:\Downloads\UNLOGICAL_v2*.xlsx` theo mtime.

Ba chiều như memory merge đã ghi (`new == build` → bỏ qua, `base == build` → áp,
cả hai đổi → **báo rồi bỏ qua**), và trước khi ghi từng ô có bốn chốt: multiset tag
`[...]` phải khớp, `[主人公]` phải cùng có hoặc cùng không, dấu ngoặc phải cân, và
**ngắt dòng cứng lấy từ build chứ không lấy từ sheet** (cột sd_* là một dòng phẳng;
ghi nguyên văn là làm phẳng bố cục — đã từng mất 1.530 ngắt dòng vì việc này).
Khoá lấy đúng cột ID của sheet: `76/txt/0011` → `ScenarioData` scenarioID 76
`text[11]`; `TerminalHomeAlertData/alert/id71` → asset/field/id trong bundle `json`.

**Vòng "mainframe" 17/08/2026** (snapshot `(23)` so với `(22)`, backup
`_backup\scenario01.UNLOGICAL_v2(23)`, `_backup\json.UNLOGICAL_v2(23)`):

- Đếm trước khi sửa: `Mainframe` 13 chỗ hiển thị / `máy chủ chính` 7 chỗ, mà **cả
  14 chỗ trong thoại đều dịch từ cùng một chữ `メインフレーム`**.
- Sheet đổi 6 ô thoại + 1 alert; áp hết. `113/0055` và `127/0283` giữ nguyên là
  đúng — bản Nhật ở đó là 主要システム / メインシステム, không phải メインフレーム.
- Hai chỗ không có tab trên sheet nên sửa ở build: mục từ điển `no=402` đảo
  title/ruby thành `Mainframe` + `MÁY CHỦ CHÍNH` (ngược quy ước "title tiếng Việt,
  ruby tiếng Anh" của 5 mục kia, nhưng khớp với chữ người chơi bấm vào:
  `[dic no=402 text=Mainframe]`), và `ChapterData` vốn đã dùng đúng thuật ngữ.
- `TerminalHomeAlertData` id71 "Hệ thống chính (Mainframe) đã bị xóa" →
  "Mainframe đã bị xóa", khớp luôn với `[terinfo]` của cùng sự kiện trong
  `03_05_01` — trước đó hai chỗ cùng một thông báo mà viết khác nhau.
- Sau cùng: `máy chủ chính` còn **0** chỗ trong cả build (kể cả bản sao
  `scriptText`, dọn thêm 2 chỗ ở sID 76/90 vì mirror không khớp verbatim).
- Còn lại **8 `Mainframe` / 6 `mainframe`** trong thoại — hoa khi là danh xưng
  ("Mainframe Angelica", "từ Mainframe"), thường khi là danh từ chung ("hệ thống
  mainframe"). Đó là cách sheet đang viết; muốn nhất quán một kiểu thì sửa trên
  sheet rồi chạy lại tool này.

### Snapshot bị tải đè lên cùng tên — vòng `(32)` lần hai, 18/08/2026

`(32).xlsx` được **export lại tại chỗ** lúc 14:11 ngày 18/08, sau khi vòng `(32)` lần đầu đã
merge xong (backup `scenario01.UNLOGICAL_v2(32)` lúc 22:29 ngày 17/08). Hai nội dung khác
nhau **670 ô**. Bản export đã merge không còn trên disk, nên **không có snapshot nào đại diện
cho bản nền của build** — đó là nguồn của 26 xung đột giả.

Ba bản vá sinh ra từ vòng này:

- **Làm phẳng `\n` của sheet ngay trong `read_sheet()`.** Tool so ba chiều trên bản đã làm
  phẳng *phía build* (`cur.replace("\n", " ")`) nhưng để nguyên `bv`/`nv`. 56/41.247 ô của
  `(32)` có `\n` thật, và những ô đó **không bao giờ** khớp được → báo "cả hai bên đổi" oan.
  `80/txt/0166` là ca thật: chỉ sheet đổi (`‘ ’` cong → `"`), build không ai chạm.
  `carry_breaks()` cũng giả định phía mới là một dòng phẳng nên để `\n` sống tới đó là chồng
  ngắt dòng.
- **`backup_path()` — không bao giờ bỏ qua backup vì tên đã tồn tại.** Tên backup lấy từ tên
  file snapshot, mà người dùng tải lại đè lên cùng tên (memory: "N là thứ tự tải, không phải
  thời gian"). Tên trùng nghĩa là *vòng trước cùng tên sheet*; bỏ qua là mất đúng cái mốc để
  lùi một bước. Giờ thêm hậu tố `-2`, `-3`… Vòng này sinh `scenario01.UNLOGICAL_v2(32)-2`
  (517 ô) và `-3` (27 ô lấy theo sheet).
- **`--take-sheet=id,id,…`** — áp ô mà build cũng đã đổi, sau khi người đã xem. Vẫn qua đủ
  các chốt khác; chỉ bỏ *một* điều kiện "build chưa ai sửa". Phải liệt kê id tường minh,
  không có chế độ "lấy tất".

Phân loại 27 ô bị chặn — gấp dấu nháy + khoảng trắng rồi so:

| nhóm | số | xử lý |
|---|---|---|
| chỉ khác dấu nháy (`'…'` build vs `"…"` sheet) | 22 | lấy sheet — upstream, và `"` là quy ước đa số |
| áp thì mất thụt treo `　` | 4 | lấy sheet rồi `fix_novel_list_wrap.py --apply` (nó dựng lại đúng 4 khối) |
| khác chữ thật | 1 | `71/txt/1133`, sheet thêm ngoặc mở còn thiếu + hoa `Chẳng` → lấy sheet |

Tổng vòng: **544 ô ScenarioData + 1 trang rule_body**. Sheet cũng mang luôn 5 chỗ `thiết bị`
trần thành `terminal` (viết thường) — `fix_terminal_term.py --apply` hạ về `Terminal`, đúng
lý do gate đó có mặt trong danh sách chốt.

Ba trang `rule_body` id30/44/45 vẫn bị chặn đúng: build đã là `Terminal`, sheet vẫn `terminal`.
id46 lệch số dòng (build 9 / sheet 10 — sheet thêm một dòng trắng) **và** vẫn `qua thiết bị`
**và** đổi `kỹ năng` thành `skill`. Ba việc phải sửa trên sheet.

### Tab `TerminalRuleData` map theo (id, trang), và đừng lấy khoảng trắng của sheet

`rule_body/idN` **lặp một hàng cho mỗi trang** của id đó (39 hàng / 21 id), nên hàng
thứ k là `content[k].text` của item id N — nhét vào dict theo id là gộp mất, đúng cái
bẫy memory đã ghi. `read_rule_rows()` giữ thứ tự hàng, `merge_rule_text()` lấy **câu
chữ** của sheet nhưng **giữ khoảng trắng đầu dòng của build**: sheet đã rã hết `　`
thành một space ASCII và biến dòng trắng thành một dấu cách, áp nguyên văn là ép thụt
lề còn 1/3 và phá bậc bullet. Số dòng hai bên lệch thì bỏ qua, và có chốt riêng: số
`　` không được giảm.

**Chốt ba chiều 18/08/2026** — nhánh này vốn *thiếu* nó, khác nhánh ScenarioData: nó
chỉ hỏi "sheet có đổi không", không hỏi "build có ai sửa chưa", nên một bản sửa làm
thẳng trên build bị vòng merge sau **âm thầm lật lại**. Bắt được vì
`fix_terminal_term.py` đổi id30/44/45 thành `Terminal` mà sheet vẫn ghi `terminal`:
chạy lại `apply_sheet_cells.py` là hạ ngay chữ hoa xuống. Cách kiểm không cần thêm dữ
liệu — chạy `merge_rule_text(cur, sheet_nền)`: ra đúng `cur` thì build chưa ai sửa,
khác `cur` thì hai bên đều đổi → in diff `nền` vs `build` rồi bỏ qua.

Cùng vòng đó, nhánh `*Data/field/idN` đổi `ent.get(field, "")` thành lỗi rõ ràng khi
field không tồn tại: sheet ghi `TerminalControlSkillData/skill_desc/id0` mà field thật
tên là `caption`, nên tool đọc `""` và báo "build trống / cả hai bên đổi" — nghe như
build bị mất chữ, thật ra chữ vẫn còn nguyên.

Vòng `(31)` 17/08/2026 (backup `_backup\json.UNLOGICAL_v2(31)`): 7 trang, đổi
`<…>` → `(…)` cho phần gloss tiếng Anh (`<Player>` → `(Player)`, `<Selector>`,
`<Recollection>`, `<Cherish>`, `<Recollector>`, `<Báo Đen>`, `<Thỏ Con>`) cộng vài
dòng bị xoá space cuối dòng. Ngoặc đơn hẹp hơn ngoặc nhọn (20,9 so với 35,3 đơn vị
font) nên **không dòng nào rộng thêm**; id47 còn hẹp đi 33 px.

Ba dòng của trang RULE đang rộng hơn mốc đã xác nhận trong game (1207 px theo công
thức đúng): `id51` trang 2 = 1284, `id46` trang 1 = 1277, `id60` trang 0 = 1232. Cả
ba có từ trước, không phải do vòng này; nếu muốn chắc thì chụp ba trang đó xem có bị
cắt không.

> Merge vòng này cũng **làm phẳng lại một chỗ `... ...`** (ô `70/txt/1164`) — đúng lý
> do phải chạy `fix_ellipsis_break.py --apply` sau mỗi merge. Chốt `--check` bắt được
> ngay.

### Vòng "Selector" 17/08/2026 — và hai chốt sinh ra từ nó

Snapshot `(24)` đảo `[Người lựa chọn'Selector]` → `[Selector'Người lựa chọn]` ở 72 ô,
`(27)` sửa thêm 3 ô chữ. Backup `_backup\scenario01.UNLOGICAL_v2(24)`,
`scenario01.UNLOGICAL_v2(27)`, `scenario01.selectorscript`.

Hai chốt phải nới/thêm vì vòng này:

- **Chốt tag phải phân biệt khoá tra cứu với chữ hiển thị.** Bản đầu chặn cả 72 ô vì
  nội dung tag đổi. Nhưng `[gốc'ruby]` thì **cả hai nửa đều là chữ hiển thị**, đảo
  chúng là hợp lệ; còn `[dic no=N text=X]` chỉ `no` là khoá. `tag_key()` so ruby
  theo *tập hợp* (đảo thì qua, sửa nội dung một nửa vẫn bị chặn).
- **Chốt "bản dịch rơi vào sai ô".** Snapshot `(24)` có ô `71/txt/0379` bị dán đè
  bằng bản dịch của `0377` (bản Nhật hai ô khác nhau hoàn toàn). `duplicate_paste()`
  bắt bằng cách nhóm các ô đổi theo bản dịch mới: nhóm nào có ≥2 ô mà bản Nhật khác
  nhau thì ô nào *khác xa bản cũ của chính nó* là ô bị dán đè — chặn nó, giữ ô lành.
  Người dùng sửa lại trên sheet, snapshot `(27)` đã đúng và còn thêm dấu ngoặc.
- Nền để so cũng phải chọn đúng: ô `0379` phải merge với nền `(23)` chứ không phải
  `(24)`, vì `(24)` chính là snapshot chứa bản dán đè.
- So ba chiều phải so trên **bản đã làm phẳng** (`\n` → space): build giữ ngắt dòng
  mà sheet thì không, so nguyên văn sẽ báo "cả hai bên đổi" cho cả ô vốn đã đúng.

**Vòng `(28)`: bỏ hẳn tag ruby**, giữ loanword làm chữ thường — 126 ô
(`[Selector'Người lựa chọn]` → `Selector` 72 ô, `[Thiên thần tập sự'Spirit]` →
`Spirit` 54 ô), cộng 38 tag còn sót trong `scriptText`. Backup
`_backup\scenario01.UNLOGICAL_v2(28)`, `scenario01.rubydropscript`.

Chốt tag lại phải nới lần nữa, nhưng theo kiểu **có điều kiện kiểm được**: tag ruby
được phép giữ nguyên, **đảo**, hoặc **biến mất miễn là một nửa của nó còn lại trong
câu**; mất tag mà cả hai nửa cũng mất thì vẫn bị chặn (đó là xoá hụt). Song song đó
tách hai loại chốt cứng ra: lệnh diễn xuất / `[主人公]` / `[se file=…]` phải khớp
từng cái, và **`no=` của mọi link `[dic …]` không được đổi hay mất** — chữ hiển thị
trong link thì tuỳ.

Sau vòng này thoại còn lẫn: `Spirit` 281 chỗ / "Thiên thần tập sự" **19 chỗ** (sID 69
`text[300]`, và 18 chỗ trong sID 81), `Selector` 146 chỗ / "Người lựa chọn" **1 chỗ**
(`85/txt/1136`). Toàn bộ nằm trong dữ liệu sheet nên sửa ở sheet rồi kéo xuống.

### Tiêu đề từ điển: loanword hay tiếng Việt? — đếm chữ CHÍNH trong thoại

Quy ước cũ là "title tiếng Việt, ruby tiếng Anh", nhưng 3 mục (`354` Bug, `505` Log,
`402` Mainframe) vốn đã ngược lại vì thoại viết thẳng loanword. Cách phân định không
phải cảm tính mà đếm được: **đếm thuật ngữ trong chữ chính của thoại** (bỏ phần ruby
ra, vì ruby chỉ là chú thích nhỏ phía trên).

Đo 17/08/2026 trên 25 mục có ruby Latin (backup `_backup\json.dicloanwordfirst`):

| mục | title cũ | title× | loan× | xử lý |
|---|---|---|---|---|
| 212 | Thiên thần tập sự | 78 | **227** | đảo → `Spirit` / ruby `THIÊN THẦN TẬP SỰ` |
| 362 | Tiện ích bổ sung | 0 | 5 | đảo → `Plugin` |
| 400 | Sự tương thích | 2 | 4 | đảo → `Matching` |
| 211 | Học sâu | 2 | 4 | đảo → `Deep Learning` |
| **112** | **Ban điều hành** | **271** | 141 | **giữ tiếng Việt** |

Con số 112 bác đúng cái tôi đã đề xuất trước đó (đảo cho khớp mục 402): thoại vẫn
viết "ban điều hành" nhiều gấp đôi "Operator", nên đảo tiêu đề là làm nó lệch khỏi
thoại. 20 mục còn lại thoại dùng tiếng Việt hoặc gần như không nhắc tới → giữ.

Đếm phải bỏ ruby ra mới đúng: tính cả ruby thì `212` ra 281 và `112` ra 175, đủ để
kết luận sai ở những mục mà loanword chỉ xuất hiện *bên trong* tag ruby.

### Vòng "Terminal" 18/08/2026 — và ba chỗ sheet không với tới

`python tools\fix_terminal_term.py [--apply] [--check] [--report]`

Bắt đầu từ một ảnh chụp máy thật: băng-rôn tím trong cảnh sID 71 vẫn là
`ターミナルを開いてください` (art nướng trong tranh, không phải TMP text), mà thoại ngay
trên nó thì viết "mở thiết bị đầu cuối lên". Đếm ra build đang **chia ba**:
`text[]` có 73 "thiết bị đầu cuối" / 36 "Terminal", `selText` 2 "thiết bị đầu cuối",
`TerminalRuleData` viết "thiết bị" và "thiết bị (terminal)".

Không có mục từ điển nào neo thuật ngữ này: **80/80 mục không có `ターミナル`**, và
không `no=` nào trong 85 link `[dic …]` của `ScenarioData` trỏ tới nó. Nên khác vòng
"mainframe", ở đây không có tiêu đề từ điển để đối chiếu — chốt bằng cách chọn dạng
danh xưng, đúng như câu game dùng để *đặt tên* cho nó
(`「Đây là 『Terminal』。Là bảng menu hệ thống…」`, sID 69).

Sheet `(32)` (nền `(31)`) đổi **118 ô `text[]`** + 8 trang `rule_body`; backup
`_backup\scenario01.UNLOGICAL_v2(32)`, `_backup\json.UNLOGICAL_v2(32)`. Còn ba chỗ
sheet **không mang được**, đó là việc của tool này (backup
`_backup\scenario01.terminalterm`, `_backup\json.terminalterm`):

| chỗ | vì sao sheet không với tới | số |
|---|---|---|
| `selText[]` | ~~không có cột nào trên sheet~~ — **SAI**, sheet có 449 hàng `sel`, chỉ là `read_sheet` bỏ im lặng (xem mục dưới) | 2 ô |
| `scriptText` | `apply_sheet_cells.py` bỏ mirror khi chuỗi cũ khớp ≠1 lần | 24 script |
| `TerminalRuleData` | sheet ghi "terminal" chữ thường; id46 lệch số dòng nên bị bỏ | 4 trang |

Hai luật quét (`thiết bị đầu cuối` → `Terminal`; `terminal` đứng riêng → `Terminal`)
cộng bảng `PLAN` cho chỗ một lần — `id46` trang 1 gọi là "thiết bị" mà bản Nhật là
`ターミナルから『犯人投票』を行う`.

**Không quét `thiết bị` đứng một mình.** 85 chỗ trong `text[]`, và quá nửa là thiết bị
thật: `thiết bị y tế`, `thiết bị điện tử`, `thiết bị nghe lén`, `thiết bị VR`,
`thiết bị định vị`, `thiết bị mạng`. Số còn lại (`thiết bị cầm tay`,
`thiết bị của Ran`, `mở thiết bị lên`, `thao tác trên thiết bị`) đúng là Terminal
nhưng phải xem từng câu — `--report` in ra danh sách đã lọc bớt nhóm rõ ràng không
phải. Hai chỗ `thiết bị Terminal` (`85/txt/0764`, `0960`) giờ thừa chữ.

Chốt: đổi tên làm chuỗi **ngắn đi** (17 ký tự → 8) nên không có rủi ro tràn khung;
`check_layout_breaks` xác nhận 209.819 → 209.819 ngắt dòng, 17.425 → 17.425 dòng thụt.

### Từ điển lên sheet (`export_dictionary_sheet.py`) — và khoá `no` không phải `id`

`python tools\export_dictionary_sheet.py [--out=D:\Downloads\DictionaryData_sheet.xlsx]`

`DictionaryData` là asset còn chữ để dịch duy nhất mà **sheet không phủ**. Đo trên
snapshot `(42)`: 142 tab = `INDEX` + `Bảng Xưng Hô` + 131 tab `sd_*` + 9 tab `*Data`,
không tab nào cho từ điển; quét cả workbook bằng chuỗi đặc trưng của mục 102
(`プログラムで目的を達成するた`) ra **0 ô**. Cả 80 mục được dịch thẳng trên file bằng
`fix_dictionary_*.py`, nên chưa từng có bản trên sheet để đối chiếu.

Export ra **209 hàng** — 80 `dic_title` + 49 `dic_ruby` + 80 `dic_body`. Bỏ 31 hàng
ruby vì 31 mục **không có** field đó; ra hàng thì merge chỉ báo `không có field 'ruby'`.
`category` (あ/か/さ…) ra cột D làm thông tin, nằm ngoài vùng A/B/C mà `read_sheet` đọc —
đó là khoá phân tab あかさたな của màn ARCHIVE, không phải chữ để dịch.

**Ngắt dòng để nguyên Alt+Enter, không đổi thành `
` văn bản.** Tab `*Data` là bên sở
hữu bố cục: `read_sheet()` đổi Alt+Enter thành dấu `
` văn bản rồi `expand_breaks()`
mở lại. Round-trip đo được là **209/209 hàng khớp, 867/867 ngắt dòng** — an toàn vì 80
mục không có `　` thụt lề lẫn space cạnh ngắt dòng, hai thứ duy nhất mà regex gộp
khoảng trắng trong `read_sheet` sẽ ăn mất. Thân mục vốn do `fix_dictionary_wrap.py`
ngắt tay theo khung, làm phẳng là mất hết (xem "Nội dung từ điển bị ngắt dòng hai lần").

Để merge ngược lại được thì `apply_sheet_cells.py` phải sửa hai chỗ — **cùng một lớp
lỗi với mấy nhãn field sai đã làm 262 hàng "không bao giờ áp được" ở vòng `(37)`**:

- `FIELD_MAP` thêm `dic_title`→`title`, `dic_ruby`→`ruby`, `dic_body`→`text`. Không có
  thì `FIELD_MAP.get` rơi về `("data", "dic_title")` — sai tên field.
- **Khoá nhận dạng mục không phải asset nào cũng là `id`.** DictionaryData khoá bằng
  `no`, không có field `id` nào, nên `e.get("id") == eid` làm **mọi** hàng của tab từ
  điển báo "không có id N". Thêm `KEY_OF = {"DictionaryData": "no"}` và tra bằng
  `e.get(KEY_OF.get(asset, "id"))` — ở cả chỗ tra mục lẫn chỗ đọc lại sau khi ghi.
  Cột A vẫn giữ dạng `…/id<no>` cho khớp `DATA_ID`; chỗ đổi là trong code.

Chạy thử trên hai snapshot giả (nền = y hệt build, mới = 5 ô đổi có chủ đích):

| ô | sửa gì | kết quả |
|---|---|---|
| `dic_title/id102` | "Thuật toán" → "Giải thuật" | áp |
| `dic_ruby/id150` | điền vào ô ruby đang rỗng | áp |
| `dic_body/id102` | đổi 1 dòng, giữ bố cục | áp |
| `dic_body/id110` | làm phẳng, **không** đổi chữ | "đã có bản mới", bỏ qua |
| `dic_body/id110` | làm phẳng **và** đổi chữ | áp, `carry_breaks` dựng lại đúng 9 dòng |
| `dic_title/id111` | để trắng | chặn: "ô sheet trắng mà build đang có chữ" |

Làm phẳng đơn thuần không phá được bố cục: `flat_cur == nv` nên tool coi là không có gì
để áp. Ca thật đáng lo là *đổi chữ + làm phẳng*, và ca đó `carry_breaks` đắp lại ngắt
dòng của build — đo lại ra 9 dòng, dài nhất 22 ký tự, đúng như build.

**Còn tồn: 21 hàng `dic_ruby` sẽ làm đổ `--apply`.** Đường ghi thay chuỗi theo
`json.dumps(cur)` và đòi khớp **đúng 1 lần**, mà 21 mục có `ruby` là `""` → chuỗi cần
tìm là `""`, khớp **22 lần** trong raw. Điền ruby cho một trong 21 mục đó thì tool
`raise SystemExit("DictionaryData id150: chuỗi cũ khớp 22 lần")` — hỏng to tiếng, không
ghi rác, nhưng ô đó không xuống được. Sửa thì phải thay trong **phạm vi một mục** (neo
bằng `"no": <n>`, mỗi giá trị `no` chỉ xuất hiện một lần) chứ không thay trên cả file —
cùng lý do `ScenarioData` phải vá theo cả mảng `text[]` thay vì theo từng chuỗi. Chưa làm.

## 赤川夏音 = Sekigawa Kanon (`fix_sekigawa_name.py`)

`python tools/fix_sekigawa_name.py [--apply] [--report]`

Nguồn là chú thích của chính người viết game, `00_04` dòng 9019:

    ;//読み：赤川夏音（せきがわ かのん）

赤 đọc **せき** — đó là lý do chú thích tồn tại. Quét cả 143 script ra **47 chú thích
`;//読み：`, 40 nội dung khác nhau** — và **1 cái vắt sang dòng thứ hai** mà dòng vắt
không mang chữ `読み`, nên quét kiểu "tìm `読み` rồi đọc dòng dưới" là đọc thiếu
(`00_02:2719-2720`, năm tên). Đây là thẩm quyền cao nhất cho nhân vật phụ, trên cả sheet. Xem memory `unlogical-official-romanisation`.

Build trước khi sửa sai **hai lỗi cùng lúc**: `Sekigawa` xuất hiện **0 lần**, và tên
riêng có ba cách viết trong khi 夏音 = かのん = `Kanon`.

| chỗ | trước | sau |
|---|---|---|
| `ScenarioData.talkName` | `Akagawa Kanon` ×37 — dạng `【参加者の女性Ｅ/…】`, chỉ nửa PHẢI được vẽ | 37 ô |
| `ScenarioData.text` | `Akagawa` trơ 27, `Akagawa Kanon` 2, `Akagawa Kano` 4, `Kano` trơ 9 | 42 ô |
| `ScenarioData.scriptText` | bản sao không được vẽ | 6 sID |
| `ScenarioData.scriptText_Line` sID 70 dòng 2722 | `[terinfo text="…"]` | 1 ô |
| script chương `00_02` dòng 2723 | cùng dòng `[terinfo]` đó | 1 |
| `json` GenebarkChatMain / TerminalHomeAlert / GenebarkNote / ChapterData | có cả `Akagawa Kanane-san` | 9 lần |

Đối chiếu từng ô với bản Nhật (79 ô `text`/`talkName`): khớp **1:1** — không ô nào tên
bị chèn vào chỗ bản Nhật không có, không ô nào bị rơi. Cả game chỉ có **một** người họ
赤川, luôn đi với 夏音 hoặc さん.

### Ba cái bẫy của vòng này

**`\bKano\b` chạy trên raw JSON bỏ sót 2 chỗ.** `Kano` đứng ngay sau ngắt dòng cứng
thì raw là `
Kano`; chữ `n` của escape là ký tự từ nên ranh giới `\b` biến mất
(sID 106 `scriptText`). Nên tool sửa trên dữ liệu **đã parse** rồi ghi lại bằng cách
thay giá trị đã mã hoá, đúng lối `apply_sheet_cells.py`. Đã đo: mảng `text[]` của cả 6
target cần sửa (70, 72, 106, 107, 108, 115) mã hoá lại khớp đúng 1 lần; bốn target
khớp ≠1 lần (sID 3/4/5/12) là mảng rỗng/nhỏ và không chứa tên.

**Chốt tag không soát được theo dòng trên asset `json`.** Asset json là **một dòng duy
nhất**, nên regex `\[[^\[\]
]*\]` ăn luôn cặp `[...]` của cú pháp JSON và báo oan
(`TerminalHomeAlertData`: cả mảng 86 mục trên một dòng). Đường json phải parse rồi soát
theo **từng giá trị chuỗi**; chỉ script chương mới soát theo dòng.

**`scriptText_Line` sửa được, dù là chỗ "không được đụng".** Luật đó là về **số dòng**
(vì `loadLine[j]` index vào nó); dòng 2722 chỉ đổi ký tự trong `[terinfo text="…"]` nên
số dòng không đổi — tool assert lại độ dài mọi mảng và `loadLine` sau khi ghi. Dòng này
cũng đã được dịch từ một pass trước, không còn tiếng Nhật để giữ.

### Đo lại sau khi ghi

Backup `_backup\scenario01.sekigawa`, `_backup\json.sekigawa`. Tên **dài ra**
(`Akagawa`→`Sekigawa`, `Kano`→`Kanon`) nên phải soát bề rộng, tất cả đều đạt:

- `check_scripts` 143/143 lệnh + nhãn khớp bản gốc; `check_chapterdata` 8/8
- `check_layout_breaks` 210.972 → 210.972 ngắt dòng, 17.425 → 17.425 dòng thụt
- `fix_adv_wrap --check` 0 dòng chạm hoạ tiết; `fix_center_caption_wrap`,
  `fix_ellipsis_break`, `fix_paren_balance`, `fix_novel_list_wrap`, `fix_terminal_term`,
  `fix_profile_comment` đều PASS
- **nameplate**: `Sekigawa Kanon` = 372 px, xếp 26/98 tên; tên rộng nhất đang ship là
  `Kai Munakata@k_munakata2150` 742 px — gấp đôi, nên không có rủi ro tràn

### Lỗi dịch phát hiện kèm, KHÔNG sửa ở đây

Bản Nhật viết **赤川さん** (họ + さん) ở cả 9 chỗ mà bản dịch dùng **tên riêng** trơ
(`Kano` → giờ là `Kanon`): `106/txt/0251, 0264, 0293, 0297, 0300, 0310, 0335, 0339,
0343`. Gọi họ+さん là khoảng cách xã giao — nhân vật chính mới gặp cô này lần đầu — nên
gọi thẳng tên riêng là lệch sắc thái, và trong cùng một chương còn lẫn ba kiểu
("Sekigawa Kanon", "Kanon", "cô Kanon"). Đây là việc của sheet, không phải của tool
chính tả: tool chỉ sửa cách viết, giữ nguyên lựa chọn họ/tên của từng chỗ.

### Ô sheet phải sửa upstream — 48 ô

`--report` xuất `D:\Downloads\Sekigawa_sheet_todo.xlsx`: `tab | ID | đang là | sửa thành`.
Cột "sửa thành" là chính chữ của sheet đã áp cùng luật thay, **không** phải chữ của
build — để người sửa chỉ đổi cái tên chứ không bị đè mất câu chữ khác. Chủ yếu `sd_106`
và `sd_107`. Chưa sửa trên sheet thì mọi vòng merge sau sẽ báo "cả hai bên đổi" ở 48 ô
đó mãi (chặn, không âm thầm lật lại).

### ID sheet mà tool không đọc — 3003 hàng bị bỏ IM LẶNG

Phát hiện 27/08/2026, từ một câu hỏi "GenebarkChatMainData trong game khác sheet?".

`read_sheet()` chỉ nhận hai dạng ID: `SD_ID` = `<sID>/txt/<số>` và `DATA_ID` =
`<Asset>Data/<field>/id<số>`. Khoá không khớp bị `continue` **trần** — không in gì,
không đếm. Trên snapshot `(42)`: đọc được 38.244 ô, **bỏ 3003 ô mà không một chữ nào
báo ra**. Sửa những ô đó trên sheet thì không bao giờ xuống game, và không có dấu hiệu.

| dạng ID | số | map vào | lệch với build |
|---|---|---|---|
| `GenebarkChatMainData/{spk,chat}/g{gid}c{charID}_{N}` | **2388** (cả tab) | `data[N].speaker` / `.content`, `N` = **chỉ số tuyệt đối** trong `data[]` | 0 |
| `{sID}/sel/{idx}/{opt}` | **449** | `ScenarioData.selText[idx]`, parse JSON rồi lấy `["target"][opt]` | **6** |
| `{sID}/cmd/{n}` | **116** | tham số `[terinfo]` 64 / `[geninfo]` 46 / `[select_monitor]` 6 | **17** |
| `Q&AData/qa_title/g{g}_q{q}` | **50** | `Q&AData.list[g].title[q]` | 0 |

`gid` có thể là nhiều nhóm nối bằng `;` (`g23;24cユーリ_294`, 45 hàng mỗi cột) — đừng
viết regex chỉ ăn một số.

**Đã vá phần BÁO** (không phải phần ghi): `read_sheet` trả về `(ô, unknown)`, và
`report_unknown()` in ra dạng ID + số hàng + ví dụ + tab. Chỉ báo, không chặn — vòng
merge vẫn chạy y như cũ cho các ô đọc được (đã đối chứng `(42)` vs `(41)`: vẫn đúng 4
hàng `TerminalControlSkillData`, 0 ô áp).

**Chưa mở đường ghi, và có lý do phải cẩn thận: sheet có chỗ CŨ HƠN build.** 17 hàng
`cmd` sheet có mà build chưa có đều là bản cũ — chúng viết `Nagamori **Ai**` (chính lỗi
mà `check_chapterdata.py` có một check riêng để chặn: 藍 = **Ran**) và gọi "người **thất
bại**" trong khi build cùng `TerminalHomeAlertData` đã chốt "người **thua cuộc**". Vá
đường đọc rồi merge mù là kéo lỗi cũ ngược vào game.

6 chỗ `sel` lệch: 2 là câu chữ (`恋心` build "Ái tình" / sheet "Tình yêu"; `時間切れ`
"Hết thời gian" / "Đã hết thời gian"), 4 là quy ước dấu (`『Trân Châu』` / `"Trân Châu"`,
`...` / `............`) — phải chốt bên nào thắng trước khi ghi.

### GenebarkChatMainData: chữ khớp, ngắt dòng thì không

Câu chữ khớp sheet gần như hoàn hảo — căn theo cột bản Nhật thì **1194/1194 hàng khớp
đúng thứ tự file**; so nội dung ra giống 1190, build đi trước 4 (4 ô Sekigawa), khác 0,
cột `spk` khác 0. `spk` là **khoá** (`player` / `藍`), sheet để VN == JP — dịch nó là
làm hỏng chat.

Chỗ khác thật là bố cục: build **588/1194** ô có ngắt dòng cứng (bản Nhật 602), sheet
**0** — không Alt+Enter, không dấu `
` văn bản. Nên đọc trên sheet trông khác trong
game dù chữ y nguyên. Không nguy hiểm: sheet không khai bố cục thì `carry_breaks` đắp
lại ngắt dòng của build, và còn chốt chặn làm phẳng.


### Chat có HAI bản dịch độc lập — và sheet cũng vậy

Phát hiện 27/08/2026 từ "đoạn 'lẹ dữ' có trên build mà sheet không có".

Nội dung chat Genebark nằm ở **hai asset**, mỗi bên có ô sheet riêng và **bản dịch
riêng**:

| nơi | tab sheet | màn hình |
|---|---|---|
| `GenebarkChatMainData.data[N].content` | `GenebarkChatMainData-CAB-…` | app chat trong Genebark |
| `ScenarioData.text[j]` | `sd_*` | thoại ADV trong truyện |

Ví dụ gốc, JP `出るの早くない？笑　ちょっと待って`:

| | build | sheet |
|---|---|---|
| `ScenarioData` 72/txt/1454 | `Ra nhanh dữ vậy? haha. Chờ tôi tí.` | y hệt |
| `GenebarkChatMainData.data[184]` | `Ra nhanh thế? Haha, đợi tí` | y hệt |

Nên tra tab Genebark trên sheet thì "không thấy" câu đó — nó **có**, chỉ là chữ khác,
và ô tương ứng nằm ở `sd_072`.

**Quy mô: 96% các cặp lệch nhau.** Lấy những dòng có bản Nhật **duy nhất ở cả hai bên**
(184 cặp — bỏ những câu chung như `はーい` vì chúng khớp nhiều hàng, làm số thô phồng lên
294): **177 cặp hai bản dịch KHÁC nhau**, 7 cặp giống.

**Không phải lỗi merge.** So hai ô trên *chính sheet* ra **đúng 177 khác / 7 giống** —
cùng con số. Build phản ánh sheet trung thực ở cả hai bản. Đây là chuyện dịch upstream:
hai bản được dịch độc lập, nên cùng một tin nhắn đọc trong cảnh và đọc lại trong app
Genebark là hai câu khác nhau. Muốn thống nhất thì phải chốt bên nào thắng rồi sửa trên
sheet — build không phải chỗ sửa.


### Chốt: bản ADV lấy chữ của Genebark (`fix_chat_use_genebark.py`)

`python tools\fix_chat_use_genebark.py [--apply] [--report]` rồi **bắt buộc** đo lại
`fix_adv_wrap.py --check`.

Người dùng chốt 27/08/2026: **bản Genebark thắng**. Ba bằng chứng độc lập cùng chỉ về đó:

- **177/177 ô ADV có nameplate dạng tài khoản** (`【Suzuno@Sz_36iii】`, `【RAN@ran_n_rea4】`,
  `【Kai Munakata@k_munakata2150】`…). Đều là tin nhắn chat, không phải lời nói.
- **0/177 ô bản Nhật có `「」`** — nên bản ADV viết đầy đủ có dấu câu là lệch khỏi chính
  thứ nó đang mô phỏng.
- Ba ô mà chốt chặn thông thường sẽ chặn, cả ba đều cho thấy **bản ADV là bản sai**:
  `15/txt/0081` làm rơi token `[主人公]` mà bản Nhật có (`俺が直接[主人公]の家に行こうか？`);
  `115/txt/0253` và `0254` tự thêm `「」` mà bản Nhật không có.

Nên chốt chặn ở tool này **cho phép bản mới THÊM** tag/token, chỉ chặn khi *làm mất*. Chốt
ngoặc cần **ba** điều kiện cùng lúc (bản Nhật có **và** bản cũ có **và** bản mới mất): bản
đầu chỉ hỏi "bản Nhật có mà bản mới không" đã chặn oan `86/txt/0021` và `110/txt/0215`, hai
ô mà bản Nhật có `『』` nhưng **cả hai bản dịch** đều dùng `"…"` theo quy ước dấu câu.

**Ngắt dòng: ghi PHẲNG, không dùng `carry_breaks`.** 15 cặp viết lại hẳn (giống nhau <50%),
mà difflib đặt lại ngắt dòng theo *offset ký tự cũ* — vô nghĩa khi câu đã khác hẳn. Ngắt
dòng của bản Genebark cũng bỏ: nó ngắt cho bong bóng chat, không phải khung ADV rộng 1280.
Đo lại sau khi ghi phẳng, bằng chính `render()` của `fix_adv_wrap`: dòng rộng nhất
**1278 px** so với cap 1400/1344/1281 → **0 ô tràn, 0 ô bị hạ cỡ chữ** (đều còn 42.0), 82 ô
game tự ngắt nhiều dòng. Không ô nào có tag ruby nên auto-wrap không làm nhảy chú thích —
đó là điều kiện để được phép để phẳng.

Kết quả: **177 ô `text[]` đổi**, `scriptText` mirror được 143 / bỏ 34 (khớp ≠1 lần). Backup
`_backup\scenario01.chatgenebark`.

| kiểm | kết quả |
|---|---|
| `check_scripts` | PASS 143/143 lệnh + nhãn |
| `check_chapterdata` | PASS 8/8 |
| `fix_adv_wrap --check` | PASS 0 dòng chạm hoạ tiết |
| ellipsis / paren / terminal_term / center_caption / novel_list | PASS |
| ô `text[]` trống | 229 → 229 (không sinh thêm) |
| token `[主人公]` | 833 → **834** (khôi phục đúng một ô) |
| 177 ô so lại với nguồn Genebark | 0 lệch |

**`check_layout_breaks` ĐỎ, và đỏ đúng dự kiến.** Đợt này chủ ý gỡ 83 ngắt dòng cứng. Đừng
tin mỗi chữ "FAIL" — phải chứng minh đỏ chỉ do việc mình làm. Cách chứng minh: so từng chuỗi
với backup và phân loại theo "có nằm trong tập ô mình sửa hay không". Đo ra: 177 ô `text[]`
đổi (77 ô mất ngắt dòng, 100 ô không), **0 chuỗi nào đổi ngoài tập đó**, tổng ngắt dòng
`text/talkName/selText` 7873 → 7790 = đúng 83. Phần `scriptText` còn lại là bản sao không
được vẽ.

**Còn tồn:** đây chỉ sửa phía build. Sheet vẫn giữ hai bản khác nhau ở `sd_*`, nên vòng merge
sau sẽ báo "cả hai bên đổi" ở 177 ô (chặn, không âm thầm lật lại). Sửa hẳn thì phải dán chữ
của tab Genebark sang cột D của các tab `sd_*` tương ứng — danh sách ở
`D:\Downloads\Chat_lech_Genebark_vs_ADV.xlsx`, cột "chốt bên nào?" giờ đọc là "Genebark".

### `scriptText_Line` sID 72 mất một dòng, nhưng `loadLine` đã được đánh số lại

Cùng lần soi trên. Stock 11255 dòng / build 11254: dòng bị xoá là
`[env カメラ移動 xpos=0 ypos=0 zpos=0 time=0]` ở stock index 3234 — một lệnh reset camera
xuất hiện **58 lần** trong chính script đó, không phải nội dung riêng.

Đáng lẽ đây là chỗ "không được đụng" vì `loadLine[j]` index vào nó. Nhưng đo ra là
**nhất quán**: 425 phần tử `loadLine` trước chỗ xoá giữ nguyên, 1085 phần tử sau chỗ xoá
**trừ đúng 1**. Nên mapping không hỏng. Kiểm bằng bất biến
`scriptText_Line[loadLine[j]]` == câu Nhật của `text[j]`: stock đúng 5171/39.574, build
**cũng đúng 5171** — không mất chỗ nào; riêng sID 72 là 123 ở cả hai bên.

Bài học: `check_scripts.py` **không** bắt được chuyện này (nó chỉ đọc 143 TextAsset script
chương, không đọc `ScenarioData.scriptText_Line`). Nếu ai xoá dòng mà quên đánh số lại
`loadLine` thì không có chốt nào phát hiện. Phép kiểm dùng ở trên là cái chốt đó.

## Tin nhắn bị cắt mất đầu câu (dấu `（` lẻ)

`python tools\fix_paren_balance.py [--apply] [--check]`

Lớp lỗi vô hình: bản dịch mất mệnh đề đầu, câu vẫn đọc trôi, chỉ dấu `）` lẻ là tố giác.
`guards()` của `apply_sheet_cells.py` cân `"`, `「」`, `『』` nhưng **không** cân ngoặc đơn.

Nhận diện chính xác cần hai điều kiện, và **phải gộp hai độ rộng ngoặc**:

```
số  ） + )  >  số  （ + (     trong bản dịch
VÀ  bản Nhật của đúng tin nhắn đó có một cặp đầy đủ
```

Điều kiện hai loại emoticon: `75/txt/0044` "Gì vậy, tự dưng hỏi thế **=))**" dịch từ
`なに、いきなり笑` — bản Nhật không có ngoặc nào nên không bị bắt. Gộp độ rộng thì bắt buộc:
bản dịch quen dùng `(` nửa rộng ở chỗ bản Nhật dùng `（`, đếm tách theo từng cặp bỏ sót
đúng **3/4** ô lỗi.

Đo 18/08/2026 trên 39.803 tin nhắn: **5 ô lệch, 4 lỗi thật**, cả 4 cùng một kiểu (mất `（`)
và **cả 4 đã bị cắt sẵn trên sheet** — cột Nhật của sheet vẫn nguyên, chỉ cột dịch mất cụm
đầu, nên chữa gốc là chữa upstream.

| ô | bản dịch trong build | bản Nhật |
|---|---|---|
| `126/txt/0269` | `Nhưng giờ Yuri đang bận, nếu mình giữ…` | `（でも、ユーリさんは仕事が忙しいし` ⏎ `　遅くまで…かな）` |
| `85/txt/1353` | `lúc nào trông cũng thảnh thơi quá nhỉ...)` | `（このひとは、いつ見ても気楽だな……）` |
| `85/txt/1429` | `Kai lại...)` | `（……なんで、戒くんが……）` |
| `85/txt/1431` | `anh Yuri có thể sẽ phải mất mạng sao?)` | `（現実でユーリさんが死ぬかもしれないって、` ⏎ `　わかってるのに？）` |

`--apply` chỉ chữa ô đã **đủ chữ**, liệt kê tường minh trong `PLAN`. Đã chạy 18/08/2026
(backup `_backup\scenario01.parenbalance`): 1 ô — `126/txt/0269`, snapshot (32) cấp đủ câu
nên chỉ cần thêm `（` và dựng lại ngắt dòng + thụt `　` theo bản Nhật. Ba ô kia thiếu chữ,
tool không đoán — `--check` exit 1 cho tới khi sheet được sửa.

> Ô này còn là ví dụ cho chuyện `check_layout_breaks` báo "MẤT THỤT LỀ" mà thực ra là
> **sửa đúng**: bản cũ `' nếu mình giữ…'` mở đầu bằng một space rác (di chứng của việc bị
> cắt), tool đếm space đó là dòng thụt. Đừng vá ngược theo cảnh báo mà không xem bản Nhật.

## Caption giữa màn (`[textmode=5]`) — lề thật không phải mép khung

`python tools\fix_center_caption_wrap.py [--apply] [--check]`

Widget: `level10` pid **898** `RenderCanvas_Final/EXTRALayer/EXTRAText` — rect **1920×720**,
cỡ 39, charSpacing 3,8, `m_HorizontalAlignment=2` (giữa), `m_VerticalAlignment=512` (giữa),
`m_TextWrappingMode=1` (wrap BẬT), `m_overflowMode=0` (Overflow). Nhận diện bằng cách loại
trừ trên ảnh chụp máy thật: ảnh cho **một dòng** nằm **đúng giữa** theo trục dọc, trong khi
`Message(Novel2)` (1600×720, canh **trên**) sẽ phải wrap dòng đó thành 2 và `Message(Novel)`
canh trái. `[textmode=5]` = `;//演出：ノベルモード　黒背景に白文字を中央表示`.

Engine **không vẽ `「」`** ở chế độ này — hai đầu dòng trên ảnh sạch, chữ mở đầu bằng `...`
và kết thúc bằng `này.`. Chi tiết này đổi số đo 83 px (1904 → 1821), đủ để đảo kết luận.

**Cái bẫy: rect 1920 = đúng bằng cả canvas, nên "vừa khung" không bảo vệ gì.** Chữ chạy sát
mép màn vẫn tính là vừa khung. Giới hạn thật là **lề an toàn**, và trong game có mốc sẵn —
watermark tam giác UL ở góc dưới-phải:

    tam giác UL: x 1725..1842, y 930..1050  ->  lề phải 78 px
    vùng an toàn = 1920 - 2 x 78 = 1764 px

`71/txt/0344` rộng 1821 px = **95% khung** nhưng **103% lề an toàn**. Bản Nhật
`……可哀想。こんなに泣いて、傷ついて` chỉ ~750 px = 43% lề — chưa bao giờ tới gần, nên đây là
vấn đề độ dài bản dịch.

> **Sai số đã mắc, ghi để không lặp:** lần đầu tôi suy lề này từ ảnh chụp điện thoại IMG_7147
> và ra **184 px** (vùng an toàn 1552) — hơn gấp đôi. Mép LCD tối, lẫn với bezel và ốp nhựa,
> nên chỗ tôi nhận là "mép màn" thực ra là mép ốp. Ảnh chụp Ryujinx thay thế hẳn phép đo đó.
> Ảnh chụp tay **vẫn dùng được cho phần tương đối** trong cùng ảnh (nó nói đúng rằng chữ lấn
> qua tam giác ~22 px), nhưng không dùng cho số tuyệt đối. Cũng nhớ: quét từng hàng mới tách
> được **tam giác** (mép 1842) khỏi **chữ ©BROCCOLI** (chìa thêm ~60 px) — chỉ có ở màn ADV.

**Ngắt theo DẤU CÂU, không cân độ dài.** Cân bằng cho ra chỗ ngắt giữa câu, đọc gãy; dấu câu
thì trùng nhịp bản gốc. Kiểm được: `71/txt/0345` ngắt ra **đúng chỗ bản Nhật tự ngắt**
(`大切な人を失うのはつらいでしょ？` / `　こんな風に死んでほしくはないでしょ？`).

Đã chạy 18/08/2026 (backup `_backup\scenario01.centercaption`):

| ô | trước | sau |
|---|---|---|
| `71/txt/0344` | 1821 px (103%) | 488 px (28%) + 1318 px (75%) |
| `71/txt/0345` | 2592 px (147%) | 1232 px (70%) + 1344 px (76%) |
| `71/txt/0346` | 754 px (43%) | không cần |

Khung cao 720 px với bước dòng 61,6 px = chỗ cho **11 dòng**, nên ngắt không tốn gì.

Tool **tự dò lại chỗ ngắt từ câu chữ hiện tại** nên chạy lại được sau mỗi merge (sheet làm
phẳng `\n` mỗi vòng); `PLAN` chỉ ghi *id ô*. **Hạn chế đã biết:** chưa quét được cả chế độ vì
chưa biết engine reset `textmode` ở lệnh nào — dò ngược tới `[textmode=5]` gần nhất cho ra ca
cách **2593 dòng script**, tức có thứ khác `[textmode=N]` đang reset mode. Ô nào xác định chắc
thì thêm vào `PLAN`.

## Ô SHORT STORY rộng hơn lề watermark — thu rect một float

`python tools\fix_ss_box_width.py [--apply] [--revert]`

`[textmode=4]` = chế độ short story, vẽ bởi `level10` TMP pid **893**
`RenderCanvas_Final/Message(SS)/SSText`, RectTransform pid **719**: rect **1700×944,28**,
`m_AnchoredPosition (-787, 437)`, `m_Pivot (0, 1)`. Trên canvas 1920 hộp nằm ở **x 173..1873**
— lề trái 173 px mà **lề phải chỉ 47 px**, lệch hẳn. Watermark tam giác UL có lề phải **78 px**
(x 1725..1842), nên hộp rộng hơn lề cho phép **31 px**.

TMP wrap đúng ở rect và không biết gì về watermark, nên dòng nào đầy sẽ dừng ở 1699,x = mép
1873. Đo trên build: **348 / 2 872 dòng (12,1%)** của 15 script short story lấn qua tam giác,
và **tất cả** đều dồn sát 1699,x — dấu hiệu kinh điển của "rect là thứ giới hạn, không phải
câu chữ".

| rect | tổng dòng | dòng lấn | thêm dòng | mép phải |
|---|---|---|---|---|
| 1700 (cũ) | 2 872 | 348 | — | 1873 |
| 1690 | 2 883 | 221 | +11 | 1863 |
| 1680 | 2 890 | 128 | +18 | 1853 |
| **1669** | **2 896** | **0** | **+24** | **1842** |
| 1650 | 2 905 | 0 | +33 | 1823 |
| 1574 (cân lề trái) | 3 020 | 0 | +148 | 1747 |

**Đã chốt: lề trái 120, mép phải 1842 → rect 1722** (`--left=120`, áp 18/08/2026).

| lề trái | rect | dòng | qua 1842 | trang >16 slot | đụng biên nghiêng |
|---|---|---|---|---|---|
| 173 (gốc) | 1700 | 2 872 | 348 | 2 | — |
| 173 | 1669 | 2 896 | 0 | 2 | 3 (tệ nhất +22) |
| **120** | **1722** | **2 850** | **0** | **1** | **3 (tệ nhất +44)** |
| 78 (cân hai bên) | 1764 | 2 809 | 0 | 0 | 1 (+7) |

Đánh đổi: rect rộng hơn thì dòng **dài hơn mới wrap**, nên chỗ đụng biên nghiêng nặng thêm
(+22 → +44) dù tổng dòng và số trang quá slot đều giảm. Vá rect vẫn rẻ hơn vá dữ liệu **và**
không phải chạy lại sau mỗi merge sheet.

Ảnh review ở `tools/ss_margin_preview_fixed.png` (trang `133`/24, thấy rõ cái được: 17 → 16
slot) và `tools/ss_margin_preview_worst.png` (trang `141`/8, trang thừa chữ thật nên không
cải thiện). Dựng lại bằng `python tools\_preview\build_ss_margin.py <sID> <trang> <hau-to>` —
script vẽ chữ bằng **chính font trong game** và đặt glyph theo đúng công thức advance của
`adv_layout`, đã kiểm là trùng từng chỗ ngắt dòng với ảnh chụp Ryujinx.

`m_Pivot.x = 0` nên thu `m_SizeDelta.x` ghim mép trái, chỉ kéo mép phải vào — không cần bù vị
trí. `level10` không có type tree nhúng nên **vá byte tại chỗ** (`env.file.save()` lên level10
ghi rỗng phần lớn object — xem CLAUDE.md), cùng mẹo `fix_adv_box_width.py`: đuôi RectTransform
là 10 float liền nhau, `sizeDelta.x` ở +24.

Đã chạy 18/08/2026 (backup `_backup\level10.ssboxw`): đổi **2 byte** tại offset 94716, file vẫn
160 480 byte, 1259 object, chiều cao/vị trí/pivot nguyên vẹn.

> **Còn tồn:** hộp cao tới y 1047 mà tam giác chiếm y 930..1050, nên 2 dòng cuối của một trang
> đầy nằm *ngang hàng* tam giác — ở đó giới hạn phải là x 1725 (rect 1552), không phải 1842.
> Ảnh đang có kết ở y 930, đúng chỗ tam giác bắt đầu, nên chưa biết engine có phân trang để
> tránh hay không. Cần ảnh chụp một trang đầy; nếu có đụng thì phải làm giới hạn theo từng
> dòng như `fix_adv_wrap.py`.

## Thuật ngữ trong bundle `json`

`python tools\json_term.py <TênAsset> "<cũ>" "<mới>" [--apply]` — thay một chuỗi
trong một TextAsset của `StreamingAssets\json\json`, sửa thẳng trên văn bản JSON
nên không có gì khác bị đổi theo. In ra từng trường thay đổi trước khi ghi.

Bảy file đã dịch trong bundle này **không có tab nào trên sheet**, nên chỉ sửa
được ở đây: `DictionaryData`, `ChapterData`, `SceneReplayData`,
`ScriptDialogData`, `MusicData`, `MapData`, `AnimationTextData`.

Đã dùng: `DictionaryData` mục `no=212` "Thiên sứ tập sự" → **"Thiên thần tập sự"**
(16/08/2026, backup `_backup\json.prespiritterm`).

## Chuỗi UI nằm trong code (`global-metadata.dat`)

`python tools\metadata_term.py "<cũ>" "<mới>" [--apply]` — thay một literal IL2CPP
tại chỗ. Dùng khi grep cả `romfs` lẫn các bundle **đều không ra chữ nào**: chuỗi
là hằng trong code, không phải dữ liệu.

Bảng `stringLiteral` của metadata v31: cặp (offset, size) của bảng ở header 0x08 /
0x0C, của khối dữ liệu ở 0x10 / 0x14; mỗi mục là `{uint32 length; uint32 dataIndex}`
và **dữ liệu xếp khít nhau, không có một byte đệm nào**. Nên bản dịch phải ngắn hơn
hoặc bằng bản gốc tính theo **byte UTF-8**: script ghi đè tại chỗ, điền `\x00` phần
dư, hạ `length` trong bảng. Kích thước file không đổi nên mọi offset khác an toàn.
Muốn dài hơn thì phải dời hết các khối phía sau và viết lại header — chưa làm.

Sau khi ghi, script đọc lại từ disk và đối chiếu với backup: chỉ được khác đúng
vùng dữ liệu của literal đó cộng 4 byte `length`, lệch một byte ra ngoài là dừng.

Đã dùng: alert của TERMINAL khi bấm `EXECUTION` mà kỹ năng chưa dùng được —
literal **15058** `現在使用できません` (27 byte, trống sau = 0) → **"Chưa thể sử dụng"**
(23 byte), 18/08/2026, backup `_backup\global-metadata.dat.prelitterm`.

> Chuỗi này chỉ xuất hiện trong script dưới dạng **chú thích** `;//アラート：現在使用
> できません。` ở `00_03` và `04_03_02` — chữ thật do engine vẽ khi chạy
> `[terminal tutorial=…]` và `[terminal control start]`. Tìm trong `ScenarioData`
> rồi sửa ở đó là sửa nhầm chú thích, màn hình vẫn nguyên tiếng Nhật.
>
> Không giữ được `現在` vì hết chỗ: "Hiện không thể sử dụng" 31 byte, "Hiện chưa
> thể sử dụng" 30 byte, đều vượt 27. "Chưa" gánh phần nghĩa đó — cả hai cảnh
> (tutorial `PRO-03-14`, và `SOU-03-39` lúc gọi kỹ năng 『閉鎖』) đều là *chưa*
> dùng được lúc này chứ không phải vĩnh viễn.

### Alert "ターミナルを開いてください" — và vì sao đừng đi tìm nó trong tranh

Đã vá 18/08/2026 — literal **14856** `ターミナルを開いてください` (39 byte, trống sau = 0)
→ **"Vui lòng mở Terminal"** (23 byte). Backup `_backup\global-metadata.dat.prelitterm2`.
File offset 494190, `dataIdx` 372142; literal kế bên (`ダ`, dataIdx 372181) nguyên vẹn vì
372142 + 39 = 372181, tức phần đệm `\x00` lấp vừa khít tới đầu literal sau.

**Ảnh chụp máy thật trông y như art nướng** — một tấm băng-rôn tím giữa cảnh tàu lượn, có
cả `UN:LOGICAL` dọc mép và dãy vạch thước. Nó không phải tranh. Vệt loại trừ (quét byte
UTF-8 trên cả 25 container `.assets`/`level*` **và** giải nén từng object của mọi bundle
trong `StreamingAssets`):

- chuỗi đầy đủ chỉ hiện ở `resources.assets` (4 lần) và `scenario01` (4 lần) — **cả 8 đều
  là chú thích** `;//アラート：ターミナルを開いてください`. Dịch chú thích thì màn hình vẫn
  nguyên tiếng Nhật, đúng cái bẫy mục trên đã ghi cho chuỗi cùng widget.
- `global-metadata.dat` có **đúng một** chỗ chứa `ターミナル` trong cả 9.259.608 byte, và nó
  chính là câu này.
- `ui_jp` (7937 object, 122 Texture2D, 707 Sprite, 25 SpriteAtlas) **không có prefab
  alert/notification nào**; quét tím theo từng sprite trên 165 sprite dạng băng-rôn không ra
  chỗ nào có dãy 12 glyph trắng canh giữa.

Widget thật: `level10` `Canvas_UI/NotificationLayer/Notification_Terminal/Panel/Text (TMP)`
= MonoBehaviour **888**; tấm nền tím là Image MonoBehaviour 984 lấy Sprite 387 / Texture2D 32
của `sharedassets10.assets`. Engine bật nó sau **10 giây không thao tác** ở
`[terminal time=10 target=*test_01 tutorial=1]`, hiện ở **góc trên phải** (600×124 tại
x1302..1902, y241..365 trên canvas 1920×1080) — không phải giữa màn như ảnh chụp làm tưởng.

Hai giới hạn phải cùng thoả, và giới hạn byte cắn trước:

| | mốc | `ターミナルを開いてください` | `Vui lòng mở Terminal` |
|---|---|---|---|
| byte UTF-8 | ≤ 39 (trống sau = 0) | 39 | **23** |
| bề rộng vẽ | ≤ 580 px | 444,6 | **369,5** |

Khung TMP 580×94, `m_TextWrappingMode=0` (NoWrap), `m_overflowMode=1` (Ellipsis) và
**auto-size TẮT** (`m_enableAutoSizing=0`) — quá 580 px là bị chặt rồi thay bằng `…`, chứ
không co lại. Đo ở fontSize 32 / charSpacing 2,2 với chính file font trong bundle mod.

> **Widget này dùng font KHÁC ô thoại.** Thoại ADV lấy `sharedassets7.assets` pid 85
> (`FOT-NewRodinProN-DB SDF-Dynamic`), còn alert lấy `sharedassets10.assets` pid 3568
> (`FOT-DNPShueiMGoStd-B SDF-Dynamic`). Nên "thoại tiếng Việt hiện đúng" **không** chứng minh
> alert cũng hiện đúng. Cả hai là font **Dynamic**: `m_CharacterTable` rỗng, atlas dựng lúc
> chạy từ file font nhúng (`m_SourceFontFile` → pid 305 và pid 7), nên coverage phải soi ở
> cmap của chính file font, không phải ở bảng ký tự của asset.
>
> Soi rồi: **bản 1.0.2 gốc thiếu ư/ể/ở/ụ/ử ở cả hai font**, bản mod đã dựng lại cả hai và
> đủ hết (notif 14.590 → 8.366 codepoint, ADV 16.149 → 10.178 — bỏ bớt CJK, thêm tiếng Việt).
> Kiểm nhanh:
>
> ```python
> from fontTools.ttLib import TTFont       # rút m_FontData của object Font rồi
> codes = set().union(*(t.cmap for t in TTFont(blob).\_\_getitem\_\_("cmap").tables))
> ```

## Trường `ruby` của từ điển

`python tools\fix_dictionary_ruby.py [--apply]` — 30/80 mục từ điển có trường
**thứ ba** `ruby` bên cạnh `title` và `text`; đó là furigana nổi trên tiêu đề,
vẽ bởi `level10` pid 896 `DictionaryLayer/…/Mask_Ryby/Ruby (TMP)`. Cả 30 vốn còn
nguyên tiếng Nhật nên màn ARCHIVE đang thả kana lên trên tiêu đề tiếng Việt.

Đã chạy 16/08/2026 (backup `_backup\json.predicruby`): xoá trắng 25 (24 cách đọc
hiragana + KiEL), giữ 5 từ mượn katakana thành tiếng Anh — `112` Operator,
`212` Spirit, `250` DAW, `255` Trainer, `400` Matching — và đổi `no=400` thành
**"Sự tương thích"** (bỏ "(Sync)", vì bản gốc là 適合 đọc マッチング, không có
chữ Sync nào).

## Tiêu đề từ điển tràn khung

> **Có HAI màn từ điển, và màn người chơi mở ra là màn chật hơn.**
> `level10` pid 897/896 `Canvas_UI/DictionaryLayer/…` (tiêu đề 588×64 cỡ 40,
> ruby 588×103 cỡ 15) là popup hiện **trong lúc đọc thoại**. Màn ARCHIVE mở từ
> terminal là **`level22` `RenderCanvas/Note/Title/…`**: tiêu đề pid 330 trong
> mask **500×40** cỡ 32 charSpacing 3.5, ruby pid 332 trong mask **180×14**
> cỡ 12 **charSpacing 15**. Đo theo `level22`; đo nhầm `level10` đã cho danh
> sách tràn sai hai lần.

Cả hai đều căn giữa, NoWrap, không auto-size, nằm trong mask — dài quá là bị
cắt **cả hai đầu**. Đo theo khung thật: **6/80 tiêu đề tràn** (`357` 600 px,
`351`, `213`, `209`, `350`, `214`) và **1/28 ruby** (`357`
"Non-complainant offense" 243 px trong khung 180).

`charSpacing 15` của ruby vốn dành cho 6 chữ kana toàn rộng của chuỗi mẫu
`ルビのサイズ`; chữ Latin phải trả khoảng cách đó cho **từng chữ cái**, nên mới
phình ra. Không còn ruby kana nào nữa, khoảng cách đó chẳng phục vụ gì.

`python tools\fix_dictionary_box.py [--title] [--apply]` — hai việc, cả hai đều
giữ **nguyên cỡ chữ 12**:

1. `m_characterSpacing` của ruby 15 → **0**
2. bề rộng `Mask_Ryby` **180 → 500** cho bằng `Mask_Title`

Con số 180 là di sản thời chữ kana; khung cha `Title` rộng 564 và khung hồng vẽ
sẵn còn rộng hơn, nên chỗ trống vốn vẫn còn. Nới mask thì text đang vừa vẫn
hiển thị y hệt — chỉ có chuỗi dài là hết bị cắt.

Đã chạy 16/08/2026 (backup `_backup\level22.predicbox`): vá **byte tại chỗ** vì
`level22` không nhúng type tree — đúng **3 byte** đổi so với bản gốc, kích thước
file không đổi. Với RectTransform, mỏ neo là đuôi 10 float (anchorMin,
anchorMax, anchoredPosition, sizeDelta, pivot) và `sizeDelta.x` nằm ở +24.

## Ruby viết hoa

Giá trị ruby viết **CHỮ HOA** hết (quyết định 16/08/2026) — ở 12 px dễ đọc hơn
hẳn chữ thường. Viết hoa tốn thêm ~24% bề rộng (`Non-complainant offense`
171 → 212 px), phần khung vừa nới hấp thụ hết. Đã kiểm tra font có đủ chữ hoa
tiếng Việt (Ậ Ý Ệ Ố) trước khi áp dụng.

Chữ hoa nằm trong **dữ liệu**, không phải `m_fontStyle`, để đọc JSON là biết
ngay màn hình hiện gì. Bảng giá trị nằm ở `TRANSLATE` trong
`fix_dictionary_ruby.py` (5 mục) và `PLAN` trong `fix_dictionary_titles.py`
(26 mục) — sửa thì sửa ở đó rồi chạy lại, cả hai đều bỏ qua mục đã đúng.

> **Không auto-size cho ruby.** Đã thử và bị bác: ở 12 px nó vốn là chữ nhỏ nhất
> màn hình, co thêm là không đọc được. Với chữ đã nhỏ sẵn thì tìm cách chỉnh
> tracking / ngắt dòng / rút gọn chuỗi trước, đừng đụng auto-size.

Thêm `--title` để auto-size **tiêu đề** (26–32) — cái đó 32 px nên co một chút
không sao.

Vị trí byte tính từ `m_fontSize`, mỗi trường 4 byte: `+12` enableAutoSizing,
`+16` min, `+20` max, `+24` fontStyle, `+28` horizontalAlignment,
`+32` verticalAlignment, `+36` textAlignment, `+40` characterSpacing.

`python tools\fix_dictionary_titles.py [--apply]` — chuyển phần trong ngoặc lên
trường `ruby`. Mục nào đã đúng trạng thái đích thì bỏ qua, chạy lại vô hại.

Đã chạy 16/08/2026, hai đợt (backup `_backup\json.predictitle` giữ trạng thái
trước cả hai): 26 mục, thêm mới 19 trường `ruby` (chèn giữa `title` và `text`,
đúng vị trí các mục khác dùng). Kết quả: 49/80 mục có trường `ruby`, 28 ruby
hiển thị, 0 ký tự kana, **tiêu đề tràn khung 24 → 8**.

Tám mục còn tràn — `357` (780 px), `351`, `213`, `209`, `350`, `214`, `108`,
`203` — không còn ngoặc để chuyển, phải rút gọn tên.

`no=255` giữ ruby `Trainer` và bỏ hẳn "(Breeder)": bản gốc là 育成者 đọc
トレーナー, nên Trainer mới là cách đọc còn "(Breeder)" là do người dịch tự thêm.
`no=250` xoá ruby vì trùng y hệt tiêu đề `DAW`.

> **Đừng đụng vào `no=104` "Unlogical (Lần trước)".** Ngoặc đó có sẵn trong bản
> gốc — `アンロジカル（前回）` — nên nó là một phần của tên mục, dùng để phân biệt
> với `no=103` "Unlogical". Đây là mục **duy nhất** có ngoặc đến từ bản gốc;
> 9 mục còn ngoặc khác (`110 111 159 204 252 354 356 357 502`) đều là chú thích
> tiếng Anh do người dịch thêm. Kiểm tra nguồn gốc ngoặc trước khi chuyển lên
> `ruby`.

## Nội dung từ điển bị ngắt dòng hai lần

`python tools\fix_dictionary_wrap.py [--all] [--apply]` — `DictionaryData.text`
được ngắt dòng cứng sẵn trong dữ liệu (một `\n` cho mỗi dòng hiển thị, giống bản
Nhật), nhưng ô chữ **vẫn bật wrap** (`m_TextWrappingMode = 1`). Dòng cứng nào
rộng hơn khung một chút là bị TMP ngắt **lần thứ hai**, phần đuôi rơi xuống một
dòng trống trơ:

```
phối viên nhưng phạm vi  ->  phối viên nhưng phạm / vi
quyền hạn sẽ khác nhau,  ->  quyền hạn sẽ khác     / nhau,
```

Ô chật hơn trong hai màn từ điển là **popup ADV** (cái người chơi mở lúc đọc
thoại), không phải trang ARCHIVE:

```
level10 pid 895  DictionaryLayer/ViewRoot/uch_dictionary_note_field/MainText (TMP)
                 rect 586×758  cỡ 40  charSpacing 5    lineSpacing -23
level22 pid 331  Note/NoteTextArea/Mask/MainText (TMP)
                 rect 497×476  cỡ 32  charSpacing 3.5  lineSpacing -3
```

Tính theo em thì popup được 586/40 = **14,65** em một dòng còn ARCHIVE được
497/32 = 15,5 em, nên ngắt vừa popup là vừa cả hai màn.

**Công thức bề rộng phải đúng dạng, không thì lệch 7%.** TMP nhân advance với
`fontSize/pointSize` nhưng nhân `characterSpacing` với `fontSize/100`, và phép
thử ngắt dòng đo tới **mép phải chữ cuối** nên khoảng cách sau chữ cuối không
tính:

```
W = Σ advance × fontSize/pointSize  +  (n−1) × charSpacing × fontSize/100
```

Ở cỡ 40 thì hai cách khác nhau 1,4 px mỗi chữ — cả dòng lệch 7%. `adv_layout.wrap`
vẫn dùng dạng cũ `(advance + spacing) × fontSize/pointSize`; chỉ mượn bảng advance
của nó, đừng mượn hàm đo. Xem thêm memory `unlogical-text-overflow`.

Với dạng đúng thì giới hạn **đúng bằng bề rộng rect, 586 px**, không cần hệ số bù.
Mốc đọc từ ảnh chụp popup thật (mục `112` trước khi sửa) kẹp lại rất chặt:

```
việc can thiệp hệ thống   577,6 px  ->  game vẽ LIỀN một dòng
phối viên nhưng phạm vi   590,1 px  ->  bị TMP ngắt
```

`OBSERVED_FITS` / `OBSERVED_BREAKS` trong script giữ 10 mốc đó và **tool tự dừng
nếu mô hình xếp sai một mốc** — bắt chước `fix_qa_spacing.py`, vì một mô hình
spacing sai từng làm mất một vòng vá.

> **Ảnh chụp bằng điện thoại vẫn đo được** nếu lấy một rect biết sẵn kích thước
> làm thước: khung `BG` của popup là 824×1080 và vùng hồng khớp đúng rect đó, cho
> 1152 px ảnh / 824 px canvas. Đo hai dòng dài khác nhau ra cùng tỉ lệ 0,8969 và
> 0,8970 → biết mô hình đúng *tỉ lệ* trước khi biết nó đúng *tuyệt đối*. Đừng lấy
> chiều cao khung làm thước nếu chưa chắc art lấp kín rect.

Đã chạy 17/08/2026 (backup `_backup\json.predicwrap`, `json.predicrevert`): đúng
**một** mục tràn — `no=112` với 4 dòng vượt (rộng nhất 618,7). Ngắt lại: 16 → 18
dòng, rộng nhất 576,1 px, hai trang popup (dòng 1–11 và 8–18) đọc được hết. Trước
đó nó vẽ ra 20 dòng vì TMP ngắt thêm, nên số dòng thật **giảm**.

> Vòng đầu dùng dạng công thức cũ nên báo oan 4 mục và đã ngắt lại cả `205`,
> `300`, `361`; ba mục đó vốn 590–594 px theo dạng cũ nhưng chỉ 560–570 px thật,
> tức vẫn vừa khung. Đã trả về nguyên trạng. **Sửa mô hình trước, rồi mới chọn
> mục cần sửa** — dạng sai không chỉ lệch mức, nó còn đổi cả *thứ tự* giữa các
> dòng có số chữ khác nhau.

### `\n` trong dữ liệu là thứ chịu lực — đừng bỏ đi

Bỏ hết `\n` rồi phó thác cho autowrap **là mất chữ**, vì engine phân trang ô note
bằng cách **đếm `\n` trong dữ liệu**, không biết gì về wrap của TMP:

```
MyUICompornentBase.BuildNoteLines   RVA 0x19B3490   raw.Replace(…).Split('\n')
MyUICompornentBase.CalcStartIndex_PageUnit  0x19B3450   notePageNo × NOTE_TEXT_LINE
MyUICompornentBase.CalcStartIndex_LineUnit  0x19B3440   notePageNo
Dictionary_ADV.NOTE_TEXT_LINE      RVA 0x1A17880   MOVZ W0,#11   -> 11 dòng/trang
Dictionary (terminal) — không override, lấy mặc định của
MyUICompornentBase.NOTE_TEXT_LINE  RVA 0x19AB110   MOVZ W0,#8    ->  8 dòng/trang
DictionaryBase.DefaultMaxCharsPerLine 0x1A16930    MOV W0,WZR    -> code KHÔNG tự
                                                     ngắt, `\n` là toàn bộ nguồn dòng
```

Con số 11 và 8 khớp đúng chiều cao hai ô (758/70,8 = 10,7 và 476/63,0 = 7,55), và
khớp đúng hai ảnh chụp mục `112` khi nó còn 16 dòng dữ liệu:

- trang 1 dừng đúng ở **dòng dữ liệu 11** (hiển thị 12 dòng, vì dòng 1 bị wrap)
- trang 2 bắt đầu đúng ở **dòng dữ liệu 6** = 16 − 11 (trang cuối dồn về cuối)
- đuôi trang 2 — dòng dữ liệu 16, bị TMP wrap thành 2 dòng — **rơi ra ngoài
  khung và không cuộn tới được**: chữ `phép.` chưa bao giờ hiện lên

Nếu phân trang theo số dòng TMP vẽ thật (20) thì mốc phải là 11 và 10, không phải
11 và 6. Nên **luật của dữ liệu là: mỗi `\n` = một dòng hiển thị**. Ngắt lại cho
vừa khung không chỉ đẹp hơn, nó **trả lại phần chữ đã mất**.

> Sinh lại `dump.cs` khi cần tra code (không giữ trong cây này, 22 MB + 61 MB):
> ```powershell
> python tools\extract_exefs.py "<update .nsp>" <thư mục ra>
> tools\_ext\Il2CppDumper\Il2CppDumper.exe <thư mục ra>\main `
>     D:\Downloads\UNLOGICAL_v2\Data\Managed\Metadata\global-metadata.dat <dump>
> ```
> RVA = offset trong `main.flat`, nên đọc hằng số của getter chỉ là đọc 4 byte.

## Ô thoại ADV: chữ chạy xuống dưới hoạ tiết góc

`python tools\fix_adv_box_width.py [--apply]` — khung chữ rộng 1400 nhưng **art
của ô bị vát chéo ở góc dưới bên phải**, nên dòng càng thấp càng ít chỗ thật. Đo
trên ảnh chụp gốc 1280×720 (`IMG_7139`, mép vùng tối của chỗ vát, px canvas tính
từ lề chữ ở canvas 308):

```
dòng 1  art ở 1430      dòng 2  art ở 1364      dòng 3  art ở 1301      dòng 4  ~1240
```

TMP ngắt dòng theo khung, không biết gì về art, nên dòng nào lấp đầy khung là đuôi
nó nằm trên nền tối và mất đọc — đúng trạng thái trong `SPOILER_IMG_3011.jpg`.
Quét cả build: **3.992/37.951 câu thoại ADV (10,5%)** có một dòng như vậy, 356 câu
vượt hơn 80 px.

Bảng so ba hướng (mô hình đã hiệu chỉnh khớp cả hai ảnh chụp):

| khung | ở cỡ 42 | nhỏ hơn 42 | chạm hoạ tiết |
|---|---|---|---|
| 1400 (gốc) | 37.285 | 666 | **3.992** |
| 1300 | 36.760 | 1.191 | 448 |
| **1280** | 36.620 | 1.331 | **2** |

Ngắt cứng dữ liệu theo giới hạn từng dòng thì lại **936** câu bị auto-size thu nhỏ
— nhiều hơn 665 câu mà cách thu khung phải trả — cộng thêm 3.941 câu bị sửa dữ
liệu và phải chạy lại sau mỗi merge. Nên chọn thu khung: **một float cho mỗi
component, xong là xong mãi.**

`m_Pivot.x = 0` ở cả hai rect nên thu `m_SizeDelta.x` là mép trái đứng yên, chỉ mép
phải co vào, không phải bù vị trí gì cả. Đã chạy 17/08/2026 (backup
`_backup\level10.advboxw`): `level10` pid 564 `Message(Normal)/Text` và pid 581
`Message(Highest)/Text` 1400 → **1280**, vá byte tại chỗ (2 float), kích thước file
không đổi. Hai câu trong hai ảnh sau khi vá:

```
TỐT  (IMG_7139)  vẫn cỡ 42, 3 dòng, rộng nhất 1272/1280
TRÀN (IMG_3011)  cỡ 41 -> 37,5, 3 dòng, rộng nhất 1274 — hết nằm dưới hoạ tiết
```

`python tools\fix_adv_wrap.py --check` là **chốt**: dựng lại cách game xếp chữ
(tôn trọng `\n` sẵn có, ngắt theo khung đọc trực tiếp từ `level10`, rồi auto-size)
rồi báo lỗi nếu còn dòng nào chạm art. Hiện **0/37.951**.

> **`「」` không được vẽ.** Ảnh chụp chứng minh: dòng 1 của câu TỐT đo được 1362 px
> mà mô hình cho 1371 nếu bỏ hai dấu đó, còn tính cả thì 1459 — vượt cả khung.
> Nên khi đo bề rộng thoại phải trừ `「」` ra.

> **Ba cái bẫy đã sập trong lần làm này**, ghi lại để đừng lặp: (1) cộng dồn bề
> rộng theo từng từ thì thiếu charSpacing của dấu cách, hụt ~4,5 px mỗi từ — phải
> cộng theo (tổng advance, số ký tự) rồi mới quy ra px; (2) tách từ bằng `split(" ")`
> cắt đứt cả `[Cherish'Châu ngọc]` làm hai, hai nửa không còn khớp regex tag nên bị
> đo cả phần ruby và dấu ngoặc; (3) ngắt theo giới hạn ở cỡ 42 cho câu vốn render ở
> cỡ 28 thì vụn ra 6 dòng và **tràn chiều cao** — chọn cỡ trước, rồi ngắt theo giới
> hạn ở cỡ đó.

## Dấu lửng nối dấu lửng thì ngắt dòng

`python tools\fix_ellipsis_break.py [--apply] [--check]` — câu bỏ lửng mà câu sau
mở đầu cũng bằng dấu lửng thì đọc như hai lượt nói, nên tách hai dòng (yêu cầu
17/08/2026):

```
Terminal đang gặp trục trặc... ...Kohaku, cậu có đó không?
->  Terminal đang gặp trục trặc...
    ......Kohaku, cậu có đó không?
```

Luật: một chuỗi ≥2 dấu chấm (hoặc `…`), **một** space, rồi một chuỗi như thế →
thay đúng space đó bằng `\n`. Không đụng gì khác nên chạy lại vô hại — và **phải**
chạy lại sau mỗi merge, vì sheet lưu mỗi ô một dòng phẳng. Từ 27/08/2026 cả hai
nửa còn phải qua **luật dòng cụt** ngay dưới đây.

### Luật dòng cụt (27/08/2026) — cả hai nửa

Ngắt chỉ đáng một dòng khi **vế trái kết thúc gần mép dòng**. Nếu vế trái đã tự
xuống dòng (từ 2 dòng trở lên) mà **dòng cuối của nó đầy chưa tới 3/4 khung** thì
ngắt sẽ để lại một mẩu cụt và đẩy vế sau xuống hẳn một dòng — khi đó **không ngắt**:

```
...nắm lấy cánh tay của Ran định bỏ chạy.      dòng 1 đầy
...                                            dòng 2 chỉ 103/960 px  -> KHÔNG ngắt
```

Vế trái gọn trong **một** dòng thì luôn cho ngắt, ngắn tới đâu cũng vậy — đó chính
là dáng hai lượt nói mà luật này sinh ra để có. Luật đúng cho mọi độ sâu (2 dòng,
3 dòng…): chỉ dòng **cuối** của vế trái mới tính. Ngưỡng ở `RUNT_FILL = 0.75`.

Dòng đo bằng `fix_adv_wrap` (khung thật đọc từ `level10`, hiện là **1280**, ngưỡng
960 px) ở đúng **cỡ auto-size mà tin nhắn sẽ hiện**, không phải cỡ 42 cứng.

> **Luật này GỠ được ngắt, nên tool phải làm phẳng trước rồi mới quyết định.**
> Chỉ biết chèn thêm thì không bao giờ lùi được bản vá cũ. `fix()` làm phẳng `… ⏎ …`
> (luật cũ ngắt mọi chỗ nên nửa này do chính tool sở hữu trọn vẹn) và những chỗ
> `. ⏎ …` mà cổng JP sở hữu (đo: cả 631 chỗ trong build đều do chính tool này tạo,
> 0 chỗ của người khác), rồi chạy lại luật — nên chạy hai chiều đều hội tụ.

Đã chạy 27/08/2026 làm hai đợt, cùng một luật:

| đợt | backup | gỡ | bớt một dòng | lên bậc cỡ chữ |
|---|---|---|---|---|
| nửa `. ...` | `_backup\scenario01.ellipsisrunt` | **204 / 631** (32,3 %) | 95 | 50 |
| nửa `... ...` | `_backup\scenario01.ellipsisruntell` | **5 / 33** (15,2 %) | 4 | 0 |

Còn 72 chỗ bản Nhật không xuống hàng như cũ. Số tin nhắn `. ...` hiện ở cỡ 42 đầy
đủ 154 → 185; 0 dòng chạm hoạ tiết ở cả hai đợt. Chữ không đổi một ký tự nào —
bản mới làm phẳng lại phải bằng đúng bản cũ làm phẳng.

Trong 5 chỗ `... ...` bị gỡ có **chính ví dụ mẫu ở đầu mục này** — dòng 2 của vế
trái chỉ đầy 382/960 px:

```
「Kohaku, xin lỗi vì cứ gọi cậu mãi. Terminal đang gặp trục trặc...
......Kohaku, cậu có đó không?」        3 dòng -> 2 dòng sau khi gỡ
```

> **`PAT_DOT` phải có lookbehind `(?<![.…])`.** Từ khi nửa `... ...` cũng biết từ
> chối, một chỗ `... ...` để phẳng sẽ chứa sẵn hình `. ...` — luật dấu chấm sẽ cắn
> vào dấu cuối của chuỗi lửng và **lén ngắt lại đúng chỗ vừa từ chối**. Trước đây
> không cần vì `PAT_ELL` luôn ngắt hết trước.

> **`check_layout_breaks.py` sẽ FAIL ngay sau đợt này** — nó bắt mọi chuỗi *mất*
> xuống dòng so với backup mới nhất, mà 209 chỗ này là cố ý gỡ. Sau đợt merge
> kế tiếp (lúc đó có backup trước-merge mới) thì hết.

Đã chạy 17/08/2026 (backup `_backup\scenario01.ellipsisbreak`): **33 chỗ**, toàn bộ
trong thoại, bundle `json` không có chỗ nào. Giá layout đo bằng mô hình ADV: 11 câu
thêm một dòng, 2 câu tụt một bậc cỡ chữ (`sID 74 text[561]` 42 → 37,75, `sID 91
text[135]` 42 → 40,75), và **0** câu có dòng chạy dưới hoạ tiết.

## Soi ngắt dòng ranh giới câu của bản Nhật

`python toolsix_jp_sentence_break.py [--apply] [--check]` — chỗ nào bản Nhật cho
câu sau xuống hàng riêng thì bản Việt cũng xuống hàng, **miễn là câu tiếng Việt
vẫn gọn trong một hàng** (yêu cầu 27/08/2026):

```
JP: 「はは、おおげさ。⏎　一緒にスーパー寄ってから帰ろう」
VN: 「Haha, em nói quá rồi. Cùng ghé siêu thị rồi về nhé.」
->  「Haha, em nói quá rồi.
     Cùng ghé siêu thị rồi về nhé.」
```

> ### Phần lớn ngắt dòng của bản Nhật KHÔNG phải ý đồ ngắt câu
>
> Trong 26 969 ngắt của bản gốc chỉ **9 107** nằm sau `。`; **9 444** nằm sau dấu
> phẩy `、` và hơn 5 000 nằm giữa chừng câu (`…て`, `…は`, `…に`). Tác giả tự canh
> dòng cho vừa khung — tiếng Việt không có vị trí tương ứng:
>
> ```
> JP: 瞬間、自分がまだ夢の中にいるのか、⏎これが現実なのか判断がつかなかった。
> VN: Trong khoảnh khắc, tôi chẳng thể phân biệt được ... hay đây chính là hiện thực.
> ```
>
> Cũng vì thế **không thể** đơn giản hoá thành "ngắt ở mọi ranh giới câu": chỉ
> 61,1 % ranh giới câu giữa tin nhắn của bản Nhật được xuống hàng.

Nên tool chỉ nhận ngắt **đúng ở ranh giới câu**, ánh xạ theo **thứ tự câu** — ngắt
sau câu thứ k của bản Nhật thành ngắt sau câu thứ k của bản Việt.

> ### Bản Nhật hay bỏ `。` cuối trước `」` — đó là cái bẫy của bộ tách câu
>
> `「新規の依頼来たよ。⏎　納期はけっこう余裕あるやつ」` chỉ có **một** `。`, còn bản Việt
> `「Có đơn hàng mới này. Thời hạn bàn giao cũng khá thoải mái.」` có **hai** dấu
> chấm. Đếm thô thì lệch, và tỉ lệ khớp chỉ **47 %**. Coi *cuối tin nhắn* luôn là
> một ranh giới câu (khi chưa có sẵn dấu, bỏ qua dấu đóng `」』）`) thì lên
> **10 171 / 10 489 = 97 %**. Cái thứ hai phải chặn là **dấu lửng MỞ ĐẦU dòng**
> (`⏎　……あ`) — nó không kết câu nào cả; dò ngược qua dấu mở mà gặp `
` thì bỏ.

"Vừa một hàng" đo ở **cỡ chữ tin nhắn đang hiện**: cỡ 42 với 96 % tin nhắn, còn
tin nào dài tới mức để phẳng vẫn quá ba hàng thì auto-size đã co nó rồi, đo ở cỡ
đã co đó. **Không** đo ở cỡ sau khi ngắt — thế là lý luận vòng: ngắt làm chữ co,
chữ co làm câu vừa một hàng, rồi lấy đó biện minh cho chính cái ngắt. Đo ở cỡ sau
khi ngắt thì được 7 763 tin nhắn nhưng **1 331** tin bị nhỏ chữ đi.

> ### Chốt thứ hai: ngắt KHÔNG được làm tăng số dòng (28/08/2026)
>
> Luật dòng cụt lọc theo dòng cuối của **vế trái**; đoạn cuối vẫn tự do tràn sang
> hàng nữa, đẩy tin nhắn quá khung và auto-size co chữ. Ngưỡng `RUNT_FILL` không tách
> được: dòng cuối vế trái của `18/txt/0003` là 61 %, `43/txt/0004` là 71 %, còn
> `86/txt/0315` — ô người dùng chốt GIỮ — nằm chen vào giữa ở 68 %.
>
> ```
> 18/txt/0003   phẳng 3 dòng cỡ 35    -> ngắt 4 dòng cỡ 32,25   THÊM DÒNG
> 43/txt/0004   phẳng 3 dòng cỡ 34,75 -> ngắt 4 dòng cỡ 32,25   THÊM DÒNG
> 86/txt/0315   phẳng 3 dòng cỡ 42    -> ngắt 3 dòng cỡ 40,5    giữ nguyên
> ```
>
> Chốt "không co cỡ chữ" cũng không dùng được ở đây: `86/txt/0315` cũng co 42 → 40,5.
> Thứ tách sạch là **số dòng**. `break_all()` so `render(cand)` với số dòng trước khi
> ngắt, hơn thì bỏ. Đã gỡ **85 ô / 85 ngắt** ngày 28/08 (backup
> `_backup\scenario01.noextraline`): **cả 85 đều bớt một dòng**, 77 ô giữ cỡ chữ và
> **8 ô chữ TO HƠN**, không ô nào tệ đi.

> ### Phải chốt thêm: ngắt xong cỡ chữ KHÔNG được co
>
> Chỉ đòi các đoạn *trước* mỗi ngắt vừa một hàng thì **đoạn cuối** vẫn tự do tràn
> sang hàng hai, đẩy tin nhắn quá khung và auto-size co chữ. Đúng 468/6 900 tin
> rơi vào đó, **toàn bộ** vì đoạn cuối, ví dụ:
>
> ```
> ―Ba năm trước. Khi tôi và Ran vẫn còn là học sinh cấp ba. Ca khúc ... cơn sốt cực lớn.
>     3 dòng cỡ 42  ->  vẫn 3 dòng nhưng cỡ 35,75
> ```
>
> Cùng số dòng mà chữ nhỏ đi là lỗ thuần. Nhưng **đòi cả đoạn cuối vừa một hàng**
> thì quá tay — còn 3 326 tin, loại oan 3 106 tin có đoạn cuối dài hai hàng mà tổng
> vẫn ba hàng, tức không tốn gì. Chốt đúng chỗ là `render(sau) >= render(trước)`:
> giữ hết những gì không tốn gì, loại đúng những gì tốn một bậc cỡ chữ.

Năm chốt nữa, thiếu một cái là bỏ cả tin nhắn: bản Việt phải **phẳng hoàn toàn**
(ô đã có ngắt là của fixer khác, không giành); **số câu hai bên bằng nhau**; chỗ
cắt phải đang là một **dấu cách** và **không nằm trong `[...]`**; ngắt xong **cỡ chữ
không được co**; và không dòng nào được chạm hoạ tiết góc ô thoại.

Không thụt `　` ở dòng sau như bản Nhật — bản Việt có 1 151 dòng sau ngắt không
thụt so với 71 dòng có thụt, theo lệ số đông.

Đã chạy 27/08/2026 (backup `_backup\scenario01.jpsentbreak`): **6 432 tin nhắn,
6 651 chỗ ngắt**; 2 028 tin cao thêm một dòng, **0** tin co cỡ chữ, **0** dòng
chạm hoạ tiết. Bỏ qua 14 774 ô có ngắt bên bản Nhật nhưng không đủ chốt. Diff
nhị phân: đúng 6 432 `text[]` đổi, mọi chỗ chỉ là **space → xuống dòng**, chữ
không đổi một ký tự nào, `loadLine` / `scriptText_Line` nguyên vẹn.

> **`scriptText` mirror được 5 591, hụt 841 — và đó là lệch có sẵn.** Xem thẳng
> thì `text[]` và `scriptText` của những ô ấy vốn đã khác chữ từ các đợt dịch
> trước (`khích lệ mãi.` ↔ `khích lệ mãi được.`, `"Unlogical"` ↔ `『Unlogical』`),
> phần lớn không tìm thấy dòng nào khớp, số còn lại khớp nhiều lần nên `mirror()`
> từ chối đoán. Game vẽ `text[]`, nên không ảnh hưởng hiển thị.

> ### Chỗ ngắt hình dấu lửng nhường cho `fix_ellipsis_break.py`
>
> Hai luật cùng nhắm một chỗ `. ⏎ …` nhưng chốt khác nhau, nên **gỡ qua ngắt lại vô
> tận**: luật dấu lửng vừa gỡ 85 ô vì thêm dòng thì luật soi ngắt JP đòi lại đúng
> **67** ô trong số đó — cả 67 đều là hình dấu lửng, và cả 67 đều thêm một dòng.
>
> Chốt 28/08/2026: `plan()` bỏ những chỗ cắt mà vế sau mở đầu bằng dấu lửng. Một chủ
> sở hữu cho một hình — đúng nguyên tắc đã dùng cho ô chat. Giá phải trả gần như
> bằng không: sau chốt chỉ còn **3 ô** thật sự thuộc về luật này (ngắt ở ranh giới
> câu khác, dấu lửng nằm chỗ khác trong tin nhắn), backup
> `_backup\scenario01.ellcede`.

> ### Tin nhắn chat thì không đụng — `fix_chat_use_genebark.py` sở hữu
>
> Chat trong cảnh ADV lấy chữ từ app Genebark, và tool bên đó **cố ý ghi phẳng**.
> Nhận diện bằng bảng tên dạng tài khoản: `talkName` có `@`
> (`【Kai Munakata@k_munakata2150】`) — 289 ô, trong đó 137 ô có ngắt bên bản Nhật.
> Chốt thêm 27/08/2026 theo yêu cầu người dùng.
>
> Lần chạy trước khi có chốt đã lỡ ngắt một số ô chat, nên tool có thêm `unplan()`:
> làm phẳng rồi soi lại, ra **đúng** chuỗi đang có thì ngắt đó là của chính nó, trả
> về phẳng. Ngắt của người dịch hay của fixer khác không dựng lại được y hệt nên
> được để yên — đã gỡ **45 ô / 47 ngắt**, còn 43 ô chat mang ngắt không phải của
> tool này (bản dịch tự có, và `fix_chat_use_genebark` chỉ viết lại 177/289 ô).
>
> Lý do trong docstring của `fix_chat_use_genebark.py` — *"ngắt dòng của bản
> Genebark ngắt cho bong bóng chat, không phải cho khung ADV 1280"* — **không đúng
> với dữ liệu**: ghép 1:1 theo bản Nhật đã làm phẳng ra **258 cặp, cả 258 ngắt dòng
> giống hệt nhau, 0 cặp khác**. Chỉ có một bản ngắt dùng chung. Nhưng chốt vẫn giữ:
> chữ ở đó do tool kia sở hữu, hai tool cùng ghi một ô là nguồn lỗi.

> **Tool này KHÔNG gỡ lại được** — nó chỉ quyết định trên ô phẳng nên chạy lại là
> no-op. Không sao: merge sheet làm phẳng sạch mọi `
` và quy trình sau merge vốn
> là chạy lại toàn bộ fixer, lúc đó nó quyết định lại từ đầu. **Chạy sau
> `fix_ellipsis_break.py`** — hai luật không giẫm chân nhau (chỉ 24/6 651 ngắt mới
> mang hình `. ⏎ …`, và `fix_ellipsis_break.fix()` không sửa lại chỗ nào trong số
> đó), nhưng thứ tự này giữ nguyên quyền quyết định của luật dấu lửng.

## Ngắt dòng asset chat Genebark — theo dấu câu (`fix_chat_wrap.py`)

`python tools\fix_chat_wrap.py [--apply] [--check]`

Widget: `ui_jp` › `genebark.prefab` › `GenebarkChatContentItem` (1388×166) › `Message_TMP`
rect **1210×80**, cỡ **32**, `characterSpacing` **5**, `lineSpacing` −60,
`m_TextWrappingMode = 1` (wrap **BẬT**), `m_overflowMode = 0`, `m_margin` 0. Ảnh chụp máy
thật cho thấy **không có bong bóng** — mỗi tin là một khối chữ canh trái, giữa các tin có
vạch `UnderLine` rộng 1388.

### Font khác ô thoại ADV — dùng advance của `adv_layout` là sai

Chat dùng `FOT-DNPShueiMGoStd-B SDF-Dynamic`, ô thoại ADV dùng `FOT-NewRodinProN-DB SDF`.
Bản Dynamic có glyph table **rỗng** (nạp lúc chạy từ `m_SourceFontFile`), nên lấy advance từ
bản tĩnh cùng typeface `FOT-DNPShueiMGoStd-B SDF` trong `font_jp` (2803 ký tự, pointSize 58);
cache ở `tools\_chat_advances.json`.

Công thức đúng cho widget này là kiểu `adv_layout`: **`(Σadvance + 5×n) × 32 / 58`**. Hiệu
chỉnh trên ảnh Ryujinx `_2026-08-14_21-39-21.png` — tỉ lệ canvas→màn hình lấy từ vạch
`UnderLine` (đo 1283 px / prefab 1388 = **0,9243**), rồi so 10 dòng chữ biết trước:

| | đo trên ảnh | model A `(Σadv+CS·n)·F/58` | model B `Σadv·F/58+(n−1)·CS·F/100` |
|---|---|---|---|
| `Nghĩ đi nghĩ lại vẫn thấy chẳng có manh mối gì` | 799 | **799** | 744 |
| tỉ lệ model/đo, trung bình 10 dòng | — | **1,010** | 0,939 |

Nên **công thức của `fix_adv_wrap.wd()` thấp hơn 6% và không dùng được ở đây.** Mốc kiểm
chứng: bản Nhật gốc **0/1194 dòng vượt 1210**, rộng nhất 834 px (69%).

### Vì sao cần: 91% ngắt dòng cũ nằm GIỮA câu

Đo trước khi sửa: 926 chỗ ngắt, **843 (91%) giữa câu**, 52 sau dấu kết câu, 31 sau phẩy —
ra `…gửi đến rồi. Tôi ⏎ check qua thì thấy ok…`. Di sản đợt 10/08/2026 (backup
`_backup\scenario01.prechatbreaks`, tool đã mất): nó bắt chước cách tác giả Nhật canh dòng
cho khung của họ, mà tiếng Việt không có vị trí tương ứng.

### Luật: kết câu trước, phẩy khi cần, câu dài thì để TMP

Đã đo **ba** luật trên 1194 mục, thước là "khớp số dòng bản Nhật":

| luật | khớp JP | ít dòng hơn JP | nhiều dòng hơn JP |
|---|---|---|---|
| gom tham lam tới 1210 (như `fix_center_caption_wrap`) | 70% | **346** | 7 |
| ngắt sau MỌI dấu câu | 62% | 107 | **342** |
| **kết câu (`. ! ? ...`) luôn ngắt, phẩy (`, ; :`) chỉ khi quá khung** | **74%** | 159 | 156 |

Gom tham lam **gộp mất câu mà bản Nhật tách**: `data[15]` bản Nhật hai dòng
(`ちゃんとケーブル挿さってる？` / `またＵＳＢ半挿しになってない？`) mà gom lại chỉ 920 px nên ra
một dòng. Ngắt sau mọi dấu phẩy thì gãy hơn cả cái đang sửa: `data[12]` ra `Này,` /
`tự nhiên máy mất tiếng luôn...`. Luật thắng cho `data[729]` ra **đúng ba dòng như bản
Nhật** (554 / 219 / 1038 px), và đó cũng là ô duy nhất trước đây vừa có ngắt tay vừa có
dòng tràn.

**Một mệnh đề tự nó dài hơn 1210 thì KHÔNG cắt** — để nguyên, mặc TMP tự ngắt (wrap đang
bật). Cắt giữa mệnh đề là đúng cái lỗi đang sửa. Còn **65 dòng** như vậy, rộng nhất 1841 px.

### Kết quả 28/08/2026 (backup `_backup\json.chatwrap`)

**707 ô đổi** (655 chuỗi khác nhau), 487 ô vốn đã đúng.

| | trước | sau |
|---|---|---|
| ngắt sau dấu kết câu | 52 (6%) | **566 (81%)** |
| ngắt sau dấu phẩy | 31 (3%) | 130 (19%) |
| ngắt GIỮA câu | **843 (91%)** | **0** |
| khớp số dòng bản Nhật | 78%* | 74% |
| dòng vượt 1210 mà còn cắt được | 7 | **0** |

\* con số 78% cũ là ngẫu nhiên: ngắt theo bề rộng tình cờ ra cùng số dòng trong khi vị trí
ngắt sai. Thước thật là cột "ngắt GIỮA câu".

Chốt chặn: chỉ đổi **space thành `\n`** (assert bản làm phẳng trước/sau giống hệt — đo lại
**0 ô bị đổi chữ**); không cắt trong `[...]` (tag được che rồi trả lại); `[主人公]` đo theo
tên mặc định engine thay vào chứ không phải 5 ký tự của tag.

**Gộp theo nội dung trước khi thay chuỗi.** 707 ô chỉ có 655 chuỗi khác nhau — cùng câu xuất
hiện ở hai nhóm chat. Thay-tất-cả cho ô đầu làm chuỗi cũ của ô sau biến mất, rồi lượt sau
báo "không thấy chuỗi cũ" và **dừng giữa đường** (thật: `data[174]`). Lần đó tool dừng trước
khi ghi nên không hỏng gì, nhưng đó là may.

**Tự dò lại từ câu chữ hiện tại**, nên chạy lại được sau mỗi vòng merge; không ghim chỉ số ô.


### Lề phải = lề trái, và bề rộng wrap THỰC TẾ của TMP không phải 1210

Yêu cầu 28/08/2026, sau ảnh chụp màn CHAT thật `_2026-08-28_13-17-14.png`.

Quy ảnh về canvas bằng tỉ lệ vạch ngăn (1283 px ảnh / 1388 prefab = **0,9243**). Tỉ lệ này
được kiểm chéo trên 5 dòng biết trước chữ: đo/model ra 0,919–0,929 — model advance đúng.

| mốc | canvas px |
|---|---|
| mép trái panel (`UnderLine`) | 39 |
| mép trái icon | 84 ⇒ **lề trái = 45** |
| mép trái chữ | 177 |
| mép phải panel | 1427 |

⇒ chữ dừng ở `1427 − 45 = 1382` ⇒ bề rộng **1205 px**. `LIMIT` đổi 1210 → **1205**.

**Prefab ghi `Message_TMP` = 1210 nhưng lúc chạy nó RỘNG HƠN.** Kẹp được từ `data[40]` —
một dòng trong dữ liệu mà máy vẽ thành hai:

```
vẽ hết "…quá nửa số buổi"        1269 px  <= W
thêm " đâu" thì mới xuống hàng   1342 px  >  W
=> W ∈ [1269, 1342)   trong khi lề chỉ cho 1205
```

Trên ảnh, dòng đó chạy tới x=1800 mà vạch ngăn dừng ở 1774 — chữ vượt cả panel. Vậy
**"để TMP ngắt" và "lề phải bằng lề trái" không thể cùng đúng**; bản đầu của tool chọn
cái thứ nhất nên phá lề.

Sửa: thêm `split_space_balanced()` làm bước cuối — sau dấu kết câu rồi dấu phẩy, còn quá
lề thì ngắt ở **khoảng trắng**, chọn chỗ **cân nhất** mà cả hai dòng đều trong lề.

**Cân, không tham lam** — đây là ngoại lệ có lý của luật "ngắt theo dấu câu, không cân độ
dài": luật đó áp cho việc *chọn giữa dấu câu và cân*, còn ở đây không còn dấu câu nào để
chọn. Gom tham lam sinh ra đuôi cụt — `data[89]` ra dòng hai chỉ **60 px** (`đấy`),
`data[40]` ra `buổi đâu` 148 px; cân thì ra 643/586 và 678/654. Mệnh đề rộng nhất trong
asset là 1841 px < 2×1205 nên mọi ca chỉ cần hai dòng.

Kết quả (backup `_backup\json.chatwrap-2`): **65 ô đổi** (59 chuỗi), 1129 ô đã đúng,
**0 ô bị đổi chữ**. Dòng rộng nhất đúng **1205 px** ⇒ mép phải 1382 ⇒ **lề phải 45 = lề
trái 45**. `--check` siết lại: **không** dòng nào được quá lề (bản cũ tha những dòng
"không cắt được theo dấu câu", nay không tha nữa vì TMP ngắt rộng hơn lề).

## Danh sách có số trong chế độ novel — thụt treo

`python tools\fix_novel_list_wrap.py [--apply]` — cùng họ lỗi với ô từ điển, nhưng
ở ô novel `level10` pid 894 `Message(Novel)/NovelText` (rect **1400×720**, cỡ 42,
charSpacing 6, lineSpacing −11,5, wrap BẬT, auto-size TẮT).

**Engine thụt 1 em ở đầu mỗi dòng CÓ TRONG DỮ LIỆU; dòng do TMP tự ngắt thì
không.** Đo trên ảnh chụp thật, so hai dòng liền nhau nên méo phối cảnh triệt
tiêu: đuôi dòng bị wrap nằm lệch **41 px canvas = 0,98 em** sang trái. Bản JP
không bao giờ gặp vì mỗi mục luật đều ngắt cứng **và** dòng tiếp mở đầu bằng hai
khoảng trắng toàn rộng, nên thân chữ mọi dòng rơi đúng một cột:

```
４．[運営'オペレーター]はゲームの進行を見守り、     42 + 89 = 131 px
　　ルールの不備や、問題が発生した際には           42 + 89 = 131 px
```

Bản dịch bỏ cả hai: chỉ còn **38/40.537** dòng bắt đầu bằng `　` (JP:
17.299/66.772). Số nửa rộng `5. ` rộng 64,6 px chứ không phải 89, nên tiền tố
dòng tiếp dùng `　` + một khoảng trắng thường = 61,5 px — lệch 3 px, không thấy
được; hai `　` sẽ vượt 24 px.

Giới hạn ngắt: `W(dòng) ≤ (1400 − 42) × 0,99`. Trừ 42 vì engine chèn thụt lề vào
chính chuỗi nên nó **ăn bề rộng wrap**; nhân 0,99 vì kẹp đo được ở ô từ điển rộng
12,5 px trên 586 (≈2%), mà dư 7 px trên 1400 thì mỏng hơn thế.

**Tự dò khối, nên chạy lại được sau mỗi lần merge.** Không ghim theo chỉ số tin
nhắn — dò bằng phía Nhật, phía không bao giờ đổi:

```
tin nhắn j là một mục liệt kê  <=>  scriptText_Line[loadLine[j]] mở đầu bằng
                                    １．…９． hoặc ・ ※ ＊ *
                               và   dòng đó nằm giữa [ノベルモード…開始…] và …終了…
```

Tiền tố thụt treo chọn theo bề rộng dấu đầu mục mà **bản dịch** đang dùng: `5. `
67,1 px → `　 ` (61,5), `・` 44,5 → `　` (44,5, khít), `* ` 39,0 → `　`. Chỉ dùng
tiền tố mở đầu bằng `　`: bản JP có 17.299 dòng như vậy và chúng hiển thị đúng,
tức U+3000 chắc chắn không bị engine cắt; space ASCII đầu dòng thì chưa có bằng
chứng nào trong game này.

Đã chạy 17/08/2026 (backup `_backup\scenario01.novellist`): dò ra **29 khối** trên
7 scene, **19 khối** phải sửa (18 tràn khung + 1 chỉ dư 5 px), rộng nhất sau khi
sửa 1386/1400. `--check` xác nhận 29/29 vừa khung và có thụt treo. Mirror vào
`scriptText` được 6/19 — 13 khối còn lại nằm trong số 11% mà hai bản đã lệch nhau
nên không khớp verbatim; vô hại vì `scriptText` không được vẽ.

### Chốt sau mỗi lần merge sheet

```powershell
python tools\fix_novel_list_wrap.py --apply     # dựng lại ngắt dòng + thụt treo
python tools\fix_novel_list_wrap.py --check     # exit 1 nếu còn khối sai
python tools\fix_dictionary_wrap.py  --apply    # ô từ điển, cùng lý do
python tools\fix_terminal_term.py    --check    # exit 1 nếu sheet mang lại cách gọi cũ
python tools\fix_paren_balance.py    --check    # exit 1 nếu tin nhắn mất dấu `（` mở
python tools\check_layout_breaks.py  [<backup>] # exit 1 nếu MẤT ngắt dòng/thụt lề
python tools\check_layout_breaks.py  --json     # cùng chốt cho bundle json
```

`check_layout_breaks.py` so bundle hiện tại với backup trước merge, **từng chuỗi
một**, trên hai thứ mà một ô sheet phẳng không mang được: số `\n` và số dòng mở
đầu bằng `　`/space. Mất là lỗi, thêm thì không sao (chính các fixer thêm vào).
Không tham số thì lấy backup mới nhất khớp `_backup\scenario01.*`.

Chạy thử ngược về mốc 15/08 (`scenario01.prenamekey`) thì chốt này **bắt được lỗi
thật** mà mọi vòng merge trước đã bỏ lọt:

- 3 tin nhắn chat mất ngắt dòng khi một pass sửa cách viết tắt — `sID=86 text[49]`
  ("E" → "Em"), `sID=86 text[560]` và `sID=124 text[161]` ("a" → "anh"): sửa chữ
  nhưng `\n` ở ranh giới câu rơi mất.
- 2 tin nhắn **rỗng hẳn**: `sID=107 text[99]` và `text[302]`, bản Nhật là
  `「…………」`. Cả file chỉ có đúng 2 chỗ rỗng như vậy (quét toàn bộ 39.803 tin nhắn
  so với bản Nhật), nên đây là sót của một vòng apply ghi ô trắng đè lên.

`python tools\fix_lost_breaks.py [--apply]` đã trả cả 5 chỗ về (17/08/2026, backup
`_backup\scenario01.lostbreaks`). Mỗi mục trong bảng `BREAKS`/`EMPTIES` khai đúng
chuỗi nó chờ tìm thấy, nên chạy lại là no-op và nếu câu chữ đã được dịch lại thì
tool **dừng** chứ không đoán. Ba chỗ chat chỉ trả `\n` về ranh giới câu, giữ nguyên
cách viết mới ("Em"/"Anh"); hai chỗ rỗng trả về `「......」` — 300/375 chỗ có bản
Nhật `「…………」` trong file này đang là `「......」`, khớp cả quy ước `……` → `...`.

`scriptText` của ba tin nhắn chat không khớp verbatim nên tool bỏ qua mirror: cả ba
nằm trong số 11% mà hai bản đã lệch từ trước (bản `scriptText` còn giữ "E"/"a"
viết tắt). Không ảnh hưởng hiển thị, nhưng nếu vá đợt lệch đó thì nhớ ba chỗ này.

Sau khi sửa, so lại với mốc 15/08 thì sạch: 349.797 chuỗi cả hai bên, ngắt dòng
208.817 → 209.760, dòng thụt 17.378 → 17.425, **không chuỗi nào mất**, và số tin
nhắn rỗng còn 0.

### Ba bản sao của một câu thoại, và bản nào là bản sống

```
ScenarioData.target[i].text[j]          <- ĐANG HIỆN TRÊN MÁY (người dùng xác nhận)
ScenarioData.target[i].scriptText       <- bản sao thứ hai, KHÔNG ai index tới
ScenarioData.target[i].scriptText_Line  <- script chương, VẪN TIẾNG NHẬT, 10.234 dòng
ScenarioData.target[i].loadLine[j]      <- index vào scriptText_Line, không vào scriptText
```

`loadLine[98] = 608` và `scriptText_Line[608]` đúng là câu JP của tin nhắn 98 —
nên **số dòng của `scriptText` đổi bao nhiêu cũng không phá mapping**, nhưng
`scriptText_Line` và `loadLine` thì không được đụng. `ADVManager.GetScenarioText`
(RVA 0x18E9A80) nạp file script chương từ bundle, và 143 file đó vẫn là tiếng
Nhật (chỉ 7 dòng khác bản gốc, đều là tham số `[terinfo text="…"]` đã dịch) — nên
chữ Việt chỉ có thể đến từ `text[]`.

**`scriptText` đã lệch khỏi `text[]` ở 4371/39.803 tin nhắn (11%); bản JP lệch 0.**
Vừa là chuẩn hoá (`『』` → `"`, `……` → `...`) vừa là bản dịch mới chỉ vào một bên
(`1.` trong `scriptText` còn là "theo từng màn (stage)" trong khi `text[]` đã là
"theo từng Stage"). Tool này đồng bộ `scriptText` theo `text[]` cho 4 mục nó sửa.

### Vì sao việc này không sửa được trên sheet

- Cột tiếng Việt của các tab `sd_*` **luôn là một dòng phẳng** (0/~2.900 hàng có
  newline) — sheet không có chỗ diễn đạt ngắt dòng cứng, mà bản vá này toàn bộ
  là ngắt dòng cứng.
- Mỗi lần merge phải **dựng lại** ngắt dòng bằng `carry_breaks` (difflib) vì bản
  build có ~730 `\n` mà sheet không có. Ngắt dòng sống ở hạ nguồn, không ở sheet.
- Áp sheet nguyên văn đã từng **làm phẳng 1.530 ngắt dòng** trên sáu asset.
- `　` cũng không sống nổi trên sheet: 203 thụt lề của `TerminalRuleData` đã rã
  thành một space ASCII (sheet còn 0 U+3000), mà space chỉ rộng ~1/3 `　`; nhiều
  space liền nhau thì lại bị quy ước "double space = ngắt dòng bị làm phẳng" của
  chính sheet thu về một.

Nên sheet giữ **câu chữ**, còn ngắt dòng + thụt treo là việc của bản build. Lần
merge sau sẽ xoá nó nếu không có chốt: so số `\n` và số `　` của mục đã sửa với
backup trước khi ghi.

Dòng cuối trơ một chữ (`phép.`) trông y như đúng cái lỗi đang sửa, nên hàm ngắt
kéo chữ từ dòng trên xuống khi dòng cuối hẹp hơn 40% giới hạn — chỉ chạm dòng
cuối, không lan lên trên.

## Ending List (Recollection) — tiêu đề đè lên dòng dưới

Một dòng của danh sách là prefab `RecollectionButton` trong
**`sharedassets21.assets`** (bundle của `level21`, cảnh Recollection):

```
RecollectionButton   rect 596×51
  Off/LeftParts      icon 36×44 ở x = 43..79
  Text  pid 169      stretch kín ô, margin trái 94  ->  bề rộng chữ 502
                     fontSize 32, charSpacing 3.8, auto-size TẮT,
                     wrap Normal, overflow = Overflow
```

Chuỗi mẫu của bản gốc là `ああああ五ああああ十あああ四` — 14 chữ toàn rộng, tức
khung chỉ được thiết kế cho tiêu đề tiếng Nhật ngắn. Tiêu đề dài quá 502 px thì
xuống **dòng thứ hai** và vì overflow không bị cắt, nó **vẽ tràn ra khỏi ô cao
51 px, đè thẳng lên dòng kế tiếp**. 16/38 tiêu đề tiếng Việt trong
`SceneReplayData` vượt ngưỡng đó.

Ở đây **TMP tự wrap chứ code game không đụng vào** — mô hình `adv_layout` tái
tạo đúng cả ba điểm ngắt dòng thấy trong ảnh chụp (`…của sự hy` vừa khít 502,
`…của kẻ mộng` và `…của chủ nghĩa` thì không), nên chỉnh component là ăn thua.

`python tools\fix_recollection_list.py [--apply]` — đặt
`m_TextWrappingMode = 0` (NoWrap) và bật auto-size **17–32**. NoWrap thì
auto-size chỉ co theo bề rộng, luôn một dòng, không bao giờ chạm ô bên dưới.
`m_fontSizeMax` ghim đúng `m_fontSize` gốc (32); để nguyên giá trị gốc 72 là
tiêu đề ngắn bị thổi phồng.

Đã chạy 16/08/2026 (backup `_backup\sharedassets21.assets.prerecolle` = bản gốc
1.0.2, vì trước đó romfs chưa có file này). Diff nhị phân: **đúng 1 object đổi,
kích thước không đổi**; 22/38 tiêu đề vẫn ở cỡ 32, còn lại co xuống 31.5…17.0.

Chỉ `sharedassets21.assets` nằm trong romfs, `.resS` để game tự lấy từ bản gốc —
Ryujinx phủ romfs theo từng file (tiền lệ: `sharedassets7/10.assets` cũng không
kèm `.resS`). `sharedassets21.assets` không nhúng type tree, phải mượn `nodes`
của một MonoBehaviour TMP trong bundle `ui_jp`.

**Không nới khung được như "Danh sách SHORT STORY" bên dưới** — ở đây không còn
một pixel trống nào. Đã tính lại toạ độ canvas 1920×1080 từ `level21`:

```
MainPanel   685×407 @ (-363, 61)   -> tâm x = 597, khung 254.5 .. 939.5
Buttons     100×0,  pivot (.5,1) @ (0,164) -> neo góc trái ở x = 547
hàng        596×51, pivot (0,1)   -> code đặt anchoredPos.x ≈ -285, hàng 262 .. 858
line_cut    8×361 @ (257,180)     -> vạch dọc 850 .. 858
Slider      24×324 @ (295,0)      -> thanh cuộn 880 .. 904
```

Mép phải của hàng **trùng đúng mép phải của vạch dọc** (858). Muốn rộng thêm thì
phải dời cả vạch lẫn thanh cuộn, mà quá 939.5 là ra ngoài khung cửa sổ tím — vốn
là art nướng sẵn trong `Frame` 1920×1080, không phải sliced sprite. Nới hết mức
cũng chỉ được 502 → 537 px, tức tiêu đề tệ nhất từ cỡ 17.0 lên 18.2: không đáng.
Bớt `m_margin.x` (94) cũng vô nghĩa — icon kết thúc ở x = 79, chỉ còn 10 px.

> **Còn tồn:** `#recollection_35` "Bằng đôi chân này, một bước, rồi một bước
> nữa" (45 ký tự, cần cỡ 17) và `#recollection_04` "[Error]Cerberus của chủ
> nghĩa duy lý" (cần 21.5) sẽ nhỏ rõ so với hàng xóm. Muốn đều hơn thì phải rút
> gọn bản dịch — `SceneReplayData` không có tab trên sheet nên sửa thẳng bằng
> `json_term.py`.

## Phím tắt màn Ending List

`python tools\fix_recollection_key.py [--apply]` — `Ⓐシーン再生 Ⓑ戻る` ở góc dưới
bên phải màn Recollection là **tranh vẽ**: sprite `UL_recolle_key` (300×34) trong
`sharedassets21.assets`, atlas `sactx-0-2048x2048-ASTC 4x4-Recollection`. Chuỗi
`シーン再生` trong `resources.assets` là hộp thoại xác nhận khác (`SystemText`
id 42) và trong `global-metadata.dat` là literal IL2CPP — không dính gì tới dải
này.

| trước | sau |
|---|---|
| Ⓐ シーン再生 | Ⓐ Play scene |
| Ⓑ 戻る | Ⓑ Back |

"Play scene" lấy đúng chữ game tự dùng ở `UL_library_key`. Icon Ⓐ/Ⓑ cắt nguyên
xi (x 2–31 và 202–231), chữ vẽ bằng `font_BASE.ttf` cỡ 19, mực hồng
`(254,160,174)` đo từ chính tranh gốc. Dùng lại `keyart.Container` +
`fix_key_prompts.compose`, sprite tight-mesh 85 đỉnh nên phải `full_rect_mesh()`.

Đã chạy 16/08/2026, backup `_backup\sharedassets21.assets.prerecollekey` (đã
gồm bản vá Ending List ở trên). Kiểm tra sau khi vá: `sprite.image` vẽ ra 2644 px
đục / ảnh dựng 2630 → **không hụt** (dư 14 px là nhiễu ASTC ở mép); 174 object,
0 object rỗng; 47 sprite còn lại lệch pixel đục **0**; pid 169 giữ nguyên bản vá
NoWrap + auto-size. Đặt `.image` làm texture nội tuyến nên file phình
101 KB → **4.29 MB**; `.resS` vẫn để game lấy từ bản gốc.

> **Tách riêng khỏi `fix_key_prompts.py` là cố ý.** Script kia không có bộ lọc,
> chạy lại sẽ ghi đè cả `sharedassets5/6/11`, `scene_jp`, `ui_jp`.
>
> **Tranh nguồn phải lấy từ bản gốc 1.0.2, không lấy từ bản vá.** Toạ độ icon
> trong `SPEC` là bố cục tiếng Nhật; chạy lần hai trên tranh đã dịch thì Ⓑ đã
> dời sang trái ~26 px nên `compose` cắt nhầm chỗ và ra tranh hỏng. Đã dính đúng
> lỗi này một lần.
>
> **`shutil.move` không báo lỗi đúng lúc.** `os.rename` bị Windows chặn vì bước
> kiểm tra còn giữ handle, shutil quay sang copy — **copy xong rồi** mới chết ở
> `os.unlink`. Nhìn traceback tưởng chưa ghi gì, thật ra file đích đã bị thay.
> Script giờ đọc bytes rồi ghi thẳng.

## Phím tắt màn MUSIC

`python tools\fix_music_key.py [--apply]` — bốn dòng gợi ý phím ở góc dưới bên
phải màn MUSIC là **tranh vẽ sẵn**, sprite `UL_music_key` (pid 73) trong
`sharedassets13.assets`, ô `(300, 588)–(653, 664)` của atlas
`sactx-0-1024x2048-ASTC 4x4-Music-594a0ae0` (pid 47). Tìm chuỗi trong romfs,
trong các bundle và trong `global-metadata.dat` đều **không ra chữ nào**.

| trước | sau |
|---|---|
| Ⓐ 再生/停止 | Ⓐ Play/Stop |
| Ⓑ 戻る | Ⓑ Back |
| Ⓨ 一時停止 | Ⓨ Pause |
| Ⓧ モード切替 | Ⓧ Mode |

Đã chạy 16/08/2026, backup `_backup\sharedassets13.assets.premusickey`. Font
`FOT-NewRodin ProN DB` cỡ 28, màu hồng `#FFD2D9` đo từ chính bản gốc, bốn nút
tròn Ⓐ Ⓑ Ⓨ Ⓧ cắt nguyên xi từ tranh cũ chứ không vẽ lại. Cột hai dời từ x=180
sang x=212 để "Play/Stop" đủ chỗ; cả khối rộng 337/353 px nên không phải đụng
tới `textureRect` hay `uvTransform`.

`モード切替` để là **"Mode"** chứ không phải "Loop Mode": nút X đổi chế độ lặp,
nhưng bản gốc chỉ nói "đổi chế độ", và "Loop Mode" cỡ 28 rộng 162 px — quá khổ.

Sprite này tight-mesh (116 đỉnh), nên script dựng lại mesh thành quad phủ kín ô,
mẫu lấy từ `UL_music_bg_base_02` (pid 61) cùng file. Kiểm tra sau khi vá:
`sprite.image` và ô cắt từ atlas cùng đếm được **7127 px đục — lệch 0**.

> **Đừng `open(path, "wb")` lên chính file đang `UnityPy.load()`.** Python mở
> file (cắt trắng) *trước* khi `env.file.save()` kịp đọc, nên 106/108 object
> không đụng tới bị ghi lại **rỗng** — file vẫn đủ 108 object, header vẫn đúng,
> chỉ `byte_size` bằng 0. Serialize ra `bytes` xong mới mở file mà ghi. Lần đầu
> chạy script này đã dính đúng lỗi đó và phải khôi phục từ backup.

## Hai đầu thanh trượt màn OPTION (`小` / `大` → `−` / `+`)

`python tools\fix_volume_ends.py [--apply]` — mỗi dòng của tab SOUND là **một
sprite dải ngang** (~1094×35) trong `sharedassets7.assets`, gộp cả nhãn ở mép
trái, 10 vạch nghiêng ở giữa, và hai chữ `小` / `大` ở hai đầu thang. Không có
chuỗi ký tự nào. Ô chữ đo bằng phân đoạn màu tím, **chỉ xét `x > 600`** vì nhãn
`SOICHI` / `HOTARU` cũng vẽ màu tím ở mép trái.

```
小  x 627..653 (27 px)      大  x 1065..1091 (26 px)
```

Nét `−` / `+` dày 3 px (khớp nét ngang của `大`), dài 22 px, siêu lấy mẫu 4× rồi
thu nhỏ; màu lấy từ **chính từng dải** chứ không viết cứng, vì nén ASTC làm mỗi
dải lệch vài đơn vị.

> ### KHÔNG `full_rect_mesh()` cho những sprite này — đã hỏng một lần
>
> Atlas xếp **sát nét**: `textureRect` của một dải rộng 1094 px nhưng nét thật
> chỉ chiếm vài mảng rời, và Unity **nhét sprite khác vào chỗ trống bên trong
> chính hình chữ nhật đó**. Mesh tight là thứ duy nhất giữ cho mỗi dải chỉ vẽ
> phần của mình. Phủ full-rect thì `X BUTTON`, `SKIP CHOICES`, `QUICK LOAD`,
> `B STICK` … hiện thẳng vào giữa hàng âm lượng — nhìn ảnh render mới thấy, mọi
> kiểm tra đếm object/kích thước đều báo bình thường.
>
> Nhưng mesh tight lại **không phủ hết ô chữ** (nó bám sát nét `小`/`大`), nên nét
> mới vẽ ra sẽ bị xén thành từng mảnh. Cách đúng: **nối thêm đúng hai quad** phủ
> hai ô chữ, giữ nguyên toàn bộ mesh cũ. Đây là ca ngược với `fix_music_key.py`
> — ở đó sprite chiếm trọn ô nên full-rect an toàn.

Mesh gốc vốn đã là một tập quad thẳng trục (`indexCount = 6 × số quad`, thứ tự
`0,1,2, 0,2,3`) và **UV trong dữ liệu gốc toàn số 0** — Unity tự suy UV từ
`textureRect`, không đọc UV của mesh. Quad nối thêm cũng để UV 0 cho khớp.

```
local_x = (textureRectOffset.x - m_Rect.width  * pivot.x + px)       / m_PixelsToUnits
local_y = (textureRectOffset.y - m_Rect.height * pivot.y + (H - py)) / m_PixelsToUnits
```

Hai luồng vertex nằm liền nhau trong `m_DataSize`: luồng 0 là float3 vị trí
(12 B/đỉnh), **đệm cho tròn 16 B**, rồi luồng 1 là float2 UV (8 B/đỉnh).

Đã chạy 16/08/2026 (backup `_backup\sharedassets7.assets.prevolends`, đã gồm bản
vá key prompt trước đó). Kiểm tra sau khi vá, đọc lại từ disk: 76 sprite, 0
object rỗng, **33 188 điểm đổi — toàn bộ nằm trong hai ô chữ, 0 điểm nào ở ngoài**;
biên độ tối đa ngoài ô chữ là 8 (nhiễu nén lại ASTC, cùng mức với 50 sprite không
đụng tới). Mỗi dải 24–141 đỉnh → +8.

> **Tab GAME không đụng tới.** Cặp nhãn ở đó là `遅/速`, `薄/濃`, `中/大`,
> `既読/強制`, `ON/OFF` — chữ có nghĩa, `−/+` không diễn đạt được "chậm/nhanh" hay
> "nhạt/đậm". Phải vẽ chữ, tách thành đợt riêng.
>
> **Nhãn tên nhân vật ở mép trái là tranh mod vẽ lại.** Bản gốc để chữ Nhật
> (`雅火`, `戒`, `琥珀`, `伊槻` …); chỉ `BGM`, `MOVIE`, `SE`, `VOICE` là Latin sẵn.
> Một đợt trước đã vẽ đè thành MIYABI, KAI, RAN, SOICHI, YURI, KOHAKU, SHINJU,
> HOTARU, MENOU, RURI, HIDAKA, CHIHIRO, ITSUKI, KYOSUKE, SHIORI, MITSUKI,
> ANGELICA, ???, OTHERS. `ConfigVolumeData.label` vẫn còn tiếng Nhật nhưng
> **không hiển thị** — nhãn thấy trên màn hình là sprite.
>
> (Ghi chú cũ ở đây từng viết là "đã Latin từ trước" — sai, và chính nó làm lạc
> hướng khi truy lỗi nét mảnh. Xem mục **Viền chữ mất màu** ngay dưới.)

## Viền chữ mất màu — tranh mod mảnh hơn tranh gốc một cấp weight

`python tools\fix_alpha_bleed.py [--apply]`

Nhãn mod vẽ (`MIYABI`, `KAI`, `RAN` …) trông mảnh hơn nhãn gốc (`SE`, `VOICE`)
dù **cùng typeface, cùng chiều cao chữ hoa 25 px**. Đo thân chữ `I` — chữ có
trong cả `VOICE`, `MIYABI`, `KAI` nên so được một-đối-một, tính cả phủ khử răng
cưa:

```
                    trong atlas   trên màn
VOICE  (gốc)             3.75        3.77     <- đi qua nguyên vẹn
MIYABI (mod)      4.02 / 3.82   3.04 / 2.79   <- rụng ~1 px
KAI    (mod)             3.82        2.96
```

Tranh mod vẽ **đủ dày**; nó rụng nét trên đường từ atlas ra màn hình.

**Nguyên nhân: thiếu loang màu ở vùng trong suốt.** Nhà phát hành trải màu mực
ra khắp nền trong suốt — dải `雅火` gốc giữ RGB `255,148,190` ở *mọi* điểm, kể cả
`alpha = 0`. Tranh mod để RGB `0,0,0` sát ngay cạnh nét:

```
ch_01_miya   x=  38        39          40..42        43
   RGB      0,0,0     80,46,60    255,148,191   245,142,184
   A            0           25            255           235
```

Hai chỗ nền đen lọt vào nét: **ASTC 4×4** để RGB và alpha chung một khối (thấy
ngay trong atlas: `A=25` mà RGB chỉ còn `80,46,60`), và **GPU lấy mẫu song
tuyến** — texel trong suốt mang RGB `0,0,0` vẫn được tính vào phép nội suy vì
alpha không premultiply. Chỗ thứ hai ăn hết phần nét: trên màn, kênh blue của
điểm viền tụt còn **117**, thấp hơn cả nền (169) lẫn mực (191), nên mắt không
tính viền vào thân chữ nữa.

> **Mô phỏng lại được, nên kiểm tra không cần chạy game.** Trung bình 2×2 texel
> rồi ghép lên nền ô nhãn tái tạo đúng số đo trên ảnh chụp tới hai chữ số thập
> phân (`VOICE` 3.75 vs 3.77, `miya` 3.03 vs 3.04, `kai` 2.96 vs 2.96). Cột
> "song tuyến" của `report()` chính là cái mắt nhìn thấy — cột "texel" thì không.

**Cách sửa:** giãn màu từ điểm đục gần nhất ra mọi điểm chưa đục, **giữ nguyên
alpha**. Đúng quy ước tranh gốc. Không vẽ lại chữ, không đụng mesh.

> **Bán kính 4, đừng để rộng hơn.** Song tuyến chỉ chạm texel kề (1 px), khối
> ASTC rộng 4 px (3 px). Atlas xếp sát nét nên bán kính lớn sẽ hút màu của
> sprite **hàng xóm** — thử bán kính 12 thì nét mảnh của `UL_option_keycon_button_X`
> (xếp chèn ngay trong ô của `VOICE`) bị kéo mất màu.

Vá cả texture atlas chứ không riêng 23 dải SOUND: mọi sprite mod vẽ lại trong
cùng file đều dính. `UL_option_keycon_button_X` là ví dụ — chữ tím `134,81,170`
đặc, viền cũng bị kéo tối; sau khi vá, dựng thử trên nền trắng thì hết viền xám.

Đã chạy 17/08/2026 (backup `_backup\sharedassets7.assets.prebleed`). Đọc lại từ
disk: 85 object, 76 sprite, **0 object rỗng**, format vẫn ASTC 4×4.

```
                trước          sau
MIYABI     3.03 px       4.01 px
KAI        2.96 px       3.79 px
ITSUKI     2.49 px       3.28 px
VOICE      3.75 px       3.75 px   (không đổi — vốn đã đúng)
viền hỏng  50% tb        3% tb ; số dải >20%: 18 -> 2
```

Điểm đục gần như không xê dịch: trong 628 352 điểm `alpha ≥ 250`, RGB lệch trung
bình **0.02**, chỉ **3 điểm** lệch quá 8. Alpha toàn ảnh lệch trung bình 0.007
(nhiễu nén lại ASTC). 702 543 điểm đổi RGB — toàn bộ nằm ở vùng chưa đục.

> Hai dải `ch_06_koha` và `ch_13_itsu` vẫn báo 32% / 27% "viền hỏng" sau khi vá.
> **Dương tính giả**: thước đo quét cả nửa trái ô sprite nên vớ phải sprite lạ
> xếp chèn, không phải nhãn. Dựng thử thì cả hai đều đầy đặn hơn hẳn.

> **Lỗi này nhiều khả năng dính mọi asset mod vẽ lại** (`ui_jp`, `scene_jp`,
> `sharedassets*` khác, dải phím, nhãn Q&A, ô GET/TOTAL, tên Profile…). Mới quét
> và vá `sharedassets7.assets`. Chỗ khác chưa đụng.

## Nhãn tab SOUND dày hơn nét gốc — bào lại cho khớp

`python tools\fix_label_weight.py [--apply]`

Chạy **sau** `fix_alpha_bleed.py`. Trả lại phần viền bị ăn mất xong thì lộ ra
chuyện thứ hai: nhãn mod **vốn được vẽ đậm hơn** nét gốc, trước đó lỗi viền che
mất. Đo bề dày thân đứng trong atlas, cô lập từng nhãn bằng mesh tight:

```
gốc   BGM 3.59   MOVIE 3.74   VOICE 3.72        -> mốc 3.72
mod   18 dải, 3.83 .. 4.16                      -> trung vị 4.00
```

Trên màn cũng đúng chừng đó: `MOVIE` chữ `M` 3.66 px, `MIYABI` chữ `M` 4.04 px,
`MIYABI` chữ `I` 4.21 px. Chênh ~0.28 px, mắt đọc thành "đậm hơn một cấp weight".

Bào mòn **1/8 px mỗi bên**: siêu lấy mẫu ×8, lọc min 3×3 một vòng, thu nhỏ lại
bằng trung bình khối — giữ được khử răng cưa, khác hẳn cách hạ ngưỡng alpha
(cách đó làm mép răng cưa trở lại). Chỉ đụng kênh alpha; RGB đã loang đúng từ
đợt trước nên giữ nguyên. Thử 2/8 px thì xuống 3.49 — mỏng quá.

> ### Cô lập bằng mesh, đừng cô lập bằng `textureRect`
>
> Rect của các dải **chồng lên nhau**: `ch_03_ai` và `ch_11_hida` trùm nhau gần
> trọn, `ch_05_yuri` nằm lọt trong `com_frame_01_base`. Đó chính là lý do atlas
> phải dùng mesh tight. Cắt theo rect thì bào nhầm sang tranh sprite khác.
>
> Mesh của mỗi sprite là **đúng** những điểm nó vẽ: `ch_02_kai` có 792/792 điểm
> mực ở nửa trái nằm trong mesh; `ch_01_miya` mesh ôm gọn ô chữ và bỏ ngoài 3522
> điểm của hai sprite tab xếp chèn. Script kiểm tra 18 mặt nạ có rời nhau không,
> chồng một điểm là dừng.

Mesh đọc từ luồng vertex 0 (float3, 12 B/đỉnh), nhóm 4 đỉnh một quad thẳng trục,
đổi sang toạ độ ô cắt bằng nghịch đảo công thức trong `fix_volume_ends.py`.

Đã chạy 17/08/2026 (backup `_backup\sharedassets7.assets.prelabelweight`). Đọc
lại từ disk: mod trung vị **3.74** so với mốc gốc **3.72** (min 3.56, max 3.91).
25 389 điểm alpha đổi; RGB chỉ 3 điểm lệch quá 8. Năm dải gốc không bị đụng —
lệch alpha tối đa 0–6, đúng mức nhiễu nén lại. 85 object, 76 sprite, 0 object
rỗng, vẫn ASTC 4×4.

> `SE` 6.02 và `ch_17_unkn` 5.64 là **ngoại lệ của thước đo**, không phải nét
> đậm: `SE` chỉ có hai chữ mà `S` toàn nét cong, `???` không có thân đứng nào.
> Cả hai bị loại khỏi mốc, và vì là nhãn gốc nên cũng không bị bào.

## Tên trong popup Profile — bỏ chữ Nhật, chỉ để romaji

Màn Profile vẽ tên bằng **hai ô chữ lồng nhau** (`ui_jp`, prefab `Terminal_Profile`):

```
BG/Pop/Common/Name            Image `UL_term_c_popup_prof_moji_name` 540x36
  Text (TMP)   pid 6645790041897977147   ô  66x40, cỡ 31   <- name
    Eizi(TMP)  pid 1526125385128713001   ô 226x40, cỡ 20   <- ruby
```

`Eizi` = 英字 ("chữ Latin"). **Bản gốc 1.0.2 vốn đã mang romaji của nhà phát hành
trong `TerminalProfileData.ruby`**, nên màn hình xưa nay hiện `琥珀 Kohaku`. Đó
chính là lý do 14 dòng `prof_name` trên sheet chưa bao giờ được merge — đổ thẳng
bản dịch vào `name` sẽ ra "Kohaku Kohaku" và tràn ô 66 px. Xem
[[unlogical-official-romanisation]].

`python tools\fix_profile_name.py [--apply]` làm đúng một phép biến đổi,
**không đổi một ký tự nào đang hiện trên màn hình**, chỉ đổi chỗ và cỡ:

```
name = ruby        ruby = ""
```

Ô 66 px vừa khít 2 chữ kanji và **`m_TextWrappingMode = 1`**, nghĩa là chữ Latin
sẽ bị **wrap xuống dòng hai** chứ không tràn — nên bắt buộc phải nới. Đo từ chính
tranh nền: caption "Name" (đã là tiếng Anh) nằm bên trái, gạch chân chạy hết
540 px, mép trái ô Text cách mép trái khung 131 px → còn **409 px** dùng được.

```
m_SizeDelta.x        66 -> 400     (chừa 9 px)
m_TextWrappingMode    1 -> 0       NoWrap
m_enableAutoSizing    0 -> 1       20..31, max ghim đúng cỡ gốc
```

> **Đừng tin số đo bề rộng ở màn này.** `FOT-iroha21popuraStdN-R SDF-Dynamic` là
> font **Dynamic**: bảng glyph nhúng chỉ có 84 mục và **thiếu 21 chữ cái Latin**
> (game nạp thêm lúc chạy từ TTF nguồn). Mọi phép tính đều phải thay thế advance
> nên chỉ là ước lượng (~279 px cho `Himejima Kyosuke`, dư ~130 px). NoWrap +
> auto-size biến sai số đó thành vô hại — cùng cách đã dùng ở
> `fix_recollection_list.py`.

Đã chạy 16/08/2026 (backup `_backup\json.preprofname`, `_backup\ui_jp.preprofname`).
Đọc lại từ disk: bundle `json` **chỉ `TerminalProfileData` đổi nội dung** (36/36
TextAsset), 14/21 dòng chuyển xong; `ui_jp` 7937 object, 0 object rỗng,
dataflags 194, và các bản vá cũ còn nguyên (11 ô nút Q&A vẫn `characterSpacing = 2`,
5 sprite tên Q&A vẫn đủ).

Bảy dòng còn chữ Nhật ở `name` là chỗ giữ chỗ, không hiển thị tên thật:
`主人公`, `モブ1`–`モブ5`, `モブ？`.

Cả 14 tên khớp đúng bản xuất `UNLOGICAL_v2 (5).xlsx` (16/08 20:39) — kể cả `id 4`
`新庄 稜央` = **`Shinjo Rio`**, chỗ mà bản xuất trước đó còn ghi `Shinjo Ryo`.

> Nếu sau này phải sửa tên này lần nữa thì thay **trọn cụm**: `Ryo` trần còn
> trúng `Hinode Ryoku`, nhân vật khác, 80 chỗ.

## Ô Comment của popup Profile — nới ra sát hai icon

Cùng prefab `Terminal_Profile`, ô chữ dài nằm dưới gạch chân "Comment":

```
BG/Pop/Common/Comment・Property   pid rect -6189876832534220432   TMP pid 1053535555780865634
                                 rect 880x150 tại (3,-142), cỡ 31, wrap=1, charSpacing -3.3
BG/Pop/Player/UL_term_c_popup_icon_player_01 / _02   64x64 tại (417,-89) và (417,-158)
```

Toạ độ tính theo gốc `Pop` (1056×624; trên ảnh 1920×1080 tâm `Pop` ở x = 1122).
Ô chữ dùng chung cho cả tab Player (trường `comment`) lẫn tab Spirit.

**Rect vốn đã thừa, không phải thiếu**: mép phải của nó ở 443, tức là chạy xuyên
qua cả hai icon (mép trái icon 385). Cái bó chữ lại là `\n` cứng trong
`TerminalProfileData.comment` — dòng dài nhất chỉ 584 px, dừng cách icon hơn
250 px. Bản gốc Nhật ngắt tay ở 20–21 chữ kanji (~675 px) và **không mục nào quá
3 dòng**; bản dịch ngắt hẹp hơn thế nên phình thành 4–6 dòng, tràn xuống dưới
khung 150 px (3 dòng = 119 px, 4 dòng = 163 px).

`python tools\fix_profile_comment.py [--check|--apply]` làm hai việc cùng lúc —
làm một việc thôi thì màn hình không đổi gì:

```
rect  m_SizeDelta.x        880 -> 800      mép trái -437 đứng yên (thẳng nhãn "Comment")
      m_AnchoredPosition.x   3 -> -37      mép phải 443 -> 363, cách mép icon thấy được
                                           (387) đúng 24 px; TMP không vẽ dưới icon được nữa
data  ngắt lại 13/14 chuỗi comment cho cột 792 px (= 800 × 0.99)
```

> **Mô hình bề rộng phải hiệu chuẩn từ ảnh chụp, đừng tin `m_characterSpacing`.**
> Advance lấy từ **TTF nhúng trong `ui_jp`** (`Font` `FOT-iroha21popuraStdN-R`,
> pid 2079251334914095402, unitsPerEm 1000 — chính bản mod đã thay để có chữ
> Việt; font asset trỏ tới nó là Dynamic, bảng glyph nhúng chỉ 84 mục nên vô
> dụng, xem mục trên). Công thức:
>
> ```
> W(dòng) = tổng(advance) * 31/1000 + (số ký tự - 1) * 1.25
> ```
>
> `m_characterSpacing` ghi **-3.3** nhưng game vẽ *rộng ra*: đo 25 bước chữ liên
> tiếp trên `_2026-08-18_03-12-37.png` (dòng 2 của Kyosuke, 26 chữ ứng đúng 26
> vệt mực) ra **+1.19 ± 0.10 px mỗi khe**, và phần dư không tỉ lệ với bề rộng
> chữ nên là hằng số mỗi khe chứ không phải sai số scale. Lấy 1.25 cho chắc. Với
> mô hình này gốc bút của cả ba dòng rơi đúng x = 685 = mép trái rect, và bề
> rộng dự đoán luôn nhích hơn thực tế ~5 px — lệch về phía an toàn.

Kết quả: 9 mục Player đều còn **≤ 3 dòng** như bản gốc (id 5 và id 7 gọn vào 1
dòng); 5 mục Spirit còn 3–4 dòng, trước đó tới 6. Ba mục Spirit dài nhất
(`id 15` Hotaru, `id 17` Ruri, `id 18` Menou) vẫn 4 dòng = 163 px, quá khung
150 px 13 px — **không cột nào ≤ 822 px cứu được** (id 15 cần 840 px mới xuống 3
dòng, id 17/18 thì xa hơn nữa). Muốn hết hẳn thì phải nới `m_SizeDelta.y`
150 → 176 kèm dời `m_AnchoredPosition.y` -142 → -155 cho khung mọc xuống, hoặc
cắt chữ; chưa làm.

Đã chạy 18/08/2026 (backup `_backup\ui_jp.preprofcomment`,
`_backup\json.preprofcomment`). Đọc lại từ disk, so từng object theo byte:
`ui_jp` 7937/7937 object, **đúng 1 object đổi** (RectTransform đó, vẫn 108 byte),
bản vá tên cũ còn nguyên (`Name/Text` vẫn 400×40, NoWrap, auto-size 20..31);
bundle `json` 37/37 object, **đúng 1 TextAsset đổi**.

> **`check_layout_breaks.py --json` sẽ báo MẤT NGẮT DÒNG cho 13 khoá
> `TerminalProfileData/info[*]/comment`** — đó là chủ ý, cột rộng hơn thì ít dòng
> hơn. Lần chạy sau khi vá báo đúng 13 khoá đó và không khoá nào khác, tức là
> không có gì bị phẳng thêm. Cổng đó dùng để so với backup *trước khi merge
> sheet*, nên đừng chỉa nó vào `_backup\json.preprofcomment`.

## Danh sách SHORT STORY tràn khung

Một hàng của màn "SS LIST" là prefab `SS_Button` trong `sharedassets17.assets`
(**628×64**, `Image` kiểu Sliced làm nền hồng của dòng đang chọn). `Text (TMP)`
căng hết khung nhưng có `m_margin = (181, 0, 30, 0)` chừa chỗ cho số thứ tự và
biểu tượng phong bì, nên bề rộng chữ thật chỉ **417 px** ở cỡ 32 /
characterSpacing 4, NoAutoSize, wrap Normal, overflow Overflow. Sáu tiêu đề
tiếng Việt vượt mức đó và xuống hàng, tràn ra ngoài hàng cao 64 px.

`Buttons` (`level17` pid 39) đặt các hàng bằng `VerticalLayoutGroup` với
`m_ChildControlWidth = 0`, `m_ChildAlignment = UpperCenter`:

```
mép trái = 960 + m_Padding.m_Left/2 - W/2        (canvas 1920×1080)
```

Nới `W` mà không đụng padding thì nền hồng **nở đều sang cả hai bên** và nuốt
mất nhãn `New` nằm ngoài mép trái, nên phải tăng padding kèm theo rồi dời các
con của prefab (đều neo theo tâm) ngược lại đúng nửa phần nở thêm.

`python tools\widen_ss_list.py [--apply]` — 628 → **676**, padding 95 → **143**,
`New` −343 → −367, `OFF`/`ON` 0 → −24, `m_margin.z` 30 → **12**. Chỉ mép phải
của nền hồng dịch ra (1321.5 → 1369.5, thanh cuộn bắt đầu ở 1372, cột
1320–1374 trống hoàn toàn); mọi thứ khác đứng yên từng pixel. Bề rộng chữ
417 → **483 px**, đủ cho cả 20 tiêu đề nằm một dòng — dài nhất là
"Chiếc tai nghe bỏ quên" (467 px), rồi "Bức thư của Fushikura" (456).

Cả hai file vốn không có trong bản vá; script tự chép từ bản gốc 1.0.2 và lưu
`_backup\sharedassets17.assets.presswidth`, `_backup\level17.presswidth`.
Chạy lại vô hại.

### Dải phím `Ⓐ決定 Ⓑ戻る` ở góc — coi chừng bản sao trùng tên

`UL_short_a_key` và `UL_short_c_history_key` **nằm ở hai nơi**: trong `ui_jp` và
trong `sharedassets17.assets`. Màn SHORT STORY đọc bản của `sharedassets17` —
`level17` pid 225 (`Kay`, Image phủ kín 1920×1080) trỏ
`m_Sprite = {m_FileID 4, m_PathID 58}`, mà external thứ 4 của `level17` chính là
`sharedassets17.assets`. Vá bản trong `ui_jp` thì màn hình **không đổi gì**; bản
`ui_jp` của `UL_short_a_key` thậm chí không có prefab nào tham chiếu tới (chỉ
`UL_short_c_history_key` có, ở Image pid 5360002391062628675). `fix_key_prompts.py`
nay có job riêng cho `sharedassets17.assets`, và thêm cờ `--only <chuỗi>` để chạy
lẻ một file:

```powershell
python tools\fix_key_prompts.py --only sharedassets17 --apply
```

Đã chạy 16/08/2026 (backup `_backup\sharedassets17.assets.prekeyprompt-*`):
`Ⓐ決定 Ⓑ戻る` → **Ⓐ Select Ⓑ Back** (hồng `#FEA1AE`, cỡ 19), `Ⓑ戻る` →
**Ⓑ Back** (xám, cỡ 20). Diff nhị phân: đúng **3 object** đổi — atlas
`sactx-0-4096x2048-ASTC 4x4-ShortStory-8d995ad8` và hai sprite (mesh tight
44/21 đỉnh → quad 4 đỉnh); `sprite.image` và ô cắt atlas cùng đếm 2236/1120 px
đục, **lệch 0**. Ghi `.image` làm atlas bị nhúng thẳng vào file nên
`sharedassets17.assets` phình 136 KB → 8,5 MB; **không cần kèm `.resS`** vì hai
texture còn lại vẫn trỏ offset 0 và 8.400.896 vào file `.resS` gốc (8,6 MB) mà
Ryujinx phủ romfs theo từng file nên vẫn lấy được.

## Nút màn Q&A — chữ giãn quá xa

`python tools\fix_qa_spacing.py [--apply]` — hạ `m_characterSpacing` **7 → 2**
cho **11** ô chữ trong `ui_jp`: prefab mẫu `Q&A_Button` cộng `Q&A_Button01..10`
nướng sẵn trong prefab `Q&A` (lẻ ở cột `Left`, chẵn ở cột `Right`; cột phải có
`m_LocalScale.x = -1` nên khung lật ngược).

```
Text (TMP)   rect 532×96, m_margin (24, 9, 21, 18)  ->  bề rộng chữ 487
             font FOT-DotGothic12Std-M SDF-Dynamic (pointSize 58, lineHeight 116)
             fontSize 33, căn giữa, wrap Normal, overflow Overflow, auto-size TẮT
```

Font này **đơn cách** — `m_FaceInfo.m_TabWidth = 29` và TTF nhúng ngay trong
`ui_jp` (pid 1447034940015195371, chính là `ULPixel.ttf`) cho mọi glyph advance
đúng 512/1024 em. Chuỗi mẫu bản gốc `あいうえ五あいうえ十あい` chỉ 12 chữ toàn rộng
nên `cs = 7` gần như không thấy; chữ Latin nửa rộng phải trả đúng khoảng đó cho
**từng chữ cái**, thành ra giãn hẳn.

> ### Hai phần của bước chữ KHÔNG cùng hệ số tỉ lệ
>
> TMP nhân advance của glyph với `fontSize / pointSize`, nhưng nhân
> `characterSpacing` với **`fontSize / 100`** (`currentEmScale`, đơn vị phần trăm
> em — *không* phải `currentElementScale`). Chênh nhau 1,72 lần.
>
> ```
> bước chữ = 29 * 33/58 + cs * 33/100 = 16.50 + 0.33 * cs
> W(n)     = (n-1) * bước chữ + 16.50        <= 487
> ```
>
> `W(n)` cộng `16.50` chứ không phải một bước đầy đủ vì **TMP ngắt theo mép phải
> của glyph**, khoảng cách đuôi không tính.
>
> Đợt vá đầu dùng công thức cũ `(adv + cs) * fontSize/58`, ra bước chữ nhỏ hơn
> thật, và hứa nhầm rằng `cs = 3` đủ kéo "Người hợp cạ trong Unlogical" về một
> dòng — thực tế **thiếu đúng 1,7 px**. `adv_layout.py` vẫn dùng công thức cũ;
> đó chính là lý do nó *luôn lệch về phía rộng hơn* và `SAFETY = 0.985` che mất.

```
cs=7 -> 18.81 px/chữ (26 chữ/dòng)   cs=3 -> 17.49 (27)
cs=2 -> 17.16 (28)                   cs=0 -> 16.50 (29)
```

Script tự đối chiếu mô hình với **sáu** điểm ngắt dòng đọc từ hai ảnh chụp thật
(bảng `CALIBRATION`) trước khi cho vá, sai một mốc là dừng. Cả sáu đều khớp, kể
cả mốc sát nút `W(26) = 486.7` trong khung 487.

Chọn **2.0**: "Người hợp cạ trong Unlogical" (28 chữ) cần 479.8/487 px, dư 7,2 px.
Kết quả **8/10 → 9/10 mục một dòng**; mục còn lại "Thích làm nũng hay thích được
người yêu nuông chiều?" (52 chữ) từ **3 dòng xuống 2** — 52 chữ thì `cs = 0` cũng
không cứu nổi (cần 29 chữ/dòng × 2 dòng), muốn một dòng phải rút gọn bản dịch hoặc
bật auto-size.

Hai dòng cao 99 px trong ô 96 px, mà bước hàng là 121 px nên vẫn thừa ~11 px,
không đè lên nút bên dưới như bản 3 dòng.

Đã chạy hai đợt 16/08/2026 (backup `_backup\ui_jp.preqaspacing` giữ trạng thái gốc
`cs = 7` trước cả hai). Diff nhị phân đợt hai so với backup đó: 15 object đổi —
**11 ô chữ của mình**, cộng 4 object của việc màn SECTION làm song song
(3 sprite tight→quad nên `byte_size` tụt đúng 3084, và atlas 4096×4096); 7937
object, 0 object rỗng.

## Tên nhân vật trên dải tiêu đề màn Q&A

`python tools\fix_qa_names.py [--apply]` — tên ở góc trên là **tranh vẽ**:
`Q&A_Front_Individual_01..05` trong `ui_jp`, mỗi cái một `Name` (Image, rect
328×54) trỏ sprite `UL_q&a_chara_icon_frame_nm_0N_*`. Sprite đóng gói **sát nét**
nên ô atlas chỉ bằng đúng phần mực, còn `m_Rect` mới là 328×54.

| sprite | ô atlas | gốc | thành |
|---|---|---|---|
| `nm_01_miya` | 82×40  | 雅火       | Miyabi        |
| `nm_02_kai`  | 148×40 | 宗像　戒    | Munakata Kai  |
| `nm_03_ran`  | 148×40 | 永守　藍    | Nagamori Ran  |
| `nm_04_soi`  | 190×40 | 弥坂　奏壱  | Yasaka Soichi |
| `nm_05_yuri` | 118×37 | ユーリ      | Yuri          |

Cách đọc lấy đúng **bảng tên của chính bản dịch**: nameplate trong `ScenarioData`
ghi cả hai vế và đếm được `雅火/Miyabi` ×3872, `宗像 戒/Munakata Kai` ×3724,
`永守 藍/Nagamori Ran` ×4036, `弥坂 奏壱/Yasaka Soichi` ×3904, `神楽 侑莉/Yuri`
×3986 (so với `神楽 侑莉/Kagura Yuri` chỉ ×6). Khớp luôn hậu tố tên file.

**Cỡ 24 do ô hẹp nhất quyết định.** Font `FOT-DotGothic12Std-M` (= `ULPixel.ttf`)
đơn cách, chữ Latin rộng nửa em: `Munakata Kai` / `Nagamori Ran` 12 chữ →
12 × 24/2 = 144 px, ô chỉ có 148. Năm nhãn thay nhau vào **cùng một chỗ** khi đổi
nhân vật nên phải chung một cỡ. 24 cũng đúng **2× lưới điểm ảnh** của font
(thiết kế 12 px/em) nên nét sắc; 27–28 vừa ô nhưng lẻ lưới, nét răng cưa.

> **Đính chính 27/08/2026: lưới của `ULPixel` là 16 px/em, không phải 12.** Đọc
> thẳng `glyf` thì mọi toạ độ đều là bội của 64 trên `unitsPerEm` 1024, tức
> 1024/64 = **16 điểm mỗi em**. Cỡ sắc nét là 16/32/48/64 (đo tỉ lệ pixel khử
> răng cưa = 0 %); cỡ 24 rơi vào 1,5 px một điểm nên **vẫn bị khử răng cưa**
> (51 % pixel nửa mực), cỡ 33 ở "Ô GET/TOTAL của màn MOVIE" cũng vậy. Cỡ 24 ở
> đây do bề rộng ô quyết định — kết luận chọn cỡ vẫn đứng, chỉ lý do "2× lưới"
> là sai. Xem "Thẻ THE END" ở cuối tài liệu.

> **Không nới ô ra được — đã thử.** Muốn cỡ 36 (3× lưới, gần sức nặng chữ kanji
> gốc, mực cao 29 px thay vì 20) thì "Miyabi" cần 102 px trong ô 82. Quanh ô có
> 151 px trong suốt bên trái và 22 px bên phải, **nhưng vùng đó nằm trong
> `textureRect` của hai sprite khác** (x 567..859 và x 941..1022) — vẽ đè vào là
> mực hiện lên giữa hai sprite kia. Muốn to hơn phải **dời hẳn ô** sang chỗ trống
> thật của atlas.
>
> `uvTransform` là phép affine từ toạ độ sprite sang pixel atlas, đã kiểm chứng
> số học trên `nm_01_miya`:
> ```
> texX = localX * uvTransform.x + uvTransform.y     uvTransform.x = m_PixelsToUnits
> localX = (textureRectOffset.x - m_Rect.width * pivot.x) / m_PixelsToUnits
> ```
> Nới ô mà giữ nguyên `localX` thì `uvTransform` **không đổi**; dời ô thì phải
> tính lại cả hai. Xem [[unity-sprite-uvtransform-trap]].

Đã chạy 16/08/2026 (backup `_backup\ui_jp.preqanames`). Diff nhị phân: **đúng 6
object đổi** — atlas `sactx-0-2048x1024-ASTC 4x4-Q&A-9a1394f3` và 5 sprite (mesh
tight 11–32 đỉnh → quad 4 đỉnh); 7937 object, 0 object rỗng, `dataflags 194`
(LZ4HC), và `characterSpacing = 2` của nút Q&A vẫn còn nguyên.

> **Ryujinx đang chạy thì `os.replace` báo WinError 5.** Emulator giữ `ui_jp` mở
> ở chế độ cho đọc/ghi nhưng **không cho rename** (thiếu `FILE_SHARE_DELETE`).
> Mở `r+b` ghi đè tại chỗ thì được — nhưng phải `del Container` + `gc.collect()`
> trước, vì UnityPy cũng còn giữ handle của chính file nguồn. Script ghi ra
> `.out`, ghi đè tại chỗ, rồi đối chiếu SHA-256 mới xoá file tạm.

## `adv_layout.py`

Mô hình bố cục của hộp `Message(Normal)/Text` và `Message(Highest)/Text`
(`level10` pid 886/887): rect 1400×186, font `FOT-NewRodinProN-DB SDF`
(pointSize 58, lineHeight 116, asc 51.04, desc −6.96), fontSize 42 auto-size
28–42, characterSpacing 5.3, lineSpacing −42.

```
advance(px)  = (glyphAdvance + characterSpacing) * fontSize / pointSize
line pitch   = fontSize * (lineHeight/pointSize + lineSpacing/100)
block height = (n-1) * pitch + fontSize * (asc-desc)/pointSize
```

Đã hiệu chuẩn với ảnh chụp thật: vị trí từng từ dự đoán lệch dưới 2.4 px trên
đoạn dài 730 px và **luôn lệch về phía rộng hơn**, và mô hình tái tạo đúng
từng ký tự các điểm ngắt dòng của game. Bảng advance đọc thẳng từ font asset
trong bundle `font_jp`, cache vào `_advances.json`.

`SAFETY = 0.985` là mép an toàn: ngắt ở 99.9% thì chỉ cần một cặp kerning là
TMP ngắt lại, và chú thích lại nhảy như cũ.

## Dải phím ở chân màn hình (Ⓐ決定 Ⓑ戻る …)

Những dải này **không phải chuỗi ký tự** — chúng là tranh vẽ nằm trong atlas
ASTC của từng màn hình, nên tìm `決定` / `戻る` khắp `romfs` lẫn
`global-metadata.dat` đều không ra. Tổng cộng game có **17 dải** kiểu này, tên
đều dạng `UL_*_key*`.

`python tools\keyprompt_audit.py [thư_mục]` — kiểm kê cả 17 dải, đọc bản vá
trước rồi mới tới bản gốc, và xuất một tấm `_audit.png` xem được ngay dải nào
còn tiếng Nhật. File `.resS` thiếu trong bản vá thì tự mượn của bản gốc (game
lấy từ romfs nền nên **không cần** chép `.resS` vào bản vá).

| màn hình | file | sprite |
|---|---|---|
| ADV backlog | `ui_jp` | `UL_adv_backlog_key`, `…key2` |
| ARCHIVE | `sharedassets9` | `UL_archive_key` |
| CHAPTER / SECTION | `sharedassets6` + `ui_jp` | `UL_section_abc_com_key` |
| Từ điển | `sharedassets22` | `UL_dictionary_key` |
| LIBRARY | `sharedassets5` | `UL_library_key` … `key5` |
| Bản đồ | `sharedassets10` | `UL_map_key` |
| Hướng dẫn | `sharedassets11` | `UL_manual_key` |
| MOVIE | `scene_jp` | `UL_movie_a_key` |
| MUSIC | `sharedassets13` | `UL_music_key` |
| OPTION | `sharedassets7` | `UL_option_com_key` |
| Q&A | `ui_jp` | `UL_q&a_key` |
| Recollection | `sharedassets21` | `UL_recolle_key` |
| Save/Load | `sharedassets19` | `UL_salo_key` |
| SHORT STORY | `sharedassets17` + `ui_jp` | `UL_short_a_key`, `UL_short_c_history_key` |
| STATUS | `ui_jp` | `UL_status_a_com_key`, `UL_status_b_ind_key` |
| SYSTEM MENU | `ui_jp` | `UL_sys_plate_key` |

Vài sprite **có bản trùng tên ở hai nơi** (`sharedassets` của cảnh và `ui_jp`).
Cảnh dựng sẵn đọc bản trong `sharedassets`, nên chỉ vá `ui_jp` thì màn hình
không đổi — vá cả hai cho chắc.

### `keyart.py`

Lớp bọc UnityPy lo phần khó của mọi sprite atlas: `Container(...).sprite(tên)`
trả về `.crop()` / `.paste()` / `.full_rect_mesh()`. Ba điểm dễ sập:

- **Ô thật của sprite nằm ở `SpriteAtlas.m_RenderDataMap`**, tra bằng
  `m_RenderDataKey`. `m_RD` của chính sprite ghi `textureRect` theo hệ toạ độ
  canvas 1920×1080 chứ không phải toạ độ atlas — dùng nhầm là cắt trúng chỗ khác.
- **Mesh thì ngược lại: nằm ở `m_RD` của sprite**, `SpriteAtlasData` bản Unity
  này không mang mesh. Mesh gốc là *tight*, `UnityPy` cũng áp nó khi đọc
  `sprite.image` y như game, nên vẽ chữ mới xong phải `full_rect_mesh()`.
- **Bundle chứa nhiều serialized file**: `path_id` trùng nhau giữa các file, phải
  tra theo cặp `(file, path_id)`. `scene_jp` là ca dính lỗi này.

### `fix_key_prompts.py`

`python tools\fix_key_prompts.py [--only <chuỗi>] [--apply]`

Giữ nguyên icon nút bấm (cắt thẳng từ tranh gốc), chỉ xoá chữ Nhật rồi vẽ lại
bằng **`FOT-NewRodin ProN DB`** — font UI của chính game, khớp IoU **0.995** với
chữ đã dịch sẵn ở `UL_archive_key` và `UL_music_key`.

**Cỡ chữ.** Nhắm cỡ **28** (ứng với đĩa nút 29 px, cho nét cao ~24 px) rồi rút
dần cho tới khi xếp vừa bề ngang ô — thực tế ra 20–28 tuỳ ô rộng hẹp. Mốc là
tranh tiếng Anh **chính chủ** của nhà phát triển: `UL_term_key_02` để chữ cao 27
px cạnh đĩa 27 px, khoảng cách icon→chữ 6, giữa hai cụm 12. Đợt đầu dùng cỡ 19
(nét cao 16 px) nên chữ trông bé hẳn so với nút — đừng lặp lại.

**Xếp chỗ.** Chọn xong cỡ thì **dồn hết chỗ dư vào khoảng cách giữa các cụm**
(tối đa 34 px), dư nữa thì đẩy cả dải sang phải cho sát mép. Nhờ vậy dải căng
đầy ô đúng như bản Nhật thay vì bỏ trống một khoảng bên phải, và cụm `Ⓑ Back`
không bị dồn về trái.

Khai báo được **nhiều dòng** (`UL_adv_backlog_key`): mỗi dòng một danh sách,
thứ tự từ trên xuống, khớp với các dải mực mà script tự dò. Một "icon" có thể là
**cặp nút** như `ⓁⓇ` — khai báo trọn khối `(2, 66, …)`, hàm kiểm tra tự chia đôi.
Cụm **không có nút** thì để `(None, None, "chữ")` — dùng cho câu nhắc ở màn nhập
tên. Phần tử đầu mỗi dòng khai thêm được **font riêng và cỡ ghim**:
`(None, None, "Please enter your name", FONT_PIXEL, 24)`.

> Màn nhập tên trộn hai mặt chữ: hàng phím dùng `FOT-NewRodin ProN DB`, còn câu
> nhắc dùng **`ULPixel` cỡ 24** cho khớp ô `LAST NAME / Suzuno` ngay trên nó (đo
> lại từ bản vá cũ, IoU 0.978). Vẽ câu nhắc bằng NewRodin là mất chất dot-matrix
> của cả màn.

Từ vựng bám theo tiếng Anh **chính chủ** của game (`UL_map_key`,
`UL_term_key_02` vốn đã là tiếng Anh): 決定 → *Select*, 戻る → *Back*,
再生 → *Play*, シーン再生 → *Play scene*, CGコメント開始 → *CG comment*,
初期化 → *Reset*, ロック → *Lock*.

Script **chạy lại vô hại và đổi tham số được**, vì ảnh luôn dựng lại từ bản gốc
1.0.2 chứ không đọc bản vá. Nếu đọc bản vá thì lần chạy thứ hai sẽ cắt nhầm
"icon" ở toạ độ cũ (đĩa Ⓑ đã dời chỗ) và phá nát art đã dịch. `check_spec()` bắt
lỗi khai báo sai bằng cách kiểm mọi toạ độ icon có thật sự là hình tròn không.

Backup: `_backup\<file>.prekeyprompt-<ngày giờ>`.

### `fix_sys_plate_key.py`

Riêng `UL_sys_plate_key` (SYSTEM MENU) nghiêng ~15° nên tách ra. Script xoay
**ảnh phân tích** cho chữ nằm ngang để đo toạ độ, nhưng khi ghép lại chỉ xoay
*lớp chữ mới* — icon, mã vạch, khung tem giữ nguyên pixel gốc, không lấy mẫu lại
lần nào. Backup `_backup\ui_jp.presysplate-<ngày giờ>`.

### Lưu ý về dung lượng

Đặt `.image` cho texture đang stream từ `.resS` sẽ **nhúng thẳng** pixel vào
`.assets` (`m_StreamData` rỗng) nên file phình ra: `sharedassets6` 170 KB →
16.9 MB, `sharedassets5` → 8.6 MB, `sharedassets11` → 1.1 MB. Vẫn rẻ hơn chép
nguyên `.resS` (`sharedassets10.assets.resS` một mình đã 62 MB) và game chạy
bình thường, vì các texture còn lại vẫn trỏ đúng offset vào `.resS` của romfs nền.

## Nhãn route trên thẻ SAVE/LOAD còn tiếng Nhật (`戒・SECTION 1`)

Thẻ save hiện `<tên nhân vật>・<chương>`. Phần chương lấy từ `ChapterData.chapter`
(`SECTION 1`, đã Latin sẵn), còn **tên route là literal IL2CPP**, không nằm trong
bundle nào — nên grep `romfs` không ra:

```
#14936 ユーリ・   #15016 奏壱・   #15030 戒・   #15074 藍・   #15090 雅火・
```

> **Đừng nhầm với `SystemTextData`.** `resources.assets` có id 84–88 đúng bằng năm cái
> tên đó và slot `JP` **đã dịch từ trước** (`Miyabi`, `Kai`, `Ran`, `Soichi`, `Yuri`).
> Màn save vẫn ra tiếng Nhật vì nó không đọc bảng đó. Thấy chuỗi đã dịch trong dữ liệu
> mà màn hình vẫn sai thì phải nghĩ tới literal, đừng sửa lại chỗ vốn đã đúng.

> **Chỉ vá biến thể có `・`, tuyệt đối không đụng literal tên trần.** `戒` (#15029),
> `藍` (#15072), `雅火` (#15089), `奏壱` (#15015), `ユーリ` (#14935) là **khoá tra cứu** —
> `Q&AData.bustup.chara`, `GenebarkChatCharaIdData`, `AdvCharacterBustUpDatabase` đều
> so bằng đúng mấy chuỗi đó. Biến thể `X・` thì chỉ dùng để ghép nhãn nên đổi vô hại.

Đã vá 28/08/2026 bằng `tools\metadata_term.py` (backup
`_backup\global-metadata.dat.prelitterm3..7`). Ngân sách byte vừa khít, không phải
nới khối nào:

| literal | cũ | mới | byte |
|---|---|---|---|
| #15090 | `雅火・` | `Miyabi・` | 9 → 9 |
| #15030 | `戒・` | `Kai・` | 6 → 6 |
| #15074 | `藍・` | `Ran・` | 6 → 6 |
| #15016 | `奏壱・` | `Soichi・` | 9 → 9 |
| #14936 | `ユーリ・` | `Yuri・` | 12 → 7 |

Giữ nguyên dấu `・` — đó là dấu phân cách của chính thiết kế thẻ. `Kai - ` cũng vừa
đúng 6 byte nếu muốn đổi.

### Hậu tố mùa của route EXTRA — phải xếp lại cả vùng

`python tools\fix_extra_season_label.py [--apply]`. Ba literal `・夏\n\r`, `・春\n\r`,
`・秋\n\r` (#14955–57) mỗi cái 8 byte. `・Hè` và `・Thu` vừa khít, nhưng **`・Xuân` cần 10**
nên `metadata_term.py` bó tay — nó chỉ vá tại chỗ từng literal một.

Cách ra: bảng literal là cặp `(length, dataIndex)`, mà **cả 37 byte** từ `・` (#14953) đến
hết `・秋` là của riêng năm literal ấy, không literal nào khác chen vào. Xếp lại cả vùng
thì tự do phân bổ:

```
373480  ・EXTRA\n\r   10      <- #14954, và #14953 trỏ vào 3 byte đầu
373490  ・Hè\n\r       8      <- #14955
373498  ・Xuân\n\r    10      <- #14956
373508  ・Thu\n\r      8      <- #14957
373516  \x00            1      thừa
```

> **Mẹo đủ chỗ: cho `・` (#14953) trỏ CHỒNG lên 3 byte đầu của `・EXTRA\n\r`.** Literal chỉ
> là `(offset, length)` nên chồng lấn khi đọc là vô hại, và nội dung nó nhận vẫn đúng bằng
> `・`. Không có mẹo này thì thiếu đúng 2 byte — 36 cần, 34 có.

Đã chạy 28/08/2026, backup `_backup\global-metadata.dat.preseason`. Kiểm sau khi ghi:
kích thước file không đổi, **39 byte đổi — 34 trong vùng dữ liệu, 5 trong bảng literal, 0
chỗ khác**, và năm khoá tra cứu tên trần vẫn nguyên. `・EXTRA` vốn đã Latin nên giữ. Chạy
lại lần hai thì script từ chối vì không thấy chuỗi Nhật cũ.

## Tên nhân vật chính vẫn là `環無` sau khi bấm New Game

Vá literal 15063 trong `global-metadata.dat` **chỉ đổi giá trị mặc định cho máy
chưa từng chơi**. Máy đã có save thì màn nhập tên lấy tên từ `auto_data`, nên
bấm New Game vẫn thấy `環無` — trông y như bản vá không ăn.

`python tools\fix_save_playername.py [--apply]` — **đóng Ryujinx trước**, script
sửa `m_PlayerName`, `m_LanguagePlayerName`, `m_LanguageNickName` trong cả hai khe
nhật ký của `%APPDATA%\Ryujinx\bis\user\save\0000000000000001\{0,1}\auto_data`
thành `Kanna`, backup `_backup\auto_data.slot{0,1}.prename-<ngày giờ>`.

Bố cục `auto_data`: 524288 byte = một luồng gzip từ offset 0 rồi đệm 0. Giải nén
ra đúng 524288 byte gồm tiền tố độ dài kiểu .NET `BinaryWriter` (7-bit), JSON
UTF-8 (~464 KB, 65 trường), rồi đệm 0. Không có checksum ngoài CRC của gzip, nên
ghi lại thoải mái miễn giữ đúng hai kích thước đó. `m_CurrentLanguage = 0` (Nhật)
nên chỉ chỉ số 0 của hai mảng ngôn ngữ được đọc; chỉ số 1 là `Hina`, tên tiếng
Anh chính chủ, để nguyên.

## Ô GET/TOTAL của màn MOVIE

`UL_movie_a_total_plate` (348×243, trong `scene_jp`) gộp chung khung, chữ
`GET/TOTAL`, đường kẻ, con robot và hai dòng `なまえ：` / `すずの`.

`python tools\fix_movie_total_plate.py [--apply]` — xoá đúng hộp
`(60, 134)-(192, 208)` (chừa robot ở x ≥ 196) rồi vẽ `NAME:` / `Suzuno` bằng
`ULPixel` cỡ 33, canh **chữ hoa cao 21 px** cho khớp `GET/TOTAL` ngay trên, giãn
chữ 4 px theo nhịp của dòng đó. Mesh tight 29 đỉnh nên dựng lại thành quad.
Backup `_backup\scene_jp.pretotalplate-<ngày giờ>`.

PIL không có tuỳ chọn tracking nên phải vẽ từng ký tự rồi tự cộng khoảng giãn.

## Nhãn còn tiếng Nhật ở màn SECTION SELECT

Ba nhãn này **nằm chung sprite với đồ hoạ khác** nên grep không ra, mà dò theo
tên sprite cũng không ra vì tên chỉ nói "frame_base" / "love_on":

| sprite | ô | cũ | mới |
|---|---|---|---|
| `UL_section_b_skill_chara_frame_base` | 1104×100 | `セレクター / フラグ` ở mép phải | Selector / Flag |
| `UL_section_b_opera_ON_moji` | 241×30 | `オペレータースキル` | Operator Skill |
| `UL_section_c_love_HIGH_on` / `LOW_on` | 504×92 | `好感度` xếp dọc ở mép phải | Likability xoay 90° |

```powershell
python tools\fix_selector_flag_label.py [--apply]
python tools\fix_section_labels.py [--apply]
```

**Từ tiếng Anh lấy từ chính hình nền của game, đừng tự dịch.**
`UL_section_b_bg_on_operator` in "OPERATOR SKILL"; `UL_section_c_chara_*` (nền
trang, 1620×840, nằm trong `ui_jp`) in "Likability" và "High/Low" **xoay theo
chiều kim đồng hồ, đọc từ trên xuống** — nhãn dọc bám đúng chiều đó. Đừng dịch
`好感度` thành "Amity": "AMITY" là nền của trang `section_b`, còn `好感度` nằm trên
thanh của trang `section_c` mà nền trang đó in "Likability".

Cả ba đều có bản trùng tên ở `sharedassets6.assets` **và** `ui_jp`; cảnh dựng sẵn
đọc bản `sharedassets6`, nhưng cứ vá cả hai.

Nhãn `オペレータースキル` giãn chữ rất rộng cho đầy ô; bản dịch cũng giãn chữ để
lấp đúng bề ngang đó thay vì để trống một mảng bên phải.

Đã soát hết 75 sprite của `sharedassets6` (kể cả 4 nền 1620×840): ngoài ba nhãn
trên, không còn chữ Nhật nào ở màn này.

## Nhãn `選択肢` của dòng lựa chọn trong BACKLOG

Màn BACKLOG dựng mỗi dòng từ một template có sẵn trong `ui_jp`, container
`assets/assetbundleresources/ui/ローカライズ/jp/adv/backlog/backlog_scrollview.prefab`,
nằm dưới `Scroll View/Viewport/Content`:

| template | `BackName_TMP` | ai ghi |
|---|---|---|
| `Log_Base` | `矢代` | code ghi đè lúc chạy |
| `Log_Base_Chat` | `Suzuno` | code ghi đè lúc chạy |
| `Log_Base_Chat_Select` | `Suzuno` | code ghi đè lúc chạy |
| `Log_Base_SELECT` | **`選択肢`** | **không ai ghi — hiện thẳng ra màn hình** |

Ba template kia mang tên nhân vật giả (`矢代`, `Suzuno`, và `ダミーテキスト` ở
`BackMessage_TMP`) vì dòng thoại có người nói, code nạp tên vào lúc chạy. Dòng
lựa chọn thì **không có người nói**, nên chuỗi ghi trong prefab chính là chữ chạy
trên máy. Đó là chỗ duy nhất phải sửa — và cũng là lý do không thể tìm ra nó bằng
cách soát `global-metadata.dat`.

```powershell
python tools\fix_backlog_select_label.py [--apply]
```

Ô chữ 120×50, cỡ 32, `characterSpacing` 4, pivot x = 0, canh trái,
`overflowMode` = Overflow:

```
選択肢    102.6 px          Choice   138.6 px          Choices  161.4 px
```

Tràn 19 px sang phải là vô hại — bên phải nhãn là khoảng trống trên nóc khung
trắng, và ba template kia vốn tràn nhiều hơn thế (`Suzuno Kanna` ≈ 250 px trong
đúng ô 120 px ấy, ảnh chụp máy thật cho thấy vẫn một dòng). Điều **thật sự** ràng
buộc là `m_TextWrappingMode = 1`: nhãn phải là **một từ**, không có chỗ ngắt, thì
mới chắc chắn không rơi xuống dòng hai. `Lựa chọn`, `SKIP CHOICES` … thì có thể —
đừng đặt vào ô này.

`Choice` bám cách gọi sẵn có của bản vá: ô `SKIP CHOICES` ở màn CONFIG (tranh vẽ
trong atlas) đã dịch `選択肢` thành "choices".

`genebark.prefab` cũng chứa `選択肢`, nhưng ở `uiGroups[0].groupName =
「選択肢テキスト」` — tên nhóm animation, là khóa tra cứu, không hiện ra màn hình.
**Không đụng.**

`Log_Base_SELECT` không có bản trùng ở `sharedassets*` hay `resources.assets`
(grep `Log_Base_SELECT` / `BackName_TMP` ra 0) — chỉ vá `ui_jp` là đủ.

## Thẻ THE END — tiêu đề ending vẫn còn tiếng Nhật

`python tools\fix_endcard_title.py [--check|--apply]` — dòng
`#017　くらい、つめたい` dưới chữ `THE END` sau mỗi BAD END **là tranh vẽ**: 32
texture 1920×1080 trong bundle `StreamingAssets/cg/cg_end`, gọi qua bốn macro
`エンドカード_*` của `macro` (`resources.assets`). Trang Ending List đọc
`SceneReplayData` nên đã dịch từ lâu; thẻ thì không đổi theo.

Tiêu đề lấy thẳng từ `SceneReplayData` (`#recollection_NN` → ending `NNN`), nên
thẻ và danh sách luôn khớp từng chữ. `SceneReplayData` có 38 mục, `cg_end` chỉ có
32 tranh — sáu số thiếu (013, 020, 025, 030, 036, 038) là các END đẹp, chúng chạy
credit chứ không hiện thẻ. Đúng 32 lời gọi macro trong `ScenarioData`.

Bốn kiểu thẻ, mỗi kiểu một bố cục:

```
a_bad_001   9 thẻ   nền navy + lưới ô,      chữ điểm ảnh sáng,  giữa 959.5   baseline 764
a_bad_002   7 thẻ   nền đen + lưới phối cảnh, chữ điểm ảnh trắng, giữa 959.5   baseline 625
a_bad_003  11 thẻ   nền trắng bản vẽ,        chữ điểm ảnh xám đá, giữa 960     baseline 647
b_bad_sad   5 thẻ   nền hoa/lông vũ,         gothic mảnh NGHIÊNG, giữa 1566.5  baseline 641
```

Ba kiểu đầu là `FOT-DotGothic12Std-M` cỡ em 45 (kiểu 001) và 36 (kiểu 002/003).
Bản dịch đã thay font đó bằng `ULPixel` trong `ui_jp` nên thẻ cũng vẽ bằng
`ULPixel` cho đồng bộ với chữ điểm ảnh trong game — **cỡ 48 cho cả ba kiểu**.

> **Lưới của `ULPixel` là 16 px/em, không phải 12.** Chỉ 32/48/64 mới ra nét sắc
> (đo: tỉ lệ pixel khử răng cưa = 0 %); 36 hay 45 — đúng cỡ tranh gốc — thì nhoè.
> Em gốc 45 ↔ 48 lệch 7 %, còn 36 ↔ 48 thì dòng dài thêm 1/3; vẫn chọn 48 vì
> khung đủ rộng và ba kiểu thẻ cùng một cỡ trông liền mạch hơn.

Kiểu `b_bad_sad` không phải chữ điểm ảnh: gothic mảnh **nghiêng**, `#NN` thì đứng
thẳng, đậm hơn (mực `(149,149,149)` so với `(182,183,184)`) và baseline cao hơn
5 px. Vẽ bằng `FOT-DNPShueiMGoStd-L` cỡ 37 (shear 0.18, xoay quanh **baseline**
chứ không phải tâm ảnh — xoay quanh tâm đẩy cả dòng sang ngang ~3 px) và
`-B` cỡ 23 cho `#NN`. Độ nghiêng 0.18 đo từ chính tranh gốc bằng cách trượt mask
theo nhiều hệ số và lấy hệ số làm cột mực dồn nhất.

**Xoá chữ cũ bằng nội suy dọc, không tô đè.** Dựng mask nét trong đúng khung chữ
gốc, nở 3 px, rồi mỗi cột lấy màu nội tuyến giữa hàng sạch ngay trên và ngay
dưới. Nền cả bốn kiểu trong dải đó chỉ có vạch **dọc** hoặc dải màu mượt nên nội
suy dựng lại đúng nguyên trạng — kể cả vạch lưới chạy xuyên qua chữ. Đã kiểm
trước khi vá: không hàng lưới **ngang** nào cắt qua khung chữ (kiểu 001 lưới ngang
ở y 619–621 và 780–782, khung chữ 714–778), và ở kiểu 002 vùng đen liền mạch từ
x 412 đến 1507 nên vạch phối cảnh nằm ngoài tầm.

Bề rộng dòng dài nhất (`#035 Bằng đôi chân này, một bước, rồi một bước nữa`) là
1217 px — script tự báo `TRÀN LỀ` nếu dòng nào vượt `safe` của kiểu thẻ.

Đã chạy 27/08/2026, backup `_backup\cg_end.endcard` (= bản gốc 1.0.2, trước đó
romfs chưa có file này). Diff nhị phân: **đúng 32 Texture2D đổi**, 32 Sprite và
`AssetBundle` **giữ nguyên từng byte**; 65 object, 0 object rỗng. Ngoài khung chữ
lệch tối đa 12/255 một kênh (nhiễu mã hoá lại ASTC), trung bình 0,003. File phình
3,90 MB → 7,70 MB vì `image data` bị nhúng thẳng thay cho `.resS` trong archive.

> **Luôn dựng lại từ bản gốc `UNLOGICAL_v2`, không đọc `romfs`.** Chạy lần hai
> trên tranh đã vá thì mask nét sẽ bắt đúng chữ tiếng Việt vừa vẽ và khung chữ
> gốc không còn đúng nữa. Script ghim `STOCK` nên chạy lại bao nhiêu lần cũng ra
> cùng một kết quả.

Font lấy thẳng từ `ui_jp` của bản dịch lúc chạy (rút ra thư mục tạm của hệ thống), nên
không phụ thuộc thư mục scratchpad nào — khác `fix_key_prompts.py` và các script
cùng họ, vốn trỏ vào một scratchpad đã bị dọn.

## Sub-graphic SELECT của Stage 1 (spec `anim02_19..22` của `fix_anim_text.py`)

Cảnh Selector chọn đường ray không phải chuỗi ký tự — là **tranh** trong bundle
`StreamingAssets/anim/anim02`, gọi từ script bằng `[anim slot=0 file=NN seqno=…]`
(ví dụ `00_03` dòng 387: `[anim slot=0 file=22 seqno=10 layer=back]`, ngay dưới
comment `;//演出：サブグラ　３種のウィンドウあり　『犠牲者２名』のウィンドウが光る`).

Bốn texture 1920x1080, một bộ:

| file | trạng thái |
| --- | --- |
| 19 | chưa chọn — cả ba viên đều mờ |
| 20 | đã chọn 『自殺』 — viên A sáng + nhãn `Select` + chấm nối |
| 21 | đã chọn 『犠牲者５名』 |
| 22 | đã chọn 『犠牲者２名』 |

**Chữ nằm đúng một toạ độ ở cả bốn texture** — chỉ nền viên đổi giữa mờ và sáng —
nên một bảng `PILLS` dùng chung được. Hộp mực chữ Nhật gốc:

| viên | hộp mực | tâm viên | khoảng trống giữa hai hoạ tiết mạch |
| --- | --- | --- | --- |
| A `自殺` | x 343..395, y 429..449 | 367,5 | x 288..461 (174 px) |
| B `犠牲者５名` | x 678..792, y 627..649 | 734,0 | x 655..828 (174 px) |
| C `犠牲者２名` | x 1567..1681, y 446..467 | 1623,5 | x 1544..1717 (174 px) |

Khoảng trống đo trên texture **trạng thái sáng** — ở trạng thái mờ nền viên
chuyển màu quá mượt nên phép dò hoạ tiết bám vào cả nền. Chữ canh giữa theo tâm
viên nên bề ngang tối đa là `2 × min(tâm − trái, phải − tâm)` ≈ **160 px**.

Tên ba đường ray lấy từ chính `ScenarioData` đã dịch (『Tự sát』 114 lượt,
『2 người hy sinh』/『5 người hy sinh』 trong nhóm 232 lượt "hy sinh"), để người
chơi nghe Hắc phục đọc tên đường ray xong nhìn lên màn hình thấy trùng từng chữ.
`5 người hy sinh` cỡ 22 rộng 152 px — vừa, còn ~3 px mỗi bên.

Cỡ chữ Nhật gốc đo được ~23 px/em (`犠牲者５名` rộng 115 px). Chữ Latin đặt cỡ 22
mới lọt khung, và canh giữa theo **hộp mực** chứ không theo đường chân chữ: dấu
thanh (`ườ`) đội lên và dấu nặng (`ự`) thò xuống làm hộp mực lệch hẳn so với chữ
Nhật, canh theo baseline thì cả dòng tụt xuống 4 px.

**Xoá chữ cũ bằng nội suy NGANG, ngược với `fix_endcard_title.py`.** Nền viên
chuyển màu theo chiều **dọc**, nên dọc theo một hàng nó gần như phẳng còn nội suy
dọc phải bắc qua trọn 21 px thân chữ Nhật — thử lần đầu để lại vệt sọc thấy rõ.
Mask phải nở 2 px: nét chữ nhạt dần ra nền hồng nên ngưỡng màu (`R−G>90`,
`G<150`) không bắt được rìa khử răng cưa, chính rìa sót lại thành vệt.

**Viên thuốc có alpha giảm dần ra hai đầu** — 250 ở giữa, ~128 ở mép. Chữ Nhật
gốc rộng đúng bằng vùng alpha ≥ 240 (x 680..795); chữ tiếng Việt dài 152 px nên
hai đầu rơi vào vùng alpha ~180. Đã dựng thử ghép lên đúng màu nền trời của cảnh
(lấy mẫu từ ảnh chụp máy thật, `RGB 203,176,195`): chênh lệch gần như không thấy,
và bản thân viên thuốc vốn đã mờ dần ra mép nên đọc ra vẫn liền mạch. Không nâng
alpha — nâng thì phải nâng trọn cột, tức là đổi hình dáng viên.

Đã chạy 27/08/2026, backup `_backup\anim02.selectlane` (= bản gốc 1.0.2, trước đó
romfs chưa có `anim/anim02`). Diff đọc lại từ đĩa: **đúng 4/51 Texture2D đổi**,
47 texture còn lại **trùng từng pixel**; 51 Sprite trùng từng byte (`m_PathID`,
`textureRect`, `m_VertexData`) nên không dính bẫy tight-mesh; số object từng loại
y hệt bản gốc. Ngoài ba khung chữ chỉ 39–138 pixel lệch, tối đa 24/255 một kênh
(nhiễu mã hoá lại ASTC 4x4 tràn khối). File 21,9 MB → 22,3 MB.

> Cũng như `fix_endcard_title.py`, script **luôn dựng lại từ `UNLOGICAL_v2`**,
> không đọc `romfs` — chạy lần hai trên tranh đã vá thì mask nét sẽ bắt đúng chữ
> tiếng Việt vừa vẽ.

Ban đầu việc này có script riêng `fix_anim_select_lane.py`; nay đã gộp thành bốn
spec `tools/_anim_specs/anim02_19..22.json` của `fix_anim_text.py` (xem mục dưới).
**Bắt buộc phải gộp**, không phải cho gọn: hai script đều dựng `anim02` lại từ bản
gốc rồi ghi đè, nên cái nào chạy sau sẽ xoá sạch kết quả của cái chạy trước. Một
bundle chỉ được có đúng một đường ghi. Bản gộp cho ra **đúng từng pixel** kết quả
cũ sau khi sửa một lỗi cắt số: `x` tâm viên là `367.5`, `int()` cắt thành `367`
làm cả dòng lệch 1 px — `op_text` nay giữ số thực rồi mới làm tròn.

### Sửa tay một tranh (`--export` / thư mục `_parked/anim_edit`)

Có những chỗ công cụ không dựng nổi bằng op: quầng sáng mềm quanh nét, chữ uốn
theo phối cảnh, chữ xoay 90°, hiệu ứng nhiễu. Khi đó xuất PNG ra sửa bằng tay:

```
python tools\fix_anim_text.py --export anim04_123 anim02_2
```

- `_parked\anim_edit\<bundle>_<texture>.png` — **file để sửa**, khởi tạo bằng bản
  đã vá hiện tại (hoặc bản gốc nếu texture chưa có spec).
- `_parked\anim_edit\goc\<bundle>_<texture>.png` — bản gốc chưa đụng, chỉ để đối
  chiếu; `--apply` không bao giờ đọc thư mục con này.

Sửa xong, `--apply` sẽ dùng ảnh đó **nguyên xi và ĐÈ LÊN spec** của texture ấy —
không op nào chạy nữa. Muốn quay lại dùng spec thì xoá file png đi.

Vì đây là cái bẫy dễ quên (sửa spec mà không thấy đổi gì), cả `--check` lẫn
`--apply` đều in cảnh báo liệt kê từng texture đang bị đè, và `build_review.py`
cũng đọc ảnh sửa tay thay cho spec để trang review hiện đúng cái sẽ vào game.

`load_edit` chặn trước khi ghi: kích thước phải **khớp đúng** texture gốc, và nếu
texture gốc có vùng trong suốt mà ảnh sửa tay lại đục hoàn toàn thì cảnh báo — dấu
hiệu điển hình của việc làm phẳng kênh alpha lúc lưu. `anim02_2` và `anim04_123`
đều là 1920x1080 **đục hoàn toàn** (alpha 255 mọi pixel) nên sửa như ảnh phẳng
được, không phải giữ alpha.

Lưu ý: PNG xuất ra là kết quả *chính xác* của spec, còn ảnh đọc ngược từ bundle sẽ
lệch tới ~18/255 một kênh vì texture nén ASTC — đừng lấy ảnh trích từ bundle làm
mốc so sánh.
