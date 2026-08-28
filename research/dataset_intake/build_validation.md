# Kết quả build từ nguồn đã xác minh

Ngày kiểm tra: 28-08-2026.

## Input

- FlyWire v783 connectivity: 15.091.983 cạnh, SHA256
  `efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347`.
- Checkpoint gốc: 15.091.983 trọng số, SHA256
  `d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691`.
- Annotation: 342 root ID PAM/PPL/PPM trong condition exploratory hiện tại.
- Config: `configs/conditions/dopamine_deficiency.exploratory.yaml`, tuổi tính
  toán 5 ngày.

## Kết quả

- Trạng thái: `CHECKPOINT_READY`.
- Trọng số thay đổi: 69.735.
- Trọng số được giữ nguyên: 15.022.248.
- Tỷ lệ thay đổi: khoảng 0,4621%.
- Checkpoint đầu ra không chứa NaN hoặc Inf.
- SHA256 đầu ra local:
  `febcb73ef725a527176642f0765f44632349002d70c4cfa2de0be10e48ad1222`.

Checkpoint sinh ra nằm trong `results/dataset_source_integration/` và bị Git
ignore. Hash đầu ra chỉ mô tả lần build này; manifest cạnh checkpoint mới là
nguồn provenance cho từng lần chạy.

## Bug đã sửa

Trước khi sửa, `prepare_neural_checkpoint.py` thay toàn bộ checkpoint bằng cột
trọng số connectome rồi mới perturb, khiến 100% trọng số thay đổi. Script hiện
perturb trực tiếp trên checkpoint gốc và giữ nguyên mọi cạnh không liên quan.
Regression test kiểm tra hành vi này bằng một connectome nhỏ có kiểm soát.

## Giới hạn

Đây là build kỹ thuật của một perturbation dopamine exploratory. Nó chưa dùng
target literature đã phê duyệt, chưa chạy calibration/holdout và chưa phải mô
hình Parkinson sinh học.
