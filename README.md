# UNLOGICAL — Bản Patch Việt Hóa

Bản patch dịch thuật do fan thực hiện dành cho tựa game visual novel **UNLOGICAL** trên Nintendo Switch (Title ID: `010068501ff9a000`).

* **Cốt truyện, hội thoại và lựa chọn** — Tiếng Việt
* **UI, menu và văn bản hệ thống** — Tiếng Anh

Repository này **chỉ chứa các file game đã được bản dịch sửa đổi**. Đây không phải là bản sao của game. Bạn phải tự sở hữu và tự trích xuất (dump) file game gốc của riêng mình.

---

## Yêu cầu

|  |  |
| --- | --- |
| Phiên bản game | **v1.0.2** |
| Title ID | `010068501ff9a000` |
| Đã kiểm tra trên | Ryujinx (cũng hoạt động trên máy Switch gốc qua Atmosphère LayeredFS) |

Bản patch được dựng trên nền phiên bản v1.0.2. Việc áp dụng cho các phiên bản game khác có thể gây văng game (crash) hoặc lỗi hiển thị văn bản.

---

## Hướng dẫn cài đặt

### 1. Tải file phông chữ dung lượng lớn

File `StreamingAssets/font/font_jp` (270 MB) có dung lượng quá lớn đối với một kho lưu trữ Git, nên được phát hành dưới dạng **file đính kèm phiên bản (release asset)**. Hãy tải nó từ trang [Releases](https://www.google.com/search?q=../../releases).

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
    level10  level19  level20  level22
    resources.assets
    sharedassets7.assets   sharedassets9.assets   sharedassets10.assets
    sharedassets13.assets  sharedassets16.assets  sharedassets19.assets
    sharedassets22.assets

```

### 3. Cấu hình Ryujinx

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

Những phần này hiện vẫn là tiếng Nhật và đang được theo dõi để xử lý tiếp:

* 21 tên nhân vật ở màn hình Hồ sơ (`TerminalProfileData.name`)
* 17 nhãn chỉnh âm lượng giọng nói từng nhân vật trong phần Cài đặt âm thanh
* 5 tên linh hồn trong danh sách Amity
* 3 dòng thoại kịch bản có chứa ký tự `っ` bị dư

---

## Kiểm tra tính toàn vẹn của file

File `manifest.json` liệt kê mọi file được phát hành kèm theo dung lượng và mã MD5. Để kiểm tra một bản sao:

```powershell
Get-FileHash -Algorithm MD5 romfs\Data\StreamingAssets\json\json

```

---

## Tuyên bố pháp lý

Đây là bản dịch phi thương mại, không chính thức do người hâm mộ thực hiện. Bản patch này phân phối các file dữ liệu game đã qua chỉnh sửa và sẽ không hoạt động nếu không có bản game UNLOGICAL hợp pháp. Mọi bản quyền đối với trò chơi gốc, kịch bản và hình ảnh thuộc về các chủ sở hữu tương ứng. Dự án không liên kết hoặc nhận được sự ủy quyền từ nhà phát hành. Nếu bên giữ bản quyền có yêu cầu, repository này sẽ bị gỡ bỏ.
