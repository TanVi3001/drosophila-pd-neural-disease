# Gate 14A - Pozo Holdout Protocol

## Mục tiêu

Gate 14A khóa protocol cho Pozo 2022 holdout trước khi có thể xem xét chạy
Gate 14B. Gate này chỉ tạo protocol và artifact provenance; không chạy
simulation, holdout validation hoặc calibration.

## Trạng thái đầu vào

- Gate 13B: `CHEN_RATIO_CALIBRATION_PASS`.
- Gate 13C: `CHEN_CALIBRATED_CONFIRMATION_PASS`.
- Burden đã khóa: `proxy_burden_level = 0.5`.
- Audit target: `READY_FOR_CALIBRATION`.
- PINK1 hiện là `organism_level_proxy`, không có gene-specific neuron mapping.

## Pozo target

- Model: `Pink1B9`.
- Metric: `distance_traveled_mm`.
- Giá trị bệnh: `62.091 mm`.
- Spread: `61.288`, giữ nguyên dạng paper-reported IQR/min-max; không đổi thành SD/SE.
- Sample size: `n=21 fly`.
- Allocation: holdout only.
- Đây không phải speed target và không được chuyển distance thành speed.

## Endpoint holdout

- Control distance: 323.326 mm.
- Disease/control ratio: 0.19203837612811836.
- Primary endpoint Gate 14B: `distance_ratio_to_control`.
- Provenance: dòng control cùng Pozo Figure 3B trong `full_target_survey_matrix.csv`.

Absolute distance của paper chỉ là reference-only vì thời lượng assay và scale
runtime không được giả định là tương đương trực tiếp. Pozo không được dùng để
tune hoặc chọn lại `proxy_burden_level`.

## Thiết kế Gate 14B dự kiến

- Condition: `pink1` organism-level proxy.
- Control burden: `0.0`.
- Holdout burden đã khóa: `0.5`.
- Seeds: `12, 13, 14, 15, 16, 17`.
- Planned runs: `12`.
- Không tuning, không calibration, không parameter search trên holdout.

## Kiểm tra blocker

- Không có blocker dữ liệu cho việc khóa protocol.

## Ranh giới khoa học

Đây là protocol cho computational locomotion holdout. Nó không phải biological
Parkinson validation, không phải gene-specific PINK1 validation, không phải
chẩn đoán lâm sàng, không phải drug efficacy validation và không thay thế thí
nghiệm wet-lab. Gate 14A không chạy simulation và không tạo disease metrics.

## Final status

`READY_FOR_GATE_14B_POZO_RATIO_HOLDOUT`
