# Cyclone 3.2

Demo tối ưu ảnh Android bằng Kotlin/XML/RecyclerView. Repo chỉ gồm source app, một APK demo, bộ ảnh mẫu, cấu hình A/D và công cụ chạy lại cơ bản.

## 1. Cài APK và chạy ngay

Tải [Cyclone-3.2.apk](apk/Cyclone-3.2.apk), cài trên Android 8.0/API26 trở lên. Đã kiểm tra trên máy ảo Android 12/API31.

Mở Cyclone → Thử nghiệm → nguồn `https://picsum.photos`, cấu hình D, 100 mục, JPEG, version 1, độ trễ 0, tắt chèn lỗi → Áp dụng nguồn ảnh → quay lại. Cần Internet khi dùng Picsum. Cuộn danh sách, chạm ảnh để xem chi tiết; thử Tải lại và xóa cache trong Thử nghiệm.

Cài qua USB nếu cần:

```sh
adb devices -l
adb -s SERIAL install -r apk/Cyclone-3.2.apk
```

Thay `SERIAL` bằng mã máy ảo/thiết bị. Nếu khác chữ ký với bản cũ, sao lưu kết quả app trước khi gỡ bản cũ để cài mới.

## 2. Mở source trong Android Studio

Tải Code → Download ZIP và giải nén, hoặc:

```sh
git clone https://github.com/Sunn-dk/Cyclone.git
cd Cyclone
```

Open thư mục có `settings.gradle.kts`. Cài SDK Platform 34 và Build-Tools 34.0.0; chọn Gradle JDK 17 → Sync → module `app` → chọn máy ảo → Run. Lần đầu cần Internet để tải dependency. Android Studio tạo `local.properties` theo SDK của máy đang dùng.

Build bằng PowerShell tại gốc repo:

```powershell
.\gradlew.bat :app:assembleDebug :app:assembleBenchmark
```

macOS/Linux dùng `./gradlew` với cùng tác vụ. APK tạo ở `app/build/outputs/apk/`. Debug dùng phát triển; benchmark dùng demo/đo. APK tải sẵn là benchmark 3.2/code5.

## 3. Chạy ảnh mẫu local

[images-100-jpeg.zip](demo/images-100-jpeg.zip) gồm 100 ảnh JPEG, mỗi ảnh có ba kích thước. Cần Python 3.10 trở lên và `adb` trong PATH; không cần cài thư viện Python để phục vụ bộ ảnh có sẵn.

Terminal thứ nhất ở gốc repo:

```sh
python -m zipfile -e demo/images-100-jpeg.zip datasets/demo-100
python scripts/image_server.py --dir datasets/demo-100
```

Giữ server chạy. Terminal thứ hai:

```sh
adb devices -l
adb -s SERIAL reverse tcp:8000 tcp:8000
```

Trong Thử nghiệm: nguồn `http://127.0.0.1:8000`, 100 mục, JPEG, version 1, độ trễ 0, tắt chèn lỗi → Áp dụng nguồn ảnh → quay lại → Tải lại. Bộ mẫu chỉ có 100 mục/JPEG; không chọn 500/1.000 hoặc PNG/WebP với bộ này. Sau khi khởi động lại máy ảo, chạy lại reverse.

Kiểm tra mất kết nối nguồn thử bằng `adb -s SERIAL reverse --remove tcp:8000`; khôi phục bằng lệnh reverse phía trên. Dừng server bằng Ctrl+C. Không cần đổi mạng toàn hệ thống.

## 4. So sánh A và D

- A: ảnh gốc, giải mã gốc, tắt cache; vẫn tải bất đồng bộ.
- D: cache RAM/đĩa, giải mã theo ô, thumbnail 720 px; ảnh chi tiết 1.600 px.
- B/C/E là các cấu hình trung gian và biến thể trong app.

Chọn A rồi D, giữ cùng nguồn, số mục và thao tác. A/D là hai cấu hình trong cùng app, không phải debug/benchmark. Xem [cách tái tạo A/D](docs/D5_TAI_TAO_TRUOC_SAU.md).

Chạy tự động một lượt mỗi cấu hình: dừng server tương tác trước, vì runner tự mở server.

```sh
python scripts/run_one.py --config configs/baseline-A.json --fixtures datasets/demo-100 --serial SERIAL --out results/A-moi
python scripts/run_one.py --config configs/optimized-D.json --fixtures datasets/demo-100 --serial SERIAL --out results/D-moi
```

Dùng `--out` mới mỗi lần để giữ kết quả cũ. Chỉ so kết quả cùng điều kiện; không quay video khi đo.

## 5. Tùy chọn tạo ảnh cho 500/1.000 mục và định dạng khác

Chỉ dùng phần này khi cần bộ lớn, khoảng 1 GB. Pillow dùng để tạo và kiểm tra ảnh mới.

```sh
python -m pip install -r scripts/requirements.txt
python scripts/image_server.py --prepare --dir datasets/fixtures --count 1000 --format ALL --version 1
python scripts/verify_dataset.py datasets/fixtures --out results/dataset-verification.json
```

Thay `datasets/demo-100` bằng `datasets/fixtures` khi mở server/chạy runner. Hash ảnh mới phụ thuộc bản Pillow; giữ manifest của bộ đang dùng. Kiểm tra server bằng `python -m unittest discover -s tests/server`.

Kiểm SHA-256 APK và ZIP ảnh mẫu theo [SHA256SUMS.txt](SHA256SUMS.txt). Repo không kèm SDK/JDK, cache build, khóa ký hoặc kết quả đo của máy phát triển.
