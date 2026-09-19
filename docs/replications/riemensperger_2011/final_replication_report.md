# Tái lập computational Riemensperger 2011

## 1. Câu hỏi nghiên cứu

Liệu perturbation cấp lớp neuron dopamine, được xây dựng từ bằng chứng Riemensperger 2011 và chạy qua neural core/FlyGym, có tái hiện được hướng thay đổi locomotion của ruồi thật hay không?

## 2. Bằng chứng từ paper

- DTHg; ple: median speed 10.8 mm/s.
- DTHgFS+/-; ple: median speed 7.8 mm/s.
- WT: median speed 15 mm/s, dùng như tham chiếu thứ cấp.
- Khoảng cách trong 15 phút: control 425 cm và disease 193 cm.
- Uncertainty của paper: `NOT_REPORTED`; không tạo SD, SE, CI hoặc p-value.

## 3. Thiết kế bốn nhóm

`A` = real DTHg; ple control; `B` = virtual healthy; `C` = real DTHgFS+/-; ple dopamine-deficient; `D` = virtual dopamine-class perturbation.

## 4. Mapping và neural transform

Mapping là `DOPAMINE_CLASS_LEVEL_EXPLORATORY` với 342 target IDs, không phải gene-specific. Transform là presynaptic connectome-weight hypothesis với burden `1.0`. Burden là tham số không đơn vị, không phải phần trăm dopamine mất. Healthy checkpoint không bị ghi đè.

## 5. Runtime và protocol

Runtime `655e854544e3d814dfe422883ff0de66b619d6c1`, profile `GATE24E_MEMORY_SAFE`, FlyGym 2.1.0, thiết bị CUDA. Cả hai nhánh dùng seed 0-4, 5000 steps, timestep 0.0001 s, stimulus p9, CPG 12 Hz và cùng world/controller. Scientific command không dùng video CLI, compare-to hoặc visualization.

## 6. Trạng thái execution

| Gate | Trạng thái |
| --- | --- |
| 21A | `RIEMENSPERGER_2011_EVIDENCE_LOCKED` |
| 21B | `HEALTHY_VIRTUAL_REPLICATION_PASS` |
| 21C | `HEALTHY_COMPARABILITY_ACCEPTABLE_FOR_RATIO_ANALYSIS` |
| 21D | `READY_FOR_RIEMENSPERGER_DISEASE_REPLICATION` |
| 21E | `DOPAMINE_DEFICIENCY_VIRTUAL_REPLICATION_PASS` |
| 21F | `FOUR_GROUP_ANALYSIS_COMPLETE` |
| 21G | `ROBUSTNESS_EXECUTION_REQUIRED` |


Healthy passed seeds: `5/5`.

Disease passed seeds: `5/5`.

## 7. Phân tích four-group

- Real direction ratio: 7.8 / 10.8 = 0.722222...
- Virtual direction ratio: `1.0`.
- Decision: `NOT_REPRODUCED`.
- Diễn giải chỉ mô tả directionality và magnitude; không tuning theo kết quả real disease, không hậu nghiệm đổi threshold.

## 8. Giới hạn và claim lock

Virtual duration là 0.5 s, khác assay 15 phút; statistic và unit of analysis cũng khác; paper không báo uncertainty. Vì vậy không claim quantitative validation, parameter equivalence, gene-specific validation, biological Parkinson validation, clinical validation hoặc drug validation. Frame không phải replicate; seed là đơn vị thống kê.

Gate24E vẫn giữ `NEGATIVE_VALIDATION_RESULT` và `DIRECTIONAL_CROSS_ASSAY_DISCORDANCE`. Gate25-R2 vẫn giữ reproducibility freeze đã khóa.

## 9. Reproducibility và human review

Per-seed metrics, manifest, telemetry GPU, checksum và execution freeze được lưu trong Gate26. Raw rollout lớn giữ ngoài Git và không commit. Final signoff là `RIEMENSPERGER_FINAL_REVIEW_APPROVED`, với quyết định `APPROVED_NOT_REPRODUCED_CLOSURE`; Gate26 đã `CLOSED` sau khi kết quả `NOT_REPRODUCED` được khóa.
