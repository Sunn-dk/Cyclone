# Cyclone 3.0

Android Kotlin/XML demo cho đề tối ưu ảnh. Source kế thừa v2; không dựng lại từ đầu. Giữ package com.example.imageopt để tương thích script, đổi tên hiển thị thành Cyclone.

## Môi trường/build
JDK17, SDK Platform34, Build-Tools34.0.0, Gradle wrapper8.7, AGP8.5.2, Kotlin1.9.24, Coil2.7.0. Mở thư mục này bằng Android Studio, chọn Gradle JDK17. SDK path dùng local.properties do IDE tạo trên máy bạn.
~~~powershell
.\gradlew.bat assembleDebug assembleBenchmark lintDebug
~~~
APK sinh ở app/build/outputs/apk/debug và benchmark. Benchmark không debuggable, profileable và ký debug để cài thử. Không dùng debug và benchmark lẫn trong cùng ma trận.

## Hai phiên bản tái tạo
- configs/baseline-A.json: tải cùng item qua URL raw3000, Size.ORIGINAL, cache RAM/đĩa tắt. Vẫn async, timeout, error và cùng UI/chức năng. Không cố tình thêm lỗi/delay.
- configs/optimized-D.json: cache RAM/đĩa bật, decode theo ô, URLthumbnail720.
- B: cache trên ảnh gốc; C: decode theo ô từ URLgốc; E: D + UX và URLchi tiết1600.
- Cùng APK chọn A–E tại Thử nghiệm. Hai APK debug/benchmark không phải cặp trước/sau.
- Hai cấu hình JSON có thể chạy riêng bằng scripts/run_one.py từ gốc gói:
~~~powershell
python Cyclone/scripts/run_one.py --config Cyclone/configs/baseline-A.json --fixtures datasets/fixtures --out results/baseline
python Cyclone/scripts/run_one.py --config Cyclone/configs/optimized-D.json --fixtures datasets/fixtures --out results/optimized
~~~
So sánh A/D gộp nhiều kỹ thuật. Không kết luận hiệu quả riêng từng kỹ thuật khi chưa đo tách biệt.

## Nguồn ảnh
Mặc định dùng Picsum. Đổi nguồn ngay ở màn Thử nghiệm, không cần sửa Kotlin. Nguồn local: http://127.0.0.1:8000 sau adb reverse tcp:8000 tcp:8000. Server chỉ bindloopback. Không quảng cáo hỗ trợ LANWi-Fi trong bản server này.

## Công cụ
- scripts/image_server.py: chuẩn bị/serve dữ liệu, format/v/delay/error.
- scripts/verify_dataset.py: kiểm hash, kích thước và tính duy nhất.
- scripts/run_suite.py: các ca chức năng +36lượt cold +2trace riêng.
- scripts/run_reload.py: tải lại đo lặp, mỗi lượt giữ tiến trình sau prime.
- scripts/run_regressions.py: UI/cache/export/cancel/version.
- scripts/run_one.py: một cấu hình JSON.
- scripts/record_demo.ps1: quay màn hình khi người dùng chủ động bắt đầu.
- scripts/measure.ps1: thu công cụ ADB tương tác; xem giới hạn cửa sổ đo.

Đọc ../05_TAI_HIEN_KIEM_THU_V3.md cho lệnh đầy đủ, định nghĩa số đo và ../06_VIEC_BAN_CAN_LAM.md cho video. Lượt tự động xuất ZIP và ảnh riêng cửa sổ app sau khi dừng, lưu ở external files/automation. Scripts kéo về thư mục --out.

Không xóa dữ liệu cá nhân, không thay đổi Wi-Fi/cellular. Cold chỉ xóa cache thử nghiệm của app; restart chỉ force-stop app. Offline chỉ ngắt adb reverse của nguồn thử nghiệm.

## Kiểm chứng/giới hạn
Nguồn số liệu và trạng thái mới nhất nằm ở ../evidence và ../04_DOI_CHIEU_YEU_CAU.md. Không tự gọi tất cả testcase là Pass vì build được. PSS là đỉnh lấy mẫu; viewport pre-draw là mốc đại diện; CPUms là tổng CPU tiến trình; frame deadline/proxy1chu kỳ/gfxinfo phải giữ riêng định nghĩa. Không có tự ETagrevalidate.

Không có chương báo cáo hoàn chỉnh trong source. Video chưa được quay theo lựa chọn của người dùng.
