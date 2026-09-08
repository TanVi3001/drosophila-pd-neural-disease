# Gate 24 - Parkin prospective validation

**Gate23:** `GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED_READY`
**Gate24A:** `ASSAY_COMPATIBILITY_LOCKED_DIRECTION_ONLY`
**Gate24B:** `MODEL_FREEZE_COMPLETE`
**Gate24C:** `PROSPECTIVE_PREDICTION_DRAFTED`
**Gate24D:** `WAITING_PROSPECTIVE_PREDICTION_REVIEW`
**Gate24E:** `NOT_EXECUTED`
**Holdout:** `SEALED`

## Khóa provenance
- 330 root IDs: `330`; mapping SHA256 `776274356c16eb458ef945e2a5153af4676bbddebef31cdb1b698f1d6aeaaf80`.
- Root-set SHA256: `e36b0210ea6d2d2b7225f62feba73ae5c9e6535565c8b936558d0eaaf04a2085`.
- Checkpoint SHA256: `d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691`; checkpoint không commit vào Git.
- Config SHA256: `dc037ecac8f78aaff32bfbf780c1cbf27d1b60cc6854adecbdaf0c94ce4ebdd0`.
- Seed: `[0, 1, 2, 3, 4]`; đơn vị thống kê là seed, frame không phải replicate.

## Assay và prediction
- DAM counts và climbing position không được chuyển thành FlyGym planar speed.
- Trục xác nhận chính: `LOCOMOTOR_IMPAIRMENT_DIRECTION`.
- Metric ảo phụ: `median_planar_speed_mm_s`, `distance_traveled_mm`, `displacement_mm`.
- Quantitative cross-assay validation: `false`.
- Cackovic holdout chưa mở và không được dùng để chọn burden, seed, checkpoint hoặc threshold.

## Blocker hiện tại
- Gate24D human preregistration signoff is missing
- external FlyGym runtime worktree is dirty; clean runtime commit required before GPU
- Parkin neural transform is not implemented; current operator is action-level proxy

## Claim lock
> Parkin-specific intervention with a driver-defined 330-root dopaminergic connectome target and a preregistered directional computational validation protocol; no biological validation claim.

Không được viết rằng mô hình đã biological Parkinson validation, Parkinson validated, clinical validation hoặc drug validation.

## Execution boundary
Gate24 lần này chỉ tạo preregistration, firewall, audit và blind-runner. GPU, simulation, calibration, tuning và holdout numerical analysis chưa chạy.
