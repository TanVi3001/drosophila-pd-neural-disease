# Gate 26 Submission Package

**Status:** `SUBMISSION_PACKAGE_READY_FOR_INTERNAL_REVIEW`

Package nay dong goi manuscript draft, figures, tables va checksum cua evidence
da khoa den Gate 25. No phu hop cho internal review hoac mot computational-proxy
manuscript/preprint workflow; khong phai bang chung Parkinson sinh hoc,
gene-specific, lam sang hay dieu tri.

## Kiem tra doc lap

```powershell
py -3.12 scripts/verify_gate26_submission_package.py
py -3.12 scripts/audit_calibration_targets.py
py -3.12 -m compileall -q src scripts tests
py -3.12 -m pytest -q -rs -p no:cacheprovider
git diff --check
```

Khong can GPU de kiem tra package. Chi cai `.[analysis]` neu can tao lai PNG
cua Gate 24 tu dau.
