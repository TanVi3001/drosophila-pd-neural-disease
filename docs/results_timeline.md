# Results Timeline

| Gate | Commit/Status | Mục đích | Kết quả chính | Hệ quả đối với claim |
| --- | --- | --- | --- | --- |
| Gate 12G | Integrated proxy rollout; `60/60 PASS` | Chạy proxy burden ở scope organism-level | Rollout computational đạt QC | Tạo nền tảng cho calibration, chưa là biological validation |
| Gate 13A | `READY_FOR_GATE_13B_CHEN_RATIO_CALIBRATION` | Chuẩn bị Chen-only objective | Objective ratio khả thi | Chưa chạy calibration |
| Gate 13B | `CHEN_RATIO_CALIBRATION_PASS` | Chọn burden theo Chen ratio | Chọn burden `0.5` | Candidate gần nhất trên discrete grid, không phải perfect fit |
| Gate 13C | `CHEN_CALIBRATED_CONFIRMATION_PASS` | Rerun bằng seed độc lập | Confirmation ratio `0.6142` | Xác nhận computational của parameter đã khóa |
| Gate 14A | `POZO_HOLDOUT_PROTOCOL_LOCKED` | Khóa protocol holdout | Pozo giữ vai trò holdout độc lập | Không dùng Pozo để calibration |
| Gate 14B | `POZO_HOLDOUT_RUNTIME_PASS` | Chạy Pozo holdout | `12/12 PASS`; directionality PASS; quantitative mismatch | Chỉ báo cáo directional concordance |
| Gate 14C | `HOLDOUT_ADJUDICATION_COMPLETE` | Adjudicate diễn giải và khóa claim | Simulated ratio `0.9470` vs target `0.1920` | Claim lock: quantitative mismatch vẫn lớn |

## Tổng kết

Timeline cho thấy pipeline đã đi qua calibration computational, confirmation,
holdout runtime và adjudication. Nó chưa chuyển thành biological Parkinson
validation, gene-specific validation, clinical validation hoặc drug validation.
