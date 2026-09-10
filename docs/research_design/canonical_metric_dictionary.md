# Canonical Metric Dictionary

Các endpoint dưới đây là các đại lượng khác nhau và không được tự động đổi
tên cho nhau:

| Canonical metric | Đơn vị | Quy tắc chính |
| --- | --- | --- |
| `mean_planar_speed_mm_s` | mm/s | Chỉ so sánh với mean planar speed |
| `median_planar_speed_mm_s` | mm/s | Giữ median; không đổi thành mean |
| `distance_traveled_mm` | mm | Không đổi thành speed |
| `displacement_mm` | mm | Không đồng nhất với path distance |
| `activity_time_s` | s | Phụ thuộc movement threshold |
| `percent_moving` | percent | Cần khai báo mẫu số và threshold |
| `climbing_success_fraction` | fraction | Không phải planar speed |
| `geotactic_index` | assay-specific | Cần công thức assay |
| `turn_rate` | turns/s | Cần bộ phân loại turn |
| `heading_change` | degree/radian | Cần quy tắc unwrap góc |
| `gait_concurrency` | count/fraction | Cần leg-event classifier |
| `swing_duration` | s | Endpoint gait riêng |
| `stance_duration` | s | Endpoint gait riêng |

Mean, median, SD, SE, SEM, CI, IQR và range luôn được lưu theo đúng loại
paper báo cáo. Default của Generation 2 là
`NO_IMPLICIT_STATISTIC_CONVERSION`.
