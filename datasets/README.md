# Dataset nghiên cứu

Thư mục này chỉ lưu các bảng dữ liệu nhỏ, manifest và provenance cần để nhóm
nghiên cứu review cùng nhau. Connectome, checkpoint, PDF, supplementary gốc và
rollout lớn không được commit trực tiếp.

## Cấu trúc

- `source_intake/`: bản báo cáo nguồn do nhóm cung cấp và manifest kiểm định.
- `literature_phenotypes/`: các giá trị phenotype đã trích xuất ở mức candidate.

## Trạng thái khoa học

Các hàng trong `literature_phenotypes/phenotype_records.csv` chưa phải
calibration target đã phê duyệt. Chúng chỉ được chuyển sang
`calibration_targets/targets.csv` sau khi một reviewer khác kiểm tra bài gốc,
figure/table, assay, đơn vị, cỡ mẫu và uncertainty.

Không dùng dữ liệu trong thư mục này để tuyên bố mô hình Parkinson sinh học,
chẩn đoán, dự đoán lâm sàng hoặc đáp ứng thuốc.

## Dữ liệu lớn

Nguồn FlyWire v783 và checkpoint được lấy bằng commit cố định:

```powershell
python scripts/fetch_brain_source.py --output external/fly-brain
python scripts/check_neural_inputs.py `
  --brain-root external/fly-brain `
  --output results/neural_input_status.json
```

SHA256 chuẩn nằm trong [`../data/source_catalog.json`](../data/source_catalog.json).
