from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "experiments/gate_17a_final_report"
SUMMARY = REPORT_ROOT / "results/final_report_summary.json"
MANIFEST = REPORT_ROOT / "manifests/final_report_manifest.json"


def test_gate17a_report_files_exist() -> None:
    for relative in (
        "docs/report/final_vietnamese_report.md",
        "docs/report/final_report_short_summary.md",
        "docs/report/final_report_outline.md",
        "experiments/gate_17a_final_report/results/final_report_summary.json",
        "experiments/gate_17a_final_report/manifests/final_report_manifest.json",
    ):
        assert (ROOT / relative).is_file(), relative


def test_gate17a_summary_is_vietnamese_and_claim_safe() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["status"] == "FINAL_REPORT_READY"
    assert summary["language"] == "vi"
    assert summary["base_release_tag"] == "v1.0.0"
    assert summary["claim_lock_active"] is True
    assert summary["key_results"] == {
        "chen_selected_burden": 0.5,
        "chen_target_ratio": 0.6701030927835051,
        "gate13c_confirmation_ratio": 0.6142225784195846,
        "pozo_control_distance_mm": 1.66679,
        "pozo_holdout_distance_mm": 1.57846,
        "pozo_simulated_ratio": 0.947,
        "pozo_target_ratio": 0.192,
        "directionality_pass": True,
        "quantitative_ratio_match": False,
    }
    assert "organism-level computational locomotion proxy" in summary["final_claim"]
    assert "directional Pozo holdout concordance" in summary["final_claim"]
    assert "quantitative ratio mismatch" in summary["final_claim"]
    assert summary["no_new_simulation_run"] is True
    assert summary["no_calibration_run"] is True
    assert summary["no_tuning_run"] is True
    assert summary["no_raw_metric_modification"] is True
    assert summary["boundaries"] == {
        "biological_validation": False,
        "gene_specific_validation": False,
        "clinical_validation": False,
        "drug_validation": False,
        "therapeutic_validation": False,
    }


def test_gate17a_manifest_records_provenance() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["status"] == "FINAL_REPORT_READY"
    assert manifest["claim_lock_active"] is True
    assert manifest["large_artifacts_committed"] is False
    assert manifest["no_new_simulation_run"] is True
    assert manifest["no_calibration_run"] is True
    assert manifest["no_tuning_run"] is True
    assert manifest["no_raw_metric_modification"] is True
    assert manifest["source_files"] == [
        "docs/claims/current_claim_lock.md",
        "docs/release/final_project_claim.md",
        "docs/release/release_notes_v1.0.0.md",
        "docs/project_summary.md",
        "docs/limitations.md",
        "docs/results_timeline.md",
        "experiments/gate_16a_final_release/results/final_release_summary.json",
        "experiments/gate_14c_holdout_adjudication/results/holdout_adjudication_summary.json",
    ]
    assert set(manifest["sha256"]) == {
        "docs/report/final_vietnamese_report.md",
        "docs/report/final_report_short_summary.md",
        "docs/report/final_report_outline.md",
        "docs/claims/current_claim_lock.md",
        "docs/release/final_project_claim.md",
    }


def test_gate17a_report_has_required_results_and_boundaries() -> None:
    text = (ROOT / "docs/report/final_vietnamese_report.md").read_text(encoding="utf-8")
    for phrase in (
        "4.875 mm/s",
        "7.275 mm/s",
        "0.6701030927835051",
        "0.5",
        "0.6142225784",
        "0.9470",
        "0.1920",
        "12/12",
        "0.5 giây",
        "directional concordance",
        "không phải biological Parkinson validation",
        "không phải gene-specific validation",
    ):
        assert phrase in text


def test_gate17a_no_positive_overclaim_in_report() -> None:
    text = "\n".join(
        (ROOT / relative).read_text(encoding="utf-8").lower()
        for relative in (
            "docs/report/final_vietnamese_report.md",
            "docs/report/final_report_short_summary.md",
        )
    )
    for phrase in (
        "biologically validated",
        "clinically validated",
        "drug efficacy",
        "therapeutic efficacy",
        "proves parkinson",
        "gene-specific validation achieved",
        "quantitatively validated",
        "biological parkinson validation achieved",
        "mô hình đã chứng minh parkinson sinh học",
    ):
        assert phrase not in text
