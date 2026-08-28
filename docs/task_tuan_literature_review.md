# Task dành cho Tuấn: Review dữ liệu phenotype và bàn giao calibration

## Mục tiêu

Đọc và kiểm tra thủ công các phenotype record đã được nhập từ literature, sau đó
ghi nhận quyết định review để nhóm có thể biết target nào đủ điều kiện cho
calibration hoặc holdout. Đây là công việc kiểm chứng provenance, không phải
tạo dữ liệu khoa học mới.

## Phạm vi bắt buộc

Review các file sau:

- `datasets/literature_phenotypes/paper_registry.csv`
- `datasets/literature_phenotypes/phenotype_records.csv`
- `datasets/literature_phenotypes/second_review_audit.csv`
- `datasets/literature_phenotypes/root_id_mapping_audit.csv`
- `research/paper_review/paper_analysis_vi.csv`
- `research/paper_review/paper_information.json`
- `calibration_targets/targets.csv`

Hiện có 6 paper và 14 phenotype record. Mỗi record phải được xem xét riêng,
không gộp nhiều phenotype vào một dòng.

## Quy tắc khoa học và bảo toàn dữ liệu

- Không tạo paper, DOI, PMID, số liệu, uncertainty, citation hoặc root ID.
- Không suy ra mapping gene-specific chỉ từ tên gene.
- Không sửa FlyGym, simulation, Disease Layer, Calibration Engine hoặc public API.
- Không dùng OCR hay đo chiều cao cột để tự tạo số nếu số liệu không được báo rõ.
- Không đổi median thành mean, SEM/SE thành SD, IQR thành SD.
- Không đổi climbing score, beam-break count hoặc activity count thành walking
  speed nếu paper không cung cấp phép quy đổi hợp lệ.
- Không bypass paywall. Nếu PDF không truy cập được, ghi rõ trạng thái thiếu
  provenance thay vì thay thế bằng nguồn không xác minh được.

## Bước 1: Chuẩn bị môi trường

Từ thư mục gốc repository:

```powershell
git pull --ff-only origin main
git switch -c review/tuan-literature-signoff
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
```

Nếu PowerShell chặn activation, có thể chạy Python trực tiếp:

```powershell
.\.venv\Scripts\python.exe scripts/audit_calibration_targets.py
```

## Bước 2: Đọc paper và kiểm tra từng record

Với từng `record_id`, đối chiếu paper gốc và điền hoặc xác nhận:

1. genotype
2. tuổi (ngày sau nở hoặc cách ghi nguyên văn)
3. giới tính
4. assay
5. metric
6. đơn vị
7. sample size
8. figure/table/supplementary
9. loại uncertainty
10. giá trị uncertainty
11. trạng thái supplementary
12. khả năng chuyển sang metric FlyGym

Nếu paper chỉ có mô tả định tính hoặc không ghi rõ trường nào, giữ giá trị
trống và ghi `NOT_REPORTED`/`PENDING_HUMAN_SIGNOFF` phù hợp. Phần ghi chú cần
nói rõ trang, hình hoặc bảng đã kiểm tra.

Các điểm cần đặc biệt cẩn thận:

- Riemensperger: walking speed là median; không đưa trực tiếp vào metric mean.
- Pokrzywa: xác nhận mốc tuổi và SE trước khi dùng cho calibration.
- Dumitrescu: DAM activity không tương đương walking speed.
- Pozo: giữ đúng loại spread được paper báo, không gán thành SD.
- Hwang: nếu giá trị chỉ nằm trên Figure 5E mà không có số trong text, không tự
  đọc số từ hình.
- Godena: xác nhận phạm vi motor neuron/VNC và nguồn mapping trước khi dùng.

## Bước 3: Điền review lần hai

Trong `research/paper_review/paper_analysis_vi.csv` và
`datasets/literature_phenotypes/second_review_audit.csv`, ghi:

- tên reviewer thật;
- ngày review thực tế theo định dạng `YYYY-MM-DD`;
- các trường uncertainty và assay transfer đã được kiểm tra;
- quyết định cho từng record.

