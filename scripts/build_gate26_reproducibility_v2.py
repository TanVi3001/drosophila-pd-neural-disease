"""Build canonical Gate26 provenance metadata from exact Git blob bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "353ba33eb635138dcee5a65819e8f723d7448efc"
PREVIOUS_COMMIT = "c1babdd71d3cfbc7d376c18b156cef2661109abd"
GATE = ROOT / "experiments/gate_26_riemensperger_full_completion"
LEGACY_INVENTORY = GATE / "manifests/reproducibility_inventory.json"
LEGACY_CHECKSUMS = GATE / "manifests/checksums.sha256"
RECONCILIATION = GATE / "reconciliation/gate26_legacy_byte_diagnosis.json"
V2_INVENTORY = GATE / "manifests/reproducibility_inventory_v2_git_blob.json"
V2_CHECKSUMS = GATE / "manifests/checksums_v2_git_blob.sha256"
AMENDMENT = GATE / "manifests/gate26_reproducibility_canonicalization_amendment.json"
REVIEW = ROOT / "research/validation/prospective/gate26_reproducibility_canonicalization_reviewer_signoff.json"
MIXED_PATH = "docs/replications/riemensperger_2011/riemensperger_2011_pipeline_completion_update.md"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def git_blob(ref: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "blob", f"{ref}:{path}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def line_variants(data: bytes) -> tuple[bytes, bytes, bytes, int, int, int]:
    if b"\x00" in data:
        return data, data, data, 0, 0, 0
    parts = data.split(b"\n")
    newline_count = len(parts) - 1
    lf = b"\n".join(parts)
    uniform_crlf = b"\r\n".join(parts)
    mixed = b"".join(
        part + (b"\r\n" if index < newline_count - 1 else b"\n")
        for index, part in enumerate(parts[:-1])
    ) + parts[-1]
    return lf, uniform_crlf, mixed, newline_count, max(newline_count - 1, 0), 1 if newline_count else 0


def classify(recorded: str, canonical: str, current: str, lf: str, crlf: str, mixed: str, path: str) -> str:
    if recorded == canonical:
        return "EXACT_LEGACY_MATCH"
    if current != canonical:
        return "WORKTREE_DIFFERS_FROM_GIT_BLOB"
    if recorded == crlf:
        return "UNIFORM_CRLF_WORKTREE_SERIALIZATION"
    if path == MIXED_PATH and recorded == mixed:
        return "MIXED_CRLF_FINAL_LF_WORKTREE_SERIALIZATION"
    if recorded == lf:
        return "LEGACY_HASH_MATCHES_LF_VARIANT"
    return "CONTENT_DRIFT_NOT_EXPLAINED_BY_EOL"


def load_legacy_records() -> list[dict]:
    document = json.loads(LEGACY_INVENTORY.read_text(encoding="utf-8"))
    if document["record_count"] != 37 or len(document["records"]) != 37:
        raise ValueError("Legacy Gate26 inventory is not exactly 37 records")
    return document["records"]


def build(source_commit: str) -> dict:
    records = load_legacy_records()
    diagnosis_records: list[dict] = []
    canonical_records: list[dict] = []
    for record in records:
        path = record["path"]
        canonical = git_blob(source_commit, path)
        current = (ROOT / path).read_bytes()
        lf, crlf, mixed, newline_count, internal_crlf_count, final_lf_count = line_variants(canonical)
        canonical_sha = digest(canonical)
        current_sha = digest(current)
        classification = classify(record["sha256"], canonical_sha, current_sha, digest(lf), digest(crlf), digest(mixed), path)
        semantic_equal = classification in {
            "EXACT_LEGACY_MATCH",
            "UNIFORM_CRLF_WORKTREE_SERIALIZATION",
            "MIXED_CRLF_FINAL_LF_WORKTREE_SERIALIZATION",
            "LEGACY_HASH_MATCHES_LF_VARIANT",
        }
        diagnosis_records.append({
            "path": path,
            "legacy_recorded_sha256": record["sha256"],
            "canonical_git_blob_sha256": canonical_sha,
            "current_worktree_sha256": current_sha,
            "legacy_size_bytes": record["size_bytes"],
            "git_blob_size_bytes": len(canonical),
            "working_tree_size_bytes": len(current),
            "lf_variant_sha256": digest(lf),
            "crlf_variant_sha256": digest(crlf),
            "mixed_crlf_final_lf_variant_sha256": digest(mixed),
            "newline_count": newline_count,
            "internal_crlf_count": internal_crlf_count,
            "final_lf_count": final_lf_count,
            "classification": classification,
            "semantic_content_equal": semantic_equal,
        })
        canonical_records.append({
            "path": path,
            "sha256": canonical_sha,
            "size_bytes": len(canonical),
            "source_commit": source_commit,
            "byte_source": "GIT_BLOB",
        })

    mismatches = [item for item in diagnosis_records if item["classification"] != "EXACT_LEGACY_MATCH"]
    unexplained = [item for item in mismatches if not item["semantic_content_equal"]]
    uniform = [item for item in mismatches if item["classification"] == "UNIFORM_CRLF_WORKTREE_SERIALIZATION"]
    mixed = [item for item in mismatches if item["classification"] == "MIXED_CRLF_FINAL_LF_WORKTREE_SERIALIZATION"]
    root_cause = "GATE26_LEGACY_WORKTREE_EOL_CANONICALIZATION_MISMATCH" if not unexplained else "GEN1_RECONCILIATION_BLOCKED_UNEXPLAINED_CONTENT_DRIFT"

    previous = git_blob(PREVIOUS_COMMIT, MIXED_PATH)
    previous_crlf = b"\r\n".join(previous.split(b"\n"))
    historical_corroboration = {
        "commit": PREVIOUS_COMMIT,
        "path": MIXED_PATH,
        "source_newline_count": previous.count(b"\n"),
        "all_crlf_size_bytes": len(previous_crlf),
        "all_crlf_sha256": digest(previous_crlf),
        "expected_all_crlf_size_bytes": 1985,
        "expected_all_crlf_sha256": "9aa804853b7a07fad24eeb2886117f347e351b69450b2d2ad37e05981c59fd3b",
        "matches_expected": len(previous_crlf) == 1985 and digest(previous_crlf) == "9aa804853b7a07fad24eeb2886117f347e351b69450b2d2ad37e05981c59fd3b",
    }
    if not historical_corroboration["matches_expected"]:
        raise ValueError("Historical CRLF corroboration did not match the continuation task")

    write_json(RECONCILIATION, {
        "schema_version": "gate26-legacy-byte-diagnosis-v2",
        "source_commit": source_commit,
        "legacy_inventory_status": "LEGACY_PRECANONICAL_WORKTREE_BYTE_INVENTORY",
        "record_count": len(diagnosis_records),
        "mismatch_count": len(mismatches),
        "uniform_crlf_worktree_serialization_count": len(uniform),
        "mixed_crlf_final_lf_serialization_count": len(mixed),
        "unexplained_content_drift_count": len(unexplained),
        "unexplained_content_drift": bool(unexplained),
        "semantic_content_drift": bool(unexplained),
        "root_cause": root_cause,
        "historical_corroboration": historical_corroboration,
        "records": diagnosis_records,
    })
    write_json(V2_INVENTORY, {
        "schema_version": "gate26-reproducibility-inventory-v2-git-blob",
        "status": "COMPLETE_CANONICAL_GIT_BLOB",
        "record_count": len(canonical_records),
        "source_commit": source_commit,
        "records": canonical_records,
    })
    V2_CHECKSUMS.write_text("".join(f"{record['sha256']}  {record['path']}\n" for record in canonical_records), encoding="utf-8")
    write_json(AMENDMENT, {
        "schema_version": "gate26-reproducibility-canonicalization-amendment-v1",
        "status": "GATE26_REPRODUCIBILITY_CANONICALIZATION_PROPOSED",
        "source_commit": source_commit,
        "legacy_inventory_status": "LEGACY_PRECANONICAL_WORKTREE_BYTE_INVENTORY",
        "legacy_inventory_path": str(LEGACY_INVENTORY.relative_to(ROOT)).replace("\\", "/"),
        "legacy_inventory_sha256": file_digest(LEGACY_INVENTORY),
        "legacy_checksums_path": str(LEGACY_CHECKSUMS.relative_to(ROOT)).replace("\\", "/"),
        "legacy_checksums_sha256": file_digest(LEGACY_CHECKSUMS),
        "legacy_record_count": len(records),
        "legacy_mismatch_count": len(mismatches),
        "uniform_crlf_worktree_serialization_count": len(uniform),
        "mixed_crlf_final_lf_serialization_count": len(mixed),
        "unexplained_content_drift_count": len(unexplained),
        "canonical_v2_inventory_path": str(V2_INVENTORY.relative_to(ROOT)).replace("\\", "/"),
        "canonical_v2_inventory_sha256": file_digest(V2_INVENTORY),
        "canonical_v2_checksums_path": str(V2_CHECKSUMS.relative_to(ROOT)).replace("\\", "/"),
        "canonical_v2_checksums_sha256": file_digest(V2_CHECKSUMS),
        "root_cause": root_cause,
        "scientific_evidence_modified": False,
        "scientific_result_changed": False,
        "execution_freeze_changed": False,
        "simulation_rerun": False,
        "gpu_used": False,
        "retuning": False,
        "reason": "cross_platform_repository_byte_canonicalization",
        "canonical_explanation": "Gate26 legacy reproducibility hashes were generated from platform-specific pre-commit working-tree bytes. Ten mismatches reproduce under uniform CRLF serialization; the completion-update artifact reproduces exactly under a mixed serialization containing 34 CRLF separators and a final LF separator. The committed semantic contents remain unchanged. Generation-1 canonical reproducibility is therefore amended to hash exact Git blob bytes.",
        "human_approval": "PENDING_HUMAN_REVIEW",
    })
    write_json(REVIEW, {
        "schema_version": "gate26-reproducibility-canonicalization-review-v1",
        "status": "WAITING_GATE26_REPRODUCIBILITY_CANONICALIZATION_HUMAN_REVIEW",
        "decision": "PENDING_HUMAN_REVIEW",
        "root_cause_approved": False,
        "legacy_inventory_preservation_approved": False,
        "canonical_git_blob_policy_approved": False,
        "v2_inventory_approved": False,
        "v2_checksums_approved": False,
        "scientific_evidence_unchanged_approved": False,
        "gate26_result_unchanged_approved": False,
        "gate26_reconciliation_closed": False,
        "reviewer_1": "",
        "reviewer_2": "",
        "review_date": "",
        "no_auto_sign": True,
    })
    return {"record_count": len(diagnosis_records), "mismatch_count": len(mismatches), "uniform_crlf_count": len(uniform), "mixed_crlf_count": len(mixed), "unexplained_count": len(unexplained), "root_cause": root_cause}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default=SOURCE_COMMIT)
    args = parser.parse_args()
    result = build(args.ref)
    print(json.dumps(result, indent=2))
    return 2 if result["unexplained_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
