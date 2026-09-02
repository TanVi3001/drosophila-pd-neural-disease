# Gate 12F-B - Tích hợp operator vào action hook

## Mục tiêu

Gate 12F-B nối `proxy_burden_operator` vào action hook thật đã được phát hiện ở
Gate 12F-A. Phần nối được đóng gói thành adapter trong repository này và patch
cho runner FlyGym external.

## Hook thật

- Runtime external: `E:/Drosophila_Parkinson/drosophila-pd-flygym/scripts/run_brain_body_rollout.py`
- Producer: `HybridTurningController.step()`
- Action: `LocomotionAction`
- `joint_angles`: NumPy shape `(42,)`
- `adhesion_onoff`: Boolean shape `(6,)`
- Điểm áp dụng: sau khi tạo action và trước `apply_locomotion_action(...)`
- Physics step tiếp theo: `simulation.step()`

## Adapter

`src/drosophila_pd_neural/action_hook_adapter.py` thực hiện:

- đọc operator settings từ config Gate 12E;
- copy `joint_angles` trước khi biến đổi;
- burden `0.0` giữ nguyên giá trị nhưng trả bản sao;
- burden dương áp dụng attenuation theo config;
- giữ nguyên `adhesion_onoff` và không sửa mảng đầu vào;
- giữ shape `(42,)`, giá trị hữu hạn và seed deterministic;
- hỗ trợ `LocomotionAction`, protocol object và mapping fallback.

Operator chỉ là phép biến đổi action-level đã cấu hình. Nó không phải mapping
gene-specific và không phải cơ chế sinh học của Parkinson.

## External patch

Patch: `experiments/gate_12f_b_action_hook_integration/patches/flygym_proxy_burden_hook.patch`.

Patch thêm cờ bật tường minh cho operator, đường dẫn config/source và metadata
hash. Khi không bật cờ, healthy runner giữ nguyên hành vi. External worktree
đã có thay đổi local từ trước; patch Gate 12F-B được áp dụng tại file runner
nhưng không commit vào repository FlyGym.

## Probe

Probe `scripts/smoke_test_action_hook_integration.py` chỉ tạo action vector
42 chiều và kiểm tra identity, attenuation, shape, finite, không mutate,
adhesion preservation và deterministic seed. Probe không khởi động FlyGym,
không chạy brain, không tạo disease metrics.

## Trạng thái

`CONNECTED_TO_EXTERNAL_RUNTIME`

Đây là trạng thái wiring đã được nối vào file runner external và probe adapter
đã pass. Chưa có full disease rollout; Gate 12G mới là bước chạy rollout
proxy thật qua hook này.

## Không thực hiện

- Không full disease rollout.
- Không calibration.
- Không holdout validation.
- Không tuning theo Chen hoặc Pozo.
- Không gene-specific mapping.
- Không biological Parkinson validation.

## Ranh giới khoa học

Đây chỉ là tích hợp computational action-level cho locomotion. Nó không phải
mô hình Parkinson sinh học, chẩn đoán lâm sàng, dự đoán lâm sàng hay xác nhận
hiệu quả thuốc.
