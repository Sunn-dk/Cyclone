# Cyclone 3.2 — Hướng dẫn Chạy ứng dụng & Tái hiện Phép đo

Ứng dụng Android demo tối ưu hóa tải ảnh, lưu trữ đệm (Caching) và hiển thị lưới so le bằng **Kotlin + XML + RecyclerView + Coil 2.7.0**. 

---

## 1. Cài đặt & Chạy ngay (30 giây)

### Bước 1: Cài đặt APK
Tải [apk/Cyclone-3.2.apk](apk/Cyclone-3.2.apk) và cài lên điện thoại hoặc máy ảo Android (từ Android 8.0 / API 26 trở lên, khuyến nghị Android 12 / API 31).

Cài nhanh qua cổng USB/máy ảo bằng lệnh `adb`:
```sh
adb install -r apk/Cyclone-3.2.apk
```

### Bước 2: Chọn nguồn ảnh để chạy

* **Cách A — Dùng ảnh Internet (Picsum, nhanh nhất, cần mạng Wi-Fi):**
  1. Mở ứng dụng **Cyclone**.
  2. Bấm nút **Thử nghiệm** (góc trên phải) → ở mục **02 / Nguồn ảnh**, nhập:
     `https://picsum.photos`
  3. Chọn **Cấu hình D** (tối ưu), **100 mục**, định dạng **JPEG**, độ trễ **0 ms**, tắt công tắc chèn lỗi.
  4. Bấm **Áp dụng nguồn ảnh** → bấm **Về bộ sưu tập** để xem ảnh.

* **Cách B — Dùng ảnh cục bộ (Local Server, chuẩn xác 100%, không cần Internet):**
  1. Mở **Terminal 1** tại thư mục dự án để bật máy chủ ảnh:
     ```sh
     # Giải nén bộ 100 ảnh mẫu (nếu chưa giải nén)
     python -m zipfile -e demo/images-100-jpeg.zip datasets/demo-100
     
     # Chạy máy chủ ảnh nội bộ
     python scripts/image_server.py --dir datasets/demo-100
     ```
  2. Mở **Terminal 2** để chuyển tiếp cổng vào điện thoại/máy ảo:
     ```sh
     adb reverse tcp:8000 tcp:8000
     ```
  3. Trên ứng dụng Cyclone → vào **Thử nghiệm** → nhập địa chỉ:
     `http://127.0.0.1:8000`
  4. Bấm **Áp dụng nguồn ảnh** → bấm **Về bộ sưu tập** → bấm **Tải lại**.

---

## 2. Mở mã nguồn trong Android Studio

1. **Yêu cầu môi trường:** Android Studio, **JDK 17**, Android SDK Platform **34**, Build-Tools **34.0.0**.
2. **Mở dự án:** Khởi động Android Studio → **Open** → chọn thư mục chứa tệp `settings.gradle.kts`.
3. **Đồng bộ & Chạy:** Chờ Gradle Sync xong → chọn module **`app`** → chọn thiết bị chạy → bấm **Run (Shift + F10)**.

Build trực tiếp bằng dòng lệnh:
* **Windows (PowerShell):**
  ```powershell
  .\gradlew.bat :app:assembleDebug :app:assembleBenchmark
  ```
* **macOS / Linux:**
  ```sh
  ./gradlew :app:assembleDebug :app:assembleBenchmark
  ```
*(Tệp APK xuất ra tại: `app/build/outputs/apk/debug/` và `app/build/outputs/apk/benchmark/`)*

---

## 3. Cách tái hiện các phép đo (Trước vs Sau Tối ưu)

