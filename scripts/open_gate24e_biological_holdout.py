"""Open the authorized Gate24E biological holdout once and test direction only.

This module deliberately does not read individual-level data, import numeric
holdout values, run the simulator, or alter the frozen virtual prediction.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
SIGNOFF = ROOT / "research/validation/prospective/gate24e_virtual_prediction_freeze_reviewer_signoff.json"
FREEZE = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/immutable_virtual_prediction_freeze.json"
FIREWALL = ROOT / "experiments/gate_24_prospective_validation/manifests/holdout_firewall_manifest.json"
SOURCE = ROOT / "research/validation/biological/parkin_validation_sources.csv"
OUTPUT_ROOT = ROOT / "experiments/gate_24e_blinded_parkin_prediction"
OPENING_MANIFEST = OUTPUT_ROOT / "manifests/biological_holdout_opening.json"
DIRECTION_RESULT = OUTPUT_ROOT / "results/biological_holdout_direction.csv"
SUMMARY = OUTPUT_ROOT / "results/cross_assay_validation_summary.json"
CHECKSUMS = OUTPUT_ROOT / "manifests/biological_holdout_checksums.sha256"
REPORT = ROOT / "docs/validation/gate24e_biological_holdout_directional_validation.md"

EXPECTED_AUTHORIZATION_COMMIT = "648e0dbc5a845be4186ce76a6130b95aa06842ce"
EXPECTED_FREEZE_SHA256 = "f44e9ad10b9fc4795ae2173d3e8b27fc9ea0d8202925bfc08cdcc72d06b00863"
EXPECTED_GRID_DECISION = "DIRECTIONAL_VALIDATION_NOT_SUPPORTED"
EXPECTED_SOURCE_ID = "cackovic_2018_park_loss_of_function"

ALLOWED_BIOLOGICAL_DIRECTIONS = {
    "BIOLOGICAL_IMPAIRMENT_SUPPORTED",
    "BIOLOGICAL_IMPAIRMENT_NOT_SUPPORTED",
    "BIOLOGICAL_DIRECTION_INCONCLUSIVE",
}
ALLOWED_CROSS_ASSAY_DECISIONS = {
    "DIRECTIONAL_CROSS_ASSAY_CONCORDANCE",
    "DIRECTIONAL_CROSS_ASSAY_DISCORDANCE",
    "DIRECTIONAL_CROSS_ASSAY_INCONCLUSIVE",
}


class HoldoutGateError(RuntimeError):
    """Raised when the one-time holdout gate cannot be opened safely."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise HoldoutGateError(f"Expected JSON object: {path}")
    return value


def _current_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HoldoutGateError(message)


def validate_authorization(signoff: Mapping[str, Any], freeze: Mapping[str, Any], current_commit: str) -> None:
    _require(signoff.get("status") == "VIRTUAL_PREDICTION_FREEZE_REVIEW_APPROVED", "freeze review is not approved")
    _require(signoff.get("decision") == "APPROVED_TO_OPEN_GATE24E_BIOLOGICAL_HOLDOUT", "holdout opening is not authorized")
    _require(signoff.get("holdout_open_authorized") is True, "holdout_open_authorized must be true")
    _require(signoff.get("holdout_opened") is False, "signoff says the holdout was already opened")
    _require(signoff.get("virtual_prediction_freeze_sha256") == EXPECTED_FREEZE_SHA256, "signoff freeze SHA256 mismatch")
    _require(freeze.get("virtual_prediction_freeze_sha256") == EXPECTED_FREEZE_SHA256, "virtual prediction freeze SHA256 mismatch")
    _require(freeze.get("grid_decision") == EXPECTED_GRID_DECISION, "frozen virtual decision changed")
    _require(current_commit == EXPECTED_AUTHORIZATION_COMMIT, "authorization commit does not match the approved commit")
    for key in ("retuning_allowed", "seed_change_allowed", "parameter_change_allowed", "metric_change_allowed", "decision_rule_change_allowed"):
        _require(signoff.get(key) is False, f"{key} must remain false")
    _require(signoff.get("tuning_using_holdout") is False, "holdout tuning is forbidden")
    _require(signoff.get("posthoc_parameter_selection") is False, "post-hoc parameter selection is forbidden")
    _require(signoff.get("biological_validation_claim_allowed") is False, "biological validation claim must remain forbidden")


