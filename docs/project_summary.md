# Project Summary

## Mục tiêu

Xây dựng một computational locomotion proxy ở mức organism-level cho các kiểu
hình vận động Parkinson-like trên Drosophila bằng pipeline FlyGym/MuJoCo.
Đây là mô hình tính toán để đánh giá vận động, không phải mô hình Parkinson
sinh học hoàn chỉnh.

## Pipeline

1. Literature target audit.
2. Healthy baseline.
3. Disease proxy configuration.
4. Integrated proxy rollout.
5. Chen-only ratio calibration.
6. Calibrated confirmation rerun.
7. Pozo holdout evaluation.
8. Holdout adjudication và claim lock.

## Kết quả chính

- Chen calibration chọn `proxy_burden_level = 0.5` trên discrete grid.
- Gate 13C confirmation ratio là `0.6142`.
- Pozo holdout runtime đạt `12/12` rollout PASS.
- Pozo directionality PASS: distance giảm ở burden `0.5` so với burden `0.0`.
- Pozo quantitative ratio mismatch: simulated `0.9470` so với target `0.1920`.

## Kết luận hiện tại

Dự án đạt mức computational organism-level proxy với directional phenotype
concordance. Kết quả chưa đạt biological validation hoặc gene-specific
validation. Pozo được giữ độc lập làm holdout và không được dùng để chọn lại
hoặc tune parameter.

## Ranh giới diễn giải

Kết quả hiện tại không phải clinical validation, drug validation, therapeutic
validation hay bằng chứng xác nhận cơ chế Parkinson. Mọi diễn giải phải tuân
theo [current claim lock](claims/current_claim_lock.md).
