# Gate 09B - Apply Real Signoff and READY_FOR_CALIBRATION

## Reviewer authorization

- Reviewer: `Lê Tấn Vĩ`.
- Review date: `2026-09-02`.
- Role: `project scientific reviewer`.
- Signoff artifact: `research/paper_review/gate_09_real_reviewer_signoff.md`.
- Chen second review: approved.
- Chen CI95 policy: approved.
- Chen assay transfer: allowed.
- Pozo distance holdout policy: approved.
- Pozo IQR/min-max policy: approved.
- Pozo assay transfer: allowed.

Các thông tin trên được áp dụng từ completed reviewer signoff do người dùng
cung cấp. Không tạo thêm reviewer hoặc ngày review.

## Calibration target được duyệt

Chen 2014 Old A30P được đưa vào calibration:

- Paper ID: `chen_2014_adult_walking`.
- Gene model: `human_alpha_synuclein`; genotype: `A30P`.
- Age/timepoint: `30`; sex: `male`.
- Assay: adult horizontal walking.
- Metric: `mean_planar_speed_mm_s`.
- Giá trị nguồn: `0.4875 cm/s`.
- Quy đổi vật lý: `1 cm/s = 10 mm/s`.
- Giá trị sau quy đổi: `4.875 mm/s`.
- Uncertainty: `CI95`, từ `0.0525 cm/s` thành `0.525 mm/s`.
- Sample size: `20`; sample unit: `fly`.
- Allocation: `calibration`.
- Assay transfer: `allowed`.
- Provenance: `research/paper_review/digitized/chen_2014_adult_walking_speed.csv`.

CI95 được giữ nguyên là CI95, không relabel thành SE.

## Holdout target được duyệt

Pozo 2022 Pink1B9 được đưa vào holdout:

- Paper ID: `pozo_2022_pink1_serotonin`.
- Gene model: `pink1`; genotype: `Pink1B9`.
- Age: `28`; sex: `not_reported`.
- Assay: Open-field locomotor tracking.
- Metric: `distance_traveled_mm`.
- Giá trị: `62.091 mm`.
- Spread: `61.288`, giữ nguyên paper-reported IQR/min-max.
- Sample size: `21`; sample unit: `fly`.
- Allocation: `holdout`.
- Assay transfer: `allowed`.
- Provenance: `research/paper_review/pozo_distance_holdout_signoff.md`, Figure 3B.

Pozo chỉ là distance/path-length holdout. Không đổi distance thành speed,
không đổi IQR/min-max thành SD hoặc SE và không dùng target này trong
calibration.

## Target không được promote

- Pokrzywa: `pending`, vì exact independent-vial sample size còn thiếu.
- Riemensperger: `pending`, vì median speed chưa có numeric IQR/range phù hợp.
- Hwang và Godena: validation-only.
- Dumitrescu: not-comparable cho speed.

## Thay đổi dữ liệu

- `calibration_targets/targets.csv`: thêm đúng 2 approved rows, Chen cho
  calibration và Pozo cho holdout; giữ nguyên 2 pending rows hiện có.
- `research/paper_review/target_promotion_candidates.csv`: Chen và Pozo được
  đánh dấu `approved`/`ready_to_promote=true`; Pokrzywa vẫn false/pending.
- `docs/target_approval_policy.md`: bổ sung quy tắc CI95 và
  `paper_reported_center` chỉ cho distance holdout.
- `scripts/audit_calibration_targets.py`: nhận diện CI95 và kiểm tra
  `paper_reported_center` chỉ được dùng cho holdout distance.
- `tests/test_target_audit.py`: cập nhật regression cho trạng thái Gate 09B và
  thêm kiểm tra policy mới.

## Audit result

- Status: `READY_FOR_CALIBRATION`.
- Approved target count: `2`.
- Calibration target count: `1`.
- Holdout target count: `1`.
- Pokrzywa không được tính vào readiness.
- Audit chỉ là readiness gate cho computational calibration; chưa chạy
  calibration hoặc simulation.

## Validation

- `py -3.12 -m compileall -q src scripts tests`: PASS.
- `py -3.12 -m pytest -q -rs -p no:cacheprovider`: PASS, `60 passed`.
- `git diff --check`: PASS.
- CSV parse: PASS; `targets.csv` có 4 row và promotion candidates có 3 row.
- Disease simulation, calibration và holdout validation: không chạy trong Gate
  09B.

## Bước tiếp theo sau readiness

1. Đóng băng target manifest, config, version và checksum.
2. Kiểm tra metric `mean_planar_speed_mm_s` thật sự có trong artifact simulation.
3. Chạy computational calibration bằng Chen.
4. Giữ Pozo độc lập và chỉ dùng sau calibration cho holdout distance.
5. Chạy disease conditions nhiều seed và so sánh với Healthy baseline.

## Ranh giới khoa học

`READY_FOR_CALIBRATION` chỉ có nghĩa là đã có target y văn được reviewer ký
duyệt cho computational calibration. Nó không phải biological Parkinson
validation, không phải chẩn đoán lâm sàng, không phải xác nhận hiệu lực thuốc
và không thay thế thí nghiệm wet-lab.
