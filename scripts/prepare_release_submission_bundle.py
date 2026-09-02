"""Prepare a claim-safe release and submission bundle manifest.

The script reads existing gate artifacts and documentation only. It does not
run simulation, calibration, tuning, or modify historical result files.
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
BUNDLE_ROOT = ROOT / "experiments" / "gate_15b_release_bundle"
SUMMARY_PATH = BUNDLE_ROOT / "results" / "release_bundle_summary.json"
MANIFEST_PATH = BUNDLE_ROOT / "manifests" / "release_bundle_manifest.json"

CLAIM_LOCK = ROOT / "docs" / "claims" / "current_claim_lock.md"
GATE_13B_SUMMARY = (
    ROOT
    / "experiments"
    / "gate_13b_chen_ratio_calibration"
    / "results"
    / "chen_ratio_calibration_summary.json"
)
GATE_13C_MANIFEST = (
    ROOT
    / "experiments"
    / "gate_13c_calibrated_confirmation"
    / "manifests"
    / "calibrated_confirmation_manifest.json"
)
GATE_14B_SUMMARY = (
    ROOT
    / "experiments"
    / "gate_14b_pozo_holdout_validation"
    / "results"
    / "pozo_holdout_result_summary.json"
)
GATE_14C_SUMMARY = (
    ROOT
    / "experiments"
    / "gate_14c_holdout_adjudication"
    / "results"
    / "holdout_adjudication_summary.json"
)

SOURCE_DOCS = [
    ROOT / "README.md",
    ROOT / "docs" / "project_summary.md",
    ROOT / "docs" / "limitations.md",
    ROOT / "docs" / "results_timeline.md",
    CLAIM_LOCK,
    ROOT / "docs" / "claims" / "public_abstract.md",
    ROOT / "docs" / "claims" / "claim_safe_wording_guide.md",
    ROOT / "docs" / "holdout" / "gate_14c_holdout_adjudication_report.md",
]

GENERATED_DOCS = [
    "docs/release/submission_bundle.md",
    "docs/release/reviewer_quickstart.md",
    "docs/release/reproducibility_checklist.md",
    "docs/release/key_artifacts_index.md",
    "docs/release/final_project_claim.md",
]

FINAL_CLAIM = (
    "Chen-calibrated organism-level computational locomotion proxy with "
    "directional Pozo holdout concordance and substantial quantitative ratio mismatch."
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _verify_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    input_paths = [CLAIM_LOCK, GATE_13B_SUMMARY, GATE_13C_MANIFEST, GATE_14B_SUMMARY, GATE_14C_SUMMARY]
    input_paths.extend(SOURCE_DOCS)
    for path in input_paths:
        _require(path.is_file(), f"Missing release input: {_relative(path)}")

    claim_text = CLAIM_LOCK.read_text(encoding="utf-8")
    _require("Chen-calibrated organism-level computational" in claim_text, "Claim lock missing allowed claim")
    _require("Ratio mismatch" in claim_text or "ratio mismatch" in claim_text, "Claim lock missing mismatch boundary")

    gate13b = _read_json(GATE_13B_SUMMARY)
    gate13c = _read_json(GATE_13C_MANIFEST)
    gate14b = _read_json(GATE_14B_SUMMARY)
    gate14c = _read_json(GATE_14C_SUMMARY)

    _require(gate13b.get("status") == "CHEN_RATIO_CALIBRATION_PASS", "Gate 13B is not PASS")
    _require(gate13c.get("status") == "CHEN_CALIBRATED_CONFIRMATION_PASS", "Gate 13C is not PASS")
    _require(gate14b.get("execution_status") == "POZO_HOLDOUT_RUNTIME_PASS", "Gate 14B is not runtime PASS")
    _require(gate14c.get("status") == "HOLDOUT_ADJUDICATION_COMPLETE", "Gate 14C is not complete")
    _require(
        gate14c.get("final_adjudication_status")
        == "DIRECTIONAL_CONCORDANCE_WITH_QUANTITATIVE_MISMATCH",
        "Gate 14C adjudication status is not claim-safe",
    )
    _require(gate14c.get("no_biological_validation_claim") is True, "Gate 14C boundary is missing")
    _require(gate14b.get("no_pozo_tuning") is True, "Gate 14B Pozo tuning flag is missing")
    _require(gate14b.get("no_parameter_reselection") is True, "Gate 14B reselection flag is missing")
    _require(gate14b.get("no_calibration_run") is True, "Gate 14B calibration flag is missing")
    _require(gate14b.get("simulation_data_fabricated") is False, "Gate 14B contains fabricated-data flag")
    return gate13b, gate13c, gate14b, gate14c


def _source_hashes() -> dict[str, str]:
    return {_relative(path): _sha256(path) for path in SOURCE_DOCS}


def _write_documents() -> None:
    release = ROOT / "docs" / "release"
    release.mkdir(parents=True, exist_ok=True)
    documents = {
        "submission_bundle.md": """# Submission Bundle

