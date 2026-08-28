# Tiếp nhận nguồn dataset ngày 28-08-2026

Thư mục này ghi lại kết quả kiểm tra báo cáo
`DATASET_SOURCES_DETAILED_REPORT.md`. Báo cáo đầu vào có SHA256:

`0ba52d63e7e78a8114a5392cfae1a84d5280a0678c590d87665351bb7542d60c`

## Nguyên tắc tiếp nhận

- File có nguồn, license, kích thước và SHA256 khớp được đánh dấu
  `VERIFIED_EXTERNAL`.
- Paper có DOI đúng nhưng chưa trích xuất từng giá trị được đánh dấu
  `SOURCE_VERIFIED_TARGETS_PENDING`.
- File chỉ xuất hiện trong phần mô tả nhưng không có trong workspace được đánh
  dấu `MISSING_FILE` hoặc `MISSING_FILES`.
- Không tái tạo JSON, tham số, kết quả thống kê hoặc calibration target từ phần
  mô tả bằng văn xuôi.
- Không thay đổi `review_status` trong `calibration_targets/targets.csv`.

## File

- `artifact_audit.csv`: tình trạng file và quyền sử dụng.
- `literature_source_review.csv`: kiểm tra metadata nguồn y văn.
- [`../../data/source_catalog.json`](../../data/source_catalog.json): catalog
  máy đọc được cho connectome và checkpoint đã xác minh.

Connectome/checkpoint lớn vẫn nằm ngoài Git. Dùng `scripts/fetch_brain_source.py`
để lấy lại từ commit cố định, sau đó dùng `scripts/check_neural_inputs.py` để
kiểm tra manifest và SHA256.
