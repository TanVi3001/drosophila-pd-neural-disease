# Gate 29-F - Khóa bằng chứng canonical pair

Trạng thái: `GATE29F_CANONICAL_PAIR_EVIDENCE_LOCKED`.

## Mục tiêu

Gate này đóng gói bằng chứng của cặp healthy engineering đã được chạy đúng một lần. Nó kiểm tra rằng instrumentation đọc neural/body signals không làm thay đổi rollout.

## Danh tính execution

- Pair: `GATE29_CANONICAL_PAIR_V1`
- Seed: `9202`
- Jobs: `2`
- Execution state: `PAIR_COMPLETE`
- Execution code: `e458c3f8f70c92c28313fa040e9089d44a4d7338`
- Freeze commit: `c42090c3d33cb423e0cef177117b50c1ddb6eaaa`
- Authorization commit: `77867ed400b93f21467ae1d0dd678966005d189b`
- Runtime commit: `655e854544e3d814dfe422883ff0de66b619d6c1`
- Checkpoint SHA256: `d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691`

## GPU safety

- Baseline: peak `993.0 MiB`, max `59.0 C`.
- Trace: peak `1138.0 MiB`, max `50.0 C`.
- Ngưỡng abort: `82.0 C`.
- Cả hai job kết thúc với return code 0; không retry.

## Metrics

| Metric | Baseline | Trace | Delta |
|---|---:|---:|---:|
| `median_planar_speed_mm_s` | 2.5078710186 | 2.5078710186 | 0 |
| `distance_traveled_mm` | 1.51592272278 | 1.51592272278 | 0 |
| `thorax_displacement_xy_mm` | 0.902288657165 | 0.902288657165 | 0 |

## Non-perturbation comparison

| Signal | Shape | Max absolute difference | Kết quả |
|---|---|---:|---|
| `timestamp_s` | `5000` | 0 | `PASS` |
| `thorax` | `5000x3` | 0 | `PASS` |
| `joint_positions` | `5000x66` | 0 | `PASS` |
| `actuator_position` | `5000x42` | 0 | `PASS` |
| `contact_found` | `5000x6` | 0 | `PASS` |

Kết luận kỹ thuật: `TRACE_OBSERVATION_NONPERTURBING_PASS` với `rtol=0.0` và `atol=1e-12`.

## Provenance và lưu trữ

Gói khóa `10` raw artifacts, tổng `66431868` bytes bằng SHA256. Raw `.npz` nằm ngoài Git; repository chỉ giữ manifest, checksum, kết quả tổng hợp và báo cáo nhẹ.

## Giới hạn claim

Gate 29-F chỉ chứng minh instrumentation không làm thay đổi cặp healthy engineering trong các signal đã khóa. Gate này không phải disease execution, không calibration, không xác nhận dopamine, không chứng minh neural causality sinh học và không phải biological Parkinson validation.
