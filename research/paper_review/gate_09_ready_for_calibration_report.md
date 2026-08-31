# Gate 09 - Apply Real Signoff and READY_FOR_CALIBRATION

## Baseline

- Main commit: `66461c7` (`Merge target digitization and signoff gate`).
- Gate 08 context: `30b5ca9` trên branch
  `review/gate-08-authorized-ready-promotion`.
- Audit trước Gate 09: `WAITING_TARGET_DATA`.
- Không chạy disease simulation, calibration hoặc holdout validation.

## Reviewer signoff

Gate 09 yêu cầu signoff thật cho Chen và Pozo, nhưng hiện chưa có thông tin
được cung cấp:

- Reviewer name: chưa có.
- Review date: chưa có.
- Reviewer role: chưa có.
- Chen signoff: `pending`.
- Pozo signoff: `pending`.
- Chen assay transfer: `pending`.
- Pozo assay transfer: `pending`.

Biểu mẫu chính thức nằm tại
`research/paper_review/gate_09_real_reviewer_signoff.md` và đang ở trạng thái
chờ điền. Không thể coi `approved/rejected/pending` trong task description là
quyết định của reviewer.

## Calibration target - Chen 2014

- Trạng thái: `pending`, chưa approved.
- Endpoint: adult horizontal walking speed.
- Old A30P: `0.4875 cm/s` tương đương `4.875 mm/s` khi dùng quy đổi vật lý.
- CI95: `0.0525 cm/s` tương đương `0.525 mm/s`, giữ nguyên loại `CI95`.
- Sample size: `20`, unit `fly`.
- Assay transfer: chưa được reviewer xác nhận `allowed`.
- Provenance: file digitization Chen.
- Còn thiếu: reviewer, review date, second review digitization, CI95 policy và
  assay-transfer authorization.

Chen vẫn là calibration candidate ưu tiên, nhưng chưa đủ điều kiện để thêm
vào `targets.csv`.

## Holdout target - Pozo 2022

- Trạng thái: `pending`, chưa approved.
- Endpoint: `distance_traveled_mm`.
- Value: `62.091 mm`.
- Spread: `61.288`, giữ nguyên IQR/min-max paper-reported.
- Sample size: `21`, unit `fly`.
- Assay transfer: chưa được reviewer xác nhận `allowed`.
- Allocation dự kiến: `holdout`.
- Provenance: `pozo_distance_holdout_signoff.md`, Figure 3B.
- Còn thiếu: reviewer, review date, distance holdout policy, IQR/min-max policy
  và explicit holdout signoff.

Pozo không được dùng làm calibration speed target.

## Pokrzywa và các target khác

- Pokrzywa giữ pending vì thiếu exact independent-vial count và SE signoff.
- Riemensperger giữ pending vì median speed chưa có numeric spread phù hợp.
- Hwang và Godena giữ validation-only.
- Dumitrescu giữ not-comparable cho speed.

## `targets.csv` update

Không cập nhật `calibration_targets/targets.csv`.

- Không thêm Chen approved calibration row.
- Không thêm Pozo approved holdout row.
- Không thay đổi row pending hiện tại.
- Không sửa audit script hoặc test để bypass yêu cầu signoff.

## Audit result

- Command: `py -3.12 scripts/audit_calibration_targets.py`.
- Status: `WAITING_TARGET_DATA`.
- Approved target count: `0`.
- Calibration target count: `0`.
- Holdout target count: `0`.

Không đạt `READY_FOR_CALIBRATION` vì thiếu human signoff thật, assay transfer
authorization và các policy xác nhận liên quan.

## Validation

- `py -3.12 -m compileall -q src scripts tests`: PASS.
- `py -3.12 -m pytest -q -rs -p no:cacheprovider`: PASS, `58 passed`.
- `git diff --check`: PASS.
- CSV parse: PASS; `targets.csv` và `target_promotion_candidates.csv` không
  lệch cột.
- Không chạy disease simulation, calibration hoặc holdout validation.

## Dữ liệu cần cung cấp

1. Tên reviewer thật.
2. Ngày review thật theo `YYYY-MM-DD`.
3. Vai trò và quyền hạn reviewer.
4. Chen: `approved`, `allowed`, second review và CI95 policy.
5. Pozo: `approved`, `allowed`, distance holdout policy và IQR/min-max policy.
6. Provenance và allocation cho từng target.

Chỉ sau khi có các thông tin này mới được cập nhật target rows và chạy lại
audit. Không thể đạt READY hợp lệ bằng cách tự điền các giá trị còn thiếu.

## Scientific boundary

`READY_FOR_CALIBRATION`, nếu đạt ở gate sau, chỉ nghĩa là đã có target y văn
được ký duyệt cho computational calibration. Nó không phải biological
Parkinson validation, không phải clinical diagnosis, không phải drug efficacy
validation và không thay thế wet-lab experiments.
