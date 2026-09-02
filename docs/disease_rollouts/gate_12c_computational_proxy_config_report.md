# Gate 12C — Computational Proxy Disease Configs

## Mục tiêu

Gate 12C mở khóa disease rollout ở mức computational proxy cho `alpha_synuclein` và `pink1`.

## Trạng thái

- `alpha_synuclein`: `RUN_READY_FOR_GATE_12D`
- `pink1`: `RUN_READY_FOR_GATE_12D`
- `parkin`: `BLOCKED`
- `dj1`: `BLOCKED`
- `lrrk2`: `BLOCKED`

## Scope

`alpha_synuclein` và `pink1` là organism-level computational proxy. Không có root-ID mapping và không có gene-specific neuron mapping. Đây không phải biological validation.

## Burden curve

Burden curve là dimensionless computational proxy level:

- `0.0`: `no_burden`
- `0.25`: `mild_proxy_burden`
- `0.5`: `moderate_proxy_burden`
- `0.75`: `high_proxy_burden`
- `1.0`: `full_proxy_burden`

Các mức này chỉ là các mức cấu hình để khảo sát độ nhạy locomotion. Chúng chưa được hiệu chuẩn theo dữ liệu literature trong Gate 12C.

## Runtime

Dùng runtime giống Gate 11:

- 5000 steps
- timestep `0.0001 s`
- duration khoảng `0.5 s`
- seeds `0–5`
- giữ nguyên physics, timestep, duration và seed policy

## Không thực hiện trong Gate 12C

- Không simulation.
- Không calibration.
- Không holdout validation.
- Không tune bằng Chen.
- Không tune bằng Pozo.

## Điều kiện bị khóa

`parkin`, `dj1` và `lrrk2` chưa có target neuron/edge, burden curve, full burden, mapping provenance và checkpoint compatibility review. Vì vậy không được chuyển sang trạng thái run-ready.

## Final status

`READY_FOR_GATE_12D_PROXY_ROLLOUTS`

## Boundary

Kết quả này chỉ cho phép chuẩn bị computational proxy rollout. Không được gọi đây là mô hình Parkinson sinh học đã được validate, không phải chẩn đoán, dự đoán lâm sàng, đánh giá thuốc hoặc bằng chứng thay thế thí nghiệm wet-lab.
