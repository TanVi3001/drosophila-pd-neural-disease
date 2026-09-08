"""Regression checks for the read-only Gate 24E-S4F cleanup package."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "experiments"
    / "gate_24e_storage_probe"
    / "manifests"
    / "storage_cleanup_reconciliation.json"
)
SIGNOFF = (
    ROOT
    / "research"
    / "validation"
    / "prospective"
    / "gate24e_storage_cleanup_reviewer_signoff.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_s4f_stays_read_only_and_storage_blocked() -> None:
    manifest = _load(MANIFEST)

    assert manifest["status"] == "WAITING_STORAGE_CLEANUP_REVIEW"
    assert manifest["required_bytes"] == 17_548_739_588
    assert manifest["current_capacity_pass"] is False
    assert manifest["deletion_authorized"] is False
    assert manifest["scientific_jobs_executed"] == 0
    assert manifest["scientific_batch_authorized"] is False
    assert manifest["holdout"] == "SEALED"
    assert manifest["holdout_opened"] is False


def test_s4f_inventory_preserves_canonical_groups_and_gate24e_evidence() -> None:
    manifest = _load(MANIFEST)
    groups = {item["canonical_status"]: item for item in manifest["candidate_groups"]}

    assert set(groups) == {
        "CANONICAL_GATE_EVIDENCE",
        "DERIVED_REPRODUCIBILITY_PACKAGE",
        "HISTORICAL_MOVEMENT_VERIFICATION_EVIDENCE",
    }
    assert groups["CANONICAL_GATE_EVIDENCE"]["total_bytes"] == 4_704_802_797
    assert groups["DERIVED_REPRODUCIBILITY_PACKAGE"]["total_bytes"] == 3_935_172_359
    assert groups["HISTORICAL_MOVEMENT_VERIFICATION_EVIDENCE"]["total_bytes"] == 2_816_614_089

    protected = tuple(manifest["protected_paths"])
    listed_files = []
    for group in manifest["candidate_groups"]:
        listed_files.extend(group["archive_eligible_files"])
        listed_files.extend(group["delete_eligible_files"])
        listed_files.extend(group["unknown_files"])

    for path in listed_files:
        assert not any(protected_path in path for protected_path in protected)
        assert "attempt_04" not in path
        assert "attempt_05" not in path


def test_s4f_cleanup_options_require_human_review() -> None:
    manifest = _load(MANIFEST)
    options = manifest["cleanup_options"]

    assert set(options) == {
        "OPTION_A_LOW_RISK",
        "OPTION_B_MODERATE",
        "OPTION_C_MAXIMUM_SAFE_AFTER_ARCHIVE",
    }
    assert manifest["recommended_option"] == "OPTION_B_MODERATE"
    assert options["OPTION_B_MODERATE"]["capacity_pass"] is True
    assert manifest["projected_capacity_pass"] is True
    assert manifest["projected_free_after_cleanup"] == 19_964_367_493
    assert manifest["recommended_reclaim_bytes"] == 6_726_320_773


def test_s4f_signoff_remains_scientifically_closed_after_human_approval() -> None:
    signoff = _load(SIGNOFF)

    assert signoff["status"] == "STORAGE_CLEANUP_REVIEW_APPROVED"
    assert signoff["decision"] == "APPROVED_OPTION_B_MODERATE"
    assert len(signoff["approved_paths"]) == 2
    assert signoff["approved_action"] == (
        "EXTERNAL_ARCHIVE_VERIFY_SHA256_THEN_DELETE_LOCAL_APPROVED_SUBSET_ONLY"
    )
    assert signoff["scientific_contract_changed"] is False
    assert signoff["scientific_jobs_executed"] == 0
    assert signoff["scientific_batch_authorized"] is False
    assert signoff["holdout"] == "SEALED"
    assert signoff["holdout_opened"] is False
