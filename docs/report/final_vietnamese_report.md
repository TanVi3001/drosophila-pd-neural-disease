# Báo cáo tổng kết dự án

## 1. Tên đề tài

**Mô phỏng và đánh giá computational locomotion proxy cho kiểu hình vận động Parkinson-like trên Drosophila**

## 2. Tóm tắt

Dự án xây dựng một computational locomotion proxy ở mức organism-level cho các kiểu hình vận động Parkinson-like trên Drosophila. Pipeline sử dụng FlyGym/MuJoCo để thực thi locomotion và một proxy operator tác động lên lệnh vận động trước khi lệnh được gửi tới môi trường. Mục tiêu của pipeline là tạo ra một quy trình có thể kiểm tra, ghi provenance, calibration và đánh giá holdout một cách có kiểm soát.

Chen 2014 được dùng làm nguồn calibration duy nhất cho tỉ lệ walking speed disease/control. Tham số `proxy_burden_level = 0.5` được chọn bằng lưới rời rạc và được xác nhận lại bằng các lần rerun độc lập. Pozo 2022 được giữ hoàn toàn ngoài calibration và dùng như một holdout về distance/path length. Holdout cho thấy cùng chiều suy giảm khoảng cách, nhưng tỉ lệ disease/control mô phỏng chưa khớp định lượng với tỉ lệ từ Pozo.

Kết quả hiện tại chỉ hỗ trợ **directional computational phenotype concordance** ở mức organism-level. Đây không phải biological Parkinson validation, gene-specific validation, clinical validation, drug validation hay therapeutic validation.

## 3. Bối cảnh và động lực

Drosophila thường được dùng trong nghiên cứu vận động và bệnh thần kinh vì có hệ thần kinh được nghiên cứu sâu, nhiều assay hành vi và các mô hình gene liên quan đến kiểu hình thần kinh. Tuy nhiên, dự án này không thực hiện wet-lab và không thay thế thí nghiệm trên ruồi thật.

Động lực của dự án là tạo một pipeline mô phỏng có kiểm soát để nhóm có thể:

- chạy locomotion trong một môi trường tính toán thống nhất;
- ghi lại input, seed, artifact và checksum;
- tách rõ calibration khỏi holdout;
- đối chiếu các metric mô phỏng với target literature mà không đổi đơn vị hoặc statistic tùy ý;
- khóa cách diễn giải để không vượt quá bằng chứng.

Vì vậy, thuật ngữ phù hợp cho kết quả là computational locomotion proxy, không phải một mô hình sinh học hoàn chỉnh của bệnh Parkinson.

## 4. Mục tiêu nghiên cứu

1. Xây dựng pipeline mô phỏng locomotion trên Drosophila.
2. Tạo disease/proxy layer ở mức organism-level.
3. Calibration proxy bằng Chen-only disease/control ratio.
4. Kiểm tra lại tham số đã khóa bằng rerun độc lập.
5. Đánh giá holdout bằng Pozo 2022 mà không dùng Pozo để tune tham số.
6. Khóa claim khoa học theo evidence và ghi rõ giới hạn của mô phỏng.

## 5. Phạm vi và giới hạn

Phạm vi của báo cáo là một computational locomotion proxy. Các rollout được dùng trong các gate hiện có có thời lượng mô phỏng ngắn, khoảng **0.5 giây**, nên không thể được diễn giải như quá trình tiến triển bệnh theo thời gian dài.

Các giới hạn chính:

- Không phải biological Parkinson validation.
- Không phải gene-specific mechanism hoặc gene-specific validation.
- Không phải mô hình chẩn đoán lâm sàng.
- Không phải drug validation, therapeutic validation hoặc dự đoán đáp ứng thuốc.
- Pozo absolute distance chỉ là reference-only do runtime và thang đo assay không hoàn toàn tương đồng.
- Pozo holdout đạt directionality nhưng không đạt quantitative ratio match.
- Parkin, DJ-1 và LRRK2 vẫn không được xem là đã có validation gene-specific nếu thiếu mapping và provenance tương ứng.
- Kết quả hiện tại không chứng minh cơ chế bệnh và không thay thế thí nghiệm trên ruồi thật.

## 6. Dữ liệu mục tiêu từ literature

