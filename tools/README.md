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

> **Tool đã xoá (02/09/2026).** Lời thoại không còn ruby trên sheet, nên
> `wrap_ruby_lines.py` hết việc và bị gỡ khỏi `tools/`; bản cuối ở commit `508f596`
> (`git show 508f596:tools/wrap_ruby_lines.py`). Phần dưới giữ lại làm hồ sơ.

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

> **Tool đã xoá (02/09/2026)** cùng lý do với `wrap_ruby_lines.py`; bản cuối ở commit
> `508f596` (`git show 508f596:tools/fix_ruby_syntax.py`).

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

### Thụt treo `　` làm phép so ba chiều báo oan — vòng `(90)`, 03/09/2026

Sheet chỉ đổi một chữ ở `89/txt/0006` (`những Player` → `các Player`) mà tool báo
**CẢ HAI BÊN ĐỔI — bỏ qua**. Phía build được làm phẳng bằng `cur.replace("\n", " ")`, nên
dòng nối tiếp của khối luật novel — mở đầu bằng thụt treo `　 ` do `fix_novel_list_wrap.py`
đặt — để lại `sẽ 　 cùng` giữa câu, khác bản nền `sẽ cùng`, và build bị coi là "đã đổi". Lỗi
này nằm sẵn từ trước, chỉ chưa nổ vì các vòng 88/89 không sửa ô nào trong 29 khối luật; từ
nay bất kỳ ô nào có `　` giữa câu (khối luật, `rule_body`) đều dính. Sửa: phép so "build đã
đổi" và "đã có bản mới" đi qua `flat_cell()` (gộp mọi khoảng trắng kể cả U+3000) trên cả ba
phía; `nv`/`bv`/`flat_cur` bên dưới giữ nguyên cho `carry_breaks` và các chốt khác.
`--take-sheet` vẫn có cho ca hai bên đổi thật. Vòng (90) áp 1 ô, backup
`_backup\scenario01.UNLOGICAL_v2(90)`; `carry_breaks` mang được chỗ ngắt nhưng rơi tiền tố
`　 ` — đúng dự kiến, `fix_novel_list_wrap.py --apply` ngay sau dựng lại cả tiền tố lẫn chỗ
ngắt (ô này thành `…Munakata Kai` / `　 sẽ cùng nhau loại bỏ các Player tại sân khấu ẩn.`).

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

### Vòng (89), tối 02/09/2026 — và cái giá của việc sửa chính tả ở build

Snapshot `(89)` so với `(88)`, backup `_backup\scenario01.UNLOGICAL_v2(89)`; bundle `json`
vòng này không đổi. **4 ô đổi, áp hết**, đều là văn xuôi `ScenarioData` và không ô nào
vướng chốt: `72/txt/0926` (viết lại câu Kai tước dao), `72/txt/0927` (`cậu ấy` → `anh ấy`),
`85/txt/0293` (`thái độ kẻ cả` → `thái độ trịnh thượng`), `86/txt/0664` (đảo sang bị động).
Chỉ `86/txt/0664` có ngắt dòng cứng và `carry_breaks` đặt lại đúng chỗ trên câu chữ mới.
Sau merge: `fix_chat_use_genebark --apply` no-op (231/231 cặp đã giống), `fix_adv_wrap` /
`novel_list` / `dictionary_wrap` / `ellipsis_break` không có gì để sửa, toàn bộ `--check`
cùng `check_scripts` và `check_layout_breaks` (`+0` ngắt dòng, `+0` thụt lề) PASS.

**`trịnh thượng` không phải từ tiếng Việt** — sheet viết sai, dạng đúng là `trịch thượng`,
và chính build đã dùng dạng đúng sẵn ở `84/txt/0492`. Nên đây là thống nhất về dạng đã có,
không phải tự chế cách viết mới. Sai **2 chỗ chứ không phải 1**: ô `85/txt/0293` vừa merge
vòng này, và ô `93/txt/0321` (`「...Nói cái giọng trịch thượng gì thế?」`) đã sai từ trước —
quét cả file trước khi sửa mới lòi ra chỗ thứ hai. Thay trên **chuỗi thô** của asset nên
`text[]` và bản sao `scriptText` cùng đổi một lượt (4 chỗ = 2 + 2); `scriptText_Line` có 0
chỗ khớp, vẫn assert nguyên vẹn sau khi ghi. Backup `_backup\scenario01.trichthuong`.

**Cái giá phải trả ngay:** sửa ở build xong thì chạy lại merge `(89)` so `(88)`, ô đó lập
tức thành "cả hai bên đổi" — build đã đúng còn snapshot vẫn `trịnh thượng`:

```
!! 85/txt/0293                        CẢ HAI BÊN ĐỔI — bỏ qua
      build : 'Dù thái độ trịch thượng của cậu ta làm tôi hơi ngứa mắt, nhưng Shinju…'
      sheet : 'Dù thái độ trịnh thượng của cậu ta làm tôi hơi ngứa mắt, nhưng Shinju…'
```

Chốt chạy **đúng** — chặn chứ không âm thầm lật lại. **Sheet đã sửa ngay tối đó**, nên ô
này tự lành từ snapshot `(90)` mà không kêu tiếng nào: `new != base` đưa nó vào diện xét,
rồi `new == build` cho ra `= 85/txt/0293  đã có bản mới`. Chỉ ồn đúng một vòng, và chỉ khi
chạy lại chính cặp `(89)`/`(88)`.

Bài học vẫn giữ: **sửa câu chữ thẳng ở build là vay một cảnh báo, và chỉ sheet mới trả
được**. Sửa upstream rồi merge xuống thì không vay gì. Sửa ở build là để có bản chơi được
ngay — và khi sửa thì đẩy luôn lên sheet, đừng để ô đó tự tiêu; ca này đẩy kịp nên hết
sau một vòng, còn 48 ô `sd_106`/`sd_107` ở trên thì không, và chúng kêu tới tận bây giờ.

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

#### Đã mở đường ghi cho `cmd` — và cách pin được chỉ số (28/08/2026)

`{sID}/cmd/{n}` = lệnh thứ `n` trong `scriptText` của scenario đó, trong ba lệnh
`terinfo` / `geninfo` / `select_monitor`. Chỗ hóc là **đếm từ đâu**: đếm thô thì chỉ khớp
109/116, lệch một vị trí và chỉ ở `sID 71`.

> **Chốt: bên xuất sheet CHỈ ăn dạng có ngoặc kép `text="…"`.** Bản gốc có đúng một lệnh
> viết **không ngoặc** — `71` @12609, `[terinfo text=敗北者が確定しました\n小住祥太…]` — và
> sheet không có hàng cho nó. Đếm cả nó vào thì lệch chỉ số từ đó trở đi. Chỉ đếm dạng có
> ngoặc: **116/116**, và tổng số lệnh có ngoặc trong bản gốc cũng đúng bằng 116 hàng `cmd`
> của sheet.

> Dấu vết dẫn tới chốt này: hai lệnh ở `71` @8716 và @12609 mang **cùng một chuỗi**, một
> cái có ngoặc một cái không. Ba giả thuyết sai trước đó — "gộp trùng liền kề" (hỏng `68`,
> nó có `New\u3000Chat` hai lần thật), "gộp trùng theo nội dung" (cũng hỏng `68`), và
> "liệt kê từ script chương" (không khớp: một target là **một khối nhãn**, không phải cả
> file).

**Ghi vào CẢ HAI nơi.** Lệnh chạy từ script chương (game dùng `loadLine` trỏ vào đó),
`scriptText` chỉ là bản sao. Nhánh ghi sửa `scriptText` theo chỉ số, rồi thay **mọi** chỗ
có cùng chuỗi nguồn trong 143 script chương — chuỗi nguồn giống nhau thì bản dịch phải
giống nhau. Bỏ sót một bên là vòng sau lại thấy lệch, đúng bài học của `fix_stage_term.py`.

Vòng `(56)→(57)` là vòng đầu có `cmd`: 9 ô đổi, 2 ô build đã đúng sẵn, **7 ô rơi vào
`CẢ HAI BÊN ĐỔI`** — upstream đang viết lại nhóm "người thua cuộc" (`Đã xác nhận` →
`Đã xác định`, khớp build) nhưng đồng thời **gộp danh sách tên bằng `: ` + `, `** trong khi
build giữ `\n` + `　` như bản Nhật. Đó là tranh chấp **bố cục**, mà luật của dự án là build
sở hữu bố cục — nên đừng ép qua bằng `--take-sheet` trước khi **đo bề rộng khung terinfo**.
Chưa ai đo widget đó.

Sau khi mở nốt: **ô đọc được 40 262, hàng câm còn 1194** — đúng bằng `spk`, dạng duy nhất
cố ý đóng.

#### Đã mở đường ghi cho `sel` và `qa_title` (28/08/2026)

```
SEL_ID  {sID}/sel/{idx}/{opt}      -> ScenarioData.selText[idx], parse JSON rồi target[opt]
QA_ID   Q&AData/qa_title/gN_qN     -> Q&AData.list[g].title[q]
```

Bản đồ chứng minh trước khi viết code, bằng cách đối chiếu **cột bản Nhật** của sheet với
đúng vị trí trong bản gốc 1.0.2: `sel` **449/449**, `qa_title` **50/50**.

> **`selText` là JSON LỒNG trong JSON.** Ô chứa nguyên chuỗi `{"target":[…]}`, nên phải
> parse rồi ghi lại cả chuỗi, không thay chuỗi thô được. Và phải vá theo **cả ô**
> `selText[idx]`, không theo từng lựa chọn — hai lựa chọn trong cùng một cụm có thể trùng
> chữ nhau, thay theo chuỗi sẽ đụng cả hai. Cùng lớp lỗi với `text[]` của `70/txt/1216`.

> **Khối ghi `selText` phải nằm TRƯỚC đoạn ghi `scenario01`.** Đặt sau thì `out_s` sửa
> xong không ai ghi xuống — đã dính đúng lỗi này khi cài, phát hiện vì `sel` không bao
> giờ xuất hiện trong phần đọc lại. Điều kiện ghi cũng phải là `changed_s or sel_edits`.

Kết quả sau khi mở cả ba dạng:

```
ô đọc được   38 453  ->  40 146
hàng câm      3 003  ->   1 310   (còn spk 1194 cố ý đóng, và cmd 116 đang kẹt)
```

Vòng `(54)→(56)` là vòng đầu chạy thật với đường mới: 42 ô `ScenarioData`, **1 lựa chọn**
(`72/sel/0460/0001` — `Tôn trọng ý chí của Player` → `…quyết định của Player`), 9 ô chat
Genebark, 0 tiêu đề Q&A. Snapshot `(57)` giống hệt `(56)` (cùng 41 611 id / 42 719 hàng /
143 tab, 0 ô đổi) — chênh dung lượng chỉ là nhiễu khi xuất.

#### Đã mở đường ghi cho `GenebarkChatMainData/chat` (28/08/2026)

`GB_ID` nhận id dạng `GenebarkChatMainData/chat/g{gid}c{cid}_{N}`, `{N}` là **chỉ số
tuyệt đối** trong `data[]` (`gid` có thể nhiều nhóm nối bằng `;`). Đọc được: **38 453 →
39 647 ô**; hàng câm **3003 → 1809**.

> **`spk` KHÔNG mở, cố ý.** Nó là khoá (`player` / `藍`), sheet để VN == JP — dịch là
> hỏng chat. Nhánh ghi còn chốt lại lần nữa: so mảng `speaker` trước/sau, lệch một ly là
> dừng.

Nhánh ghi **gán theo chỉ số rồi dump lại cả asset**, không thay theo chuỗi như nhánh
`*Data` — nội dung chat có câu trùng nhau (`OK`, `Ừ`…) nên `count(cũ) != 1` sẽ nổ oan.
Bù lại bằng chốt mạnh hơn: so bản **đã parse** trước/sau, chỉ đúng những chỉ số đã định
mới được khác, và số mục `data[]` không đổi.

Đã thử khứ hồi có kiểm soát: đặt `data[28]` lùi về bản `(52)`, chạy merge `(52)→(53)`,
ghi ra đúng bản `(53)`, đối chiếu lại **0 mục khác** so với trạng thái trước khi thử và
`speaker` nguyên vẹn (backup `_backup\json.gbwritetest`).

> **Hệ quả phải nói rõ: 184 ô `sd_*` có cặp 1:1 trở thành ô CHẾT.** Sửa ở đó cũng bị
> `fix_chat_use_genebark` ghi đè. Nơi duy nhất để sửa chat của 184 câu ấy là tab
> Genebark. 105 ô chat còn lại (không có cặp) thì vẫn do `sd_*` quyết.
>
> **Đã dạy `apply_sheet_cells` bỏ qua 184 ô đó (30/08/2026).** Nó tự tính lại bảng cặp
> mỗi lần chạy bằng chính `fix_chat_use_genebark.pairs()` — không nhúng danh sách cứng —
> rồi in ra ô Genebark sở hữu:
>
> ```
> 2 ô sd_* là BẢN CHIẾU của chat Genebark — KHÔNG ghi:
>    -  104/txt/0128   ô dẫn xuất — tab Genebark (g52c藍_630) sở hữu, bỏ qua
> ```
>
> Ô nào có bản dịch **khác** ô Genebark tương ứng thì báo mức `!!` "SỬA NHẦM Ô" — đó là
> dấu hiệu người dịch gõ vào ô dẫn xuất, chữ ấy sẽ không bao giờ lên màn hình.
> `--take-sheet` **không** gỡ được chốt này: ô dẫn xuất thì ghi kiểu gì cũng bị
> `fix_chat_use_genebark` lật lại, honour nó là nói dối người dùng. Bảng cặp nạp lười
> nên vòng merge nào không đụng ô `sd_*` thì không tốn thêm giây nào (đo A/B trên
> (62)/(61): 8,54 s so 8,30 s, lẫn trong nhiễu). Vòng CÓ kích hoạt chốt chặn
> ((60)/(59)) tốn thêm 0,25 s; bảng cặp tính hết 0,21 s và chỉ tính một lần.
>
> **Nạp `pairs()` mà không kích hoạt bẫy stdout.** Không `import` thẳng được:
> `fix_chat_use_genebark.py` gán `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, …)`
> ở đầu file **y hệt** `apply_sheet_cells.py`, nên hai wrapper cùng bọc MỘT buffer;
> wrapper nào bị gom rác trước thì `__del__` đóng buffer chung và mọi `print` sau đó
> ném `ValueError: I/O operation on closed file`. Tệ hơn phần nhìn thấy: chữ còn nằm
> trong đệm của wrapper kia **mất hẳn không dấu vết** — triệu chứng thật là một dòng
> biến mất rồi mới tới exception. Dính đúng lỗi này 4 lần khi dựng và khi soi lại.
> Và nó còn gọi `main()` TRẦN ở cuối file (cả hai tool đều không có
> `if __name__ == "__main__"`), mà `main()` đó đọc `APPLY = "--apply" in sys.argv`
> — tức argv của tiến trình NÀY: `apply_sheet_cells.py --apply` sẽ khiến nó ghi thẳng
> vào `romfs` trước khi merge kịp bắt đầu. Đã đo: nạp với argv có `--apply` cho
> `mod.APPLY is True`. Nên `load_tool_module()` đọc mã, **cắt AST cấp cao nhất** đúng
> hai loại lệnh đó (phép gán vào `sys.stdout`, lệnh gọi trần tên `main`) rồi exec
> phần còn lại. Lọc hẹp có chủ ý — cắt mọi `ast.Expr` là `Call` sẽ nuốt luôn
> `sys.path.insert(0, HERE)`. Có lưới an toàn: nếu bộ lọc hụt thì `detach()` wrapper
> mồ côi rồi trả `sys.stdout` về, chứ không để nó gom rác và giết print về sau.
>
> **Số cặp là bất biến, và được chốt (`PAIRS_EXPECTED = 184`).** Cây gốc THIẾU thì
> `load_text` đã dừng ầm ĩ; nhưng cây gốc **CÓ MẶT mà nội dung sai** thì `pairs()` chỉ
> ghép được ít cặp hơn và chốt chặn **tự tắt bớt trong im lặng**. Đo thật: trỏ `STOCK`
> sang cây đã dịch `romfs` cho **93** cặp chứ không phải 0 — 91 ô dẫn xuất lọt lưới,
> merge ghi chúng, rồi `fix_chat_use_genebark --apply` lật lại: bẫy vừa vá mở lại,
> lần này khó thấy hơn vì người dùng tin là đã có chốt. Nay lệch một cặp cũng dừng,
> và số cặp được in ra mỗi lần chạy.
>
> **`--check-chat` — soi đứng yên, vì cảnh báo trong merge chỉ nổ MỘT vòng.** `todo`
> chỉ gồm ô có `new != base`, nên vòng sau — khi snapshot vừa rồi đã thành sheet nền —
> ô vẫn lệch y nguyên nhưng không còn "đã đổi" và không tool nào nhắc lại nữa; bản
> dịch nằm vĩnh viễn trên sheet mà không bao giờ lên màn hình (đúng lớp lỗi memory
> `unlogical-wrong-cell-audit`). `python tools\\apply_sheet_cells.py --check-chat` so cả
> 184 cặp trên snapshot mới nhất bất kể vòng này có gì đổi, `PASS`/`FAIL` + rc=1.
> Trạng thái 30/08 trên (62): **PASS 184/184**.
>
> **Chốt chặn hơi RỘNG, có chủ ý.** Chặn cả 184 cặp, không tái tạo ba tầng lọc của
> `fix_chat_use_genebark.main()` (nameplate có `@`, bản Nhật không mở `「`, `guards`).
> Nếu bản sửa từ sheet **thêm** tag ruby thì `guards` của tool kia nổ ("mất tag") và
> nó sẽ bỏ qua ô đó, tức bản sửa lẽ ra sống sót — tái hiện được với
> `[Kai'カイ]` ở `86/txt/0395`. Vẫn chọn chặn cả 184: điều kiện đó phụ thuộc nội dung
> nên không đoán trước được, hai tool cùng suy luận về một điều kiện động là nguồn lỗi
> mới, và cách sửa mà thông báo chỉ ra (chép sang ô Genebark) vẫn đúng — làm vậy còn
> đồng bộ luôn cả app chat lẫn cảnh ADV. Đo: hôm nay 0/184 ô bị chặn oan vĩnh viễn.
>
> **Nhánh `rule_body` từng bị nuốt chung với chốt này — đã sửa.** `rule_body` không đi
> qua `todo` (nó map theo (id, trang) từ tab riêng) mà lại nằm SAU `if not todo:
> return`, nên một vòng mà mọi ô đổi đều là ô chat dẫn xuất sẽ thoát sớm và bỏ qua hẳn
> bản sửa trang RULE — không ghi, không báo, đến cả dòng "áp được:" lẫn "CHẠY THỬ"
> cũng không in nên không có gì để thấy là thiếu; vòng sau `rn == rb` và khác biệt mất
> vĩnh viễn. **Lỗi này CÓ SẴN từ trước** — đo được: bản `.bak` cũng nuốt trọn một vòng
> chỉ đổi `rule_body` — chốt chặn chỉ làm nó dễ trúng hơn hẳn, vì một vòng chỉ có 1–2
> ô đổi là chuyện thường ở kho này. Nay `rn`/`rb`/`rkeys` tính TRƯỚC phần thoát sớm và
> điều kiện là `if not todo and not rkeys`. Giá: 2,2 s mở thêm hai workbook ở đúng
> nhánh thoát sớm (1,09 + 1,14 s); nhánh thường vốn đã trả khoản này.
>
> **`--new X` cách nhau bằng khoảng trắng nay chạy thật.** `arg()` cũ chỉ nhận tiền tố
> `--ten=`, nên dạng cách nhau bằng khoảng trắng — **đúng dạng docstring đầu file đang
> dạy** — bị bỏ qua không một lời và tool lặng lẽ rơi về `newest_two()`, merge hai
> snapshot mới nhất thay cho cặp vừa chỉ định (với `--apply` là ghi nhầm hẳn một bộ
> ô). Lỗi có sẵn, không do đợt chốt chặn. Giá trị bắt đầu bằng `--` thì không ăn, nên
> `--match --apply` vẫn giữ nguyên cờ `--apply`.

