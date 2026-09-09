# Cập nhật hoàn tất pipeline Riemensperger 2011

## Phạm vi

Đây là `PAPER_GUIDED_COMPUTATIONAL_REPLICATION`: kiểm tra perturbation cấp lớp dopamine có tái hiện hướng suy giảm locomotion của Riemensperger 2011 khi chạy qua neural core và FlyGym hay không. Đây không phải biological Parkinson validation, gene-specific validation, clinical validation hay drug validation.

## Trạng thái gate

| Gate | Trạng thái |
| --- | --- |
| 21A | `RIEMENSPERGER_2011_EVIDENCE_LOCKED` |
| 21B | `HEALTHY_VIRTUAL_REPLICATION_PASS` |
| 21C | `HEALTHY_COMPARABILITY_ACCEPTABLE_FOR_RATIO_ANALYSIS` |
| 21D | `READY_FOR_RIEMENSPERGER_DISEASE_REPLICATION` |
| 21E | `DOPAMINE_DEFICIENCY_VIRTUAL_REPLICATION_PASS` |
| 21F | `FOUR_GROUP_ANALYSIS_COMPLETE` |
| 21G | `ROBUSTNESS_EXECUTION_REQUIRED` |


Gate24E và Gate25 được giữ nguyên kết luận đã khóa. Gate21D chỉ được reconciliate từ evidence đã review; không có mapping gene-specific mới.

## Hợp đồng rollout

Healthy và disease dùng cùng seed `0,1,2,3,4`, 5000 steps, duration 0.5 s, timestep 0.0001 s, stimulus `p9`, CPG 12 Hz, world và controller. QC yêu cầu finite values, timestamp tăng đều, contact, joint trajectory và action trajectory thay đổi. Telemetry GPU được lưu theo seed nếu `nvidia-smi` khả dụng.

## Kết quả hiện tại

- Healthy: `HEALTHY_VIRTUAL_REPLICATION_PASS`; `5/5 seeds passed.
- Disease: `DOPAMINE_DEFICIENCY_VIRTUAL_REPLICATION_PASS`; `5/5 seeds passed.
- Four-group interpretation: `NOT_REPRODUCED`.
- Final decision: `NOT_REPRODUCED`.

## Checklist phê duyệt cuối

File signoff ở `research/validation/prospective/riemensperger_2011_final_reviewer_signoff.json` đã được reviewer có thẩm quyền duyệt với trạng thái `RIEMENSPERGER_FINAL_REVIEW_APPROVED` và quyết định `APPROVED_NOT_REPRODUCED_CLOSURE`. `gate26_closed = true`; review cuối được hoàn tất sau execution freeze và sau khi kết quả `NOT_REPRODUCED` đã được khóa.
