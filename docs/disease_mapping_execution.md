# Báo cáo mapping literature -> neuron -> simulation

## Phạm vi

Task này nối bằng chứng paper với neuron trong connectome để chuẩn bị chạy
computational locomotion experiment. Kết quả không phải biological Parkinson
validation, không phải chẩn đoán, clinical prediction hay drug-response model.

## Kết quả mapping

- dopamine_deficiency_exploratory đã có 342 FlyWire v783 root ID.
- 342/342 ID có trong 2025_Completeness_783.csv.
- 342/342 annotation có cell_type PAM/PPL/PPM và top_nt=dopamine.
- Condition dùng presynaptic_gain=0.15 như proxy exploratory cho mức giảm
  dopamine được báo cáo trong Riemensperger et al.; đây không phải synaptic
  weight đo trực tiếp.
- PINK1, Parkin, DJ-1, LRRK2 và alpha-synuclein có bằng chứng ở mức nhóm
  dopaminergic/driver trong literature, nhưng chưa có phép ghép paper-cell cụ
  thể sang FlyWire root ID được nhóm review.

## Tình trạng target

calibration_targets/targets.csv vẫn có hai dòng pending. Riemensperger
2011 còn thiếu sample size và variance số học của endpoint walking speed; phép
đổi từ open-arena assay sang FlyGym cũng chưa được phê duyệt. Pokrzywa 2017
ghi xu hướng theo nhiều mốc tuổi, không đủ để dùng như một target đơn mốc.
Do đó không chạy calibration loss và không gọi kết quả là holdout validation.

## Exploratory multi-seed

Campaign đã chạy bằng FlyGym thật và CUDA với 3 seed cho healthy và 3 seed cho
dopamine_deficiency_exploratory, mỗi run 1000 bước, 1001 frame.

| Condition | Seed | Walking speed (mm/s) | Total distance (mm) | Trạng thái |
| --- | ---: | ---: | ---: | --- |
| healthy | 0 | 4.807703 | 0.481251 | PASS |
| healthy | 1 | 4.081902 | 0.408598 | PASS |
| healthy | 2 | 5.378275 | 0.538365 | PASS |
| dopamine deficiency exploratory | 0 | 4.810552 | 0.481536 | PASS |
| dopamine deficiency exploratory | 1 | 3.974715 | 0.397869 | PASS |
| dopamine deficiency exploratory | 2 | 5.378622 | 0.538400 | PASS |

Delta trung bình theo ba seed của walking_speed_mm_s là khoảng -0.034663
mm/s, độ lệch chuẩn mẫu của delta khoảng 0.062820 mm/s. Đây chỉ là thống
kê mô tả của campaign computational ngắn; không dùng để khẳng định phenotype
sinh học và không thay thế target literature.

## Artifact

Output đầy đủ nằm tại results/dopamine_deficiency_exploratory/, gồm
campaign_status.json, campaign_summary.csv, baseline_comparison.csv,
rollout, metrics, viewer pose và viewer bundle cho từng run PASS. Checkpoint
perturbation được tạo từ connectome thật tại bước chuẩn bị.

## Bước bắt buộc tiếp theo

1. Research lead review từng target: genotype, tuổi, giới tính, assay, đơn vị,
   sample size, variance, provenance và khả năng quy đổi metric.
2. Chọn rõ target thuộc calibration hoặc holdout, không dùng đồng thời.
3. Với từng gene, xác định paper có driver/cell population nào và thu thập
   mapping neuron-ID hoặc xác nhận chỉ dùng class-level proxy.
4. Chỉ khi target được approved mới chạy calibration; hiện trạng vẫn là
   WAITING_TARGET_DATA.