25 hàng lệch build đã xử 28/08/2026 theo chốt của người dùng ("sheet đúng hết"): ghi 24
hàng theo sheet (`carry_breaks` đắp lại ngắt dòng, 0 ngắt nào mất), hàng thứ 25
(`data[641]`) hoá ra **không lệch** — chênh đúng một dấu cách do phép làm phẳng sinh ra.
Kết quả phụ: `-san` sạch hẳn (build 13+4 → 0), nhưng **`-chan` còn 11 chỗ** mà sheet cũng
đang giữ.

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

**Còn tồn (2) — 47 ô chiếu NGOÀI bảng 184, và 42 trong số đó hai màn hình đang hiện chữ
khác nhau ngay lúc này.** Đếm trên bản gốc: **231** ô ADV có bản Nhật trùng một tin nhắn
Genebark, `pairs()` chỉ ghép được 184, còn **47** ô rơi ra vì bản Nhật KHÔNG duy nhất —
ví dụ `106/txt/0156` (`明日、お時間いただけませんか？`) ứng với hai hàng chat `g53c奏壱_635`
và `g54c奏壱_659`, không ghép 1:1 được. Phân loại đầy đủ trên 1194 hàng chat gốc: 184 vào
`pairs()`, 230 trùng trong Genebark, 1 trùng trong ScenarioData, 779 không có trong
ScenarioData.

Không chặn 47 ô này ở `apply_sheet_cells` là **đúng**: ép mọi ô Genebark đổi chữ rồi chạy
`fix_chat_use_genebark --report` cho đúng 184 ô sẽ ghi, "ghi mà không bị chặn" = rỗng —
tool này không bao giờ chạm 47 ô kia. Nhưng lỗ hổng thì có thật và **chưa ai canh**: sửa ô
`GenebarkChatMainData/chat/g53c奏壱_635` trên sheet thì merge ghi xuống bundle json (ô sở
hữu, không cảnh báo gì), rồi `fix_chat_use_genebark --apply` **không** chép sang
`106/txt/0156` vì cặp đã bị `pairs()` loại — app chat hiện câu mới, cảnh ADV giữ câu cũ, và
không tool nào trong danh sách kiểm bắt được. 42 ô đang ở đúng trạng thái đó:

```
72/txt/1432   ADV='Xin được chào lại em, tôi là Yasaka Soichi. Dù'  chat='Chào em, tôi là Yasaka Soichi. Dù là ở đây hay'
72/txt/1444   ADV='Đang ở đâu thế?'                                 chat='Cậu đang ở đâu đấy?'
75/txt/0022   ADV='Cậu đăng xuất được chưa?'                        chat='Thoát game được chưa?'
75/txt/0499   ADV='Anh có chút chuyện muốn thảo luận với em.'        chat='Anh có chút chuyện muốn bàn với em'
```

Đây là **nửa còn lại của cùng bài toán**, không phải lỗi của chốt chặn ô dẫn xuất (chốt đó
phủ đúng phạm vi `fix_chat_use_genebark` đè). Ghép 1:1 không giải được — muốn xử thì phải
ghép theo ngữ cảnh (thứ tự hàng chat trong nhóm, hoặc `groupIDs` ↔ scenarioID) rồi mới
quyết được ô nào sở hữu ô nào.

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

**Tầng hai (02/09/2026): mệnh đề tự nó quá lề thì ngắt theo từ, và ở tầng này thì CÂN độ
dài.** Ba ô không có dấu câu nào nằm đúng chỗ — `85/txt/0767` là một mệnh đề liền 2556 px.
Bỏ mặc không phải là "giữ nguyên": rect rộng 1920 nên TMP vẫn wrap, chỉ là wrap ở **1920**,
tức dòng chạy hết mép màn và đè qua watermark — đúng cái lỗi mục này sinh ra để chặn. Ngắt ở
1764 chỉ đổi *chỗ* ngắt chứ không thêm dòng nào TMP đã không tự thêm. Cân độ dài (ngược tầng
một) vì ở đây không còn dấu câu nào để trùng nhịp bản gốc: gom tham lam đã thử và bỏ — nó để
lại dòng cụt và cắt giữa từ ghép (`99/txt/0214` ra 1707 + 365 px với `địa` / `điểm` nằm hai
dòng). Cân bằng không có bảng từ ghép nào chống lưng, chỉ làm xác suất cắt trúng thấp đi, nên
**ô nào rơi vào tầng hai vẫn nên đọc lại một lượt**.

**Tối 02/09/2026, thử rồi hoàn tác: thu rect `EXTRAText` 1920 → 1764 thay cho ngắt cứng.**
Ý là để TMP tự wrap trong lề an toàn và bỏ ngắt theo từ trong dữ liệu, vì chỗ ngắt ấy để
lại dòng cụt ở ô tóm tắt thẻ SAVE (ảnh IMG_7241). Ảnh máy thật IMG_7243 chụp `85/txt/0767`
sau khi đổi: dòng 1 thụt vào một khoảng, dòng 2 sát lề — **engine thụt 1 em cho dòng CÓ
TRONG DỮ LIỆU và không thụt cho dòng TMP ngắt, ở caption cũng như ở ô novel**, và khối chữ
canh giữa theo cả khối chứ không canh giữa từng dòng. Bản Nhật ở đây cũng viết hai dòng data
(`ゲームの勝敗に影響を及ぼす情報を` / `プレイヤーに開示してはならない。`) nên hai dòng thẳng hàng.
Kết luận: caption quá 1764 px **phải ngắt cứng trong dữ liệu**, mỗi dòng ≤ 1764, để mọi dòng
đều là dòng data; thu rect không thay được. Đã revert nguyên commit `ce015cc` (rect, tool
`fix_caption_box_width.py`, ba ô nối lại). Dòng cụt ở ô tóm tắt thẻ SAVE vì thế vẫn còn, và
cách duy nhất còn lại cho nó là chọn *chỗ* ngắt tầng hai theo cả ô tóm tắt.

**Rồi làm đúng cách đó, cùng tối.** `wrap_words()` giờ duyệt mọi cách chia ra đúng k dòng
hợp lề 1764 và chọn theo thứ tự: ít dòng nhất trong ô tóm tắt thẻ SAVE (mô hình
`adv_layout` với cỡ 27, charSpacing 8,4, 731,5 px — đúng số đo của
`fix_save_summary_clip.py`), rồi không kết dòng bằng lượng từ (`những`/`các`/`một`…), rồi
mới cân độ dài như cũ. `main()` soát lại cả ô tầng hai đang vừa lề: chỗ ngắt khác kết quả
tool thì dựng lại, vì ngắt theo từ không mang nghĩa để phải giữ. Kết quả: `85/txt/0767`
đổi từ 1305 + 1235 thành **1679 + 861 px** — ở ô tóm tắt ra ba dòng trọn, không dòng cụt,
không bị cắt; `99/txt/0214` và `99/txt/0215` giữ nguyên vì ngắt cân sẵn đã là ít dòng nhất.
Tầng một không đụng.

Khung cao 720 px với bước dòng 61,6 px = chỗ cho **11 dòng**, nên ngắt không tốn gì.

Đã chạy 18/08/2026 (backup `_backup\scenario01.centercaption`) — 3 ô trong `PLAN` viết tay:

| ô | trước | sau |
|---|---|---|
| `71/txt/0344` | 1821 px (103%) | 488 px (28%) + 1318 px (75%) |
| `71/txt/0345` | 2592 px (147%) | 1232 px (70%) + 1344 px (76%) |
| `71/txt/0346` | 754 px (43%) | không cần |

**Chạy lại 02/09/2026 sau khi bỏ `PLAN`** (backup `_backup\scenario01.centercaption2`) — quét
ra **41 ô** caption, 8 ô còn quá lề:

| ô | trước | sau | tầng |
|---|---|---|---|
| `71/txt/0060` | 2592 px (147%) | 1232 + 1344 px | dấu câu |
| `71/txt/0090` | 2592 px (147%) | 1232 + 1344 px | dấu câu |
| `71/txt/0116` | 2592 px (147%) | 1232 + 1344 px | dấu câu |
| `85/txt/0767` | 2556 px (145%) | 1305 + 1235 px | từ |
| `86/txt/0664` | 1862 px (106%) | 858 + 988 px | dấu câu |
| `97/txt/0288` | 1869 px (106%) | 1085 + 767 px | dấu câu |
| `99/txt/0214` | 2088 px (118%) | 1059 + 1013 px | từ |
| `99/txt/0215` | 2907 px (165%) | 937 + 978 + 960 px | cả hai |

Ba ô đầu là **cùng một câu với `71/txt/0345`**: cảnh Angelica lặp lại **bốn lần** trong
prologue (script line 642 / 1000 / 1319 / 3224) và vòng 18/08 chỉ vá bản thứ tư — ba bản kia
vẫn phẳng 2592 px suốt từ đó. Đó là cái giá của `PLAN` viết tay và là lý do bỏ nó. `mirror()`
phải sửa theo: ba ô mang chuỗi y hệt nhau nên đòi khớp **đúng một lần** trong `scriptText` sẽ
bỏ cả ba; giờ nó nhận `expect=` số bản sao đang cùng sửa.

Sát ngưỡng, chưa vượt nên để nguyên: `103/txt/0414` **96%** (đúng câu đó, bản route 3),
`92/txt/0027` 92%.

Tool **tự dò lại chỗ ngắt từ câu chữ hiện tại** nên chạy lại được sau mỗi merge (sheet làm
phẳng `\n` mỗi vòng) và không ghi chuỗi đích ở đâu cả.

**Hạn chế cũ đã gỡ.** Câu hỏi "engine reset `textmode` ở lệnh nào" có đáp án:
**`[ノベルモード…終了…]`**, đúng họ lệnh `fix_novel_list_wrap.py` đang dùng — `sID 92` line
168..178 mở bằng `[textmode=5]` và đóng bằng `[ノベルモード1終了]`, không có `[textmode=0]`
nào. Lấy nó làm điểm kết khối thì **cả 26 khối `[textmode=5]` đều đóng gọn trong 6–28 dòng
script**; hai khối từng dài 1905 và 3774 dòng (`sID 71` line 1319, `sID 92` line 168) biến
mất, kể cả ca "cách 2593 dòng" từng ghi ở đây. Khối = từ `[textmode=5]` tới `[textmode=N]`
hoặc `[ノベルモード…終了…]` kế tiếp; ô nào có `loadLine` rơi vào khoảng đó là caption. Chỉ nhận
dòng lệnh thật (`strip()` mở đầu bằng `[`) — script có cả `;//[ノベルモード…]` là comment.

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

## Soi ô sheet mất dấu câu cuối (`check_sheet_end_punct.py`)

`python tools\check_sheet_end_punct.py [--sheet=…] [--csv=…] [--chat]` — chỉ ĐỌC,
không ghi. Bắt lớp lỗi của `90/txt/0433`: bản Nhật `「えっ」`, bản Việt `「Hả」` —
câu kết thúc mà không có `.` / `?` / `!`.

**Không so với bản Nhật, vì bản Nhật không phải tín hiệu.** Tiếng Nhật bỏ `。` trước
`」` là quy ước của nó. Quy ước của bản dịch thì ngược lại, và đo được trên snapshot
(53):

| bản Nhật kết | bản Việt kết | số ô |
|---|---|---|
| `。！？` | có dấu | 22 740 |
| `。！？` | **trần** | 3 |
| trần | có dấu | 13 796 |
| trần | **trần** | 1 336 |

Tức trong 15 132 ô mà bản Nhật kết trần, **91,2% bản Việt vẫn thêm dấu**. Nên câu hỏi
duy nhất là: chữ cuối ô tiếng Việt, sau khi gỡ tag và gỡ ngoặc đóng, có phải dấu kết
câu không. Gỡ ngoặc đóng là bắt buộc — dấu câu nằm TRONG `」`, xét thẳng ký tự cuối
thì mọi ô thoại đều "có dấu".

**Chỉ soi `sd_*` hàng `N/txt/NNNN`.** Mọi field nhãn/tiêu đề kết trần 100% theo thiết
kế — `dic_title` 80/80, `ss_title` 20/20, `rule_title` 21/21, `prof_name` 14/14,
`skill_name` 10/10, `qa_title` 45/50, `alert` 84/86, `rule_body` 14/39 (mục tiêu vòng
chơi, dạng gạch đầu dòng) — đưa vào là chôn 1 339 ô thật dưới ~2 500 ô nhiễu. Hàng
`/cmd/` và `/sel/` cũng là nhãn UI (`New　Chat`, `Xác thực thành công`): 418 hàng,
cùng lý do. Ngược lại các field THÂN bài sạch tuyệt đối — `dic_body` 0/80,
`news_body` 0/61, `skill_desc` 0/10 — nên tiêu chí này không phải là suy đoán.

Kết quả in ra chia bốn dạng, vì bốn dạng cần bốn cách xử:

- **`thoại` 1 027 + `độc thoại` 139** — lỗi thật, sửa được hàng loạt.
- **`SNS` 117** — người nói có `@handle`, tin nhắn trong kịch bản. Cùng nhóm với
  `GenebarkChatMainData/chat` (489/1 194 ô kết trần, 41%): bỏ dấu chấm trong chat là
  văn phong, người đọc quyết. `--chat` gộp thêm nhóm chat vào CSV.
- **`dẫn truyện` 56** — phần lớn là **nhãn chứ không phải câu**: tiêu đề tin tức, tên
  người trên tài liệu, `▽ Ngày thứ N`, `☆☆ Phần thưởng phá đảo ☆☆`. Xem bằng mắt.

Phân bố theo chương cho thấy đây là **vệt theo đợt dịch, không phải rải đều**: đa số
chương ở 0–2%, nhưng chín chương vọt lên — `sd_110` 40,8%, `sd_101` 40,6%, `sd_136`
31,0%, `sd_105` 21,3%, `sd_102` 19,9%, `sd_095` 17,4%, `sd_103` 16,8%, `sd_119`
15,4%, `sd_125` 13,9% — gom 978/1 339 ô.

Bằng chứng cứng nhất là 36 ô có **cùng một câu tiếng Việt xuất hiện chỗ khác CÓ dấu**:
`95/txt/0603` `「...Vâng」` với `70/txt/0796` `「...Vâng.」`; `101/txt/0275`
`「...Này, Ran」` với `98/txt/0074` `「...Này, Ran.」`; `119/txt/0004` `「Kanna, bên
này」` với `72/txt/1117` `「Kanna, bên này.」`.

Build và sheet lệch nhau đúng **một** ô, nên đây không phải mất mát khi merge mà là
bản dịch vốn thiếu: `69/txt/0048` build `「!? ... Cái,」` còn sheet `「!? ...Cái」`.

> Cạm bẫy khi đọc danh sách: `TAG` gỡ cả `[主人公]`, nên `119/txt/0005`
> `「[主人公], bên này」` hiện ra thành `「, bên này」` và trông như ô hỏng. Nó lành —
> xem cột bản gốc trước khi kết luận.

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




### Gỡ tầng ngắt-ở-khoảng-trắng — ngắt cứng chỉ còn ở dấu câu (30/08/2026)

Chốt của người dùng: *"ngắt cứng chỉ còn ở dấu câu, phần thừa để engine"*.

Tầng ba `split_space_balanced()` thêm hôm 28/08 để giữ lề đã bị **gỡ hẳn**. Lý do nó tự
mâu thuẫn: ngắt ở khoảng trắng là ngắt **giữa mệnh đề** — đúng cái lỗi mà cả đợt này sinh
ra để sửa. Giữ lề bằng cách tái phạm chính lỗi ấy thì không đáng.

Kết quả sau khi gỡ (backup `_backup\json.chatwrap-5` 64 ô, `_backup\scenario01.chatwrap-2`
15 ô):

| | trước đợt đầu | sau khi gỡ tầng ba |
|---|---|---|
| chỗ ngắt sau **dấu kết câu** | 52 | **683 (80%)** |
| chỗ ngắt sau **dấu phẩy** | 31 | **166 (20%)** |
| chỗ ngắt **giữa mệnh đề** | **843 (91%)** | **0** |
| tổng chỗ ngắt cứng | 926 | 849 |

**Đánh đổi đã biết và đã chấp nhận:** 79 dòng (64 asset app + 15 ScenarioData) không còn
dấu câu nào để cắt. TMP ngắt chúng ở bề rộng của nó, nên chữ chạy quá lề phải — mô phỏng
ở hai đầu khoảng đã kẹp:

| bề rộng TMP | dòng vẫn quá lề sau khi TMP ngắt | quá bao nhiêu |
|---|---|---|
| 1269 | 70 | 0–64 px |
| 1342 | 79 | 12–136 px |

`--check` nới theo: chỉ FAIL khi dòng quá lề mà **còn cắt được theo dấu câu**; mệnh đề
liền thì liệt kê kèm mức quá lề chứ không tính là lỗi.

> **Đường sửa triệt để là thu ô chữ, không phải ngắt cứng thêm.** Muốn engine ngắt đúng
> lề thì hạ `Message_TMP` sizeDelta.x xuống 1205 — cùng cách session kia đã làm cho
> BACKLOG (`BackMessage_TMP` 1210 → 872). **Chưa thử**, vì đo ra bề rộng wrap thực tế là
> [1269, 1342) trong khi prefab ghi 1210, tức con số prefab đang bị ghi đè lúc chạy;
> ứng viên là script `ChatItemUI` gắn trên `GenebarkChatContentItem` (soát rồi: hàng chat
> **không** có `ContentSizeFitter` hay `LayoutGroup` nào). Kiểm bằng cách đổi số, tắt game
> mở lại — LayeredFS chỉ đọc `ui_jp` lúc boot — rồi chạy `e2e\checks\measure_chat.py`.


### CHỐT (30/08/2026): thu `m_margin`, không thu `sizeDelta` — và hai số đo cũ bị bác

Yêu cầu cuối: *"vạch phải giống bản Nhật gốc, không chấp nhận bất kì thay đổi vị trí và
độ dài vạch, chỉ tác động phần text box thôi"*. Đã xác nhận trên máy thật.

**`UnderLine` là CON của `Message_TMP`.** Thu `sizeDelta` là vạch dịch — đo được:

| sizeDelta.x | vạch ngăn (px ảnh) | dài |
|---|---|---|
| 1210 | 318..1600 | 1283 |
| 900 | 268..1445 | 1178 |

Hai mép dịch **không bằng nhau** (+50 / +155) và độ dài đổi 105 px, dù `UnderLine` khai
cứng 1388 — `ChatItemUI` bố trí lại cả hàng. Nên đường `sizeDelta` bị loại hẳn.

**Đường đúng là `m_margin`** — nó thu vùng vẽ chữ *bên trong* rect, RectTransform không
đổi nên vạch đứng yên tuyệt đối. Kiểm sau khi ghi, giống stock từng số:

```
Message_TMP  size (1210, 80)  pos (177, -61)      = stock
UnderLine    size (1388, 4)   pos (-88, -19)      = stock
m_margin     (0, 0, PHẢI 45, 0)                   <- chỉ đây đổi
```

`python tools\set_chat_box_width.py --margin=45 --apply` (`--restore` về stock).

