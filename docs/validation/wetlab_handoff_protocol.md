# Wet-lab handoff protocol for Parkin validation

Tài liệu này là handoff protocol, không phải kết quả thí nghiệm. Nhóm thực
hiện phải tuân thủ quy định và phê duyệt của cơ sở nghiên cứu.

## Hypothesis

Một can thiệp Parkin được định nghĩa chính xác có thể tạo ra thay đổi vận động
đo được ở ruồi giấm; mô hình ảo sẽ dự đoán chiều thay đổi trước khi mở dữ liệu
held-out.

## Required design

- Ghi chính xác allele, RNAi line hoặc transgene và driver.
- Dùng control có matched genetic background, sex, age và assay.
- Xác định biological replicate trước khi thu dữ liệu; frame không phải replicate.
- Khóa primary endpoint, exclusion rule, uncertainty và direction trước khi mở holdout.
- Blinding người xử lý dữ liệu khi có thể.
- Không dùng validation data để calibration hoặc tuning.

## Intake format

Dữ liệu gửi vào phải theo `research/validation/biological/parkin_biological_data_contract.yaml`.
Mỗi dòng cần `sample_id`, `biological_replicate`, provenance, source/DOI, raw-data
path và metadata assay đầy đủ. Nếu không có uncertainty, ghi `NOT_REPORTED`,
không suy ra SD/SE từ biểu đồ.

## Exclusion and provenance

Các nguồn `SYNTHETIC`, `GENERATED` và `SIMULATION_AS_REAL` bị importer từ chối.
Không chuyển DAM beam-break count thành mm/s nếu chưa có policy assay-transfer
được reviewer phê duyệt.

## Import and review

```powershell
py -3.12 scripts/import_gene_specific_biological_validation.py `
  --input <reviewed-biological-table.csv>
py -3.12 scripts/audit_gene_specific_validation_readiness.py
```

Importer chỉ kiểm tra và ghi manifest; nó không sinh measurement sinh học.
