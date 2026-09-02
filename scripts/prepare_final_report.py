"""Prepare the Gate 17A Vietnamese scientific report artifacts.

The script verifies existing release, calibration, confirmation, and holdout
artifacts, then writes only the new Gate 17A summary and manifest. It never
runs simulation, calibration, tuning, or edits historical artifacts.
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
REPORT_ROOT = ROOT / "experiments" / "gate_17a_final_report"
SUMMARY_PATH = REPORT_ROOT / "results" / "final_report_summary.json"
MANIFEST_PATH = REPORT_ROOT / "manifests" / "final_report_manifest.json"

GATE_13B = ROOT / "experiments/gate_13b_chen_ratio_calibration/results/chen_ratio_calibration_summary.json"
GATE_13C = ROOT / "experiments/gate_13c_calibrated_confirmation/manifests/calibrated_confirmation_manifest.json"
GATE_14B = ROOT / "experiments/gate_14b_pozo_holdout_validation/results/pozo_holdout_result_summary.json"
GATE_14C = ROOT / "experiments/gate_14c_holdout_adjudication/results/holdout_adjudication_summary.json"
GATE_16A = ROOT / "experiments/gate_16a_final_release/results/final_release_summary.json"

REPORT_FILES = [
    "docs/report/final_vietnamese_report.md",
    "docs/report/final_report_short_summary.md",
    "docs/report/final_report_outline.md",
]

SOURCE_FILES = [
    "docs/claims/current_claim_lock.md",
    "docs/release/final_project_claim.md",
    "docs/release/release_notes_v1.0.0.md",
    "docs/project_summary.md",
    "docs/limitations.md",
    "docs/results_timeline.md",
    "experiments/gate_16a_final_release/results/final_release_summary.json",
    "experiments/gate_14c_holdout_adjudication/results/holdout_adjudication_summary.json",
]

HASH_FILES = [
    *REPORT_FILES,
    "docs/claims/current_claim_lock.md",
    "docs/release/final_project_claim.md",
]

GENERATED_FILES = [
    *REPORT_FILES,
    "experiments/gate_17a_final_report/results/final_report_summary.json",
]

FINAL_CLAIM = (
    "Chen-calibrated organism-level computational locomotion proxy with "
    "directional Pozo holdout concordance and substantial quantitative ratio mismatch"
)

FORBIDDEN_POSITIVE_PHRASES = (
    "biologically validated",
    "clinically validated",
    "drug efficacy",
    "therapeutic efficacy",
    "proves parkinson",
    "gene-specific validation achieved",
    "quantitatively validated",
    "biological parkinson validation achieved",
    "mô hình đã chứng minh parkinson sinh học",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected JSON object: {_relative(path)}")
    return value


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _verify_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    required = [
        ROOT / "docs/claims/current_claim_lock.md",
        ROOT / "docs/release/final_project_claim.md",
        GATE_13B,
        GATE_13C,
        GATE_14B,
        GATE_14C,
        GATE_16A,
    ]
    required.extend(ROOT / relative for relative in REPORT_FILES)
    for path in required:
        _require(path.is_file(), f"Missing report input: {_relative(path)}")

    gate13b = _read_json(GATE_13B)
    gate13c = _read_json(GATE_13C)
    gate14b = _read_json(GATE_14B)
    gate14c = _read_json(GATE_14C)
    gate16a = _read_json(GATE_16A)

    _require(gate13b.get("status") == "CHEN_RATIO_CALIBRATION_PASS", "Gate 13B is not PASS")
    _require(gate13c.get("status") == "CHEN_CALIBRATED_CONFIRMATION_PASS", "Gate 13C is not PASS")
    _require(gate14b.get("execution_status") == "POZO_HOLDOUT_RUNTIME_PASS", "Gate 14B is not runtime PASS")
    _require(
        gate14c.get("final_adjudication_status")
        == "DIRECTIONAL_CONCORDANCE_WITH_QUANTITATIVE_MISMATCH",
        "Gate 14C adjudication is not claim-safe",
    )
    _require(gate16a.get("status") == "FINAL_RELEASE_READY", "Gate 16A is not ready")
    _require(gate16a.get("release_version") == "v1.0.0", "Gate 16A release version is missing")
    _require(gate16a.get("claim_lock_active") is True, "Gate 16A claim lock is inactive")

    boundaries = gate16a.get("boundaries", {})
    for key in (
        "biological_validation",
        "gene_specific_validation",
        "clinical_validation",
        "drug_validation",
        "therapeutic_validation",
    ):
        _require(boundaries.get(key) is False, f"Boundary {key} is not false")

    claim_text = "\n".join(
        (ROOT / relative).read_text(encoding="utf-8")
        for relative in (
            "docs/claims/current_claim_lock.md",
            "docs/release/final_project_claim.md",
        )
    )
    _require("organism-level computational locomotion proxy" in claim_text, "Allowed claim is missing")
    _require("directional Pozo holdout concordance" in claim_text, "Pozo concordance is missing")
    _require("ratio mismatch" in claim_text.lower(), "Mismatch boundary is missing")

    report_text = "\n".join(
        (ROOT / relative).read_text(encoding="utf-8").lower() for relative in REPORT_FILES
    )
    for phrase in FORBIDDEN_POSITIVE_PHRASES:
        _require(phrase not in report_text, f"Forbidden positive wording: {phrase}")

    return gate13b, gate13c, gate14b, gate14c, gate16a


def _hashes() -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in HASH_FILES:
        path = ROOT / relative
        _require(path.is_file(), f"Missing hash input: {relative}")
        result[relative] = _sha256(path)
    return result


def prepare_report() -> dict[str, Any]:
    gate13b, gate13c, gate14b, gate14c, gate16a = _verify_inputs()
    summary = {
        "schema_version": "gate-17a-final-report-summary-v1",
        "status": "FINAL_REPORT_READY",
        "language": "vi",
        "base_release_tag": "v1.0.0",
        "claim_lock_active": True,
        "final_claim": FINAL_CLAIM,
        "main_report": REPORT_FILES[0],
        "short_summary": REPORT_FILES[1],
        "outline": REPORT_FILES[2],
        "key_results": {
            "chen_selected_burden": gate13b["selected_burden_level"],
            "chen_target_ratio": gate13b["chen_ratio_target"],
            "gate13c_confirmation_ratio": gate13c["confirmation_ratio"],
            "pozo_control_distance_mm": round(float(gate14b["mean_distance_control"]), 5),
            "pozo_holdout_distance_mm": round(float(gate14b["mean_distance_holdout"]), 5),
            "pozo_simulated_ratio": round(float(gate14b["simulated_distance_ratio"]), 4),
            "pozo_target_ratio": round(float(gate14b["pozo_target_ratio"]), 4),
            "directionality_pass": gate14b["directionality_pass"],
            "quantitative_ratio_match": False,
        },
        "boundaries": {
            "biological_validation": False,
            "gene_specific_validation": False,
            "clinical_validation": False,
            "drug_validation": False,
            "therapeutic_validation": False,
        },
        "no_new_simulation_run": True,
        "no_calibration_run": True,
        "no_tuning_run": True,
        "no_raw_metric_modification": True,
    }
    _write_json(SUMMARY_PATH, summary)

    manifest = {
        "schema_version": "gate-17a-final-report-manifest-v1",
        "status": "FINAL_REPORT_READY",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_value("rev-parse", "HEAD"),
        "python_version": platform.python_version(),
        "source_files": SOURCE_FILES,
        "generated_files": GENERATED_FILES,
        "sha256": _hashes(),
        "claim_lock_active": True,
        "no_new_simulation_run": True,
        "no_calibration_run": True,
        "no_tuning_run": True,
        "no_raw_metric_modification": True,
        "large_artifacts_committed": False,
    }
    _write_json(MANIFEST_PATH, manifest)
    _ = gate14c, gate16a
    return summary


def main() -> int:
    try:
        summary = prepare_report()
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        print(f"Final report preparation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Status: {summary['status']}")
    print(f"Summary: {SUMMARY_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