**Số 45 lấy từ ảnh stock `_2026-08-30_14-35-09.png`:** vạch kết thúc x=1600, chữ chạm
x=1623 ⇒ **lố 23 px**. Vùng chữ 1210 canvas vẽ ra 1178 px ⇒ tỉ lệ **0,9736**. Cộng khoảng
hở ⇒ margin 45 ⇒ vùng chữ 1165 canvas ⇒ chữ dừng ở 1579, **trong vạch 21 px**.

> **Dùng tỉ lệ của chính thứ đang chỉnh.** Ba mốc cho ba tỉ lệ khác nhau — vạch ngăn
> 0,9244 (1283/1388), mép chữ 0,9736 (1178/1210), icon ảnh thật ~0,91 (62/68). Chúng đá
> nhau vì `ChatItemUI` vẽ vạch và icon không theo kích thước khai báo. Chỉ tỉ lệ đo từ
> **vùng chữ** mới dùng được cho việc chỉnh vùng chữ.

#### Hai kết luận cũ của tôi bị bác

- ~~"bề rộng wrap thực tế của TMP không phải 1210, mà [1269, 1342)"~~ — **sai**. TMP ngắt
  đúng ở bề rộng vùng chữ; **model trong `fix_chat_wrap.py` đo cao hơn TMP ~5%**. Kẹp từ
  cặp A/B: `W_model/box ∈ [1,049; 1,109)`. Chứng cứ dứt điểm: mực chữ trải 1178 px ảnh cho
  vùng 1210 canvas — đúng bằng khung, không tràn.
- ~~"`ChatItemUI` ghi đè bề rộng nên thu prefab vô nghĩa"~~ — **sai**. Probe ô 900 làm ngắt
  dòng dịch vào rõ rệt, tức prefab **có** được tôn trọng. `ChatItemUI` có đụng bố cục
  *hàng* (vạch, icon), nhưng không ghi đè bề rộng vùng chữ.

#### `LIMIT` phải đi theo margin

`LIMIT = (1210 − margin) × 1,049` — nhân hệ số thấp nhất của khoảng đã kẹp cho chắc. Với
margin 45: `1165 × 1,049 ≈ 1222`, đặt **1220**. Cao hơn thì ngắt cứng dài hơn khung và TMP
ngắt lại giữa mệnh đề; thấp hơn thì ngắt cứng chặt hơn cần thiết.

Kết quả cuối: **873 chỗ ngắt cứng, 0 chỗ giữa mệnh đề**; 73 dòng mệnh đề-liền để engine
ngắt. Backup `_backup\ui_jp.chatboxwidth-5`, `json.chatwrap-7`, `scenario01.chatwrap-4`.

### Hai MÀN HÌNH, hai asset — và cái tôi sửa đầu tiên là cái ít người thấy hơn

Phát hiện 30/08/2026 từ hai ảnh chụp cách nhau 4 phút.

| màn hình | asset | ảnh |
|---|---|---|
| **app CHAT** mở từ menu Genebark | `GenebarkChatMainData.data[].content` | `_2026-08-30_01-40-43.png` — ngắt **đúng** |
| **cảnh ADV** vẽ giao diện chat trong lúc kể chuyện | `ScenarioData.text[]`, ô có `talkName` chứa `@` | `_2026-08-30_01-36-35.png` — **phẳng** |

Bản đầu của `fix_chat_wrap.py` chỉ ghi asset thứ nhất, nên người chơi đọc truyện vẫn thấy
dòng chạy dài rồi TMP tự ngắt giữa câu.

**Cách chứng minh màn ADV đọc `ScenarioData`:** ba dòng đầu ảnh 01:36 —
`May quá. Tầm mấy giờ thì bàn được nhỉ?`, `Hửm. Để tôi học xong…`, `Ok. Cố lên nha` —
**không có trong `GenebarkChatMainData`**, mà nằm liên tiếp ở `68/txt/0123–0129`, đúng
thứ tự trên màn hình.

**Và chúng vẽ ở widget CHAT chứ không phải ô thoại ADV.** Đo 6 dòng biết trước chữ trên
chính ảnh đó, quy về canvas:

| model | tỉ lệ model/đo |
|---|---|
| chat — `FOT-DNPShueiMGoStd-B`, cỡ 32, spacing 5 | **1,002** |
| ô thoại ADV — `FOT-NewRodinProN-DB`, cỡ 42 | 1,595 |

> **Đã vá `fix_adv_wrap.py` (30/08/2026):** `adv_messages()` trước đó gom cả 289 ô chat
> này và đo bằng font + cỡ của ô thoại ADV — **rộng gấp ~1,6 lần thực tế**. `--check` vẫn
> PASS, nhưng chỉ vì các dòng ấy tình cờ đủ ngắn; một ô chạm cap là `--apply` ngắt lại
> bằng số đo sai. Nay `adv_messages()` bỏ qua ô có `talkName` chứa `@`:
> **37.951 → 37.662 tin nhắn**, đúng 289 ô. Soát cả 8 dạng nameplate có `@`
> (`【Suzuno@Sz_36iii】` 97, `【Unknown@73w35vq】` 46, `【RAN@ran_n_rea4】` 41,
> `【Kai Munakata@k_munakata2150】` 37, `【yasaka@eggsand_yaa】` 37, `【YURI@yyy58302199】` 14,
> `【M@6avbjie_w】` 9, `【Shiori@S_hi0ri_kxoxo】` 8) — **tất cả đều là tên tài khoản**, không
> ô nào bị loại oan. `fix_jp_sentence_break.py` đã có sẵn đúng chốt này từ 27/08.

Kết quả (backup `_backup\scenario01.chatwrap`): **139/289 ô đổi**, 150 ô vốn đã đúng,
`scriptText` mirror 111 / bỏ 28. Cùng đợt chạy lại asset app: 2 ô đổi
(`_backup\json.chatwrap-4`) — sheet merge vòng (62) ngày 29/08 làm phẳng lại chúng, đúng
lý do tool tự dò lại từ câu chữ hiện tại thay vì ghim chỉ số ô.

Kiểm sau khi ghi: `check_scripts` 143/143, `check_chapterdata` 8/8, `fix_adv_wrap --check`
0 dòng chạm hoạ tiết, và cả hai asset `--check` **0 dòng quá lề**.

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

## Ngắt cứng giữa cụm từ (`fix_midphrase_break.py`)

Cùng một chuỗi `ScenarioData.text[]` được **ba widget bề rộng khác nhau** vẽ — ô
thoại ADV 1280, BACKLOG 1210, preview thẻ SAVE còn hẹp hơn — nên một chỗ ngắt canh
cho ADV là sai ở hai chỗ kia, không cách nào canh vừa cả ba. Widget nào cũng bật
word-wrap. Ngắt cứng chỉ thật sự mua được bốn thứ, và **cả bốn đều đã có chủ**:

| lý do | quy mô | ai lo |
|---|---|---|
| ruby: `Ruby_Text` đặt chú thích theo mảng `\\n` của chính câu | 0 ô từ vòng (88) | tool này bỏ qua nếu có — xem dưới |
| novel: engine thụt 1 em cho dòng DATA, không thụt cho dòng TMP ngắt | 1.623 ô | `fix_novel_list_wrap.py` |
| hoạ tiết góc ô ADV | vài ô | `fix_adv_wrap.py` |
| caption giữa màn quá lề watermark | 41 ô | `fix_center_caption_wrap.py` |
| ngắt ở ranh giới câu, mirror bản Nhật | 6.875 chỗ | `fix_jp_sentence_break.py`, `fix_ellipsis_break.py` |

Còn lại là ngắt lấp cho vừa bề rộng: không mang nghĩa, và **sinh lỗi** — đoạn trước
dài quá khung thì TMP ngắt lại, mẩu thừa rơi xuống đứng lẻ một hàng ngay trước
`\\n` viết tay kế tiếp.

Ký tự cuối của 7.222 chỗ ngắt cứng trong thoại ADV (đã lọc script test):

```
.  5794 (80,2%)    ?  783 (10,8%)    !  281 (3,9%)    ,  14    ―  3
còn lại chữ cái thường: 347 chỗ (4,8%)   <- đúng nhóm tool này gỡ
```

Quy ước sẵn có đã rõ; tool chỉ dọn 4,8% ngoại lệ — **224 tin nhắn, 347 chỗ ngắt**.

Ba cái bẫy đã dính, ghi lại để đừng dính lại:

- **Đếm dòng cụt sai gấp 16 lần.** Đếm "đuôi của mọi đoạn bị TMP ngắt" gộp cả dòng
  cuối tin nhắn (đương nhiên ngắn) lẫn dòng ngắn do người viết cố ý (`Ơ...` /
  `Cái gì!?` đứng riêng rồi ngắt ở dấu kết câu). Ra 3.369, rồi 161. Số thật là
  **10**: phải cùng lúc là đuôi của đoạn bị TMP cắt **và** không phải dòng cuối tin
  nhắn. Xem `fix_adv_wrap.widows()`.
- **Hai tool cùng ngắt thì phải biết nhường.** `fix_adv_wrap` ngắt giữa cụm từ để né
  hoạ tiết, `fix_center_caption_wrap` ngắt giữa cụm từ (còn cân độ dài) để né
  watermark — cả hai đều **cố ý**. Không miễn thì tool này gỡ ngay ra, và đã gỡ thật:
  `85/txt/0767`, `99/txt/0214`, `99/txt/0215` mất ngắt ngay sau khi tầng hai của
  `fix_center_caption_wrap` vừa đặt vào. `candidates()` bỏ qua ô caption và ô nào nối
  xong sẽ chạm hoạ tiết.
- **Chuỗi trùng.** `text[]` có câu y hệt ở nhiều ô; thay chuỗi mù thì đụng cả ô không
  phải ứng viên. Chỉ thay hàng loạt khi MỌI ô mang chuỗi đó đều là ứng viên.

Không đụng script test của nhà phát triển (`sample1`, `UL_test`,
`UL_Live2d_test_sample`, `01_test_live2d_0*` — sID 0–8, 1.687 ô toàn tiếng Nhật,
không có trong `ChapterData`, không màn nào tới được). Lọc bằng tỉ lệ ký tự CJK:
nối tiếng Nhật bằng dấu cách là hỏng.

**Ruby (02/09/2026).** Ảnh máy thật IMG_7232 — `72/txt/0380`, Hotaru — là đúng lỗi mục
này mô tả (mẩu `không` đứng lẻ một hàng) mà `--check` vẫn PASS, vì ô ấy mang
`[dic no=252 text=tinh chỉnh'tuning]` và tool bỏ qua mọi ô có ruby. Ô đó đã được nối
một lần bằng phép đo `ruby_safe()`: nối được khi mọi dòng data trước dòng ruby vẽ đúng
một hàng và phần đầu dòng tới hết tag ruby nằm trọn hàng vẽ đầu, đo ở cỡ auto-size thật
(32,25 pt, tag kết ở 1115 px, TMP vẽ 1277 / 1216 / 1255 px). Rồi cùng ngày quyết định
**bỏ hẳn ruby khỏi lời thoại**: sheet đã bỏ, hai snapshot (86)/(87) vẫn mang 5 tag
(`72/txt/0380`, `72/txt/0467`, `103/txt/0336`, `116/txt/0867`, `127/txt/0385`), nên
phép đo ấy được gỡ, tool quay về bỏ qua ô có ruby, còn `wrap_ruby_lines.py` và
`fix_ruby_syntax.py` bị xoá. Snapshot mới hơn merge xuống là 4 ô kia thành ô thường và
tool này dọn nốt.

**Vòng (88), tối 02/09/2026** (backup `_backup\scenario01.UNLOGICAL_v2(88)` và
`_backup\json.UNLOGICAL_v2(88)`): sheet bỏ nốt 5 tag — `[dic no=252 text=tinh chỉnh'tuning]`
thành `text=tinh chỉnh (tuning)`, `[Quyền quản trị'Skill]` / `[Điều Đình'Kỹ năng]` thành
`skill Quyền quản trị` / `skill Điều Đình`, `[Người tham gia'Player]` thành `Player`, và
`[×'Error]` thành `dấu "x"`. Ca cuối mất cả hai nửa tag nên phải vào `RUBY_DROP_OK`, lý do
ghi tại chỗ. Cùng vòng: `116/txt/0865` `quét sinh hiệu` → `quét chỉ số sinh tồn` và tiêu đề
từ điển `no=352` `Dấu hiệu sinh tồn` → `Chỉ số sinh tồn` (`sinh hiệu` còn 0 chỗ trong build),
`116/txt/0862` `những Player` → `các Player`. 8 ô áp hết, `check_layout_breaks` PASS ngay
sau merge; tool này nối 3 ô vừa hết ruby (6 chỗ ngắt), `fix_adv_wrap --check` PASS.
**Từ vòng này thoại không còn tag ruby nào.**

`check_layout_breaks.py` sẽ báo **mất** ngắt dòng sau đợt này — đúng dự kiến, giống
trường hợp `fix_ellipsis_break.py` gỡ ngắt theo luật dòng cụt.

```powershell
python tools\fix_midphrase_break.py            # chạy thử
python tools\fix_midphrase_break.py --apply
python tools\fix_midphrase_break.py --check    # chốt sau merge
python tools\fix_adv_wrap.py --apply           # chạy ngay sau, cho ô chạm hoạ tiết
```

Backup: `_backup\scenario01.midphrase`.

## Ngắt cứng giữa cụm từ trong văn xuôi chế độ novel (`fix_novel_prose_break.py`)

`python tools\fix_novel_prose_break.py [--apply] [--check]`

Ảnh máy thật IMG_7238 (02/09/2026), `70/txt/0094` — câu mở đầu khối luật, vẽ bởi
`Message(Novel)`:

```
  ―Hôm qua, những gì Kohaku đã dạy tôi là "Công          dòng DATA   1284 px
  việc tối thiểu" của một Operator (Điều hành viên) và   dòng DATA   1547 px > 1400
"Kiến                                                    TMP ngắt xuống, KHÔNG thụt
  thức cơ bản" về Unlogical.                             dòng DATA
```

Cùng cơ chế đã đo ở mục thụt treo bên dưới: ô novel thụt 1 em cho dòng CÓ TRONG DỮ
LIỆU và không thụt cho dòng TMP tự ngắt. Nên một `\n` đặt giữa cụm từ chỉ vô hại khi
dòng đứng trước nó **vừa khung**; dòng đó tràn thì mẩu thừa rơi xuống đứng lẻ, thụt
ngược, rồi `\n` kế tiếp lại thụt vào — `Kiến thức` bị xé làm hai hàng lệch nhau. Đây là
lớp lỗi `fix_midphrase_break.py` đã dọn ở ADV, nhưng tool đó miễn vùng novel — và ở
novel nó lộ hơn ADV, vì cái thụt.

Khảo sát cả 1.630 tin nhắn vùng novel (`[ノベルモードN開始…]` … `…終了…`, bỏ mục liệt kê):

| | ノベルモード1 (1400) | 2 (1600) | 3 (chưa đo) |
|---|---|---|---|
| một dòng, tràn khung — TMP wrap, dáng đoạn văn thụt đầu dòng | 803 | 50 | 4 |
| nhiều dòng, có dòng tràn | 104 | 1 | 1 |
| … trong đó dòng tràn đứng TRƯỚC một `\n` | 13 | 0 | 0 |
| … và `\n` ấy ngắt giữa cụm từ — **lỗi** | **3** | 0 | 0 |

Mười ca còn lại của hàng thứ ba ngắt ở ranh giới câu: đuôi câu rơi xuống rồi câu sau
thụt vào, đọc như hai đoạn văn — cùng dáng với 803 ô một dòng, để nguyên.

**Sửa: trong ô lỗi, gỡ mọi `\n` giữa cụm từ (nối bằng dấu cách), giữ `\n` ở ranh giới
câu.** Ô ấy đằng nào cũng bị TMP wrap; trộn ngắt kiểu khối Nhật (mỗi vế một dòng thụt)
với wrap của TMP trong cùng một đoạn thì không có cách xếp cho thẳng hàng. Không ngắt
lại cho vừa 1400: ngắt lấp chỗ là thứ vòng (87) vừa bỏ, và merge kế tiếp dài chữ ra là
hỏng lại y như cũ.

| ô | trước | sau |
|---|---|---|
| `70/txt/0094` | 3 dòng, dòng 2 = 1547 px, ngắt sau `"Công` / `"Kiến` | 1 dòng |
| `80/txt/0168` | 2 dòng, dòng 1 = 2163 px, ngắt sau `thôi,` | 1 dòng |
| `80/txt/0183` | 3 dòng, 1471 + 1437 px, ngắt sau `người,` / `yếu` | 1 dòng |

Mirror vào `scriptText` 0/3 — ba ô nằm trong 11% hai bản đã lệch nhau, vô hại vì bản đó
không được vẽ. `check_layout_breaks.py` báo mất `\n` ở đúng ba ô này, đúng dự kiến.
Backup `_backup\scenario01.novelprose`.

Tự dò từ phía Nhật nên chạy lại được sau mỗi merge; `--check` vào chốt sau merge (bảng
ở mục kế). Bỏ qua ô có ruby (ngắt dòng là neo của `Ruby_Text`), ô còn kana (script
test) và mục liệt kê. `ノベルモード3` (6 ô nhiều dòng) chưa biết widget nào vẽ nên chỉ
đếm, không đo.

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

**Tối 02/09/2026: chọn chỗ ngắt theo cả ô tóm tắt thẻ SAVE.** Ảnh máy thật IMG_7244 (màn
SAVE, slot 019): ô tóm tắt 731 px wrap dòng 1 của `89/txt/0006`, `cùng` rơi xuống đứng lẻ
rồi tới chỗ ngắt thụt treo. Đo cả 29 khối trên mô hình của `fix_save_summary_clip.py`: 14
khối tốn thêm dòng ở ô tóm tắt chỉ vì chỗ ngắt gom tham lam. `reflow()` giờ duyệt mọi cách
chia ra cùng số dòng vừa 1344 và chọn theo thứ tự: ít dòng nhất ở ô tóm tắt (tên đo cận
trên `WWWWWW`), rồi ít dòng nhất với tên mặc định, rồi tham lam nhất. Hai chốt mới trên mọi
ứng viên: không dòng nào để ngoặc / ngoặc kép mở dở, và không tách cặp trong `NO_SPLIT` —
bảng từ ghép soát tay từ 445 cặp từ liền nhau của 29 khối (`trò chơi`, `đăng xuất`,
`Game Master`…). Không có bảng đó thì tối ưu theo ô tóm tắt sẵn sàng cắt `trò / chơi`,
`hoàn / toàn`, `bất / kỳ`, `cho / đến`; tham lam cũ cũng đã cắt `đăng / xuất`, `kẻ / thù`,
`Game / Master`. Kết quả: **16 khối đổi**, số dòng mỗi khối giữ nguyên nên
`check_layout_breaks` không thấy gì, tổng dòng của 16 khối ở ô tóm tắt **65 → 49**;
`89/txt/0006` thành `…Munakata Kai sẽ` / `　 cùng nhau loại bỏ…` — hết dòng cụt với tên mặc
định, còn tên 6 ký tự Latin thì dòng 1 vẫn wrap, không cách chia nào tránh được với chữ lúc
đó. Sheet (90) rút `những Player` → `các Player` (dòng hai 1390 → 1323 px, vừa 1344), tool
liền chọn `…Munakata Kai` / `　 sẽ cùng nhau loại bỏ các Player tại sân khấu ẩn.`: ba dòng ở ô
tóm tắt với mọi tên. Backup `_backup\scenario01.novellist` (23:42). Thêm mục luật mới thì
soát lại `NO_SPLIT`.

