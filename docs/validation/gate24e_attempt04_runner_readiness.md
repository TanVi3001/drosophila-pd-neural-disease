# Gate 24E-S4B: Readiness của runner attempt_04

## Kết quả

`READY_FOR_GATE24E_STORAGE_ATTEMPT_04`

Runner single-use đã được triển khai tại
`scripts/run_gate24e_storage_probe_attempt04.py`. Chế độ được xác nhận trong
gate này là `--dry-run`; chưa chạy `--execute`, chưa khởi động GPU và chưa
khởi động simulation.

## Contract đã khóa

- Human authorization: `ATTEMPT04_AUTHORIZATION_APPROVED`.
- Reviewer: `Tuan Le` và `To Dang Minh Tuan`; ngày `2026-09-08`.
- Seed kỹ thuật: `9001`, loại khỏi scientific seeds `0..4`.
- Steps: `100000`; duration: `10.0 s`; device: `cuda`.
- Runtime: commit `655e854544e3d814dfe422883ff0de66b619d6c1`.
- Artifact profile: `GATE24E_MEMORY_SAFE`.
- Runtime worktree phải sạch trước mỗi lần chạy.
- `attempt_04` không được tồn tại trước execution; không overwrite, retry,
  cleanup tự động hay tạo `attempt_05`.

## Hành vi khi execute trong tương lai

Runner sẽ ghi authorization snapshot, log và manifest nhẹ; theo dõi free disk
mỗi giây; giữ lại `free_before`, `minimum_free_during_run`, `free_after`,
`final_artifact_bytes`, `peak_disk_consumption` và phép chiếu 25 job theo công
thức đã duyệt. Nếu có `KeyboardInterrupt`, child được kết thúc sạch, log được
bảo toàn, attempt được đánh dấu consumed và runner trả mã lỗi; tuyệt đối không
restart.

Một probe thành công phải có marker `100000/100000`, `status.json=PASS`,
`rollout.npz`, `metadata.json`, `manifest.json` và `metrics/metrics.json`.
Không yêu cầu `rollout.json`, viewer hoặc video.

## Ranh giới khoa học

Probe này chỉ đo khả năng lưu trữ kỹ thuật. `scientific_jobs_executed=0`,
`scientific_batch_authorized=false`, holdout vẫn `SEALED`, và runner không gọi
analyzer hay tính kết quả hướng bệnh. Nó không thay đổi model, mapping,
checkpoint, grid, seed khoa học hay claim lock.