### 6.1 Chen 2014 calibration target

Target được dùng cho calibration là adult horizontal walking speed của mô hình Old A30P và đối chứng Old CT:

| Hạng mục | Giá trị |
| --- | --- |
| Disease speed | 4.875 mm/s |
| Control speed | 7.275 mm/s |
| Target ratio | 0.6701030927835051 |
| Uncertainty | 0.525 CI95 |
| Sample size | n = 20 fly |
| Allocation | calibration |
| Statistic | mean |
| Unit conversion | 1 cm/s = 10 mm/s |

CI95 được giữ nguyên là CI95. Không đổi CI95 thành SE, SD hoặc một loại uncertainty khác.

### 6.2 Pozo 2022 holdout target

Pozo 2022 Pink1B9 được dùng làm holdout ở endpoint distance/path length:

| Hạng mục | Giá trị |
| --- | --- |
| Model | Pink1B9 |
| Disease distance | 62.091 mm |
| Control distance | 323.326 mm |
| Metric | `distance_traveled_mm` |
| Target ratio | 0.19203837612811836 |
| Spread | 61.288, giữ nguyên như paper-reported |
| Sample size | n = 21 fly |
| Allocation | holdout |
| Transfer | distance/path-length holdout |

Pozo không được dùng làm speed target. Distance không được chuyển thành speed và spread không được đổi thành SD hoặc SE.

## 7. Phương pháp

### 7.1 Pipeline tổng quan

Pipeline được thực hiện theo các gate có provenance riêng:

1. Target audit kiểm tra metric, uncertainty, sample size, reviewer và allocation.
2. Healthy baseline cung cấp reference locomotion.
3. Proxy config mô tả burden và phạm vi tác động.
4. Action hook integration nối operator vào lệnh vận động thực tế.
5. Integrated proxy rollouts ghi lại output computational.
6. Chen calibration chọn burden theo disease/control ratio.
7. Confirmation rerun kiểm tra tham số đã khóa trên seed độc lập.
8. Pozo holdout đánh giá một endpoint không được dùng để tune.
9. Holdout adjudication phân biệt directionality với quantitative agreement.
10. Release bundle khóa artifact, claim và giới hạn công bố.

### 7.2 Proxy operator

Proxy operator tác động lên thành phần `joint_angles` của lệnh vận động. Thành phần `adhesion_onoff` không bị sửa. `burden = 0.0` là control/identity, còn `burden = 0.5` là tham số computational đã được khóa sau Chen calibration.

Operator là một phép biến đổi ở cấp lệnh hành động. Nó không phải mô hình dopamine, alpha-synuclein, tế bào thần kinh bệnh lý hoặc cơ chế phân tử. Cách mô tả đúng là computational perturbation có kiểm soát.

### 7.3 Calibration method

Chen-only ratio calibration sử dụng lựa chọn trên lưới rời rạc với các candidate burden `0.25`, `0.5`, `0.75` và `1.0`. Objective là tối thiểu hóa sai số tuyệt đối giữa simulated disease/control ratio và Chen target ratio. Candidate được chọn là `proxy_burden_level = 0.5`.

Pozo và PINK1 không được dùng trong calibration. Không có parameter reselection sau khi bước calibration kết thúc.

### 7.4 Confirmation rerun

Confirmation chỉ dùng alpha-synuclein organism-level proxy với burden đã khóa `0.5`, control burden `0.0` và các seed độc lập. Có `12/12` rollout PASS. Confirmation ratio là `0.6142225784`, so với Chen target ratio `0.6701030927835051`; ratio error là `0.0558805144` và drift so với Gate 13B là `0.0286013923`.

Đây là kiểm tra tính tái lập của hành vi computational dưới protocol đã khóa, không phải validation sinh học hay gene-specific validation.

### 7.5 Pozo holdout evaluation

Pozo holdout dùng Pink1 organism-level proxy với burden đã khóa `0.5`, control burden `0.0`, holdout burden `0.5` và seed `12-17`. Có `12/12` rollout PASS. Quy trình không tuning Pozo, không chọn lại tham số và không chạy calibration trong holdout.

## 8. Kết quả

### 8.1 Calibration result

