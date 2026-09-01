# Gate 09A - Metric Review Scaffold Report

## Mục đích

Gate 09A tạo cấu trúc thư mục và biểu mẫu chuẩn để reviewer phân tích metric
của Chen 2014, Pokrzywa 2017 và Pozo 2022 trước khi thực hiện Gate 09B.

## Files được tạo

- `README.md`
- `metric_review_checklist.md`
- `chen_2014_metric_review_template.csv`
- `pokrzywa_2017_metric_review_template.csv`
- `pozo_2022_metric_review_template.csv`
- `gate_09_signoff_template.md`
- `target_rows_draft_template.csv`

## Quyết định dữ liệu

- Không tạo approved row mới.
- Không sửa `calibration_targets/targets.csv`.
- Tất cả draft row giữ `review_status=pending` hoặc trường signoff ở trạng
  thái `pending`/`CHUA_DIEN`.
- Chen là calibration candidate dự kiến.
- Pozo là distance holdout candidate dự kiến.
- Pokrzywa là calibration fallback và vẫn phụ thuộc exact independent-vial
  count.

## Expected validation state

- Audit tiếp tục trả `WAITING_TARGET_DATA`.
- Không chạy simulation.
- Không chạy calibration.
- Không chạy holdout validation.
- Gate 09A không phải biological Parkinson validation và không phải clinical
  diagnosis.

## Bước tiếp theo

Reviewer cần đọc trực tiếp PDF, figure, table và supplementary; điền metric,
uncertainty, sample size, assay transfer, reviewer và review date. Chỉ sau khi
đủ evidence mới được xử lý Gate 09B.
