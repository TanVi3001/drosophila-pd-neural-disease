"""Regression checks for the completed Gate 24E-S4G cleanup."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "experiments/gate_24e_storage_probe/manifests/s4g_cleanup_execution.json"
VERIFICATION = ROOT / "experiments/gate_24e_storage_probe/manifests/s4g_archive_verification.json"
PREFLIGHT = ROOT / "experiments/gate_24e_storage_probe/manifests/s4g_archive_preflight.json"
SIGNOFF = ROOT / "research/validation/prospective/gate24e_storage_cleanup_reviewer_signoff.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_s4g_archive_and_deletion_are_complete_and_verified() -> None:
    execution = _load(MANIFEST)
    verification = _load(VERIFICATION)
    preflight = _load(PREFLIGHT)

    assert execution["status"] == "GATE24E_STORAGE_CAPACITY_RESOLVED"
    assert execution["archive_verified"] is True
    assert execution["selected_file_count"] == 1148
    assert execution["selected_total_bytes"] == 6_726_320_773
    assert execution["deleted_file_count"] == 1148
    assert execution["deleted_total_bytes"] == 6_726_320_773
    assert execution["free_after"] > execution["required_bytes"]
    assert execution["must_keep_preserved"] is True
    assert execution["gate11_preserved"] is True
    assert execution["attempt04_rollout_unchanged"] is True
    assert execution["scientific_plan_unchanged"] is True

    assert verification["verification_status"] == "PASS"
    assert verification["files_verified"] == 1148
    assert verification["bytes_verified"] == 6_726_320_773
    assert verification["hash_mismatches"] == []
    assert preflight["selected_file_count"] == 1148
    assert preflight["selected_total_bytes"] == 6_726_320_773

    for record in execution["deleted_files"]:
        assert not Path(record["source_path"]).exists()


def test_s4g_preserves_scientific_firewall_and_locked_hashes() -> None:
    execution = _load(MANIFEST)
    signoff = _load(SIGNOFF)

    assert execution["scientific_jobs_executed"] == 0
    assert execution["scientific_batch_authorized"] is False
    assert execution["holdout"] == "SEALED"
    assert execution["holdout_opened"] is False
    assert execution["gpu_executed"] is False
    assert execution["simulation_executed"] is False
    assert execution["attempt04_rollout_sha256_before"] == (
        "23ab2861c884b49bcb5402d854c2f6bf0ebe093337d2b66454f4f9a3a7c9389b"
    )
    assert execution["attempt04_rollout_sha256_after"] == execution["attempt04_rollout_sha256_before"]
    assert execution["scientific_plan_sha256_before"] == (
        "4515e1916631b019711154dccb5fb887110d5572e3eb82b7ea5118c643db5aac"
    )
    assert execution["scientific_plan_sha256_after"] == execution["scientific_plan_sha256_before"]

    assert signoff["status"] == "STORAGE_CLEANUP_REVIEW_APPROVED"
    assert signoff["decision"] == "APPROVED_OPTION_B_MODERATE"
    assert signoff["approved_action"] == (
        "EXTERNAL_ARCHIVE_VERIFY_SHA256_THEN_DELETE_LOCAL_APPROVED_SUBSET_ONLY"
    )