**Lượt hai cùng đêm (ảnh IMG_7245): cách chia SẠCH hơn cách chia ngắn.** Với cách chia hai
dòng tốt nhất, `89/txt/0006` vẫn bị TMP wrap dòng dữ liệu thứ hai ngay trong ô tóm tắt —
`…tại sân` / `khấu ẩn.`, đuôi sát lề không thụt treo. Gọi một cách chia là *sạch* khi không
dòng dữ liệu nào bị wrap ở đó: mọi hàng của ô tóm tắt đều là dòng dữ liệu, tiền tố `　 ` theo
sang được, không từ nào bị TMP tách. `reflow()` giờ lấy cách chia sạch ở đúng số dòng tham
lam nếu có, không thì cho phép **thêm một dòng** để sạch, miễn còn trong 3 hàng của ô tóm
tắt (`SUMMARY_ROWS`). 03/09/2026 đổi **11 khối**: 5 khối 1 → 2 dòng (`70/txt/0095`,
`121/txt/0108`, `127/txt/0407`, `127/txt/0410`, `127/txt/0413`), 6 khối 2 → 3 dòng
(`70/txt/0096`, `70/txt/0099`, `78/txt/0111`, `89/txt/0006`, `103/txt/0021`,
`121/txt/0105`); `89/txt/0006` thành `…Munakata Kai` / `　 sẽ cùng nhau loại bỏ các Player
tại` / `　 sân khấu ẩn.`. Còn 6 khối dài vẫn wrap trong ô tóm tắt vì cần ≥ 4 hàng, đằng nào
cũng bị cắt `…` ở đó. `check_layout_breaks` chỉ đếm mất, nên +18 ngắt dòng và +18 dòng thụt
đi qua.

### Chốt sau mỗi lần merge sheet

```powershell
python tools\fix_novel_list_wrap.py --apply     # dựng lại ngắt dòng + thụt treo
python tools\fix_novel_list_wrap.py --check     # exit 1 nếu còn khối sai
python tools\fix_novel_prose_break.py --check   # exit 1 nếu văn xuôi novel có dòng tràn trước ngắt giữa cụm từ
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

> **Thay thế 02/09/2026:** auto-size ở đây đã **tắt lại**, tiêu đề dài giờ *chạy chữ* — xem mục
> [Chạy chữ (marquee)](#chạy-chữ-marquee-tên-bài-music-ending-list-tiêu-đề-section) bên dưới. Phần còn lại giữ làm hồ sơ.

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

## Chạy chữ (marquee): tên bài MUSIC, Ending List, tiêu đề section

Ba ô một dòng mà bản dịch dài hơn khung — tên bài ở màn MUSIC (16/21 tràn sau khi đã bỏ
charSpacing), tiêu đề Ending List (đang co auto-size xuống tới cỡ 17), tiêu đề section trong
khung tóm tắt (căn giữa nên bị mask cắt cả hai đầu). Cả ba giờ **chạy chữ** bằng chính code của
game, không vá NSO. Làm 02/09/2026, bốn script dùng chung `tools\marquee_lib.py`.

### `AutoScrollText` — component có sẵn mà studio không dùng

`global-metadata.dat` khai `AutoScrollText` (`Assets/Scripts/Auto/AutoScrollText.cs`, MonoScript
`globalgamemanagers.assets` pid 1187) nhưng **0 instance** trong toàn bộ scene/prefab (quét
5 905 MonoBehaviour của `level*`/`sharedassets*`/`resources` và cả `ui_jp`/`scene_jp`). Code vẫn
được biên dịch. Đọc bằng Il2CppDumper (`dump.cs` sinh từ NSP update) + capstone trên `main.flat`:

```
[RequireComponent(RectMask2D)]
Awake        textRect = targetText.rectTransform; mask = GetComponent<RectMask2D>()  (cùng GameObject)
OnEnable     TMPro_EventManager.TEXT_CHANGED += OnTMPTextChanged; StartScroll()
StartScroll  anchoredPosition.x = 0; CalculateWidths();  chỉ chạy khi preferredWidth > mask.rect.width
ScrollMode   Loop = 0   : trôi sang trái, ra hết thì vòng lại từ x = maskWidth
             Restart = 1: trôi tới x = -(textWidth - maskWidth), dừng pauseDuration, về 0, chờ startDelay
.ctor        startDelay 1.0, speed 50 px/s, pauseDuration 1.0
```

Field serialize: `targetText` (PPtr TMP), `scrollMode`, `startDelay`, `speed`, `pauseDuration`
— 60 byte kể cả header. Mỗi lần `MusicRoom`/`SceneReplayRoom` gán chữ, TMP bắn TEXT_CHANGED
và component tự tính lại, nên gắn xong là chạy. Dùng `Restart` (đọc được đầu tên hầu hết thời
gian); `Loop` để chọn qua `--mode`.

### Thêm một class chưa từng có trong file

File **không nhúng type tree** (`level13`, `sharedassets21`): MonoScript nằm ở external
`globalgamemanagers.assets`, type entry chỉ cần hai hash — `script_id = MD4(className +
namespace + assemblyName)` (đối chiếu khớp 23/23 entry sẵn có của `level13`; OpenSSL 3 đã bỏ
md4 nên `marquee_lib` cài lại thuần Python) và `old_type_hash = MonoScript.m_PropertiesHash`.
Bundle **có type tree** (`ui_jp`): MonoScript nằm ngay trong CAB, phải thêm MonoScript object
(chép từ MonoScript sẵn có, đổi tên/hash) và type entry **kèm node** — ghép từ node sẵn có:
header của `ContentSizeFitter`, `PPtr<$TextMeshProUGUI>` của `EventTriggerButton.textMeshPro`,
`UInt8` của `useTextColor`. `TypeTreeNode` của UnityPy không `deepcopy` được, dựng lại từ
`to_dict()`. Kiểm: đọc component mới bằng chính node vừa dựng phải ra đúng giá trị đã ghi.

**Và phải chèn vào `m_PreloadTable` của AssetBundle.** Mỗi asset trong bundle có một dải preload
nạp *trước* nó; trong dải của `chapterselect.prefab` mọi MonoScript đều đứng trước MonoBehaviour
dùng nó (15/15). Object mới không có trong dải thì MonoScript chưa nạp lúc deserialize → component
thành "missing script". Bản vá đầu (`81f5b528`) thiếu bước này: `LayoutElement`/`AutoScrollText`
chết, `ContentSizeFitter` sống vì MonoScript của nó đã nạp từ prefab khác → rect co bằng chữ, tiêu
đề dạt trái và không chạy (ảnh `_2026-09-02_12-13-21`). Sửa: chèn MonoScript rồi component vào
đầu dải, `preloadSize` +6, dời `preloadIndex` của 58 container phía sau, kiểm các dải vẫn liền
mạch tới cuối bảng. `level13`/`sharedassets21` không có bảng này (`PreloadData` của scene chỉ trỏ
file ngoài, prefab nạp theo PPtr) nên không cần.

Object mới = `copy.copy` một ObjectReader cùng class, đổi `path_id`/`type_id`/`data`, rồi
`env.file.save()`. File co lại vài trăm byte đến 1,3 KB dù thêm object: bản gốc canh mỗi object
ở mốc **16 byte**, UnityPy canh **8** — `level17`/`level22` đã ship cũng canh 8 và chạy bình
thường. Cửa an toàn bắt buộc trong cả bốn script: **nạp lại blob và so byte từng object với
bản gốc**, chỉ các object cố ý sửa được khác, không thì không ghi.

### Ba bài học về hình học, đều do `anchoredPosition.x = 0` bị ép

1. **Mask không được phủ lề trái của TMP.** Ô MUSIC: rect 400 px tại canvas 565..965, TMP
   `m_margin.x = 14` → chữ nghỉ ở 579, cách icon ♫ 14 px. Bản vá đầu để mask trùng rect: chữ
   nghỉ vẫn đúng, nhưng lúc trôi chữ chui vào 14 px lề và dí sát icon (ảnh chụp
   `_2026-09-02_03-27-47`). Sửa: mask = đúng vùng chữ (579..965, 386 px), lề TMP về 0 và gộp
   vào vị trí mask. Ngưỡng `preferredWidth > 386` = ngưỡng tràn cũ, tập tên chạy chữ không đổi.
2. **Căn giữa khi vừa, căn trái khi dài** không làm được bằng alignment: TMP căn giữa trong rect
   cố định thì tên dài tràn đều hai bên, đầu bị mask cắt ngay lúc nghỉ. Giải bằng layout: rect
   con neo + pivot **mép trái** mask, `ContentSizeFitter` (ngang = PreferredSize) +
   `LayoutElement.minWidth = bề rộng mask, priority 1` → rect rộng `max(mask, preferredWidth)`.
   Tên ngắn: rect = mask, chữ căn giữa trong đó. Tên dài: rect = đúng bề rộng chữ, lấp đầy từ
   mép trái — chính là x = 0 mà scroller cần, và `-(textWidth − maskWidth)` đưa đuôi tới đúng
   mép phải. `LayoutUtility` lấy `minWidth` từ LayoutElement (priority 1 > TMP 0) và
   `preferredWidth` từ TMP (LayoutElement để −1). Dùng cho MUSIC và tiêu đề section; Ending List
   căn trái nên không cần.
3. Lề âm cũng vậy: `Mask_Title/Title` có `m_margin.x = −5` (bù charSpacing 6 cho cân giữa); với
   rect neo trái, −5 đẩy chữ ra ngoài mask 5 px và bị cắt → về 0 (tâm lệch 2,5 px, không thấy).

**Chỉ hàng đang chọn mới chạy (Ending List).** `AutoScrollText.OnEnable → StartScroll`, nên đặt nó trên
`TextMask` là mọi hàng đang hiện cùng chạy — bản đầu 02/09 bị đúng thế. `EventTriggerButton.curObject =
{select: [On], deSelect: [Off]}` và `CurObjectSetActive → GameObject.SetActive`, tức `On` chỉ active khi
hàng được chọn. Treo scroller lên GO `TitleScroll` dưới `On` (kèm RectMask2D riêng 502 px vì `mask =
GetComponent<RectMask2D>()` cùng GameObject — nó không có con graphic nên không cắt gì; `targetText` vẫn
là TMP trong `TextMask`): chọn hàng → OnEnable → chờ startDelay rồi trôi; rời hàng → OnDisable dừng
coroutine và trả x về 0. Ô MUSIC và tiêu đề section chỉ có một phần tử nên vẫn để chạy thường trực.

### Từng màn

| màn | file | script | thay đổi |
|---|---|---|---|
| MUSIC `TrackTitle` | `level13` | `fix_music_title_marquee.py` | GO cha `TrackTitleMask` 386×100 tại (−188,−228) [RectMask2D, AutoScrollText]; `TrackTitle` neo trái + CSF + LayoutElement; TMP căn giữa, margin.x 14→0. 375 object nguyên byte, 4 sửa, 6 mới |
| Ending List hàng | `sharedassets21.assets` | `fix_recollection_marquee.py` | GO `TextMask` [RectMask2D] chèn giữa `RecollectionButton` và `Text`: stretch, thụt trái 94, cao hơn hàng 10 px mỗi bên (dấu không bị cắt); `AutoScrollText` đặt trên GO `TitleScroll` dưới `On` (chỉ active khi hàng được chọn) nên **chỉ hàng đang chọn chạy chữ**; `Text` neo trái 502×51; TMP **auto-size tắt**, cỡ 32 cố định, margin.x 94→0. Quét disassembly: `CreateReplayButtons` chỉ `Instantiate` + `GetComponent<EventTriggerButton>()`, chữ đi qua PPtr `textMeshPro → #169`, không `Transform.Find` → chèn GO an toàn |
| Section title | `ui_jp` (`ChapterSelect/Story/SynopsisTitle/Mask_Title/Title (TMP)`) | `fix_section_title_marquee.py` | `Mask_Title` đã có RectMask2D, chỉ gắn AutoScrollText; `Title` neo trái + CSF + LayoutElement 527; margin.x −5→0; +2 MonoScript (`AutoScrollText`, `LayoutElement`), +2 type entry có node, +6 entry preload. Không đổi cây. 7 932 object nguyên byte |

Tham số chung: `restart`, startDelay 1,5 s, 60 px/s, pause 2 s. Mỗi script từ chối file đã vá —
đổi tham số thì chép backup (`_backup\level13.premarquee`, `sharedassets21.assets.premarquee`,
`ui_jp.presectionmarquee`) đè lại rồi chạy lại. Nhãn hàng `ChapterSelectButton/Text` chỉ là
"SECTION n" cố định, không đụng.

### Viết hoa tên bài (`fix_music_title_case.py`)

`MusicData.title` (bundle `json`, **không có tab trên sheet**) đổi sang VIẾT HOA TOÀN BỘ, 21/21,
sửa thẳng trên văn bản JSON như `json_term.py`. Ô này dùng font TMP **SDF-Dynamic** (bảng ký tự
rỗng, glyph sinh lúc chạy), nên kiểm glyph phải soi cmap của file font nguồn:
`TMP#244.m_fontAsset → TMP_FontAsset.m_SourceFontFile → Font.m_FontData` (`sharedassets13`
pid 48). Bản vá đã thay DotGothic bằng **ULPixel** (2 032 glyph), đủ cả 66 ký tự cần; bản gốc
thiếu 51 chữ hoa có dấu — script dừng nếu thiếu, để ai lùi font thì không ship ô vuông. Backup
`_backup\json.premusiccase`.

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

### Đo `[主人公]` / `【player】` — luôn theo cận trên, không theo tên mặc định

Tên nhân vật chính do người chơi gõ, **tối đa 6 ký tự**, nên bề rộng của mọi dòng
chứa token là một khoảng chứ không phải một số. Ba mốc, tất cả nằm ở `adv_layout`:

| hằng | giá trị | dùng ở đâu |
|---|---|---|
| `DEFAULT_PLAYER_NAME` | `Kanna` | mốc mặc định — cái chắc chắn xảy ra |
| `PLAYER_MEASURE` | `WWWWWW` | `[主人公]` giữa câu (tên riêng) |
| `PLAYER_FULL_MEASURE` | `Suzuno WWWWWW` | `【player】` nameplate (họ + tên) |

`W` là glyph rộng nhất trong `A-Za-z0-9` (advance 60,3), hơn cả kana toàn rộng
(58) — nên 6 chữ `W` là cận trên thật, không phải ước lượng.

Ba cái bẫy đã dính, ghi lại để đừng dính lại:

1. **Xoá tag về rỗng.** `fix_novel_list_wrap.shown()` từng trả `""` cho mọi tag,
   nên `[主人公]` được đo **0 px** thay vì 277,2. Dòng `sID=89 text[6]` vượt khung
   86 px trên máy thật trong khi `--check` báo PASS; TMP đẩy chữ `loại` xuống dòng
   riêng, mà dòng TMP tự ngắt thì **không có thụt treo** nên nó thò hẳn sang trái
   một em. Đây là dạng lỗi chỉ hiện ở màn hình, không cách nào thấy khi đọc data.
2. **Đo bằng tên mặc định.** Đúng cho người chơi không đổi tên, sai cho mọi người
   còn lại. Chênh lệch `Kanna` → `WWWWWW` là **+115,7 px** mỗi lần xuất hiện.
3. **Quên mất họ.** `【player】` vẽ **họ + tên** (`Suzuno Kanna`), không phải mỗi
   tên — ảnh chụp máy thật trong `fix_backlog_autosize` /
   `fix_backlog_select_label` đọc ra đúng chuỗi đó. Đo bằng `Kanna` là thiếu
   219,7 px, và chính chỗ thiếu đó đã giấu 11 nameplate đang tràn sẵn.

Ngân sách nameplate: khung 500 px − `Suzuno ` 219,7 = **280,3 px cho phần tên**.
Mọi tên 6 ký tự thật thử qua đều lọt (`WILLOW` 226,3 px là rộng nhất), nên
`fix_nameplate_wrap` **chặn theo mốc mặc định** và chỉ **báo** cái cận trên: bề
rộng ấy do người chơi gõ ra, không sửa được ở phía dữ liệu, chặn thì gate đỏ
vĩnh viễn mà chẳng có việc gì để làm.

Chỗ nào đo chữ mà chưa qua ba hằng này thì kiểm lại: mỗi tool tự viết `shown()`
của nó, **không tool nào gọi `adv_layout.tag_display`**, nên sửa ở một chỗ không
lan sang chỗ khác.

### Bỏ họ chỉ khi tràn — `【player_firstname】`

Engine biết nhiều khoá tên hơn data dùng. Trong `global-metadata.dat`: bốn token
thân bài `[主人公]` (tên) / `[主人公苗字]` (họ) / `[主人公氏名]` (họ tên) /
`[主人公愛称]` (biệt danh), và ba khoá nameplate `player`, `player_firstname`,
`player_lastname`. Script phát hành chỉ dùng `[主人公]` và `【player】`, nhưng
`resources.assets` có đúng một `【player_firstname】` đứng ở vị trí nameplate —
tổ viết đã dùng, nên khoá này chạy được.

**Luật: nameplate phải là họ + tên như bản Nhật. Chỉ bỏ họ khi tràn khung 500 px.**
Ba plate ghép hai người là ngoại lệ duy nhất hiện có (522–545 px → 302–325 px);
9.802 plate `【player】` còn lại giữ nguyên `Suzuno Kanna`.

Canh hai chiều trong `fix_nameplate_wrap`, vì một chiều là không đủ:

- `RENAMES` ép ba chỗ ngoại lệ giữ dạng đã đổi — merge sheet trả về `player` thì
  `--check` báo "chờ đổi", `--apply` sửa lại.
- `surname_required()` bắt chiều ngược — plate nào dùng `player_firstname` mà
  dựng lại bằng `player` vẫn vừa khung thì là bỏ họ vô cớ, `--check` trả 1.

Bẫy khi tự viết `shown()`: `player_firstname` **chứa** `player` làm tiền tố, phải
thay nó trước, không thì ra `Suzuno Kanna_firstname`.

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

## Tên màn: `Stage N`, và cụm thông báo `Cập nhật quy tắc`

`python tools\fix_stage_term.py [--apply|--check]` — người dùng chốt 28/08/2026 **ưu tiên
sheet**: sheet viết `Cập nhật quy tắc: Stage 1`, build viết `Cập nhật luật: Giai đoạn 1`.
"Ưu tiên sheet" nói bên nào thắng, **không nói phạm vi** — nên vẫn đếm chữ chính văn theo
đúng luật của dự án, và số đo ra cùng một câu trả lời:

```
chữ VẼ RA (ScenarioData.text[], 39 574 ô)      bundle json (UI)
    'Stage <số/EX>'       307                      'Stage <số>'      26
    'Giai đoạn <số/EX>'     5   <- lạc lõng         'Giai đoạn <số>'   0
```

> **Hai cái bẫy, và đây mới là phần khó của việc này.** `giai đoạn` viết thường (36 lần)
> là văn xuôi — "giai đoạn chuẩn bị", "giai đoạn này" — nên mẫu phải neo vào **chữ số hoặc
> `EX`** ngay sau, không neo vào từ. Và `luật` trên chữ vẽ ra 89 lần **gần như toàn là từ
> thường**: `luật chơi` 18, `quy luật` 12, `kỷ luật` 6, `pháp luật` 3. Thay đại trà là hỏng
> văn. Chỉ đổi đúng cụm thông báo cố định, và chỉ **bên trong `[terinfo text="…"]`**.

Đã chạy 28/08/2026 (backup `_backup\scenario01.stageterm`): 11 asset, **42 chỗ**
`Giai đoạn <số>` → `Stage <số>` và **34 chỗ** `Cập nhật/Bổ sung luật` → `quy tắc`, ở cả
`ScenarioData` lẫn 10 script chương. Sau khi vá: `Stage <số>` 312 / `Giai đoạn <số>` **0**,
còn `giai đoạn` thường vẫn đúng 36 và bốn cụm `luật` từ thường không suy suyển.

