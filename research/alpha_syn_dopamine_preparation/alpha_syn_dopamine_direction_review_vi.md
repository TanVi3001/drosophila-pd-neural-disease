# Đánh giá định hướng Parkinson in silico và quyết định triển khai

## Phân biệt tài liệu định hướng với lệnh thực thi

File tổng hợp trong `Downloads` là tài liệu chiến lược. Nó xếp hạng hướng nghiên cứu, nêu điều kiện bằng chứng và thứ tự các gate; nó không phải execution authorization, không thay thế preregistration, không cấp quyền chạy GPU và không cho phép tự fit hoặc retune.

Yêu cầu hiện tại của nhóm là dùng tài liệu đó để chọn bước tiếp theo cho project. Vì vậy, bước được triển khai ở đây chỉ là chuẩn bị Gate A/B: chuẩn hóa endpoint registry, giữ nguyên các trường chưa đủ bằng chứng ở trạng thái pending, và dựng study-level split để review trước khi fit.

## Quyết định chiến lược được áp dụng

- Paper đầu tiên: `alpha-synuclein -> dopamine circuit -> locomotion`.
- PINK1–serotonin: để ở flagship tiếp theo, sau khi paper alpha-synuclein ổn định.
- Parkin/JNK, DJ-1/stress và LRRK2 axonal transport: module/dự án sau, không trộn vào paper đầu tiên.
- Generic multi-gene scalar burden: không dùng làm kiến trúc mục tiêu.
- Claim cao nhất hiện tại: uncertainty-aware, connectome-constrained computational phenotype comparison; không gọi là biological Parkinson model hay thay thế wet-lab.

## Quan hệ với Gate29-H

Gate29-H đã hoàn thành 15/15, QC PASS và cho kết quả null trong class-level computational protocol. Kết quả này được giữ nguyên trong release packet. Nó không được chuyển thành alpha-synuclein evidence, không được dùng để retune burden, và không mở lại holdout.

## Gate A/B đang triển khai

1. Tách `walking_speed` của paper khỏi `mean_planar_speed_mm_s` và `median_planar_speed_mm_s` của simulator.
2. Giữ riêng distance, climbing, DAM activity và activity time; không suy ra speed khi chưa có assay-transfer rule.
3. Ghi duration, frame rate, assay window, statistic, spread, sample unit và provenance cho từng endpoint.
4. Khóa allocation theo study trước fitting; một study chỉ có một role.
5. Chuẩn bị baselines, leave-one-study-out, uncertainty, ablation, sensitivity và identifiability criteria.

## Trạng thái

`alpha_syn_dopamine_study_split_manifest_v1.json` đang ở trạng thái `PREPARED_PENDING_DUAL_HUMAN_REVIEW`. Chưa có fitting, chưa có GPU execution authorization và chưa có model change nào được coi là scientific result.
