# Gate 12F-A - Action Hook Discovery

## Mục tiêu

Tìm action hook thật để chuẩn bị nối `proxy_burden_operator` vào brain-body runner hiện tại. Gate này chỉ discovery và documentation; không chạy disease rollout, calibration hoặc holdout validation.

## Kết quả discovery

- **Action source:** `../drosophila-pd-flygym/scripts/run_brain_body_rollout.py`, trong `_run_simulation`.
- **Action producer:** `flygym_demo.complex_terrain.HybridTurningController.step` trả về `LocomotionAction`.
- **Action type:** `flygym_demo.complex_terrain.common.LocomotionAction`.
- **Action shape:** `joint_angles` là vector NumPy `(42,)`; `adhesion_onoff` là mảng boolean `(6,)`.
- **Action hook:** `layer.apply_to_action(controller_action, ActionPerturbationContext(...))` tại đoạn sau `controller.step(...)` và trước khi ghi action vào simulation.
- **Simulation write:** `apply_locomotion_action(simulation, fly.name, action)` gọi `sim.set_actuator_inputs(...)` và `sim.set_leg_adhesion_states(...)`.
- **Simulation step:** `simulation.step()` ngay sau lời gọi ghi action.
- **Action range:** chưa được khai báo hoặc kiểm tra bởi `LocomotionAction`. `actuator_forcerange=(-65, 65)` trong model là khoảng lực actuator, không phải khoảng joint-angle action, nên không dùng nó làm action range.
- **Action trajectory:** controller action object không được lưu trực tiếp trong recorder. Các mảng actuator trong `rollout.npz` là quan sát từ recorder, không được coi là bản sao trực tiếp của action command.

Discovery được thực hiện trên platform repository tại revision `3ceb8ce`; platform worktree đang có thay đổi local chưa commit. Gate 12F-B cần khóa revision platform và kiểm tra lại diff trước khi chạy integration.

## Vị trí tích hợp

Điểm tích hợp đúng cho operator là:

```text
controller_action = controller.step(...)
action = apply_proxy_burden_to_action(controller_action, ...)
apply_locomotion_action(simulation, fly.name, action)
simulation.step()
```

Trong code platform hiện tại, hook tương ứng đã tồn tại dưới dạng `layer.apply_to_action(...)`. Tuy nhiên, disease repository hiện chỉ điều phối bằng subprocess và chưa truyền operator Gate 12E vào platform runner. Vì vậy Gate 12E trước đó ghi `connected_to_runner=false` là chính xác; discovery này không tự biến thành integration.

## Integration contract

Gate 12F-B phải áp dụng module `src/drosophila_pd_neural/proxy_burden_operator.py` tại hook trước `apply_locomotion_action` và sau khi controller tạo action. Integration phải bảo đảm:

- burden bằng 0 là identity;
- output giữ nguyên shape;
- output hữu hạn, không NaN/Inf;
- cùng seed cho cùng kết quả;
- không mutate action đầu vào;
- không đổi adhesion nếu operator chỉ biến đổi joint angles;
- metadata ghi rõ operator config, burden và trạng thái áp dụng.

## Readiness

`DISCOVERED`

`READY_FOR_GATE_12F_B_INTEGRATION`

Điều này chỉ có nghĩa là đã xác định được hook thật trong platform runner. Nó không có nghĩa operator đã được nối, disease rollout đã chạy hoặc disease condition đã được xác nhận.

## Boundary

Gate 12F-A không tạo disease metrics, không chạy simulation, không calibration, không holdout validation và không claim gene-specific mapping. Đây là discovery của một hook trong computational locomotion pipeline, không phải biological Parkinson validation, chẩn đoán lâm sàng hoặc đánh giá thuốc.
