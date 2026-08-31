# Gate 09 Real Reviewer Signoff

## Trạng thái

`WAITING_TARGET_DATA`

Biểu mẫu này chỉ có hiệu lực khi được điền bởi reviewer thật có thẩm quyền.
Tại Gate 09, thông tin signoff thực tế chưa được cung cấp, nên không target
nào được approve hoặc đưa vào `calibration_targets/targets.csv`.

## Reviewer identity

- Reviewer name: `NOT_PROVIDED`
- Review date: `NOT_PROVIDED`
- Reviewer role: `NOT_PROVIDED`

## Calibration target approval

- Selected target: Chen 2014 adult horizontal walking speed
- Decision: `pending`
- Assay transfer: `pending`
- Digitization second review: `pending`
- CI95 policy: `pending`
- Allocation: `calibration` chỉ sau khi signoff hợp lệ
- Provenance: `research/paper_review/digitized/chen_2014_adult_walking_speed.csv`

Dữ liệu ứng viên Chen đang có:

- Old A30P: `0.4875 cm/s`, CI95 digitize `0.0525 cm/s`.
- Sau quy đổi vật lý: `4.875 mm/s`, CI95 `0.525 mm/s`.
- `sample_size=20`, `sample_unit=fly`, age/timepoint `30`, sex `male`.

Không đổi CI95 thành SE. Chỉ approve khi reviewer thật xác nhận second review
của digitization, policy CI95, assay transfer và allocation.

## Pokrzywa fallback

- Selected target: Pokrzywa 2017 alpha-synuclein day 21 speed
- Decision: `pending`
- Assay transfer: `pending`
- Sample-size policy: `pending`

Pokrzywa chưa được chọn vì paper chỉ ghi `3-10 independent vials`, chưa có
exact numeric unit-of-analysis count. Không dùng khoảng này làm `sample_size`.

## Holdout target approval

- Selected target: Pozo 2022 Pink1B9 `distance_traveled_mm`
- Decision: `pending`
- Assay transfer: `pending`
- Distance holdout policy: `pending`
- IQR/min-max policy: `pending`
- Allocation: `holdout` chỉ sau khi signoff hợp lệ
- Provenance: `research/paper_review/pozo_distance_holdout_signoff.md`

Dữ liệu ứng viên Pozo đang có:

- `metric=distance_traveled_mm`.
- `value=62.091 mm`.
- `variance=61.288`, giữ nguyên IQR/min-max theo paper.
- `sample_size=21`, `sample_unit=fly`, age `28`, genotype `Pink1B9`.

Không đổi distance thành speed và không đổi IQR/min-max thành SD hoặc SE.

## Machine-readable signoff fields

```text
REVIEWER_NAME=NOT_PROVIDED
REVIEW_DATE=NOT_PROVIDED
REVIEWER_ROLE=NOT_PROVIDED

CALIBRATION_TARGET=chen_2014_adult_walking
CHEN_SIGNOFF=pending
CHEN_ASSAY_TRANSFER=pending
CHEN_DIGITIZATION_SECOND_REVIEW=pending
CHEN_CI95_POLICY=pending

HOLDOUT_TARGET=pozo_2022_pink1_serotonin
POZO_SIGNOFF=pending
POZO_ASSAY_TRANSFER=pending
POZO_DISTANCE_HOLDOUT_POLICY=pending
POZO_IQR_MINMAX_POLICY=pending
```

## Reviewer statement

Chưa có reviewer được ủy quyền cung cấp statement. Không dùng tên người thực
hiện task để thay thế human signoff.

## Scientific boundary

Reviewer chỉ authorizes các target cho computational calibration readiness. Đây
không phải biological Parkinson validation, clinical diagnosis, drug efficacy
validation hoặc thay thế thí nghiệm wet-lab.
