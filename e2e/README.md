# e2e — kiểm thử bản patch UNLOGICAL trên Ryujinx

Chạy game thật trong Ryujinx, tự điều hướng tới một màn hình, chụp ảnh bằng hotkey screenshot
của Ryujinx (`F8`), rồi kiểm tra ảnh + dữ liệu đã đóng gói trong `romfs`.

Sinh ra để verify fix màn **SECTION SELECT**, nhưng khung sườn dùng được cho màn khác.

## Yêu cầu

| thứ | giá trị |
|---|---|
| Ryujinx | `D:\Apps\Ryujinx\Ryujinx.exe` (1.3.3) |
| game | `D:\Downloads\UNLOGICAL\UNLOGICAL [010068501FF9A000].xci` |
| mod | junction `%APPDATA%\Ryujinx\mods\contents\010068501ff9a000\vn-translation\romfs` → `D:\Downloads\010068501ff9a000\romfs` |
| python | `UnityPy`, `Pillow` |

Sửa đường dẫn ở đầu `run.ps1` nếu máy khác.

> Ryujinx **có** nhận đường dẫn game qua CLI, nhưng nếu sai đường dẫn nó chỉ ghi
> `Couldn't find any application in ...` vào log rồi đứng ở game list — không báo gì trên UI.
> `run.ps1` kiểm tra file tồn tại trước khi chạy vì lý do đó.

## Dùng

```powershell
# đầy đủ: khởi động game, điều hướng, chụp, kiểm tra
.\run.ps1 -Case section-select

# game đang mở và đã ở đúng màn hình rồi, chỉ chụp + kiểm tra
.\run.ps1 -Case section-select -SkipLaunch -SkipNavigate

# chỉ kiểm tra dữ liệu, không cần chạy game
python checks\check_chapterdata.py
```

