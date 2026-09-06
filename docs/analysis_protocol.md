# Analysis protocol cho Healthy baseline và disease comparison

## Phạm vi

Protocol này quy định cách đọc artifact rollout và so sánh các condition trong
project. Đây là phân tích locomotion tính toán, không phải mô hình Parkinson sinh
học, chẩn đoán, dự đoán lâm sàng hay đánh giá thuốc.

## Protocol thực nghiệm cố định

Mọi disease comparison phải giữ nguyên các yếu tố của Healthy baseline: cùng
FlyGym/MuJoCo, morphology, terrain, timestep, thời lượng, stimulus, CPG, renderer
khi có video, neural source, checkpoint và quy tắc seed. Healthy baseline hiện tại
dùng 5.000 bước, 5.001 frame, timestep 0,0001 s, thời gian mô phỏng 0,5 s,
stimulus `p9`, CPG 12 Hz và device CUDA.

Không được trộn rollout 1.000 bước với rollout 5.000 bước trong một bảng so sánh
nếu chưa chuẩn hóa cửa sổ quan sát. Video chậm chỉ là artifact trực quan; không
được dùng playback duration làm simulation duration.

## Đơn vị phân tích và ghép seed

- Đơn vị phân tích chính là một rollout hoàn chỉnh của một seed.
- Disease comparison nên ghép cùng seed giữa Healthy và disease condition khi
  cùng seed có mặt ở cả hai nhóm.
- Không xem từng frame là một replicate độc lập.
- Nếu seed thiếu, frame thiếu, timestamp lỗi, NaN/Inf hoặc artifact không khớp
  manifest thì loại rollout đó khỏi phân tích và ghi lý do.
- Không loại một seed chỉ vì metric không phù hợp kỳ vọng khoa học; mọi exclusion
  phải dựa trên QC định trước.

## Metric chính

| Metric | Cách dùng trong repository | Calibration | Validation/publication |
|---|---|---|---|
| `walking_speed_mm_s` | Scalar metric do runner ghi; không tự đổi median thành mean | Có điều kiện khi statistic, assay và target tương thích | Có |
| `thorax_planar_displacement_mm` | Norm của chênh lệch thorax XY frame cuối và đầu | Có thể dùng nếu target có cùng endpoint | Có |
| `planar_path_length_mm` | Tổng norm của từng bước thorax trên mặt phẳng XY | Có thể dùng với target distance/path tương thích | Có |
| `trajectory_efficiency` | `thorax_planar_displacement / planar_path_length` nếu path > 0 | Chưa có target literature được duyệt | Có |
| `heading_variance_rad2` | Scalar variance từ runner | Chỉ dùng khi có target cùng định nghĩa | Có |
| `joint_velocity_rms_rad_s` | `sqrt(mean(joint_velocity^2))` trên các frame và khớp | Chưa có target tương thích | Có |
| `body_orientation_variance_rad2` | Scalar variance hiện có của runner | Chỉ dùng khi định nghĩa target tương thích | Có |
| `foot_contact_frame_fraction` | Tỷ lệ frame có ít nhất một chân contact | Chưa có target | QC và publication |
| `com_planar_displacement_mm` | Norm của chênh lệch COM XY frame cuối và đầu | Chưa có target | Có |

`pause_fraction`, `symmetry_index` và endpoint tên `orientation_stability` hiện
chưa có định nghĩa/export đủ để đưa vào calibration. Raw action command cũng chưa
được export; actuator state chỉ là kiểm tra thay thế và không được gọi là action
array.

## Thống kê mô tả

Với mỗi condition và metric, báo cáo:

- số rollout hợp lệ `n`;
- mean;
- sample SD với `ddof=1`;
- SE = SD / sqrt(n);
- min, max và danh sách seed;
- CI 95% chỉ khi protocol đã chọn phương pháp và số seed đủ.

Healthy baseline hiện dùng bootstrap percentile 10.000 lần với seed phân tích 0
để mô tả kỹ thuật. Với n=5, CI không được diễn giải là uncertainty sinh học.

## Disease comparison

Chỉ so sánh disease với Healthy sau khi disease rollout đạt cùng QC. Với metric
được ghép seed, báo cáo delta:

```text
delta = disease_metric - healthy_metric
```

Có thể báo cáo relative change khi denominator và ý nghĩa metric cho phép, nhưng
phải giữ cả giá trị tuyệt đối. Không suy ra bệnh từ hướng của một metric đơn lẻ.

## Calibration và holdout

- Calibration chỉ dùng target có `review_status=approved`, uncertainty số học,
  sample size hợp lệ, reviewer/ngày review, allocation và assay transfer được
  phê duyệt.
- Holdout phải độc lập với calibration theo paper, cohort hoặc endpoint đã định
  trước.
- Không dùng target validation-only trong loss.
- Không chuyển climbing, DAM activity, activity time hoặc median sang mean speed
  nếu chưa có policy và endpoint tương ứng.

## Diễn giải kết quả

Kết quả được phép mô tả là computational locomotion phenotype/response dưới một
perturbation đã cấu hình. Chỉ sau calibration và holdout hợp lệ mới được nói về
concordance với literature, vẫn trong giới hạn computational. Không được gọi đó
là biological Parkinson validation.
