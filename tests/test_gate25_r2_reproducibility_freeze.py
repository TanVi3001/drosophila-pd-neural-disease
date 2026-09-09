"""Regression tests for the closed Gate24E Gate25-R2 reproducibility freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.run_gate25_r2_reproducibility_freeze import (
    ANCHOR_COMMIT,
    EXPECTED_FINAL_EVIDENCE_SHA256,
    EXPECTED_RAW_TREE_SHA256,
    EXPECTED_RUNTIME_COMMIT,
    EXPECTED_VIRTUAL_FREEZE_SHA256,
    FREEZE_PATH,
    HISTORICAL_REPORT,
    HISTORICAL_REPORT_SHA256,
    INVENTORY_PATH,
    ReproducibilityFreezeError,
    audit,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_gate25_r2_audit_is_complete_and_file_only() -> None:
    result = audit()
    assert result["status"] == "GATE25_R2_REPRODUCIBILITY_FREEZE_COMPLETE"
    assert result["gate24e_final_status"] == "GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE"
    assert result["gpu"] is False
    assert result["simulation"] is False


def test_historical_gate25_is_preserved_and_old_r2_can_coexist() -> None:
    assert sha256_file(HISTORICAL_REPORT) == HISTORICAL_REPORT_SHA256
    assert HISTORICAL_REPORT != FREEZE_PATH
    assert HISTORICAL_REPORT.is_file()
    assert FREEZE_PATH.is_file()


def test_exact_gate24e_closure_identifiers_are_locked() -> None:
    freeze = _json(FREEZE_PATH)
    assert freeze["locked_identifiers"]["final_evidence_freeze_sha256"] == EXPECTED_FINAL_EVIDENCE_SHA256
    assert freeze["locked_identifiers"]["virtual_prediction_freeze_sha256"] == EXPECTED_VIRTUAL_FREEZE_SHA256
    assert freeze["locked_identifiers"]["raw_runs_tree_sha256"] == EXPECTED_RAW_TREE_SHA256
    assert freeze["locked_identifiers"]["runtime_commit"] == EXPECTED_RUNTIME_COMMIT


def test_inventory_is_deterministic_and_changes_invalidate_r2() -> None:
    inventory = _json(INVENTORY_PATH)
    paths = [item["path"] for item in inventory["files"]]
    assert paths == sorted(paths)
    assert len(paths) == len(set(paths))
    altered = dict(inventory["files"][0])
    altered["sha256"] = "0" * 64
    target = ROOT / altered["path"]
    assert target.is_file()
    with pytest.raises(ReproducibilityFreezeError, match="Inventory checksum changed"):
        from scripts.run_gate25_r2_reproducibility_freeze import _verify_inventory

        _verify_inventory({"files": [altered]})


def test_raw_archive_is_external_not_public() -> None:
    inventory = _json(INVENTORY_PATH)
    freeze = _json(FREEZE_PATH)
    assert inventory["raw_archive"]["committed_to_git"] is False
    assert inventory["raw_archive"]["publicly_available"] is False
    assert freeze["raw_archive_policy"]["publicly_available"] is False
    assert inventory["raw_archive"]["file_count"] == 275
    assert inventory["raw_archive"]["total_bytes"] == 13958129260


def test_checksum_manifest_is_sorted_and_excludes_itself() -> None:
    checksums = ROOT / "experiments/gate_25_r2_parkin_reproducibility/manifests/checksums.sha256"
    lines = checksums.read_text(encoding="utf-8").splitlines()
    paths = [line.split("  ", maxsplit=1)[1] for line in lines]
    assert paths == sorted(paths)
    assert len(paths) == len(set(paths))
    assert "experiments/gate_25_r2_parkin_reproducibility/manifests/checksums.sha256" not in paths
    for line in lines:
        digest, path = line.split("  ", maxsplit=1)
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


def test_negative_result_and_claim_boundary_are_preserved() -> None:
    freeze = _json(FREEZE_PATH)
    assert freeze["scientific_result"] == "NEGATIVE_VALIDATION_RESULT"
    assert freeze["cross_assay_decision"] == "DIRECTIONAL_CROSS_ASSAY_DISCORDANCE"
    assert freeze["biological_validation_supported"] is False
    assert "biologically validated Parkinson model" in freeze["claim_boundary"]["forbidden"]


def test_anchor_commit_is_the_post_relocation_content_commit() -> None:
    inventory = _json(INVENTORY_PATH)
    assert inventory["anchor_commit"] == ANCHOR_COMMIT
