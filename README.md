# Cyclone 3.2 — Hướng dẫn Chạy ứng dụng & Tái hiện Phép đo

Ứng dụng Android demo tối ưu hóa tải ảnh, lưu trữ đệm (Caching) và hiển thị lưới so le bằng **Kotlin + XML + RecyclerView + Coil 2.7.0**. 

---

## 1. Tải về & Cài đặt APK (Chọn 1 trong các cách nhanh nhất)

### Cách lấy mã nguồn siêu tốc:
* **Clone Git siêu tốc (Chỉ lấy bản mới nhất, nhẹ gấp 5 lần):**
  ```sh
  git clone --depth 1 https://github.com/Sunn-dk/Cyclone.git
  cd Cyclone
  ```
* **Hoặc tải file nén ZIP:** Bấm nút xanh **Code → Download ZIP** trên GitHub rồi giải nén.

---

### Cách cài đặt APK [apk/Cyclone-3.2.apk](apk/Cyclone-3.2.apk):
Hỗ trợ Android 8.0 (API 26) trở lên (khuyến nghị Android 12 / API 31). Chọn 1 trong 3 cách:

* **Cách 1 — Kéo thả vào máy ảo (Nhanh nhất cho Emulator):**
  Kéo tệp `Cyclone-3.2.apk` thả trực tiếp vào cửa sổ máy ảo Android Studio. Ứng dụng sẽ tự động cài trong 3 giây.
* **Cách 2 — Cài qua dòng lệnh ADB (Điện thoại cắm cáp USB hoặc máy ảo):**
  ```sh
  adb install -r apk/Cyclone-3.2.apk
  ```
* **Cách 3 — Cài trực tiếp trên điện thoại thật:**
  Tải file APK trực tiếp về điện thoại qua trình duyệt/Zalo/Drive rồi bấm cài đặt.

---

## 2. Chọn nguồn ảnh để chạy thử

Sau khi mở ứng dụng **Cyclone**, chọn 1 trong 2 nguồn ảnh:

* **Cách A — Dùng ảnh Internet (Picsum, nhanh nhất, cần Wi-Fi):**
  1. Bấm nút **Thử nghiệm** (góc trên phải) → ở mục **02 / Nguồn ảnh**, nhập:
     `https://picsum.photos`
  2. Chọn **Cấu hình D** (tối ưu), **100 mục**, định dạng **JPEG**, độ trễ **0 ms**, tắt chèn lỗi.
  3. Bấm **Áp dụng nguồn ảnh** → bấm **Về bộ sưu tập** để xem ảnh.

* **Cách B — Dùng ảnh cục bộ (Local Server, chuẩn xác 100%, không cần mạng):**
  1. Mở **Terminal 1** tại thư mục dự án để bật máy chủ ảnh mẫu có sẵn:
     ```sh
     # Giải nén bộ 100 ảnh mẫu (chỉ cần làm lần đầu)
     python -m zipfile -e demo/images-100-jpeg.zip datasets/demo-100
     
     # Chạy máy chủ ảnh (dùng thư viện chuẩn của Python, không cần cài thêm package)
     python scripts/image_server.py --dir datasets/demo-100
     ```
  2. Mở **Terminal 2** để chuyển tiếp cổng vào thiết bị:
     ```sh
     adb reverse tcp:8000 tcp:8000
     ```
  3. Trên app Cyclone → vào **Thử nghiệm** → nhập địa chỉ:
     `http://127.0.0.1:8000`
  4. Bấm **Áp dụng nguồn ảnh** → bấm **Về bộ sưu tập** → bấm **Tải lại**.

---

## 3. Mở mã nguồn trong Android Studio & Build lệnh

* **Mở dự án:** Khởi động Android Studio → **Open** → chọn thư mục chứa `settings.gradle.kts` → Chọn **JDK 17**, SDK Platform **34** → Chọn module **`app`** → Bấm **Run (Shift + F10)**.
* **Build bằng dòng lệnh (không cần mở Android Studio):**
  * *Windows:* `.\gradlew.bat :app:assembleDebug :app:assembleBenchmark`
  * *macOS / Linux:* `./gradlew :app:assembleDebug :app:assembleBenchmark`

---

## 4. Cách tái hiện các phép đo (Trước vs Sau Tối ưu)

Nhóm tích hợp sẵn 5 cấu hình ngay trong 1 APK để đối chứng khoa học:
* **Cấu hình A (Trước tối ưu - Baseline):** Tải ảnh gốc 3.000 px, giải mã nguyên bản `Size.ORIGINAL`, tắt hoàn toàn Cache.
* **Cấu hình D (Sau tối ưu - Optimized):** Tải Thumbnail 720 px, giải mã theo kích thước hiển thị ô ImageView, bật Cache RAM 25% + Disk 150 MiB, chi tiết tải ảnh 1.600 px.

---

### Cách 1: Thao tác trực quan trên App (Dành cho buổi chấm Demo)

Vào màn hình **Thử nghiệm** trên app Cyclone để biểu diễn trực tiếp:

1. **So sánh Độ mượt & Tiêu thụ RAM khi cuộn danh sách (Yêu cầu 1, 4, 5):**
   * **Với Cấu hình A:** Chọn **A** → Bấm **Xóa RAM + đĩa** → Bấm **Bắt đầu đo** → Bấm **Về bộ sưu tập** → Bấm **Tự cuộn** (cuộn trong 8 giây).
     * *Kết quả:* Danh sách bị giật khựng, nhiều ô chưa kịp hiện ảnh, đỉnh RAM PSS vọt lên **~160–170 MiB**, dọn rác GC chạy liên tục >10 lần.
   * **Với Cấu hình D:** Chọn **D** → Bấm **Xóa RAM + đĩa** → Bấm **Bắt đầu đo** → Bấm **Về bộ sưu tập** → Bấm **Tự cuộn**.
     * *Kết quả:* Cuộn mượt mà, ảnh hiện nhanh, đỉnh RAM PSS giảm hơn một nửa xuống chỉ còn **~76 MiB**, GC chỉ chạy 1 lần.

2. **Kiểm tra Cơ chế Bộ nhớ đệm Cache (Yêu cầu 3):**
   * **RAM Cache Hit:** Sau khi tải xong danh sách ở Cấu hình D, bấm **Tải lại** → Ảnh hiển thị tức thì sau **~61 ms**, thời gian request = **`0 ms`** (`MEMORY_CACHE = 5`).
   * **Disk Cache Hit:** Vào **Thử nghiệm** → bấm **Xóa cache RAM** (giữ lại Disk) → quay lại bấm **Tải lại** → Ảnh đọc trực tiếp từ đĩa không tốn mạng (`DISK = 5`, `NETWORK = 0`).

3. **Kiểm tra Mất mạng Offline & Ảnh lỗi HTTP 404 (Yêu cầu 1, 2, 3):**
   * **Thử Offline:** Tại Terminal gõ `adb reverse --remove tcp:8000` rồi bấm **Tải lại** trên app: Các ảnh đã cache vẫn hiển thị bình thường; các ô chưa cache hiển thị ảnh lỗi dự phòng (`ic_error`) an toàn, không sập ứng dụng. Bật lại mạng: `adb reverse tcp:8000 tcp:8000`.
   * **Thử lỗi 404:** Vào **Thử nghiệm** → Bật công tắc **Chèn ảnh lỗi** (gây lỗi 404 ở các mục chia hết cho 10) → Bấm **Áp dụng nguồn ảnh**. Đúng mục số 10 hiện icon báo lỗi, không ảnh hưởng các ảnh khác.

4. **Kiểm tra Chi tiết & Khôi phục vị trí (Yêu cầu 1, 2):**
   * Bấm vào 1 sản phẩm bất kỳ: Màn hình chi tiết nạp ảnh nét phân giải cao 1.600 px.
   * Bấm nút **Quay lại** (hoặc xoay ngang/dọc màn hình): Ứng dụng giữ nguyên chính xác vị trí cuộn trước đó.

---

### Cách 2: Tái hiện tự động bằng Dòng lệnh (CLI Scripts)

> *Đóng máy chủ ở mục 2 trước (nhấn `Ctrl + C`) vì các script tự động quản lý cổng riêng.*

1. **Đo nhanh 1 lượt cấu hình Trước tối ưu (A) vs Sau tối ưu (D):**
   ```sh
   # Đo Cấu hình A (Trước tối ưu)
   python scripts/run_one.py --config configs/baseline-A.json --fixtures datasets/demo-100 --out results/A-moi

   # Đo Cấu hình D (Sau tối ưu)
   python scripts/run_one.py --config configs/optimized-D.json --fixtures datasets/demo-100 --out results/D-moi
   ```

2. **Chạy toàn bộ 14 bài kiểm thử chức năng tự động (Functional Suite):**
   ```sh
   python scripts/run_suite.py --fixtures datasets/demo-100 --out results/kiem-thu-chuc-nang --suite functional
   ```
   *(Kiểm tra tự động: Tải lạnh, RAM cache, Disk cache, Khởi động lại app, Mất mạng offline, Xóa cache khi offline, Phục hồi mạng, Lỗi 404, Mạng chậm 2s, Timeout 15s, Định dạng PNG/WebP).*

---

## 5. Bảng số liệu đối chứng tiêu biểu (Đo trên Pixel 5 / API 31)

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

## 6. Mở rộng tạo bộ dữ liệu lớn (1.000 ảnh)

Dành cho kịch bản nâng cao kiểm tra độ chịu tải lớn (9.000 tệp ảnh ~ 1 GB):
```sh
python -m pip install -r scripts/requirements.txt
python scripts/image_server.py --prepare --dir datasets/fixtures --count 1000 --format ALL --version 1
python scripts/verify_dataset.py datasets/fixtures --out results/dataset-verification.json
```
Khi chạy kiểm thử với bộ lớn, đổi tham số `--fixtures datasets/demo-100` thành `--fixtures datasets/fixtures`.
