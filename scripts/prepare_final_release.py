"""Prepare the Gate 16A reviewer-ready release artifacts.

This script reads and verifies prior gate artifacts and writes only the new
Gate 16A summary and manifest. It does not run simulation, calibration,
tuning, or modify historical metrics/manifests.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = ROOT / "experiments" / "gate_16a_final_release"
SUMMARY_PATH = RELEASE_ROOT / "results" / "final_release_summary.json"
MANIFEST_PATH = RELEASE_ROOT / "manifests" / "final_release_manifest.json"

RELEASE_BUNDLE_SUMMARY = (
    ROOT
    / "experiments"
    / "gate_15b_release_bundle"
    / "results"
    / "release_bundle_summary.json"
)
HOLDOUT_SUMMARY = (
    ROOT
    / "experiments"
    / "gate_14c_holdout_adjudication"
    / "results"
    / "holdout_adjudication_summary.json"
)

REQUIRED_INPUTS = [
    ROOT / "docs" / "release" / "submission_bundle.md",
    ROOT / "docs" / "release" / "final_project_claim.md",
    ROOT / "docs" / "claims" / "current_claim_lock.md",
    RELEASE_BUNDLE_SUMMARY,
    HOLDOUT_SUMMARY,
]

SOURCE_FILES = [
    "README.md",
    "docs/release/submission_bundle.md",
    "docs/release/reviewer_quickstart.md",
    "docs/release/reproducibility_checklist.md",
    "docs/release/key_artifacts_index.md",
    "docs/release/final_project_claim.md",
    "docs/claims/current_claim_lock.md",
]

HASH_FILES = SOURCE_FILES + [
    "docs/release/release_notes_v1.0.0.md",
    "docs/release/final_release_checklist.md",
]

GENERATED_FILES = [
    "docs/release/release_notes_v1.0.0.md",
    "docs/release/final_release_checklist.md",
    "experiments/gate_16a_final_release/results/final_release_summary.json",
]

FINAL_CLAIM = (
    "Chen-calibrated organism-level computational locomotion proxy with "
    "directional Pozo holdout concordance and substantial quantitative ratio mismatch"
)

FORBIDDEN_POSITIVE_CLAIMS = (
    "biologically validated",
    "clinically validated",
    "drug efficacy",
    "therapeutic efficacy",
    "proves parkinson",
    "gene-specific validation achieved",
    "quantitatively validated",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected JSON object: {_relative(path)}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _verify_prior_artifacts() -> tuple[dict[str, Any], dict[str, Any]]:
    for path in REQUIRED_INPUTS:
        _require(path.is_file(), f"Missing release input: {_relative(path)}")

    release_bundle = _read_json(RELEASE_BUNDLE_SUMMARY)
    holdout = _read_json(HOLDOUT_SUMMARY)
    claim_text = "\n".join(
        (ROOT / relative).read_text(encoding="utf-8")
        for relative in (
            "docs/release/final_project_claim.md",
            "docs/claims/current_claim_lock.md",
        )
    )

    _require(release_bundle.get("status") == "RELEASE_BUNDLE_READY", "Gate 15B is not ready")
    _require(release_bundle.get("claim_lock_active") is True, "Gate 15B claim lock is inactive")
    _require(
        holdout.get("final_adjudication_status")
        == "DIRECTIONAL_CONCORDANCE_WITH_QUANTITATIVE_MISMATCH",
        "Gate 14C adjudication status is not claim-safe",
    )
    _require("organism-level computational locomotion proxy" in claim_text, "Allowed claim is missing")
    _require("directional Pozo holdout concordance" in claim_text, "Pozo boundary is missing")
    _require("ratio mismatch" in claim_text.lower(), "Mismatch boundary is missing")

    boundary = release_bundle.get("boundaries", {})
    for key in (
        "biological_validation",
        "gene_specific_validation",
        "clinical_validation",
        "drug_validation",
        "therapeutic_validation",
        "quantitative_pozo_validation",
    ):
        _require(boundary.get(key) is False, f"Boundary {key} is not false")

    for phrase in FORBIDDEN_POSITIVE_CLAIMS:
        _require(phrase not in FINAL_CLAIM.lower(), f"Forbidden positive claim: {phrase}")
    return release_bundle, holdout


def _source_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in HASH_FILES:
        path = ROOT / relative
        _require(path.is_file(), f"Missing hash input: {relative}")
        hashes[relative] = _sha256(path)
    return hashes


def prepare_final_release() -> dict[str, Any]:
    release_bundle, holdout = _verify_prior_artifacts()
    summary = {
        "schema_version": "gate-16a-final-release-summary-v1",
        "status": "FINAL_RELEASE_READY",
        "release_version": "v1.0.0",
        "base_main_commit": _git_value("rev-parse", "--short", "main"),
        "claim_lock_active": True,
        "release_bundle_ready": True,
        "final_claim": FINAL_CLAIM,
        "key_results": {
            "chen_selected_burden": 0.5,
            "gate13c_confirmation_ratio": 0.6142225784,
            "pozo_simulated_ratio": 0.9470,
            "pozo_target_ratio": 0.1920,
            "pozo_directionality_pass": True,
            "pozo_quantitative_ratio_match": False,
        },
        "boundaries": {
            "biological_validation": False,
            "gene_specific_validation": False,
            "clinical_validation": False,
            "drug_validation": False,
            "therapeutic_validation": False,
            "quantitative_pozo_validation": False,
        },
        "no_new_simulation_run": True,
        "no_calibration_run": True,
        "no_tuning_run": True,
        "no_raw_metric_modification": True,
    }
    _write_json(SUMMARY_PATH, summary)

    manifest = {
        "schema_version": "gate-16a-final-release-manifest-v1",
        "status": "FINAL_RELEASE_READY",
        "release_version": "v1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_value("rev-parse", "main"),
        "python_version": platform.python_version(),
        "source_files": SOURCE_FILES,
        "generated_files": GENERATED_FILES,
        "sha256": _source_hashes(),
        "no_new_simulation_run": True,
        "no_calibration_run": True,
        "no_tuning_run": True,
        "no_raw_metric_modification": True,
        "claim_lock_active": True,
        "large_artifacts_committed": False,
    }
    _write_json(MANIFEST_PATH, manifest)
    _ = release_bundle, holdout
    return summary


def main() -> int:
    try:
        summary = prepare_final_release()
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        print(f"Final release preparation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Status: {summary['status']}")
    print(f"Summary: {SUMMARY_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
