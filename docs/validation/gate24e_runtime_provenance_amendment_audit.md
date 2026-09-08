# Gate 24E-R1: Kiểm toán amendment provenance của runtime memory-safe

## Kết luận kiểm toán

Trạng thái hiện tại là `WAITING_GATE24E_RUNTIME_AMENDMENT_REVIEW`.

So sánh source giữa runtime gốc `3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06`
và runtime memory-safe `655e854544e3d814dfe422883ff0de66b619d6c1` cho thấy thay đổi
được giới hạn ở serialization, phân tích scalar hậu mô phỏng, chính sách artifact tùy chọn
và cờ CLI chọn profile. Không có bằng chứng source-level về thay đổi quỹ đạo mô phỏng.

`SIMULATION_SEMANTICS_CHANGED: false`

Kết luận này cho phép đưa amendment cho hai người kiểm tra độc lập. Nó chưa cho phép chạy
`attempt_03` và chưa cho phép chạy 25 job khoa học.

## Chuỗi provenance được bảo toàn

| Thành phần | Giá trị khóa |
| --- | --- |
| Gate 24D signoff | `PROSPECTIVE_PREDICTION_LOCKED` |
| Gate 24D signoff SHA256 | `24e5118a778257887c9541ceb679e9c4d4a87ddd2053a81c000301e6b9d90526` |
| Model freeze SHA256 | `eb370a25c00b39173272468e050e4ab917a0e99df0c3ee3ab73635868dfe916a` |
| Runtime gốc | `3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06` |
| Runtime amendment | `655e854544e3d814dfe422883ff0de66b619d6c1` |
| Profile amendment | `GATE24E_MEMORY_SAFE` |
| Holdout | `SEALED` |
| Job khoa học đã chạy | `0/25` |

Gate 24D vẫn là phê duyệt cho hợp đồng khoa học ban đầu. Gate 24E-R1 là review object bổ
sung cho thay đổi kỹ thuật; nó không ghi đè reviewer, ngày hoặc quyết định Gate 24D.

## Phạm vi diff nguồn

Diff chính xác gồm sáu file, trong đó năm file là source runtime và một file là test:

| File | Phân loại | Ảnh hưởng simulation |
| --- | --- | --- |
| `scripts/run_brain_body_rollout.py` | `CLI_ARTIFACT_PROFILE`, `POST_SIMULATION_EXPORT`, `POST_SIMULATION_ANALYSIS`, `OPTIONAL_POSTPROCESS` | Không |
| `src/drosophila_pd/flygym_adapter/export.py` | `POST_SIMULATION_EXPORT` | Không |
| `src/drosophila_pd/analysis/memory_safe.py` | `POST_SIMULATION_ANALYSIS` | Không |
| `src/drosophila_pd/flygym_adapter/__init__.py` | `POST_SIMULATION_EXPORT` API export | Không |
| `src/drosophila_pd/analysis/__init__.py` | `POST_SIMULATION_ANALYSIS` API export | Không |
| `tests/test_memory_safe_export.py` | Test-only | Không |

Không có vùng thay đổi nào được phân loại là `SIMULATION_SEMANTICS` với giá trị thay đổi
`true`. Hash chuẩn hóa của thân vòng lặp ở cả hai commit cùng là
`d90d204826e1bda64197b74eecabf9cb96fe17eef3907df41bd79c7238223b5e`.

## Kiểm toán đường thực thi mô phỏng

Thứ tự sau không đổi:

1. `brain.step()`.
2. `decoder.update(...)`.
3. `bridge.compute_drive(...)`.
4. `controller.step(...)`.
5. `apply_locomotion_action(...)`.
6. `simulation.step()`.
7. `recorder.record()`.

Diff không thay đổi seed, stimulus, số step, timestep, cách dựng controller, CPG, disease
layer, brain update, action application hoặc MuJoCo stepping. Nhánh memory-safe chỉ bắt
đầu sau khi vòng lặp hoàn tất và `frame_count` đã được chốt.

## Khác biệt artifact được phép

| Artifact/chức năng | Legacy | `GATE24E_MEMORY_SAFE` |
| --- | --- | --- |
| Full-frame `rollout.json` | Có | Không yêu cầu |
| `rollout.npz` | Có | Bắt buộc, ghi bằng memmap và streaming ZIP |
| Metadata | Có | Giữ lại |
| Manifest/checksum | Có | Giữ lại |
| Scalar metrics | Có | Giữ lại |
| Viewer và viewer bundle | Có | Bỏ qua |
| Video | Không thuộc quyết định Gate 24 | Không yêu cầu |
| Biomarker postprocess | Có ở legacy | Bỏ qua vì không thuộc quyết định chính |

Các khác biệt này làm giảm peak memory sau mô phỏng. Chúng không thay đổi trạng thái neural,
motor command hoặc physics trajectory.

## Tương đương dữ liệu và metric

Fixture tổng hợp nhỏ được chạy không GPU và không simulation, cho kết quả `6 passed`:

- `NPZ_EQUIVALENCE_PASS`: mọi array trong NPZ memory-safe bằng NPZ legacy.
- `PRIMARY_METRIC_EQUIVALENCE_PASS`: `median_planar_speed_mm_s` không đổi.
- `SECONDARY_METRIC_EQUIVALENCE_PASS`: `distance_traveled_mm` không đổi.
- `MEMORY_REGRESSION_PASS`: đường export không gọi serializer full-frame và peak Python
  memory của fixture nằm dưới guard đã khóa.

Định nghĩa phân tích vẫn là:

```text
step_distance = norm(diff(thorax[:, :2]))
instantaneous_speed = step_distance / diff(timestamp_s)
median_planar_speed = median(instantaneous_speed)
distance_traveled = sum(step_distance)
```

Analyzer khoa học vẫn là `scripts/analyze_gate24e_blinded_prediction.py`, SHA256
`e179a58cdcf5b6dc9e4a0960be2e25fe792b7356ffdf8cb94754184ae8d2bed4`.
Decision rule đã preregister không đổi.

## Audit adapter và công việc chỉ được làm sau review

Ba adapter hiện tại cố ý chưa được chuyển sang runtime amendment:

- `scripts/run_neural_experiment.py` cần forward duy nhất
  `--artifact-profile GATE24E_MEMORY_SAFE` đến canonical runner.
- `scripts/run_gate24e_runtime_adapter.py` đang pin runtime gốc; sau amendment review mới
  được đổi sang clean path/commit mới và thêm profile mà không đổi seed, step, device,
  checkpoint, stimulus, CPG hoặc physics.
- `scripts/run_gate24e_storage_probe_retry.py` chỉ quản lý `attempt_02`; không được tái dùng
  để chạy `attempt_03`. Một authorization và command manifest riêng là bắt buộc.

Không triển khai thay đổi adapter trong R1 để tránh tạo đường thực thi vượt qua human gate.

## Giới hạn khoa học

Amendment không thay đổi mapping, root set, checkpoint, neural transform, parameter grid,
seed, metric hoặc decision rule. Nó không phải biological validation, không mở holdout và
không tạo kết quả khoa học mới.