### Lỗi dữ liệu tìm được cùng đợt: marker `[terinfo] ` lọt vào chữ hiển thị

Sáu chuỗi trong `ScenarioData.scriptText` mang dạng:

```
[terinfo text="[terinfo] Cập nhật luật chơi: Stage 2"]
[terinfo text="[terinfo] Đã có thể tiến hành bỏ phiếu kẻ thủ ác"]
[terinfo text="[terinfo] Hệ thống máy chủ đã bị xóa bỏ"]                …
```

Bản gốc 1.0.2 có **0** lần `[terinfo] `, build có **6** — tức do một đợt dịch làm ra. Nguồn:
sheet để tên lệnh ở một cột riêng (70 ô mang đúng giá trị `[terinfo]`, id dạng `N/cmd/N`),
một pass kéo ô đã nối cột lệnh vào cột chữ. Đã dọn cùng đợt, backup
`_backup\scenario01.terinfoleak`; chốt trước khi ghi: mọi chỗ `[terinfo] ` phải nằm ngay
sau `text="`, và diff trên JSON đã parse chỉ được có đúng hai phép đổi.

> **Còn tồn, cần người quyết.** Bộ `terinfo` vẫn tự mâu thuẫn ở chỗ khác: `Đã xác định
> người thua cuộc` (56) ↔ `Đã xác nhận` (sheet) ↔ `Người thất bại:` (5); `Cập nhật kỹ năng`
> (17) ↔ `Cập nhật Skill` (1); `Đăng ký hồ sơ：` dùng dấu hai chấm **toàn rộng**; và
> `敗北者が確定` còn 43 lần chưa dịch. Không gộp vào đợt này vì sheet không phủ hết, và
> sửa 56 chuỗi theo một dòng sheet là quá tay.

## Nhãn `選択肢` của dòng lựa chọn trong BACKLOG

> ### Đính chính 28/08/2026 — sửa prefab KHÔNG đủ, chữ đến từ literal IL2CPP
>
> Mục dưới đây kết luận `Log_Base_SELECT` không có người nói nên "chuỗi trong prefab
> chính là chữ chạy trên máy". **Sai.** Ảnh chụp máy thật của bản release v1.2.6 vẫn hiện
> `選択肢`, dù `ui_jp` trong đúng file zip đó đã mang `Choice` (đối chiếu CRC từng file
> giữa zip và bản làm việc: khớp). Code ghi đè nốt cả ô này.
>
> Chuỗi thật là literal IL2CPP **#15084 `選択肢`** (9 byte) → `Choice` (6 byte, vừa ô,
> ghi tại chỗ), vá 28/08/2026 bằng `fix_sound_tab_name.py`, backup
> `_backup\global-metadata.dat.presoundnames`. Bằng chứng độc lập có sẵn từ trước mà lúc
> đó không ai nối lại: file save ghi `m_saveText = 選択肢` — chuỗi đó do game sinh ra lúc
> bấm save, tức phải đến từ code chứ không từ prefab.
>
> Đổi được vì **cả bên ghi lẫn bên đọc dùng chung literal này**: `ADVManager$$SetSelectButton*`
> và `$$SelectBackLogAdd` ghi nó vào mục backlog, `BackLog$$TextUpdate`,
> `BackLog_NovelScroll$$TextUpdate`, `BackLog$$PlayVoice` đọc lại — một literal đổi thì
> hai vế cùng đổi. (`_backup\global-metadata.dat.prelitterm8` là bản sao trùng nội dung
> của cùng mốc lùi đó, sinh ra từ một lượt thử trước; giữ lại, không dùng tới.)
>
> Bản vá prefab để nguyên: nó chỉ là placeholder, để `Choice` cho khỏi lệch.
>
> **Bài học, lặp lại lần thứ hai trong ngày** (xem "Nhãn route trên thẻ SAVE/LOAD"): dữ
> liệu đã dịch mà màn hình vẫn ra tiếng Nhật thì **đừng sửa lại chỗ vốn đã đúng** — tìm
> literal. Và cách rẻ nhất để biết prefab có phải nguồn thật hay không là hỏi *"chuỗi này
> có bao giờ bị ghi ra chỗ khác không?"*: nếu nó nằm trong file save thì nó đến từ code.


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

> ### Đính chính 29/08/2026 — `Choice` **có** rớt xuống dòng hai
>
> Ảnh chụp máy thật `_2026-08-29_15-46-37.png`: nhãn hiện thành `Choic` / `e`. Câu kết
> luận ngay bên trên — *"nhãn phải là một từ, không có chỗ ngắt, thì mới chắc chắn không
> rơi xuống dòng hai"* — là **sai**. Khi một từ đã dài hơn bề ngang ô, TMP không còn chỗ
> ngắt hợp lệ nào nên nó ngắt **giữa từ**, từng ký tự một; đúng một từ không cứu được gì.
> `overflowMode = Overflow` cũng không: Overflow chỉ cho khối chữ tràn *xuống dưới* sau
> khi đã ngắt, chứ không tắt ngắt. Chỉ `m_TextWrappingMode = 0` (NoWrap) mới cho chữ chạy
> ngang ra ngoài ô.
>
> Câu *"`Suzuno Kanna` ≈ 250 px trong đúng ô 120 px ấy, ảnh chụp máy thật cho thấy vẫn một
> dòng"* cũng đọc nhầm ảnh: tên một dòng trong ảnh là của `Log_Base`, mà ô của `Log_Base`
> rộng **1010 px** chứ không phải 120.
>
> Sửa (`fix_backlog_select_label.py`, backup `_backup\ui_jp.prebacklogselectrect`):
>
> | | trước | sau |
> |---|---|---|
> | `m_SizeDelta.x` | 120 | **240** — đủ cho cả nhãn hai từ (`Lựa chọn` 185.8 px) |
> | `m_TextWrappingMode` | 1 | **0** (NoWrap) |
>
> Nới ô không chạm ai: `pivot.x = 0` + canh trái nên mép trái ghim, chỉ mép phải đẩy ra;
> đo từ prefab, nhãn ở `x = -821` còn mép phải `BasePanel` (1220 px, `x = -280`) ở `+330`
> ⇒ còn **1151 px** trống. Ba anh em `log` / `Image` / `Voice` của template SELECT đều
> `m_IsActive = False`, mà `BackName_TMP` là con của chính `Log_Base_SELECT` (nơi gắn
> `EventTriggerButton`), nên ô chữ tuy `m_RaycastTarget = 1` cũng không cướp click của ai.
>
> **Hai template chat KHÔNG dính lỗi này — code tự nới ô lúc chạy.** Đã kiểm hai lần trên
> máy thật, không tên nào rớt dòng dù `BackName_TMP` của `Log_Base_Chat` /
> `Log_Base_Chat_Select` cũng khai 120×50, cỡ 33, `m_TextWrappingMode = 1`.
>
> | ảnh | tên | mực chữ | `@id` bắt đầu | ⇒ bề ngang ô thật |
> |---|---|---|---|---|
> | `_2026-08-29_22-49-21.png` | `Suzuno` | x 231→345 (114 px) | x 369 | ≈ **118** |
> | `_2026-08-29_22-59-16.png` | `Kai Munakata` | x 233→452 (**219 px**, một dòng) | x 475 | ≈ **224** |
>
> Chốt bằng `BackNameID_TMP`: trong hai template chat nó là **con của `BackName_TMP`**, neo
> vào **mép phải** cha (`anchorMin.x = 1`, pivot 0, offset 20). Nếu ô cha đứng yên ở 120 px
> thì `@id` phải luôn bắt đầu ở `trái + 140` — đo được 138 với `Suzuno` **nhưng 244 với
> `Kai Munakata`**. Tức ô cha nở theo chữ: 118 và 224 px, khớp bề rộng advance của chính hai
> tên (123,7 và 236,5 px, model nhỉnh hơn ~5%). Vậy 120 px trong prefab chỉ là số lúc dựng;
> lúc chạy code đặt lại theo preferred width, nên tên dài cỡ nào cũng một dòng.
>
> **Vì sao `Log_Base_SELECT` thì rớt.** Nó không có `BackNameID_TMP`, và nhãn của nó là
> chuỗi cố định code ghi thẳng — không đi qua nhánh đo-rồi-nới đó, nên 120 px là số thật và
> `Choice` (138,6 px) bị ngắt giữa từ. Hai chỗ nhìn giống nhau nhưng đi hai đường code khác
> nhau; đừng suy từ chỗ này sang chỗ kia.
>
> **Bài học của cả mục này:** số đo tĩnh trong prefab chỉ là giả thuyết. Hai kết luận sai
> liên tiếp ở đây — "một từ thì không thể rớt dòng" (sai vì TMP ngắt giữa từ) và "năm tên
> chat sẽ tràn ô 120" (sai vì dùng nhầm font NewRodin cho ô dùng DNPShueiMGo, rồi sai tiếp
> vì ô đó không cố định) — đều chỉ vỡ ra khi chụp ảnh máy thật. Cứ nghi ngờ thì chụp.

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

## Tên nhân vật ở dòng INFO tab SOUND (`fix_sound_tab_name.py`)

Tab SOUND có 21 thanh trượt. Nhãn thanh trượt lấy từ `ConfigVolumeData.label` —
dữ liệu, đã La-tinh hoá từ lâu (`Miyabi`, `Hotaru`, `Kyosuke`…). Nhưng **dòng
INFO ở đáy màn hình** thì không: `Config.InfoTextInit()` (RVA `0x19BC090`) dựng
nó bằng

```
String.Concat(<literal tên tiếng Nhật>, GetSystemText(76))
```

đúng 16 lần. `SystemTextID 76` (`CONFIG_COMMON_SET_VOICE_VOLUME`) đã dịch, nên
màn hình ra `光希's volume settings` — nhãn thì Latin, dòng INFO ngay dưới lại
tiếng Nhật. Ghi chú phát hành v1.2.5 nói "bốn tên còn sót"; thật ra là **16**.

### Chỉ vá được 1 trong 16

Trình biên dịch C# gộp chuỗi giống nhau thành **một** mục literal, nên literal
`蛍` mà `InfoTextInit` dùng cũng chính là literal `ADVManager` dùng. Xref trên
bản dump Il2CppDumper:

| literal | ai dùng |
|---|---|
| `恭介` | `Config$$InfoTextInit` — **chỉ một chỗ** |
| `蛍` `栞` `光希` | + `ADVManager$$CutInPositionOffset`, `$$DigitalAnimationIdAdjust`, `Config$$.cctor` |
| `雅火` `戒` `藍` | + thêm `$$GetNameColor` / `DebugManager$$TextUpdate` |

Hai hàm `ADVManager` là `switch` trên chuỗi (`ComputeStringHash` + hàng loạt
`String.op_Equality`). Chúng nhận `chara` **lấy thẳng từ tag lệnh trong kịch
bản** — `[蛍 出 1111 M すまし slot=0]` — và tag lệnh thì không bao giờ được dịch
(quy tắc `[...]`). Đo trên build: tag sprite của cả 20 tên **giống bản gốc từng
byte**. Nên vế bên kia phép so mãi mãi là tiếng Nhật; đổi literal = phép so trượt.

`恭介` an toàn vì nhân vật đó không có sprite riêng — anh ta dùng sprite của
`伊槻` (tình tiết cải trang). ScenarioData có **0** tag `[恭介 …]`.

### Bài học `涼乃`, và phép chốt sinh ra từ nó

Một bản trước đổi literal #15053 `涼乃` → `Suzuno`. `涼乃` là **họ của nhân vật
chính** (hiện trên nameplate, nên đổi là đúng) — nhưng nó **đồng thời** là khoá
sprite của chính cô: ScenarioData còn **495** tag `[涼乃 …]`. Từ đó
`CutInPositionOffset` và `DigitalAnimationIdAdjust` không còn nhận ra nhân vật
chính, rơi về nhánh mặc định. Hỏng lặng lẽ, không phép kiểm nào bắt được.

Đó là bản vá literal **duy nhất** từng đụng vào một khoá lệnh còn sống. Mọi bản
khác đều chọn biến thể có `・` (`戒・`, `藍・`, `雅火・`, `奏壱・`, `ユーリ・`) — 0 tag,
nên vô hại. `環無` → `Kanna` cũng 0 tag.

Nên script tự nạp ScenarioData và **từ chối vá nếu còn tag lệnh nào lấy chuỗi đó
làm khoá**. Ba tên `蛍` / `栞` / `光希` nằm sẵn trong danh sách `REFUSED` kèm số tag,
để lần sau khỏi phải điều tra lại.

### Chỗ ghi

`恭介` chiếm 6 byte, `Kyosuke` cần 7, và ô kề (`#15029 戒`) xếp khít — 0 byte dư.
Nhưng bảng literal là cặp `(length, dataIndex)` nên chuỗi mới ghi ở **đâu cũng
được**. Script dựng lại bản đồ byte từ cả 15.224 mục, tìm ra **33 byte mồ côi
trong 8 khoảng** (lớn nhất 16 byte @372.165 — phần dư của bản vá
`ターミナルを開いてください` → `Vui lòng mở Terminal`), rồi cấp phát từ khoảng vừa nhất.
Chuỗi nào vừa ô cũ thì ghi tại chỗ, khỏi tiêu chỗ trống.

```powershell
python tools\fix_sound_tab_name.py [--apply]
```

Đã chạy 28/08/2026, backup `_backup\global-metadata.dat.presoundnames`. Vá 2
literal: `#15028 恭介` → `Kyosuke` (dời sang @372.165), `#15084 選択肢` → `Choice`
(tại chỗ). Kiểm sau khi ghi: kích thước file không đổi, **26 byte đổi, 0 chỗ
khác**, 15.224 literal giải mã UTF-8 sạch, 0 mục tràn khối.

**Còn tồn:** 15 tên kia. Muốn chữa phải cấp cho `InfoTextInit` literal riêng —
tức vá nhị phân `main` rồi dựng lại `.ips`, không phải vá metadata. Rủi ro thật:
slot literal được nạp theo danh sách usage của từng hàm, trỏ sang slot ngoài
danh sách thì có thể null lúc chạy. Chưa làm.

## Nameplate hỏng khoá và tên nhân vật chính bị viết cứng (`fix_nameplate_key.py`)

`ScenarioData` giữ mỗi nameplate ở **ba** trường:

| trường | vai |
|---|---|
| `scriptText_Line` | bản THÔ, khớp từng byte với bản gốc — không bao giờ sửa |
| `scriptText` | bản dịch |
| `talkName` | bản dịch, một ô cho mỗi tin nhắn |

Cách soát: so nửa khoá của `【khoá/hiển thị】` giữa build và bản gốc **theo từng vị
trí**. 673 chỗ lệch, 39 kiểu — phần lớn là bản dịch cố ý cho nhân vật phụ
(`看護師` → `Y tá`), vô hại vì chỉ 6 khoá được `ADVManager$$GetNameColor` đọc
(`宗像 戒`, `永守 藍`, `弥坂 奏壱`, `神楽 侑莉`, `雅火`, `ユーリ`). Sáu chỗ còn lại là lỗi:

| hỏng | đúng | n | vì sao |
|---|---|---|---|
| `【Phía Đông堂 伊槻/姫嶋 恭介】` | `【東堂 伊槻/Himejima Kyosuke】` | 60 | `東` bị pass thay chữ đổi thành "Phía Đông" *giữa khoá*; 423 chỗ cùng loại đã đúng |
| `【Miyabi/瑠璃】` | `【雅火/Ruri】` | 3 | ngược đời: nửa KHOÁ bị La-tinh hoá, nửa HIỂN THỊ còn tiếng Nhật. `雅火` là khoá màu tên |
| `【Quán cà phêの店員】` | `【NV quán café】` | 1 | `カフェ` bị đổi giữa chuỗi, bỏ lại `の店員`; 25 chỗ cùng loại đã đúng |
| `【Kanna＆Kai】` | `【player＆Kai】` | 14 | token `player` bị viết cứng thành tên mặc định |
| `【Kai＆Kanna】` | `【Kai＆player】` | 4 | nt |
| `【Kanna＆Ran】` | `【player＆Ran】` | 4 | nt |

Ba dòng cuối là đúng thứ CLAUDE.md cấm: ai đặt tên khác `Kanna` sẽ thấy sai tên,
mà một lượt chơi bằng tên mặc định thì trông hoàn hảo nên không lộ. `player` là
literal mà `ADVManager$$CharaNameConvert` / `$$ShowCharaNameUpdate` /
`$$GetNameColor` thay thế, và bản gốc cũng ghép `【player＆戒】` y như vậy — giữ
token trong chuỗi ghép là đúng.

Ba dòng đầu chỉ hỏng ở `scriptText`; ba dòng `player` hỏng ở cả `scriptText` lẫn
`talkName`. Sau khi sửa, hai trường dịch khớp số với nhau ở cả sáu (423/423,
3/3, 13/13, 7/7, 2/2, 2/2) — đó là dấu hiệu tốt nhất cho biết đã đúng.

`json.dumps(..., separators=(",",":"))` tái tạo `ScenarioData` **khớp nguyên
văn** bản gốc, nên chỉ 86 chỗ đó đổi và kiểm chứng được. Không chỗ nào đổi số
dòng, nên `loadLine` / `selLine` vẫn trỏ đúng (script tự kiểm lại cả hai).

```powershell
python tools\fix_nameplate_key.py [--apply]
```

Đã chạy 28/08/2026, backup `_backup\scenario01.nameplatekey`. Sau khi ghi: **0
chuỗi lẫn nửa Nhật nửa Việt** còn lại trong nameplate, `scriptText_Line` khớp bản
gốc, 269.210 dòng thô nguyên vẹn.

## Nameplate ADV dài quá khung, xuống 2 hàng (`fix_nameplate_wrap.py`)

Ảnh máy thật `_2026-08-30_03-17-51.png`: `【ＪＥＣ職員Ａ/Người quen của Yuri】` vẽ thành
**hai hàng** — `Người quen của` ở trên, `Yuri` ở dưới, đổ ra ngoài ô nameplate và đè
lên tranh nền.

### Khung và vì sao nó không co chữ

`level10` pid 650 / 699 (`Message(Normal|Highest)/Name`), rect **500 × 70**. `level10`
không có type tree nên đọc bằng cách dump byte thô của MonoBehaviour — các trường TMP
nằm đúng thứ tự serialize:

| offset | trường | giá trị |
|---|---|---|
| 308 | `m_fontSize` | 42 |
| 320 | `m_enableAutoSizing` | **0** |
| 348 | `m_characterSpacing` | 5.5 |
| 356 | `m_lineSpacing` | 0 |
| 372 | `m_enableWordWrapping` | **1** |
| 380 | `m_overflowMode` | 0 (Overflow) |

Auto-size TẮT + word-wrap BẬT + overflow tràn = tên dài **không bao giờ bị hạ cỡ chữ**,
nó xuống hàng rồi đổ ra ngoài. Khác hẳn ô ADV (`fix_adv_wrap`) vốn co chữ 42→28. Hai
object này byte khớp `UNLOGICAL_v2` — mod chưa từng đụng, đây là hành vi sẵn có.

### Cỡ chữ phải đo từ ảnh, con số trong scene sai

Game chỉnh lại nameplate lúc chạy: đo trên ảnh ra **~47,5 px** chứ không phải 42, và
gốc chữ nằm ở x=62 trong khi rect nói 87. Nên mô hình hiệu chuẩn thẳng từ ảnh — dò
(cỡ chữ, characterSpacing, gốc) khớp vị trí trái của 12 glyph `Người quen của`:

    bề rộng(px) = tổng(advance_glyph × 47.5/58 + 0.44)      rms 0,6 px, lệch nhiều nhất 1,2 px
    bước dòng   = 47.5 × 116/58 = 95 px                     (đúng 95 px đo được giữa 2 hàng)

