# Gate 08 Authorized Reviewer Signoff

## Trạng thái

`WAITING_TARGET_DATA`

Tài liệu này là biểu mẫu signoff dành cho reviewer có thẩm quyền. Tại thời
điểm tạo Gate 08, chưa có tên reviewer, ngày review, vai trò hoặc quyết định
signoff thật được cung cấp. Vì vậy biểu mẫu này không phải là phê duyệt và
không được dùng để promote target.

## Reviewer identity

- Reviewer name: `NOT_PROVIDED`
- Review date: `NOT_PROVIDED`
- Reviewer role: `NOT_PROVIDED`

## Calibration signoff

- Selected target: Chen 2014 Old A30P adult horizontal walking speed (dự kiến)
- Decision: `pending`
- Assay transfer: `pending`
- Digitization second review: `pending`
- CI95 policy: `pending`

Chen candidate hiện có:

- Original value: `0.4875 cm/s`.
- Converted value: `4.875 mm/s` theo quy đổi vật lý `1 cm/s = 10 mm/s`.
- Original uncertainty: `0.0525 cm/s`, giữ loại `CI95`.
- Converted uncertainty: `0.525 mm/s`.
- Sample size: `20`, `sample_unit=fly`.
- Age/timepoint: `30`; sex: `male`.
- Provenance: `research/paper_review/digitized/chen_2014_adult_walking_speed.csv`.

Chỉ được approve khi reviewer thật xác nhận độc lập phép digitization, CI95
policy, assay transfer và allocation `calibration`. Không đổi CI95 thành SE.

## Pokrzywa fallback signoff

- Selected target: Pokrzywa 2017 alpha-synuclein day 21 speed (fallback)
- Decision: `pending`
- Assay transfer: `pending`
- Sample-size policy: `pending`

Pokrzywa chỉ được xem xét nếu có exact numeric independent-vial count và
uncertainty được reviewer xác nhận. Khoảng `3-10 independent vials` không được
đổi thành một sample size số học.

## Holdout signoff

- Selected target: Pozo 2022 Pink1B9 `distance_traveled_mm` (dự kiến)
- Decision: `pending`
- Assay transfer: `pending`
- Distance holdout policy: `pending`
- IQR/min-max policy: `pending`

Pozo candidate hiện có:

- Metric: `distance_traveled_mm`.
- Value: `62.091 mm`.
- Spread: `61.288`, giữ nguyên IQR/min/max theo paper.
- Sample size: `21`, `sample_unit=fly`.
- Age: `28`; genotype: `Pink1B9`.
- Provenance: `research/paper_review/pozo_distance_holdout_signoff.md` và
  Figure 3B.

Chỉ được approve khi reviewer/research lead thật xác nhận assay transfer cho
distance/path-length, policy IQR/min-max và allocation `holdout`. Không đổi
distance thành speed và không đổi spread thành SD/SE.

## Machine-readable signoff fields

Các giá trị dưới đây phản ánh thông tin hiện có, không phải placeholder được
chấp thuận:

```text
REVIEWER_NAME=NOT_PROVIDED
REVIEW_DATE=NOT_PROVIDED
REVIEWER_ROLE=NOT_PROVIDED

CHEN_SIGNOFF=pending
CHEN_ASSAY_TRANSFER=pending
CHEN_DIGITIZATION_SECOND_REVIEW=pending
CHEN_CI95_POLICY=pending

POKRZYWA_SIGNOFF=pending
POKRZYWA_ASSAY_TRANSFER=pending
POKRZYWA_SAMPLE_SIZE_POLICY=pending

POZO_SIGNOFF=pending
POZO_ASSAY_TRANSFER=pending
POZO_DISTANCE_HOLDOUT_POLICY=pending
POZO_IQR_MINMAX_POLICY=pending
```

## Reviewer statement

Chưa có reviewer được ủy quyền cung cấp statement. Reviewer chỉ được ký sau
khi kiểm tra PDF/figure/supplementary, provenance và tính tương thích assay.

## Scientific boundary

This signoff only authorizes computational calibration readiness. It is not
biological Parkinson validation, clinical diagnosis, drug efficacy validation,
or a replacement for wet-lab experiments.
