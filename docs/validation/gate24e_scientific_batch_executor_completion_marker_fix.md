# Gate 24E-S4I-A.1: Sửa provenance marker hoàn tất của batch executor

## Trạng thái

- Trạng thái amendment: `EXECUTOR_TECHNICAL_AMENDMENT_COMPLETE`
- Scientific jobs đã chạy: `0`
- GPU đã chạy: `NO`
- Simulation đã chạy: `NO`
- Execution manifest: `NOT_EXECUTED`
- Holdout: `SEALED`

Gate này chỉ sửa lỗi kỹ thuật trong executor đã freeze. Không có dữ liệu khoa học,
metric, rollout hoặc diễn giải sinh học mới được tạo.

## Lỗi được phát hiện

Executor trước đây chuyển cả `stdout` và `stderr` của child process vào
`subprocess.DEVNULL`. Trong khi đó, platform runner báo hoàn tất trên `stdout` bằng
marker:

```text
Progress: 100000/100000
```

Sau khi child kết thúc, executor cũ lại tìm `100000/100000` trong các file `*.log`
của output directory. Platform không bảo đảm tạo file log chứa marker này. Vì vậy,
một simulation có thể chạy đủ, sinh artifact hợp lệ, nhưng vẫn bị executor báo
technical failure do marker trên stdout đã bị hủy.

## Sửa đổi kỹ thuật

`scripts/run_gate24e_scientific_batch.py` nay:

1. Chuyển `stdout` và `stderr` hợp nhất vào `tempfile.TemporaryFile()` trên đĩa.
2. Không hiển thị stdout của child trên console.
3. Đọc file tạm theo từng khối 64 KiB để tìm đúng marker `100000/100000` mà không
   nạp toàn bộ output vào RAM.
4. Trả về `ChildRunResult` chỉ chứa dữ kiện kỹ thuật: return code, thời điểm bắt đầu
   và kết thúc, marker có được quan sát hay không, và số byte đã capture.
5. Đóng và loại bỏ capture tạm sau khi child kết thúc; stdout thành công không được
   lưu vào scientific output.
6. Không còn dùng file `*.log` trong output làm nguồn xác nhận marker.

Một job chỉ hoàn tất khi đồng thời có marker từ child capture và toàn bộ artifact
contract: `status=PASS`, `simulation_run=true`, `rollout.npz`, `metadata.json`,
`manifest.json`, `metrics/metrics.json` và profile `GATE24E_MEMORY_SAFE`.

Executor chỉ kiểm tra sự tồn tại của `metrics/metrics.json`; nó không deserialize,
in hoặc tổng hợp speed, distance, ratio, delta hay bất kỳ scalar khoa học nào.

## Sửa provenance bộ đếm

Ngay trước khi child được launch, execution manifest được ghi nguyên tử với:

```text
executed_job_count = số job đã launch
current_job_status = LAUNCHED
```

Chỉ sau khi return code, marker và artifact contract đều đạt, executor mới tăng:

```text
completed_job_count
gpu_jobs_executed
simulation_jobs_executed
```

Nếu job đã launch nhưng thất bại, `executed_job_count` vẫn giữ job đó,
`failed_job_count=1`, `current_job_status=FAILED`, batch dừng và không retry. Nếu
runtime drift, output collision hoặc storage gate chặn trước launch thì các bộ đếm
execution không tăng.

Tại trạng thái hoàn tất 25/25, contract bắt buộc:

```text
executed_job_count = 25
completed_job_count = 25
failed_job_count = 0
gpu_jobs_executed = 25
simulation_jobs_executed = 25
```

## KeyboardInterrupt

`_run_child()` bắt `KeyboardInterrupt`, gửi terminate và chờ tối đa 10 giây. Chỉ
khi child không kết thúc trong khoảng chờ này mới gửi kill. Exception được chuyển
thành `TechnicalStop`, manifest ghi job đã launch và executor không chạy job kế
tiếp.

## Scientific freeze

Không thay đổi:

- Scientific plan SHA256:
  `4515e1916631b019711154dccb5fb887110d5572e3eb82b7ea5118c643db5aac`
- 25 jobs, gồm 5 healthy và 20 Parkin.
- Ordering `SEED_MAJOR`.
- Seeds `[0, 1, 2, 3, 4]` và parameter grid `[0.0, 0.25, 0.5, 0.75, 1.0]`.
- Runtime commit `655e854544e3d814dfe422883ff0de66b619d6c1`.
- Model commit `be4b10a80755d9f7bad931f56b8a739bd64e3619`.
- Mapping SHA256
  `776274356c16eb458ef945e2a5153af4676bbddebef31cdb1b698f1d6aeaaf80`.
- Checkpoint, artifact profile, decision rule và holdout firewall.

Old executor SHA256:
`8cab483f60e0cd3a45d43196d5c1401c77ff68b2e430bd2bed82043308192f84`.

Amended executor SHA256:
`4d10edecbc8d987285ea82eb36a7bcfd686da3abde3b5160a3dcec23a2e78f3f`.

## Phạm vi kiểm thử

Regression tests không chạy simulation thật. Chúng kiểm tra marker đầy đủ, marker
dở dang, marker vắng mặt, không phụ thuộc output log, capture không in ra console,
không lưu stdout thành công, artifact thiếu, status lỗi, `simulation_run=false`,
non-zero return code, KeyboardInterrupt, MemoryError, runtime drift, storage equality,
output collision và bộ đếm cho 1 job, lỗi ở job thứ hai, cùng batch giả lập 25/25.

## Hành động tiếp theo

```text
EXECUTE_EXACT_GATE24E_25_JOB_SCIENTIFIC_BATCH_WITH_AMENDED_FROZEN_EXECUTOR
```

Hành động này thuộc gate execution riêng. S4I-A.1 dừng trước `--execute`.