Nhóm tích hợp sẵn 5 cấu hình ngay trong 1 APK để đối chứng khoa học:
* **Cấu hình A (Trước tối ưu - Baseline):** Tải ảnh gốc 3.000 px, giải mã nguyên bản `Size.ORIGINAL`, tắt hoàn toàn bộ nhớ đệm (Cache).
* **Cấu hình D (Sau tối ưu - Optimized):** Tải Thumbnail 720 px cho danh sách, giải mã theo kích thước hiển thị ô ImageView, bật Cache RAM 25% + Disk 150 MiB, chi tiết tải ảnh 1.600 px.

---

### Cách 1: Tái hiện trực quan trên giao diện ứng dụng (Thực hiện khi chấm Demo)

Mở màn hình **Thử nghiệm** trên app Cyclone để kiểm chứng từng tiêu chí:

1. **So sánh Độ mượt & Tiêu thụ RAM khi cuộn danh sách (Yêu cầu 1, 4, 5):**
   * **Với Cấu hình A:** Chọn **A** → Bấm **Xóa RAM + đĩa** → Bấm **Đặt lại thống kê** → Bấm **Bắt đầu đo** → Bấm **Về bộ sưu tập** → Bấm **Tự cuộn** (cuộn trong 8 giây).
     * *Hiện tượng:* Danh sách bị giật khựng, nhiều ô chưa kịp hiện ảnh, đỉnh RAM PSS vọt lên **~160–170 MiB**, dọn rác GC chạy liên tục >10 lần.
   * **Với Cấu hình D:** Chọn **D** → Bấm **Xóa RAM + đĩa** → Bấm **Bắt đầu đo** → Bấm **Về bộ sưu tập** → Bấm **Tự cuộn**.
     * *Hiện tượng:* Danh sách cuộn cực kỳ mượt mà, ảnh hiện nhanh, đỉnh RAM PSS giảm hơn một nửa xuống chỉ còn **~76 MiB**, GC chỉ chạy 1 lần.

2. **Kiểm tra Cơ chế Bộ nhớ đệm Cache (Yêu cầu 3):**
   * **RAM Cache Hit:** Sau khi tải xong danh sách ở Cấu hình D, bấm **Tải lại** → Ảnh hiển thị tức thì sau **~61 ms**, thời gian request = **`0 ms`** (`MEMORY_CACHE = 5`).
   * **Disk Cache Hit:** Vào **Thử nghiệm** → bấm **Xóa cache RAM** (giữ lại Disk) → quay lại bấm **Tải lại** → Ảnh đọc thành công từ đĩa mà không tốn mạng (`DISK = 5`, `NETWORK = 0`).

3. **Kiểm tra Chế độ Mất mạng Offline & Ảnh lỗi HTTP 404 (Yêu cầu 1, 2, 3):**
   * **Thử Offline:** Tại Terminal gõ `adb reverse --remove tcp:8000` rồi bấm **Tải lại** trên app: Các ảnh đã cache vẫn hiển thị bình thường; các ô chưa cache hiển thị ảnh lỗi dự phòng an toàn, không sập ứng dụng. Bật lại mạng bằng `adb reverse tcp:8000 tcp:8000`.
   * **Thử lỗi 404 & Mạng chậm:** Vào **Thử nghiệm** → Bật công tắc **Chèn ảnh lỗi** (gây lỗi 404 ở các mục chia hết cho 10) + đặt **Độ trễ máy chủ** = `1500 ms` → Bấm **Áp dụng nguồn ảnh**. Giao diện vẫn cuộn mượt không bị đơ ANR, đúng mục số 10 hiện icon báo lỗi.

4. **Kiểm tra Màn hình Chi tiết & Khôi phục vị trí (Yêu cầu 1, 2):**
   * Bấm vào 1 sản phẩm bất kỳ: Màn hình chi tiết nạp ảnh nét phân giải cao 1.600 px.
   * Bấm nút **Quay lại** (hoặc xoay ngang/dọc màn hình): Ứng dụng giữ nguyên chính xác vị trí cuộn trước đó.

---

### Cách 2: Tái hiện tự động bằng Dòng lệnh (CLI Scripts)

