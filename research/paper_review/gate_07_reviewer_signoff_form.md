# Gate 07 - Reviewer Signoff Form

## Trạng thái biểu mẫu

Biểu mẫu này dùng để research lead hoặc reviewer được ủy quyền ghi nhận
signoff thật cho từng target. Tại thời điểm tạo biểu mẫu, chưa có human
signoff được cung cấp; biểu mẫu không phải là phê duyệt và không được dùng để
đưa target vào `targets.csv`.

## Reviewer

- Reviewer name: `CHƯA_CÓ_HUMAN_SIGNOFF`
- Review date: `CHƯA_CÓ_HUMAN_SIGNOFF`
- Role/authority: `CHƯA_CÓ_HUMAN_SIGNOFF`

## Calibration target signoff

- Selected target: `CHƯA_CÓ_QUYẾT_ĐỊNH`
- Metric: `CHƯA_CÓ_QUYẾT_ĐỊNH`
- Value: `CHƯA_CÓ_SIGNOFF`
- Uncertainty: `CHƯA_CÓ_SIGNOFF`
- Sample size: `CHƯA_CÓ_SIGNOFF`
- Sample unit: `CHƯA_CÓ_SIGNOFF`
- Assay transfer: `pending`
- Allocation: `calibration` chỉ sau khi target được ký duyệt
- Provenance: `CHƯA_CÓ_SIGNOFF`
- Decision: `pending`
- Reviewer statement: Chưa có phát biểu signoff của reviewer được ủy quyền.

Ứng viên cần được xem xét:

- Chen 2014: adult horizontal walking speed, Old A30P, giá trị digitize
  `0.4875 cm/s`, CI95 digitize `0.0525 cm/s`, `n=20`.
- Pokrzywa 2017: day 21 mean speed `2.5 mm/s`, SE hình xấp xỉ `0.12`,
  nhưng chưa có exact independent-vial count.

Không được đổi CI95 thành SE, không được dùng Pokrzywa khi chưa xác nhận n
độc lập theo vial, và không được điền tên reviewer hoặc ngày review giả.

## Holdout target signoff

- Selected target: `pozo_2022_pink1_serotonin` chỉ sau khi được ký duyệt
- Metric: `distance_traveled_mm`
- Value: `62.091 mm`
- Uncertainty: `61.288`, giữ nguyên spread IQR/min-max theo paper
- Sample size: `21`
- Sample unit: `fly`
- Assay transfer: `pending`
- Allocation: `holdout`
- Provenance: `research/paper_review/pozo_distance_holdout_signoff.md` và
  Figure 3B
- Decision: `pending`
- Reviewer statement: Chưa có phát biểu signoff của research lead.

Không đổi distance thành speed, không đổi IQR/min-max thành SD hoặc SE và
không dùng cùng cohort cho calibration và holdout.

## Assay transfer decisions

- `CHEN_ASSAY_TRANSFER`: `pending`
- `POKRZYWA_ASSAY_TRANSFER`: `pending`
- `POZO_ASSAY_TRANSFER`: `pending`

Mỗi quyết định phải do reviewer có thẩm quyền ghi rõ là `allowed` hoặc
`rejected`, kèm lý do và provenance. Giá trị `pending` hiện tại không mở
calibration gate.

## Scientific boundary

This signoff only authorizes computational calibration readiness. It is not
biological Parkinson validation, clinical diagnosis, drug efficacy validation,
or a replacement for wet-lab experiments.
