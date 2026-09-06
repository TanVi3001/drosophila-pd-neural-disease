# Pipeline thí nghiệm ảo có ràng buộc từ literature

## Mục đích

Pipeline này biến một phenotype trong paper thành một protocol computational có
thể kiểm tra lại trên virtual fly. Mỗi protocol phải giữ provenance, assay,
metric, statistic, unit-of-analysis, allocation, runtime và scientific boundary.

Pipeline không tự biến paper thành dữ liệu huấn luyện và không tự tạo kết quả.
Lệnh preflight chỉ đọc config/target, sinh manifest và dừng trước simulation.

## Sơ đồ

```text
paper + supplementary
  -> source/phenotype review
  -> endpoint + assay bridge
  -> calibration hoặc holdout allocation
  -> preflight manifest
  -> FlyGym/MuJoCo runner
  -> seed-level QC/metrics/video
  -> baseline comparison
  -> mismatch/concordance report
```

## Chạy preflight

```powershell
py -3.12 scripts/prepare_literature_constrained_experiment.py `
  --config experiments/literature_constrained/configs/chen_alpha_syn_calibration.yaml `
  --output results/literature_constrained/chen_alpha_syn_calibration

py -3.12 scripts/prepare_literature_constrained_experiment.py `
  --config experiments/literature_constrained/configs/pozo_pink1_holdout.yaml `
  --output results/literature_constrained/pozo_pink1_holdout
```

Mỗi output có:

- `experiment_manifest.json`: hash config, validation status, plan và boundary;
- `preflight_report.md`: lỗi hoặc điều kiện còn thiếu;
- `simulation_executed=false`: preflight không được trình bày như rollout.

`READY_FOR_RUNTIME` chỉ nghĩa là protocol/target đã qua preflight. Để chạy
simulation, vẫn cần brain source, checkpoint, annotation và platform runtime
đúng provenance; việc chạy phải được thực hiện bằng runner đã được review.

## Chính sách chuyển assay

- `identity`: metric và unit hai bên giống nhau.
- `physical_unit_conversion`: chỉ đổi đơn vị vật lý trong cùng họ speed/velocity
  và phải có factor, rationale, provenance.
- Không đổi distance thành speed.
- Không đổi median thành mean.
- `activity_time_s`, `climbing_score` và `DAM_activity` hiện là
  `validation_only` cho đến khi có virtual assay tương ứng.

## Ranh giới diễn giải

Pipeline này hỗ trợ paper-guided virtual experiment, organism-level proxy,
directional concordance và quantitative mismatch. Nó không chứng minh
biological Parkinson validation, gene-specific mechanism, chẩn đoán lâm sàng
hay hiệu lực thuốc.