| Hạng mục | Giá trị |
| --- | --- |
| Calibration source | Chen 2014 |
| Target ratio | 0.6701030927835051 |
| Selected burden | 0.5 |
| Gate 13B simulated ratio | 0.585621186102 |
| Gate 13B ratio error | 0.0844819066814 |
| Method | Discrete grid selection |

### 8.2 Confirmation result

| Hạng mục | Giá trị |
| --- | --- |
| Runs | 12/12 PASS |
| Confirmation ratio | 0.6142225784 |
| Ratio error vs Chen | 0.0558805144 |
| Drift from Gate 13B | 0.0286013923 |
| Parameter reselection | No |

### 8.3 Pozo holdout result

| Hạng mục | Giá trị |
| --- | --- |
| Runs | 12/12 PASS |
| Control distance | 1.66679 mm |
| Holdout distance | 1.57846 mm |
| Simulated ratio | 0.9470 |
| Pozo target ratio | 0.1920 |
| Directionality | PASS |
| Quantitative ratio match | NOT SUPPORTED |

## 9. Diễn giải khoa học

Pipeline đã chạy thành công theo các artifact được lưu. Chen-only calibration đã khóa burden `0.5`, và confirmation rerun cho thấy hành vi computational của tham số này có thể được tái lập dưới các seed độc lập.

Pozo holdout cho thấy distance ở condition burden giảm so với control, vì vậy directionality được ghi nhận là PASS. Tuy nhiên simulated ratio `0.9470` còn cách xa Pozo target ratio `0.1920`. Do đó, bằng chứng hiện tại chỉ hỗ trợ directional concordance; không hỗ trợ quantitative ratio validation.

Không được suy diễn từ kết quả này rằng proxy đã tái tạo bệnh Parkinson sinh học, đã xác nhận cơ chế gene cụ thể, hoặc có giá trị chẩn đoán, lâm sàng, dược lý hay điều trị. Đây không phải gene-specific validation.

## 10. Reproducibility

Các lệnh kiểm tra artifact và provenance gồm:

```powershell
py -3.12 scripts/prepare_final_release.py
py -3.12 scripts/prepare_release_submission_bundle.py
py -3.12 scripts/adjudicate_pozo_holdout_claims.py
py -3.12 scripts/prepare_pozo_holdout_protocol.py
py -3.12 scripts/run_chen_ratio_calibration.py
py -3.12 scripts/prepare_chen_only_calibration_objective.py
py -3.12 scripts/audit_calibration_targets.py
py -3.12 -m pytest -q -rs -p no:cacheprovider
```

Các lệnh trên dùng để kiểm tra trạng thái và artifact hiện có. Gate 17A không chạy GPU, không chạy simulation mới, không calibration và không tuning.

GPU rollout artifacts của các gate trước đã được lưu kèm checksum và manifest. Reviewer không cần rerun GPU mặc định để đọc báo cáo này. Release không commit binary artifact lớn, viewer bundle, checkpoint hoặc video.

## 11. Kết luận

Dự án đạt mức reviewer-ready cho một **Chen-calibrated organism-level computational locomotion proxy**. Kết quả Pozo holdout hỗ trợ directional concordance nhưng không hỗ trợ quantitative ratio validation. Vì vậy, claim hợp lệ hiện tại là computational phenotype concordance ở mức organism-level, chưa phải biological Parkinson validation hay gene-specific validation.

## 12. Hướng phát triển tiếp theo

1. Kéo dài runtime simulation để protocol gần hơn với thời lượng assay, đồng thời kiểm tra ảnh hưởng của thời lượng lên metric.
2. Mở rộng candidate burden hoặc dùng operator liên tục chỉ sau khi có protocol và target được phê duyệt.
3. Bổ sung mapping và provenance gene-specific nếu có nguồn dữ liệu đủ rõ.
4. Bổ sung target độc lập cho PINK1 hoặc alpha-synuclein khi có nguồn định lượng và assay transfer được review.
5. Đăng ký trước tolerance của holdout trước khi chạy một vòng đánh giá mới.
6. So sánh nhiều proxy operator bằng cùng physics, seed policy và endpoint contract.
7. Không dùng kết quả hiện tại cho claim clinical, drug hoặc therapeutic.
