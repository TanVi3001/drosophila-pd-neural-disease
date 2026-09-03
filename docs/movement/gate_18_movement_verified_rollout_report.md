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
  --output 'C:\\Temp\\drosophila_pd_gate18_tracking\\healthy_seed_000' `
  --video --video-fps 60 --video-width 960 --video-height 540 `
  --video-playback-speed 1.0 --video-camera-mode tracking `
  --stimulus p9 --cpg-frequency-hz 12.0
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
experiments/gate_18_movement_verified_rollout/results/healthy_seed_000_tracking/flygym_rollout.mp4
```

Video H.264 có 599 frame, 60 FPS và thời lượng khoảng 9.98 giây. Camera dùng chế độ tracking theo body `nmf/c_thorax`, nên fly còn trong khung hình ở đầu, giữa và cuối video. QA trực quan của camera là **PASS**. Tần số video 60 FPS cũng giúp quan sát rõ hơn các thay đổi chân giữa các frame; CPG/physics không bị thay đổi bởi camera.

## 4. Artifact và provenance

Artifact summary nhỏ, có thể review trong Git, nằm tại:

```text
experiments/gate_18_movement_verified_rollout/results/movement_verified_summary.csv
experiments/gate_18_movement_verified_rollout/results/movement_verified_summary.json
experiments/gate_18_movement_verified_rollout/manifests/movement_verified_rollout_manifest.json
```

Rerun tracking lưu tại `C:\Temp\drosophila_pd_gate18_tracking\healthy_seed_000`; MP4 đã được sao chép vào thư mục `healthy_seed_000_tracking` trong repo để tiện demo. Rollout JSON/CSV, NPZ và metrics JSON lớn vẫn giữ ở ổ C: và không được commit vào Git. Lần tracking này bị dừng ở bước export `viewer_pose` vì validator đọc tài liệu hơn 2 GB gây tốn RAM; đây không ảnh hưởng các frame MP4 và metrics đã ghi trước đó.

External FlyGym worktree đang dirty tại thời điểm chạy. Vì vậy kết quả này là runtime verification tại máy hiện tại; cần clean rerun với đủ dung lượng và manifest đầy đủ trước khi dùng làm artifact publication-grade.

## 5. Kết luận phạm vi

Gate 18 xác nhận được một **computational locomotion rollout** có chuyển động, contact, joint/action thay đổi và metrics hợp lệ ở mức artifact đã lưu. Kết quả này **không phải** biological Parkinson validation, không phải chẩn đoán lâm sàng, không phải dự đoán lâm sàng và không phải đánh giá drug response.

Chưa được phép kết luận disease condition từ gate này. Trước khi chạy disease multi-seed cần:

1. Rerun Healthy với external worktree sạch và output root còn đủ dung lượng.
2. Bổ sung observation recording hoặc ghi rõ contract không yêu cầu observation trong runner.
3. Ghi thêm observation array nếu quality gate nghiên cứu yêu cầu kiểm tra observation độc lập.
4. Chạy lại với external worktree sạch và đủ bộ viewer artifact trước khi dùng làm artifact publication-grade.
5. Chỉ sau khi Healthy artifact đạt gate đầy đủ mới chạy disease condition nhiều seed.