def validate_pre_open_firewall(firewall: Mapping[str, Any]) -> None:
    _require(firewall.get("status") == "SEALED", "holdout firewall is not SEALED before opening")
    _require(firewall.get("no_numeric_holdout_import") is True, "pre-open firewall permits numeric import")
    _require(firewall.get("no_holdout_tuning") is True, "pre-open firewall permits holdout tuning")
    _require(firewall.get("gpu_executed") is False, "GPU execution is recorded in pre-open firewall")
    _require(firewall.get("simulation_executed") is False, "simulation execution is recorded in pre-open firewall")


def _read_source_row(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    _require(len(rows) == 1, "held-out source must contain exactly one locked source row")
    row = rows[0]
    _require(row.get("source_id") == EXPECTED_SOURCE_ID, "unexpected biological holdout source")
    _require(row.get("raw_data_available") == "false", "raw biological values are unexpectedly available")
    _require(row.get("not_used_for_tuning") == "true", "holdout source is not marked not_used_for_tuning")
    _require(row.get("transfer_status") == "VALIDATION_ONLY", "holdout source transfer policy changed")
    return row


def biological_direction_from_source(row: Mapping[str, str]) -> str:
    endpoint = (row.get("endpoint") or "").lower()
    notes = (row.get("notes") or "").lower()
    _require("climbing" in endpoint and "deficit" in endpoint, "source does not provide the locked climbing-deficit endpoint")
    _require("loss-of-function" in notes or "loss of function" in notes, "source does not identify Parkin loss-of-function")
    return "BIOLOGICAL_IMPAIRMENT_SUPPORTED"


def cross_assay_decision(biological_direction: str, virtual_decision: str) -> str:
    _require(biological_direction in ALLOWED_BIOLOGICAL_DIRECTIONS, "invalid biological direction")
    _require(virtual_decision == EXPECTED_GRID_DECISION, "virtual decision is not the frozen decision")
    if biological_direction == "BIOLOGICAL_IMPAIRMENT_SUPPORTED":
        return "DIRECTIONAL_CROSS_ASSAY_DISCORDANCE"
    if biological_direction == "BIOLOGICAL_IMPAIRMENT_NOT_SUPPORTED":
        return "DIRECTIONAL_CROSS_ASSAY_CONCORDANCE"
    return "DIRECTIONAL_CROSS_ASSAY_INCONCLUSIVE"


def _write_exclusive_json(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(document, handle, ensure_ascii=True, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise HoldoutGateError("biological holdout opening already exists; single-use gate refuses rerun") from exc


def _write_direction(path: Path, row: Mapping[str, str], direction: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source_id", "source_citation", "assay", "endpoint", "age_context",
        "biological_condition", "control_condition", "direction_label",
        "raw_data_available", "quantitative_cross_assay_allowed", "notes",
    ]
    output = {
        "source_id": row["source_id"],
        "source_citation": "Cackovic et al. 2018; DOI:10.3389/fncel.2018.00039; PMID:29497364",
        "assay": row["assay"],
        "endpoint": row["endpoint"],
        "age_context": row["age_days"],
        "biological_condition": row.get("intervention") or row.get("genotype", ""),
        "control_condition": row["matched_control"],
        "direction_label": direction,
        "raw_data_available": "false",
        "quantitative_cross_assay_allowed": "false",
        "notes": (
            "Summary-level directional evidence only. No raw numeric values, individual-level data, "
            "mm/s conversion, effect-size equivalence, or threshold matching was imported."
        ),
    }
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(output)


def _write_report(path: Path, opening: Mapping[str, Any], row: Mapping[str, str], direction: str, decision: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Gate 24E-S4K: Biological holdout directional validation

## Scope

This gate opened the authorized biological holdout exactly once after the
blinded virtual prediction was frozen. It performs directional cross-assay
validation only. No GPU, FlyGym simulation, retuning, parameter selection, or
numeric cross-assay conversion was performed.

## Frozen virtual prediction

- Freeze SHA256: `{opening['virtual_prediction_freeze_sha256']}`.
- Frozen grid decision: `{opening['virtual_grid_decision']}`.
- Authorization commit: `{opening['authorization_commit']}`.
- Prediction was frozen before the holdout was opened: `true`.

The frozen virtual result did not support the preregistered locomotor
impairment direction. That result is retained and is not relabeled after
opening the holdout.

## Human authorization

- Status: `VIRTUAL_PREDICTION_FREEZE_REVIEW_APPROVED`.
- Decision: `APPROVED_TO_OPEN_GATE24E_BIOLOGICAL_HOLDOUT`.
- Reviewers: `{opening['reviewer_1']}` and `{opening['reviewer_2']}`.
- Review date: `{opening['review_date']}`.
- Opened at UTC: `{opening['opened_at_utc']}`.

## Held-out biological evidence

- Source: Cackovic et al. 2018, DOI `10.3389/fncel.2018.00039`, PMID `29497364`.
- Assay: `{row['assay']}`.
- Endpoint: `{row['endpoint']}`.
- Age context: `{row['age_days']}`.
- Biological direction: `{direction}`.
- Evidence type: `{row['data_type']}`.
- Raw data available in the repository: `false`.

The preserved source package supports a Parkin loss-of-function climbing
impairment direction at summary level. It does not provide raw individual
values in this repository, so no numeric value is reported here.

## Cross-assay decision

The biological assay is negative geotaxis/climbing, whereas the virtual assay
uses planar locomotion. These endpoints are not quantitatively equivalent.
The only permitted comparison is locomotor impairment direction.

- Quantitative cross-assay validation: `false`.
- Cross-assay decision: `{decision}`.
- Retuning after holdout: `false`.
- Post-hoc parameter selection: `false`.

Because the biological source supports impairment while the frozen virtual
prediction did not support impairment, this is a directional discordance under
the preregistered cross-assay protocol. This negative validation result does
not authorize changing the model or re-running Gate24E.

## Claim boundary

This result does not support a biologically validated Parkinson model, a
validated Parkinson mechanism, human or clinical validation, or drug
validation. The allowed statement is:

> The frozen Parkin computational perturbation did not reproduce the held-out
> biological locomotor impairment direction under the preregistered
> cross-assay validation protocol.

Any improved model must be a new experiment with a new gate and versioned
provenance; it must not rewrite the Gate24E frozen evidence.
"""
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_checksums(paths: list[Path], output: Path, root: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for path in paths:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        lines.append(f"{_sha256(path)}  {relative}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _complete_opening(root: Path, opening: Mapping[str, Any]) -> dict[str, Any]:
    row = _read_source_row(root / SOURCE.relative_to(ROOT))
    direction = biological_direction_from_source(row)
    decision = cross_assay_decision(direction, EXPECTED_GRID_DECISION)
    direction_path = root / DIRECTION_RESULT.relative_to(ROOT)
    summary_path = root / SUMMARY.relative_to(ROOT)
    report_path = root / REPORT.relative_to(ROOT)
    _write_direction(direction_path, row, direction)
    summary = {
        "schema_version": "gate24e-cross-assay-validation-summary-v1",
        "status": "GATE24E_BIOLOGICAL_HOLDOUT_VALIDATED_DIRECTION_ONLY",
        "holdout_status": "OPENED_FOR_VALIDATION",
        "holdout_opened": True,
        "virtual_prediction_freeze_sha256": EXPECTED_FREEZE_SHA256,
        "virtual_grid_decision": EXPECTED_GRID_DECISION,
        "biological_direction": direction,
        "cross_assay_decision": decision,
        "primary_validation_axis": "LOCOMOTOR_IMPAIRMENT_DIRECTION",
        "quantitative_cross_assay_validation": False,
        "retuning_after_holdout": False,
        "posthoc_parameter_selection": False,
        "biological_validation_claim": "NOT_SUPPORTED",
        "gpu_executed": False,
        "simulation_executed": False,
        "source_id": row["source_id"],
        "source_sha256": _sha256(root / SOURCE.relative_to(ROOT)),
        "raw_data_available": False,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    _write_report(report_path, opening, row, direction, decision)
    _write_checksums([root / OPENING_MANIFEST.relative_to(ROOT), direction_path, summary_path, report_path], root / CHECKSUMS.relative_to(ROOT), root)
    return summary


def open_holdout(root: Path = ROOT, *, current_commit: str | None = None, opened_at_utc: str | None = None) -> dict[str, Any]:
    signoff = _json(root / SIGNOFF.relative_to(ROOT))
    freeze = _json(root / FREEZE.relative_to(ROOT))
    firewall = _json(root / FIREWALL.relative_to(ROOT))
    current_commit = current_commit or _current_commit(root)
    validate_authorization(signoff, freeze, current_commit)
    validate_pre_open_firewall(firewall)

    opening_path = root / OPENING_MANIFEST.relative_to(ROOT)
    if opening_path.exists():
        raise HoldoutGateError("biological holdout opening already exists; single-use gate refuses rerun")
    opened_at_utc = opened_at_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    opening = {
        "schema_version": "gate24e-biological-holdout-opening-v1",
        "status": "BIOLOGICAL_HOLDOUT_OPENED_FOR_VALIDATION",
        "opened_at_utc": opened_at_utc,
        "authorization_commit": current_commit,
        "virtual_prediction_freeze_sha256": EXPECTED_FREEZE_SHA256,
        "virtual_grid_decision": EXPECTED_GRID_DECISION,
        "purpose": "DIRECTIONAL_CROSS_ASSAY_VALIDATION_ONLY",
        "tuning_allowed": False,
        "model_change_allowed": False,
        "parameter_selection_allowed": False,
        "holdout_opened": True,
        "holdout_status": "OPENED_FOR_VALIDATION",
        "reviewer_1": signoff.get("reviewer_1"),
        "reviewer_2": signoff.get("reviewer_2"),
        "review_date": signoff.get("review_date"),
        "prior_firewall_status": "SEALED",
        "gpu_executed": False,
        "simulation_executed": False,
    }
    # This exclusive write is the irreversible single-use transition. Only
    # after it succeeds may the held-out source package be read.
    _write_exclusive_json(opening_path, opening)
    return _complete_opening(root, opening)


def finalize_opened_holdout(root: Path = ROOT) -> dict[str, Any]:
    """Finish an interrupted post-opening write without opening a second time."""
    opening_path = root / OPENING_MANIFEST.relative_to(ROOT)
    _require(opening_path.is_file(), "no prior biological holdout opening exists")
    _require(not (root / DIRECTION_RESULT.relative_to(ROOT)).exists(), "direction artifact already exists")
    _require(not (root / SUMMARY.relative_to(ROOT)).exists(), "summary artifact already exists")
    opening = _json(opening_path)
    _require(opening.get("status") == "BIOLOGICAL_HOLDOUT_OPENED_FOR_VALIDATION", "invalid opening manifest")
    _require(opening.get("holdout_opened") is True, "opening manifest does not record an opened holdout")
    _require(opening.get("virtual_prediction_freeze_sha256") == EXPECTED_FREEZE_SHA256, "opening freeze SHA256 mismatch")
    return _complete_opening(root, opening)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    result = finalize_opened_holdout(root) if (root / OPENING_MANIFEST.relative_to(ROOT)).exists() else open_holdout(root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
