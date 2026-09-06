# Đề cương đề tài: Tái lập kiểu hình vận động Drosophila trên ruồi ảo

**Trạng thái:** `PROPOSED_AND_FEASIBLE`
**Phạm vi:** thí nghiệm tính toán có ràng buộc bằng bằng chứng literature
**Nền tảng:** FlyGym/MuJoCo và lớp chuyển dịch paper-to-experiment
**Ngày cập nhật:** 2026-09-07

## 1. Tên đề tài

### Tên tiếng Việt

**Tái lập có kiểm soát các kiểu hình vận động Drosophila liên quan Parkinson từ
literature trên ruồi ảo FlyGym/MuJoCo**

### Tên tiếng Anh

**Evidence-constrained computational reproduction of Parkinson-like Drosophila
locomotion phenotypes in a FlyGym/MuJoCo virtual fly**

Tên đề tài cố ý dùng “Parkinson-like locomotion phenotypes”, không dùng “biological
Parkinson model”, vì pipeline hiện tại đánh giá kiểu hình vận động tính toán chứ chưa
chứng minh đầy đủ cơ chế bệnh ở cấp gene, neuron hoặc phân tử.

## 2. Ý tưởng và câu hỏi nghiên cứu

Nhiều paper trên ruồi thật báo cáo thay đổi vận động ở các mô hình liên quan đến
alpha-synuclein, PINK1, Parkin, DJ-1, LRRK2 hoặc thiếu dopamine. Dự án không lấy
một con số trong paper rồi ép mô hình phải khớp. Thay vào đó, nhóm xây dựng một quy
trình có thể kiểm tra từng bước:

```text
paper/supplementary
  -> phenotype record và provenance
  -> review assay, metric, statistic, uncertainty, sample unit
  -> assay bridge được duyệt hoặc validation-only
  -> hypothesis/proxy khai báo trước
  -> FlyGym/MuJoCo rollout nhiều seed
  -> QC, metrics, manifest, checksum và video
  -> so sánh direction, magnitude, uncertainty và mismatch
```

**Câu hỏi nghiên cứu chính:**

> Khi giữ rõ protocol, cohort, endpoint và điều kiện có thể chuyển đổi, một virtual
> fly với perturbation được khai báo trước có tạo ra thay đổi cùng chiều và, nếu
> assay tương thích, gần mức quan sát trong paper hay không?

Kết quả không khớp cũng là kết quả có giá trị: nó chỉ ra giới hạn của proxy, khác
biệt assay, thiếu capability hoặc giả thuyết cần được sửa và kiểm tra độc lập.

## 3. Giả thuyết kiểm tra

Các giả thuyết phải được khóa trong config trước khi chạy:

1. Một proxy ở mức action/organism có thể tạo ra thay đổi có hướng trong một số
   metric locomotion của virtual fly.
2. Directional concordance không bảo đảm quantitative concordance.
3. Mismatch giữa virtual fly và paper giúp xác định capability gap hoặc assay bridge
   chưa phù hợp.
4. Calibration chỉ sử dụng target được duyệt; holdout được giữ độc lập và không
   được dùng để tune proxy.

Đây là giả thuyết tính toán. Nó không đồng nghĩa với giả thuyết rằng proxy đã mô
phỏng neuron chết, mất dopamine, kết tụ alpha-synuclein hoặc cơ chế Parkinson thật.

## 4. Kiến trúc triển khai

### 4.1. Nền tảng virtual fly

Repository `drosophila-pd-flygym` sở hữu FlyGym/MuJoCo, fly body, controller,
action lifecycle, physics, rollout, metric, QC, manifest và viewer. Extension không
copy hoặc sửa source platform; chỉ dùng public `Perturbation` contract.

### 4.2. Lớp chuyển paper thành thí nghiệm

Repository hiện tại sở hữu paper registry, phenotype records, PDF/provenance,
review matrix, target policy, calibration/holdout workflow, condition metadata và
proxy adapter.

### 4.3. Action-level proxy