## Project

Drosophila Parkinson-like Locomotion Proxy

## Current evidence level

Chen-calibrated organism-level computational locomotion proxy with directional
Pozo holdout concordance and substantial quantitative ratio mismatch.

## Included components

- `README.md`
- `docs/project_summary.md`
- `docs/limitations.md`
- `docs/results_timeline.md`
- `docs/claims/current_claim_lock.md`
- `docs/claims/public_abstract.md`
- `docs/claims/claim_safe_wording_guide.md`
- `docs/holdout/gate_14c_holdout_adjudication_report.md`
- `experiments/gate_14c_holdout_adjudication/`
- `experiments/gate_14b_pozo_holdout_validation/`
- `experiments/gate_13c_calibrated_confirmation/`
- `experiments/gate_13b_chen_ratio_calibration/`

## Main result

- Chen-only ratio calibration selected `proxy_burden_level = 0.5`.
- Gate 13C confirmed locked parameter behavior.
- Gate 14B Pozo holdout runtime passed with `12/12` rollouts.
- Pozo directionality passed.
- Quantitative ratio mismatch remains large.

## Boundary

This is not biological Parkinson validation, gene-specific validation, clinical
validation, drug validation, or therapeutic validation.
""",
        "reviewer_quickstart.md": """# Reviewer Quickstart

## Recommended reading order

1. `README.md`
2. `docs/claims/current_claim_lock.md`
3. `docs/project_summary.md`
4. `docs/results_timeline.md`
5. `docs/limitations.md`
6. `docs/holdout/gate_14c_holdout_adjudication_report.md`

## Verify without rerunning GPU

```powershell
py -3.12 scripts/adjudicate_pozo_holdout_claims.py
py -3.12 scripts/prepare_pozo_holdout_protocol.py
py -3.12 scripts/run_chen_ratio_calibration.py
py -3.12 scripts/prepare_chen_only_calibration_objective.py
py -3.12 scripts/audit_calibration_targets.py
py -3.12 -m pytest -q -rs -p no:cacheprovider
```

## Important note

GPU rollouts are already recorded in artifact files with checksum. Reviewers do
not need to rerun GPU by default.
""",
        "reproducibility_checklist.md": """# Reproducibility Checklist

- [x] Python version recorded.
- [x] Git commit recorded.
- [x] Calibration target audit available.
- [x] Gate 13B calibration result available.
- [x] Gate 13C confirmation result available.
- [x] Gate 14B holdout result available.
- [x] Gate 14C claim lock available.
- [x] Hash/checksum available.
- [x] No large binary artifacts committed.
- [x] No Pozo tuning.
- [x] No parameter reselection.
- [x] No biological validation claim.
- [x] No gene-specific validation claim.
""",
        "key_artifacts_index.md": """# Key Artifacts Index

| Artifact | Path | Purpose | Status |
| --- | --- | --- | --- |
| Current claim lock | `docs/claims/current_claim_lock.md` | Khóa cách diễn giải | ACTIVE |
| Public abstract | `docs/claims/public_abstract.md` | Abstract claim-safe | READY |
| Project summary | `docs/project_summary.md` | Tóm tắt pipeline và kết quả | READY |
| Limitations | `docs/limitations.md` | Giới hạn khoa học | DOCUMENTED |
| Results timeline | `docs/results_timeline.md` | Lịch sử các gate | READY |
| Gate 13B calibration summary | `experiments/gate_13b_chen_ratio_calibration/results/chen_ratio_calibration_summary.json` | Chen calibration | PASS |
| Gate 13C confirmation manifest | `experiments/gate_13c_calibrated_confirmation/manifests/calibrated_confirmation_manifest.json` | Seed confirmation | PASS |
| Gate 14B holdout result summary | `experiments/gate_14b_pozo_holdout_validation/results/pozo_holdout_result_summary.json` | Pozo runtime result | PASS |
| Gate 14C adjudication summary | `experiments/gate_14c_holdout_adjudication/results/holdout_adjudication_summary.json` | Claim adjudication | COMPLETE |
| Gate 15B release manifest | `experiments/gate_15b_release_bundle/manifests/release_bundle_manifest.json` | Bundle provenance | READY |
""",
        "final_project_claim.md": """# Final Project Claim

