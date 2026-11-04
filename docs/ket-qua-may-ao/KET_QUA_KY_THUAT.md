# Tổng hợp kỹ thuật từ dữ liệu thật

Không phải chương báo cáo tiểu luận. Mỗi ô là median các giá trị quan sát; n là tổng lượt, viewport_observed_n là số lượt đạt mốc, không tự điền0 cho mốc thiếu; PSS là median các max lấy mẫu, không phải max liên tục. Frame p90 là median của p90 từng lượt. Mẫu riêng ở all_trials.csv và ZIP gốc.

| scenario | count | config | n | viewport_observed_n | viewport_ms | median_request_ms | median_decode_ms | sampled_peak_pss_mib | process_cpu_ms | frame_p90_ms | gc_count | gc_ms | allocated_bytes | layout_p90_ms | draw_p90_ms | sync_p90_ms | median_deadline_miss_pct | median_response_file_payload_bytes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| load | 100 | A | 3 | 3 | 1057.00 | 826.00 | 759.00 | 173.45 | 2317.00 | 212.19 | 1.00 | 121.00 | 1702272.00 | 4.25 | 11.24 | 0.68 | 62.50 | 1256649.00 |
| load | 100 | D | 3 | 3 | 739.00 | 612.00 | 485.00 | 76.17 | 1631.00 | 217.48 | 1.00 | 151.00 | 1866416.00 | 4.54 | 6.11 | 0.95 | 46.67 | 182216.00 |
| load | 500 | A | 3 | 3 | 1213.00 | 926.00 | 880.00 | 160.30 | 2548.00 | 335.51 | 1.00 | 90.00 | 1751520.00 | 5.08 | 9.18 | 0.38 | 100.00 | 1256649.00 |
| load | 500 | D | 3 | 3 | 774.00 | 586.00 | 488.00 | 78.05 | 1822.00 | 503.02 | 1.00 | 41.00 | 1901192.00 | 13.55 | 8.96 | 0.48 | 83.33 | 182216.00 |
| load | 1000 | A | 3 | 3 | 1419.00 | 1118.00 | 1055.00 | 155.78 | 2542.00 | 211.19 | 1.00 | 229.00 | 1751424.00 | 6.63 | 8.63 | 7.17 | 100.00 | 1256649.00 |
| load | 1000 | D | 3 | 3 | 870.00 | 761.00 | 560.00 | 76.01 | 1933.00 | 386.37 | 1.00 | 35.00 | 1964624.00 | 8.24 | 1.43 | 1.87 | 100.00 | 182216.00 |
| reload | 100 | A | 3 | 3 | 1361.00 | 1050.00 | 937.00 | 175.50 | 2451.00 | 817.68 | 1.00 | 205.00 | 1319008.00 | 8.54 | 13.95 | 2.01 | 100.00 | 1256649.00 |
| reload | 100 | D | 3 | 3 | 61.00 | 0.00 | — | 74.55 | 422.00 | 187.56 | 0.00 | 0.00 | 589920.00 | 0.23 | 6.50 | 0.28 | 100.00 | 0.00 |
| scroll | 100 | A | 3 | 0 | — | 338.00 | 244.00 | 170.54 | 10029.00 | 160.56 | 13.00 | 650.00 | 6587096.00 | 1.14 | 1.44 | 1.16 | 97.82 | 6924386.00 |
| scroll | 100 | D | 3 | 3 | 775.00 | 96.00 | 43.00 | 77.37 | 5972.00 | 56.42 | 1.00 | 107.00 | 5734952.00 | 0.20 | 0.49 | 0.76 | 58.31 | 1012969.00 |
| scroll | 500 | A | 3 | 0 | — | 383.00 | 306.00 | 155.31 | 10257.00 | 226.79 | 12.00 | 756.00 | 6158864.00 | 2.15 | 1.47 | 1.38 | 100.00 | 5875066.00 |
| scroll | 500 | D | 3 | 3 | 987.00 | 148.00 | 71.00 | 78.96 | 7154.00 | 92.00 | 1.00 | 54.00 | 5702488.00 | 0.41 | 0.88 | 1.16 | 100.00 | 1012969.00 |
| scroll | 1000 | A | 3 | 0 | — | 433.00 | 334.00 | 164.82 | 11064.00 | 322.09 | 11.00 | 1133.00 | 5997240.00 | 3.53 | 1.83 | 1.53 | 100.00 | 4771026.00 |
| scroll | 1000 | D | 3 | 2 | 1058.50 | 154.00 | 82.00 | 85.52 | 7656.00 | 98.76 | 1.00 | 102.00 | 5749424.00 | 0.46 | 0.66 | 1.06 | 100.00 | 1012969.00 |

## Định dạng — D/100/cold

| format | n | median_request_ms | median_decode_ms | sampled_peak_pss_mib | process_cpu_ms | median_response_file_payload_bytes |
|---|---|---|---|---|---|---|
| JPEG | 3 | 1321.00 | 1110.00 | 75.78 | 2775.00 | 182216.00 |
| PNG | 3 | 1419.00 | 1116.00 | 76.99 | 3074.00 | 394444.00 |
| WEBP | 3 | 1426.00 | 1169.00 | 76.89 | 3296.00 | 99914.00 |

Payload là tổng dung lượng tệp tương ứng với request NETWORK thành công, tra files.json; không phải byte TCP/TLS/HTTP thực trên dây. Nhiệt/pin có lưu từng lượt; không khóa xungCPU. Không suy cải thiện riêng từng kỹ thuật từ A/D. Mốc viewport gồm ảnh lỗi nên đọc viewport_errors; các lượt chính này không có lỗi. Trace, stress cancel và prime không trộn vào bảng A/D chính.

Không gộp số đo Sony v3 vào ma trận máy ảo v3.2. Các lượt thử công cụ trước bản APK cuối được giữ riêng và không dùng để so sánh hiệu năng.
