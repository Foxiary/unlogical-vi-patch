# UNLOGICAL — Bản Patch Việt Hóa

Bản patch dịch thuật do fan thực hiện dành cho tựa game visual novel **UNLOGICAL** trên Nintendo Switch (Title ID: `010068501ff9a000`).

* **Cốt truyện, hội thoại và lựa chọn** — Tiếng Việt
* **UI, menu và văn bản hệ thống** — Tiếng Anh

Repository này **chỉ chứa các file game đã được bản dịch sửa đổi**. Đây không phải là bản sao của game. Bạn phải tự sở hữu và tự trích xuất (dump) file game gốc của riêng mình.

---

## Yêu cầu

|  |  |
| --- | --- |
| Phiên bản game | **v1.0.2** — bắt buộc, xem bên dưới |
| Mã bản cập nhật | `v131072` |
| Title ID | `010068501ff9a000` |
| Đã kiểm tra trên | Ryujinx (cũng hoạt động trên máy Switch gốc qua Atmosphère LayeredFS) |

> ### ⚠ Phải đúng v1.0.2, không phải "nên"
>
> Cài lên **1.0.0 hoặc 1.0.1 thì game văng ngay khi khởi động**, kèm thông báo
> *"The software was closed because an error occurred."* Đây không phải lỗi cài đặt sai — bản patch
> gắn chặt với phiên bản:
>
> * `global-metadata.dat` được vá **tại chỗ theo offset**. Offset của bản 1.0.1 khác 1.0.2, nên
>   ghi vào là hỏng bảng chuỗi của game.
> * 11 file `.assets` vẫn trỏ vào `.resS` của game gốc bằng **địa chỉ tuyệt đối**. Bản patch cố ý
>   không kèm `.resS` (LayeredFS lấy từ máy bạn) — điều đó chỉ đúng khi game gốc **cùng phiên bản**.
>
> Đo trên hai bản dump 1.0.0 và 1.0.2: **24 trong 27 file** bản patch thay thế đều khác nhau giữa
> hai phiên bản. Chỉ 3 file giống nhau, nên **không có cách cài một phần cho an toàn**.

### Kiểm tra máy đang ở phiên bản nào

**Trên Switch** — mở DBI, chọn game, xem hai dòng:

```
Version : 1.0.2
Update  : Version 2 [v131072]
```

Nếu thấy `1.0.1` / `[v65536]` thì cài file update `[v131072]` đè lên. Không cần gỡ gì, không mất save.

**Trên Ryujinx** — chuột phải vào game → **Manage Title Updates**, chọn bản `v131072`.

---

## Cài đặt nhanh (khuyến nghị)

Chỉ cần **một file duy nhất** — không cần tải cả repository.

