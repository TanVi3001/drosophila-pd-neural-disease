# Step 2: Disease Neural Branch

## Mục đích

Step này tạo một manifest tham chiếu cho nhánh disease tách khỏi healthy core. Nhánh disease chỉ mô tả condition, mapping, quy tắc perturbation và nguồn chứng cứ; nó không ghi đè checkpoint healthy và không chạy mô phỏng.

## Luồng kiểm soát

```text
healthy core lock
        |
        +--> disease branch manifest
              +--> condition metadata
              +--> neuron/edge mapping
              +--> perturbation rule
              +--> burden curve
              +--> provenance và checkpoint parent
```

Chạy:

```powershell
py -3.12 scripts/prepare_disease_neural_branch.py `
  --core-lock results/neural_core_lock/healthy_neural_core_lock.json `
  --config configs/conditions/dopamine_deficiency.exploratory.yaml `
  --annotations annotations/neuron_annotations.csv `
  --mapping-audit datasets/literature_phenotypes/root_id_mapping_audit.csv `
  --output results/neural_branches/dopamine_deficiency_exploratory/branch_manifest.json
```

`DISEASE_NEURAL_BRANCH_READY` hiện chỉ có nghĩa là đủ cấu trúc cho một nhánh perturbation tính toán. Condition dopamine hiện là `class_level_exploratory`; không được gọi là gene-specific hay biological Parkinson validation. Các template PINK1, Parkin, DJ-1, LRRK2 và alpha-synuclein tiếp tục chờ mapping được review.

## Điều kiện không đạt

Nếu thiếu parent lock, target neuron/edge, burden curve, provenance, annotation hoặc mapping audit phù hợp, manifest giữ trạng thái `WAITING_*`. Đây là cơ chế bảo vệ dữ liệu, không phải lỗi cần sửa bằng cách điền giả.
