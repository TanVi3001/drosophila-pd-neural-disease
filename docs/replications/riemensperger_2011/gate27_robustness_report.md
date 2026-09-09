# Gate 27 - Riemensperger 2011 prospective robustness

## 1. Purpose

Gate27 kiểm tra độ bền của đáp ứng vận động trên burden grid đã preregister. Đây là thí nghiệm prospective mới, không phải cứu, retune hay diễn giải lại Gate26.

## 2. Relationship to closed Gate26

Gate26 giữ nguyên `NOT_REPRODUCED`, healthy `5/5 PASS`, disease burden 1.0 `5/5 PASS`, real ratio `0.7222222222222222` và virtual ratio `1.0`.

## 3. Prospective robustness question

Primary question: burden tăng có tạo median paired delta của `median_planar_speed_mm_s` nhỏ hơn 0 một cách nhất quán so với healthy cùng seed hay không?

## 4. Frozen burden grid

Grid: `[0.0, 0.25, 0.5, 0.75, 1.0]`. Gain: `{0.0: 1.0, 0.25: 0.7875, 0.5: 0.575, 0.75: 0.3625, 1.0: 0.15}`. Burden không đơn vị và không biểu diễn phần trăm dopamine mất, knockdown hay mức độ bệnh sinh học.

## 5. Endpoint reuse

Burden 0.0 dùng lại 5 healthy seeds Gate26; burden 1.0 dùng lại 5 disease seeds Gate26. Không rerun hai endpoint. Chỉ 15 job mới ở burden 0.25, 0.50 và 0.75.

## 6. Transform integrity

Transform audit `PASS`; target count `342`; targeted outgoing edges `69735`. Burden 0 tensor-identical với healthy; mọi burden dương thay đổi targeted edges theo gain đã khóa.

## 7. Fifteen new simulations

`15/15` job mới hoàn tất tuần tự, không retry và không thay seed. Protocol: 5000 steps, 0.5 s, timestep 0.0001 s, p9, CPG 12 Hz, CUDA, runtime profile `GATE24E_MEMORY_SAFE`.

## 8. QC

Mỗi rollout đạt finite values, timestamp monotonic, ground contact, joint trajectory và action trajectory thay đổi.

## 9. Seed-level results

Chi tiết 25 burden x seed nằm trong `experiments/gate_27_riemensperger_robustness/metrics/gate27_per_seed_grid.csv`. Seed là đơn vị thống kê; frame không phải replicate.

## 10. Grid summary

| Burden | Gain | n seeds | Median speed (mm/s) | Median paired delta | Direction pass |
| ---: | ---: | ---: | ---: | ---: | --- |
| 0.00 | 1.0000 | 5 | 2.58532086102 | 0 | `False` |
| 0.25 | 0.7875 | 5 | 2.58532086102 | 0 | `False` |
| 0.50 | 0.5750 | 5 | 2.58532086102 | 0 | `False` |
| 0.75 | 0.3625 | 5 | 2.58532086102 | 0 | `False` |
| 1.00 | 0.1500 | 5 | 2.58532086102 | 0 | `False` |

## 11. Monotonicity

Median speed non-increasing: `True`. Tất cả burden dương có median paired delta < 0: `False`.

## 12. Final robustness classification

`ROBUSTNESS_NO_IMPAIRMENT_ACROSS_GRID`

Gate26 vẫn là `NOT_REPRODUCED`, bất kể kết quả Gate27.

## 13. Downstream diagnostics

`DOWNSTREAM_TRACE_NOT_AVAILABLE`. Frozen Gate26 endpoint raw rollouts are not committed and were not duplicated; matched action/joint arrays are unavailable for read-only comparison.

## 14. Limitations

Rollout ảo dài 0.5 s, khác assay thật 15 phút. Mapping chỉ ở mức dopamine class exploratory. Paper không cung cấp uncertainty phù hợp. Distance chỉ là endpoint mô tả thứ cấp và không được phép ghi đè classification từ speed.

## 15. Claim boundaries

Không calibration, không parameter optimization, không chọn best burden, không quantitative validation, biological Parkinson validation, gene-specific validation, clinical validation hoặc drug validation.

## 16. Reproducibility

Freeze, transform audit, telemetry, seed-level metrics, summary, manifest và SHA256 nhẹ được lưu trong Gate27. Raw `.npz`, checkpoint `.pt` và logs giữ local ngoài Git.

## 17. Human review status

`WAITING_GATE27_RIEMENSPERGER_ROBUSTNESS_HUMAN_REVIEW`. Mã không tự phê duyệt hoặc đóng Gate27.
