# Báo cáo xác nhận Gate 28A sau canonicalization Gate26

## Trạng thái

- `GATE28A_GEN2_SCIENTIFIC_CONTRACT_COMPLETE`
- `WAITING_GATE28A_GEN2_HUMAN_REVIEW`
- `NO ACTIVE GENERATION-1 REPRODUCIBILITY BLOCKER`

Gate 28A vẫn là một scientific contract cho Generation 2. Task này không chạy
GPU, simulation, fitting, calibration hoặc retuning; Gate28B cũng chưa được
triển khai.

## Reconciliation Gate26

Ở lần tạo Gate28A ban đầu, legacy inventory của Gate26 có 37 record và ghi
nhận 11 mismatch. Audit lịch sử đó được giữ nguyên tại
`manifests/gate26_legacy_checksum_audit.json` và không bị xoá hoặc sửa lịch sử.

Một task provenance độc lập sau đó đã kiểm tra raw Git blob và giải thích toàn
bộ 11 mismatch:

- 10 trường hợp là `UNIFORM_CRLF_WORKTREE_SERIALIZATION`;
- 1 trường hợp là `MIXED_CRLF_FINAL_LF_WORKTREE_SERIALIZATION`;
- 0 trường hợp content drift không giải thích được.

Gate26 canonical v2 dùng byte của Git blob, đạt 37/37 và đã được human review
approved/closed trên `main`. Kết quả khoa học Gate26 vẫn là `NOT_REPRODUCED`;
canonicalization không thay đổi kết quả, evidence hoặc execution freeze.

## Nội dung khoa học được giữ nguyên

Gate28A giữ nguyên Generation-2 scope, metric dictionary, duration policy,
experimental-unit contract, assay registry, literature registry, study split,
claim policy và các audit metric ban đầu. Các số audit vẫn là:

- metric occurrences: 6059;
- walking-speed occurrences: 440;
- ambiguous walking-speed occurrences: 418;
- assay contracts: 5;
- literature registry records: 13.

Pozo 2022 vẫn là `HISTORICAL_EXPOSED_EVALUATION_SOURCE`, không phải future
sealed holdout. Riemensperger 2011 vẫn là
`GEN2_DOPAMINE_FUNCTIONAL_DEFICIENCY_REFERENCE`. Alpha-synuclein LOSO vẫn
`NOT_YET_FROZEN`.

## Giới hạn và phê duyệt

Gate28A chưa phải biological Parkinson validation, gene-specific validation,
clinical validation hay drug validation. Gate28A human signoff vẫn để pending;
không được chuyển sang Gate28B chỉ dựa trên refresh provenance này.
