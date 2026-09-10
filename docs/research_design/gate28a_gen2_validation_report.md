# Gate 28A Generation 2 Validation Report

## Kết quả contract

- Status: `GATE28A_GEN2_SCIENTIFIC_CONTRACT_COMPLETE`.
- Human review: `WAITING_GATE28A_GEN2_HUMAN_REVIEW`.
- GPU: không chạy.
- Simulation: không chạy.
- Model fitting: không chạy.
- Calibration: không chạy.
- Data fabrication: không có.

Các test riêng của Gate 28A pass. Các artifact mới chỉ là contract, registry,
audit, manifest và checksum nhẹ.

## Blocker kế thừa được phát hiện

Gate26 inventory có đủ 37 record, nhưng checksum audit tại thời điểm Gate28A
cho thấy 11 record không khớp với file đang ở `origin/main`. Gate28A không
sửa các file lịch sử và không cập nhật checksum lịch sử để ép kết quả thành
37/37. Chi tiết được lưu tại:

`experiments/gate_28a_gen2_scope_metric_study_split/manifests/gate26_legacy_checksum_audit.json`

Vì vậy:

```text
gate26_reproducibility_37_of_37 = false
legacy_evidence_reconciliation_status = BLOCKED_STALE_INVENTORY
```

## Kiểm tra hiện tại

- Gate25 verify-only: PASS.
- Compileall: PASS.
- Gate28A contract tests: PASS.
- `git diff --check`: PASS.
- Full pytest: `669 passed, 2 skipped, 1 failed`.
- Failure hiện tại nằm ở checksum artifact Generation 1 trong
  `tests/test_riemensperger2011_reproducibility.py`, không phải artifact mới
  của Gate28A.

## Quyết định

Không được chuyển sang Gate28B hoặc human signoff cuối cùng cho tới khi nhóm
quyết định riêng cách reconcile checksum lịch sử. Việc reconcile đó phải là
một task được review độc lập; không được sửa raw metrics, kết luận khoa học,
checkpoint hoặc claim lock trong Gate28A.
