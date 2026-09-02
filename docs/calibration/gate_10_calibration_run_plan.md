# Gate 10: Calibration Run Plan

## Mục đích

Gate 10 chuyển trạng thái `READY_FOR_CALIBRATION` thành một kế hoạch chạy có thể
kiểm tra được. Đây là kế hoạch thực thi, chưa phải kết quả calibration. Không
được chạy simulation, tối ưu tham số hoặc holdout validation chỉ bằng cách đọc
tài liệu này.

## Trạng thái đầu vào

- Gate 09B đã đạt `READY_FOR_CALIBRATION`.
- Có 2 target approved đủ metadata và provenance.
- Target calibration: Chen 2014 adult horizontal walking speed.
- Target holdout: Pozo 2022 Pink1B9 distance.
- Audit hiện tại: 1 target calibration và 1 target holdout.
- Pokrzywa vẫn pending và không được dùng trong run này.

## Quy tắc sử dụng target

Chen 2014 là target duy nhất để calibration. Metric là
`mean_planar_speed_mm_s`, giá trị `4.875 mm/s`, uncertainty được giữ nguyên
là `CI95 = 0.525 mm/s`, với `20 fly`.

Pozo 2022 được giữ kín cho holdout sau khi calibration hoàn tất. Metric là
`distance_traveled_mm`, giá trị `62.091 mm`, spread `61.288` được giữ đúng dạng
paper-reported IQR/min-max, với `21 fly`. Không đổi distance thành speed và
không dùng Pozo để tuning.

## Metric contract

### Bắt buộc cho calibration

- `mean_planar_speed_mm_s`, đơn vị `mm/s`.
- Giá trị phải hữu hạn và có provenance của rollout.

### Bắt buộc cho holdout

- `distance_traveled_mm`, đơn vị `mm`.
- Metric phải được artifact simulation xuất trực tiếp hoặc có quy tắc đo đã
  được phê duyệt trước khi chạy.

### Kiểm tra chất lượng baseline

- Vị trí và vận tốc hữu hạn.
- Có phát hiện locomotion.
- Có phát hiện contact.
- Timestamp tăng đơn điệu.
- Không suy ra pause, symmetry, action hoặc orientation stability nếu artifact
  không ghi nhận hoặc repository chưa định nghĩa công thức.

## Quy trình chạy dự kiến

1. Khóa commit, Python, package versions, config, checkpoint và seed policy.
2. Kiểm tra license, checksum và manifest của các artifact bên ngoài.
3. Chạy healthy baseline theo cùng physics, timestep, duration và renderer dự
   kiến cho disease conditions.
4. Kiểm tra artifact baseline theo metric contract trước khi chạy disease.
5. Chạy các condition disease đã có mapping và checkpoint hợp lệ với cùng seed
   policy.
6. Chạy calibration chỉ trên Chen, ghi lại parameter, loss, seed và artifact.
7. Khóa tham số sau calibration; không thay đổi chúng khi đánh giá holdout.
8. Đánh giá Pozo như holdout distance độc lập.
9. Xuất bảng metrics theo seed, uncertainty, manifest, checksum và báo cáo.

Các bước trên chỉ được thực hiện sau khi run plan được research lead review.

## Chính sách runtime và seed

- Dùng 6 seed: `0, 1, 2, 3, 4, 5` cho healthy và disease conditions.
- Calibration ghi nhận các random seed này; optimization seed là `0`.
- Holdout dùng cùng danh sách seed nhưng không được dùng để chọn tham số.
- Mỗi run phải ghi Python version, package versions, git commit, config hash,
  checkpoint hash và artifact hashes.
- Không thay đổi physics, timestep, duration hoặc seed policy giữa baseline và
  condition nếu không có lý do được ghi trong report.

## Artifact bên ngoài

Trước khi execution cần kiểm tra và ghi checksum/provenance cho:

- connectome edge list;
- FlyWire annotation table;
- plastic weights;
- brain-body source và checkpoint;
- bridge scales;
- experimental locomotion database.

Artifact lớn không đưa trực tiếp vào Git. Dùng external storage hoặc release
asset, kèm license note, SHA-256 và manifest.

## Điều kiện dừng

Dừng trước calibration nếu thiếu một trong các điều kiện sau:

- runtime hoặc checkpoint không hợp lệ;
- metric bắt buộc không có, sai đơn vị, NaN hoặc Inf;
- baseline không có locomotion/contact hợp lệ;
- artifact thiếu manifest/checksum;
- target bị thay đổi hoặc thiếu provenance;
- phát hiện tuning dùng holdout.

## Ranh giới khoa học

Gate 10 chỉ mô tả kế hoạch calibration cho một computational locomotion model.
Nó không phải biological Parkinson validation, clinical prediction, diagnosis,
drug efficacy validation hoặc sự thay thế cho thí nghiệm trên ruồi thật.

## File cấu hình

- `experiments/gate_10_calibration_plan/calibration_run_plan.yaml`
- `experiments/gate_10_calibration_plan/seed_policy.yaml`
- `experiments/gate_10_calibration_plan/metric_contract.yaml`
- `experiments/gate_10_calibration_plan/artifact_requirements.yaml`