Cùng phép dò đó áp lên dòng ADV trong chính ảnh ra 42,5 px / gốc 307,1 — khớp
`m_fontSize` 42 và mép rect 308, nên phép dò là đúng, chỉ riêng nameplate bị game
chỉnh. Lưu ý `adv_layout.CHAR_SPACING = 5.3` là **đơn vị font**, không phải px.

Khung suy ra từ ba mốc, không phải đoán:

| chuỗi | px | thực tế |
|---|---|---|
| `Người quen của Yuri` | 553 | gãy (ảnh) |
| `Himejima Kyosuke` | 495 | không gãy, ×423 ô, chơi nhiều lần |
| `Người quen của ` | 442 | vừa (ảnh) |

→ khung ∈ [495, 553), tức đúng **500** của rect.

### Nameplate trong `[chat]` dùng widget khác — ĐỪNG tính chung

289 ô nameplate dạng tài khoản (`【Kai Munakata@k_munakata2150】` 893 px,
`yasaka@eggsand_yaa` 589, `YURI@yyy58302199` 584, `Shiori@S_hi0ri_kxoxo` 573,
`Unknown@73w35vq` 561) nằm trong khối `[chat start] … [chat end]` và vẽ bằng widget chat
Genebark — khung rộng hơn nhiều, cỡ chữ nhỏ hơn (xem đo 742 px ở mục Sekigawa). Chơi
thật **không cái nào gãy**; lần soát đầu tôi báo nhầm chúng là "gãy sẵn từ bản gốc".

Máy quét trạng thái theo dòng bỏ sót 15 ô (`107/269–279`, `106/167–168`): chúng nằm
trong **nhánh lựa chọn** mà `[next target=*SOU-03-12-02]` nhảy vào, còn `[chat start]`
thì ở trước chỗ rẽ nhánh. Luật đúng dùng cả hai chiều:

    trong chat = (lệnh [chat …] gần nhất phía TRƯỚC là start/restart)
              hoặc (lệnh [chat …] gần nhất phía SAU là end/stop)

Vế thứ hai bắt đúng cả 15 ô đó — không thể `[chat end]` một phiên chat chưa mở.

### Mười tên đã rút gọn

| cũ | px | mới | px | n | chỗ |
|---|---|---|---|---|---|
| `ナレーション/Giọng từ màn hình ngoài phố` | 778 | `Giọng từ màn hình` | 494 | 1 | 117/0 |
| `Người nước ngoài bí ẩn` | 620 | `Người nước ngoài` | 472 | 1 | 74/340 |
| `ＪＥＣ職員Ａ/Đồng nghiệp của Yuri` | 587 | `Đồng nghiệp` | 343 | 2 | 120/29, 31 |
| `Thanh niên đi đường` | 555 | `Người đi đường` | 408 | 2 | 120/21, 22 |
| `ＪＥＣ職員Ａ/Người quen của Yuri` | 553 | `Người quen Yuri` | 436 | 5 | 116/11, 13, 19, 22, 24 |
| `Sinh viên khoa khác` | 545 | `SV khoa khác` | 375 | 3 | 17/9, 13, 15 |
| `Màn hình ngoài phố` | 530 | `Màn hình LED` | 376 | 2 | 84/128-129 |
| `Munakata Kai＆Yuri` | 527 | `Kai＆Yuri` | 242 | 1 | 83/292 |
| `Các người tham gia` | 525 | `Người tham gia` | 408 | 6 | 70/214… |
| `Phụ nữ hàng xóm` | 473 | `Nữ hàng xóm` | 357 | 2 | 72/1106-1107 |

`街頭ビジョン` (84, chính màn hình phát bản tin) và `ナレーション/街頭ビジョンの声` (117, lời
dẫn trailer phát ra *từ* màn hình) là hai chuỗi khác nhau trong bản Nhật — giữ cặp
`X` / `Giọng ... X`. `Phụ nữ hàng xóm` 473 px vốn chưa gãy, rút cho có biên.
`Giọng từ màn hình` 494 px chỉ dưới khung 6 px; thấy gãy trên máy thật thì hạ tiếp
xuống `Giọng màn hình` (420 px).

**Ba chỗ mất sắc thái, cố ý đánh đổi lấy bề rộng.** Muốn lấy lại thì phải nghĩ chữ
ngắn hơn, đừng chỉ nối lại chữ cũ:

- `通行人の若者` (thanh niên) → `Người đi đường`: mất "trẻ", và gần trùng
  `Người qua đường` (`通りすがりの人`, 461 px, ×4) vốn là một vai khác.
- `ユーリの同僚` → `Đồng nghiệp`: mất "của Yuri". Cùng mạch còn `ユーリの仲間` →
  `Đồng đội của Yuri` (485 px) giữ nguyên, nên hai vai vẫn phân biệt được.
- `宗像 戒＆ユーリ` → `Kai＆Yuri`: bỏ họ. Các nameplate ghép khác đã dùng tên trơ
  (`Yuri＆Kai＆Soichi`, `Tobari＆Awayuki`) nên đây lại là nhất quán hơn.

```powershell
python tools\fix_nameplate_wrap.py [--apply]
```

Đã chạy 30/08/2026, backup `_backup\scenario01.nameplatewrap` (chụp trước đợt đầu, lùi
được cả hai lượt). 50 chỗ đổi (25 `scriptText` + 25 `talkName`) qua hai lượt.

Sau khi ghi: **0 nameplate ADV vượt khung**, rộng nhất còn lại là `Himejima Kyosuke`
495 px — đúng cái mốc "chơi 423 lần không gãy" đã dùng để suy ra khung, nên biên tự
xác nhận lại. So với backup: `text`, `selText`, `scriptText_Line`, `voice`, `loadLine`,
`selLine` **giống hệt từng mục** — chỉ hai trường nameplate đổi. `check_scripts`
143/143, `check_chapterdata` 8/8, `check_layout_breaks` 222.966 → 222.966 ngắt dòng và
17.425 → 17.425 dòng thụt, `fix_adv_wrap` / `fix_ellipsis_break` / `fix_paren_balance` /
`fix_novel_list_wrap` / `fix_terminal_term` / `fix_center_caption_wrap` đều PASS.
(`fix_jp_sentence_break` và `fix_profile_comment` FAIL sẵn từ trước, ở `text[]` và
`TerminalProfileData` — hai chỗ tool này không chạm.)

### Nameplate KHÔNG nằm trong sheet — không phải đẩy ngược lên upstream

Tab `sd_*` để nameplate bản Nhật ở **cột B** làm chú thích (`【ＪＥＣ職員Ａ/ユーリの知人】`),
**không có cột dịch kèm**; `read_sheet()` lại chỉ đọc cột C (Nhật) và D (Việt). Quét
snapshot `(62)` cho cả 10 tên cũ: **0 ô**. Nên `talkName` chỉ sống trong build, merge
không bao giờ trả lại tên dài, và 10 chỗ này không sinh nợ upstream như 48 ô của đợt
Sekigawa.

`--check` vẫn đáng chạy sau merge — nó soát **mọi** nameplate chứ không riêng bảng
`RENAMES`, nên bắt được tên dài mới do người sửa thẳng trên build.

### Một nameplate còn tiếng Nhật, và nó cũng không có trên sheet

`3/18`, `4/18`, `5/18` giữ `【不知火の男Ａ/Shigeru】;【不知火の男Ａ】` — ô `;` thứ hai không có
nửa hiển thị nên vẽ thẳng cái khoá `不知火の男Ａ` (288 px, không tràn). Bản Nhật cũng cùng
dạng (`/茂】;【不知火の男Ａ】`), tức bản dịch chỉ làm nửa đầu.

Không sửa được qua sheet: **9 scenario không có tab `sd_*` nào** — 0, 1, 2, 3, 4, 5, 7,
8, 12 — và toàn bộ text của chúng còn tiếng Nhật (sID 7 riêng nó đã 1.235 ô). **Chúng
là script test của nhà phát triển, không vào được trong game** — xem mục dưới. Không
phải lỗ hổng dịch.

## DLC là một title khác — `010068501FF9B001` (`extract_dlc_romfs.py`, `apply_dlc_sheet.py`)

Ảnh máy thật IMG_7247 (03/09/2026): màn Download Contents còn nguyên tiếng Nhật, và người
dùng báo "toàn bộ nội dung DLC vẫn tiếng Nhật". Không phải merge sót: **nội dung DLC không
nằm trong romfs của game gốc.** DLC 1 là AOC `UNLOGICAL [010068501FF9B001][v0][DLC 1].nsp`
(2,25 MB, đăng ký trong `%APPDATA%\Ryujinx\games\010068501ff9a000\dlc.json`); LayeredFS áp
theo title nên mod `contents/010068501ff9a000` không đổi được gì ở đó. Bóc bằng
`extract_dlc_romfs.py` (mượn crypto của `extract_exefs.py`, thêm phần đọc IVFC/RomFS) ra
`D:\Downloads\UNLOGICAL_DLC1\romfs`, đóng vai dump gốc của AOC:

| file | nội dung |
|---|---|
| `scenario/scenario_aoc01` | `ScenarioData` riêng: 5 scenario 1005–1009, script `09_01`…`09_05` ("朝のひと時", mỗi nhân vật một truyện ngắn), **399 câu**, 0 lựa chọn, 0 tag hiển thị; `scenariolist`, `ChapterAlready` |
| `json/json_aoc01` | `DLCData_01`: 5 `charaName.jp` (chữ hiện ở danh sách nhân vật) + tên sprite (khoá, giữ) |
| `sprite/sprite_jp_aoc01` | 16 ảnh: 5 bảng tên `UL_dlc_c_name_*` (đã Latin "Miyabi After"…), 5 thumbnail `UL_dlc_c_win_02_*` (góc trên còn `朝のひと時`), 5 bảng tiêu đề `UL_dlc_c_win_03_*` (chữ trang trí Latin), `UL_dlc_a_headsup_01` (màn Caution, tiếng Nhật) |
| `texture/texture_aoc01` | nền |

Các script `09_01_01`…`09_05_10` trong `scenario01` gốc là chương thường, không liên quan.
Game gốc chỉ giữ phần vỏ: `SceneLabelList` có 25 label `*…-DLC-02-…`, `SystemContentFileNameData`
trỏ tới `UL_dlc_*`, và ba ảnh hub nằm trong bundle gốc **chưa ship**: `sprite/sprite02`
(5 cửa sổ CHAPTER `UL_dlc_cd_win_01_*` 480×152, tên Nhật bằng font pixel — chính là cửa sổ
`永守 藍` trong ảnh), `texture/texture02` (`UL_dlc_b_key` `Ⓐ決定 Ⓑ戻る`, `UL_dlc_cd_key`
`Ⓐシーン再生 Ⓑ戻る`, `UL_dlc_b_bg_base`), `ui/ui01` (trang trí).

**Sheet gốc `UNLOGICAL_v2` không có tab DLC** — soát cả snapshot 90 và 91. Bản dịch nằm trong
workbook riêng `D:\Downloads\UNLOGICAL_DLC1.xlsx`, tab `sd_1005`…`sd_1009`, cùng khuôn 4 cột,
id `1005/txt/0000`; JP khớp 399/399 ô của AOC, VN đủ 399. (`UNLOGICAL_DLC2.xlsx`, id
2005–2009, là DLC 2 — AOC đó **chưa có trên máy**, cần NSP để bóc.)

`apply_dlc_sheet.py` ghi từ bundle GỐC của AOC (không ba chiều, chạy lại là idempotent) ra bản
làm việc `D:\Downloads\010068501ff9b001\romfs`, junction vào
`%APPDATA%\Ryujinx\mods\contents\010068501ff9b001\vn-translation\romfs`. Chốt như
`apply_sheet_cells.py`: JP khớp build, multiset tag, `[主人公]` hai bên (`TOKEN_DROP_OK` cho
`1006/txt/0004` — bản dịch thay tên bằng "em", ô không có bản đôi), ô `isDefaultNameAdjust`
phải mang `Kanna`. Hai bẫy đã dính: mảng JSON của asset viết **không có khoảng trắng** sau dấu
phẩy (json.dumps mặc định không khớp), và câu một dòng xuất hiện y hệt ở `text[]` lẫn
`scriptText_Line[]` nên thay theo từng chuỗi là mơ hồ — phải thay **nguyên mảng** `text[]` /
`talkName[]`. Nameplate không có trên sheet, đổi theo dạng bản gốc `【khoá Nhật/tên La-tinh】`
(`【雅火/Miyabi】` 1936 lần trong build…): 119 nameplate. `DLCData_01.charaName` → tên La-tinh.
Kết quả 03/09/2026: 399/399 câu, chỉ `ScenarioData` và `DLCData_01` đổi, 7 asset còn lại
nguyên byte. Thư mục thử cho máy thật: `D:\Downloads\unlogical-vi-patch-dlc1-romfs\vn-translation\romfs`
→ chép vào `contents/010068501ff9b001/`.

**Còn lại, chưa làm:** ảnh có chữ Nhật (`朝のひと時` trên 5 thumbnail, màn Caution, 5 cửa sổ
CHAPTER và 2 dải phím trong bundle gốc — cần tiêu đề tiếng Việt và câu Caution; font
`ULPixel`/`font_BASE` của `fix_key_prompts.py` nằm ở scratchpad đã mất, phải trích lại từ
Font asset), và chỗ đặt trong repo / cách đóng gói phát hành cho title thứ hai.

## `scenarioID` 0–12 là script test, KHÔNG dịch

`scenarioID` là **chỉ số vào `scenariolist.keys`** (TextAsset trong bundle `scenario01`,
144 khoá). 13 khoá đầu đều là đồ test, nội dung thật bắt đầu từ chỉ số 13:

| sID | keys[sID] | #text | nội dung |
|---|---|---|---|
| 0-2 | `01_test_live2d_01..03` | 37/48/8 | duyệt biểu cảm Live2D của `矢代` / `鳴神` / `朧` — `鳴神` và `朧` là nhân vật *Kamigami no Asobi*, không có trong UNLOGICAL |
| 3-5 | `sample1..3` | 94 mỗi cái | văn bản mẫu của engine (`わたしたちは二十三区の黒鶴たちへ伝令に来た。`) |
| 7 | `UL_Live2d_test_sample` | 1235 | 1.235 dòng toàn tên biểu cảm (`すまし`…) |
| 8 | `UL_test` | 89 | **bảng kiểm QA gửi khách**: `スクリプトベース演出リスト…` / `こちらの演出やアニメーションで問題ないかご確認お願い致します` |
| 12 | `UL_test_select` | 0 | thử lựa chọn, 5 lệnh nhảy, 0 ô text |

`sd_013` = `07_01` — tab đầu tiên của sheet trùng đúng chỗ nội dung thật bắt đầu, tức
upstream cũng cắt ở đây.

Năm bằng chứng độc lập cho thấy không vào được:

1. `ChapterData` — 43 mục, nguồn duy nhất của SECTION SELECT — không mục nào có `file`
   là script test.
2. `SceneLabelList`, `SceneReplayData`, `MapData`: **0/31** nhãn mà script test định
   nghĩa (`*Live2D-01-00`…).
3. Không script thật nào nhảy vào nhãn của script test (quét `*<nhãn>` trên cả 143).
4. `global-metadata.dat`: **0** lần xuất hiện `ul_test` / `UL_test` / `ul_check` /
   `01_test_live2d` / `sample1` — code cũng không gọi tên chúng.
5. `scenariolist` còn 4 khoá **không có TextAsset nào**: `ul_check`, `ul_test2`,
   `ul_test3`, `ul_test4` (chỉ số 6, 9, 10, 11) — danh sách này vốn là rác build.

Nên đừng đưa 9 scenario đó lên sheet, và đừng tính chúng vào tiến độ dịch.

## Chữ BACKLOG tràn ra đè lên mục kế tiếp (`fix_backlog_autosize.py`)

Ảnh máy thật `_2026-08-29_15-46-29.png`: một tin nhắn **3 dòng cứng** của ADV nở
thành **5 dòng** trong BACKLOG — hai từ `là` / `lại` rơi mồ côi cuối dòng, và
dòng cuối `Ran.` vẽ đè lên tên `Suzuno Kanna` của mục bên dưới.

BACKLOG đọc **đúng chuỗi `ScenarioData.text[]`** mà ADV đọc, kể cả ngắt dòng
cứng. Khung thì khác hẳn:

|            | ADV                   | BACKLOG `Log_Base`        |
|------------|-----------------------|---------------------------|
| bề rộng    | 1280                  | **1210**                  |
| cỡ chữ     | 42, **tự thu tới 28** | 42, **`autoSize = 0`**    |
| chiều cao  | khung co theo cỡ chữ  | hàng **1556×336 cố định**, `VerticalLayoutGroup.childControlHeight = 0` |
| tràn       | —                     | `overflowMode = Overflow` → **không cắt, vẽ đè hàng dưới** |

Hẹp hơn 70 px nên dòng vốn đã vừa ADV bị ngắt lại; không tự thu chữ nên không có
gì bù. Bản Nhật không lộ vì nó ngắt cứng sẵn cho vừa — 66.543 dòng cứng, chỉ
**54 tin nhắn (0,14%)** vượt 3 dòng. Bản Việt vượt **4.323 (10,9%)**, dài nhất 8
dòng.

**Bỏ ngắt dòng cứng không cứu được:** đo thử thì chỉ còn 3.185 (8,05%) — gỡ được
26%. Vì 64% số ca tràn **vốn không có ngắt cứng nào**, chúng chỉ là câu dài. Mà
sửa `text[]` thì đổi luôn ADV. Nên đường đó bị loại ở cả hai đầu.

### Chỗ trống vốn đã có sẵn

Ô `BackMessage_TMP` khai `1210×50` nhưng thật ra đang vẽ tràn ra ngoài ô đó —
`overflowMode = Overflow` che chuyện ấy, nên con số 50 là hư cấu. Chỗ thật:

```
mép trên chữ  y = +45          (ô 50 px, pivot dọc 0,50, pos y = +20)
đáy hàng      y = -168         (Log_Base 1556×336)
              ---------
              213 px
```

Đo lại trên ảnh máy thật: từ mép trên mực dòng 1 (y=479) xuống đáy khung trắng
(y=706) là **227 px** — mô hình chặt hơn thực tế 14 px, giữ 213 cho an toàn.
Bề rộng thì khớp 1:1: dòng dài nhất trong ảnh đo được **1205 px mực** trong khung
1210. Bước dòng đo giữa hai dòng đầy = **66,5 px**, mô hình tính 67,2.

Bản vá chỉ **khai đúng** phần chỗ chữ vốn đã chiếm rồi bật tự thu chữ như ADV.
Pivot dọc 0,50 nên phải dời tâm xuống để giữ nguyên mép trên: `y = top − h/2`.

| template | rect cũ | rect mới | tự thu | tràn trước → sau |
|---|---|---|---|---|
| `Log_Base` | 1210×50 @(−781, +20) | **1210×213 @(−781, −61,5)** | 42→28 | 4.323 (10,92%) → **0** |
| `Log_Base_Chat` | 1210×50 @(−720, −9) | **1210×184 @(−720, −76)** | 40→26 | 101 (8,46%) → **0** |

89% tin nhắn ADV và 92% tin nhắn chat vẫn hiển thị nguyên cỡ chữ cũ; chỉ câu dài
mới nhỏ lại. Sàn 28 của `Log_Base` lấy cho khớp sàn khung ADV; ô chat cần 27 mới
sạch nên để 26, chừa biên cho sai số ~1% của mô hình.

`Log_Base_Chat_Select` và `Log_Base_SELECT` khai sẵn 1220×280 — đủ chỗ, không đụng.

