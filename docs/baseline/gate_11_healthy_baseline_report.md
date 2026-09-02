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
| 0 | `PASS` | 2.8147900404746955 | 1.407676499241302 | `PASS` | `PASS` | `PASS` | `INCOMPLETE` |
| 1 | `PASS` | 2.751075909819597 | 1.3758130625006904 | `PASS` | `PASS` | `PASS` | `INCOMPLETE` |
| 2 | `PASS` | 3.3043165130501264 | 1.6524886881762586 | `PASS` | `PASS` | `PASS` | `INCOMPLETE` |
| 3 | `PASS` | 3.30745541859186 | 1.6540584548376787 | `PASS` | `PASS` | `PASS` | `INCOMPLETE` |
| 4 | `PASS` | 3.07981684120186 | 1.5402164022849538 | `PASS` | `PASS` | `PASS` | `INCOMPLETE` |
| 5 | `PASS` | 3.071372395386294 | 1.5359933349325787 | `PASS` | `PASS` | `PASS` | `INCOMPLETE` |

## Tổng hợp metric quan sát được

Các thống kê dưới đây được tính giữa các seed; chúng không phải uncertainty của dữ liệu ruồi thật và không được dùng để thay thế target literature.

| Metric | n | Mean | Sample SD | SE |
| --- | ---: | ---: | ---: | ---: |
| `body_orientation_variance_rad2` | 6 | 0.00034098421793060766 | 6.63448362468752e-05 | 2.7085165978891735e-05 |
| `com_velocity_mean_mm_s` | 6 | 3.806291284940517 | 0.18388240193355887 | 0.07506967623576435 |
| `heading_variance_rad2` | 6 | 0.0003830253455806166 | 0.00020155627777755877 | 8.228500583494788e-05 |
| `step_frequency_hz` | 6 | 2145.666666666833 | 225.60998795858876 | 92.10489189566658 |
| `stride_frequency_hz` | 6 | 357.6111111111388 | 37.60166465976479 | 15.350815315944432 |
| `thorax_displacement_xy_mm` | 6 | 0.8889657957491469 | 0.10536267049762321 | 0.043014130109361975 |
| `total_distance_mm` | 6 | 1.5277077403289103 | 0.11767701363817501 | 0.04804143964467764 |
| `trajectory_curvature_mean_rad_per_mm` | 6 | 0.4820999397912243 | 0.0629231637455184 | 0.025688274029685612 |
| `walking_speed_max_mm_s` | 6 | 33.52460532987854 | 6.2849027727605105 | 2.565800812711071 |
| `walking_speed_mm_s` | 6 | 3.0548045197540716 | 0.2353069658831898 | 0.09606366655605078 |

## Metric contract

- `mean_planar_speed_mm_s`: `MISSING`.
- `distance_traveled_mm`: `MISSING`.
- `displacement_mm`: `MISSING`.

Các tên metric quan sát được được giữ nguyên theo artifact runtime. Không tự đổi `walking_speed_mm_s` thành `mean_planar_speed_mm_s` và không đổi `total_distance_mm` thành `distance_traveled_mm`.

## Quality control

- Kiểm tra numeric arrays: không NaN/Inf nếu trạng thái seed là PASS.
- QC trực tiếp từ rollout: timestamp, timestep, thorax displacement, contact, joint trajectory, actuator trajectory, observation state và quaternion.
- Mỗi seed có thư mục rollout riêng và log riêng.
- Log tổng hợp: `experiments/gate_11_healthy_baseline/logs/run.log`.

## External artifact provenance

- Brain source status: `READY`.
- Checksum chi tiết nằm trong `manifests/external_input_audit.json` và `manifests/healthy_baseline_manifest.json`.

## Giới hạn và bước tiếp theo

Nếu metric contract còn `INCOMPLETE`, chưa được dùng baseline này để calibration cho đến khi metric simulation tương thích được xuất trực tiếp và được review. Kết quả này không phải biological validation và không phải Parkinson result.

## Ranh giới khoa học

Đây là computational locomotion baseline. Nó không phải biological Parkinson model validation, clinical prediction, diagnosis, drug efficacy validation hoặc thay thế thí nghiệm wet-lab.
