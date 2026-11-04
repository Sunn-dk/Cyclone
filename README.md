# Cyclone 3.2

## Báo cáo và dữ liệu để chuẩn bị nộp

Cập nhật ngày 04/11/2026. Tải toàn bộ bằng **Code → Download ZIP**, hoặc clone repository.

- [Báo cáo PDF hoàn chỉnh](docs/bao-cao/BAO_CAO_CYCLONE_3_2_HOAN_CHINH.pdf), [bản Word](docs/bao-cao/BAO_CAO_CYCLONE_3_2_HOAN_CHINH.docx).
- [Số liệu và minh chứng máy ảo](docs/ket-qua-may-ao/README.md): bảng CSV, biểu đồ và ZIP dữ liệu gốc của đợt 03/11/2026 dùng trong báo cáo.
- [APK benchmark để demo/đo](apk/Cyclone-3.2.apk), [APK debug](apk/Cyclone-3.2-debug.apk).
- [Tái tạo trước/sau A và D](docs/D5_TAI_TAO_TRUOC_SAU.md); hướng dẫn build và chạy ở các mục dưới.

Mã Kotlin và APK vẫn là phiên bản 3.2/code5. Lần cập nhật này bổ sung tài liệu, minh chứng và công cụ kiểm thử; không tạo số đo mới. Video không nằm trong bản cập nhật này.

Ứng dụng Android viết bằng **Kotlin/XML/RecyclerView** để xem ảnh và thử nghiệm tối ưu tải ảnh. Có danh sách100/500/1.000 mục, màn chi tiết, placeholder/ảnh lỗi, cache RAM/đĩa và cấu hình trước/sau tối ưu.

## Chạy ngay bằng APK

1. Tải [apk/Cyclone-3.2.apk](apk/Cyclone-3.2.apk), chép vào điện thoại Android8.0/API26 trở lên và cài đặt. Đây là APK benchmark dùng chạy demo; tên ứng dụng là **Cyclone**.
2. Mở Cyclone, dùng Internet để tải ảnh Picsum. Mặc định D/100/JPEG. Nếu đã cài bản cũ, vào **Thử nghiệm** đặt nguồn `https://picsum.photos`, JPEG, độ trễ0 và tắt chèn lỗi; nhấn **Áp dụng nguồn ảnh** rồi quay lại.
3. Cuộn ảnh, chạm một mục để xem chi tiết. D/E dùng ảnh720px cho danh sách và1600px cho chi tiết; bitmap được giải mã theo view.

Có thể cài qua USB bằng Android SDK Platform-Tools:

```sh
adb devices -l
adb -s SERIAL install -r apk/Cyclone-3.2.apk
```

Thay `SERIAL` bằng thiết bị của bạn. Nếu Android báo khác chữ ký giữa APK tải sẵn và APK tự build trên máy khác, hãy xuất/lưu kết quả app trước, rồi gỡ bản cũ và cài bản mới. Không tự xóa dữ liệu khi chưa sao lưu.

## Lấy source và build trên máy khác

```sh
git clone https://github.com/Sunn-dk/Cyclone.git
cd Cyclone
```

Cần Android Studio, **JDK17**, Android SDK Platform34 và Build-Tools34.0.0. Lần sync/build đầu cần Internet để tải Gradle và dependency. Không cần Python khi chỉ cài APK/chạy ảnh Internet.

- Android Studio -> Open -> chọn thư mục repository chứa `settings.gradle.kts`.
- SDK Manager -> cài Android SDK Platform34, Build-Tools34.0.0 và Platform-Tools.
- Gradle Settings -> chọn Gradle JDK17; Sync. Android Studio tạo `local.properties` theo SDK trên máy bạn; không chép đường dẫn SDK của máy khác.
- Chọn module **app**, thiết bị Android/API26 trở lên rồi Run. Module probe chỉ là helper kiểm tra chia sẻ ZIP.

Windows PowerShell, từ gốc repository:

```powershell
.\gradlew.bat :app:assembleDebug :app:assembleBenchmark :app:lintDebug
```

macOS/Linux:

```sh
./gradlew :app:assembleDebug :app:assembleBenchmark :app:lintDebug
```

Nếu dùng terminal, đặt `JAVA_HOME` tới JDK17 và `ANDROID_HOME` tới SDK trên máy bạn, hoặc cấu hình `sdk.dir` trong `local.properties`. APK mới ở `app/build/outputs/apk/debug/` và `benchmark/`. Debug để phát triển; benchmark để đo. A/D là cấu hình trong cùng app, không phải hai loại build này.

## Chạy nguồn ảnh local có sẵn, không phụ thuộc Picsum

