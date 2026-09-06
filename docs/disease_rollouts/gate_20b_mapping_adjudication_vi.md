# Gate 20B: Adjudication mapping gene-specific

Gate 20B là cổng review trước disease neural-first. Mục tiêu là kiểm tra mapping neuron/edge theo từng condition có bằng chứng truy lại được, không phải tạo ID tự động.

## Cách chạy

```powershell
py -3.12 scripts/run_gate20b_mapping_adjudication.py
py -3.12 scripts/audit_disease_mapping_readiness.py
```

## Kết quả hiện tại

Gate hiện trả `MAPPING_REVIEW_BLOCKED`, `0/5` mapping được `APPROVED`. Đây là kết quả đúng vì hồ sơ hiện tại chưa có export root-ID/edge-ID không rỗng cho từng gene.

| Condition | Trạng thái | Lý do chính |
| --- | --- | --- |
| alpha-synuclein | `WAITING_REVIEWED_ROOT_ID_MAPPING` | Pan-neuronal/DA scope chưa có export root-ID được duyệt. |
| PINK1 | `MODEL_SCOPE_NOT_CELL_SPECIFIC` | Paper mô tả whole-animal mutant, không chỉ ra neuron subset. |
| Parkin | `WAITING_REVIEWED_ROOT_ID_MAPPING` | TH-GAL4 là driver class; chưa có export TH-to-FlyWire được review. |
| DJ-1 | `NOT_MAPPABLE_FROM_PAPER` | Phenotype hành vi không đủ để suy ra root ID. |
| LRRK2 | `NOT_MAPPABLE_TO_CURRENT_CONNECTOME` | Cần phạm vi motor neuron/VNC, trong khi nguồn hiện tại brain-only. |

## Hồ sơ cần bổ sung

Mỗi condition cần file export identifier thật, cell type/scope, driver scope, phiên bản FlyWire/connectome, nguồn export/query, reviewer thứ hai và ngày review. `mapping_identifier_count=0` phải giữ nguyên cho đến khi file export đó tồn tại và được kiểm tra.

Không được dùng 342 dopamine IDs làm mapping gene-specific cho các gene khác. Không chuyển whole-animal genotype hoặc behavioral phenotype thành neural target.

## Artifact

- `experiments/gate_20b_mapping_adjudication/results/mapping_adjudication.md`;
- `experiments/gate_20b_mapping_adjudication/manifests/mapping_adjudication_manifest.json`;
- `research/disease_mapping/gene_specific_mapping_review.csv`.

Chỉ sau khi Gate 20B và Gate 20A cùng mở mới được materialize disease branch và chạy multi-seed. Gate này không chạy simulation, calibration hoặc holdout.