Chỉ sử dụng các quyết định sau:

- `APPROVED_FOR_CALIBRATION`
- `APPROVED_FOR_HOLDOUT`
- `VALIDATION_ONLY`
- `NOT_COMPARABLE`
- `PENDING_HUMAN_SIGNOFF`

Không dùng `APPROVED_FOR_CALIBRATION` hoặc `APPROVED_FOR_HOLDOUT` nếu còn
thiếu provenance, uncertainty cần thiết, assay transfer hoặc đơn vị tương
thích. Nếu chỉ có thể đối chiếu định tính, dùng `VALIDATION_ONLY`.

## Bước 4: Kiểm tra root-ID mapping

Mỗi mapping được chấp nhận phải có đủ:

- `condition_id`
- `root_id`
- `neuron_name`
- `cell_type`
- `driver_scope`
- `connectome_version`
- `root_id_source`
- reviewer và ngày review
- `mapping_status`

Nguồn phải chỉ rõ FlyWire version, root ID, cell type, expression/driver scope
và nguồn xác nhận. Nếu chưa có bằng chứng gene-specific thì giữ trạng thái
exploratory hoặc pending; không điền root ID suy đoán.

## Bước 5: Cập nhật calibration targets

Chỉ cập nhật `calibration_targets/targets.csv` khi target đã được review đủ.
Target hợp lệ phải có:

```text
review_status=approved
```

và trong `notes` phải có thông tin tương tự:

```text
reviewer=<ten_that>;review_date=YYYY-MM-DD;allocation=calibration
```

hoặc:

```text
reviewer=<ten_that>;review_date=YYYY-MM-DD;allocation=holdout
```

Không đặt cùng một target vào cả calibration và holdout. Nếu chưa đủ thông tin,
giữ trạng thái chờ review; `WAITING_TARGET_DATA` là kết quả đúng, không phải
lỗi.

## Bước 6: Chạy audit và kiểm tra hồi quy

```powershell
python scripts/audit_calibration_targets.py
Get-Content results\calibration_readiness\target_audit.md
python -m compileall -q src scripts tests
pytest -q -rs -p no:cacheprovider
git diff --check
```

Chỉ khi audit trả `READY_FOR_CALIBRATION` và có ít nhất một target calibration
cùng một target holdout mới chạy bước so sánh:

```powershell
python scripts/compare_literature_targets.py `
  --metrics results\healthy_baseline\metrics.json `
  --targets calibration_targets\targets.csv `
  --output results\literature_comparison
```

`PASS` của phép so sánh chỉ có nghĩa là dữ liệu đủ để chạy phép tính. Nó không
phải là biological Parkinson validation, không phải chẩn đoán, không phải dự
đoán lâm sàng và không phải đánh giá thuốc.

## Bàn giao cần gửi lại

Gửi một commit hoặc pull request gồm:

- các CSV/JSON đã review;
- danh sách PDF đã kiểm tra và SHA256 nếu PDF được tải hợp lệ;
- bảng record nào được calibration, holdout, validation-only hoặc không tương
  thích;
- output của `audit_calibration_targets.py`;
- các blocker còn lại và lý do;
- kết quả compileall, pytest và `git diff --check`.

Không đưa `temporary/`, PDF cục bộ, `results/`, checkpoint, video hoặc môi
trường ảo vào commit. Các artifact đó phải được lưu ngoài Git hoặc được mô tả
bằng manifest/checksum phù hợp.

## Tiêu chí hoàn thành

Task chỉ được xem là hoàn thành khi:

- mọi record có provenance hoặc được đánh dấu pending;
- reviewer và ngày review là thông tin thật;
- quyết định calibration/holdout có căn cứ;
- root-ID mapping có nguồn xác minh hoặc được giữ pending;
- không có dữ liệu được bịa hoặc suy diễn;
- test và audit chạy thành công;
- nhóm có thể truy lại paper, figure/table và lý do của từng quyết định.
