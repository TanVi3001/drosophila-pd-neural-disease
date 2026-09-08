# Gate24.1 - Audit kiến trúc perturbation

## Kết luận

Operator trước Gate24 tác động ở cấp action. Nó nhận `LocomotionAction`, thay
đổi trực tiếp `joint_angles` theo mức burden rồi mới chuyển action sang hook
FlyGym. Operator đó không đọc root-ID, không đọc connectome edge và không tác
động vào trạng thái neural trước khi sinh motor output.

## Kiến trúc hiện tại trước Gate24.1

```text
brain
  -> action generation
  -> ACTION-LEVEL PROXY
  -> FlyGym
```

Đây là negative control hợp lệ để kiểm tra pipeline action hook, nhưng không
được dùng làm primary Parkin prediction.

## Kiến trúc Gate24.1

```text
healthy neural checkpoint
  -> PARKIN DRIVER-DEFINED NEURAL TRANSFORM
  -> perturbed neural representation
  -> brain-to-body action generation
  -> public brain-body bridge
  -> FlyGym
```

Transform mới làm việc trên vector synaptic weights trước khi brain runner
được khởi tạo. Target được resolve bằng 330 root-ID đã review qua thứ tự
explicit trong FlyWire completeness/connectome; root-ID không bị dùng trực
tiếp như tensor index.

## Quy tắc tính toán

Với edge `e`, `T` là tập target root-ID và `p` là `neural_perturbation_strength`
không có đơn vị:

```text
w_prime[e] = w[e] * (1 - p), nếu presynaptic_root[e] thuộc T
w_prime[e] = w[e],           nếu không thuộc T
```

`p = 0` phải trả về bản sao đúng của healthy neural representation. Checkpoint
healthy không bị ghi đè; checkpoint Parkin là artifact mới có SHA256 riêng.

## Ranh giới khoa học

Được phép gọi đây là **Parkin-specific intervention represented by a reviewed
driver-defined neural perturbation**. Không được gọi `p` là phần trăm
Parkin-knockdown, phần trăm mất dopamine, cơ chế synapse sinh học, biological
Parkinson validation hoặc gene-expression validation.
