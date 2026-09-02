from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "experiments" / "gate_15b_release_bundle"
SUMMARY = BUNDLE / "results" / "release_bundle_summary.json"
MANIFEST = BUNDLE / "manifests" / "release_bundle_manifest.json"


def test_gate15b_bundle_files_exist() -> None:
    for relative in (
        "docs/release/submission_bundle.md",
        "docs/release/reviewer_quickstart.md",
        "docs/release/reproducibility_checklist.md",
        "docs/release/key_artifacts_index.md",
        "docs/release/final_project_claim.md",
        "scripts/prepare_release_submission_bundle.py",
        "experiments/gate_15b_release_bundle/results/release_bundle_summary.json",
        "experiments/gate_15b_release_bundle/manifests/release_bundle_manifest.json",
    ):
        assert (ROOT / relative).is_file(), relative


def test_gate15b_summary_is_claim_safe_and_ready() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["status"] == "RELEASE_BUNDLE_READY"
    assert summary["claim_lock_active"] is True
    assert summary["no_new_simulation_run"] is True
    assert summary["no_calibration_run"] is True
    assert summary["no_tuning_run"] is True
    assert summary["no_raw_metric_modification"] is True
    assert "organism-level computational locomotion proxy" in summary["final_claim"]
    assert "directional Pozo holdout concordance" in summary["final_claim"]
    assert "quantitative ratio mismatch" in summary["final_claim"]
    assert summary["key_statuses"] == {
        "chen_ratio_calibration": "CHEN_RATIO_CALIBRATION_PASS",
        "chen_confirmation": "CHEN_CALIBRATED_CONFIRMATION_PASS",
        "pozo_runtime": "POZO_HOLDOUT_RUNTIME_PASS",
        "holdout_adjudication": "DIRECTIONAL_CONCORDANCE_WITH_QUANTITATIVE_MISMATCH",
    }


def test_gate15b_manifest_records_boundaries_and_source_hashes() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["status"] == "RELEASE_BUNDLE_READY"
    assert manifest["claim_lock_active"] is True
    assert manifest["no_new_simulation_run"] is True
    assert manifest["no_calibration_run"] is True
    assert manifest["no_tuning_run"] is True
    assert manifest["no_raw_metric_modification"] is True
    assert manifest["large_artifacts_committed"] is False
    assert len(manifest["sha256"]) == 8
    assert "README.md" in manifest["source_files"]
    assert "docs/claims/current_claim_lock.md" in manifest["source_files"]
    assert "docs/release/final_project_claim.md" in manifest["generated_files"]


def test_gate15b_key_artifact_index_covers_prior_gates() -> None:
    index = (ROOT / "docs/release/key_artifacts_index.md").read_text(encoding="utf-8")
    for phrase in ("Gate 13B", "Gate 13C", "Gate 14B", "Gate 14C", "Gate 15B"):
        assert phrase in index


def test_gate15b_release_docs_do_not_make_positive_overclaims() -> None:
    text = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in sorted((ROOT / "docs/release").glob("*.md"))
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
