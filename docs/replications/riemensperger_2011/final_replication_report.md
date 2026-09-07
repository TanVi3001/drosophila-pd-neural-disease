# Tái lập computational Riemensperger 2011

## 1. Câu hỏi nghiên cứu

Liệu một perturbation ở mức lớp neuron dopamine, được xây dựng từ evidence của Riemensperger 2011 và chạy qua neural core/FlyGym công khai, có tái hiện hướng thay đổi locomotion của ruồi thật hay không?

## 2. Thiết kế bốn nhóm

A. Real DTHg; ple control; B. virtual healthy; C. real DTHgFS±; ple; D. virtual dopamine-class perturbation.

## 3. Trạng thái gate

- 21A: `RIEMENSPERGER_2011_EVIDENCE_LOCKED`
- 21D: `WAITING_DOPAMINE_MAPPING_REVIEW`

## 4. Claim lock

> The Riemensperger 2011-guided computational replication remains a gated study; no biological validation claim is made.

Không được gọi kết quả này là biological Parkinson validation, gene-specific validation, clinical validation, drug validation hoặc therapeutic validation.

## 5. Evidence và giới hạn

Paper báo median speed 10.8 mm/s cho DTHg; ple, 7.8 mm/s cho DTHgFS±; ple và 15 mm/s cho WT; median distance là endpoint riêng. Variance không báo cáo được giữ là NOT_REPORTED. Virtual duration khác 15 phút của assay thật nên raw-scale agreement không được khẳng định; ratio chỉ là endpoint exploratory có giới hạn.

## 6. Tái lập

Mọi gate phải lưu config, input/output SHA256, commit, Python/runtime, seed list, QC và trạng thái simulation. GPU chỉ được chạy sau khi evidence lock và mapping class-level có human signoff.
