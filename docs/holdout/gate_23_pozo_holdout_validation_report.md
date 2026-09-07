# Gate 23: Pozo holdout validation

**Trạng thái runtime:** `PASS`  
**Diễn giải holdout:** `MISMATCH`

Gate 23 xác minh lại holdout Pozo trên artifact Gate 14B đã được khóa. Gate này không chạy GPU, không chạy simulation mới, không calibration, không tuning và không sửa raw metrics.

## Thiết kế khóa

- Condition: `pink1`, phạm vi `organism_level_proxy`.
- Tham số calibration từ Chen đã khóa: `proxy_burden_level = 0.5`.
- Endpoint duy nhất: `distance_traveled_mm`.
- Không chuyển distance thành speed.
- Pozo chỉ là holdout, không dùng để chọn lại tham số.
- Đơn vị tính toán: rollout seed; runtime Gate 14B có 12/12 run thành công.

## Kết quả

- Khoảng cách control trung bình: `1.66678981 mm`.
- Khoảng cách holdout trung bình: `1.57846176 mm`.
- Tỷ lệ mô phỏng: `0.947007089770`.
- Tỷ lệ Pozo: `0.192038376128`.
- Sai số tỷ lệ: `0.754968713642`.
- Directionality: `PASS`.
- Quantitative interpretation: `MISMATCH`.

Kết quả đúng là **directionality concordance nhưng quantitative mismatch**. Khoảng cách giảm khi burden 0.5 được áp dụng, nhưng tỷ lệ `0.9470` khác xa tỷ lệ Pozo `0.1920`; không được gọi là quantitative holdout validation.

## Giới hạn claim

Kết quả chỉ hỗ trợ so sánh computational locomotion proxy ở mức organism-level. Không phải biological Parkinson validation, không phải gene-specific PINK1 validation, không phải clinical validation và không phải drug validation.

## Provenance

- `gate14a_protocol`: `experiments/gate_14a_pozo_holdout_protocol/configs/pozo_holdout_protocol.yaml`
- `gate13b_calibrated_config`: `experiments/gate_13b_chen_ratio_calibration/configs/calibrated_alpha_synuclein_proxy.yaml`
- `gate13c_confirmation_manifest`: `experiments/gate_13c_calibrated_confirmation/manifests/calibrated_confirmation_manifest.json`
- `gate14b_manifest`: `experiments/gate_14b_pozo_holdout_validation/manifests/pozo_holdout_manifest.json`
- `gate14b_summary`: `experiments/gate_14b_pozo_holdout_validation/results/pozo_holdout_result_summary.json`
- `gate14b_metrics`: `experiments/gate_14b_pozo_holdout_validation/results/pozo_holdout_metrics.csv`
- `gate14c_adjudication`: `experiments/gate_14c_holdout_adjudication/results/holdout_adjudication_summary.json`