1. Tải `unlogical-vi-patch-v1.2.1-romfs.zip` từ trang [Releases](../../releases).
2. Mở thư mục mod của Ryujinx (chuột phải vào game → **Open Mods Directory**, hoặc dán đường dẫn `%APPDATA%\Ryujinx\mods\contents\010068501ff9a000\` vào Explorer).
3. Giải nén file zip **trực tiếp vào thư mục đó**, sao cho có đủ **cả hai** thư mục:
   * `...\contents\010068501ff9a000\vn-translation\romfs\Data\...`
   * `...\contents\010068501ff9a000\vn-translation\exefs\669EA2FE0282C2C0EFEA4DA183419FB7.ips`
4. Khởi động game. LayeredFS tự nhận diện, không cần bật/tắt gì thêm.

> **Phải có đủ cả `romfs` lẫn `exefs`.** File `.ips` chỉ nặng 19 byte nhưng nó tắt luật ngắt dòng cứng ở màn chọn chương. Nếu chỉ chép `romfs`, phần tóm tắt chương sẽ bị cắt dòng giữa từ, mỗi 18 ký tự một lần. Đây cũng là lý do bản v1.1 phát hành lần đầu bị thiếu và đã được thay thế.

File zip chỉ chứa dữ liệu game đã sửa đổi, không kèm README hay tài liệu.

---

## Cài đặt thủ công (dành cho người rành kỹ thuật)

### 1. Tải file phông chữ dung lượng lớn

File `StreamingAssets/font/font_jp` (270 MB) có dung lượng quá lớn đối với một kho lưu trữ Git, nên được phát hành dưới dạng **file đính kèm phiên bản (release asset)**. Hãy tải nó từ trang [Releases](../../releases).

### 2. Sắp xếp thư mục mod

Sắp xếp các file sao cho đúng chuẩn cấu trúc sau:

```text
<mods>/contents/010068501ff9a000/vn-translation/romfs/Data/
    Managed/Metadata/global-metadata.dat
    StreamingAssets/anim/anim01
    StreamingAssets/font/font_jp          <- Lấy từ trang Releases
    StreamingAssets/json/json
    StreamingAssets/movie/movie_jp_02
    StreamingAssets/scenario/scenario01
    StreamingAssets/scene/scene_jp
    StreamingAssets/ui/ui_jp
    level10  level17  level19  level20  level22
    resources.assets
    sharedassets5.assets   sharedassets6.assets   sharedassets7.assets
    sharedassets9.assets   sharedassets10.assets  sharedassets11.assets
    sharedassets13.assets  sharedassets16.assets  sharedassets17.assets
    sharedassets19.assets  sharedassets21.assets  sharedassets22.assets

<mods>/contents/010068501ff9a000/vn-translation/exefs/
    669EA2FE0282C2C0EFEA4DA183419FB7.ips

```

### 3. Bản vá code (19 byte, bắt buộc)

File `.ips` ở trên là bản vá IPS32 tác động lên chính executable của game, không phải dữ liệu. Nó đổi `Chapter.get_DefaultMaxCharsPerLine` từ `18` thành `40`, tức **nới luật ngắt dòng cứng** ở phần tóm tắt màn chọn chương, để engine thôi cắt lại những dòng mà dữ liệu đã ngắt sẵn theo từ.

Cố ý **không** đặt về `0`: cùng hàm đó đếm số dòng nó ngắt ra để phân trang thanh cuộn, nên tắt hẳn thì game chỉ thấy một dòng, một trang, và thanh cuộn chết.

Tên file **chính là build ID** của bản game, nên nó chỉ áp dụng đúng cho **v1.0.2**. Cài lên bản update khác thì Ryujinx sẽ bỏ qua (không khớp build ID) và bạn quay lại tình trạng ngắt mỗi 18 ký tự.

Gỡ bản vá = xóa đúng một file này. Nhưng nếu gỡ thì nên dùng lại `romfs` của v1.0, vì dữ liệu tóm tắt từ v1.1 trở đi đã bỏ hết ngắt dòng thủ công.

Trên máy Switch chạy Atmosphère, file này đặt ở `atmosphere/exefs_patches/<tên bất kỳ>/`.

### 4. Cấu hình Ryujinx

Thư mục chứa mod là:

```text
%APPDATA%\Ryujinx\mods\contents\010068501ff9a000\

```

Nếu chưa chắc chắn, bạn hãy nhấp chuột phải vào game → chọn **Open Mods Directory**. Sau đó khởi động game; không cần bật/tắt gì thêm vì LayeredFS sẽ tự động nhận diện các file.

---

## Các phần đã được dịch

**Cốt truyện**

* 132/140 kịch bản scenario (toàn bộ hội thoại, lời dẫn và các lựa chọn)
* 8 kịch bản chưa dịch còn lại là tài liệu thử nghiệm của nhà phát triển, không bao giờ xuất hiện trong game

Terminal (Thiết bị)

* Toàn bộ 21 trang Quy tắc (điều kiện hoàn thành, nội dung trò chơi, vai trò người vận hành)
* Toàn bộ 86 thông báo cảnh báo ở Trang chủ
* Phiên âm La-tinh (romanisation) cho tên trong Hồ sơ

**Từ điển / Lưu trữ**

* Toàn bộ 80 mục từ điển
* Các nhãn phân loại Lưu trữ (hình ảnh vẽ sẵn)

**Hình ảnh có chèn văn bản**

* Màn hình Nhập tên
* Các nhãn trang Lưu trữ và nút bấm gợi ý
* Biểu tượng nút bấm trong cài đặt phím (Key-config)
* Nút bấm gợi ý trong Xem lại nhật ký hội thoại (Backlog)

## Các phần tồn đọng đã biết

Chỉ còn đúng hai cái tên chưa có cách viết La-tinh:

* `小住祥太` và `芳谷尚紀` — hai người chơi phụ, xuất hiện ở hai thông báo Trang chủ. Cả game lẫn bản dịch đều không ở đâu ghi cách đọc của họ, nên chưa chốt được.

Các mục từng nằm trong danh sách này đã xong: tên ở màn Hồ sơ, 5 tên linh hồn trong danh sách Amity, ký hiệu `小`/`大` ở hai đầu thanh trượt âm lượng (nay là `−`/`+`), 17 nhãn âm lượng giọng nhân vật, và 3 dòng thoại dư ký tự `っ`.

Còn bốn tên vẫn hiện tiếng Nhật ở **dòng INFO đáy tab SOUND** (`蛍`, `栞`, `恭介`, `光希`). Chúng là string literal trong `global-metadata.dat` chứ không phải dữ liệu, mà dạng La-tinh lại dài hơn số byte gốc nên chưa ghi đè tại chỗ được.

> **Tab SOUND hiển thị tên nhân vật ở hai nơi**, và rất dễ chỉ sửa một. Chữ trên từng dải thanh trượt là **hình vẽ sẵn** trong sprite `UL_option_sound_menu_ch_*`; còn dòng INFO đáy màn ghép `ConfigVolumeData.label` với `SystemTextData` id 71 (`"'s volume settings"`). Sửa xong tranh mà quên `label` thì màn hình hiện `MIYABI` ở dải nhưng `雅火's volume settings` ở dưới.

Ngoài ra, một vấn đề về trình bày (không phải tiếng Nhật sót lại):

* **Ngắt dòng thủ công bị mất trong quá trình dịch.** Bản gốc có 22.208 đoạn văn bản chứa ngắt dòng cứng. Phần **màn hình chat Genebark đã được khôi phục** — 135 tin nhắn nay xuống dòng đúng chỗ bản gốc ngắt, giống hệt bản Nhật. Phần lời dẫn và hội thoại ADV thì vẫn còn gộp: hiện có 552 đoạn giữ ngắt dòng cứng trên tổng 39.572 đoạn có nội dung. Chữ vẫn tự động xuống dòng nên không mất nội dung, chỉ là nhịp đọc chưa giống bản gốc.

---

## Kiểm tra tính toàn vẹn của file

File `manifest.json` liệt kê mọi file được phát hành kèm theo dung lượng và mã MD5. Để kiểm tra một bản sao:

```powershell
Get-FileHash -Algorithm MD5 romfs\Data\StreamingAssets\json\json

```

---

## Tài liệu kỹ thuật

Ghi chú kỹ thuật về cách bản patch được thực hiện — vị trí lưu trữ văn bản trong game, cách engine hiển thị chúng, và các lỗi thường gặp: xem thư mục [`docs/`](docs/).

| | |
| --- | --- |
| [Bố cục dữ liệu](docs/01-data-layout.md) | File nào chứa văn bản gì, và quy tắc khe JP |
| [Hiển thị văn bản](docs/02-text-rendering.md) | Xuống dòng, tràn khung, tự động co chữ, quy tắc chỉnh sửa an toàn |
| [Màn hình hình ảnh](docs/03-baked-art.md) | Văn bản UI được vẽ sẵn vào sprite atlas |
| [Đóng gói lại với UnityPy](docs/04-repacking.md) | Mã hóa texture, đóng gói bundle, mesh của sprite |
| [Tên nhân vật chính](docs/05-protagonist-name.md) | Chuỗi IL2CPP và dữ liệu save |

## Công cụ dựng bản patch

Các script đã dùng để tạo ra những file trong `romfs/`, cùng bộ kiểm thử chạy game thật:

| | |
| --- | --- |
| [`tools/`](tools/) | Script vá theo từng việc — bố cục hộp thoại ADV, ngắt dòng và cú pháp ruby, nhãn section, nút bấm gợi ý, tên người chơi trong file save |
| [`e2e/`](e2e/) | Chạy game trong Ryujinx bằng scancode, nhận diện màn hình qua pixel; kèm hai phép kiểm tra tĩnh đối chiếu với bản gốc |

`e2e\checks\check_scripts.py` so chuỗi lệnh và nhãn scene của cả 143 kịch bản với bản gốc — nó đã bắt được một lệnh `[env カメラ移動]` bị mất khi dịch. `check_chapterdata.py` kiểm tra dữ liệu màn chọn chương. **Chạy cả hai sau mỗi lần ghi vào `scenario01`.**

Các script trong `tools/` là công cụ dùng một lần trong quá trình dựng patch, không phải phần mềm hoàn chỉnh: đường dẫn được ghi thẳng trong file và trỏ tới máy của người dựng, nên phải sửa lại trước khi chạy.

---

## Tuyên bố pháp lý

Đây là bản dịch phi thương mại, không chính thức do người hâm mộ thực hiện. Bản patch này phân phối các file dữ liệu game đã qua chỉnh sửa và sẽ không hoạt động nếu không có bản game UNLOGICAL hợp pháp. Mọi bản quyền đối với trò chơi gốc, kịch bản và hình ảnh thuộc về các chủ sở hữu tương ứng. Dự án không liên kết hoặc nhận được sự ủy quyền từ nhà phát hành. Nếu bên giữ bản quyền có yêu cầu, repository này sẽ bị gỡ bỏ.
