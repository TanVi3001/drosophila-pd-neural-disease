# Gate 10: Calibration Readiness Checklist

Tài liệu này là checklist trước khi chạy. Dấu chọn phải do người thực hiện
điền sau khi kiểm tra artifact thật; không đánh dấu dựa trên kế hoạch.

## Trạng thái target

- [ ] Audit trả `READY_FOR_CALIBRATION` ngay trước execution.
- [ ] Chen 2014 là target calibration duy nhất.
- [ ] Pozo 2022 được giữ độc lập làm holdout.
- [ ] Pokrzywa vẫn không được dùng khi chưa đủ independent-vial count.
- [ ] Không có thay đổi value, uncertainty, reviewer hoặc provenance.

## Runtime và artifact

- [ ] Python và package versions đã ghi.
- [ ] Git commit và config hash đã ghi.
- [ ] Checkpoint, connectome, annotation, bridge scales và plastic weights có
      provenance, license note và SHA-256.
- [ ] Runtime smoke test pass.
- [ ] Manifest không thiếu file và không có artifact trùng.

## Healthy baseline

- [ ] Healthy baseline dùng đúng physics, timestep, duration và renderer.
- [ ] Đủ seed `0, 1, 2, 3, 4, 5`.
- [ ] Vị trí và vận tốc hữu hạn.
- [ ] Timestamp tăng đơn điệu.
- [ ] Locomotion được phát hiện.
- [ ] Contact được phát hiện.
- [ ] `mean_planar_speed_mm_s` có đơn vị `mm/s`.

## Disease run

- [ ] Condition có mapping và checkpoint hợp lệ.
- [ ] Seed policy giống healthy baseline.
- [ ] Artifact theo từng seed đầy đủ.
- [ ] Không có disease run bị thiếu frame, NaN hoặc Inf.
- [ ] Chưa dùng holdout để chọn tham số.

## Calibration

- [ ] Chỉ tối ưu theo Chen 2014.
- [ ] `CI95` vẫn được lưu là `CI95`, không đổi thành SE.
- [ ] Không chuyển median thành mean.
- [ ] Không chuyển distance thành speed.
- [ ] Ghi parameter, loss, seed, config và checksum.
- [ ] Khóa tham số sau calibration trước holdout.

## Holdout validation

- [ ] Pozo chỉ được đánh giá sau khi calibration đã khóa.
- [ ] Chỉ dùng `distance_traveled_mm`.
- [ ] Giữ nguyên paper-reported spread.
- [ ] Không dùng kết quả holdout để quay lại tuning.

## Quyết định execution

- [ ] Research lead review run plan.
- [ ] Mọi blocker đã được giải quyết và ghi lại.
- [ ] Người thực hiện xác nhận đây là computational locomotion experiment.

## Ranh giới khoa học

Checklist này không xác nhận biological Parkinson validation, chẩn đoán lâm
sàng, hiệu quả thuốc hoặc thay thế thí nghiệm wet-lab.
