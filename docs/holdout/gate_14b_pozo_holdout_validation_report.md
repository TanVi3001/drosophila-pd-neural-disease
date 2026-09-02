# Gate 14B - Pozo Ratio Holdout Validation Run

## Mục tiêu

Gate 14B chạy holdout evaluation cho Pozo 2022 bằng PINK1 organism-level
computational proxy, với parameter đã khóa từ Chen calibration. Đây là
computational proxy holdout check, không phải biological Parkinson validation.

## Input và lock

- Gate 13B: `CHEN_RATIO_CALIBRATION_PASS`.
- Gate 13C: `CHEN_CALIBRATED_CONFIRMATION_PASS`.
- Gate 14A: `READY_FOR_GATE_14B_POZO_RATIO_HOLDOUT`.
- Locked burden: `proxy_burden_level = 0.5`.
- Không chọn lại parameter và không dùng Pozo để tune.

## Pozo holdout target

- Model: `Pink1B9`.
- Metric: `distance_traveled_mm`.
- Disease value: `62.091 mm`.
- Control value: `323.326 mm`.
- Target ratio: `0.19203837612811836`.
- Spread: `61.288`, giữ nguyên paper-reported, không đổi thành SD/SE.
- Sample size: `n=21`.
- Allocation: holdout only.
- Đây không phải speed target; không chuyển distance thành speed.

## Run design

- Condition duy nhất: `pink1`.
- Scope: `organism_level_proxy`.
- Control burden: `0.0`.
- Holdout burden: `0.5`.
- Seeds: `12, 13, 14, 15, 16, 17`.
- Planned runs: `12`.
- Runtime cố định: `5000` steps, timestep `0.0001 s`, duration `0.5 s`.

## Results

- Execution status: `POZO_HOLDOUT_RUNTIME_PASS`.
- Scientific status: `POZO_RATIO_HOLDOUT_CONCORDANCE_REPORTED`.
- Successful runs: `12`.
- Failed runs: `0`.
- Blocked runs: `0`.
- Mean distance control: `1.66678980695` mm.
- Mean distance holdout: `1.57846176434` mm.
- Simulated distance ratio: `0.94700708977`.
- Ratio error: `0.754968713642`.
- Directionality (`burden_0.5 < burden_0.0`): `True`.
- Absolute distance error: `60.51253823566` mm, reference-only (`62.091 - 1.57846176434`); không dùng để kết luận concordance vì khác biệt scale/thời lượng assay.

## Runtime và QC

- Successful runs: `12`; QC pass count được ghi trong summary CSV.
- Không có runtime blocker.

Mỗi run PASS phải có metrics finite, timestamp/quaternion/action/observation QC,
locomotion và contact hợp lệ, cùng operator checks theo burden. Artifact lớn
như NPZ, video và viewer bundle không được lưu trong Gate 14B repository output.

## Diễn giải giới hạn

`POZO_HOLDOUT_RUNTIME_PASS` chỉ cho biết 12 rollout computational đã chạy và
qua QC. Ratio được báo cáo theo protocol; không có numerical tolerance được
đăng ký trước nên không tự đặt ngưỡng hậu nghiệm. Scientific status không phải
là biological validation. Kết quả không chứng minh gene-specific PINK1 mapping,
cơ chế Parkinson, chẩn đoán lâm sàng, drug efficacy hoặc thay thế thí nghiệm
wet-lab. Absolute distance chỉ là reference-only vì scale/thời lượng assay và
runtime không được giả định tương đương trực tiếp.

## Cấm trong Gate 14B

- Không calibration.
- Không parameter search hoặc Pozo tuning.
- Không chạy alpha-synuclein, Parkin, DJ-1 hoặc LRRK2.
- Không đổi distance thành speed hoặc spread thành SD/SE.

## Final status

- Execution: `POZO_HOLDOUT_RUNTIME_PASS`.
- Scientific: `POZO_RATIO_HOLDOUT_CONCORDANCE_REPORTED`.
