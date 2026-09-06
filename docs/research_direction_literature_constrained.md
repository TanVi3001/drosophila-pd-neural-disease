# Định hướng nghiên cứu: thí nghiệm ảo có ràng buộc từ literature

**Trạng thái:** `PROPOSED_AND_FEASIBLE`

**Ngày ghi nhận:** 2026-09-07

## 1. Thay đổi ý tưởng

Dự án được mở rộng từ một computational locomotion proxy đơn lẻ thành một
**quy trình tái lập có kiểm soát các thí nghiệm hành vi trên Drosophila bằng
virtual fly**.

Luồng nghiên cứu mới là:

```text
paper/supplementary
    -> phenotype record và provenance
    -> review assay, metric, statistic, uncertainty, sample unit
    -> assay bridge được phê duyệt hoặc validation-only
    -> condition/proxy được khai báo trước
    -> FlyGym/MuJoCo rollout nhiều seed
    -> QC, metric, manifest và video
    -> so sánh direction/magnitude với literature
    -> báo cáo mismatch, capability gap và giả thuyết tiếp theo
```

Vận động phẳng vẫn là endpoint đầu tiên có runtime và metric tương ứng. Các
assay khác không được tự động quy đổi sang walking speed.

## 2. Câu hỏi nghiên cứu

Với một phenotype và protocol đã được review, một virtual fly có thể tạo ra
thay đổi locomotion cùng chiều và, khi assay tương thích, gần mức độ quan sát
được trong paper hay không?

Câu hỏi này kiểm tra khả năng tái lập computational của endpoint. Nó không
khẳng định rằng proxy đã mô phỏng đầy đủ cơ chế bệnh, neuron loss,
dopamine/alpha-synuclein biology hoặc Parkinson sinh học.

## 3. Vì sao hướng này khả thi

Kiến trúc hiện tại đã có các lớp cần thiết:

- `drosophila-pd-flygym/` giữ FlyGym/MuJoCo, controller, action hook, physics,
  rollout, metric, QC và viewer.
- `drosophila-pd-neural-disease/` giữ paper registry, phenotype review,
  target policy, calibration/holdout, condition metadata và proxy adapter.
- Chen-only calibration và Pozo holdout đã tạo được một quy trình computational
  có tách calibration khỏi holdout.
- Healthy baseline nhiều seed và Gate 20 đã cung cấp protocol để kiểm tra
  runtime trước khi mở rộng disease matrix.

Do đó, thay đổi này có thể triển khai theo hướng additive: mở rộng schema,
assay adapter, experiment manifest và analysis; không cần copy hoặc sửa sở hữu
của platform FlyGym/MuJoCo.

## 4. Những gì cần hoàn thiện

### 4.1 Bằng chứng và mapping

- Hoàn tất provenance của từng paper, figure/supplementary, uncertainty và
  unit-of-analysis.
- Giữ các target không tương thích ở `VALIDATION_ONLY` hoặc
  `NOT_COMPARABLE`.
- Chỉ dùng gene-specific condition khi có mapping neuron/edge và checkpoint
  provenance độc lập. Gene name hoặc driver name không đủ để suy ra root ID.

### 4.2 Capability của virtual assay

Runtime hiện có nền tảng cho flat-ground locomotion. Climbing, flight, DAM,
tremor, PER và negative geotaxis cần endpoint/arena/metric riêng trước khi
được dùng làm target số học.

### 4.3 Disease experiment

Gate 20 hiện chỉ là organism-level computational proxy. Mọi positive-burden
rollout phải đủ seed, QC, manifest và action metadata trước khi diễn giải.
Không được gọi matrix exploratory này là gene-specific validation.

## 5. Tiêu chí thành công của một vòng nghiên cứu

Một vòng chỉ được gọi là tái lập computational trong phạm vi xác định khi có:

1. paper và provenance nguồn;
2. phenotype record được review;
3. metric/đơn vị/statistic/uncertainty không bị đổi nghĩa;
4. assay bridge được phê duyệt;
5. condition, seed, physics, timestep và duration được khóa trước;
6. rollout thật đạt QC, không NaN/Inf và có trajectory/contact hợp lệ;
7. so sánh seed-level với baseline;
8. mismatch và giới hạn được báo cáo đầy đủ;
9. holdout độc lập, không dùng để tune calibration.

Kết quả cuối mỗi vòng phải được gắn một trạng thái như
`REPRODUCED_COMPUTATIONALLY_WITHIN_DEFINED_SCOPE`,
`DIRECTIONALLY_CONCORDANT_QUANTITATIVE_MISMATCH`, `VALIDATION_ONLY`,
`NOT_COMPARABLE` hoặc `WAITING_PLATFORM_CAPABILITY`.

## 6. Ranh giới claim

### Có thể nói

- paper-guided virtual experiment;
- computational locomotion phenotype comparison;
- organism-level/action-level proxy;
- directional concordance hoặc quantitative mismatch;
- reproducible rollout protocol với manifest, checksum và seed-level metrics.

### Chưa được nói

- biological Parkinson validation;
- gene-specific Parkinson model đã được xác nhận;
- chứng minh cơ chế neuron/dopamine/alpha-synuclein;
- chẩn đoán, dự đoán lâm sàng hoặc đánh giá thuốc.

## 7. Thứ tự triển khai được đề xuất

1. Giữ claim lock và cập nhật experiment registry theo định hướng này.
2. Đồng bộ platform contract hiện tại trước khi tái chạy kết quả lịch sử.
3. Hoàn tất Gate 20 với positive-burden matrix và QC đầy đủ, chỉ ở scope
   organism-level proxy.
4. Thêm assay bridge riêng cho endpoint literature có giá trị cao; không ép
   climbing/DAM/distance thành walking speed.
5. Tái chạy calibration/holdout trên protocol hiện hành và lưu artifact mới.
6. Xây figures/tables theo seed-level result, uncertainty, mismatch và
   capability gap để chuẩn bị manuscript.

Tài liệu này là định hướng triển khai. Nó không thay đổi kết quả raw, target,
claim lock hoặc trạng thái biological validation hiện có.
