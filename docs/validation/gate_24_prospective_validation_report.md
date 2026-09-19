# Gate 24 - Parkin prospective validation

**Gate23:** `GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED_READY`
**Gate24A:** `ASSAY_COMPATIBILITY_LOCKED_DIRECTION_ONLY`
**Gate24B:** `WAITING_MODEL_FREEZE`
**Gate24C:** `PROSPECTIVE_PREDICTION_DRAFTED`
**Gate24D:** `PROSPECTIVE_PREDICTION_LOCKED`
**Gate24E:** `NOT_EXECUTED`
**Holdout:** `SEALED`

## Khóa provenance
- 330 root IDs: `330`; mapping SHA256 `776274356c16eb458ef945e2a5153af4676bbddebef31cdb1b698f1d6aeaaf80`.
- Root-set SHA256: `e36b0210ea6d2d2b7225f62feba73ae5c9e6535565c8b936558d0eaaf04a2085`.
- Checkpoint SHA256: `MISSING`; checkpoint không commit vào Git.
- Parkin neural checkpoint SHA256: `GRID_MANIFEST`; materialized CPU-side, không chạy simulation.
- Neural transform: `WAITING_NEURAL_TRANSFORM`; operation level `NEURAL_PRE_ACTION`.
- Action-level proxy: `NEGATIVE_CONTROL_ONLY`; không phải primary disease representation.
- Primary parameter: `NONE_SELECTED`; status `PREREGISTERED_GRID_NO_SINGLE_BIOLOGICAL_PARAMETER`.
- Grid checkpoint hashes: `{'0.25': 'MISSING', '0.5': 'MISSING', '0.75': 'MISSING', '1.0': 'MISSING'}`.
- Config SHA256: `f824a3e3a53273f3951ad37a7963c9aaa5a87f5928fce1fd5cd043317afb833b`.
- Seed: `[0, 1, 2, 3, 4]`; đơn vị thống kê là seed, frame không phải replicate.

## Assay và prediction
- DAM counts và climbing position không được chuyển thành FlyGym planar speed.
- Trục xác nhận chính: `LOCOMOTOR_IMPAIRMENT_DIRECTION`.
- Metric ảo phụ: `median_planar_speed_mm_s`, `distance_traveled_mm`, `displacement_mm`.
- Quantitative cross-assay validation: `false`.
- Cackovic holdout chưa mở và không được dùng để chọn burden, seed, checkpoint hoặc threshold.

## Blocker hiện tại
- model freeze hashes or required locks are incomplete
- Parkin neural checkpoint/manifest is not ready; action proxy cannot be primary

## Claim lock
> Parkin-specific intervention represented by a reviewed driver-defined neural perturbation and a preregistered directional computational validation protocol; no biological validation claim.

Không được viết rằng mô hình đã biological Parkinson validation, Parkinson validated, clinical validation hoặc drug validation.

## Execution boundary
Gate24 lần này chỉ tạo preregistration, firewall, audit và blind-runner. GPU, simulation, calibration, tuning và holdout numerical analysis chưa chạy.
