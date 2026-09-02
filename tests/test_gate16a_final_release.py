from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = ROOT / "experiments" / "gate_16a_final_release"
SUMMARY = RELEASE_ROOT / "results" / "final_release_summary.json"
MANIFEST = RELEASE_ROOT / "manifests" / "final_release_manifest.json"


def test_gate16a_release_files_exist() -> None:
    for relative in (
        "docs/release/release_notes_v1.0.0.md",
        "docs/release/final_release_checklist.md",
        "experiments/gate_16a_final_release/results/final_release_summary.json",
        "experiments/gate_16a_final_release/manifests/final_release_manifest.json",
    ):
        assert (ROOT / relative).is_file(), relative


def test_gate16a_summary_is_ready_and_claim_safe() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["status"] == "FINAL_RELEASE_READY"
    assert summary["release_version"] == "v1.0.0"
    assert summary["claim_lock_active"] is True
    assert summary["release_bundle_ready"] is True
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
        "quantitative_pozo_validation": False,
    }


def test_gate16a_manifest_records_release_provenance() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["status"] == "FINAL_RELEASE_READY"
    assert manifest["release_version"] == "v1.0.0"
    assert manifest["claim_lock_active"] is True
    assert manifest["large_artifacts_committed"] is False
    assert manifest["no_new_simulation_run"] is True
    assert manifest["no_calibration_run"] is True
    assert manifest["no_tuning_run"] is True
    assert manifest["no_raw_metric_modification"] is True
    assert set(manifest["sha256"]) == {
        "README.md",
        "docs/release/submission_bundle.md",
        "docs/release/reviewer_quickstart.md",
        "docs/release/reproducibility_checklist.md",
        "docs/release/key_artifacts_index.md",
        "docs/release/final_project_claim.md",
        "docs/claims/current_claim_lock.md",
        "docs/release/release_notes_v1.0.0.md",
        "docs/release/final_release_checklist.md",
    }


def test_gate16a_release_docs_do_not_use_positive_overclaims() -> None:
    text = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in (
            ROOT / "docs/release/release_notes_v1.0.0.md",
            ROOT / "docs/release/final_release_checklist.md",
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
    ):
        assert phrase not in text