Dành cho việc kiểm tra định lượng tự động, xuất số liệu ra CSV/JSON:

> **Lưu ý:** Trước khi chạy script, hãy đóng máy chủ tương tác ở mục 1 (nhấn `Ctrl + C`) vì các script sẽ tự động quản lý máy chủ riêng.

1. **Đo nhanh 1 lượt cấu hình Trước tối ưu (A) vs Sau tối ưu (D):**
   ```sh
   # Đo Cấu hình A (Trước tối ưu)
   python scripts/run_one.py --config configs/baseline-A.json --fixtures datasets/demo-100 --out results/A-moi

   # Đo Cấu hình D (Sau tối ưu)
   python scripts/run_one.py --config configs/optimized-D.json --fixtures datasets/demo-100 --out results/D-moi
   ```
   *Kết quả tóm tắt in ngay trên Terminal và lưu chi tiết tại thư mục `results/`.*

2. **Chạy toàn bộ 14 bài kiểm thử chức năng tự động (Functional Suite):**
   ```sh
   python scripts/run_suite.py --fixtures datasets/demo-100 --out results/kiem-thu-chuc-nang --suite functional
   ```
   *Script tự động kiểm tra lần lượt: Tải lạnh, RAM cache, Disk cache, Khởi động lại app, Mất mạng offline, Xóa cache khi offline, Phục hồi mạng, Lỗi 404, Mạng chậm 2s, Timeout 15s, Định dạng PNG/WebP.*

---

## 4. Bảng số liệu đối chứng tiêu biểu (Đo trên Pixel 5 / API 31)

| Chỉ số đo lường | Trước tối ưu (Cấu hình A) | Sau tối ưu (Cấu hình D) | Mức độ cải thiện |
| :--- | :---: | :---: | :---: |
| **Thời gian nạp hiển thị khung nhìn đầu** | `1.057 ms` | **`739 ms`** | **Nhanh hơn 30,1%** |
| **Thời gian tải lại danh sách (Reload)** | `1.361 ms` | **`61 ms`** | **Nhanh hơn 95,5%** (RAM Hit) |
| **Đỉnh bộ nhớ tiến trình (Sampled PSS Peak)** | `173,5 MiB` | **`76,2 MiB`** | **Tiết kiệm 56,1% RAM** |
| **Băng thông mạng tải danh sách 100 ảnh** | `6,92 MB` | **`1,01 MB`** | **Giảm 85,5% dung lượng tải** |
| **Thời gian giải mã mỗi ảnh khi cuộn (Decode)** | `244–334 ms` | **`43–82 ms`** | **Nhanh gấp ~4 lần** |
| **Thời gian dừng dọn rác bộ nhớ (GC time)** | `650–1.133 ms` (11–13 lần) | **`54–107 ms` (1 lần)** | **Giảm hơn 85% áp lực GC** |
| **Độ trễ khung hình khi cuộn (Frame p90)** | `160,56 ms` | **`56,42 ms`** | **Giảm 64,8% độ trễ (mượt hơn)** |

---

## 5. Tùy chọn nâng cao: Tạo bộ ảnh 1.000 mục & các định dạng khác

Nếu muốn mở rộng thử nghiệm lên quy mô lớn (1.000 ảnh × 3 kích thước × 3 định dạng JPEG/PNG/WebP = 9.000 tệp ~ 1 GB):
```sh
# Cài đặt Pillow để tạo ảnh
python -m pip install -r scripts/requirements.txt

# Tạo bộ 1.000 ảnh chuẩn
python scripts/image_server.py --prepare --dir datasets/fixtures --count 1000 --format ALL --version 1

# Xác minh tính toàn vẹn của tập dữ liệu
python scripts/verify_dataset.py datasets/fixtures --out results/dataset-verification.json
```
Khi chạy với bộ lớn, chỉ cần thay tham số đường dẫn `--fixtures datasets/fixtures`.
