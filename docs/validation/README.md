# Gate 22 validation ladder

Gate 22 tách Track A (Riemensperger 2011 dopamine-class computational
replication) khỏi Track B (Parkin gene-specific and biological validation).

Trạng thái hiện tại được audit tự động và dừng ở
`WAITING_BIOLOGICAL_VALIDATION_DATA`. Parkin class-level root IDs không được
dùng lại làm gene-specific mapping. Không có dữ liệu wet-lab hay biological
holdout nào được tạo trong repository.

Chạy audit:

```powershell
py -3.12 scripts/audit_gene_specific_validation_readiness.py
```