Repo kèm [demo/images-100-jpeg.zip](demo/images-100-jpeg.zip): **100ảnh JPEG x3 kích thước =300tệp**. Bộ này phục vụ D/A/B/C/E với100 mục; chọn JPEG. Không đổi sang500/1000 hoặc PNG/WebP khi dùng bộ100 này.

Cần Python3.10 trở lên và `adb` trong PATH. Khi chỉ phục vụ bộ ZIP đã có, server dùng thư viện chuẩn Python, không cần Pillow.

Mở terminal thứ nhất ở gốc repository:

```sh
python -m zipfile -e demo/images-100-jpeg.zip datasets/demo-100
python scripts/image_server.py --dir datasets/demo-100
```

Trên macOS/Linux có thể dùng `python3` thay `python`. Giữ terminal server mở.

Mở terminal thứ hai:

```sh
adb devices -l
adb -s SERIAL reverse tcp:8000 tcp:8000
```

Trong Cyclone -> Thử nghiệm:

- Chọn D,100,JPEG; version1; độ trễ0; tắt chèn lỗi.
- Nguồn `http://127.0.0.1:8000` -> Áp dụng -> quay lại -> Tải lại.
- Địa chỉ127.0.0.1 trên điện thoại đi qua `adb reverse`; không nhập IP LAN của máy tính. Sau khi rút USB/tắt máy ảo, chạy lại reverse ở lần kết nối sau.

Chỉ ngắt nguồn thử local khi kiểm tra offline:

```sh
adb -s SERIAL reverse --remove tcp:8000
```

Khôi phục bằng lệnh reverse phía trên. Dừng server bằng Ctrl+C. Các thao tác này không thay Wi-Fi/cellular toàn hệ thống.

## Cấu hình và tạo bộ ảnh lớn

- [configs/baseline-A.json](configs/baseline-A.json): raw3000, giải mã gốc, cache tắt; vẫn tải bất đồng bộ và xử lý lỗi.
- [configs/optimized-D.json](configs/optimized-D.json): cache bật, giải mã theo ô, thumbnail720; chi tiết1600.
- B thêm cache; C thêm downsampling; E thêm crossfade/preview.

Để chạy một lượt với bộ100 có sẵn:

```sh
python scripts/run_one.py --config configs/baseline-A.json --fixtures datasets/demo-100 --serial SERIAL --out results/baseline-moi
python scripts/run_one.py --config configs/optimized-D.json --fixtures datasets/demo-100 --serial SERIAL --out results/optimized-moi
```

Dừng server tương tác trước khi dùng runner vì runner tự mở cổng8000. Luôn chọn `--out` mới; công cụ không ghi đè dữ liệu đã đo. `adb` có thể truyền bằng `--adb DUONG_DAN_ADB` nếu chưa có trong PATH.

Muốn có1.000 mục/JPEG-PNG-WebP và bộ cập nhật nội dung, cài Pillow rồi tạo ảnh trước khi mở server:

```sh
python -m pip install -r scripts/requirements.txt
python scripts/image_server.py --prepare --dir datasets/fixtures --count 1000 --format ALL --version 1
python scripts/image_server.py --prepare --dir datasets/updated-v2 --count 100 --format JPEG --version 2
python scripts/verify_dataset.py datasets/fixtures --out results/dataset-verification.json
python scripts/image_server.py --dir datasets/fixtures
```

Bộ lớn cần khoảng1GB dung lượng ảnh, không được tạo mặc định khi cài app. Bytes/hash ảnh tái tạo có thể khác giữa các phiên bản Pillow; luôn dùng manifest của chính bộ đang chạy. Thử nghiệm ảnh đổi dùng URL phiên bản mới hoặc xóa cache; app không tự ETag revalidate.

## Kiểm tra và giới hạn

```sh
python -m pip install -r scripts/requirements.txt
python -m unittest discover -s tests/server
python scripts/test_cpu_sampling.py
python scripts/test_ui_helpers.py
```

Giải thích và lệnh tái tạo hai phiên bản cơ sở A / tối ưu D theo D5: [D5 Tái tạo trước sau](docs/D5_TAI_TAO_TRUOC_SAU.md). Bản phát hành 3.0 không phải baseline của phép so A/D này.

Đã kiểm tra APK3.2 trên máy ảo Android12/API31. Yêu cầu tối thiểu API26 là cấu hình build; chưa thử mọi điện thoại/phiên bản Android. Picsum cần Internet và phụ thuộc dịch vụ ngoài; bộ local là lựa chọn độc lập. Kiểm SHA256 của APK và bộ ảnh theo [SHA256SUMS.txt](SHA256SUMS.txt).

Mã nguồn giữ Gradle8.7, AGP8.5.2, Kotlin1.9.24, Coil2.7.0. Không đóng gói JDK, SDK, cache Gradle, `local.properties` hoặc khóa ký của máy phát triển.
