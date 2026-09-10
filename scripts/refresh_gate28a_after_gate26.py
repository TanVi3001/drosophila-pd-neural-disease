"""Refresh Gate28A provenance artifacts after Gate26 canonical closure."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/gate_28a_gen2_scope_metric_study_split"
MAIN_COMMIT = "cbd1ca071b2a8f28983d1cb78096501847fefbc1"
ORIGINAL_GATE28A_COMMIT = "2dafaafc5a09eca1908457a54d8a0a5dc4e45b24"
V2_INVENTORY = "experiments/gate_26_riemensperger_full_completion/manifests/reproducibility_inventory_v2_git_blob.json"
GATE26_SIGNOFF = ROOT / "research/validation/prospective/gate26_reproducibility_canonicalization_reviewer_signoff.json"
GATE28_SIGNOFF = ROOT / "research/validation/prospective/gate28a_gen2_scope_metric_study_split_reviewer_signoff.json"


def canonical_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(canonical_bytes(path)).hexdigest()


def write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_blob(ref: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "blob", f"{ref}:{path}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout


def verify_gate26() -> tuple[int, list[str]]:
    document = json.loads(
        (ROOT / V2_INVENTORY).read_text(encoding="utf-8")
    )
    failures: list[str] = []
    for record in document["records"]:
        blob = git_blob("HEAD", record["path"])
        if hashlib.sha256(blob).hexdigest() != record["sha256"]:
            failures.append(record["path"])
        if len(blob) != record["size_bytes"]:
            failures.append(f"size:{record['path']}")
    return len(document["records"]), failures


def update_gate26_recheck() -> None:
    legacy = json.loads(
        (GATE / "manifests/gate26_legacy_checksum_audit.json").read_text(encoding="utf-8")
    )
    signoff = json.loads(GATE26_SIGNOFF.read_text(encoding="utf-8"))
    required_signoff = {
        "status": "GATE26_REPRODUCIBILITY_CANONICALIZATION_REVIEW_APPROVED",
        "decision": "APPROVED_GATE26_REPRODUCIBILITY_CANONICALIZATION_CLOSURE",
        "gate26_reconciliation_closed": True,
    }
    for key, value in required_signoff.items():
        if signoff.get(key) != value:
            raise ValueError(f"Gate26 signoff is not approved/closed: {key}")
    count, failures = verify_gate26()
    if failures or count != 37:
        raise ValueError(f"Gate26 canonical verifier failed: {failures}")
    write_json(GATE / "manifests/gate26_canonical_recheck.json", {
        "schema_version": "gate28a-gate26-canonical-recheck-v1",
        "status": "GATE26_CANONICAL_RECHECK_PASS",
        "checked_against_main": MAIN_COMMIT,
        "legacy_inventory_record_count": legacy["record_count"],
        "legacy_mismatch_count": legacy["mismatch_count"],
        "legacy_mismatch_status": "EXPLAINED_PLATFORM_SERIALIZATION_HISTORY",
        "canonical_inventory": V2_INVENTORY.rsplit("/", 1)[-1],
        "canonical_record_count": count,
        "canonical_verified_count": count,
        "canonical_verification_pass": True,
        "canonical_policy": "GIT_BLOB_BYTES",
        "canonical_reconciliation_status": "HUMAN_APPROVED_CLOSED",
        "canonical_reconciliation_commit": MAIN_COMMIT,
        "unexplained_content_drift": False,
        "scientific_evidence_changed": False,
        "gate26_result": "NOT_REPRODUCED",
        "gate26_result_changed": False,
        "original_gate28a_commit": ORIGINAL_GATE28A_COMMIT,
    })


def update_manifest() -> None:
    path = GATE / "manifests/gate28a_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest.update({
        "source_main_commit": MAIN_COMMIT,
        "full_repository_regression_status": "PASS",
        "legacy_evidence_reconciliation_status": "RESOLVED_CANONICAL_GIT_BLOB_V2",
        "gate26_changed": False,
        "gate26_reproducibility_inventory_records": 37,
        "gate26_reproducibility_37_of_37": True,
        "gate26_checksum_mismatch_count": 11,
        "gate26_checksum_mismatch_scope": "LEGACY_PRECANONICAL_WORKTREE_INVENTORY",
        "gate26_legacy_checksum_mismatch_count": 11,
        "gate26_canonical_checksum_mismatch_count": 0,
        "gate26_canonical_verified_count": 37,
        "gate26_canonical_record_count": 37,
        "gate26_canonical_reconciliation_closed": True,
        "gate26_result": "NOT_REPRODUCED",
        "gate26_result_changed": False,
        "retuning": False,
        "gate28b_execution": False,
    })
    write_json(path, manifest)


def update_report() -> None:
    report = """# Báo cáo xác nhận Gate 28A sau canonicalization Gate26

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
"""
    (ROOT / "docs/research_design/gate28a_gen2_validation_report.md").write_text(report, encoding="utf-8")


def refresh_inventory() -> None:
    prefixes = [
        ROOT / "configs/generation2",
        ROOT / "docs/research_design",
        ROOT / "docs/claims/generation2_claim_policy.md",
        ROOT / "docs/claims/claim_document_scope_audit.md",
        ROOT / "research/literature_v2",
        GATE,
        ROOT / "research/validation/prospective/gate28a_gen2_scope_metric_study_split_reviewer_signoff.json",
        ROOT / "results/duration_comparability_audit.csv",
        ROOT / "results/walking_speed_semantic_audit.csv",
        ROOT / "results/public_personal_path_audit.csv",
        ROOT / "scripts/build_gate28a_contract_artifacts.py",
        ROOT / "scripts/refresh_gate28a_after_gate26.py",
        ROOT / "tests/test_gate28a_gen2_scientific_contract.py",
    ]
    files: set[Path] = set()
    for prefix in prefixes:
        if prefix.is_file():
            files.add(prefix)
        elif prefix.is_dir():
            files.update(path for path in prefix.rglob("*") if path.is_file())
    files = {
        path for path in files
        if not path.name in {"checksums.sha256", "reproducibility_inventory.json"}
        and path.suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg", ".mp4", ".npz", ".pt"}
    }
    records = [
        {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path), "size_bytes": len(canonical_bytes(path))}
        for path in sorted(files)
    ]
    inventory = {
        "schema_version": "gate28a-reproducibility-inventory-v2-git-blob-compatible",
        "status": "COMPLETE_CANONICAL_TEXT_BYTES",
        "record_count": len(records),
        "raw_gpu_artifacts_included": False,
        "canonical_policy": "GIT_BLOB_BYTES",
        "records": records,
    }
    inventory_path = GATE / "manifests/reproducibility_inventory.json"
    write_json(inventory_path, inventory)
    inventory_sha = sha256(inventory_path)
    lines = [f"{record['sha256']}  {record['path']}" for record in records]
    lines.append(f"{inventory_sha}  {inventory_path.relative_to(ROOT).as_posix()}")
    (GATE / "manifests/checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"record_count": len(records), "inventory_sha256": inventory_sha}, indent=2))


def main() -> None:
    update_gate26_recheck()
    update_manifest()
    update_report()
    refresh_inventory()
    review = json.loads(GATE28_SIGNOFF.read_text(encoding="utf-8"))
    if review["status"] != "WAITING_GATE28A_GEN2_HUMAN_REVIEW" or review["gate28a_closed"] is not False:
        raise ValueError("Gate28A human review must remain pending")


if __name__ == "__main__":
    main()
