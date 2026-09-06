# Gate 20C - Mapping acquisition và human signoff

**Trạng thái:** `MAPPING_ACQUISITION_BLOCKED`

## Kết quả hiện tại

- Approved condition: `0/5`.
- Condition đã được kiểm tra trong package: `5/5`.
- Disease mapping readiness: `DISEASE_MAPPING_BLOCKED`.
- Không chạy GPU, simulation, calibration hoặc tuning.
- Không sửa raw metrics hay healthy core.
- Không suy ra root ID/edge ID từ gene, driver, phenotype hoặc tên tế bào.

## Bảng condition

| Condition | Import thật | Identifier | Signoff | Kết luận |
| --- | ---: | ---: | --- | --- |
| `alpha_synuclein` | không | `0` | `MODEL_SCOPE_NOT_CELL_SPECIFIC` | `BLOCKED_NO_MANUAL_IMPORT` |
| `pink1` | không | `0` | `MODEL_SCOPE_NOT_CELL_SPECIFIC` | `BLOCKED_NO_MANUAL_IMPORT` |
| `parkin` | không | `0` | `WAITING_REVIEWED_ROOT_ID_MAPPING` | `BLOCKED_NO_MANUAL_IMPORT` |
| `dj1` | không | `0` | `NOT_MAPPABLE_FROM_PAPER` | `BLOCKED_NO_MANUAL_IMPORT` |
| `lrrk2` | không | `0` | `WAITING_VNC_CONNECTOME_MAPPING` | `BLOCKED_NO_MANUAL_IMPORT` |

## Có thể đạt 5/5 approved ngay không?

**Không.** Package hiện không chứa export mapping condition-specific có root ID/edge ID thật và reviewer signoff tương ứng cho cả năm condition. Vì vậy hệ thống giữ `0/5`, không tạo ID tổng hợp và không nâng trạng thái bằng suy luận.

Để một condition được tính là approved, cần đồng thời có identifier thật, cell type/class, driver hoặc anatomy scope, connectome version, source URL, query/export source, SHA-256 của artifact, reviewer_2, review_date, signoff hợp lệ và YAML condition đã có target/provenance/burden tương thích.

## Dữ liệu cần bổ sung

1. Một file `codex_export.csv`, `flywire_export.tsv` hoặc `paper_mapping_evidence.csv` cho từng condition, theo đúng schema trong query plan.
2. `reviewer_signoff.json` do reviewer thật điền, không dùng tên/ngày giả.
3. SHA-256 của export và provenance của nguồn; không commit nguyên dump lớn nếu chỉ cần filtered export.
4. Mapping VNC/motor-neuron tương thích cho LRRK2 nếu muốn mở rộng ngoài brain-only scope.

## Gate kế tiếp

Chỉ sau khi có import hợp lệ và signoff, chạy lại script này với kiểm tra audit. Nếu có condition approved nhưng YAML còn thiếu burden/provenance, condition vẫn bị chặn khỏi disease rollout.

## Ranh giới khoa học

Gate 20C chỉ là cổng thu nhận và kiểm tra provenance mapping. Nó không phải xác nhận cơ chế bệnh, không tạo disease metrics, không thay thế thí nghiệm trên ruồi thật và không phải công cụ chẩn đoán hay đánh giá thuốc.
