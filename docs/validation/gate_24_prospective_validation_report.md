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
- Parkin neural checkpoint SHA256: `GRID_MANIFEST`; materialized CPU-side, không chạy simulation.
- Neural transform: `PARKIN_DRIVER_DEFINED_NEURAL_TRANSFORM_READY`; operation level `NEURAL_PRE_ACTION`.
- Action-level proxy: `NEGATIVE_CONTROL_ONLY`; không phải primary disease representation.
- Primary parameter: `NONE_SELECTED`; status `PREREGISTERED_GRID_NO_SINGLE_BIOLOGICAL_PARAMETER`.
- Grid checkpoint hashes: `{'0.25': 'dd2a4413d1aa4baed30df96884afdd030bac3a246d1bcc7a241baa955082cb8c', '0.5': 'f682057bfff2bd523ba9a934970c9986e041ce44cb16fb8781ce2e9c5aebcff1', '0.75': '0b73e25620d10e56e293f859fb95c45630c7b798073b482d73f95a7d5c51e802', '1.0': '0ecf37ce96b6d4ea09b00204c3f01c6f41b6a2820b5f21170c6856760850e2b1'}`.
- Config SHA256: `f824a3e3a53273f3951ad37a7963c9aaa5a87f5928fce1fd5cd043317afb833b`.
- Seed: `[0, 1, 2, 3, 4]`; đơn vị thống kê là seed, frame không phải replicate.

## Assay và prediction
- DAM counts và climbing position không được chuyển thành FlyGym planar speed.
- Trục xác nhận chính: `LOCOMOTOR_IMPAIRMENT_DIRECTION`.
- Metric ảo phụ: `median_planar_speed_mm_s`, `distance_traveled_mm`, `displacement_mm`.
- Quantitative cross-assay validation: `false`.
- Cackovic holdout chưa mở và không được dùng để chọn burden, seed, checkpoint hoặc threshold.

## Blocker hiện tại
- Gate24D human preregistration signoff is missing

## Claim lock
> Parkin-specific intervention represented by a reviewed driver-defined neural perturbation and a preregistered directional computational validation protocol; no biological validation claim.

Không được viết rằng mô hình đã biological Parkinson validation, Parkinson validated, clinical validation hoặc drug validation.

## Execution boundary
Gate24 lần này chỉ tạo preregistration, firewall, audit và blind-runner. GPU, simulation, calibration, tuning và holdout numerical analysis chưa chạy.