`ProxyBurdenPerturbation` là một biến đổi tính toán ở ranh giới action. Nó có thể
giảm joint-angle command theo burden đã khai báo trong config và giữ adhesion theo
contract. Nó không phải mô hình trực tiếp của neuron loss, dopamine depletion,
protein aggregation hoặc mutation biology.

## 5. Thiết kế thực nghiệm

### Giai đoạn A: bằng chứng và assay

Mỗi phenotype record phải có paper/DOI/PMID, genotype, tuổi, giới tính, assay,
metric, đơn vị, statistic, uncertainty, sample unit, figure/table và supplementary
provenance. Những endpoint không tương thích được giữ là `VALIDATION_ONLY`,
`NOT_COMPARABLE` hoặc `WAITING_TARGET_DATA`.

Không được:

- đổi median thành mean;
- đổi SE, SEM, SD, IQR, range hoặc CI95 cho nhau;
- đổi distance, climbing, DAM activity hoặc flight thành walking speed;
- suy root ID chỉ từ tên gene hoặc driver;
- dùng holdout để chọn burden.

### Giai đoạn B: healthy baseline

Chạy healthy với cùng physics, timestep, controller, duration, renderer và seed
policy. Kiểm tra timestamp, NaN/Inf, contact, thorax displacement, joint/action
trajectory, orientation và metric contract trước khi chạy disease proxy.

### Giai đoạn C: exploratory disease proxy

Chạy grid burden đã khai báo trước ở mức organism/action-level. Mỗi seed phải có
rollout thật, QC pass, metrics seed-level, manifest và checksum. Các nhãn
`alpha_synuclein` hoặc `pink1` trong grid exploratory không tự động chứng minh
gene-specific mapping.

### Giai đoạn D: calibration và confirmation

Chen adult horizontal walking speed là calibration objective khi target, unit,
uncertainty, sample unit, reviewer và assay transfer đã được duyệt. Calibration
chỉ chọn trong grid đã định trước. Confirmation phải dùng seed độc lập và không sửa
proxy sau khi xem holdout.

### Giai đoạn E: holdout

Pozo `distance_traveled_mm` được dùng riêng như holdout distance/path-length.
Không chuyển endpoint này thành speed và không dùng nó để tune calibration. Báo cáo
phải tách directionality khỏi magnitude và ghi mismatch nếu có.

## 6. Metric và đầu ra

### Metric chính

- `mean_planar_speed_mm_s`;
- `distance_traveled_mm`;
- net planar displacement;
- trajectory efficiency khi endpoint được định nghĩa tương thích.

### Metric phụ và QC

- heading và heading variance;
- joint velocity và symmetry;
- body orientation stability;
- contact ratio;
- timestamp/timestep consistency;
- action và observation trajectory validity.

### Artifact bắt buộc

Mỗi experiment hợp lệ nên xuất:

- config và input checksum;
- seed-level metrics CSV/JSON;
- rollout manifest;
- QC report;
- comparison report;
- biểu đồ có đơn vị và uncertainty;
- video MP4 đại diện nếu cần trực quan hóa;
- storage policy, để raw artifact lớn có thể dọn sau khi hash mà không mất
  provenance.

## 7. Tiêu chí đánh giá

Report phải tách bốn lớp:

1. **Runtime/QC:** simulation có chạy thật, đủ frame, finite và contact/action hợp
   lệ không?
2. **Computational result:** metric và phân phối giữa control với condition thay
   đổi thế nào ở cấp seed?
3. **Paper comparison:** direction, magnitude, uncertainty và assay có tương thích
   không?
4. **Interpretation:** giữ giả thuyết, sửa proxy, thêm capability, xin provenance
   hay kết luận chưa tái lập được?

Các trạng thái kết quả được phép dùng:

- `REPRODUCED_COMPUTATIONALLY_WITHIN_DEFINED_SCOPE`;
- `DIRECTIONALLY_CONCORDANT_QUANTITATIVE_MISMATCH`;
- `VALIDATION_ONLY`;
- `NOT_COMPARABLE`;
- `WAITING_TARGET_DATA`;
- `WAITING_PLATFORM_CAPABILITY`;
- `NOT_REPRODUCED`.

