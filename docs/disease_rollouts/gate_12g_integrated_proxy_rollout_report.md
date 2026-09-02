# Gate 12G - Integrated Proxy Disease Rollout Report

**Trạng thái:** `INTEGRATED_PROXY_ROLLOUTS_PASS`

Báo cáo này ghi nhận rollout computational của proxy organism-level qua action hook FlyGym thật.
Không phải biological Parkinson validation, không phải chẩn đoán, dự đoán lâm sàng hoặc đánh giá thuốc.

## Phạm vi và đầu vào

- Condition chạy: `alpha_synuclein`, `pink1`.
- Scope: `organism_level_proxy`; không có gene-specific mapping.
- Condition nền của runner: `healthy`; proxy được áp ở action-level hook.
- Calibration, holdout validation, Chen tuning và Pozo tuning: `OFF`.
- Planned runs: `60`.

## Runtime và operator

- CUDA available: `True`.
- External patch verified: `True`.
- Operator config SHA256: `ed1f4674419f14a90987fdf397e93d1a67de5a2c6606edc79acdbf7d358c4de5`.
- Operator chỉ thay đổi `joint_angles`; `adhesion_onoff` không bị thay đổi.
- burden=0 kiểm tra identity; burden>0 yêu cầu action hash thay đổi.

## Kết quả theo burden

| Condition | Burden | PASS | Speed mean (mm/s) | Distance mean (mm) | Displacement mean (mm) | QC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `alpha_synuclein` | 0.0 | 6 | 1.77793159 | 1.52770774 | 0.888965796 | 6 |
| `alpha_synuclein` | 0.25 | 6 | 1.46318546 | 1.39682669 | 0.731592731 | 6 |
| `alpha_synuclein` | 0.5 | 6 | 1.04119441 | 1.39770692 | 0.520597204 | 6 |
| `alpha_synuclein` | 0.75 | 6 | 0.504226783 | 1.76939963 | 0.252113392 | 6 |
| `alpha_synuclein` | 1.0 | 6 | 3.75631721 | 5.25654715 | 1.8781586 | 6 |
| `pink1` | 0.0 | 6 | 1.77793159 | 1.52770774 | 0.888965796 | 6 |
| `pink1` | 0.25 | 6 | 1.46318546 | 1.39682669 | 0.731592731 | 6 |
| `pink1` | 0.5 | 6 | 1.04119441 | 1.39770692 | 0.520597204 | 6 |
| `pink1` | 0.75 | 6 | 0.504226783 | 1.76939963 | 0.252113392 | 6 |
| `pink1` | 1.0 | 6 | 3.75631721 | 5.25654715 | 1.8781586 | 6 |

## Healthy baseline tham chiếu

- Healthy mean_planar_speed_mm_s: `1.77793159`.
- Healthy distance_traveled_mm: `1.52770774`.
- Healthy displacement_mm: `0.888965796`.
- Các giá trị trên chỉ là tham chiếu computational; không được diễn giải như biological effect.

## Blockers hoặc lỗi

- Không có blocker runtime nào được ghi nhận.

## Giới hạn khoa học

- Đây là organism-level computational proxy rollout, không phải mapping gene-specific.
- Proxy burden là dimensionless và chưa được dùng để fit Chen hoặc đánh giá Pozo.
- Thời lượng mô phỏng theo Gate 11 khoảng 0.5 giây; không phải diễn tiến bệnh theo thời gian sinh học.
- Không có calibration, holdout validation hoặc biological Parkinson validation trong Gate 12G.

## Final status

`INTEGRATED_PROXY_ROLLOUTS_PASS`.
