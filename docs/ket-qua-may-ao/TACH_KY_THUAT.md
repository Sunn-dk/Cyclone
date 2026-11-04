# Đo tách kỹ thuật trên máy ảo

Đây là hồ sơ kỹ thuật, không phải chương báo cáo. n=3 là lựa chọn thực nghiệm. Không suy rộng ra Sony hoặc mạng Internet.

| Kịch bản | Cấu hình | n | Viewport ms | Request ms | Decode ms | PSS mẫu MiB | CPU ms | NETWORK/DISK/RAM |
|---|---|---|---|---|---|---|---|---|
| cache_prime | A | 3 | 1988.00 | 1584.00 | 1500.00 | 172.54 | 3677.00 | 5.0/0.0/0.0 |
| cache_prime | B | 3 | 1852.00 | 1492.00 | 1380.00 | 171.44 | 3696.00 | 5.0/0.0/0.0 |
| cache_warm | A | 3 | 1397.00 | 1174.00 | 1111.00 | 175.52 | 2331.00 | 5.0/0.0/0.0 |
| cache_warm | B | 3 | 70.00 | 0.00 | — | 73.70 | 470.00 | 0.0/0.0/5.0 |
| decode_cold | B | 3 | 1880.00 | 1571.00 | 1400.00 | 174.04 | 3487.00 | 5.0/0.0/0.0 |
| decode_cold | C | 3 | 1550.00 | 1391.00 | 1018.00 | 77.41 | 3109.00 | 5.0/0.0/0.0 |
| thumbnail_cold | C | 3 | 1506.00 | 1370.00 | 981.00 | 72.08 | 3052.00 | 5.0/0.0/0.0 |
| thumbnail_cold | D | 3 | 1445.00 | 1351.00 | 1080.00 | 72.87 | 2921.00 | 5.0/0.0/0.0 |

- Cache: A/B đều tải ảnh gốc, giải mã gốc; khác policy cache. So warm sau prime lạnh riêng. B có thể đọc đĩa khi ảnh gốc vượt RAM cache; không mặc định mọi warm là RAM.
- Downsampling: B/C cùng URL raw3000, cache lạnh, cùng chức năng; C giải mã theo ô.
- Thumbnail: C/D cùng cache lạnh và giải mã theo ô; D dùng tài nguyên720 thay raw3000.
- D/E dùng chi tiết1600; E thêm crossfade/preview: mới kiểm tra chức năng, chưa đo tách ảnh hưởng UX này.
- Không trộn load với scroll, không lấy các cặp load này để kết luận số frame giật trong cuộn. Mỗi số là median từng lượt; xem CSV để thấy biến động.
