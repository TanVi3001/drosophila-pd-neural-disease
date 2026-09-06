# Gate 20B - Real Mapping Provenance Report

## 1. Objective

Gate 20B tạo package provenance cho mapping disease, nhưng không chạy GPU, simulation, calibration hoặc tuning.
Mục tiêu là phân biệt mapping thật, mapping class-level và khoảng trống provenance trước khi mở disease rollout.

## 2. Starting status

- Gene-specific mapping review: `MAPPING_REVIEW_BLOCKED`.
- Disease mapping: `DISEASE_MAPPING_BLOCKED`.
- Mapping identifier count trước Gate 20B: `0` cho 5 condition disease.
- Condition được duyệt trước Gate 20B: `0/5`.

## 3. Evidence source policy

Chỉ chấp nhận root ID/edge ID từ FlyWire annotations, Codex query/export, connectome annotation hoặc paper/supplementary có mapping cụ thể.
Không suy ra ID từ gene name, genotype, driver name, phenotype hoặc hành vi. Bảng annotation local được ghi hash để truy vết, nhưng không được coi là mapping condition-specific.
Nguồn công khai được ghi trong từng `source_manifest.json`: FlyWire annotations và Codex documentation/query path.

## 4. Condition review table

| Condition | Mapping level | Identifier count | Decision | Rollout scope | Blocker |
| --- | --- | ---: | --- | --- | --- |
| `alpha_synuclein` | `PAN_NEURONAL_ORGANISM_LEVEL` | `0` | `MODEL_SCOPE_NOT_CELL_SPECIFIC` | `ORGANISM_LEVEL_PROXY_ONLY` | Pan-neuronal expression does not identify a reviewed condition-specific root-ID set. |
| `pink1` | `WHOLE_ANIMAL_ORGANISM_LEVEL` | `0` | `MODEL_SCOPE_NOT_CELL_SPECIFIC` | `ORGANISM_LEVEL_PROXY_ONLY` | The whole-animal mutant does not identify a reviewed neuron or edge intervention. |
| `parkin` | `DRIVER_OR_CLASS_LEVEL` | `0` | `WAITING_REVIEWED_ROOT_ID_MAPPING` | `CLASS_LEVEL_EXPLORATORY_ONLY` | TH-GAL4 describes a class, but no reviewed TH-GAL4-to-FlyWire export is present. |
| `dj1` | `NOT_MAPPABLE_FROM_PAPER` | `0` | `NOT_MAPPABLE_FROM_PAPER` | `VALIDATION_ONLY` | Behavioral evidence does not specify a neuron or edge intervention. |
| `lrrk2` | `WAITING_VNC_CONNECTOME_MAPPING` | `0` | `WAITING_VNC_CONNECTOME_MAPPING` | `VALIDATION_ONLY` | The cited scope requires motor-neuron/VNC coverage that is not present in the current brain-only catalog. |

## 5. Approved or ready condition

Chưa có condition nào được approve. Không condition nào có root ID hoặc edge ID thật được review cho disease intervention trong package này.
Vì vậy Gate 21 disease rollout chưa được mở; trạng thái đúng là `MAPPING_REVIEW_BLOCKED_WITH_PROVENANCE_GAP` và `DISEASE_MAPPING_BLOCKED`.
Parkin là ứng viên class-level đáng ưu tiên kiểm tra tiếp, nhưng vẫn cần export TH-GAL4/driver-to-root và reviewer signoff riêng.

## 6. YAML updates

Các condition YAML hiện vẫn là template không có target_neurons/target_edges. Gate 20B không thêm ID giả và không ghi đè healthy core.
Mỗi package mapping export chỉ chứa một dòng metadata với identifier để trống; source manifest ghi rõ đây là reference-only.

## 7. Audit result

- `audit_gene_specific_mapping_review.py`: `MAPPING_REVIEW_BLOCKED`.
- `audit_disease_mapping_readiness.py`: `DISEASE_MAPPING_BLOCKED`.
- `audit_calibration_targets.py`: `READY_FOR_CALIBRATION` độc lập với disease mapping.
- Không có simulation, calibration, tuning hoặc raw metric modification.

## 8. Exact evidence still required

1. Filtered FlyWire/Codex export có root ID hoặc edge ID thật cho từng intervention scope.
2. Connectome version, cell type, anatomy scope và driver/expression scope của export.
3. SHA-256 của export và query/export date.
4. Reviewer thứ hai xác nhận scope và ký duyệt.
5. Riêng LRRK2 cần VNC/motor-neuron mapping tương thích nếu muốn mở locomotion rollout.

## 9. Scientific boundary

Gate 20B chỉ xác nhận provenance/readiness của mapping tính toán.
Gate này không xác nhận Parkinson sinh học, không xác nhận gene-specific disease mechanism, không phải clinical validation và không phải drug validation.
Không được dùng package này để kết luận rằng disease rollout đã chạy hoặc đã có disease metrics.
