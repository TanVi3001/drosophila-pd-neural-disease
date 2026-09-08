# Gate 24E-S3A: Kích hoạt runtime cho attempt_03

Gate này chỉ chuẩn bị một technical storage probe duy nhất bằng runtime
memory-safe đã được hai reviewer phê duyệt. Lệnh `--dry-run` xác minh commit,
profile artifact, provenance, worktree sạch, holdout và seed tách khỏi scientific
batch; lệnh này không chạy mô phỏng và không khởi tạo GPU.

Trạng thái hiện tại:

- `READY_FOR_GATE24E_STORAGE_ATTEMPT_03`
- `attempt_03` chưa thực thi.
- `scientific_batch_authorized=false`.
- Holdout vẫn `SEALED`.
- `attempt_01` và `attempt_02` được giữ nguyên.

Lệnh kiểm tra:

```powershell
py -3.12 scripts/run_gate24e_storage_probe_attempt03.py --dry-run
```

Không gọi `--execute` trong Gate 24E-S3A. Việc chạy technical probe là một
task được phê duyệt riêng và không phải là calibration, holdout validation hay
scientific batch.
