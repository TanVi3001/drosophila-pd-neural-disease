import hashlib
import json
import subprocess
from pathlib import Path

from scripts.verify_gate26_reproducibility_v2 import verify


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/gate_26_riemensperger_full_completion"
INVENTORY = GATE / "manifests/reproducibility_inventory.json"
CHECKSUMS = GATE / "manifests/checksums.sha256"
V2_INVENTORY = GATE / "manifests/reproducibility_inventory_v2_git_blob.json"
V2_CHECKSUMS = GATE / "manifests/checksums_v2_git_blob.sha256"
DIAGNOSIS = GATE / "reconciliation/gate26_legacy_byte_diagnosis.json"
AMENDMENT = GATE / "manifests/gate26_reproducibility_canonicalization_amendment.json"
SIGNOFF = ROOT / "research/validation/prospective/gate26_reproducibility_canonicalization_reviewer_signoff.json"
SOURCE_COMMIT = "353ba33eb635138dcee5a65819e8f723d7448efc"


def _git_blob(path: str, ref: str = "HEAD") -> bytes:
    return subprocess.run(["git", "cat-file", "blob", f"{ref}:{path}"], cwd=ROOT, stdout=subprocess.PIPE, check=True).stdout


def test_canonical_inventory_is_complete_and_uses_git_blobs() -> None:
    document = json.loads(V2_INVENTORY.read_text(encoding="utf-8"))
    assert document["status"] == "COMPLETE_CANONICAL_GIT_BLOB"
    assert document["source_commit"] == SOURCE_COMMIT
    assert document["record_count"] == 37
    assert len(document["records"]) == 37
    assert all(record["byte_source"] == "GIT_BLOB" for record in document["records"])
    assert all(record["source_commit"] == SOURCE_COMMIT for record in document["records"])


def test_canonical_checksums_match_git_blobs() -> None:
    document = json.loads(V2_INVENTORY.read_text(encoding="utf-8"))
    lines = V2_CHECKSUMS.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 37
    expected = {record["path"]: record["sha256"] for record in document["records"]}
    observed = {}
    for line in lines:
        digest, path = line.split("  ", 1)
        observed[path] = digest
        assert hashlib.sha256(_git_blob(path)).hexdigest() == digest
    assert observed == expected


def test_verifier_passes_against_head() -> None:
    assert verify("HEAD") == (37, [])
    result = subprocess.run(["python", "scripts/verify_gate26_reproducibility_v2.py", "--ref", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
    assert "GATE26_CANONICAL_REPRODUCIBILITY_PASS" in result.stdout
    assert "verified_records=37/37" in result.stdout


def test_diagnosis_explains_all_legacy_mismatches_without_semantic_drift() -> None:
    document = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    assert document["record_count"] == 37
    assert document["mismatch_count"] == 11
    assert document["uniform_crlf_worktree_serialization_count"] == 10
    assert document["mixed_crlf_final_lf_serialization_count"] == 1
    assert document["unexplained_content_drift_count"] == 0
    assert document["semantic_content_drift"] is False
    assert document["root_cause"] == "GATE26_LEGACY_WORKTREE_EOL_CANONICALIZATION_MISMATCH"
    records = document["records"]
    assert sum(item["classification"] == "UNIFORM_CRLF_WORKTREE_SERIALIZATION" for item in records) == 10
    assert sum(item["classification"] == "MIXED_CRLF_FINAL_LF_WORKTREE_SERIALIZATION" for item in records) == 1
    assert all(item["semantic_content_equal"] for item in records)
    assert all(item["current_worktree_sha256"] == item["canonical_git_blob_sha256"] for item in records)


def test_legacy_manifests_are_preserved_and_only_new_reconciliation_is_added() -> None:
    legacy = json.loads(INVENTORY.read_text(encoding="utf-8"))
    assert legacy["record_count"] == 37
    assert len(CHECKSUMS.read_text(encoding="utf-8").splitlines()) == 37
    changed = subprocess.run(["git", "diff", "--name-only", "origin/main...HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    gate26_evidence_or_provenance = [
        path for path in changed
        if path.startswith("experiments/gate_26_riemensperger_full_completion/")
        or path == "research/validation/prospective/gate26_reproducibility_canonicalization_reviewer_signoff.json"
        or path in {
            "scripts/build_gate26_reproducibility_v2.py",
            "scripts/verify_gate26_reproducibility_v2.py",
            "tests/test_riemensperger2011_reproducibility.py",
        }
    ]
    assert gate26_evidence_or_provenance == [], gate26_evidence_or_provenance


def test_amendment_and_signoff_keep_scientific_and_human_locks() -> None:
    amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    assert amendment["status"] == "GATE26_REPRODUCIBILITY_CANONICALIZATION_PROPOSED"
    assert amendment["legacy_record_count"] == 37
    assert amendment["legacy_mismatch_count"] == 11
    assert amendment["unexplained_content_drift_count"] == 0
    for field in ("scientific_evidence_modified", "scientific_result_changed", "execution_freeze_changed", "simulation_rerun", "gpu_used", "retuning"):
        assert amendment[field] is False
    signoff = json.loads(SIGNOFF.read_text(encoding="utf-8"))
    assert signoff["status"] == "GATE26_REPRODUCIBILITY_CANONICALIZATION_REVIEW_APPROVED"
    assert signoff["decision"] == "APPROVED_GATE26_REPRODUCIBILITY_CANONICALIZATION_CLOSURE"
    assert signoff["no_auto_sign"] is True
    assert signoff["gate26_reconciliation_closed"] is True
