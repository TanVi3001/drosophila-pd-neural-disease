"""Regression tests for the Gate 26 manuscript submission package."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.build_gate26_submission_package import DEFAULT_CONFIG, DEFAULT_EXPERIMENT, DEFAULT_PACKAGE, _read_config, build_submission_package
from scripts.verify_gate26_submission_package import verify

ROOT = Path(__file__).resolve().parents[1]


def test_gate26_is_analysis_only_and_claim_safe() -> None:
    config = _read_config(DEFAULT_CONFIG)
    assert config["analysis_only"] is True
    assert all(
        config[key] is False
        for key in ("run_gpu", "run_simulation", "run_calibration", "run_holdout_validation", "run_tuning")
    )
    assert "biological Parkinson validation" in config["claim_lock"]["forbidden_positive_claims"]


def test_gate26_builds_claim_safe_manuscript_and_tables() -> None:
    manifest = build_submission_package()
    assert manifest["status"] == "SUBMISSION_PACKAGE_READY_FOR_INTERNAL_REVIEW"
    assert manifest["boundaries"]["biological_parkinson_validation"] is False
    assert manifest["boundaries"]["gene_specific_validation"] is False
    assert manifest["artifact_count"] >= 20

    manuscript = (DEFAULT_PACKAGE / "manuscript_vi.md").read_text(encoding="utf-8")
    assert "quantitatively mismatched" in manuscript
    normalized_manuscript = " ".join(manuscript.split())
    assert "not a biological, gene-specific, clinical, or therapeutic validation" in normalized_manuscript
    with (DEFAULT_PACKAGE / "tables/table_01_evidence_scope.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert any(row["result"] == "Directional PASS; quantitative MISMATCH" for row in rows)
    assert len(list((DEFAULT_PACKAGE / "figures").glob("*.png"))) == 5


def test_gate26_independent_verification_passes_and_preserves_boundaries() -> None:
    result = verify()
    assert result["status"] == "INDEPENDENT_REPRODUCIBILITY_CHECK_PASS"
    assert result["checked_artifacts"] >= 20
    summary = json.loads((DEFAULT_EXPERIMENT / "results/submission_readiness.json").read_text(encoding="utf-8"))
    assert summary["pozo_quantitative_ratio"] == "MISMATCH"
    assert summary["ready_for_biological_parkinson_claim"] is False
