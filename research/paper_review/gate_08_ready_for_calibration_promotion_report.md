# Gate 08 - Authorized Promotion to READY_FOR_CALIBRATION

## Baseline

- Main commit: `66461c7` (`Merge target digitization and signoff gate`).
- Gate 05 context: `2f32519`.
- Gate 06 context: `8561d30` trên branch
  `review/gate-06-target-promotion-ready`.
- Gate 07 context: `1cdce85` trên branch
  `review/gate-07-reviewer-signoff-ready`.
- Audit trước Gate 08: `WAITING_TARGET_DATA`.
- Không chạy disease simulation, calibration hoặc holdout validation.

## Reviewer authorization

Chưa có human authorization hợp lệ được cung cấp cho Gate 08. Các dòng signoff
trước đó còn trống hoặc ở trạng thái pending, nên không thể dùng làm căn cứ
promote:

- Reviewer name: `NOT_PROVIDED`.
- Review date: `NOT_PROVIDED`.
- Reviewer role: `NOT_PROVIDED`.
- Chen signoff: `pending`.
- Chen assay transfer: `pending`.
- Chen digitization second review: `pending`.
- Chen CI95 policy: `pending`.
- Pozo signoff: `pending`.
- Pozo assay transfer: `pending`.
- Pozo distance holdout policy: `pending`.
- Pozo IQR/min-max policy: `pending`.

Form chính thức được tạo tại
`research/paper_review/gate_08_authorized_reviewer_signoff.md`.

## Calibration target approved

### Chen 2014 Old A30P

- Trạng thái: `PENDING_HUMAN_SIGNOFF`, chưa approved.
- Candidate: adult horizontal walking speed.
- Giá trị: `0.4875 cm/s` được digitize, tương đương `4.875 mm/s` sau quy đổi
  vật lý.
- Uncertainty: `CI95`, `0.0525 cm/s` tương đương `0.525 mm/s`.
- Sample size: `20`, `sample_unit=fly`.
- Unit conversion: `1 cm/s = 10 mm/s`.
- Assay transfer: chưa được xác nhận `allowed`.
- Provenance: `research/paper_review/digitized/chen_2014_adult_walking_speed.csv`.
- Thiếu: reviewer/date, second review, CI95 policy và assay transfer.

Chen là calibration candidate ưu tiên, nhưng chưa được đưa vào
`calibration_targets/targets.csv`.

### Pokrzywa fallback

Pokrzywa vẫn `pending` và không được chọn làm calibration target vì paper chỉ
ghi khoảng `3-10 independent vials`; exact unit-of-analysis count chưa có.
SE hình xấp xỉ cũng chưa được human signoff.

## Holdout target approved

### Pozo 2022 Pink1B9

- Trạng thái: `PENDING_HUMAN_SIGNOFF`, chưa approved.
- Metric: `distance_traveled_mm`.
- Value: `62.091 mm`.
- Uncertainty/spread: `61.288`, giữ nguyên IQR/min-max theo paper.
- Sample size: `21`, `sample_unit=fly`.
- Assay transfer: chưa được xác nhận `allowed`.
- Allocation dự kiến: `holdout`.
- Provenance: `research/paper_review/pozo_distance_holdout_signoff.md`, Figure 3B.
- Thiếu: reviewer/date, explicit holdout signoff và distance assay-transfer
  policy.

Pozo không được dùng để calibration speed và không được đổi spread thành
SD/SE.

## `targets.csv` changes

Không cập nhật `calibration_targets/targets.csv` trong Gate 08.

- Chen chưa đủ signoff để thêm row approved calibration.
- Pozo chưa đủ signoff để thêm row approved holdout.
- Các row pending hiện tại được giữ nguyên.
- Không thay đổi policy, audit script hoặc test để bypass gate.
- `target_promotion_candidates.csv` chưa được chuyển candidate nào sang
  `ready_to_promote=true`.

## Audit result

- Command: `py -3.12 scripts/audit_calibration_targets.py`.
- Status: `WAITING_TARGET_DATA`.
- Approved target count: `0`.
- Calibration target count: `0`.
- Holdout target count: `0`.

Acceptance result: **B - WAITING đúng khoa học**. Không đạt mục tiêu A vì
thiếu human signoff thật và assay-transfer authorization.

## Validation

- `py -3.12 -m compileall -q src scripts tests`: PASS.
- `py -3.12 -m pytest -q -rs -p no:cacheprovider`: PASS, `58 passed`.
- `git diff --check`: PASS.
- CSV parse: PASS; `targets.csv` có 2 row và
  `target_promotion_candidates.csv` có 3 row, không lệch cột.
- Không chạy disease simulation, calibration hoặc holdout validation.

## Dữ liệu cần research lead cung cấp

1. Tên reviewer thật và vai trò/ủy quyền.
2. Ngày review thật theo `YYYY-MM-DD`.
3. Chen: xác nhận second review của digitization, CI95 policy và assay
   transfer.
4. Pozo: xác nhận distance/path-length assay transfer, IQR/min-max policy và
   holdout độc lập.
5. Quyết định allocation duy nhất cho mỗi target.
6. Chỉ sau khi đủ các trường trên mới điền form, cập nhật target rows và chạy
   lại audit.

## Ranh giới khoa học

`READY_FOR_CALIBRATION`, nếu đạt ở gate sau, chỉ có nghĩa là đủ target y văn
được duyệt cho computational calibration. Nó không phải biological Parkinson
validation, không phải chẩn đoán lâm sàng, không phải xác nhận hiệu lực thuốc
và không thay thế thí nghiệm wet-lab.