## 8. Đóng góp khoa học dự kiến

Đóng góp của đề tài là một **quy trình tái lập computational có provenance**, nối
paper về ruồi thật với virtual fly thông qua assay bridge được review. Quy trình
cho phép:

- kiểm tra endpoint nào có thể tái lập trên FlyGym;
- định lượng direction, magnitude và mismatch;
- phân biệt calibration với holdout;
- phát hiện capability gap thay vì che giấu mismatch;
- tạo artifact reproducible cho người khác kiểm tra và mở rộng.

Đóng góp này có ý nghĩa giao thoa giữa sinh học tính toán và kỹ thuật mô phỏng,
nhưng không được trình bày như bằng chứng thay thế wet-lab.

## 9. Trạng thái evidence hiện tại

Theo context của nhóm tại ngày 2026-09-07:

- Healthy baseline đã có protocol multi-seed để kiểm tra locomotion và runtime;
- Chen calibration và Pozo holdout đã có workflow computational, nhưng các kết quả
  lịch sử phải được phân biệt với kết quả re-run trên contract hiện tại;
- Pozo holdout từng cho thấy directional concordance nhưng quantitative mismatch;
- Gate 20 hiện chỉ thuộc organism-level exploratory proxy và cần đủ positive-burden
  rollout trước khi kết luận disease effect;
- neural edge checkpoint runtime, gene-specific root-ID mapping và các assay
  climbing/flight/DAM/tremor vẫn là capability hoặc provenance gap nếu chưa được
  xác nhận độc lập.

Các dòng trên là trạng thái của evidence package, không phải tuyên bố rằng mô hình
đã được xác nhận sinh học.

## 10. Claim được phép trong bài báo

Có thể viết:

> Chúng tôi xây dựng một paper-guided virtual experiment pipeline để đánh giá các
> kiểu hình vận động Drosophila liên quan Parkinson trong phạm vi assay có thể
> chuyển đổi sang FlyGym/MuJoCo. Pipeline tách calibration khỏi holdout, ghi nhận
> provenance và báo cáo cả directional concordance lẫn quantitative mismatch.

Không được viết rằng project đã:

- xác nhận biological Parkinson;
- chứng minh mô hình gene-specific cho PINK1, Parkin, DJ-1, LRRK2 hoặc alpha-syn;
- chứng minh cơ chế neuron/dopamine/protein;
- chẩn đoán, dự đoán lâm sàng hoặc đánh giá thuốc;
- tái lập đầy đủ mọi phenotype trong paper;
- thay thế thí nghiệm trên ruồi thật.

## 11. Lộ trình để gửi bài

1. Khóa version của hai repository, environment, config, seed và manifest.
2. Hoàn thiện human review cho phenotype records và assay transfer.
3. Re-run Healthy baseline trên platform contract hiện tại.
4. Hoàn tất Gate 20 với positive-burden rollout, QC và seed-level summary.
5. Re-run Chen calibration/confirmation bằng artifact mới, tách khỏi historical
   result.
6. Re-run Pozo holdout độc lập, giữ mismatch nếu còn.
7. Tạo figures/tables về pipeline, QC, baseline, proxy dose-response và
   calibration/holdout.
8. Viết Methods, Reproducibility, Limitations và Claim Lock.
9. Đóng gói source, config, manifest, checksums và artifact nhẹ; raw artifact lớn
   chỉ lưu ở nơi có provenance phù hợp.
10. Chọn hội nghị/tạp chí phù hợp với computational biology, virtual experiment
    hoặc scientific software; không gửi bài với claim vượt quá evidence.

## 12. Kết luận phạm vi

Đề tài khả thi và có hướng công bố nếu được trình bày là **evidence-constrained
computational reproduction/phenotype comparison**. Giá trị khoa học nằm ở khả năng
truy vết từ paper đến virtual protocol, kiểm định có kiểm soát và phân tích mismatch.
Để nâng cấp thành biological Parkinson validation hoặc gene-specific disease model,
cần thêm mapping, checkpoint/runtime, dữ liệu độc lập và validation ngoài mô phỏng.
