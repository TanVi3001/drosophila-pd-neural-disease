# Gate 12 — Disease Condition Multi-Seed Rollouts

**Trạng thái:** `DISEASE_ROLLOUTS_BLOCKED`

## Input status

- Gate 09B: `READY_FOR_CALIBRATION` theo audit target hiện có.
- Gate 11: `HEALTHY_BASELINE_RUNTIME_PASS`.
- Metric contract: `PASS`.
- Healthy baseline duration: `0.49999999999996125 s`.
- Healthy baseline seeds: `0–5`.

## Scope

Gate 12 chỉ chạy computational disease perturbation rollouts. Không calibration, không holdout validation, không tune parameter và không dùng Chen/Pozo để khớp tham số.
Kết quả không phải biological Parkinson validation.

## Runtime gate

- Runtime artifact: `AVAILABLE`

## Conditions

| Condition | Status | Seeds PASS / planned | Mapping scope | Reason |
| --- | --- | ---: | --- | --- |
| `alpha_synuclein` | `SKIPPED` | 0 / 6 | `not_available` | MISSING_DISEASE_ARTIFACT: condition_status=WAITING_TARGET_DATA; target_neurons_or_edges_missing; burden_curve_missing; full_burden_missing; condition_provenance_missing; reviewed_mapping_or_checkpoint_provenance_missing; mapping_status=WAITING_REVIEWED_ROOT_ID_MAPPING; blocker=Pan-neuronal driver chưa phải reviewed root-ID set gene-specific. |
| `pink1` | `SKIPPED` | 0 / 6 | `not_available` | MISSING_DISEASE_ARTIFACT: condition_status=WAITING_TARGET_DATA; target_neurons_or_edges_missing; burden_curve_missing; full_burden_missing; condition_provenance_missing; reviewed_mapping_or_checkpoint_provenance_missing; mapping_status=WAITING_REVIEWED_ROOT_ID_MAPPING; blocker=Thiếu cell-specific or explicitly approved model scope; target chưa approved. |
| `parkin` | `SKIPPED` | 0 / 6 | `not_available` | MISSING_DISEASE_ARTIFACT: condition_status=WAITING_TARGET_DATA; target_neurons_or_edges_missing; burden_curve_missing; full_burden_missing; condition_provenance_missing; reviewed_mapping_or_checkpoint_provenance_missing; mapping_status=WAITING_REVIEWED_ROOT_ID_MAPPING; blocker=TH-GAL4 chưa có reviewed root-ID set; DAM không tương đương speed. |
| `dj1` | `SKIPPED` | 0 / 6 | `not_available` | MISSING_DISEASE_ARTIFACT: condition_status=WAITING_TARGET_DATA; target_neurons_or_edges_missing; burden_curve_missing; full_burden_missing; condition_provenance_missing; reviewed_mapping_or_checkpoint_provenance_missing; mapping_status=NOT_MAPPABLE_FROM_PAPER; blocker=Paper chỉ cung cấp climbing evidence; không suy ra root IDs. |
| `lrrk2` | `SKIPPED` | 0 / 6 | `not_available` | MISSING_DISEASE_ARTIFACT: condition_status=WAITING_TARGET_DATA; target_neurons_or_edges_missing; burden_curve_missing; full_burden_missing; condition_provenance_missing; reviewed_mapping_or_checkpoint_provenance_missing; mapping_status=NOT_MAPPABLE_TO_CURRENT_CONNECTOME; blocker=Thiếu phạm vi VNC/motor neuron và target climbing/flight tương thích. |

## Metrics

Chưa có disease metric nào được ghi nhận: mọi condition đều bị skip hoặc chưa qua QC. Không tạo metric giả.

## Healthy comparison

Chưa thực hiện so sánh vì chưa có disease rollout PASS. Healthy baseline vẫn được giữ nguyên làm reference.

## Limitations

- Duration hiện tại khoảng 0,5 giây, ngắn hơn nhiều behavioral assay trong literature.
- Condition gene chỉ được gọi là gene-specific khi mapping có provenance gene-specific; class-level/organism-level không được gọi như vậy.
- Đây là computational perturbation, chưa phải calibration và chưa phải holdout validation.
- Không suy ra cơ chế Parkinson sinh học, chẩn đoán, clinical prediction hay đáp ứng thuốc.

## Final status

`DISEASE_ROLLOUTS_BLOCKED`. Không calibration và không holdout validation đã được chạy trong Gate 12.
