# Handoff mapping gene-specific

Hồ sơ `research/disease_mapping/gene_specific_mapping_review.csv` là bảng kiểm soát để bổ sung mapping neuron/edge cho năm condition disease. Nó không tự tạo root ID và không coi tên gene, genotype hoặc phenotype là bằng chứng cho một tập neuron cụ thể.

## Trạng thái hiện tại

Chạy:

```powershell
py -3.12 scripts/audit_gene_specific_mapping_review.py
```

Kết quả hiện tại là `MAPPING_REVIEW_BLOCKED`, với `0/5` mapping được `APPROVED` và tất cả record có `mapping_identifier_count=0`. Đây là trạng thái chủ ý vì repo chưa có export root-ID/edge-ID gene-specific được reviewer xác nhận.

| Condition | Kết luận hiện tại | Không được làm |
| --- | --- | --- |
| alpha-synuclein | `WAITING_REVIEWED_ROOT_ID_MAPPING` | Không lấy toàn bộ neuron hoặc dopamine class làm mapping gene-specific. |
| PINK1 | `MODEL_SCOPE_NOT_CELL_SPECIFIC` | Không biến genotype whole-animal thành một tập neuron. |
| Parkin | `WAITING_REVIEWED_ROOT_ID_MAPPING` | Không tự coi toàn bộ TH-GAL4 class là mapping đã duyệt. |
| DJ-1 | `NOT_MAPPABLE_FROM_PAPER` | Không suy ra root ID từ climbing/behavioral phenotype. |
| LRRK2 | `NOT_MAPPABLE_TO_CURRENT_CONNECTOME` | Không dùng brain-only annotation thay cho motor neuron/VNC. |

## Điều kiện để bổ sung mapping thật

Mỗi condition cần một file export có:

- root ID hoặc edge ID cụ thể;
- cell type và driver scope;
- phiên bản FlyWire/connectome;
- nguồn export hoặc query có thể truy lại;
- reviewer và ngày review;
- quyết định `APPROVED` hoặc trạng thái từ chối rõ ràng.

Sau khi có file đó, reviewer cập nhật record tương ứng, chạy audit mapping và Gate 20A. Chỉ condition vượt cả mapping audit và condition-config audit mới được mở sang disease multi-seed.

## Ranh giới khoa học

Handoff này chỉ xác nhận tính đầy đủ của hồ sơ mapping. Nó không phải gene-specific biological model, biological Parkinson validation, chẩn đoán, thử thuốc hoặc bằng chứng thay thế thí nghiệm trên ruồi thật.
