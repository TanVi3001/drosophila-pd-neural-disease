# Gate24.1 - Parkin neural transform report

## Kết quả

Gate24.1 đã thay thế action-level proxy khỏi vị trí primary bằng một neural
transform tính toán ở trước bước sinh action:

```text
healthy neural checkpoint
  -> reviewed Parkin neural transform
  -> brain output
  -> controller/action hook
  -> FlyGym
```

Trạng thái kỹ thuật:

```text
PARKIN_DRIVER_DEFINED_NEURAL_TRANSFORM_READY
```

Đây là computational implementation có provenance, không phải biological
Parkinson validation.

## Mapping và checkpoint

- Mapping sử dụng đúng `330` root-ID từ `driver_to_connectome_mapping.csv`.
- Mapping SHA256: `776274356c16eb458ef945e2a5153af4676bbddebef31cdb1b698f1d6aeaaf80`.
- Root-set SHA256: `e36b0210ea6d2d2b7225f62feba73ae5c9e6535565c8b936558d0eaaf04a2085`.
- Không sử dụng bộ `342` root-ID Riemensperger.
- Healthy checkpoint SHA256: `d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691`.
- Parkin candidate checkpoint SHA256: `f682057bfff2bd523ba9a934970c9986e041ce44cb16fb8781ce2e9c5aebcff1`.
- Healthy checkpoint không bị ghi đè.
- Checkpoint disease không commit vào Git; artifact nằm trong `results/` và cần
  được lưu qua artifact storage khi chạy thật.

## Transform

Operation level: `NEURAL_PRE_ACTION`.

Với parameter `p` không có đơn vị:

```text
w_prime[e] = w[e] * (1 - p), nếu presynaptic root của edge e thuộc target T
w_prime[e] = w[e],           nếu không thuộc T
```

Materialization CPU-side với sensitivity candidate `p=0.5` đã hoàn tất:

- Identity test tại `p=0`: `PASS`.
- Edge bị tác động: `62,206`.
- Giá trị `p=0.5` không được diễn giải là 50% Parkin knockdown.
- Primary parameter: `NONE_SELECTED`; policy `PREREGISTERED_GRID_NO_SINGLE_BIOLOGICAL_PARAMETER`.
- Sensitivity grid: `[0.0, 0.25, 0.5, 0.75, 1.0]`.

Action-level proxy được giữ ở vai trò `NEGATIVE_CONTROL_ONLY`, không phải
primary disease representation.

## Runtime và kiểm thử

- FlyGym canonical commit: `3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06`.
- Worktree sạch dùng cho runtime: `E:/Drosophila_Parkinson/drosophila-pd-flygym-gate24-clean`.
- Worktree FlyGym gốc vẫn dirty và không bị reset, stash, clean hoặc xóa.
- GPU: `NO`.
- Simulation: `NO`.
- Calibration: `NO`.
- Holdout: sealed, không mở và không dùng để chọn parameter.
- Compileall: `PASS`.
- Pytest: `310 passed`.
- `git diff --check`: `PASS`.

## Trạng thái Gate24

- Gate23: `GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED_READY`.
- Gate24A: `ASSAY_COMPATIBILITY_LOCKED_DIRECTION_ONLY`.
- Gate24B: `MODEL_FREEZE_COMPLETE` ở mức artifact/hash; commit Git của neural
  changes còn pending theo quy tắc task.
- Gate24C: `PROSPECTIVE_PREDICTION_DRAFTED`.
- Gate24D: `WAITING_PROSPECTIVE_PREDICTION_REVIEW`.
- Gate24E: `NOT_EXECUTED`.
- Holdout: `SEALED`.

## Blockers còn lại

1. Human reviewer chưa ký Gate24D.
2. Chưa có cơ sở ngoài holdout để khóa một primary computational parameter;
   vì vậy chỉ dùng sensitivity grid đã đăng ký trước.
3. Neural changes chưa được commit/push trong task này; framework base commit là
   `b03fa06cbbb8cde8544a59abb882722019a6d74a`.

## Gate24.2 update

The neural implementation is now committed as
`be4b10a80755d9f7bad931f56b8a739bd64e3619`. The former `p=0.5` artifact is
not a selected primary parameter. The prospective design locks the complete
grid `[0.0, 0.25, 0.5, 0.75, 1.0]` under
`PREREGISTERED_GRID_NO_SINGLE_BIOLOGICAL_PARAMETER`; `0.0` is the healthy
identity and all four positive levels are retained.

The tracked grid manifest is
`research/validation/prospective/parkin_checkpoint_grid_manifest.json`.
Gate24D remains `WAITING_PROSPECTIVE_PREDICTION_REVIEW`; reviewer identity is
not filled automatically. No GPU, simulation, calibration, tuning, or holdout
analysis was performed.

## Claim lock

Claim hiện được phép dùng:

> Parkin-specific intervention represented by a reviewed driver-defined neural
> perturbation and a preregistered directional computational validation protocol;
> no biological validation claim.

Không được viết rằng mô hình đã xác nhận Parkinson sinh học, đã xác nhận cơ chế
gene-specific ở cấp biểu hiện gene, là công cụ chẩn đoán hoặc là công cụ thử
thuốc.
