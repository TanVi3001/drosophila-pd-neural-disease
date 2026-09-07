# Gate 25: Reproducibility Freeze

**Trang thai:** `REPRODUCIBILITY_FREEZE_COMPLETE`

## Muc dich

Gate 25 khoa compact evidence package da duoc su dung den Gate 24. Gate nay chi
doc, kiem tra va bam SHA256 artifact; khong chay GPU, FlyGym simulation,
calibration, holdout validation hoac tuning.

## Evidence anchor

- Ngay khoa: `2026-09-07`.
- Main evidence anchor: `73ca686`.
- Artifact trong inventory: `24` tep duy nhat.
- Gate 23 giu ket qua `POZO_HOLDOUT_MISMATCH`.
- Gate 24 giu `gene_specific_validation=false` va
  `biological_parkinson_validation=false`.

## Cach tai lap kiem tra

```powershell
py -3.12 scripts/audit_calibration_targets.py
py -3.12 scripts/run_gate25_reproducibility_freeze.py
py -3.12 -m compileall -q src scripts tests
py -3.12 -m pytest -q -rs -p no:cacheprovider
git diff --check
```

Neu can tao lai figure Gate 24, cai optional analysis extra bang
`py -3.12 -m pip install -e ".[analysis]"` truoc khi chay script Gate 24.

## Claim lock

Duoc phep: Chen-calibrated organism-level computational locomotion proxy with directional Pozo holdout concordance and substantial quantitative ratio mismatch.

Khong duoc dien giai ket qua nay nhu biological Parkinson validation,
gene-specific validation, clinical validation, drug efficacy validation hoac
quantitatively validated holdout model. Pozo chi dat directional concordance;
mismatch dinh luong duoc giu nguyen.

## Tiet kiem dung luong

Inventory khong dua video, checkpoint, rollout NPZ hay artifact raw lon vao
release evidence package. Cac tep raw neu can luu tru phai co checksum/provenance
rieng va co the luu o kho luu tru ngoai repository.
