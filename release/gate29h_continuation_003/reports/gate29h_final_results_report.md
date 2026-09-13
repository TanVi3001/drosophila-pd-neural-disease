# Gate29-H final results report

Freeze date: 2026-09-13

## Executive result

Trong protocol Gate29-H đã đăng ký trước, full-burden không tạo ra khác biệt quan sát được so với `healthy_control` ở endpoint chính hoặc endpoint trace đã định trước. Đây là kết luận trong phạm vi computational protocol này; không phải kết luận rằng dopamine depletion không có tác động sinh học trong ruồi giấm.

Decision lock: `NOT_REPRODUCED_WITHIN_COMPUTATIONAL_SCOPE`.

## Design and integrity

- 3 conditions x 5 seeds = 15/15 completed jobs; every QC job is PASS.
- Same-seed pairing across conditions; primary unit is one simulation seed.
- 5,000 steps per job, timestep 0.0001 s, CUDA execution, p9 stimulus.
- Full burden: burden 1.0, full presynaptic gain 0.15, target count 342.
- No automatic retry, calibration, fitting, retuning, post-hoc seed selection, or holdout opening.
- Healthy checkpoint SHA256: `d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691`.
- Full-burden checkpoint SHA256: `75492edf67a03f0afdb95e95ac9256f6d6db99d6496113696f417b5373151a3c`; this differs from the healthy checkpoint and is retained in the freeze manifest.

## Primary endpoint

Endpoint: `median_planar_speed_mm_s`; contrast: `full_burden - healthy_control`; hypothesis direction: less than zero.

- Paired differences by seed: `[0.0, 0.0, 0.0, 0.0, 0.0]`.
- Median paired difference: `0.000000 mm/s`.
- Exact one-sided sign-flip test: p = `1.00`, alpha = `0.05`; not significant.
- Percentile paired bootstrap (10,000 resamples, seed 29001): 95% CI = `[0.000000, 0.000000] mm/s`.
- Paired rank-biserial correlation: not defined because all paired differences are exactly zero.

| Seed | Healthy speed (mm/s) | Full-burden speed (mm/s) | Full - healthy (mm/s) |
|---:|---:|---:|---:|
| 0 | 2.223835 | 2.223835 | 0.000000 |
| 1 | 2.271621 | 2.271621 | 0.000000 |
| 2 | 2.638977 | 2.638977 | 0.000000 |
| 3 | 2.610920 | 2.610920 | 0.000000 |
| 4 | 2.585321 | 2.585321 | 0.000000 |

## Trace endpoint and identity control

The preregistered trace endpoint `brain_body_drive_mean_l2` also had zero full-minus-healthy difference for all five seeds. The zero-burden identity control passed: zero-burden and healthy outputs were exactly identical by seed across the checked metrics and trace arrays.

## Figure and artifact locations

- Figure: `figures/gate29h_primary_paired_speed.png`.
- Seed-level table: `tables/gate29h_primary_result.csv`.
- Full analysis table: `tables/gate29h_seed_level_metrics_and_differences.csv`.
- QC, analysis, execution summary, freeze manifest, and SHA256 list are in `manifests/` and `checksums.sha256`.

## Claim boundary

Allowed wording: “Under the preregistered Gate29-H class-level computational protocol, the full-burden condition did not differ from healthy control on the primary endpoint; all five paired differences were zero (exact one-sided sign-flip p = 1.00; 95% bootstrap CI [0, 0]).”

Not allowed: “dopamine depletion has no biological effect,” “Parkinson disease was validated,” gene-specific or clinical claims, or any wording implying that this null result licenses retuning or a new burden search.

## Review status

The packet is frozen and ready for two-person human review. The review manifest intentionally remains `WAITING_DUAL_HUMAN_ANALYSIS_REVIEW` until Lê Tấn Vĩ and Tô Đặng Minh Tuấn directly attest that they reviewed the analysis report, table, figure, and claim boundary.