```powershell
python tools\fix_backlog_autosize.py            # đo, so trước/sau
python tools\fix_backlog_autosize.py --check    # thoát 1 nếu chưa vá
python tools\fix_backlog_autosize.py --apply
```

Đã chạy 29/08/2026, backup `_backup\ui_jp.prebacklogautosize`. Kiểm sau khi ghi:
7.937 object (không đổi), **đúng 4 object đổi nội dung** — 2 `RectTransform` +
2 `MonoBehaviour` nhắm tới; **707 Sprite / 122 Texture2D / 23 Material giống hệt
từng byte**, tức không dính bẫy tight-mesh của lần vá atlas.

Không đụng một chữ nào của bản dịch: `ScenarioData`, `GenebarkChatMainData` và
khung ADV giữ nguyên tuyệt đối.


## BACKLOG ngắt dòng khác ADV (`fix_backlog_adv_scale.py`)

Phần còn lại của mục trên. Bản vá `fix_backlog_autosize.py` chống *tràn đè hàng
dưới*; nó cố ý không đụng chuyện **ngắt lại**. Ảnh máy thật
`_2026-08-29_23-12-50.png`, hàng `Áo đen`, cho thấy phần còn lại đó:

```
Đã hết 30 phút. Thời gian thảo luận kết thúc
tại
đây.
```

Đo mực dòng 1 trên ảnh: x 169 → 1301 = **1133 px**. Thêm ` tại` là **1213 px**, ô
backlog rộng **1210** ⇒ hụt **3 px** nên `tại` rơi xuống, còn `đây.` vốn là ngắt
cứng của bản dịch nên thành dòng ba.

### Cùng font, chỉ khác bề rộng khung

| | khung nguồn | BACKLOG |
|---|---|---|
| `Log_Base` ← ADV `Message/Text` | 1280×186, cỡ 42 | 1210×213, cỡ 42 |
| `Log_Base_Chat` ← `genebark` `Message_TMP` | 1210×80, cỡ **32**, `charSpacing` **5** | 1210×184, cỡ **40**, `charSpacing` **8.5** |

Asset khai hai font khác nhau (`iroha21popura` cho backlog, `adv_layout` ghi
`NewRodinProN-DB` cho ADV) nhưng **trên màn hình chữ Việt là một font**. Bằng
chứng, đo tỉ lệ bất biến theo cỡ chữ `bề ngang "Se" / cao chữ "S"`:

```
ADV      _2026-08-29_15-47-23.png  "Sekigawa"   1,765
BACKLOG  _2026-08-29_23-14-19.png  "Selector"   1,759     lệch 0,3%
```

Cả hai font asset đều **Dynamic** nên glyph chữ Việt nạp lúc chạy từ cùng một font
dự phòng — `level10` không có type tree nên không đọc thẳng được font của ADV, và
đây là cách kiểm rẻ nhất. (Một bản nháp của mục này từng kết luận hai font khác
nhau, lệch bề ngang 12,7%, dựa vào bảng advance của hai file font — sai, vì bảng
đó không phải thứ máy đang vẽ.)

Hệ quả: chỉ bề rộng khung là khác, nên tiêu chí thành phép chia.

### Con số

`42 × 1210/1280 = 39,7` ⇒ lấy **39,5**. Mọi dòng vừa khung ADV chắc chắn vừa khung
backlog vì `39,5/42 × 1280 = 1204 px < 1210`, dư 6 px biên.

Ca trong ảnh: dòng `「Đã hết 30 phút. …kết thúc tại` ở cỡ 42 đo được **1213 px**
(quá ô 1210 đúng 3 px ⇒ rớt chữ), ở 39,5 còn **1141 px**. Trên toàn bộ
`ScenarioData` có **1.437 tin nhắn** mang dòng lọt khoảng 1210–1280 px — đúng nhóm
bị backlog ngắt lại.

### Chat: backlog vẽ to hơn màn chat 25% — CHỐT GIỮ NGUYÊN 40

> **Quyết định 30/08/2026.** Bản vá cỡ 32 đã ghi rồi **hoàn tác**; người dùng chốt giữ
> nguyên cỡ 40 của nhà phát triển, chấp nhận **45/457 dòng** chat trong backlog ngắt khác
> màn chat. `fix_backlog_adv_scale.py` nay ghim ô chat ở 40 / 40 / 8,5 để không ai vá lại
> nhầm. Số đo dưới đây giữ lại làm căn cứ nếu sau này muốn xét lại:
> cỡ 40 → 45 dòng gãy · 38 → 32 · 36 → 20 · 34 → 12 · 32 → 0.
>
> Hai hướng thay thế đã loại: **áp cỡ 40 cho cả màn chat** làm 72/457 dòng gãy ngay ở màn
> đọc chính và ô chữ cao 80 px chỉ chứa nổi 1,4 dòng ở cỡ 40 (tràn khung); **nới ô backlog**
> bất khả vì dòng rộng nhất ở cỡ 40 là 1502 px trong khi ô chỉ nới tới ~1210 là đụng nhãn
> `CHAT` dọc. Còn "làm TMP riêng cho backlog" thì vốn đã riêng sẵn: `BackMessage_TMP` của
> `Log_Base_Chat` là object khác hẳn `Message_TMP` của màn chat, chỉ chung font asset.

Cùng bề rộng ô 1210, nên chỉ cần vẽ đúng cỡ của khung chat. Trước bản vá nó vẽ
cỡ 40 trong khi màn chat vẽ cỡ 32 — đo chiều cao chữ hoa trên hai ảnh thật:

```
BACKLOG  _2026-08-29_22-49-21.png  chữ "A"  cao 30 px
CHAT     _2026-08-28_13-17-14.png  chữ "K"  cao 24 px      tỉ lệ 1,250 = 40/32
```

Nên cùng một câu mà hai màn ngắt dòng khác chỗ. Trong **289 tin nhắn chat của
`ScenarioData`**, số tin có dòng vượt ô 1210: **90/289 ở cỡ 40** so với **50/289 ở
cỡ 32**. 50 tin kia dài thật, màn chat cũng ngắt — nhưng nay ngắt đúng cùng chỗ.
Ví dụ `Sợ bị hack lắm nên cậu cứ sao lưu dữ liệu cho chắc ăn nhé`: 1240 px ở cỡ 40
(rớt chữ) → 992 px ở cỡ 32 (một dòng, y màn chat).

> **Đính chính nguồn dữ liệu.** Bản đầu của mục này đo `GenebarkChatMainData` (1194
> tin của app Genebark) và ghi "301/1194 → 0". Sai tập: dòng chat trong BACKLOG đến
> từ các khối `[chat start]` của `ScenarioData`, không phải timeline của app — kiểm
> bằng chính file save (`m_backLogData.name = "Suzuno@Sz_36iii"`, text khớp
> `ScenarioData`). Widget hiển thị thì đúng là một: `genebark.prefab` ›
> `Message_TMP` 1210×80, cỡ 32, spacing 5.

`characterSpacing` 8,5 → 5,0 đi kèm cho khớp khung chat. Đo mực dòng `Anh đã liên
lạc được với Himejima chưa ạ?` trong ảnh backlog: **899 px**, model ở 40/spacing-5
cho 910 px còn ở 40/spacing-8,5 cho 1007 px ⇒ máy vốn đã vẽ như spacing 5; đổi số
này chỉ để asset khớp thực tế.

```
Log_Base       m_fontSize 42 -> 39.5   m_fontSizeMax 42 -> 39.5   sàn 28 giữ
Log_Base_Chat  m_fontSize 40 -> 32     m_fontSizeMax 40 -> 32     charSpacing 8.5 -> 5.0
```

`m_enableAutoSizing = 1` nghĩa là TMP lấy **cỡ lớn nhất còn vừa khung**, nên phải
hạ `m_fontSizeMax` cùng lúc — chỉ đổi `m_fontSize` thì nó phóng về cũ ngay.

### Vì sao KHÔNG đụng chiều cao ô

Bản đầu của tool thu ô `Log_Base` còn `186 × 0,945 = 176` px cho "khớp tỉ lệ ADV",
đã ghi rồi lùi lại. Vô ích: chiều cao không quyết định chỗ ngắt dòng, chỉ quyết
định khi nào TMP thu chữ. Kiểm trên
39.574 tin nhắn: cả 213 lẫn 176 đều ra 0 tin tràn và **cùng 1.169 tin (3,0%) phải
thu chữ** — khác nhau chỉ ở chỗ ô 176 thu sâu tới ~30 còn ô 213 dừng ở ~36,5. Giữ
**213** của `fix_backlog_autosize.py`: chữ to hơn, và hình học chỉ do một tool
nắm.

```powershell
python tools\fix_backlog_adv_scale.py            # đo, so trước/sau
python tools\fix_backlog_adv_scale.py --check    # thoát 1 nếu chưa vá
python tools\fix_backlog_adv_scale.py --apply
```

Đã chạy 29/08/2026, backup `_backup\ui_jp.prebacklogadvscale`. So với bản
`fix_backlog_autosize`: **đúng 2 MonoBehaviour đổi**, rect y nguyên vẹn, và bản vá
`Choice` (ô 240 px + NoWrap) còn nguyên.

> **Hai tool giẫm chân nhau.** `fix_backlog_autosize.py --apply` dựng số từ
> `TARGETS` của chính nó nên sẽ ghi lại cỡ 42/40 và **xoá bản vá này**. Thứ tự
> đúng: chạy nó trước, rồi mới `fix_backlog_adv_scale.py --apply`. `--check` của
> nó từ nay báo "CHƯA VÁ" vì cỡ chữ không còn khớp hằng số của nó — bình thường,
> đừng chạy `--apply` để "chữa".

## Màn PASSWORD thủng chữ (`fix_password_mesh.py`)

Ảnh chụp 06/08/2026 cho thấy dòng nhắc của popup PASSWORD ở màn Title hiện ra là

```
×N Ⱶ ÁY | HẬP N IT KHẨU          (đúng ra: XIN HÃY NHẬP MẬT KHẨU)
```

Không phải lỗi font, không phải chuỗi sai: **tranh đúng, lưới sai**. Toàn bộ màn
này là art trong atlas `sactx-0-1024x2048-ASTC 4x4-PassWord-289d7772` của
`sharedassets16.assets`; bản mod đã vẽ lại tiếng Việt (01/08/2026) nhưng để nguyên
tight-mesh ôm sát nét chữ Nhật gốc, nên nét mới nằm ngoài đường viền cũ bị xén.
Đúng bẫy của màn ARCHIVE và MUSIC.

Năm sprite bị xén, tổng **40.743 px nét**:

| sprite | nội dung | đỉnh | px mất |
|---|---|---|---|
| `UL_pass_b_frame_acce` | 3 dòng báo xác thực **thất bại** | 159 | 27.407 |
| `UL_pass_c_frame_acce` | 3 dòng báo xác thực **thành công** | 154 | 6.373 |
| `UL_pass_c_frame_acce2` | thành công + không có quyền | 152 | 3.405 |
| `UL_pass_a_frame_moji` | dòng nhắc `パスワードを入力してください` | 108 | 2.290 |
| `UL_pass_b_frame_acce2` | thất bại, bản 2 dòng | 128 | 1.268 |

`UL_pass_a_button_ok` (Ⓐ 決定 → XÁC NHẬN) và 4 sprite khung chỉ có 4–68 đỉnh phủ
kín ô nên không sao — trong ảnh chụp nút vẫn hiện đủ chữ, chính chỗ đó làm tưởng
lỗi nằm ở font.

```powershell
python tools\fix_password_mesh.py            # soi + xuất PNG mô phỏng game vẽ ra
python tools\fix_password_mesh.py --check    # thoát 1 nếu còn sprite bị xén
python tools\fix_password_mesh.py --apply
```

Đã chạy 30/08/2026, backup `_backup\sharedassets16.assets.premeshfix`. Script
**không đụng texture** — 2.097.152 byte ASTC giữ nguyên từng byte, 10/10 sprite
crop ra ảnh y hệt, chỉ `m_RD` của 5 sprite đổi thành quad 4 đỉnh. File 2.142.712 →
2.122.008 byte.

> **Cách tìm ra màn này nhanh hơn nhiều.** Danh sách scene nằm ngay trong
> `globalgamemanagers` — grep `Assets/Scene/*.unity` ra 25 đường dẫn, thứ tự đúng
> bằng `level0..level24`. `Title` là **level16** ⇒ `sharedassets16.assets`, mà file
> đó chỉ có 13 object và tên sprite là `UL_pass_*`. Trước khi biết mẹo đó đã quét
> hết `ui_jp` (2.422 object), `resources.assets`, `global-metadata.dat` và mọi
> bundle `StreamingAssets` mà không ra chuỗi nào — vì làm gì có chuỗi.

> **Mô phỏng được đúng cái game vẽ, không cần chạy game.** Rasterise `m_IndexBuffer`
> lên toạ độ pixel của ô (`x*p2u + m_Rect.w*pivot.x − textureRectOffset.x`) rồi nhân
> vào alpha: ảnh ra khớp ảnh chụp Ryujinx từng nét. `Sprite.image` của UnityPy
> **không** đi qua mesh nên nhìn vẫn lành lặn — đừng dùng nó để nghiệm thu.
> `audit()` chạy trên bản gốc 1.0.2 cho 0 px mất ở cả 10 sprite: đó là mốc đối chứng.

## Dòng "đang kiểm tra quyền truy cập" sai thì (`fix_password_access_line.py`)

Thẻ báo xác thực **thành công** (`UL_pass_c_frame_acce`) dịch lệch nghĩa một dòng:

```
JP    アクセス権を確認しました。          (đã xác nhận xong)
cũ    ĐANG KIỂM TRA QUYỀN TRUY CẬP…      (đang diễn ra)
mới   ĐÃ XÁC NHẬN QUYỀN TRUY CẬP.
```

Hai dòng còn lại của thẻ dịch đúng, và `UL_pass_c_frame_acce2` (「アクセス権があり
ません。」→ BẠN KHÔNG CÓ QUYỀN TRUY CẬP) cũng đúng — chỉ một dòng này sai.

### Font vẽ tranh mod KHÔNG có trên máy — nên cắt dán, đừng render

Quét 383 font (`C:\Windows\Fonts`, font người dùng, 7 font `Font` nhúng trong bundle)
chống lại chữ `TRUY` và bốn chữ cái rời `N Q G C`: IoU cao nhất **0,78** và **0,76**.
Khớp thật thì phải > 0,95, nên không font nào trong số đó là font đã dùng. Đặc điểm
để nhận: gần đơn cách — bước chữ **21 px** (riêng `M` 28, `I` và `.` khoảng 7), chữ
`A` **đỉnh phẳng**, `Q` đuôi thẳng, họ vuông kiểu Eurostile/Microgramma.

Vậy nên script không vẽ chữ mới mà **cắt chính nét chữ đã có trong cùng tấm tranh**
rồi xếp lại. Cả ba dòng của thẻ cộng lại đủ mọi chữ cần, trừ đúng một dấu ngã.

| cụm | nguồn | x |
|---|---|---|
| `ĐA` | dòng 2, `ĐANG` | 117–159 |
| `XÁC` | dòng 1 | 115–175 |
| `NHẬN` | dòng 1 | 191–272 |
| `QUYỀN` | dòng 2 | 378–476 |
| `TRUY` | dòng 2 | 491–572 |
| `CẬP.` | dòng 2, `CẬP…` cắt tới **dấu chấm đầu tiên** của dấu ba chấm | 588–655 |

Dấu ngã lấy từ `UL_pass_a_frame_moji` (`XIN HÃY…`) — cùng font nhưng cao chữ hoa 22 px
thay vì 27, nên phải phóng 27/22.

### Ba số đo phải lấy đúng, nếu không lòi đuôi

- **Lề cắt phải của `ĐA` chỉ được 1 px.** `N` của `ĐANG` bắt đầu ngay ở x=162 trong khi
  `A` kết thúc ở 159. Lấy lề 6 px như các cụm khác thì cạnh trái chữ `N` đi theo, và
  dòng hiện ra là `ĐÃI XÁC NHẬN…`. Các cụm khác cách nhau 14–16 px nên lề 6 px an toàn.
- **Khe giữa hai từ 15 hay 16 px là tuỳ cặp chữ**, không phải một hằng số: đo trên cả
  ba dòng gốc thì `N→T` và `M→T` ra 15, còn `C→N`, `A→Q`, `Y→C` ra 16. Script khai
  đúng cặp mình dùng.
- **Dải xoá y 198–252.** Đúng hai hàng 198 và 252 có alpha < 8 trên toàn chiều ngang;
  script assert điều đó trước khi xoá, vì lệch một hàng là cụt dấu của dòng 1 hoặc 3.

Tâm dòng x=393 (đo được ở cả ba dòng gốc), đỉnh chữ hoa y=216, dòng 1 phải dời xuống
54 px khi dán sang chỗ dòng 2. Bề ngang mực 553 → 514 px.

### Phóng chữ thì phải tách hai lớp

Alpha của atlas này **không phải** mặt nạ chữ: nó là **chữ trắng + viền đen**, béo gấp
đôi. Mực nhìn thấy là `RGB × alpha` (nền trong suốt lại có RGB **trắng**, do alpha
bleed). Cho nên:

- soi bố cục thì đo trên `RGB × alpha`, đừng đo trên alpha (đo nhầm thì cao chữ hoa ra
  33 px thay vì 27, và các chữ trong một từ "dính" vào nhau);
- phóng dấu ngã thì phóng **riêng** lớp mực và lớp alpha, mỗi lớp kéo tương phản quanh
  0,5 (hệ số 3,0) cho mép co lại còn ~1 px, rồi dựng lại `RGB = mực / alpha`. Phóng
  thẳng RGBA bằng Lanczos cho ra dấu ngã nhoè hẳn so với dấu sắc bên cạnh.

```powershell
python tools\fix_password_access_line.py            # xuất PNG so trước/sau
python tools\fix_password_access_line.py --check    # thoát 1 nếu chưa vá
python tools\fix_password_access_line.py --apply
```

Đã chạy 30/08/2026, backup `_backup\sharedassets16.assets.preaccessline`. Ghi texture
nên atlas bị mã hoá ASTC lại một lượt: chín sprite không sửa đo được **PSNR 64,7–89,7 dB**
(một cái `inf` vì không đổi byte nào) — script in bảng này sau mỗi lần `--apply`, coi
như biên nhận.


## Tên vật phẩm ở popup "Đã nhận được" lệch chữ hoa với lời thoại (`fix_item_name_case.py`)

`ScriptDialogData` là 18 dòng thông báo ngắn hiện lên khi nhận vật phẩm
("Đã nhận được 『…』"). Nó **không có trên Google Sheet** — không tab nào, không id
nào, tôi đã quét cả 40 262 ô của snapshot (79) để chắc. Nên mọi vòng merge đều bỏ
qua nó, và sai ở đây không bao giờ tự khỏi: sửa trên sheet cũng không xuống được.

`check_term_consistency.py` bắt ra một chỗ:

```
ScenarioData      "Trái tim Thiên sứ"   11 ô lời thoại
ScriptDialogData  "Trái tim thiên sứ"    1 lần, mục id 11
```

Người chơi thấy cả hai cùng lúc — popup nổi ngay trên khung thoại đang gọi vật
phẩm đó là "Trái tim Thiên sứ".

### Vì sao không thay chuỗi thẳng bằng sed

Vế "đúng" không được nhúng cứng. Script tự đếm lại trong `ScenarioData.text[]`:
dạng đúng phải **áp đảo hẳn** dạng sai, không thì nó dừng và bắt người quyết bằng
mắt. Chuyện chữ hoa/thường của một tên riêng là chuyện biên tập, và ở dự án này
đã có tiền lệ đếm đúng số nhưng gắn nhầm đối tượng (xem bài học `火守`).

