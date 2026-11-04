# D5 Tái tạo phiên bản cơ sở và phiên bản tối ưu

Cyclone dùng hai cấu hình A và D trong cùng mã nguồn để tái tạo hai phiên bản thực nghiệm. Cả hai giữ cùng danh sách sản phẩm, ID ảnh, nội dung ảnh, màn hình và thao tác. A dùng ảnh gốc; D dùng các kích thước nhỏ hơn của chính các ảnh đó. Đây là kỹ thuật cần so sánh, không phải thay bộ nội dung.

| Thuộc tính | Phiên bản cơ sở A | Phiên bản tối ưu D |
|---|---|---|
| Tải bất đồng bộ và xử lý lỗi | Có | Có |
| Cache RAM và đĩa | Tắt | Bật |
| Giải mã danh sách | Kích thước gốc | Theo kích thước ô |
| Tài nguyên danh sách | Cạnh dài 3000 px | Thumbnail cạnh dài 720 px |
| Tài nguyên chi tiết | Ảnh gốc 3000 px | Ảnh chi tiết 1600 px |
| Số mục và ID | 100, 500 hoặc 1000 | Cùng số mục và ID với A |
| Crossfade thêm của E | Tắt | Tắt |

Không dùng 3.0 làm baseline cho phép so chính: phiên bản phát hành cũ có thể khác mã và điều kiện đo. Không gọi debug/benchmark là trước/sau; chúng là loại build. Hai cấu hình thực nghiệm được lưu ở `configs/baseline-A.json` và `configs/optimized-D.json`.

## Tái tạo bằng giao diện

1. Cài cùng một APK benchmark Cyclone 3.2 trên một thiết bị.
2. Chuẩn bị cùng bộ ảnh và server theo README. Chọn cùng nguồn, JPEG, version1, trễ0, tắt chèn lỗi và cùng số mục.
3. Chọn A, xóa cache và chạy kịch bản tải/cuộn; dừng rồi xuất kết quả.
4. Chọn D và thực hiện đúng kịch bản, trạng thái cache, hướng màn hình và điều kiện mạng như A.
5. Lặp ít nhất các lượt đã mô tả trong báo cáo; lưu từng lượt. Không quay video khi đo.

## Tái tạo bằng cấu hình được lưu

Chạy từ gốc repository, thay SERIAL bằng mã thiết bị. Cần Python, adb và bộ ảnh đã giải nén theo README. Runner tự mở server thử, nên dừng server tương tác trước khi chạy.

```sh
python scripts/run_one.py --config configs/baseline-A.json --fixtures datasets/demo-100 --serial SERIAL --out results/D5-A-moi
python scripts/run_one.py --config configs/optimized-D.json --fixtures datasets/demo-100 --serial SERIAL --out results/D5-D-moi
```

Mỗi lần chạy dùng thư mục kết quả mới. Với bộ đầy đủ 1000 mục, dùng `datasets/fixtures` và `scripts/run_suite.py --suite matrix --repeats 3` để chạy 100/500/1000, load/scroll, A/D, đảo thứ tự cấu hình.

## Minh chứng có thể kiểm tra

- `image/ImageExperimentConfig.kt`: định nghĩa chính xác các cờ A và D.
- `image/ImageRequests.kt` và `image/ImageLoaderFactory.kt`: nơi áp dụng cờ.
- `configs/*.json`: cấu hình đầu vào đọc được và có thể chạy lại.
- Mỗi phiên xuất `trial.json`, `summary.json`, `requests.csv`, `frames.csv`, `memory.csv` và ZIP. Đối chiếu config/count/source/buildType/versionName và hash dataset trước khi so.
- A/D đo hiệu quả kết hợp. Cặp A/B, B/C, C/D mới dùng phân tích riêng cache, downsampling và thumbnail.

Mã Kotlin ở `app/src/main/java/com/example/imageopt/`. README và tài liệu bàn giao chỉ rõ commit nền, bản source đóng gói và SHA256. Không cần đăng lại bản 3.0 để tạo minh chứng D5.
