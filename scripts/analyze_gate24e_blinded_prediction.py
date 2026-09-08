"""Analyze completed Gate24E blinded artifacts under the locked decision rule.

This module never launches a runner and never reads the biological holdout. It
derives the locked primary and secondary virtual metrics from completed rollout
artifacts when the external platform metrics use legacy field names.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/job_plan.json"
DEFAULT_OUTPUT = ROOT / "experiments/gate_24e_blinded_parkin_prediction/results"
PARAMETERS = (0.25, 0.50, 0.75, 1.00)
SEEDS = (0, 1, 2, 3, 4)
PRIMARY_METRIC = "median_planar_speed_mm_s"
SECONDARY_METRIC = "distance_traveled_mm"


class AnalysisError(RuntimeError):
    """Raised when the frozen analysis contract cannot be evaluated."""


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AnalysisError(f"Expected JSON object: {path}")
    return value


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _scalar_metrics(document: dict[str, Any]) -> dict[str, Any]:
    value = document.get("scalar_metrics", document)
    return dict(value) if isinstance(value, dict) else {}


def _first_array(arrays: Any, names: Iterable[str]) -> np.ndarray | None:
    for name in names:
        if name in arrays.files:
            return np.asarray(arrays[name], dtype=float)
    return None


def _derive_metrics(output: Path, metrics_document: dict[str, Any]) -> tuple[float, float, int]:
    """Derive exact locked metrics without treating mean speed as a median."""

    scalars = _scalar_metrics(metrics_document)
    rollout_path = output / "rollout.npz"
    if not rollout_path.is_file():
        raise AnalysisError(f"Missing rollout.npz for metric derivation: {output}")
    with np.load(rollout_path, allow_pickle=False) as arrays:
        positions = _first_array(arrays, ("thorax", "thorax_positions", "positions"))
        time_s = _first_array(arrays, ("timestamp_s", "time_s", "timestamps_s"))
    if positions is None or time_s is None or positions.ndim != 2 or positions.shape[1] < 2:
        raise AnalysisError(f"Trajectory arrays are incomplete: {rollout_path}")
    if len(positions) != len(time_s) or len(positions) < 2:
        raise AnalysisError(f"Trajectory frame count is invalid: {rollout_path}")
    if not np.all(np.isfinite(positions)) or not np.all(np.isfinite(time_s)):
        raise AnalysisError(f"Trajectory contains non-finite values: {rollout_path}")
    intervals = np.diff(time_s)
    if not np.all(intervals > 0):
        raise AnalysisError(f"Trajectory timestamps are not strictly increasing: {rollout_path}")
    steps = np.linalg.norm(np.diff(positions[:, :2], axis=0), axis=1)
    speed = steps / intervals
    median_speed = float(np.median(speed))
    distance = float(np.sum(steps))
    if not _finite(median_speed) or not _finite(distance):
        raise AnalysisError(f"Derived metrics are non-finite: {rollout_path}")
    if _finite(scalars.get(PRIMARY_METRIC)) and _finite(scalars.get(SECONDARY_METRIC)):
        return float(scalars[PRIMARY_METRIC]), float(scalars[SECONDARY_METRIC]), len(positions)
    return median_speed, distance, len(positions)


def _expected_provenance(job: dict[str, Any], provenance: dict[str, Any]) -> list[str]:
    errors = []
    for key in (
        "job_id",
        "condition",
        "parameter",
        "seed",
        "prepared_checkpoint_sha256",
        "healthy_checkpoint_sha256",
        "mapping_sha256",
        "target_sha256",
    ):
        if provenance.get(key) != job.get(key):
            errors.append(f"{key} mismatch")
    return errors


def validate_completed_job(job: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """Return one seed-level row only when all locked QC checks pass."""

    output = Path(job["output_path"])
    errors: list[str] = []
    status_path = output / "status.json"
    metrics_path = output / "metrics" / "metrics.json"
    provenance_path = output / "adapter_job_provenance.json"
    rollout_path = output / "rollout.npz"
    if not status_path.is_file():
        errors.append("missing status.json")
    if not metrics_path.is_file():
        errors.append("missing metrics/metrics.json")
    if not provenance_path.is_file():
        errors.append("missing adapter_job_provenance.json")
    if not rollout_path.is_file():
        errors.append("missing rollout.npz")
    if errors:
        return None, errors
    status = _read_json(status_path)
    if status.get("status") != "PASS":
        errors.append(f"status={status.get('status')}")
    provenance = _read_json(provenance_path)
    errors.extend(_expected_provenance(job, provenance))
    try:
        metrics_document = _read_json(metrics_path)
        speed, distance, frame_count = _derive_metrics(output, metrics_document)
    except (AnalysisError, OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
        return None, errors
    if not _finite(speed) or not _finite(distance):
        errors.append("primary or secondary metric is non-finite")
    if errors:
        return None, errors
    return {
        "job_id": job["job_id"],
        "condition": job["condition"],
        "parameter": float(job["parameter"]),
        "seed": int(job["seed"]),
        PRIMARY_METRIC: speed,
        SECONDARY_METRIC: distance,
        "frame_count": frame_count,
        "statistical_unit": "seed",
        "qc_pass": True,
    }, []


def decision_for_directions(direction_pass: dict[float, bool]) -> str:
    """Apply the preregistered grid-level rule without selecting a parameter."""

    ordered = [bool(direction_pass.get(parameter, False)) for parameter in PARAMETERS]
    if all(ordered):
        return "VIRTUAL_DIRECTIONAL_PREDICTION_SUPPORTED"
    if not ordered[-1] or not any(ordered):
        return "DIRECTIONAL_VALIDATION_NOT_SUPPORTED"
    return "DIRECTIONAL_VALIDATION_INCONCLUSIVE"


def _load_plan(path: Path) -> dict[str, Any]:
    plan = _read_json(path)
    if plan.get("status") != "READY_FOR_25_BLINDED_GPU_JOBS" or plan.get("job_count") != 25:
        raise AnalysisError("Gate24E job plan is not the locked 25-job plan.")
    if plan.get("holdout_status") != "SEALED" or plan.get("holdout_opened") is not False:
        raise AnalysisError("Holdout is not sealed in the Gate24E job plan.")
    if plan.get("tuning_using_holdout") is not False or plan.get("posthoc_parameter_selection_allowed") is not False:
        raise AnalysisError("Gate24E plan allows forbidden holdout tuning or post-hoc selection.")
    seeds = sorted({int(job.get("seed")) for job in plan.get("jobs", [])})
    if seeds != list(SEEDS):
        raise AnalysisError("Scientific analyzer accepts only locked seeds 0 through 4.")
    if any(int(job.get("seed")) == 9001 for job in plan.get("jobs", [])):
        raise AnalysisError("Technical storage-probe seed 9001 is excluded from scientific analysis.")
    return plan


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def analyze(plan_path: Path = PLAN, output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    plan = _load_plan(plan_path)
    jobs = list(plan.get("jobs", []))
    valid_rows: list[dict[str, Any]] = []
    failed_jobs: list[dict[str, Any]] = []
    for job in jobs:
        row, errors = validate_completed_job(job)
        if row is None:
            failed_jobs.append({"job_id": job["job_id"], "errors": errors})
        else:
            valid_rows.append(row)

    healthy = {(row["seed"]): row for row in valid_rows if row["condition"] == "healthy"}
    parkin = {
        (float(row["parameter"]), row["seed"]): row
        for row in valid_rows
        if row["condition"] == "parkin"
    }
    healthy_rows = [healthy[seed] for seed in SEEDS if seed in healthy]
    parkin_rows = [parkin[key] for parameter in PARAMETERS for key in ((parameter, seed) for seed in SEEDS) if key in parkin]
    paired_rows: list[dict[str, Any]] = []
    parameter_summaries: list[dict[str, Any]] = []
    direction_pass: dict[float, bool] = {}
    for parameter in PARAMETERS:
        rows: list[dict[str, Any]] = []
        for seed in SEEDS:
            disease = parkin.get((parameter, seed))
            control = healthy.get(seed)
            if disease is None or control is None:
                continue
            row = {
                "parameter": parameter,
                "seed": seed,
                "healthy_median_planar_speed_mm_s": control[PRIMARY_METRIC],
                "parkin_median_planar_speed_mm_s": disease[PRIMARY_METRIC],
                "paired_delta_speed_mm_s": disease[PRIMARY_METRIC] - control[PRIMARY_METRIC],
                "healthy_distance_traveled_mm": control[SECONDARY_METRIC],
                "parkin_distance_traveled_mm": disease[SECONDARY_METRIC],
                "qc_pass": True,
            }
            paired_rows.append(row)
            rows.append(row)
        complete = len(rows) == len(SEEDS)
        if complete:
            deltas = np.asarray([row["paired_delta_speed_mm_s"] for row in rows], dtype=float)
            healthy_speeds = np.asarray([row["healthy_median_planar_speed_mm_s"] for row in rows], dtype=float)
            parkin_speeds = np.asarray([row["parkin_median_planar_speed_mm_s"] for row in rows], dtype=float)
            healthy_distances = np.asarray([row["healthy_distance_traveled_mm"] for row in rows], dtype=float)
            parkin_distances = np.asarray([row["parkin_distance_traveled_mm"] for row in rows], dtype=float)
            median_delta = float(np.median(deltas))
            speed_ratio = float(np.median(parkin_speeds) / np.median(healthy_speeds))
            distance_ratio = float(np.median(parkin_distances) / np.median(healthy_distances))
            direction = bool(median_delta < 0)
        else:
            median_delta = None
            speed_ratio = None
            distance_ratio = None
            direction = False
        direction_pass[parameter] = direction if complete else False
        parameter_summaries.append(
            {
                "parameter": parameter,
                "valid_seed_count": len(rows),
                "qc_pass": complete,
                "median_paired_delta_speed_mm_s": median_delta,
                "speed_ratio": speed_ratio,
                "distance_ratio": distance_ratio,
                "direction_pass": direction if complete else False,
            }
        )

    complete = not failed_jobs and len(valid_rows) == plan["job_count"]
    grid_decision = decision_for_directions(direction_pass) if complete else "GATE24E_INCOMPLETE_TECHNICAL_EXECUTION"
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "healthy_per_seed.csv", healthy_rows, ["seed", PRIMARY_METRIC, SECONDARY_METRIC, "frame_count", "statistical_unit", "qc_pass"])
    _write_csv(output_dir / "parkin_per_seed.csv", parkin_rows, ["parameter", "seed", PRIMARY_METRIC, SECONDARY_METRIC, "frame_count", "statistical_unit", "qc_pass"])
    _write_csv(
        output_dir / "paired_effects.csv",
        paired_rows,
        [
            "parameter",
            "seed",
            "healthy_median_planar_speed_mm_s",
            "parkin_median_planar_speed_mm_s",
            "paired_delta_speed_mm_s",
            "healthy_distance_traveled_mm",
            "parkin_distance_traveled_mm",
            "qc_pass",
        ],
    )
    _write_csv(
        output_dir / "parameter_summary.csv",
        parameter_summaries,
        ["parameter", "valid_seed_count", "qc_pass", "median_paired_delta_speed_mm_s", "speed_ratio", "distance_ratio", "direction_pass"],
    )
    summary = {
        "status": "GATE24E_COMPLETE" if complete else "GATE24E_INCOMPLETE_TECHNICAL_EXECUTION",
        "job_count_expected": plan["job_count"],
        "job_count_valid": len(valid_rows),
        "failed_jobs": failed_jobs,
        "primary_validation_axis": "LOCOMOTOR_IMPAIRMENT_DIRECTION",
        "primary_metric": PRIMARY_METRIC,
        "secondary_metric": SECONDARY_METRIC,
        "seed_list": list(SEEDS),
        "parameters": parameter_summaries,
        "grid_decision": grid_decision,
        "holdout_opened": False,
        "tuning_using_holdout": False,
        "posthoc_parameter_selection": False,
        "statistical_unit": "seed",
        "frame_is_statistical_replicate": False,
        "biological_validation_claim": "NOT_ALLOWED_AT_GATE24E",
        "scientific_scope": "Blinded computational Parkin prediction only; no biological validation claim.",
    }
    (output_dir / "virtual_prediction_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        summary = analyze(args.plan.resolve(), args.output.resolve())
    except (AnalysisError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps({key: summary[key] for key in ("status", "job_count_expected", "job_count_valid", "grid_decision")}, indent=2))
    return 0 if summary["status"] == "GATE24E_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
