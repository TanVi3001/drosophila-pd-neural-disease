# Target approval review summary

Review branch: `review/target-approval`
Review date: 2026-08-30
Reviewer: ChatGPT hỗ trợ audit; quyết định khoa học cần human sign-off.

## Kết luận

Trạng thái đúng hiện tại là `WAITING_TARGET_DATA`.

Không approve calibration target nào ở bước này vì `calibration_targets/targets.csv` vẫn chỉ có 2 dòng `pending`, trong đó:

- `riemensperger_2011_dopamine_deficiency`: giá trị 7.8 mm/s là median, chưa có variance tương thích, metric đang đặt là `mean_planar_speed_mm_s`, và cần quyết định assay transfer từ open arena sang FlyGym flat-ground.
- `pokrzywa_2017_alpha_syn_flytracker`: giá trị 2.5 mm/s chưa được xác nhận là endpoint tuổi chính xác, thiếu SE/variance số học, sample size đang ở dạng `3-10 vials; 10 flies/vial`, và cần quyết định assay transfer.

Do đó calibration target hợp lệ = 0 và holdout target hợp lệ = 0.

## Review theo paper

### Riemensperger 2011

Decision: `PENDING_HUMAN_SIGNOFF`

Lý do:

- Có candidate locomotion endpoint: median walking speed 7.8 mm/s, 5 ngày, n=13, Figure 2A.
- Không được approve ngay vì median không tương thích trực tiếp với metric `mean_planar_speed_mm_s` nếu chưa có quy tắc dùng median hoặc chuyển đổi thống kê.
- Chưa có variance số học phù hợp.
- Cần human sign-off cho assay transfer.

### Pokrzywa 2017

Decision: `PENDING_HUMAN_SIGNOFF`

Lý do:

- Có candidate FlyTracker velocity theo tuổi.
- Giá trị 2.5 mm/s cần xác nhận lại đúng mốc tuổi/endpoint.
- Thiếu SE/variance số học.
- Sample size cần giữ đúng đơn vị phân tích: vial hay fly.
- Không tự ghi sample size dạng một số nguyên nếu paper chỉ báo range vials.

### Pozo 2022

Decision: `PENDING_HUMAN_SIGNOFF` cho distance; `NOT_COMPARABLE` cho activity time.

Lý do:

- Distance và activity time ở Day 28 là thông tin có ích cho validation/phenotype comparison.
- Không đổi IQR hoặc min/max thành SD.
- `activity_time` không được đổi thành walking speed hoặc pause fraction nếu chưa có transfer rule.

### Dumitrescu 2023

Decision: `NOT_COMPARABLE`

Lý do:

- DAM beam-break activity không tương đương `mean_planar_speed_mm_s`.
- Có thể giữ làm evidence định tính hoặc age-dependent activity context, không dùng làm calibration speed target.

### Hwang 2013 và Godena 2014

Decision: `VALIDATION_ONLY`

Lý do:

- Cả hai chủ yếu là climbing phenotype.
- Nếu pipeline chưa có climbing assay/metric tương ứng thì không dùng làm calibration target cho speed.
- Có thể dùng làm holdout/validation định tính hoặc sau khi Multi-Assay/climbing module được triển khai.

## Root-ID mapping

Không approve root-ID mapping gene-specific ở bước này.

- 342 dopamine root IDs hiện chỉ là `CLASS_LEVEL_EXPLORATORY_ONLY`.
- Không dùng chúng để kết luận mapping PINK1, Parkin, DJ-1, LRRK2 hoặc alpha-synuclein.
- Cần FlyWire version, root ID, neuron name, cell type, driver/expression scope, source URL/accession, reviewer và review date cho từng mapping trước khi dùng cho gene-specific calibration.

## Trạng thái file hiện tại

Các file review đã đi đúng hướng:

- `research/paper_review/paper_analysis_vi.csv`: có reviewer/date/decision cho từng record.
- `datasets/literature_phenotypes/second_review_audit.csv`: có các decision an toàn như `PENDING_HUMAN_SIGNOFF`, `VALIDATION_ONLY`, `NOT_COMPARABLE`.
- `datasets/literature_phenotypes/root_id_mapping_audit.csv`: chưa suy diễn gene-specific root IDs.
- `calibration_targets/targets.csv`: vẫn giữ `pending`, không approve khi chưa đủ uncertainty, sample size, assay transfer và allocation.

## Next actions

1. Review PDF/PMC gốc thủ công cho Riemensperger và Pokrzywa.
2. Ghi rõ statistic type: mean, median, SD, SEM, SE, IQR, min/max.
3. Xác nhận đơn vị sample size: fly, vial, replicate hay independent experiment.
4. Đưa ra assay-transfer policy trước khi dùng open arena/FlyTracker/climbing cho FlyGym flat-ground.
5. Chỉ sau khi có ít nhất 1 approved calibration target và 1 approved holdout target độc lập mới chuyển audit sang `READY_FOR_CALIBRATION`.

## Scientific boundary

Giữ trạng thái `WAITING_TARGET_DATA` không phải lỗi phần mềm. Đây là quyết định khoa học đúng vì chưa đủ provenance để hiệu chuẩn hoặc holdout validation.
