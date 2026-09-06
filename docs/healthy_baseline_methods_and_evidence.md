# Healthy baseline: Methods, tái lập và bằng chứng hiện tại

## Câu hỏi nghiên cứu

Trong cùng một cấu hình vật lý và neural source, hệ thống có tạo được locomotion
Healthy ổn định qua nhiều seed, có artifact truy vết được và đủ chất lượng để làm
chuẩn kỹ thuật cho các disease condition trong tương lai hay không?

## Phạm vi

Đây là thí nghiệm locomotion tính toán. Healthy baseline không phải xác nhận sinh
học trên ruồi thật. Nó không chứng minh hoặc phủ định Parkinson, không có giá trị
chẩn đoán, dự đoán lâm sàng hoặc đánh giá thuốc.

## Protocol đã khóa

- Runtime: Python 3.12.10, FlyGym 2.1.0, MuJoCo 3.9.0, Torch 2.5.1+cu121.
- Neural source: commit `27cec28d5d202eb004683fb4c1a1033eec8deea0`.
- Checkpoint SHA256: `d51dcd247354fd92b8f5b2703f06fa9e85cf1eb485cd4f1eb5e15c20e9293e7d`.
- Neural graph: 138.639 neuron, 15.091.983 synapse, 18/18 descending neuron được ánh xạ.
- Condition: `healthy`; Disease Layer tắt; không perturbation; không calibration.
- Seeds: 0, 1, 2, 3, 4.
- Mỗi rollout: 5.000 bước, 5.001 frame, timestep 0,0001 s, thời gian mô phỏng 0,5 s.
- Stimulus `p9`, CPG 12 Hz, neural execution trên CUDA.
- Seed 0 được render thành video đại diện 60 fps, 960x540, playback speed 0,04.

Toàn bộ tham số máy đọc được nằm trong
`configs/healthy_baseline_reproducible.yaml`. Hash của protocol, source manifest,
rollout và trạng thái Git được lưu trong `provenance_lock.json` của kết quả.

## Kiểm soát chất lượng

Mỗi rollout được kiểm tra độc lập:

1. Status simulation và seed đúng protocol.
2. Đủ 5.001 frame; timestamp tăng nghiêm ngặt và có bước 0,0001 s.
3. Tất cả array số học không có NaN hoặc Inf.
4. Thorax displacement, walking speed và path length lớn hơn 0.
5. Có contact chân với mặt đất trên ít nhất 50% frame.
6. Joint position thay đổi và joint velocity RMS lớn hơn 0.
7. Quaternion hữu hạn, norm gần 1.
8. Observation state và actuator state được export, hữu hạn và đúng số frame.
9. Manifest, kích thước file và SHA256 khớp artifact.
10. Hash `rollout.npz` không trùng giữa các seed.

Runner hiện chưa export raw action command. Vì vậy báo cáo ghi `NOT_EXPORTED/WARN`
cho trường này và chỉ xác nhận actuator state. Không được diễn giải cảnh báo này
thành action command đã PASS.

## Phân tích thống kê

Đơn vị phân tích là một rollout seed. Báo cáo mean, sample SD, SE và CI 95% bằng
bootstrap percentile 10.000 lần với seed phân tích 0. Do chỉ có năm seed, các CI
được dùng để mô tả biến thiên kỹ thuật, không phải khoảng tin cậy sinh học.

## Artifact dùng cho manuscript

- `per_seed_metrics.csv`: metric của từng seed.
- `summary_statistics.csv`: mean, SD, SE và CI 95%.
- `quality_checks.csv`: toàn bộ PASS/WARN/FAIL có lý do.
- `key_metrics_by_seed.png`: speed, displacement, path length và efficiency.
- `quality_control_by_seed.png`: contact, joint velocity và thorax height.
- `trajectories_by_seed.png`: quỹ đạo thorax trong mặt phẳng.
- `flygym_rollout.mp4` của seed 0: video minh họa có provenance.

Video khoảng 12 giây chỉ là phát chậm 0,5 giây simulation. Không được mô tả video
đó như một simulation 12 giây.

## Kết quả baseline hiện tại

Năm trên năm seed hoàn tất. Audit ghi nhận 81 kiểm tra `PASS`, không có `FAIL`,
và 5 `WARN` do raw action command chưa được export. Các thống kê dưới đây dùng
rollout thật vừa chạy:

| Metric | Mean | SD | SE | Bootstrap CI 95% |
|---|---:|---:|---:|---:|
| Walking speed (mm/s) | 3,05149 | 0,262925 | 0,117583 | 2,84231 - 3,26067 |
| Thorax planar displacement (mm) | 0,849975 | 0,049747 | 0,022248 | 0,812204 - 0,888016 |
| Planar path length (mm) | 1,52605 | 0,131489 | 0,058803 | 1,42144 - 1,63066 |
| Trajectory efficiency | 0,559851 | 0,052786 | 0,023607 | 0,517962 - 0,606024 |
| Foot-contact frame fraction | 0,998680 | 0,002431 | 0,001087 | 0,996441 - 1,000000 |

Các số này mô tả baseline tính toán trong protocol 0,5 giây. Không so sánh trực
tiếp với literature nếu assay, statistic và unit of analysis chưa tương thích.

## Figures và tables đề xuất

| Thành phần | Nội dung | Trạng thái |
|---|---|---|
| Figure baseline A | Quỹ đạo của năm seed | Được sinh từ rollout thật |
| Figure baseline B | Metric theo seed và mean | Được sinh từ rollout thật |
| Figure QC | Contact, joint velocity, thorax height | Được sinh từ rollout thật |
| Table baseline | Per-seed metrics | Được sinh từ rollout thật |
| Table reproducibility | Runtime, source, config, seed, hash | Được sinh từ provenance |
| Disease comparison | Healthy so với condition | Chưa tạo trong bước này |
| Literature concordance | Simulation so với target được duyệt | Chờ target hợp lệ |

## Contribution hiện tại

Pipeline chứng minh khả năng chạy brain-body locomotion Healthy thật qua năm seed,
kiểm tra chất lượng artifact và khóa provenance. Đây là nền kỹ thuật để thiết kế
disease sweep có kiểm soát. Contribution hiện tại không bao gồm biological
Parkinson validation.

## Ghi chú về Artifact Analyzer dùng chung

Artifact Analyzer của platform đã được chạy riêng cho cả năm seed bằng đường dẫn
tuyệt đối và xác nhận runtime `PASS`. Trạng thái tổng của nó là
`WAITING_TARGET_DATA`, phù hợp vì baseline không có calibration target. Tuy nhiên,
analyzer này đang nhận `viewer_bundle` làm dataset chính đối với layout brain-body,
nên báo thiếu metric dù metric thật nằm trong `metrics/metrics.json`. Vì vậy kiểm
soát chất lượng baseline sử dụng `analyze_healthy_baseline.py`, đọc trực tiếp
`rollout.npz`, metric và manifest. Đây là giới hạn tương thích cần công bố, không
phải lý do để sửa hoặc ép Artifact Analyzer trả `PASS`.

## Điều kiện chuyển sang disease comparison

Chỉ chuyển bước khi disease condition có mapping neural/proxy có provenance, target
literature tương thích đã được reviewer phê duyệt, allocation calibration/holdout
độc lập và protocol disease giữ nguyên physics, timestep, duration cùng seed policy.
