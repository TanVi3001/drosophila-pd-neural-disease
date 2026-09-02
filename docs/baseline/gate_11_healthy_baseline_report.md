# Gate 11: Healthy Baseline Multi-Seed Report

**Trạng thái:** `PASS`

Báo cáo này ghi nhận rollout healthy computational thật theo Gate 10. Không chạy disease condition, calibration hoặc holdout validation.

## Phạm vi chạy

- Số seed: `6`; seed set: `[0, 1, 2, 3, 4, 5]`.
- Config: `experiments/gate_11_healthy_baseline/configs/healthy_baseline_multiseed.yaml`.
- Git commit: `604f988f1e274fa300e1abc385ce8fb0ff1b1005`.
- Runtime preflight: `PASS`.
- External artifact audit: `READY`.
- Disease Layer: `OFF`.
- Calibration: `OFF`.
- Video: `NOT_REQUESTED` để tránh đưa artifact lớn vào baseline commit.

## Kết quả từng seed

| Seed | Status | Observed walking speed (mm/s) | Observed distance (mm) | Locomotion | Contact | QC | Contract |
| ---: | --- | ---: | ---: | --- | --- | --- | --- |
| 0 | `PASS` | 2.8147900404746955 | 1.407676499241302 | `PASS` | `PASS` | `PASS` | `PASS` |
| 1 | `PASS` | 2.751075909819597 | 1.3758130625006904 | `PASS` | `PASS` | `PASS` | `PASS` |
| 2 | `PASS` | 3.3043165130501264 | 1.6524886881762586 | `PASS` | `PASS` | `PASS` | `PASS` |
| 3 | `PASS` | 3.30745541859186 | 1.6540584548376787 | `PASS` | `PASS` | `PASS` | `PASS` |
| 4 | `PASS` | 3.07981684120186 | 1.5402164022849538 | `PASS` | `PASS` | `PASS` | `PASS` |
| 5 | `PASS` | 3.071372395386294 | 1.5359933349325787 | `PASS` | `PASS` | `PASS` | `PASS` |

## Tổng hợp metric quan sát được

Các thống kê dưới đây được tính giữa các seed; chúng không phải uncertainty của dữ liệu ruồi thật và không được dùng để thay thế target literature.

| Metric | n | Mean | Sample SD | SE |
| --- | ---: | ---: | ---: | ---: |
| `body_orientation_variance_rad2` | 6 | 0.00034098421793060766 | 6.63448362468752e-05 | 2.7085165978891735e-05 |
| `com_velocity_mean_mm_s` | 6 | 3.806291284940517 | 0.18388240193355887 | 0.07506967623576435 |
| `displacement_mm` | 6 | 0.8889657957491469 | 0.10536267049762321 | 0.043014130109361975 |
| `distance_traveled_mm` | 6 | 1.5277077403289103 | 0.11767701363817501 | 0.04804143964467764 |
| `duration_s` | 6 | 0.4999999999999613 | 6.080941944488117e-17 | 2.482534153247273e-17 |
| `frame_count` | 6 | 5001.0 | 0.0 | 0.0 |
| `heading_variance_rad2` | 6 | 0.0003830253455806166 | 0.00020155627777755877 | 8.228500583494788e-05 |
| `mean_planar_speed_mm_s` | 6 | 1.7779315914982938 | 0.21072534099524642 | 0.08602826021872395 |
| `step_frequency_hz` | 6 | 2145.666666666833 | 225.60998795858876 | 92.10489189566658 |
| `stride_frequency_hz` | 6 | 357.6111111111388 | 37.60166465976479 | 15.350815315944432 |
| `thorax_displacement_xy_mm` | 6 | 0.8889657957491469 | 0.10536267049762321 | 0.043014130109361975 |
| `timestep_s` | 6 | 9.999999999998899e-05 | 0.0 | 0.0 |
| `total_distance_mm` | 6 | 1.5277077403289103 | 0.11767701363817501 | 0.04804143964467764 |
| `trajectory_curvature_mean_rad_per_mm` | 6 | 0.4820999397912243 | 0.0629231637455184 | 0.025688274029685612 |
| `walking_speed_max_mm_s` | 6 | 33.52460532987854 | 6.2849027727605105 | 2.565800812711071 |
| `walking_speed_mm_s` | 6 | 3.0548045197540716 | 0.2353069658831898 | 0.09606366655605078 |

## Metric contract alignment

- `mean_planar_speed_mm_s`: `PRESENT`.
- `distance_traveled_mm`: `PRESENT`.
- `displacement_mm`: `PRESENT`.

**Contract status:** `PASS`.
Các metric raw được giữ nguyên. Canonical metrics được tính hoặc kiểm tra từ rollout thật theo công thức có provenance; không chuyển distance thành speed.

- Raw runtime metric: `walking_speed_mm_s`.
  Canonical metric: `mean_planar_speed_mm_s`.
  Alias decision: `not approved; derived`.
  Reason: Derived directly from the planar thorax trajectory using the repository canonical formula. The raw walking_speed_mm_s is mean instantaneous path speed and is retained separately.
  Source/formula: `rollout.npz:thorax`; `norm(final_thorax_xy - initial_thorax_xy) / ((frame_count - 1) * timestep_s)`.
- Raw runtime metric: `total_distance_mm`.
  Canonical metric: `distance_traveled_mm`.
  Alias decision: `approved`.
  Reason: The runtime total_distance_mm is the total planar XY path length.
  Source/formula: `total_distance_mm; verified against rollout.npz:thorax`; `sum(norm(diff(thorax_xy)))`.
- Raw runtime metric: `thorax_displacement_mm (không được runtime xuất trực tiếp)`.
  Canonical metric: `displacement_mm`.
  Alias decision: `not approved; derived`.
  Reason: Derived directly as net planar thorax displacement; no distance-to-speed conversion is used.
  Source/formula: `rollout.npz:thorax`; `norm(final_thorax_xy - initial_thorax_xy)`.

## Runtime duration

- Step count: `5000`.
- Timestep: `9.999999999998899e-05` s.
- Duration: `0.49999999999996125` s.
- Duration source: `runtime_artifact:metrics/metrics.json`.
- Duration consistency check: `PASS`.
- Distance/speed consistency check: `PASS`.

## Quality control

- Mỗi seed có `no_nan=PASS` và `no_inf=PASS`; tổng hợp là không NaN/Inf.
- QC trực tiếp từ rollout: timestamp, timestep, thorax displacement, contact, joint trajectory, actuator trajectory, observation state và quaternion.
- Mỗi seed có thư mục rollout riêng và log riêng.
- Log tổng hợp: `experiments/gate_11_healthy_baseline/logs/run.log`.

## External artifact provenance

- Brain source status: `READY`.
- Checksum chi tiết nằm trong `manifests/external_input_audit.json` và `manifests/healthy_baseline_manifest.json`.

## Kết luận Gate 11B

`HEALTHY_BASELINE_RUNTIME_PASS`.
`METRIC_CONTRACT_PASS`.
`READY_FOR_DISEASE_ROLLOUTS`.
Baseline này chỉ xác nhận computational locomotion runtime; không phải biological validation và không phải Parkinson result.

## Ranh giới khoa học

Đây là computational locomotion baseline. Nó không phải biological Parkinson model validation, clinical prediction, diagnosis, drug efficacy validation hoặc thay thế thí nghiệm wet-lab.
