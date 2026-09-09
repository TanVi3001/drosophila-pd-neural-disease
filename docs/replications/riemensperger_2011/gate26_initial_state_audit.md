# Gate26 initial state audit

## Phạm vi

Đây là audit trước khi hoàn thiện computational replication theo
Riemensperger et al. 2011. Audit này chỉ mô tả artifact hiện có; chưa phải
kết quả mô phỏng mới và không thay thế human review.

## Kết quả đọc từ origin/main

| Hạng mục | Trạng thái trước Gate26 | Nhận xét |
| --- | --- | --- |
| Gate21A evidence lock | `RIEMENSPERGER_2011_EVIDENCE_LOCKED` | Median speed và distance của paper đã được khóa; uncertainty là `NOT_REPORTED`. |
| Gate21B healthy | `NOT_EXECUTED_DRY_RUN` | Chưa có đủ healthy rollout metrics để chạy Gate21C. |
| Gate21C comparability | Chưa sẵn sàng | Phụ thuộc healthy summary thật. |
| Gate21D mapping summary | `READY_FOR_RIEMENSPERGER_DISEASE_REPLICATION` | 342 dopamine-class targets, `DOPAMINE_CLASS_LEVEL_EXPLORATORY`, không gene-specific, blockers rỗng. |
| Gate21D report/status surface | Có nội dung stale ở một số artifact | Gate26 sẽ reconcile status surface, không mở rộng mapping và không tạo evidence mới. |
| Gate21E disease | `WAITING_DOPAMINE_MAPPING_REVIEW` | Manifest cũ ghi blocker mapping và thiếu external brain source. |
| Gate21F analysis | `WAITING_VIRTUAL_GROUP_RESULTS` | Healthy/disease summary chưa tồn tại. |
| Pipeline status | `WAITING_EVIDENCE`, `simulation_executed=false` | Phù hợp với việc chưa có computational rollout mới ở snapshot này. |

## Bằng chứng nền

- Gate24E: `GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE`.
- Scientific result Gate24E: `NEGATIVE_VALIDATION_RESULT`.
- Cross-assay decision: `DIRECTIONAL_CROSS_ASSAY_DISCORDANCE`.
- Gate25-R2: `GATE25_R2_REPRODUCIBILITY_FREEZE_COMPLETE`.
- Mapping scope: dopamine class-level exploratory only, target count 342.

## Technical blockers cần xử lý trước GPU

1. Hai runner Gate21B/Gate21E đang thêm các video CLI flags mà frozen runtime không hỗ trợ.
2. Scientific child command chưa truyền rõ `--artifact-profile GATE24E_MEMORY_SAFE`.
3. Healthy và disease summary chưa được sinh từ 5 seed độc lập.
4. Bản final report và pipeline status đang phản ánh snapshot cũ.

## Ranh giới khoa học

Gate26 chỉ nhằm hoàn thiện một `PAPER_GUIDED_COMPUTATIONAL_REPLICATION` với
mapping `DOPAMINE_CLASS_LEVEL_EXPLORATORY`. Không được gọi kết quả là
biological Parkinson validation, gene-specific validation, clinical validation
hoặc drug validation.