Artifact ghi vào `out\<yyyy-MM-dd_HH-mm-ss>\`: các ảnh chụp theo từng bước + `report.txt`.

## Cấu trúc

```
run.ps1                       điều phối: launch → navigate → capture → check
lib\input.ps1                 focus cửa sổ + gửi scancode + chụp F8
checks\identify.py            ảnh này là màn hình nào? (title / menu / section-select / other)
checks\check_chapterdata.py   kiểm tra tĩnh ChapterData trong bundle (không cần game)
checks\check_scripts.py       chuỗi lệnh + nhãn scene của 143 script phải khớp bản gốc
checks\measure_shot.py        đo pitch dòng, font size, độ rộng wrap, số dòng bị cắt
```

## Điều hướng hoạt động thế nào

Không dùng sleep cố định rồi hy vọng. Mỗi bước: chụp → `identify.py` → xử lý theo state. Lý do:
thời gian boot và độ dài đoạn phim mở đầu thay đổi theo lần chạy, và phím gửi quá sớm sẽ bị mất.

Trình tự boot thật (bấm sai chỗ là lạc luôn):

| state | xử lý |
|---|---|
| `loading` / `busy` | chỉ chờ, **không bấm gì** |
| `notice` | ATTENTION rồi CAUTION — mỗi màn **một** lần A, và bấm `+` **ngay sau đó** vì phim mở đầu chạy liền |
| `other` | phim mở đầu → `+` |
| `title` | A |
| `menu` | đọc `menu_cursor.py` rồi đi đúng số bước tới `section` (index 2), sau đó A |

Ba cái bẫy đã dính phải, đừng lặp lại:

- **`ALT` bị gõ trước mỗi phím.** `Focus` gõ ALT để giành foreground, mà `Send-RyuKeys` gọi
  `Focus` mỗi lần ⇒ game nhận ALT ngay trước mỗi phím và nuốt bớt: gửi `DOWN,DOWN` từ NEW GAME
  chỉ nhích tới LOAD. Nay `Focus` thoát sớm nếu cửa sổ đã foreground.
- **Có hai màn loading khác nhau.** Một cái cửa hồng ở giữa, một cái nền navy với cửa ở góc dưới
  phải. Chỉ quét vùng giữa ⇒ cái thứ hai bị coi là "màn tối không có cửa" và rơi vào nhánh `menu`,
  runner bấm `DOWN` suốt. Nay quét cửa trên toàn khung.
- **ATTENTION/CAUTION nền trắng**, không phải nền đen như tưởng. Nhận diện bằng dải banner navy
  giữa trên chứa chữ hồng.
- `menu_cursor.py` để `sys.stdout = TextIOWrapper(...)` trong `__main__`: `identify.py` import nó,
  wrapper thứ hai trên cùng buffer sẽ đóng stdout của caller.

Mapping phím lấy từ `%APPDATA%\Ryujinx\Config.json` (`input_config`, backend `WindowKeyboard`):
A=`Z`, B=`X`, D-pad = phím mũi tên, screenshot = `F8`.

`SetForegroundWindow` một mình **không** đủ — Windows chặn tiến trình background giành
foreground, nên `lib\input.ps1` gõ nhẹ ALT + `AttachThreadInput` + fallback
`SwitchToThisWindow`. Không có focus thì `F8` không tạo file và phím không tới game.

## Những gì đã đo được về màn SECTION SELECT

Ghi lại để đỡ phải đo lại:

- Khung synopsis `ChapterSelect/Story/SynopsisTitle/Mask` = **620×474**, `MainText` font 31.25,
  `m_lineSpacing` 33, `m_characterSpacing` 5.8, font `FOT-NewRodinProN-DB` (pointSize 58,
  faceInfo lineHeight 116).
- Bước dòng = `fontSize × (116/58 + 33/100)` = **2.33 × fontSize**. `m_lineSpacing` là **phần
  trăm của fontSize**, không phải đơn vị font. Kiểm chứng: 31.25 → 72.8px, đo được 72.75px.
- Khung hiện được **7 dòng**; dòng thứ 8 bị mask cắt.
- **Code game tự ngắt dòng ở đúng 18 ký tự và tự đặt font size.** Không phải TMP:
  đã thử `m_TextWrappingMode=1` + `m_enableAutoSizing` + tag `<size=..>`, và với ui_jp ở
  nguyên stock thì render vẫn ngắt mỗi 18 ký tự — kể cả **đếm luôn ký tự của tag rich-text**
  (`<size=21.5>` dài 11 + `Nhân vậ` 7 = 18). Nên chỉnh component TMP hay chèn tag đều vô ích;
  dữ liệu phải tuân theo quy ước 18 ký tự/dòng.
- Hệ quả: khung chứa được **7 × 18 = 126 ký tự**. Synopsis tiếng Việt hiện dài 127–496 ký tự
  ⇒ **mọi mục đều bị cắt bớt**. Đây là vấn đề có từ trước (thấy ngay trong ảnh đầu tiên user
  gửi), muốn sửa hẳn phải patch code IL2CPP hoặc rút ngắn bản dịch.
- Danh sách chương `ChapterSelectButton` = 439×57, lề trái 86, font 50 ⇒ **một dòng**, chỉ vừa
  ~353px. Nhãn dài hơn `SECTION 2－A` sẽ xuống dòng và đè lên mục kế tiếp.

## Màn CHAT Genebark — đo bề rộng dòng trên ảnh thật

```powershell
python e2e\checks\measure_chat.py                # tu lay anh Ryujinx moi nhat
python e2e\checks\measure_chat.py <anh.png>
```

Tự đo tỉ lệ canvas→màn hình từ vạch `UnderLine` (prefab 1388 px) trên chính ảnh đưa vào,
rồi quy bề rộng mực từng dòng về canvas px để so với khung `Message_TMP` **1210**. Kiểm
trên ảnh `_2026-08-14_21-39-21.png`: 6 vạch ngăn, dài nhất 1283 px ⇒ tỉ lệ 0,9244; 16
dòng, 0 dòng vượt, dòng dài nhất 799 canvas px — khớp đúng model advance của
`tools\fix_chat_wrap.py`. Bề rộng **mực** luôn nhỏ hơn **advance** một chút (side bearing
+ advance ký tự cuối), đo được lệch trung bình 1,0%; dưới ~2% coi là khớp.

**Runner chưa điều hướng tới được màn này.** `run.ps1` chỉ có case `section-select`; màn
chat cần load save rồi vào Terminal → Genebark → CHAT. Cách dùng hiện tại: tự đưa game
tới màn chat, rồi chạy `measure_chat.py`.

## Ba cái bẫy điều khiển input (28/08/2026)

Mất khá nhiều lượt mới ra, ghi lại kèm triệu chứng để nhận ngay:

- **Cửa sổ phải được CLICK CHUỘT một lần mới nhận input của guest.** Triệu chứng rất đặc
  trưng: `SetForegroundWindow` báo thành công, `F8` chụp được ảnh (đó là hotkey của host),
  **mũi tên hoạt động mà phím chữ thì không**. Sau một `SendInput` click giữa cửa sổ thì
  D-pad chạy ngay (đo được: `DOWN`×3 đưa highlight từ `Load` xuống đúng `Option`).
- **Nhả modifier trước khi gửi phím chữ.** `Focus-Ryu` gõ ALT để giành foreground; nếu
  keyup của ALT bị mất thì mọi phím sau đó thành ALT+phím và game bỏ qua. `GetAsyncKeyState`
  có thể báo ALT **không** nhấn mà vẫn bị — nên cứ gửi keyup cho `ALT/SHIFT/CTRL/WIN`
  (cả bản trái/phải) trước mỗi loạt phím. Sau khi làm vậy, `Z` (nút A) mới vào.
- **Title screen có timeout về vòng attract.** Nó tự quay lại phim demo/slide giới thiệu
  nhân vật sau vài giây, và **đổi cả theme** (bản hồng, bản nền đen pixel). Vòng
  "chụp → nhận diện → bấm" mất ~3s mỗi bước nên phím tới lúc menu đã biến mất; dễ tưởng
  là "phím không tới" trong khi thật ra state đã đổi. Gửi cả loạt phím trong **một** script
  với `Gap` ngắn (250–400ms), chụp một lần ở cuối.

Kéo theo: **`identify.py` và `menu_cursor.py` không dùng được ở title screen.**
`identify.py` gọi cả hai theme title là `other`; `menu_cursor.py` đếm pixel trắng nên trên
bản title trắng toát nó báo `LOAD=2676` từ chính cái nền, tức "đọc được menu" trong khi màn
hình chỉ có chữ `Press Any Button`. Ở title thì soi bằng mắt, hoặc dò dải highlight (nền
tím đậm + chữ xanh nhạt) trong vùng x 870..1060 — và nhớ là bản nền đen có màu khác.
