# Gate 13A - Chen-only Calibration Objective & Feasibility

## Mục tiêu

Gate 13A chuẩn bị objective cho calibration bằng Chen 2014 only. Gate này không tối ưu tham số, không chạy calibration và không chạy holdout validation.

## Trạng thái input

- Gate 12G integrated proxy rollouts: `INTEGRATED_PROXY_ROLLOUTS_PASS`.
- Healthy baseline manifest: `PASS`.
- Audit target: `READY_FOR_CALIBRATION` (đã kiểm tra trước khi tạo gate).
- Condition được dùng: `alpha_synuclein`, phạm vi `organism_level_proxy`.
- Chưa chạy calibration và chưa chạy holdout validation.

## Chen target

- Disease value: `4.875 mm/s`.
- Uncertainty: `0.525 CI95`.
- Sample size: `n=20 fly`.
- Metric: `mean_planar_speed_mm_s`.
- Allocation: `calibration`.
- Matched Old CT control: `7.275 mm/s` nếu có provenance.
- Disease/control ratio: `0.670103092784` nếu có thể tính từ cùng source.

Giá trị Chen gốc được ghi trong source là `0.4875 cm/s`, được đổi đơn vị vật lý thành `4.875 mm/s`. CI95 được giữ nguyên là CI95; không đổi thành SE.

## Quyết định objective

- Absolute speed target chỉ giữ vai trò `reference_only`, vì scale assay Chen và scale simulator chưa được chứng minh là đồng nhất trực tiếp.
- Ratio `mean_planar_speed_ratio_to_control` được ưu tiên cho Gate 13B khi matched control có provenance.
- Không dùng Pozo trong Gate 13A; Pozo chỉ là holdout của Gate 14.
- Không dùng PINK1 cho Chen calibration objective.

## Candidate burden table

Bảng dưới đây lấy từ summary Gate 12G của `alpha_synuclein`. Hạng chỉ để Gate 13B review, không phải kết quả tuning hay lựa chọn tham số cuối.

| Burden | Successful runs | Speed mean (mm/s) | Speed std | Ratio vs burden 0 | Ratio error vs Chen | Rank | Usable for Gate 13B |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 0 | 6 | 1.7779315915 | 0.210725340995 | 1 | 0.329896907216 | - | no |
| 0.25 | 6 | 1.46318546229 | 0.229246002192 | 0.822970618943 | 0.152867526159 | 2 | yes |
| 0.5 | 6 | 1.04119440742 | 0.2638135337 | 0.585621186102 | 0.0844819066814 | 1 | yes |
| 0.75 | 6 | 0.504226783259 | 0.339282999165 | 0.283603028188 | 0.386500064596 | 3 | yes |
| 1 | 6 | 3.75631720919 | 1.23185009645 | 2.11274563495 | 1.44264254217 | 4 | yes |

## Final status

`READY_FOR_GATE_13B_CHEN_RATIO_CALIBRATION`

Gate 13A chỉ xác nhận rằng objective có thể được chuẩn bị từ target Chen và summary proxy hiện có. Gate 13B mới là nơi nhóm nghiên cứu quyết định cách chạy calibration; Gate 13A không chọn parameter bằng tối ưu hóa.

## Boundary

Đây là computational locomotion experiment ở phạm vi organism-level proxy. Không phải biological Parkinson validation, không phải gene-specific mapping, không phải chẩn đoán lâm sàng và không phải đánh giá thuốc.

Các artifact lớn như video, NPZ và checkpoint không được sao chép vào package Gate 13A; chỉ lưu bảng summary và provenance cần thiết.
