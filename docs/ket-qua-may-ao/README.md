# Kết quả thực nghiệm Cyclone 3.2 trên máy ảo

Dữ liệu gốc của đợt 03/11/2026 trên Pixel 5 AVD, Android 12/API31, dùng APK benchmark 3.2/code5. Đây là đợt số liệu trong báo cáo hoàn chỉnh, không gộp các lượt kiểm tra lại ở đợt khác.

- `comparison.csv`: ma trận A/D và tải lại, trung vị theo nhóm.
- `all_trials.csv`: số liệu từng lượt tải/cuộn, chức năng, tải lại và định dạng.
- `ablation.csv`, `ablation_trials.csv`: tổng hợp và từng lượt tách cache, downsampling, thumbnail.
- `formats.csv`: JPEG, PNG, WebP.
- `comparison.png`: biểu đồ đối chiếu.
- [ZIP dữ liệu gốc](Cyclone-3.2-Pixel5-API31-2026-11-03.zip): giải nén để xem summary JSON, request/frame/memory CSV, log, ảnh giao diện và ART trace trong các nhóm tương ứng. `excluded/` giữ riêng các lượt thử công cụ bị loại, không nhập vào bảng chính. Không kèm log khởi động máy ảo của máy chủ hoặc bộ ảnh gần 1 GB; README gốc có lệnh tạo bộ ảnh.

PSS là max lấy mẫu; viewport là pre-draw. Ô viewport thiếu không được thay bằng 0. Frame p90 và tỷ lệ trễ hạn là trung vị các chỉ số từng lượt. Payload được tra từ dung lượng tệp của request NETWORK thành công, không phải byte truyền thực trên mạng. Trace CPU và các ca stress giữ riêng khỏi ma trận chính; sampling không phải đếm toàn bộ lời gọi.

Các script chẩn đoán mới trong `scripts/` là công cụ để chạy lần tiếp theo; sự có mặt của script không có nghĩa đã thu được scheduler hợp lệ trong bộ dữ liệu này. Không lấy trace Perfetto thiếu scheduler để kết luận CPU. Không quay video đồng thời với phép đo.
