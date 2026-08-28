# Calibration readiness

Tai lieu nay mo ta cong cu kiem tra readiness truoc khi chay calibration.
No khong them scientific algorithm, khong tu phe duyet literature va khong
chay FlyGym simulation.

## Luong xu ly

```text
targets.csv
    |
    v
audit_calibration_targets.py
    |
    +--> INVALID_TARGET_SCHEMA
    +--> WAITING_TARGET_DATA
    +--> READY_FOR_CALIBRATION
```

Audit kiem tra:

- schema va cac cot bat buoc;
- review status hop le;
- value la so huu han;
- provenance, assay, metric, don vi va metadata;
- duplicate target;
- reviewer va ngay review;
- phan bo rieng calibration va holdout.

Audit khong tu dong dien target, khong suy ra sample size/variance, khong
chuyen doi assay va khong sua `targets.csv`.

## Trang thai hien tai

Hai target mau da duoc ghi trong `calibration_targets/targets.csv` nhung dang
o trang thai `pending`. Vi vay calibration phai dung o `WAITING_TARGET_DATA`.
Day la execution gate co chu y, khong phai loi runtime.

## Cach chay

```powershell
py -3.12 scripts/audit_calibration_targets.py --targets calibration_targets/targets.csv --output results/calibration_readiness
```

File tao ra trong output:

- `target_audit.json`: ket qua may doc duoc;
- `target_audit.csv`: loi/canh bao theo tung dong;
- `calibration_manifest.json`: danh sach target calibration va holdout duoc phep dung;
- `target_audit.md`: tom tat de research lead review.

## Dieu kien calibration

`READY_FOR_CALIBRATION` chi duoc tra khi co target `approved`, du metadata,
co provenance review, co allocation `calibration` va co it nhat mot target
`holdout`. Target dung cho calibration khong duoc lap lai trong holdout.

Ngay ca khi readiness PASS, ket qua van chi la computational locomotion
matching. No khong phai biological Parkinson validation, chan doan, du doan
lam sang hay danh gia thuoc.
