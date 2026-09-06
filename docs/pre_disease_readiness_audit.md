# Audit chuẩn bị disease comparison

Ngày audit: 2026-08-30

## Kết luận ngắn

Healthy baseline đã sẵn sàng ở mức computational runtime: năm seed thật chạy bằng
FlyGym/MuJoCo/CUDA, có locomotion, QC và provenance. Disease comparison gene-specific
chưa được phép chạy theo protocol khoa học vì target literature và neural mapping
chưa đạt gate.

Trạng thái hiện tại:

```text
HEALTHY_BASELINE_READY
DISEASE_GENE_SPECIFIC_WAITING_EVIDENCE
CALIBRATION_WAITING_TARGET_DATA
HOLDOUT_WAITING_TARGET_DATA
```

## Những gì đã xác minh

- Runtime: Python 3.12.10, FlyGym 2.1.0, MuJoCo 3.9.0, Torch CUDA.
- Neural source được pin theo commit `27cec28d5d202eb004683fb4c1a1033eec8deea0`.
- Healthy seeds 0-4 đều hoàn tất với 5.001 frame và 0,5 giây simulation.
- Có dịch chuyển thorax, quỹ đạo phẳng, vận tốc đi bộ, contact, quaternion hợp lệ
  và joint trajectory thay đổi.
- Bảng metric, CI mô tả, biểu đồ và provenance/checksum đã nằm dưới
  `results/healthy_baseline_reproducible/summary/`.
- Có 6 nguồn paper và 14 phenotype records trong hồ sơ literature; PDF-backed
  review đã lưu hash cho 5 PDF và ghi rõ Dumitrescu dùng fallback full text.

## Review literature hiện tại

| Nguồn | Quyết định hiện tại | Có thể dùng ngay không? |
|---|---|---|
| Riemensperger 2011 | Pending; median speed, thiếu numeric spread tương thích | Không dùng cho mean speed |
| Pokrzywa 2017 | Pending; mean velocity nhưng thiếu numeric SE và unit of analysis | Ứng viên tốt nhất sau khi bổ sung metadata |
| Pozo 2022 | Pending cho distance; activity time không comparable với speed | Ứng viên holdout distance |
| Hwang 2013 | Validation-only | Không dùng cho flat-ground speed calibration |
| Godena 2014 | Validation-only | Không dùng khi chưa có climbing/flight và VNC scope |
| Dumitrescu 2023 | Not comparable với speed | Chỉ context DAM activity |

Không target nào được đổi sang `approved`. Không có calibration target hoặc holdout
target hợp lệ ở thời điểm audit.

## Root-ID mapping

- Dopamine deficiency: 342 ID là class-level exploratory mapping, không phải
  gene-specific mapping.
- PINK1: organism-level mutant, chưa có cell-specific root-ID intervention.
- Parkin: TH-GAL4 class scope, chưa có reviewed root-ID set.
- DJ-1: paper không cung cấp intervention cell-specific để map root ID.
- LRRK2: D42 motor-neuron/VNC scope, trong khi catalog hiện tại chưa đủ provenance
  cho phạm vi này.
- Alpha-synuclein: nSyb-GAL4 pan-neuronal, chưa có reviewed root-ID export.

Không thêm root ID vào annotation chỉ vì gene hoặc driver name.

## Config readiness

Chi tiết nằm trong
`research/disease_mapping/disease_condition_readiness.csv`.

- Healthy: đã chạy được và làm reference.
- Dopamine deficiency: chỉ exploratory class-level condition.
- PINK1, Parkin, DJ-1, LRRK2 và alpha-synuclein: template còn rỗng ở
  `target_neurons`, `target_edges`, `burden_curve` và provenance đủ để chạy.

Do đó không được dùng lệnh campaign để tạo disease result bằng cách bỏ qua gate.

## Gate để chuyển bước

Trước disease multi-seed cần đủ đồng thời:

1. Target literature có provenance, statistic và uncertainty chính xác.
2. Sample size số học cùng unit of analysis.
3. Reviewer thứ hai và ngày review thực tế.
4. Quyết định assay transfer rõ ràng.
5. Phân bổ độc quyền `calibration` hoặc `holdout`.
6. Root-ID mapping có source/version/scope/reviewer, hoặc một quyết định khoa học
   được phê duyệt rằng condition dùng proxy class-level.
7. Condition config có neuron/edge/burden/provenance đầy đủ.
8. Disease rollout đạt cùng QC với Healthy.

## Công việc có thể làm ngay trong lúc chờ review

- Research lead kiểm tra `research/paper_review/target_decision_matrix.csv` cùng
  PDF và supplementary.
- Bổ sung numeric uncertainty chỉ khi đọc được trực tiếp từ source; nếu không,
  giữ trống và để `PENDING_HUMAN_SIGNOFF`.
- Chốt assay transfer cho speed và distance riêng, không gộp endpoint.
- Chuẩn bị mapping VNC/motor-neuron cho LRRK2 nếu nguồn có provenance phù hợp.
- Sau khi Tuấn hoàn tất policy branch, chạy lại test và audit target; không tự
  phê duyệt thay reviewer.

## Ranh giới khoa học

Ngay cả khi disease comparison đạt QC và khớp một số target, kết quả vẫn chỉ là
computational locomotion concordance dưới một perturbation. Nó không chứng minh
mô hình Parkinson sinh học hoàn chỉnh, không phải chẩn đoán, clinical prediction,
drug response hay thay thế thí nghiệm trên ruồi thật.
