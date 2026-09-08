# Gate 24E-S4I-A: Freeze executor khoa học Gate24E

## Trạng thái

- Kết quả dry-run: `READY_TO_EXECUTE_EXACT_GATE24E_25_JOB_BATCH`
- Plan SHA256: `4515e1916631b019711154dccb5fb887110d5572e3eb82b7ea5118c643db5aac`
- Authorization: `SCIENTIFIC_BATCH_AUTHORIZATION_APPROVED`
- Decision: `APPROVED_FOR_EXACT_GATE24E_25_JOB_BATCH`
- Activation: `READY_FOR_GATE24E_25_JOB_SCIENTIFIC_BATCH`
- Jobs đã chạy: `0`
- Holdout: `SEALED`

Gate này chỉ freeze và kiểm tra executor. Không có scientific job, GPU hoặc
FlyGym simulation nào được chạy.

## Executor contract

Executor: `scripts/run_gate24e_scientific_batch.py`

Executor chỉ nhận đúng một trong hai mode:

- `--dry-run`: đọc và kiểm tra toàn bộ contract, không tạo output/log.
- `--execute`: dành cho gate execution riêng; không được gọi trong S4I-A.

Danh sách job được đọc trực tiếp từ `scientific_batch_plan.json`. Executor không
tự tái tạo, sắp xếp, thay seed, thay parameter, thay checkpoint hoặc thay output
path.

Ma trận bắt buộc:

- 25 jobs: 5 healthy và 20 Parkin.
- Ordering: `SEED_MAJOR`.
- Mỗi seed `0..4`: healthy, `p=0.25`, `p=0.50`, `p=0.75`, `p=1.00`.
- Không có Parkin `p=0`.
- Technical seed `9001` bị loại.
- Job ID và output directory phải duy nhất.
- Jobs chỉ chạy tuần tự từ index 1 đến 25.

## Runtime và provenance

- Python: `3.12.10`
- Approved Python: `E:\Drosophila_Parkinson\drosophila-pd-flygym\.venv\Scripts\python.exe`
- FlyGym: `2.1.0`
- Torch: `2.5.1+cu121`
- CUDA: `12.1`
- CUDA available: `true`
- GPU: `NVIDIA GeForce RTX 3050 6GB Laptop GPU`
- Runtime commit: `655e854544e3d814dfe422883ff0de66b619d6c1`
- Artifact profile: `GATE24E_MEMORY_SAFE`
- Runtime worktree: clean

## Storage safety

Executor dùng duy nhất technical measurement của attempt_04:

```text
final_artifact_bytes = 558250361
transient_bytes = 667690631
reserve_fraction = 0.20
```

Công thức cho `remaining_job_count`:

```text
remaining_final = remaining_job_count * 558250361
remaining_peak = remaining_final + 667690631
remaining_reserve = ceil(remaining_peak * 0.20)
remaining_required = remaining_peak + remaining_reserve
```

Với 25 jobs, yêu cầu tái tạo đúng `17,548,739,588 bytes`. Quy tắc là
`live_free_bytes > remaining_required`, tức phép so sánh nghiêm ngặt.

Dry-run ghi nhận:

- Live free bytes: `19,963,760,640`
- Initial remaining requirement: `17,548,739,588`
- Storage safety: `PASS`

## Preflight và output policy

Trước khi `--execute` có thể chạy job đầu tiên, executor yêu cầu auditor trả:

- `READY_FOR_GATE24E_25_JOB_SCIENTIFIC_BATCH`
- `blockers=[]`
- `authorization_valid=true`
- `capacity_pass=true`
- `checkpoint_hashes_pass=true`
- `holdout=SEALED`

Output root `experiments/gate_24e_blinded_parkin_prediction/runs` phải chưa tồn
tại. Dry-run không tạo root này và không tạo
`scientific_batch_execution.log`.

Execution manifest ban đầu là:

```text
status=NOT_EXECUTED
executed_job_count=0
completed_job_count=0
failed_job_count=0
gpu_jobs_executed=0
simulation_jobs_executed=0
```

## Completion và failure policy

Job chỉ hoàn thành khi return code bằng 0 và đồng thời có:

- `status.json` với `status=PASS`, `simulation_run=true`;
- `rollout.npz`;
- `metadata.json`;
- `manifest.json` với artifact profile chính xác;
- `metrics/metrics.json`;
- log chứa marker đầy đủ `100000/100000`.

Nếu lỗi return code, KeyboardInterrupt, MemoryError, thiếu artifact, thiếu
completion marker, storage không đủ hoặc runtime drift, executor chuyển sang:

```text
GATE24E_SCIENTIFIC_BATCH_TECHNICAL_STOP
```

và yêu cầu:

```text
HUMAN_REVIEW_GATE24E_SCIENTIFIC_BATCH_TECHNICAL_STOP
```

Không retry, không skip, không đổi seed/parameter/checkpoint, không overwrite,
không resume tự động. Completed output không được chạy lại.

## Scientific firewall

Executor chỉ kiểm tra artifact kỹ thuật. Nó không đọc hoặc in speed, distance,
ratio, delta hay diễn giải sinh học theo từng job. Nó không gọi analyzer và không
mở dữ liệu holdout. Sau khi đủ 25 jobs, trạng thái tối đa của executor chỉ là:

```text
GATE24E_25_JOB_SCIENTIFIC_BATCH_COMPLETE_UNANALYZED
```

Phân tích khoa học là gate riêng sau khi freeze prediction.

## Validation

- Preflight auditor: `READY_FOR_GATE24E_25_JOB_SCIENTIFIC_BATCH`, blockers rỗng.
- Dry-run: `READY_TO_EXECUTE_EXACT_GATE24E_25_JOB_BATCH`.
- Holdout firewall: `SEALED`.
- Pytest: `575 passed`.
- Compileall: `PASS`.
- `git diff --check`: `PASS`.
- GPU executed: `NO`.
- Simulation executed: `NO`.

## Next action

```text
EXECUTE_EXACT_GATE24E_25_JOB_SCIENTIFIC_BATCH_WITH_FROZEN_EXECUTOR
```

Gate S4I-A dừng tại đây và không tự động thực hiện next action.
