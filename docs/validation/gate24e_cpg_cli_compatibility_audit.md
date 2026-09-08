# Gate 24E-C1 — Audit tương thích CLI CPG

## Phạm vi

Đây là audit kỹ thuật cho runner Gate 24E. Audit không chạy FlyGym, không chạy
GPU, không mở holdout và không thay đổi model, mapping, checkpoint, seed,
timestep, số bước, controller, stimulus, metric hay decision rule.

## Kết luận

`CPG_CLI_OMISSION_SEMANTICALLY_EQUIVALENT`

Có đủ bằng chứng để bỏ cờ `--cpg-frequency-hz` khỏi lệnh con của platform
đông lạnh. Wrapper vẫn nhận tham số `--cpg-frequency-hz` để giữ tương thích API,
nhưng chỉ chấp nhận đúng `12.0` Hz. Giá trị khác bị từ chối bằng lỗi rõ ràng;
không bị bỏ qua âm thầm.

## Bằng chứng CLI

| Bề mặt | Kết quả |
|---|---|
| `scripts/run_neural_experiment.py` | Có `--cpg-frequency-hz`, mặc định `12.0` |
| `drosophila-pd-flygym-gate24-clean/scripts/run_brain_body_rollout.py` | Không có `--cpg-frequency-hz` trong `argparse` |
| Platform commit | `3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06` |
| FlyGym version | `2.1.0` |

Probe trước đó thất bại ở bước parse CLI vì wrapper chuyển cờ không được runner
hỗ trợ. Không có physics step hay GPU simulation nào bắt đầu.

## Bằng chứng CPG

Audit được thực hiện bằng source/runtime FlyGym 2.1.0 đã cài trong môi trường
được dùng cho platform. Hàm:

```text
make_tripod_cpg_network(
    timestep: float,
    *,
    intrinsic_frequency: float = 12.0,
    intrinsic_amplitude: float = 1.0,
    coupling_strength: float = 10.0,
    convergence_coef: float = 20.0,
    seed: int = 0,
) -> CPGNetwork
```

Source file được kiểm tra:

```text
.../site-packages/flygym_demo/complex_terrain/cpg_controller.py
SHA256: 86804054621f35e28c74f0a88db6a73faa17db586f5554db00674c9851eab592
```

Instantiation tĩnh, không tạo `Simulation`, cho kết quả:

```text
intrinsic_freqs = [12.0, 12.0, 12.0, 12.0, 12.0, 12.0]
intrinsic_amps  = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
timestep        = 0.0001
```

Source của `calculate_ddt` dùng `intrinsic_term = 2 * pi * nu`. Vì vậy `nu`
được biểu diễn bằng Hz, không phải rad/s. Sáu oscillator đều dùng cùng giá
trị 12.0 Hz khi tạo bằng helper mặc định. Đây là bằng chứng controller/runtime,
không phải tuyên bố sinh học.

## Quy tắc tương thích đã áp dụng

1. Kiểm tra platform commit đúng commit đông lạnh.
2. Kiểm tra runtime package đúng FlyGym `2.1.0`.
3. Kiểm tra giá trị wrapper yêu cầu đúng default đã audit `12.0` Hz.
4. Nếu cả ba điều kiện đúng, bỏ `--cpg-frequency-hz` khỏi child command.
5. Nếu platform/version/default thay đổi, dừng bằng lỗi và yêu cầu refreeze,
   human review; không tự sửa preregistration.

External FlyGym worktree không bị chỉnh sửa và pinned commit không đổi.

## Bảo toàn trạng thái khoa học

Các giá trị freeze được đối chiếu lại từ manifest Gate 24:

- mapping 330 root IDs: `776274356c16eb458ef945e2a5153af4676bbddebef31cdb1b698f1d6aeaaf80`
- target SHA: `e36b0210ea6d2d2b7225f62feba73ae5c9e6535565c8b936558d0eaaf04a2085`
- healthy checkpoint: `d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691`
- neural transform contract: `ffc7d25c7cf225c7cb69ff43a62133dbf2bf5a4f22f5bb0138a9217b2b375c71`
- neural transform source: `8f8fe415b9a2d4490783775ef9a4aa45a82bfe624f37d969d89eda1a7bac383b`
- parameter grid: `[0.0, 0.25, 0.5, 0.75, 1.0]`
- scientific seeds: `[0, 1, 2, 3, 4]`
- platform commit: `3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06`

Các Parkin checkpoint SHA vẫn lấy nguyên từ job plan hiện hành; Gate 24E-C1
không materialize hay thay đổi checkpoint nào.

## Probe trước đó

Probe seed `9001` vẫn được giữ nguyên tại thư mục kỹ thuật riêng. Trạng thái
lịch sử vẫn là `STORAGE_PROBE_TECHNICAL_FAILURE`. Các số đo `972 bytes`,
`4096 bytes` và số dẫn xuất liên quan được đánh dấu:

`INVALID_FOR_STORAGE_CAPACITY_ESTIMATION_DUE_TO_PRE_SIMULATION_FAILURE`

Chúng không được dùng làm ước lượng dung lượng. Gate này không retry probe.

## Trạng thái sau audit

- `wrapper_fix_applied`: `true`
- `probe_retry_authorized`: `false`
- `scientific_jobs_authorized`: `false`
- `holdout_opened`: `false`
- `READY_FOR_BLINDED_GPU_PREDICTION`: chưa đủ điều kiện thực thi trong task này
- Gate 24E scientific jobs executed: `0`

## Exact dry command

Command sau đây được xây dựng để kiểm tra hình dạng, nhưng **không được thực
thi trong Gate 24E-C1**:

```text
<python> scripts/run_neural_experiment.py
  --brain-root E:\\Drosophila_Parkinson\\external\\fly-brain-audit
  --platform-root E:\\Drosophila_Parkinson\\drosophila-pd-flygym-gate24-clean
  --seed 9001 --steps 100000 --device cuda
  --output experiments\\gate_24e_storage_probe\\run
```

Lệnh không có `--cpg-frequency-hz`, `--prepared-checkpoint`, `--parameter`,
hay `--video`.
