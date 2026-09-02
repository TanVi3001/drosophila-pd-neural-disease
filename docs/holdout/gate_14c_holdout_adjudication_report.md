# Gate 14C - Holdout Interpretation Adjudication

## Mục tiêu

Gate 14C khóa diễn giải khoa học sau Pozo holdout. Gate này chỉ đọc các
artifact đã có và không chạy simulation mới, calibration, tuning hoặc chọn lại
parameter.

## Input

- Gate 13B: `CHEN_RATIO_CALIBRATION_PASS`.
- Gate 13C: `CHEN_CALIBRATED_CONFIRMATION_PASS`.
- Gate 14A: Pozo holdout protocol locked.
- Gate 14B: Pozo holdout runtime PASS.

## Locked parameter

- `proxy_burden_level = 0.5`.
- Không chọn lại parameter.
- Không tune trên Pozo.

## Pozo result

- Condition: `pink1`, organism-level proxy.
- Planned runs: `12`.
- Successful runs: `12`.
- Control distance: `1.66679 mm`.
- Holdout distance: `1.57846 mm`.
- Simulated distance ratio: `0.9470`.
- Pozo target ratio: `0.1920383761281184`.
- Directionality: `PASS` (`burden 0.5` làm distance giảm so với `burden 0.0`).
- Quantitative ratio match: `NOT SUPPORTED`.
- Ratio error: `0.754968713642`.

Ratio mô phỏng `0.9470` khác xa ratio Pozo
`0.1920`. Vì vậy không được gọi kết quả này là
quantitative holdout validation. Sai số khoảng cách tuyệt đối chỉ là
`reference-only`, không dùng để kết luận do scale/thời lượng assay và runtime
không được giả định tương đương trực tiếp.

## Adjudication

- Runtime pipeline: `PASS`.
- Directional concordance: `REPORTED`.
- Quantitative ratio mismatch: `LARGE`.
- Evidence chỉ hỗ trợ directional phenotype concordance trong một
  computational locomotion proxy ở mức organism-level.

Không được kết luận:

- biological Parkinson validation;
- gene-specific PINK1 validation;
- quantitative Pozo validation;
- clinical validation;
- drug efficacy hoặc therapeutic validation.

## Evidence boundary

Gate 13C confirmation ratio được ghi nhận là `0.6142`; đây là
confirmation computational của burden đã khóa, không phải biological evidence.
Gate 14C không sửa raw result Gate 14B và không thêm ngưỡng ratio hậu nghiệm.

## Final claim

Chen-calibrated organism-level computational locomotion proxy with directional
Pozo holdout concordance, but substantial quantitative ratio mismatch.

## Final status

`HOLDOUT_ADJUDICATION_COMPLETE`

`DIRECTIONAL_CONCORDANCE_WITH_QUANTITATIVE_MISMATCH`
