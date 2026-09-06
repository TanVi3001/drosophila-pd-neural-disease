# Kế hoạch truy vấn Codex/FlyWire cho Gate 20C

## Mục đích

Tài liệu này quy định cách thu thập **filtered export** có thể kiểm tra lại cho năm condition bệnh. Gate 20C không tự đoán root ID từ tên gene, driver, phenotype hoặc cell class.

## Nguồn tham khảo được phép

- FlyWire annotations: <https://github.com/flyconnectome/flywire_annotations>
- Codex FAQ và hướng dẫn provenance: <https://codex.flywire.ai/faq>
- Paper/supplementary đã được nhóm review, nếu paper thật sự chỉ rõ mapping.

Không commit nguyên connectivity dump lớn. Chỉ lưu export đã lọc, câu truy vấn, ngày xuất, người xuất, phiên bản connectome và SHA-256.

## Từ khóa cần ghi lại

| Condition | Query scope tối thiểu | Cảnh báo |
| --- | --- | --- |
| `alpha_synuclein` | driver/expression scope, cell class, brain/VNC scope | pan-neuronal không tự thành gene-specific root-ID set |
| `pink1` | genotype và neural intervention scope | whole-animal mutant không tự xác định neuron target |
| `parkin` | TH-GAL4 hoặc driver scope, cell type và version | phải phân biệt class-level với gene-specific |
| `dj1` | neural intervention nếu paper có nêu rõ | behavioral phenotype không đủ để suy root ID |
| `lrrk2` | motor-neuron/VNC scope và connectome tương thích | brain-only catalog không thay thế VNC mapping |

## Schema export bắt buộc

CSV/TSV phải có các cột:

```text
condition_id,root_id,edge_id,cell_type,cell_class,driver_scope,
anatomy_scope,connectome_name,connectome_version,source_url,
query_string,query_date,exported_by,notes
```

Để được xét approved, mỗi artifact phải có `source_sha256` là SHA-256 64 ký tự của nguồn/export tương ứng (có thể bổ sung thành cột trong file). Mỗi dòng phải có root ID hoặc edge ID thật; dòng placeholder sẽ bị loại.

## Quy trình lưu file

1. Lưu một trong `manual_imports/<condition>/codex_export.csv`, `flywire_export.tsv` hoặc `paper_mapping_evidence.csv`.
2. Lưu `reviewer_signoff.json` cùng thư mục.
3. Không sửa Gate 20B export reference-only để làm bằng chứng mới.
4. Chạy `py -3.12 scripts/import_gate20c_mapping_signoff.py`.
5. Chỉ sau khi kết quả được reviewer kiểm tra mới thực hiện promotion ở gate riêng.

## Provenance tối thiểu trong signoff

Signoff cần ghi `condition_id`, `reviewer_1`, `reviewer_2`, `review_date`, `decision`, `mapping_level`, `gene_specific_mapping`, `allowed_rollout_scope` và `human_notes`. Quyết định hợp lệ chỉ là `APPROVED`, `APPROVED_FOR_CLASS_LEVEL_EXPLORATORY`, `REJECTED` hoặc `PENDING_HUMAN_SIGNOFF`.
