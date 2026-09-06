# Gate 20A: Disease mapping readiness

Gate 20A kiểm tra điều kiện mở disease multi-seed neural-first. Gate đọc `root_id_mapping_audit.csv`, `mapping_status.csv` và condition YAML; nó không tạo root ID, không suy ra gene scope và không chạy simulation.

## Kết quả hiện tại

Chạy:

```powershell
py -3.12 scripts/audit_disease_mapping_readiness.py
```

Kết quả hiện tại là `DISEASE_MAPPING_BLOCKED` cho năm condition mục tiêu:

- alpha-synuclein: `WAITING_REVIEWED_MAPPING`;
- PINK1: `WAITING_MODEL_SCOPE_REVIEW`;
- Parkin: `WAITING_REVIEWED_MAPPING`;
- DJ-1: `WAITING_MODEL_SCOPE_REVIEW`;
- LRRK2: `WAITING_MODEL_SCOPE_REVIEW`.

Dopamine deficiency được ghi là `class_level_exploratory`, có thể dùng làm reference computational nhưng không phải gene-specific Parkinson model.

## Hồ sơ cần bổ sung

Để một condition chuyển sang `READY_FOR_DISEASE_BRANCH`, nhóm cần cung cấp root ID/edge ID hoặc scope class-level được phê duyệt, cell type/driver scope, FlyWire/connectome version, nguồn mapping, reviewer, ngày review, target trong config, perturbation rule, burden curve và provenance. Tất cả phải trỏ tới bằng chứng thật.

Không được lấy toàn bộ neuron dopamine làm mapping gene-specific chỉ vì paper nói đến dopamine; cũng không thay brain-only annotation cho motor neuron/VNC của LRRK2.

## Artifact

- `experiments/gate_20a_disease_mapping/results/disease_mapping_readiness.csv`;
- `experiments/gate_20a_disease_mapping/results/disease_mapping_readiness.md`;
- `experiments/gate_20a_disease_mapping/manifests/disease_mapping_readiness_manifest.json`.

Gate này không chạy calibration, holdout hay disease simulation. Sau khi có mapping hợp lệ, chạy lại Gate 20A, rồi mới materialize branch/checkpoint và chạy smoke trước multi-seed.
