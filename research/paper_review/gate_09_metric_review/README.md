# Gate 09 Metric Review Scaffold

Thư mục này chuẩn bị form chuẩn để reviewer phân tích thủ công các candidate
target trước khi cập nhật `calibration_targets/targets.csv`.

Gate 09A chỉ tạo scaffold và template. Task này không approve target, không
chuyển audit sang `READY_FOR_CALIBRATION`, không chạy simulation và không chạy
calibration.

## Candidate chính

1. **Chen 2014 adult horizontal walking speed**
   - Ứng viên calibration dự kiến.
   - Metric nguồn: `mean_walking_velocity_cm_s`.
   - Metric có thể quy đổi: `mean_planar_speed_mm_s`.
   - Chỉ đổi `cm/s` sang `mm/s` khi reviewer xác nhận phép đổi đơn vị vật lý.
   - Giữ `CI95` là `CI95`, không đổi thành `SE`.

2. **Pozo 2022 Pink1B9 distance**
   - Ứng viên holdout dự kiến.
   - Metric giữ nguyên: `distance_traveled_mm`.
   - Không đổi distance thành speed.
   - Không đổi IQR/min-max thành SD hoặc SE.

3. **Pokrzywa 2017 alpha-synuclein speed**
   - Ứng viên calibration dự phòng.
   - Chỉ dùng nếu exact independent-vial count và SE được reviewer xác nhận.

## Cách sử dụng

1. Đọc PDF, figure, table và supplementary tương ứng.
2. Điền một template cho từng paper.
3. Đánh dấu rõ trường nào chưa xác định được.
4. Reviewer ghi tên thật, ngày review thật và quyết định transfer.
5. Chỉ sau khi đủ evidence mới xem xét Gate 09B và cập nhật target chính thức.

## Ranh giới khoa học

`READY_FOR_CALIBRATION`, nếu đạt ở task sau, chỉ có nghĩa là đủ target y văn
đã review cho computational calibration readiness. Đây không phải biological
Parkinson validation, clinical diagnosis, drug efficacy validation hoặc thay
thế wet-lab experiments.
