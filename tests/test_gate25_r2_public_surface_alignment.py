"""Regression tests for the Gate25-R2.1 public claim-surface alignment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_gate25_r2_reproducibility_freeze import (
    EXPECTED_FINAL_EVIDENCE_SHA256,
    EXPECTED_RAW_TREE_SHA256,
    EXPECTED_VIRTUAL_FREEZE_SHA256,
    HISTORICAL_REPORT,
    HISTORICAL_REPORT_SHA256,
    PREVIOUS_R2_FREEZE_SHA256,
    REFRESH_REASON,
    ARCHIVE_RUNS,
    FREEZE_PATH,
    audit,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_current_claim_lock_reflects_closed_gate24e() -> None:
    claim_lock = _read("docs/claims/current_claim_lock.md")
    for phrase in (
        "GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE",
        "NEGATIVE_VALIDATION_RESULT",
        "DIRECTIONAL_CROSS_ASSAY_DISCORDANCE",
        "BIOLOGICAL_IMPAIRMENT_SUPPORTED",
        "biologically validated Parkinson model",
        "gene-specific biological validation",
        "quantitative cross-assay equivalence",
        "Historical Chen/Pozo track",
    ):
        assert phrase in claim_lock
    assert "driver-defined neural target != Parkin-expression-specific root mapping" in claim_lock


def test_readme_current_status_matches_gate24e_and_links_r2() -> None:
    readme = _read("README.md")
    gate24e = _json("experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_final_validation_decision.json")
    assert "## Current research status" in readme
    assert gate24e["status"] in readme
    assert gate24e["scientific_result"] in readme
    assert gate24e["cross_assay_decision"] in readme
    assert "## Current Parkin prospective-validation track" in readme
    assert "## Historical organism-level proxy track - Chen / Pozo" in readme
    assert "docs/reproducibility/gate25_r2_parkin_reproducibility_freeze_report.md" in readme
    assert "not public Git data" in readme


def test_historical_evidence_remains_present_and_unchanged() -> None:
    assert HISTORICAL_REPORT.is_file()
    assert sha256_file(HISTORICAL_REPORT) == HISTORICAL_REPORT_SHA256
    for relative in (
        "experiments/gate_13b_chen_ratio_calibration",
        "experiments/gate_14b_pozo_holdout_validation",
        "docs/holdout/gate_14c_holdout_adjudication_report.md",
    ):
        assert (ROOT / relative).exists(), relative


def test_r2_refresh_records_provenance_without_changing_science() -> None:
    if not ARCHIVE_RUNS.is_dir():
        pytest.skip("external Gate24E raw archive is not distributed in GitHub Actions")
    result = audit()
    freeze = _json("experiments/gate_25_r2_parkin_reproducibility/manifests/gate25_r2_reproducibility_freeze.json")
    assert result["status"] == "GATE25_R2_REPRODUCIBILITY_FREEZE_COMPLETE"
    assert freeze["previous_gate25_r2_freeze_sha256"] == PREVIOUS_R2_FREEZE_SHA256
    assert freeze["refresh_reason"] == REFRESH_REASON
    assert freeze["scientific_result_changed"] is False
    assert freeze["gate24e_evidence_changed"] is False
    assert freeze["raw_archive_changed"] is False
    assert freeze["locked_identifiers"]["final_evidence_freeze_sha256"] == EXPECTED_FINAL_EVIDENCE_SHA256
    assert freeze["locked_identifiers"]["virtual_prediction_freeze_sha256"] == EXPECTED_VIRTUAL_FREEZE_SHA256
    assert freeze["locked_identifiers"]["raw_runs_tree_sha256"] == EXPECTED_RAW_TREE_SHA256
    assert FREEZE_PATH.is_file()


def test_r2_remains_file_only_and_raw_archive_is_not_public() -> None:
    freeze = _json("experiments/gate_25_r2_parkin_reproducibility/manifests/gate25_r2_reproducibility_freeze.json")
    assert freeze["gpu"] is False
    assert freeze["simulation"] is False
    assert freeze["raw_archive_policy"]["publicly_available"] is False
