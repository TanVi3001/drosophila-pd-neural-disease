from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE_ROOT = ROOT / "experiments" / "gate_14c_holdout_adjudication"
SUMMARY = GATE_ROOT / "results" / "holdout_adjudication_summary.json"
CLAIM_TABLE = GATE_ROOT / "results" / "claim_lock_table.csv"
MANIFEST = GATE_ROOT / "manifests" / "holdout_adjudication_manifest.json"


def test_gate14c_artifacts_exist() -> None:
    paths = [
        ROOT / "scripts" / "adjudicate_pozo_holdout_claims.py",
        SUMMARY,
        CLAIM_TABLE,
        MANIFEST,
        ROOT / "docs" / "holdout" / "gate_14c_holdout_adjudication_report.md",
        ROOT / "docs" / "claims" / "current_claim_lock.md",
    ]
    for path in paths:
        assert path.is_file(), path


def test_gate14c_summary_locks_directional_mismatch() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    result = summary["pozo_holdout_result"]
    assert summary["status"] == "HOLDOUT_ADJUDICATION_COMPLETE"
    assert (
        summary["final_adjudication_status"]
        == "DIRECTIONAL_CONCORDANCE_WITH_QUANTITATIVE_MISMATCH"
    )
    assert result["planned_runs"] == 12
    assert result["successful_runs"] == 12
    assert result["condition_id"] == "pink1"
    assert result["scope"] == "organism_level_proxy"
    assert result["directionality_pass"] is True
    assert result["quantitative_ratio_match"] is False
    assert result["simulated_distance_ratio"] == 0.9470070897697126
    assert result["pozo_target_ratio"] == 0.19203837612811836


def test_gate14c_no_execution_or_overclaim_flags() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for payload in (summary, manifest):
        assert payload["no_calibration_run"] is True
        assert payload["no_parameter_reselection"] is True
        assert payload["no_pozo_tuning"] is True
        assert payload["no_gene_specific_mapping"] is True
        assert payload["no_biological_validation_claim"] is True
    assert manifest["no_new_simulation_run"] is True
    assert manifest["no_gate14b_raw_result_modification"] is True
    assert summary["claim_lock"]["biological_validation"] is False
    assert summary["claim_lock"]["gene_specific_validation"] is False
    assert summary["claim_lock"]["clinical_validation"] is False
    assert summary["claim_lock"]["drug_validation"] is False
    assert summary["claim_lock"]["quantitative_pozo_validation"] is False


def test_gate14c_claim_table_has_all_required_rows() -> None:
    with CLAIM_TABLE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["claim"] for row in rows} == {
        "Chen calibration",
        "Chen confirmation",
        "Pozo runtime",
        "Pozo directionality",
        "Pozo quantitative ratio",
        "Biological validation",
        "Gene-specific validation",
        "Clinical/drug claim",
    }
    statuses = {row["claim"]: row["status"] for row in rows}
    assert statuses["Pozo quantitative ratio"] == "mismatch_reported"
    assert statuses["Biological validation"] == "forbidden"
    assert statuses["Gene-specific validation"] == "forbidden"
    assert statuses["Clinical/drug claim"] == "forbidden"


def test_gate14c_claim_lock_does_not_make_forbidden_positive_claims() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    primary = summary["claim_lock"]["allowed_primary_claim"].lower()
    forbidden_positive_phrases = (
        "biological parkinson validation",
        "gene-specific validation",
        "clinical validation",
        "drug efficacy",
        "quantitatively validated",
    )
    for phrase in forbidden_positive_phrases:
        assert phrase not in primary
