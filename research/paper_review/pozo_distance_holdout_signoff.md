# Pozo distance holdout signoff

## Trạng thái

`TRANSFER_REVIEW_REQUIRED`

Tài liệu này là form ghi nhận quyết định của research lead. Nó không tự tạo ra signoff và không được coi là phê duyệt khi chưa có tên reviewer thật, ngày review thật và quyết định assay transfer rõ ràng.

## Candidate

- `paper_id`: `pozo_2022_pink1_serotonin`
- Gene model: `pink1`
- Genotype: `Pink1B9`
- Age: `28` ngày
- Sex: `not_reported` trong phần đã trích xuất
- Assay: open-field locomotor tracking
- Figure: `Figure 3B`
- DOI/PMID: `10.3390/cells11091544; PMID:35563850`
- Literature center: `62.091 mm`
- Literature spread: `61.288`, giữ nguyên biểu diễn IQR với min/max theo paper
- Sample size: `21 fly`

## Quy tắc bắt buộc

- Candidate này chỉ được phân bổ `holdout`.
- Metric giữ nguyên `distance_traveled_mm`.
- Không chuyển distance thành walking speed.
- Không chuyển IQR/min-max thành SD hoặc SE.
- Không dùng candidate này cho calibration speed.
- `assay_transfer=allowed` chỉ được điền sau khi research lead xác nhận rằng open-field distance của paper phù hợp với endpoint distance/path-length của FlyGym.
- Holdout phải độc lập với target calibration; không dùng cùng cohort cho hai mục đích.

## Quyết định cần điền bởi người có thẩm quyền

```text
reviewer: <tên thật>
review_date: <YYYY-MM-DD>
assay_transfer: <allowed | TRANSFER_REVIEW_REQUIRED>
allocation: holdout
decision: <APPROVED_FOR_HOLDOUT | PENDING_HUMAN_SIGNOFF>
reason: <lý do ngắn gọn>
```

Chỉ khi điền `APPROVED_FOR_HOLDOUT`, có provenance và assay transfer `allowed`, row mới được xem xét cập nhật vào `calibration_targets/targets.csv`. Việc này vẫn không làm Pozo trở thành calibration speed target.

## Provenance

- [Pozo et al. 2022, Cells](https://www.mdpi.com/2073-4409/11/9/1544)
- Survey record: `research/paper_review/literature_survey_expanded_targets.csv`
- Review matrix: `research/paper_review/full_target_survey_matrix.csv`

## Ranh giới khoa học

Đây chỉ là quyết định transfer cho một holdout computational distance endpoint. Nó không phải biological validation, không phải chẩn đoán Parkinson và không chứng minh assay equivalence toàn diện.
