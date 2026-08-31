# Gate 07 - Reviewer Signoff and READY_FOR_CALIBRATION

## Baseline

- Main commit: `66461c7` (`Merge target digitization and signoff gate`).
- Gate 06 commit: `8561d30` trên branch
  `review/gate-06-target-promotion-ready`.
- Audit trước Gate 07: `WAITING_TARGET_DATA`.
- Gate 06 kết luận: chưa có human signoff nên không promote target.
- Không chạy simulation, calibration hoặc holdout validation.

## Reviewer signoff

Hiện chưa có thông tin signoff thật trong repository hoặc task:

- Reviewer name: chưa được cung cấp.
- Review date: chưa được cung cấp.
- Role/authority: chưa được cung cấp.
- Chen: chưa ký.
- Pokrzywa: chưa ký.
- Pozo: chưa ký assay transfer và holdout.

File signoff form được tạo tại
`research/paper_review/gate_07_reviewer_signoff_form.md`, nhưng vẫn ở trạng
thái `pending`. Không dùng tên người thực hiện task làm reviewer nếu chưa có
ủy quyền rõ ràng.

## Calibration target

### Chen 2014

- Quyết định: `pending`.
- Candidate: Old A30P adult horizontal walking speed.
- Giá trị digitize: `0.4875 cm/s`, tương đương `4.875 mm/s` nếu được duyệt
  chuyển đơn vị vật lý.
- Uncertainty: CI95 digitize `0.0525 cm/s`, tương đương `0.525 mm/s`.
- Sample size: `20 fly`.
- Assay transfer: chưa được ký `allowed`.
- Provenance: `research/paper_review/digitized/chen_2014_adult_walking_speed.csv`.
- Thiếu: reviewer thật, ngày review thật, second review độc lập, assay
  transfer signoff và chính sách sử dụng CI95.

Chen vẫn là calibration candidate ưu tiên nếu các trường trên được xác nhận.
Không đổi CI95 thành SE khi chưa có policy và signoff phù hợp.

### Pokrzywa 2017

- Quyết định: `pending`.
- Giá trị day 21: mean `2.5 mm/s`.
- Uncertainty: SE hình xấp xỉ `0.12 mm/s`.
- Sample size: paper ghi `3-10 independent vials`, chưa có exact count.
- Assay transfer: chưa được ký `allowed`.
- Provenance: `research/paper_review/digitized/pokrzywa_fig2A_day21_speed.csv`.
- Thiếu: exact independent-vial count, xác nhận SE và reviewer/date.

Không promote Pokrzywa chỉ dựa trên khoảng `3-10` vial.

## Holdout target

### Pozo 2022 - Pink1B9 distance

- Quyết định: `pending`.
- Metric: `distance_traveled_mm`.
- Giá trị: `62.091 mm`.
- Uncertainty/spread: `61.288`, giữ nguyên IQR/min-max theo paper.
- Sample size: `21 fly`.
- Assay transfer: chưa được ký `allowed`.
- Allocation dự kiến: `holdout`.
- Provenance: `research/paper_review/pozo_distance_holdout_signoff.md`, Figure 3B.
- Thiếu: reviewer thật, ngày review thật, explicit holdout signoff và
  quyết định assay transfer.

Pozo chỉ có thể là holdout distance endpoint. Không dùng làm calibration
speed target và không biến spread thành SD/SE.

## `targets.csv` update

Không cập nhật `calibration_targets/targets.csv` trong Gate 07.

Lý do:

- Chưa có reviewer và ngày review thật.
- Chưa có assay transfer `allowed` cho target nào.
- Chưa có một target calibration và một target holdout cùng đạt đủ điều kiện.
- Các row hiện tại trong `targets.csv` vẫn phải giữ `review_status=pending`.

`target_promotion_candidates.csv` tiếp tục ghi các candidate với
`ready_to_promote=false` và các trường thiếu tương ứng.

## Audit result

- Command: `py -3.12 scripts/audit_calibration_targets.py`.
- Status: `WAITING_TARGET_DATA`.
- Approved target count: `0`.
- Calibration target count: `0`.
- Holdout target count: `0`.
- Kết luận: không đạt `READY_FOR_CALIBRATION`.

Đây là trạng thái đúng về mặt khoa học, không phải lỗi cần sửa bằng cách đổi
audit script hoặc chỉnh dữ liệu.

## Validation

- `py -3.12 -m compileall -q src scripts tests`: PASS.
- `py -3.12 -m pytest -q -rs -p no:cacheprovider`: PASS, `58 passed`.
- `git diff --check`: PASS.
- CSV targets và candidate promotion: parse được, không thêm row approved.
- Signoff form: không chứa signoff giả và không được dùng để approve.

## Việc research lead cần hoàn tất

1. Điền tên reviewer thật, ngày review thật và role/authority.
2. Xem lại Chen từ PDF/figure, xác nhận digitization độc lập và CI95 policy.
3. Xác nhận Pokrzywa có exact independent-vial count; nếu không có thì giữ
   pending.
4. Xác nhận Pozo là distance holdout, assay transfer và cohort độc lập.
5. Điền allocation duy nhất cho mỗi target: `calibration` hoặc `holdout`.
6. Chỉ khi đủ metadata và provenance mới cập nhật `targets.csv` rồi chạy lại
   audit.

## Ranh giới khoa học

`READY_FOR_CALIBRATION`, nếu đạt ở gate sau, chỉ có nghĩa là đủ target y văn
cho computational calibration. Nó không phải biological Parkinson validation,
không phải chẩn đoán lâm sàng, không phải xác nhận hiệu lực thuốc và không
thay thế thí nghiệm wet-lab.