Ba chốt nữa trước khi ghi: chuỗi sai phải xuất hiện **đúng một lần**, số mục và
danh sách `id` không đổi, và số mục đổi chữ phải đúng bằng số chuỗi trong `DOI`.
Ghi xong đọc lại từ đĩa.

    python tools\fix_item_name_case.py [--apply|--check]


## `--audit-sheet` từng mù với 578 hàng, và từng báo oan một ô suốt mấy vòng

Hai lỗi của chính chế độ audit, phát hiện 02/09/2026 khi người dùng chỉ ra tab
`DictionaryData` chưa bao giờ xuống build.

### Chỉ đọc ba nguồn trong khi sheet có mười hai

`build_values()` — bảng "build đang có gì" — chỉ dựng từ `ScenarioData`,
`Q&AData/qa_title` và chat Genebark. Chín tab bundle json còn lại
(`DictionaryData`, `ShortStoryData`, `TerminalRule/Profile/ControlSkill/HomeAlertData`,
`GenebarkNews/NoteData`) rơi hết vào dòng `id không có ở build: 578` và bị đếm như id
rác, nên **không ô nào trong đó từng được đối chiếu**.

Vòng merge ba chiều vẫn ghi được chúng, nên lỗi ẩn rất kỹ: chỉ những ô SHEET ĐỔI mới
xuống được, còn ô *sheet đúng – build sai – sheet đứng yên* thì không phép nào nhìn
tới. Đo được 17 ô như vậy riêng ở tab từ điển, trong đó có ô lệch hẳn tên mục
(`Gyafun` / `Tắt đài`, `Người nuôi dưỡng` / `Người huấn luyện`) và hai ô mà **chính lời
thoại đang trỏ vào bằng tên khác** — `[dic no=451 text=Độ thiện cảm]` mở ra mục tên
"Độ hữu hảo".

Nay đọc mọi tab trong `FIELD_MAP`: `578 -> 21`.

### Đổi `\n` thành khoảng trắng rồi báo là "khác dấu câu"

`flat_cell()` làm phẳng bằng cách đổi xuống dòng thành **space**. Ô nào build ngắt dòng
ở chỗ sheet không có space là lệch vĩnh viễn:

```
build   '......\nXin lỗi em, tôi quên béng mất…'   -> làm phẳng '...... Xin lỗi em…'
sheet   '......Xin lỗi em, tôi quên béng mất…'                  '......Xin lỗi em…'
```

Sheet **không thể** mang ngắt dòng, nên đây không phải lệch bản dịch. Tôi đã xếp nhầm
nó vào nhóm "dấu câu" hai vòng liền và còn khuyên để nguyên.

Chốt mới: xoá HẲN `\n` của build (không đổi thành space) rồi mới so; khớp thì đếm riêng
vào `bỏ qua ô chỉ khác NGẮT DÒNG`. Cố ý làm hẹp — bỏ khoảng trắng ở **cả hai** bên thì
giấu luôn lỗi thiếu space giữa hai chữ (`xelửa` / `xe lửa`), một lỗi thật. Đo lại trên
snapshot (79) vẫn ra 106 ô lệch, chỉ 1 ô bị bỏ qua.

### Nhánh ghi bundle json dừng giữa chừng mà không báo

Cùng đợt, phép ghi tìm-thay theo **chuỗi giá trị cũ** đã sập: `dic_ruby/id105` đang
trống, `""` khớp 22 chỗ (mọi ruby trống trong asset) nên `SystemExit` — mà `ScenarioData`
đã ghi xong từ trước, để lại trạng thái ghi DỞ: 85 ô thoại vào đĩa, 15 ô từ điển không,
không dòng nào nói là đã mất. Chỉ lộ ra vì đọc lại từ đĩa chứ không tin dòng
"áp được 19 ô".

Nay thay theo **nguyên mục**, khoá bằng `id`/`no` — thứ duy nhất chắc chắn duy nhất
trong asset. Giá trị cũ rỗng hay trùng đều không còn là vấn đề, và bỏ được cả phép gộp
thủ công cho cặp `TerminalHomeAlertData` id17/id18 vốn trùng nhau từng chữ.

## Nhãn `マップ` của điểm lưu ở màn MAP (`fix_map_select_label.py`)

Thẻ SAVE hiện hai dòng: `Title` lấy từ `ChapterData.title` (đã dịch) và dưới nó là
**nhãn của điểm lưu**. Lưu ngay một lựa chọn thường thì dòng đó là `選択肢` — đã đổi
thành `Choice` ở mục "Nhãn `選択肢` của dòng lựa chọn trong BACKLOG". Nhưng màn MAP dùng
lệnh khác, `[select_map]` thay cho `[select]`, và nhãn của nó là một literal **khác**:
`マップ`, chưa ai đụng tới.

Ảnh chụp máy thật `_2026-09-02_00-40-16.png`, save No.038:

```
Title  Ký ức đắng không nuốt trôi
       マップ                        <- đây
```

Save đó là `04_03_03` / `*SOU-03-50`, `m_loadline=410` — đúng dòng `[select_map]` trong
`scriptText_Line`. Trong ScenarioData có **8** lệnh `[select_map]`, tức 8 điểm lưu mang
nhãn này.

### Vì sao chắc chắn là literal, không phải dữ liệu

Chuỗi `マップ` **không có trong bất kỳ dữ liệu nào hiện ra màn hình**. Quét cả cây gốc
`D:\Downloads\UNLOGICAL_v2\Data` (2,9 GB — gồm `globalgamemanagers`, nên loại luôn khả
năng "tên scene") và quét lại các bundle sau khi giải nén bằng UnityPy:

| chỗ | nội dung | có hiện không |
|---|---|---|
| `ui_jp`, `json`, `sharedassets*`, `level*` | 0 lần | — |
| `resources.assets` | 28 lần, trong bản nháp kịch bản cũ (asset chết) | không |
| `scenario01` | 111 lần, **toàn bộ** trong chú thích `;//マップパート` của `scriptText_Line` | không |
| `sprite01` | 1 lần, trong đường dẫn `…/12.マップパート/thumbnail/…` | không |
| `global-metadata.dat` | literal **#14912**, 9 byte | **có** |

Đây là lần thứ ba cùng một bài học (nhãn route SAVE/LOAD, nhãn `選択肢`, giờ là nhãn
`マップ`): dữ liệu đã dịch mà màn hình vẫn ra tiếng Nhật thì **tìm literal**, đừng sửa
lại chỗ vốn đã đúng. Dấu hiệu rẻ nhất vẫn là câu hỏi *"chuỗi này có nằm trong file save
không?"* — lần này câu trả lời còn sắc hơn: file save của chính slot đó ghi
`m_saveText = "Choice"`, tức **không phải** chuỗi đang hiện trên màn hình, nên dòng thứ
hai của thẻ SAVE là do code dựng lại lúc vẽ chứ không đọc từ save.

### Chốt trước khi vá

Bài học `涼乃`: literal chỉ đổi được khi **không dữ liệu nào so sánh với nó**, vì vế dữ
liệu là tag lệnh tiếng Nhật, vĩnh viễn không dịch. Script tự kiểm ba điều và từ chối ghi
nếu sai: chỉ đúng **một** literal mang chuỗi `マップ` (#14912), ScenarioData có **0** tag
`[マップ …]`, và **0** chuỗi hiển thị (`text` / `talkName` / `selText`) chứa `マップ`.

`マップ` 9 byte, `Map` 3 byte — ghi đè tại chỗ, 6 byte dư điền `\x00`, hạ `length` trong
bảng. Kích thước file không đổi, không offset nào dịch.

```powershell
python tools\fix_map_select_label.py            # chạy thử
python tools\fix_map_select_label.py --check    # đã vá chưa
python tools\fix_map_select_label.py --apply
```

Đã chạy 02/09/2026 (backup `_backup\global-metadata.dat.premaplabel`): **10 byte đổi, 0
byte ngoài dự kiến**, 15.224 literal đọc lại không mục nào hỏng. Metadata chỉ đọc lúc
game khởi động — phải **thoát Ryujinx và chạy lại** mới thấy.

## Ô tóm tắt thẻ SAVE/LOAD tràn xuống hàng Date (`fix_save_summary_clip.py`)

Bảng chi tiết bên trái màn SAVE (`level19`, `Load/Normal/SaveDataDetail`) hiện `Title` rồi tới
**đoạn thoại tại điểm lưu** — chính là `m_saveText` trong file save, tức nguyên câu thoại đang
hiện lúc bấm save (kèm cả ngắt dòng cứng của kịch bản).

```
SaveDataDetail          rect 828 x 364
  Text (TMP)  pid 193   stretch, sizeDelta (-90,-200), pos (5,20)  ->  738 x 164
                        margin (6.5, 24, 0, 0)  ->  731,5 x 140 dùng được
                        cỡ 27, charSpacing 8.4, lineSpacing -39, wrap = Normal
                        m_overflowMode = 0 (Overflow)          <- chỗ hỏng
```

Chuỗi mẫu của bản gốc là **3 dòng × 24 chữ toàn rộng**, đúng bằng chỗ trống:

```
pitch      = 27 × (116/58 + (−39)/100)              = 43,47 px
cao 3 dòng = 2 × 43,47 + 27 × (51,04 + 6,96)/58     = 113,9 ≤ 140  ✓
cao 4 dòng = 3 × 43,47 + 27                         = 157,4 >  140  ✗
```

`m_overflowMode = 0` không cắt gì cả: TMP **vẫn vẽ** dòng thứ tư, chỉ là vẽ ra ngoài ô, và nó rơi
thẳng lên hàng `Date / Time / Playtime` (ảnh `_2026-09-02_00-51-50.png`, save No.039). Bản Nhật
không bao giờ chạm chuyện này vì câu thoại đã ngắt sẵn cho khung ADV. Ô này chỉ rộng **731,5 px**
trong khi ô ADV rộng **1280 px**, nên mỗi dòng cứng của kịch bản thường tách làm hai ở đây.

Đo trên `ScenarioData` bằng mô hình `adv_layout` với công thức đúng (`adv·fs/point + cs·fs/100`,
xem memory `unlogical-text-overflow` — dạng cũ `(adv + cs)·fs/point` rộng hơn 1,64 px mỗi ký tự ở ô
này): **5.561 / 39.574 câu thoại = 14,1%** cần hơn 3 dòng, tệ nhất 8 dòng.

| số dòng | câu thoại | |
|---|---|---|
| 1 | 11.047 (27,9%) | |
| 2 | 11.784 (29,8%) | |
| 3 | 11.182 (28,3%) | vừa khít |
| 4 | 4.559 (11,5%) | bị cắt |
| 5–8 | 1.002 (2,5%) | bị cắt |

Sửa: `m_overflowMode` → **Ellipsis (1)**, TMP cắt ở mép ô và đặt dấu lửng vào cuối dòng cuối cùng
còn thấy được. Không đụng cỡ chữ: bật auto-size sẽ cho mỗi save một cỡ khác nhau, mà yêu cầu là
**cắt** chứ không phải thu nhỏ. `--truncate` thì cắt trơn không dấu (cũng đúng 1 byte).

> **Ellipsis chỉ dùng được sau khi vá glyph — chạy `fix_ellipsis_glyph.py` trước.** Lượt đầu
> 02/09/2026 tôi kiểm cmap thấy `…` U+2026 có trong font của ô nên coi như xong; ảnh máy thật cho
> thấy dấu cắt **lơ lửng giữa hàng**. **Có glyph không có nghĩa là đúng kiểu chữ**: đây là font
> Nhật, `…` của nó là dấu lửng toàn rộng ba chấm giữa dòng. TMP thì luôn dùng U+2026 làm dấu cắt và
> không cho đổi ký tự ở mức component — nhưng ký tự cố định *không* có nghĩa là glyph cố định, xem
> mục dưới.

### Ghi vào `level19` mà không `env.file.save()`

`level19` nằm trong danh sách cấm của CLAUDE.md. Script mượn `nodes` TMP của bundle `ui_jp`,
serialize lại **một** object rồi ghi đè đúng dải byte của nó, với ba chốt:

1. serialize lại y nguyên cây vừa đọc phải ra **đúng từng byte** như cũ — nếu type tree mượn
   không khớp thì bước này gãy ngay, trước khi có gì được ghi;
2. bản có sửa phải **cùng độ dài** và lệch **đúng 1 byte**;
3. dải byte cũ phải khớp `byte_start` và **duy nhất** trong file.

```powershell
python tools\fix_save_summary_clip.py             # chạy thử
python tools\fix_save_summary_clip.py --check     # đang ở chế độ nào
python tools\fix_save_summary_clip.py --stats     # đo lại tỉ lệ tràn
python tools\fix_save_summary_clip.py --apply [--truncate]
```

Đã chạy 02/09/2026 (backup `_backup\level19.presaveclip` = bản trước khi vá, `m_overflowMode = 0`).
Diff nhị phân với backup: **đúng 1 byte** (offset 26416, `0` → `1`), kích thước không đổi; đọc lại
từ đĩa vẫn 280 object, mọi trường khác của pid 193 y nguyên.

## `…` U+2026 nằm giữa dòng kiểu Nhật (`fix_ellipsis_glyph.py`)

Ký tự dấu cắt của TMP là cố định, **glyph thì không**. Font asset của ô thoại/ô tóm tắt là
`FOT-NewRodinProN-DB SDF-Dynamic` (`sharedassets7.assets` pid 85) với
`m_AtlasPopulationMode = 1`, `m_GlyphTable` và `m_CharacterTable` **rỗng** — atlas dựng lúc chạy
từ TTF trong `Font` pid 7 của chính file đó, tức một file trong romfs của bản mod. Sửa glyph là
đổi được kiểu chữ, không cần đụng tới code.

Đo trên TTF đang nhúng (unitsPerEm 1000):

```
…  ellipsis   x  84..916   tâm chấm 166 / 499,5 / 834   y 300..464   advance 1000
.  period     x  49..201   tâm chấm 125                 y −17..130   advance  256
```

Bản vá **dời** từng contour, không vẽ lại gì — nên hình dạng chấm giữ nguyên của nhà thiết kế:

```
dời y  −317                    đáy chấm 300 → −17, ngang đáy dấu `.`
dời x  −197 / −118 / −41       tâm chấm → 637 / 381 / 125 = ba dấu `.` liền nhau
advance 1000 → 768 = 3 × 256
```

`python tools\fix_ellipsis_glyph.py --preview` xuất `tools\_preview\ellipsis_baseline.png`, xếp ba
hàng `vậy thôi...` / `vậy thôi…` cũ / `vậy thôi…` mới trên cùng một đường chân chữ để nhìn tận mắt.

**Phạm vi ảnh hưởng nhỏ hơn tưởng tượng.** Trong `ScenarioData` còn **53/39.574** câu thoại dùng
`…`, nhưng 52 câu nằm ở `scenarioID` 3/4/5/8 — route 1 chương 0, tức kịch bản thử của nhà phát
triển, không bao giờ chạy; **chỉ 1 câu sống** (scenarioID 90). Bundle `json` **0** chỗ. Bản dịch
viết dấu lửng bằng ba chấm ASCII (memory `unlogical-punctuation-conventions`), nên hạ chấm xuống
chân chữ là **thống nhất hơn** với phần chữ còn lại. Bản sao TTF thứ hai nằm trong `ui_jp` (cùng
3.837.584 byte) — không đụng, các widget đọc bản đó gần như không bao giờ hiện `…`.

### Chốt

`fontTools` lưu **no-op** ra đúng từng byte như bản gốc (đã kiểm), nên phần chênh −23.612 byte chỉ
là bảng `glyf` được nén lại chặt hơn, không phải nội dung. Trước khi ghi, script so **từng glyph
một** giữa TTF cũ và mới: 15.649 glyph, 10.178 mã `cmap`, chỉ `ellipsis` đổi — contour, cờ điểm,
mã hint và `hmtx` của mọi glyph khác đều khớp. Sau khi ghi, đọc lại `sharedassets7.assets`: 85
object, **chỉ pid 7 đổi kích thước** (3.837.726 → 3.814.114), 0 object rỗng.

```powershell
python tools\fix_ellipsis_glyph.py             # chạy thử + đối chiếu từng glyph
python tools\fix_ellipsis_glyph.py --check     # đã hạ chấm chưa
python tools\fix_ellipsis_glyph.py --preview   # ảnh so `...` với `…`
python tools\fix_ellipsis_glyph.py --apply
```

Đã chạy 02/09/2026, backup `_backup\sharedassets7.assets.preellipsis`. Lùi lại = chép backup đè
lên `romfs\Data\sharedassets7.assets`.

## `[Error]` dính liền tiêu đề ending (`fix_error_prefix_space.py`)

Ba mục đầu của Ending List mang tiền tố `[Error]` trong `SceneReplayData` (bundle `json`):

```
#recollection_02   [Error]自己犠牲のペガサス     ->  [Error]Pegasus của sự hy sinh
#recollection_03   [Error]夢想家のグリフォン     ->  [Error]Griffin của kẻ mộng mơ
#recollection_04   [Error]合理主義のケルベロス   ->  [Error]Cerberus của chủ nghĩa duy lý
```

Bản gốc viết liền vì sau `]` là chữ Nhật — tiếng Nhật vốn không có dấu cách nên `]自` vẫn tách
bạch. Bản dịch thì sau `]` là chữ Latin, `]P` dính thành một cụm. Chèn đúng **một** dấu cách sau
`]`, không đụng ký tự nào khác (script khẳng định `len(sau) == len(trước) + số ô đổi`).

`[Error]` ở đây **là chữ hiển thị, không phải thẻ lệnh**: TMP vẽ thẳng `title.jp`, không đi qua bộ
phân tích `[...]` của kịch bản — ảnh chụp máy thật (`_2026-09-02_12-15-50.png`) hiện nguyên văn
`[Error]Pegasus…`. Nên đây là chuỗi được phép sửa, khác với `[dic no=N]` hay `[主人公]`.

**Phải sửa hai chỗ, nếu không thẻ và danh sách lệch nhau một dấu cách.** Thẻ THE END sau mỗi BAD
END *vẽ lại chính chuỗi này thành tranh* (xem mục "Thẻ THE END"), và cả ba ending 002/003/004 đều
có thẻ trong `cg_end`. `fix_endcard_title.py` luôn dựng lại từ bản gốc 1.0.2 nên chạy lại là đủ:

```powershell
python tools\fix_error_prefix_space.py            # chạy thử
python tools\fix_error_prefix_space.py --apply
python tools\fix_endcard_title.py --apply         # BẮT BUỘC chạy kèm
```

Kiểm sau khi ghi: dựng lại `cg_end` rồi so từng texture với bản trước — **32 ảnh, đúng 3 ảnh đổi**
(`a_bad_002_002/003/004`, ~8.700–10.500 px mỗi ảnh), 29 ảnh còn lại trùng khít từng pixel, tức
vòng dựng lại không kéo theo sai khác nào khác. Thẻ vẫn nằm trong lề an toàn: kiểu `a_bad_002`
cho phép x 412..1508, mục dài nhất (`#004`) chiếm 447..1472.

Hàng Ending List không cần đo lại: cả ba tiêu đề vốn đã dài hơn khung 502 px (607/599/746 px ở cỡ
32) nên đang chạy chữ bằng `AutoScrollText`; thêm một dấu cách chỉ đẩy lên 620/613/759 px, vẫn cùng
một trạng thái.

Chạy lại vô hại: `fixed()` chuẩn hoá về đúng một dấu cách nên lần hai báo `0/38`.

Đã chạy 02/09/2026, backup `_backup\json.preerrorspace` và `_backup\cg_end.endcard` (bản gốc
1.0.2). `manifest.json` cập nhật cùng lượt cho cả `json` và `cg_end`.