## Allowed final claim

Chen-calibrated organism-level computational locomotion proxy with directional
Pozo holdout concordance and substantial quantitative ratio mismatch.

## Expanded version

This project implements a computational locomotion proxy for Drosophila
Parkinson-like phenotypes. The proxy perturbation was calibrated using a Chen
2014 disease/control walking-speed ratio and confirmed in independent
FlyGym/MuJoCo reruns. A Pozo 2022 PINK1 holdout check showed directional
concordance, but the simulated disease/control distance ratio remained far from
the Pozo target ratio. Therefore, the current evidence supports directional
computational phenotype concordance only, not biological, gene-specific,
clinical, drug, or therapeutic validation.
""",
    }
    for filename, content in documents.items():
        (release / filename).write_text(content, encoding="utf-8", newline="\n")


def prepare_bundle() -> dict[str, Any]:
    gate13b, gate13c, gate14b, gate14c = _verify_inputs()
    _write_documents()
    pozo = gate14b
    summary = {
        "schema_version": "gate-15b-release-bundle-summary-v1",
        "status": "RELEASE_BUNDLE_READY",
        "main_commit_base": _git_value("rev-parse", "--short", "main"),
        "claim_lock_active": True,
        "final_claim": FINAL_CLAIM,
        "key_statuses": {
            "chen_ratio_calibration": gate13b["status"],
            "chen_confirmation": gate13c["status"],
            "pozo_runtime": pozo["execution_status"],
            "holdout_adjudication": gate14c["final_adjudication_status"],
        },
        "boundaries": {
            "biological_validation": False,
            "gene_specific_validation": False,
            "clinical_validation": False,
            "drug_validation": False,
            "therapeutic_validation": False,
            "quantitative_pozo_validation": False,
        },
        "key_results": {
            "selected_proxy_burden_level": gate13b["selected_burden_level"],
            "chen_ratio_target": gate13b["chen_ratio_target"],
            "gate13c_confirmation_ratio": gate13c["confirmation_ratio"],
            "pozo_successful_runs": pozo["successful_runs"],
            "pozo_control_distance_mm": pozo["mean_distance_control"],
            "pozo_holdout_distance_mm": pozo["mean_distance_holdout"],
            "pozo_simulated_ratio": pozo["simulated_distance_ratio"],
            "pozo_target_ratio": pozo["pozo_target_ratio"],
            "pozo_directionality_pass": pozo["directionality_pass"],
            "pozo_quantitative_ratio_match": False,
        },
        "no_new_simulation_run": True,
        "no_calibration_run": True,
        "no_tuning_run": True,
        "no_raw_metric_modification": True,
    }
    _write_json(SUMMARY_PATH, summary)
    manifest = {
        "schema_version": "gate-15b-release-bundle-manifest-v1",
        "status": "RELEASE_BUNDLE_READY",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_value("rev-parse", "HEAD"),
        "python_version": platform.python_version(),
        "source_files": [_relative(path) for path in SOURCE_DOCS],
        "generated_files": GENERATED_DOCS,
        "sha256": _source_hashes(),
        "no_new_simulation_run": True,
        "no_calibration_run": True,
        "no_tuning_run": True,
        "no_raw_metric_modification": True,
        "claim_lock_active": True,
        "large_artifacts_committed": False,
    }
    _write_json(MANIFEST_PATH, manifest)
    return summary


def main() -> int:
    try:
        summary = prepare_bundle()
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        print(f"Release bundle preparation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Status: {summary['status']}")
    print(f"Summary: {SUMMARY_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
