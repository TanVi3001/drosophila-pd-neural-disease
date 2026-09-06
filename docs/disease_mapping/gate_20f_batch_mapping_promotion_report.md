# Gate 20F: Batch mapping promotion report

## Muc tieu va gioi han

Gate 20F kiem tra lai bon condition con lai sau Gate 20E va chi nang cap
condition neu co bang chung mapping that, provenance day du va
`reviewer_signoff.json` hop le. Gate nay khong tao root ID/edge ID, khong suy
ra neuron tu ten gene va khong thay the review cua nguoi.

Khong co GPU, simulation, calibration, tuning hoac sua raw metrics duoc thuc
hien trong gate nay.

## Trang thai bat dau

Sau Gate 20E, Parkin da duoc duyet o pham vi class-level exploratory:

- `reviewer_2`: `To Dang Minh Tuan`
- `review_date`: `2026-09-07`
- `decision`: `APPROVED_FOR_CLASS_LEVEL_EXPLORATORY`
- `mapping_level`: `DRIVER_OR_CLASS_LEVEL`
- `gene_specific_mapping`: `false`
- `allowed_rollout_scope`: `CLASS_LEVEL_EXPLORATORY_ONLY`
- 330 root ID tu export FlyWire/Codex da duoc review

Trang thai bat dau cua Gate 20F la `1/5` condition duoc duyet.

## Ket qua audit batch

| Condition | Manual import | Signoff | Ket qua | Ly do |
|---|---|---|---|---|
| `parkin` | Co `codex_export.csv` | Co, da duyet | `APPROVED` | Mapping DAN class-level co root ID that; khong phai mapping gene-specific |
| `alpha_synuclein` | Chi co README | Khong co | `BLOCKED_NO_MANUAL_IMPORT` | Pan-neuronal reference khong phai target root-ID da review |
| `pink1` | Chi co README | Khong co | `BLOCKED_NO_MANUAL_IMPORT` | Whole-animal mutant khong xac dinh neuron/edge can thiep |
| `dj1` | Chi co README | Khong co | `BLOCKED_NO_MANUAL_IMPORT` | Phenotype hanh vi khong cung cap mapping neuron/edge |
| `lrrk2` | Chi co README | Khong co | `BLOCKED_NO_MANUAL_IMPORT` | Can mapping VNC/motor-neuron; catalog hien tai la brain-only |

Khong co condition nao trong bon condition con lai du dieu kien de promote.
Khong co file `reviewer_signoff.json` moi, khong co root ID/edge ID moi va
khong co YAML mapping moi duoc tao. Vi vay ket qua duoc giu trung thuc:

```text
approved_condition_count = 1/5
all_five_conditions_approved = false
status = MAPPING_ACQUISITION_READY
disease_mapping_status = READY_FOR_STEP_06
```

`READY_FOR_STEP_06` chi co nghia la pipeline mapping co it nhat mot condition
exploratory da review va san sang cho buoc tiep theo trong pham vi duoc phep.
No khong dong nghia ca 5 condition da co mapping va khong cho phep goi
Parkin la gene-specific.

## Bang chung va provenance

Bang chung Parkin da co tu Gate 20E duoc bao toan, gom:

- `research/disease_mapping/manual_imports/parkin/codex_export.csv`
- `research/disease_mapping/manual_imports/parkin/reviewer_signoff.json`
- `research/disease_mapping/exports/parkin/source_manifest.json`
- `configs/conditions/parkin.template.yaml`

Bon condition chua duoc promote van chi co cac source manifest reference-only
trong `research/disease_mapping/exports/<condition>/`. Cac file do ghi ro
khong co condition-specific export va khong co identifier. Day la ly do
khong the dung chung lam evidence de approve.

## Co dat 5/5 khong?

Khong. Gate 20F dat `1/5`; khong co du lieu that de hop le hoa viec nang cap
alpha-synuclein, PINK1, DJ-1 hoac LRRK2. De mot condition duoc promote sau
nay, nhom phai bo sung export that, source URL, query/export source, connectome
version, SHA256, signoff nguoi review thu hai, ngay review, YAML target va
burden/provenance tuong ung. LRRK2 con can dung pham vi VNC/motor-neuron.

## Bien khoa hoc

This gate promotes only evidence-supported mapping readiness. It does not
establish biological Parkinson validation, gene-specific disease validation,
clinical validation, drug validation, or disease mechanism validation.
