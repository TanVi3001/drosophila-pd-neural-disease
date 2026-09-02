# Gate 12E - Proxy Burden-to-Action Operator

## Mục tiêu

Gate 12E triển khai một operator tính toán để ánh xạ `burden_level` không thứ nguyên vào action đã được tạo bởi controller. Operator này được tạo nhằm chuẩn bị xử lý blocker từ Gate 12D:

`proxy_burden_to_action_operator_not_connected_to_current_brain_body_runner`

Gate này không chạy disease rollout lớn, không calibration và không holdout validation.

## Operator

- Kiểu: `amplitude_attenuation`.
- `burden_level` nằm trong `[0, 1]`.
- Công thức: `output = action * (1 - attenuation_strength * burden_level)`.
- Cấu hình mặc định: `attenuation_strength=0.5`, `noise_strength=0.0`.
- `burden_level=0` giữ nguyên giá trị action nhưng trả về bản sao.
- `burden_level=1` giảm biên độ theo strength đã cấu hình.
- Noise tùy chọn được tạo bằng seed để có thể lặp lại.
- Input không bị mutate; shape được giữ nguyên; output hữu hạn.
- Operator chỉ là perturbation ở cấp action cho computational locomotion, không phải cơ chế sinh học của gene.

Module được triển khai tại `src/drosophila_pd_neural/proxy_burden_operator.py` và được export từ package hiện có. Không tạo package nghiên cứu mới.

## Runner connection

Operator config được đặt tại `experiments/gate_12e_proxy_operator/configs/proxy_burden_action_operator.yaml`.

Runner Gate 12D hiện là bộ điều phối ở disease repository. Nó gọi runner neural qua subprocess nhưng không sở hữu vòng lặp tạo action, truyền action vào FlyGym và gọi `simulation.step()`. Vì vậy chưa có action hook thật để áp dụng operator vào rollout.

Kết quả trung thực:

- `connected_to_runner=false`.
- `operator_applied=false` trong các row chặn của Gate 12D.
- Runner vẫn chặn organism-level proxy thay vì ghi healthy rollout thành disease rollout.
- Hash config được ghi nếu một Gate 12D run config tham chiếu operator config.

Không coi việc import hoặc smoke test operator là đã nối được vào simulation.

## Scope

- Scope cho phép: `alpha_synuclein` và `pink1` ở mức `organism_level_proxy`.
- `parkin`, `dj1`, `lrrk2` vẫn bị chặn.
- Không có gene-specific neuron mapping.
- Không có root ID, checkpoint mapping hay action trajectory giả.
- Không dùng Chen hoặc Pozo để tune operator.

## Readiness

Smoke test operator: `PASS`.

Readiness của operator: `PROXY_OPERATOR_NOT_CONNECTED`.

Gate 12E chưa mở khóa Gate 12F. Chỉ sau khi action hook thật được nối và kiểm thử trên action/controller thật mới có thể đánh giá bước rollout tiếp theo. Gate đó vẫn phải bảo toàn boundary computational và không được gọi là biological Parkinson validation.

## Scientific boundary

Đây là một computational locomotion perturbation operator. Nó không phải biological Parkinson model, gene-specific biological mapping, clinical prediction, drug efficacy validation hoặc thay thế thí nghiệm wet-lab.

## Validation scope

- Smoke test nhỏ: kiểm tra identity, attenuation, shape, finite, deterministic seed và không mutate.
- Unit tests: kiểm tra operator config và các gate target neuron của runner.
- Không tạo video, `.npz` lớn, checkpoint hoặc disease metrics trong Gate 12E.
