# Tai lap Gate 25

Thu muc nay ghi lai cach kiem tra tinh toan ven cua evidence package dung cho
Gate 24. No khong chay GPU, FlyGym, calibration, holdout validation hay tuning.

Tu repository root, chay:

```powershell
py -3.12 scripts/audit_calibration_targets.py
py -3.12 scripts/run_gate25_reproducibility_freeze.py
py -3.12 -m compileall -q src scripts tests
py -3.12 -m pytest -q -rs -p no:cacheprovider
git diff --check
```

Kiem tra `experiments/gate_25_reproducibility_freeze/manifests/checksums.sha256`
bang SHA256 cho moi tep duoc freeze. `freeze_inventory.csv` liet ke scope,
trang thai va checksum cua moi artifact. Khong coi package nay la biological
Parkinson validation hay gene-specific validation.
