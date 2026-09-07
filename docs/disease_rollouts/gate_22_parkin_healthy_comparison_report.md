# Gate 22: So sánh Parkin proxy class-level với Healthy baseline

**Trạng thái:** `PARKIN_HEALTHY_COMPARISON_PASS`

Gate 22 là phân tích hậu nghiệm trên các bảng metric nhỏ đã được lưu từ Gate 11 và Gate 21. Gate này không chạy GPU, không chạy simulation, không calibration và không holdout validation.

## Thiết kế

- Đơn vị phân tích: một cặp rollout ghép cùng `seed`.
- Seed sử dụng: `0, 1, 2, 3, 4`; Healthy seed `5` được giữ trong baseline nhưng loại khỏi paired comparison vì Gate 21 chỉ chạy seed `0–4`.
- So sánh: `delta = Parkin_proxy - Healthy`; standardized delta = trung bình delta chia cho sample SD của các delta ghép cặp.
- Các con số là thống kê mô tả trên 5 seed, không phải uncertainty sinh học và không phải kiểm định xác nhận bệnh.
- Mapping vẫn là `class_level_exploratory`; không diễn giải là Parkin gene-specific.

## Kết quả metric chính

| Burden | Metric | n | Healthy mean | Proxy mean | Delta | Paired standardized delta | QC |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 0 | `mean_planar_speed_mm_s` | 5 | 1.6999509 | 1.6999509 | 0 | 0 | `PASS` |
| 0 | `distance_traveled_mm` | 5 | 1.5260506 | 1.5260506 | 0 | 0 | `PASS` |
| 0 | `displacement_mm` | 5 | 0.84997546 | 0.84997546 | 0 | 0 | `PASS` |
| 0.25 | `mean_planar_speed_mm_s` | 5 | 1.6999509 | 1.7086755 | 0.0087245601 | 0.47017258 | `PASS` |
| 0.25 | `distance_traveled_mm` | 5 | 1.5260506 | 1.5320377 | 0.0059871191 | 0.48049298 | `PASS` |
| 0.25 | `displacement_mm` | 5 | 0.84997546 | 0.85433774 | 0.00436228 | 0.47017258 | `PASS` |
| 0.5 | `mean_planar_speed_mm_s` | 5 | 1.6999509 | 1.6959417 | -0.004009254 | -0.47785426 | `PASS` |
| 0.5 | `distance_traveled_mm` | 5 | 1.5260506 | 1.5251347 | -0.00091593763 | -0.16848184 | `PASS` |
| 0.5 | `displacement_mm` | 5 | 0.84997546 | 0.84797084 | -0.002004627 | -0.47785426 | `PASS` |
| 0.75 | `mean_planar_speed_mm_s` | 5 | 1.6999509 | 1.7021878 | 0.0022368637 | 0.11464285 | `PASS` |
| 0.75 | `distance_traveled_mm` | 5 | 1.5260506 | 1.5285525 | 0.0025018962 | 0.22334501 | `PASS` |
| 0.75 | `displacement_mm` | 5 | 0.84997546 | 0.8510939 | 0.0011184318 | 0.11464285 | `PASS` |
| 1 | `mean_planar_speed_mm_s` | 5 | 1.6999509 | 1.6958509 | -0.0041000123 | -0.49152024 | `PASS` |
| 1 | `distance_traveled_mm` | 5 | 1.5260506 | 1.5248042 | -0.0012463983 | -0.24621463 | `PASS` |
| 1 | `displacement_mm` | 5 | 0.84997546 | 0.84792546 | -0.0020500062 | -0.49152024 | `PASS` |

## Đọc kết quả

Gate 21 đã đạt QC rollout, nên phép ghép và tính toán của Gate 22 hoàn tất. Tuy nhiên, các burden trong Gate 21 không tạo ra xu hướng đơn điệu rõ ràng trên metric chính; kết quả này chỉ xác nhận pipeline so sánh hoạt động và ghi nhận response quan sát được của proxy. Nó không chứng minh Parkin gây ra phenotype sinh học, không chứng minh mapping gene-specific và không thay thế dữ liệu ruồi thật.

## Provenance

- Healthy metrics: `experiments/gate_11_healthy_baseline/results/healthy_baseline_metrics.csv`
- Healthy manifest: `experiments/gate_11_healthy_baseline/manifests/healthy_baseline_manifest.json`
- Gate 21 metrics: `experiments/gate_21_parkin_class_level_rollout/manifests/gate21_execution_metrics.csv`
- Gate 21 manifest: `experiments/gate_21_parkin_class_level_rollout/manifests/gate21_execution_manifest.json`

## Ranh giới

Không dùng Chen hoặc Pozo ở Gate 22. Không có calibration, tuning, holdout validation, biological Parkinson validation, clinical prediction hay drug validation.
