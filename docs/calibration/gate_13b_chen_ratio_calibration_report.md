# Gate 13B - Chen-only Ratio Calibration

## Mục tiêu

Gate 13B khóa một lựa chọn calibration rời rạc bằng target Chen 2014, sử dụng tỷ lệ tốc độ đi bộ disease/control.

## Trạng thái input

- Gate 12G integrated proxy rollouts: đã có summary alpha-synuclein với 6 seed cho mỗi mức burden.
- Gate 13A objective: Chen-only ratio objective đã sẵn sàng.
- Audit: `READY_FOR_CALIBRATION`.
- Không dùng Pozo và không dùng PINK1 cho calibration.

## Chen target

- Disease A30P speed: `4.875 mm/s`.
- Control Old CT speed: `7.275 mm/s`.
- Ratio target: `0.6701030927835051`.
- Uncertainty: `0.525 CI95`; CI95 không bị đổi thành SE.
- Sample size: `n=20 fly`.

## Calibration method

- Method: `discrete_grid_selection` trên các rollout Gate 12G đã tồn tại.
- Control burden: `0.0`.
- Candidate burdens: `0.25, 0.5, 0.75, 1.0`.
- Objective: giảm nhỏ nhất `abs(simulated_ratio_to_burden0 - chen_ratio_target)`.
- Absolute speed chỉ là reference, không phải objective chính.
- Không tối ưu liên tục và không chạy simulation mới.

## Calibration result

| Burden | Speed mean (mm/s) | Speed std | Ratio | Ratio error | Rank | Selected | Usable |
|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 0 | 1.7779315915 | 0.210725340995 | 1 | 0.329896907216 | - | no | no |
| 0.25 | 1.46318546229 | 0.229246002192 | 0.822970618943 | 0.152867526159 | 2 | no | yes |
| 0.5 | 1.04119440742 | 0.2638135337 | 0.585621186102 | 0.0844819066814 | 1 | yes | yes |
| 0.75 | 0.504226783259 | 0.339282999165 | 0.283603028188 | 0.386500064596 | 3 | no | yes |
| 1 | 3.75631720919 | 1.23185009645 | 2.11274563495 | 1.44264254217 | 4 | no | yes |

## Selected parameter

- Selected `proxy_burden_level`: `0.5`.
- Selected simulated ratio: `0.585621186102`.
- Selected ratio error: `0.0844819066814`.
- Absolute speed error (reference only): `3.83380559258 mm/s`.
- Burden `0.5` là closest available discrete-grid candidate theo ratio error; đây không phải perfect fit.

## Boundary

Đây là computational proxy calibration ở phạm vi organism-level locomotion. Không phải gene-specific mapping, không phải biological Parkinson validation, không phải chẩn đoán lâm sàng và không phải đánh giá thuốc.
- Không phải biological Parkinson validation.
- Không chạy holdout validation trong Gate 13B.
- Không dùng Pozo; target Pozo vẫn được giữ cho holdout độc lập ở Gate 14.
- Không dùng PINK1, Parkin, DJ-1 hoặc LRRK2 trong objective calibration này.

## Final status

`CHEN_RATIO_CALIBRATION_PASS`

Nếu status PASS, Gate 13C có thể chạy calibrated rerun để kiểm tra lại rollout bằng cấu hình đã khóa; đây không phải holdout và không phải biological validation.
