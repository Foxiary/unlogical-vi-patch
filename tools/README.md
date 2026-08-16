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

## Thuật ngữ trong bundle `json`

`python tools\json_term.py <TênAsset> "<cũ>" "<mới>" [--apply]` — thay một chuỗi
trong một TextAsset của `StreamingAssets\json\json`, sửa thẳng trên văn bản JSON
nên không có gì khác bị đổi theo. In ra từng trường thay đổi trước khi ghi.

Bảy file đã dịch trong bundle này **không có tab nào trên sheet**, nên chỉ sửa
được ở đây: `DictionaryData`, `ChapterData`, `SceneReplayData`,
`ScriptDialogData`, `MusicData`, `MapData`, `AnimationTextData`.

Đã dùng: `DictionaryData` mục `no=212` "Thiên sứ tập sự" → **"Thiên thần tập sự"**
(16/08/2026, backup `_backup\json.prespiritterm`).

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
