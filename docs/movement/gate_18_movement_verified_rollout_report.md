# Gate 18: Kiểm chứng rollout có chuyển động

**Ngày chạy:** 2026-09-03
**Trạng thái:** `MOVEMENT_VERIFIED_ARTIFACT_PARTIAL`
**Phạm vi:** kiểm tra runtime vận động tính toán bằng FlyGym/MuJoCo và brain-body source thật.

## 1. Mục tiêu và lệnh chạy

Gate này kiểm tra một Healthy rollout thực tế trước khi chạy disease condition. Không calibration, không tuning và không chạy Disease Layer. Lệnh đã dùng:

```powershell
& 'E:\Drosophila_Parkinson\drosophila-pd-flygym\.venv\Scripts\python.exe' `
  scripts/run_neural_experiment.py `
  --brain-root 'E:\Drosophila_Parkinson\external\fly-brain-audit' `
  --platform-root 'E:\Drosophila_Parkinson\drosophila-pd-flygym' `
  --seed 0 --steps 100000 --device cuda `
  --output 'experiments/gate_18_movement_verified_rollout/results/healthy_seed_000' `
  --video --video-fps 30 --video-width 960 --video-height 540 `
  --video-playback-speed 1.0 --stimulus p9 --cpg-frequency-hz 12.0
```

100.000 bước với timestep `0.0001 s` tương ứng khoảng 10 giây thời gian vật lý. BrainEngine ghi nhận 138.639 neuron và 15.091.983 synapse trên CUDA.

## 2. Kết quả chuyển động

| Kiểm tra | Kết quả | Ghi chú |
|---|---:|---|
| Simulation hoàn tất | PASS | 100.000 bước, 100.001 frame |
| Thorax displacement | PASS | 20.3336 mm trên mặt phẳng XY |
| Tổng quãng đường | PASS | 27.3838 mm |
| Walking speed trung bình | PASS | 2.73835 mm/s |
| Timestamp | PASS | tăng đều, `dt` xấp xỉ 0.0001 s |
| NaN/Inf | PASS | không phát hiện trong các mảng rollout đã kiểm tra |
| Quaternion | PASS | giá trị hữu hạn; thứ tự được ghi là `wxyz` |
| Joint trajectory | PASS | thay đổi RMS 0.34694 rad |
| Action/actuator | PASS | hữu hạn và thay đổi, max change 2.58782 |
| Ground contact | PASS | contact sensor hoạt động ở mọi frame |
| Observation array | NOT VERIFIED | file còn giữ không chứa observation array |
| Symmetry index | UNAVAILABLE | pipeline không cung cấp cặp đối xứng cho rollout này |

Các số trên được đọc từ `rollout.npz` và `metrics/metrics.json`; không phải dữ liệu giả và không phải số đo từ ruồi thật.

## 3. Video và kiểm tra trực quan

MP4 đã được tạo tại:

```text
experiments/gate_18_movement_verified_rollout/results/healthy_seed_000/flygym_rollout.mp4
```

Video H.264 có 301 frame, 30 FPS và thời lượng khoảng 10.03 giây. FlyGym mesh thật và vật liệu màu được render. Tuy nhiên QA trực quan là **PARTIAL**: camera hiện cố định, fly di chuyển ra khỏi khung hình khoảng sau 3–4 giây. Vì vậy video chứng minh renderer đã tạo frame thật, nhưng chưa đạt chất lượng demo theo dõi liên tục toàn bộ 10 giây.

## 4. Artifact và provenance

Artifact summary nhỏ, có thể review trong Git, nằm tại:

```text
experiments/gate_18_movement_verified_rollout/results/movement_verified_summary.csv
experiments/gate_18_movement_verified_rollout/results/movement_verified_summary.json
experiments/gate_18_movement_verified_rollout/manifests/movement_verified_rollout_manifest.json
```

Rollout raw `rollout.npz`, `viewer_pose.json`, metrics JSON và MP4 đang tồn tại cục bộ. Do ổ E: hết dung lượng ở bước đóng gói viewer, `rollout.json` và `rollout.csv` đã được xóa để khôi phục dung lượng. Viewer bundle không được tạo. Các file nhị phân lớn không được commit vào Git.

External FlyGym worktree đang dirty tại thời điểm chạy. Vì vậy kết quả này là runtime verification tại máy hiện tại; cần clean rerun với đủ dung lượng và manifest đầy đủ trước khi dùng làm artifact publication-grade.

## 5. Kết luận phạm vi

Gate 18 xác nhận được một **computational locomotion rollout** có chuyển động, contact, joint/action thay đổi và metrics hợp lệ ở mức artifact đã lưu. Kết quả này **không phải** biological Parkinson validation, không phải chẩn đoán lâm sàng, không phải dự đoán lâm sàng và không phải đánh giá drug response.

Chưa được phép kết luận disease condition từ gate này. Trước khi chạy disease multi-seed cần:

1. Rerun Healthy với external worktree sạch và output root còn đủ dung lượng.
2. Bổ sung observation recording hoặc ghi rõ contract không yêu cầu observation trong runner.
3. Sửa camera video để fly luôn nằm trong khung hình, rồi QA lại toàn bộ video.
4. Chỉ sau khi Healthy artifact đạt gate đầy đủ mới chạy disease condition nhiều seed.
