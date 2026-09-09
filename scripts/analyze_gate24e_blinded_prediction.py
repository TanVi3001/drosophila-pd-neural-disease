"""Freeze the blinded Gate24E virtual prediction from the executed batch.

The analyzer is deliberately fail-closed. It accepts only the canonical
``scientific_batch_plan.json``, verifies the completed execution contract and
all 125 inventoried artifact hashes before reading a scientific metric, and
never reads a biological holdout.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = ROOT / "experiments/gate_24e_blinded_parkin_prediction"
MANIFEST_ROOT = EXPERIMENT_ROOT / "manifests"
RUNS_ROOT = EXPERIMENT_ROOT / "runs"
SCIENTIFIC_PLAN = MANIFEST_ROOT / "scientific_batch_plan.json"
STALE_JOB_PLAN = MANIFEST_ROOT / "job_plan.json"
EXECUTION_MANIFEST = MANIFEST_ROOT / "scientific_batch_execution.json"
ARTIFACT_INVENTORY = MANIFEST_ROOT / "scientific_batch_artifact_inventory.json"
DEFAULT_OUTPUT = EXPERIMENT_ROOT / "results"
FREEZE_MANIFEST = MANIFEST_ROOT / "immutable_virtual_prediction_freeze.json"
REPORT = ROOT / "docs/validation/gate24e_blinded_virtual_prediction_freeze.md"
EXECUTOR = ROOT / "scripts/run_gate24e_scientific_batch.py"

EXPECTED_PLAN_SHA256 = "4515e1916631b019711154dccb5fb887110d5572e3eb82b7ea5118c643db5aac"
EXPECTED_EXECUTOR_SHA256 = "4d10edecbc8d987285ea82eb36a7bcfd686da3abde3b5160a3dcec23a2e78f3f"
EXPECTED_PLAN_STATUS = "SCIENTIFIC_BATCH_PLAN_FROZEN"
EXPECTED_EXECUTION_STATUS = "GATE24E_25_JOB_SCIENTIFIC_BATCH_COMPLETE_UNANALYZED"
EXPECTED_INVENTORY_STATUS = "GATE24E_25_JOB_ARTIFACT_INVENTORY_COMPLETE"
EXPECTED_JOB_COUNT = 25
EXPECTED_ARTIFACT_COUNT = 125
REQUIRED_ARTIFACTS = (
    "status.json",
    "rollout.npz",
    "metadata.json",
    "manifest.json",
    "metrics/metrics.json",
)
PARAMETERS = (0.25, 0.50, 0.75, 1.00)
SEEDS = (0, 1, 2, 3, 4)
PRIMARY_METRIC = "median_planar_speed_mm_s"
SECONDARY_METRIC = "distance_traveled_mm"
ARTIFACT_DRIFT_STATUS = "VIRTUAL_PREDICTION_FREEZE_BLOCKED_ARTIFACT_DRIFT"
INCOMPLETE_STATUS = "GATE24E_INCOMPLETE_TECHNICAL_EXECUTION"
COMPUTED_STATUS = "GATE24E_VIRTUAL_PREDICTION_COMPUTED"
FROZEN_STATUS = "IMMUTABLE_VIRTUAL_PREDICTION_FROZEN"


class AnalysisError(RuntimeError):
    """Raised when the frozen analysis contract cannot be evaluated."""

    def __init__(self, message: str, *, status: str = INCOMPLETE_STATUS) -> None:
        super().__init__(message)
        self.status = status


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AnalysisError(f"Expected JSON object: {path}")
    return value


def _canonical_json_bytes(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            document,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _canonical_json_sha256(document: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(document)).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _scalar_metrics(document: dict[str, Any]) -> dict[str, Any]:
    value = document.get("scalar_metrics", {})
    return dict(value) if isinstance(value, dict) else {}


def _exact_metric(document: dict[str, Any], name: str) -> float | None:
    """Return only the named locked metric and reject conflicting duplicates."""

    candidates = []
    if name in document:
        candidates.append(document[name])
    scalars = _scalar_metrics(document)
    if name in scalars:
        candidates.append(scalars[name])
    finite = [float(value) for value in candidates if _finite(value)]
    if candidates and len(finite) != len(candidates):
        raise AnalysisError(f"Locked metric {name} is non-numeric or non-finite.")
    if len(finite) > 1 and any(value != finite[0] for value in finite[1:]):
        raise AnalysisError(f"Conflicting duplicate values for locked metric {name}.")
    return finite[0] if finite else None


def _first_array(arrays: Any, names: Iterable[str]) -> np.ndarray | None:
    for name in names:
        if name in arrays.files:
            return np.asarray(arrays[name], dtype=float)
    return None


def _derive_locked_metrics(rollout_path: Path) -> tuple[float, float, int]:
    """Apply the reviewed planar trajectory definition to a frozen rollout."""

    try:
        with np.load(rollout_path, allow_pickle=False) as arrays:
            positions = _first_array(arrays, ("thorax", "thorax_positions"))
            time_s = _first_array(arrays, ("timestamp_s", "time_s"))
    except (OSError, ValueError) as exc:
        raise AnalysisError(f"Cannot read frozen rollout {rollout_path}: {exc}") from exc
    if positions is None or time_s is None:
        raise AnalysisError(f"Reviewed trajectory channels are absent: {rollout_path}")
    if positions.ndim != 2 or positions.shape[1] < 2 or time_s.ndim != 1:
        raise AnalysisError(f"Reviewed trajectory channel shape is invalid: {rollout_path}")
    if len(positions) != len(time_s) or len(positions) < 2:
        raise AnalysisError(f"Trajectory frame count is invalid: {rollout_path}")
    if not np.all(np.isfinite(positions)) or not np.all(np.isfinite(time_s)):
        raise AnalysisError(f"Trajectory contains non-finite values: {rollout_path}")
    intervals = np.diff(time_s)
    if not np.all(intervals > 0):
        raise AnalysisError(f"Trajectory timestamps are not strictly increasing: {rollout_path}")
    planar_steps = np.linalg.norm(np.diff(positions[:, :2], axis=0), axis=1)
    planar_speed = planar_steps / intervals
    median_speed = float(np.median(planar_speed))
    distance = float(np.sum(planar_steps))
    if not _finite(median_speed) or not _finite(distance):
        raise AnalysisError(f"Derived locked metrics are non-finite: {rollout_path}")
    return median_speed, distance, len(positions)


def _expected_job_matrix() -> list[tuple[str, int, str, float]]:
    expected: list[tuple[str, int, str, float]] = []
    for seed in SEEDS:
        expected.append((f"seed{seed:02d}_healthy", seed, "healthy", 0.0))
        for parameter in PARAMETERS:
            label = f"{parameter:.2f}".replace(".", "")
            expected.append((f"seed{seed:02d}_parkin_p{label}", seed, "parkin", parameter))
    return expected


def load_scientific_plan(
    path: Path,
    *,
    expected_sha256: str = EXPECTED_PLAN_SHA256,
) -> dict[str, Any]:
    """Load only the frozen scientific plan; the historical job plan is invalid."""

    if path.name != SCIENTIFIC_PLAN.name or path.resolve() == STALE_JOB_PLAN.resolve():
        raise AnalysisError("Only scientific_batch_plan.json may source Gate24E analysis.")
    plan = _read_json(path)
    actual_sha = _canonical_json_sha256(plan)
    if actual_sha != expected_sha256:
        raise AnalysisError(
            f"Scientific plan SHA256 mismatch: expected {expected_sha256}, got {actual_sha}."
        )
    required = {
        "status": EXPECTED_PLAN_STATUS,
        "job_count": EXPECTED_JOB_COUNT,
        "healthy_job_count": 5,
        "parkin_job_count": 20,
        "technical_seed_excluded": 9001,
        "holdout": "SEALED",
        "tuning_allowed": False,
        "posthoc_selection_allowed": False,
        "primary_metric": PRIMARY_METRIC,
        "secondary_metric": SECONDARY_METRIC,
    }
    for key, expected in required.items():
        if plan.get(key) != expected:
            raise AnalysisError(f"Scientific plan contract mismatch: {key}.")
    if plan.get("scientific_seeds") != list(SEEDS):
        raise AnalysisError("Scientific analyzer accepts exactly seeds 0 through 4.")
    if plan.get("parameter_grid") != [0.0, *PARAMETERS]:
        raise AnalysisError("Scientific analyzer accepts only the preregistered grid.")
    jobs = plan.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != EXPECTED_JOB_COUNT:
        raise AnalysisError("Scientific plan must contain exactly 25 jobs.")
    expected_matrix = _expected_job_matrix()
    observed_matrix: list[tuple[str, int, str, float]] = []
    for index, job in enumerate(jobs, start=1):
        if not isinstance(job, dict):
            raise AnalysisError(f"Scientific job {index} is not an object.")
        if job.get("job_index") != index:
            raise AnalysisError("Scientific jobs are not in locked SEED_MAJOR order.")
        try:
            observed_matrix.append(
                (
                    str(job["job_id"]),
                    int(job["seed"]),
                    str(job["condition"]),
                    float(job["parameter"]),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise AnalysisError(f"Scientific job {index} is malformed.") from exc
    if observed_matrix != expected_matrix:
        raise AnalysisError("Scientific job matrix differs from the preregistered 25-job grid.")
    if any(condition == "parkin" and parameter == 0.0 for _, _, condition, parameter in observed_matrix):
        raise AnalysisError("Parkin parameter zero is forbidden; healthy is the reference.")
    if any(seed == 9001 for _, seed, _, _ in observed_matrix):
        raise AnalysisError("Technical seed 9001 is excluded from scientific analysis.")
    if len({job_id for job_id, _, _, _ in observed_matrix}) != EXPECTED_JOB_COUNT:
        raise AnalysisError("Scientific job IDs are not unique.")
    return plan


def validate_execution_manifest(
    path: Path,
    *,
    expected_plan_sha256: str,
    expected_job_ids: list[str],
) -> dict[str, Any]:
    execution = _read_json(path)
    required = {
        "status": EXPECTED_EXECUTION_STATUS,
        "planned_job_count": EXPECTED_JOB_COUNT,
        "executed_job_count": EXPECTED_JOB_COUNT,
        "completed_job_count": EXPECTED_JOB_COUNT,
        "failed_job_count": 0,
        "gpu_jobs_executed": EXPECTED_JOB_COUNT,
        "simulation_jobs_executed": EXPECTED_JOB_COUNT,
        "analysis_performed": False,
        "scientific_interpretation_performed": False,
        "scientific_batch_authorized": True,
        "holdout": "SEALED",
        "plan_sha256": expected_plan_sha256,
    }
    for key, expected in required.items():
        if execution.get(key) != expected:
            raise AnalysisError(f"Scientific execution contract mismatch: {key}.")
    if execution.get("completed_job_ids") != expected_job_ids:
        raise AnalysisError("Completed job IDs differ from the frozen scientific plan.")
    return execution


def _safe_artifact_path(
    repository_root: Path,
    runs_root: Path,
    relative: object,
) -> Path:
    if not isinstance(relative, str) or not relative:
        raise AnalysisError("Artifact inventory contains an invalid path.")
    relative_path = Path(relative)
    if relative_path.is_absolute():
        raise AnalysisError("Artifact inventory paths must be repository-relative.")
    candidate = (repository_root / relative_path).resolve()
    try:
        candidate.relative_to(runs_root.resolve())
    except ValueError as exc:
        raise AnalysisError("Artifact inventory path escapes the frozen runs directory.") from exc
    return candidate


def verify_artifact_inventory(
    path: Path,
    *,
    plan: dict[str, Any],
    expected_plan_sha256: str,
    repository_root: Path,
    runs_root: Path,
    expected_executor_sha256: str = EXPECTED_EXECUTOR_SHA256,
) -> dict[str, dict[str, Path]]:
    """Verify structure, size and SHA256 for all 125 files before metric reads."""

    inventory = _read_json(path)
    required = {
        "status": EXPECTED_INVENTORY_STATUS,
        "job_count": EXPECTED_JOB_COUNT,
        "artifact_count": EXPECTED_ARTIFACT_COUNT,
        "scientific_plan_sha256": expected_plan_sha256,
        "executor_sha256": expected_executor_sha256,
        "holdout": "SEALED",
        "analysis_performed": False,
        "scientific_interpretation_performed": False,
        "technical_artifact_qc": "PASS",
    }
    for key, expected in required.items():
        if inventory.get(key) != expected:
            raise AnalysisError(f"Artifact inventory contract mismatch: {key}.")
    rows = inventory.get("jobs")
    if not isinstance(rows, list) or len(rows) != EXPECTED_JOB_COUNT:
        raise AnalysisError("Artifact inventory must contain exactly 25 jobs.")
    plan_jobs = {str(job["job_id"]): job for job in plan["jobs"]}
    if [row.get("job_id") for row in rows if isinstance(row, dict)] != list(plan_jobs):
        raise AnalysisError("Artifact inventory job order differs from the scientific plan.")

    verified: dict[str, dict[str, Path]] = {}
    records_to_hash: list[tuple[str, str, Path, dict[str, Any]]] = []
    for inventory_row in rows:
        if not isinstance(inventory_row, dict):
            raise AnalysisError("Artifact inventory job row is malformed.")
        job_id = str(inventory_row.get("job_id", ""))
        job = plan_jobs.get(job_id)
        if job is None:
            raise AnalysisError(f"Artifact inventory has unknown job: {job_id}.")
        for key in ("job_index", "seed", "condition", "parameter"):
            if inventory_row.get(key) != job.get(key):
                raise AnalysisError(f"Artifact inventory {job_id} mismatch: {key}.")
        output_relative = inventory_row.get("output_relative_path")
        output = _safe_artifact_path(repository_root, runs_root, output_relative)
        if output.name != job_id:
            raise AnalysisError(f"Artifact inventory output does not match job ID: {job_id}.")
        if Path(str(job.get("output_directory", ""))).resolve() != output:
            raise AnalysisError(f"Plan output directory mismatch for {job_id}.")
        artifacts = inventory_row.get("artifacts")
        if not isinstance(artifacts, dict) or set(artifacts) != set(REQUIRED_ARTIFACTS):
            raise AnalysisError(f"Artifact inventory does not list exactly five required files for {job_id}.")
        verified[job_id] = {}
        for artifact_name in REQUIRED_ARTIFACTS:
            record = artifacts.get(artifact_name)
            if not isinstance(record, dict):
                raise AnalysisError(f"Malformed artifact record: {job_id}/{artifact_name}.")
            artifact_path = _safe_artifact_path(repository_root, runs_root, record.get("path"))
            if artifact_path != (output / Path(artifact_name)).resolve():
                raise AnalysisError(f"Artifact path mismatch: {job_id}/{artifact_name}.")
            verified[job_id][artifact_name] = artifact_path
            records_to_hash.append((job_id, artifact_name, artifact_path, record))
    if len(records_to_hash) != EXPECTED_ARTIFACT_COUNT:
        raise AnalysisError("Artifact inventory does not resolve to exactly 125 records.")

    drift: list[str] = []
    for job_id, artifact_name, artifact_path, record in records_to_hash:
        if not artifact_path.is_file():
            drift.append(f"{job_id}/{artifact_name}: missing")
            continue
        expected_size = record.get("size_bytes")
        if not isinstance(expected_size, int) or artifact_path.stat().st_size != expected_size:
            drift.append(f"{job_id}/{artifact_name}: byte-size mismatch")
            continue
        expected_hash = record.get("sha256")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            drift.append(f"{job_id}/{artifact_name}: invalid recorded SHA256")
            continue
        if _sha256(artifact_path) != expected_hash:
            drift.append(f"{job_id}/{artifact_name}: SHA256 mismatch")
    if drift:
        detail = "; ".join(drift[:5])
        if len(drift) > 5:
            detail += f"; plus {len(drift) - 5} more"
        raise AnalysisError(detail, status=ARTIFACT_DRIFT_STATUS)
    return verified


def _metric_frame_count(document: dict[str, Any]) -> int | None:
    value = document.get("frame_count")
    return int(value) if isinstance(value, int) and not isinstance(value, bool) and value >= 2 else None


def validate_completed_job(
    job: dict[str, Any],
    artifacts: dict[str, Path],
) -> tuple[dict[str, Any] | None, list[str]]:
    """Read one verified run and return its locked seed-level metrics."""

    errors: list[str] = []
    try:
        status = _read_json(artifacts["status.json"])
        manifest = _read_json(artifacts["manifest.json"])
        metadata = _read_json(artifacts["metadata.json"])
        metrics = _read_json(artifacts["metrics/metrics.json"])
    except (AnalysisError, OSError, ValueError, json.JSONDecodeError) as exc:
        return None, [str(exc)]
    if status.get("status") != "PASS" or status.get("simulation_run") is not True:
        errors.append("status.json does not record a completed simulation PASS")
    if manifest.get("artifact_profile") != "GATE24E_MEMORY_SAFE":
        errors.append("manifest artifact profile mismatch")
    simulation = metadata.get("simulation")
    if not isinstance(simulation, dict):
        errors.append("metadata simulation provenance missing")
    else:
        if simulation.get("random_seed") != job.get("seed"):
            errors.append("metadata seed mismatch")
        if simulation.get("brain_checkpoint_sha256") != job.get("checkpoint_sha256"):
            errors.append("metadata checkpoint mismatch")
    try:
        primary = _exact_metric(metrics, PRIMARY_METRIC)
        secondary = _exact_metric(metrics, SECONDARY_METRIC)
    except AnalysisError as exc:
        errors.append(str(exc))
        primary = secondary = None
    frame_count = _metric_frame_count(metrics)
    primary_provenance = "DIRECT_LOCKED_METRIC" if primary is not None else "DERIVED_FROM_FROZEN_ROLLOUT"
    secondary_provenance = "DIRECT_LOCKED_METRIC" if secondary is not None else "DERIVED_FROM_FROZEN_ROLLOUT"
    if primary is None or secondary is None:
        try:
            derived_primary, derived_secondary, derived_frames = _derive_locked_metrics(
                artifacts["rollout.npz"]
            )
            if primary is None:
                primary = derived_primary
            if secondary is None:
                secondary = derived_secondary
            if frame_count is None:
                frame_count = derived_frames
        except AnalysisError as exc:
            errors.append(str(exc))
    if frame_count is None:
        errors.append("valid frame_count is missing")
    if not _finite(primary) or not _finite(secondary):
        errors.append("locked primary or secondary metric is non-finite")
    if errors:
        return None, errors
    metric_provenance = (
        "DIRECT_LOCKED_METRIC"
        if primary_provenance == secondary_provenance == "DIRECT_LOCKED_METRIC"
        else "DERIVED_FROM_FROZEN_ROLLOUT"
    )
    return {
        "job_id": str(job["job_id"]),
        "condition": str(job["condition"]),
        "parameter": float(job["parameter"]),
        "seed": int(job["seed"]),
        PRIMARY_METRIC: float(primary),
        SECONDARY_METRIC: float(secondary),
        "primary_metric_provenance": primary_provenance,
        "secondary_metric_provenance": secondary_provenance,
        "metric_provenance": metric_provenance,
        "frame_count": int(frame_count),
        "statistical_unit": "seed",
        "qc_pass": True,
    }, []


def decision_for_directions(direction_pass: dict[float, bool]) -> str:
    """Apply the exact grid rule; the secondary metric is intentionally absent."""

    ordered = [bool(direction_pass.get(parameter, False)) for parameter in PARAMETERS]
    if all(ordered):
        return "VIRTUAL_DIRECTIONAL_PREDICTION_SUPPORTED"
    if not ordered[-1] or not any(ordered):
        return "DIRECTIONAL_VALIDATION_NOT_SUPPORTED"
    return "DIRECTIONAL_VALIDATION_INCONCLUSIVE"


def compute_prediction(
    plan: dict[str, Any],
    verified_artifacts: dict[str, dict[str, Path]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    virtual_rows: list[dict[str, Any]] = []
    failed_jobs: list[dict[str, Any]] = []
    for job in plan["jobs"]:
        row, errors = validate_completed_job(job, verified_artifacts[str(job["job_id"])])
        if row is None:
            failed_jobs.append({"job_id": job["job_id"], "errors": errors})
        else:
            virtual_rows.append(row)

    healthy = {row["seed"]: row for row in virtual_rows if row["condition"] == "healthy"}
    parkin = {
        (float(row["parameter"]), row["seed"]): row
        for row in virtual_rows
        if row["condition"] == "parkin"
    }
    paired_rows: list[dict[str, Any]] = []
    parameter_summaries: list[dict[str, Any]] = []
    directions: dict[float, bool] = {}
    for parameter in PARAMETERS:
        pairs: list[dict[str, Any]] = []
        for seed in SEEDS:
            control = healthy.get(seed)
            disease = parkin.get((parameter, seed))
            if control is None or disease is None:
                continue
            pair = {
                "parameter": parameter,
                "seed": seed,
                "healthy_job_id": control["job_id"],
                "parkin_job_id": disease["job_id"],
                "healthy_median_planar_speed_mm_s": control[PRIMARY_METRIC],
                "parkin_median_planar_speed_mm_s": disease[PRIMARY_METRIC],
                "paired_delta_speed_mm_s": disease[PRIMARY_METRIC] - control[PRIMARY_METRIC],
                "healthy_distance_traveled_mm": control[SECONDARY_METRIC],
                "parkin_distance_traveled_mm": disease[SECONDARY_METRIC],
                "qc_pass": True,
            }
            pairs.append(pair)
            paired_rows.append(pair)
        complete = len(pairs) == len(SEEDS)
        if complete:
            deltas = np.asarray([row["paired_delta_speed_mm_s"] for row in pairs], dtype=float)
            healthy_speed = np.asarray(
                [row["healthy_median_planar_speed_mm_s"] for row in pairs], dtype=float
            )
            parkin_speed = np.asarray(
                [row["parkin_median_planar_speed_mm_s"] for row in pairs], dtype=float
            )
            healthy_distance = np.asarray(
                [row["healthy_distance_traveled_mm"] for row in pairs], dtype=float
            )
            parkin_distance = np.asarray(
                [row["parkin_distance_traveled_mm"] for row in pairs], dtype=float
            )
            median_delta: float | None = float(np.median(deltas))
            median_healthy_speed: float | None = float(np.median(healthy_speed))
            median_parkin_speed: float | None = float(np.median(parkin_speed))
            speed_ratio: float | None = (
                float(median_parkin_speed / median_healthy_speed)
                if median_healthy_speed != 0
                else None
            )
            median_healthy_distance: float | None = float(np.median(healthy_distance))
            median_parkin_distance: float | None = float(np.median(parkin_distance))
            distance_ratio: float | None = (
                float(median_parkin_distance / median_healthy_distance)
                if median_healthy_distance != 0
                else None
            )
            direction = median_delta < 0
        else:
            median_delta = None
            median_healthy_speed = None
            median_parkin_speed = None
            speed_ratio = None
            median_healthy_distance = None
            median_parkin_distance = None
            distance_ratio = None
            direction = False
        directions[parameter] = direction if complete else False
        parameter_summaries.append(
            {
                "parameter": parameter,
                "valid_seed_count": len(pairs),
                "qc_pass": complete,
                "median_healthy_speed_mm_s": median_healthy_speed,
                "median_parkin_speed_mm_s": median_parkin_speed,
                "median_paired_delta_speed_mm_s": median_delta,
                "speed_ratio": speed_ratio,
                "median_healthy_distance_mm": median_healthy_distance,
                "median_parkin_distance_mm": median_parkin_distance,
                "distance_ratio": distance_ratio,
                "direction_pass": direction if complete else False,
            }
        )

    complete = (
        not failed_jobs
        and len(virtual_rows) == EXPECTED_JOB_COUNT
        and len(paired_rows) == len(PARAMETERS) * len(SEEDS)
        and all(row["valid_seed_count"] == len(SEEDS) and row["qc_pass"] for row in parameter_summaries)
    )
    grid_decision = decision_for_directions(directions) if complete else INCOMPLETE_STATUS
    provenance_counts = {
        name: sum(row["metric_provenance"] == name for row in virtual_rows)
        for name in ("DIRECT_LOCKED_METRIC", "DERIVED_FROM_FROZEN_ROLLOUT")
    }
    summary = {
        "status": COMPUTED_STATUS if complete else INCOMPLETE_STATUS,
        "job_count_expected": EXPECTED_JOB_COUNT,
        "job_count_valid": len(virtual_rows),
        "failed_jobs": failed_jobs,
        "artifact_qc": "PASS",
        "artifact_record_count_verified": EXPECTED_ARTIFACT_COUNT,
        "primary_validation_axis": "LOCOMOTOR_IMPAIRMENT_DIRECTION",
        "primary_metric": PRIMARY_METRIC,
        "secondary_metric": SECONDARY_METRIC,
        "primary_rule": "median_across_five_same_seed_paired_deltas_lt_0",
        "seed_list": list(SEEDS),
        "parameter_summaries": parameter_summaries,
        "grid_decision": grid_decision,
        "metric_provenance_counts": provenance_counts,
        "holdout": "SEALED",
        "holdout_opened": False,
        "tuning_using_holdout": False,
        "posthoc_parameter_selection": False,
        "statistical_unit": "seed",
        "frame_is_statistical_replicate": False,
        "biological_validation_claim": "NOT_ALLOWED_AT_GATE24E",
        "allowed_statement": "Frozen blinded computational prediction under the preregistered locomotor-direction protocol.",
    }
    return virtual_rows, paired_rows, parameter_summaries, summary


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_prediction_outputs(
    output_dir: Path,
    virtual_rows: list[dict[str, Any]],
    paired_rows: list[dict[str, Any]],
    parameter_summaries: list[dict[str, Any]],
    summary: dict[str, Any],
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    virtual_path = output_dir / "virtual_per_seed.csv"
    paired_path = output_dir / "paired_effects.csv"
    parameter_path = output_dir / "parameter_summary.csv"
    summary_path = output_dir / "virtual_prediction_summary.json"
    _write_csv(
        virtual_path,
        virtual_rows,
        [
            "job_id",
            "condition",
            "parameter",
            "seed",
            PRIMARY_METRIC,
            SECONDARY_METRIC,
            "primary_metric_provenance",
            "secondary_metric_provenance",
            "metric_provenance",
            "frame_count",
            "statistical_unit",
            "qc_pass",
        ],
    )
    _write_csv(
        paired_path,
        paired_rows,
        [
            "parameter",
            "seed",
            "healthy_job_id",
            "parkin_job_id",
            "healthy_median_planar_speed_mm_s",
            "parkin_median_planar_speed_mm_s",
            "paired_delta_speed_mm_s",
            "healthy_distance_traveled_mm",
            "parkin_distance_traveled_mm",
            "qc_pass",
        ],
    )
    _write_csv(
        parameter_path,
        parameter_summaries,
        [
            "parameter",
            "valid_seed_count",
            "qc_pass",
            "median_healthy_speed_mm_s",
            "median_parkin_speed_mm_s",
            "median_paired_delta_speed_mm_s",
            "speed_ratio",
            "median_healthy_distance_mm",
            "median_parkin_distance_mm",
            "distance_ratio",
            "direction_pass",
        ],
    )
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=True, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return [virtual_path, paired_path, parameter_path, summary_path]


def build_freeze_document(
    *,
    analysis_artifacts: list[Path],
    repository_root: Path,
    scientific_plan_sha256: str,
    scientific_plan_file_sha256: str,
    artifact_inventory_sha256: str,
    execution_manifest_sha256: str,
    analyzer_source_sha256: str,
    executor_sha256: str,
    runtime_commit: str,
    model_commit: str,
    grid_decision: str,
) -> dict[str, Any]:
    records = []
    for path in analysis_artifacts:
        try:
            relative = path.resolve().relative_to(repository_root.resolve()).as_posix()
        except ValueError:
            relative = path.resolve().as_posix()
        records.append(
            {
                "path": relative,
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    payload: dict[str, Any] = {
        "schema_version": "gate24e-immutable-virtual-prediction-freeze-v1",
        "status": FROZEN_STATUS,
        "analysis_artifacts": records,
        "source_scientific_plan_sha256": scientific_plan_sha256,
        "source_scientific_plan_file_sha256": scientific_plan_file_sha256,
        "source_artifact_inventory_sha256": artifact_inventory_sha256,
        "source_execution_manifest_sha256": execution_manifest_sha256,
        "analyzer_source_sha256": analyzer_source_sha256,
        "executor_sha256": executor_sha256,
        "runtime_commit": runtime_commit,
        "model_commit": model_commit,
        "grid_decision": grid_decision,
        "holdout": "SEALED",
        "holdout_opened": False,
        "tuning_using_holdout": False,
        "posthoc_parameter_selection": False,
        "biological_validation_claim": "NOT_ALLOWED_AT_GATE24E",
    }
    payload["virtual_prediction_freeze_sha256"] = _canonical_json_sha256(payload)
    return payload


def _write_report(
    path: Path,
    *,
    summary: dict[str, Any],
    freeze: dict[str, Any],
    starting_head: str,
) -> None:
    direct = summary["metric_provenance_counts"]["DIRECT_LOCKED_METRIC"]
    derived = summary["metric_provenance_counts"]["DERIVED_FROM_FROZEN_ROLLOUT"]
    lines = [
        "# Gate 24E-S4J: Frozen blinded virtual prediction",
        "",
        "## Provenance and execution gate",
        "",
        f"- Starting HEAD: `{starting_head}`.",
        f"- Scientific plan SHA256: `{freeze['source_scientific_plan_sha256']}`.",
        f"- Execution status: `{EXPECTED_EXECUTION_STATUS}`.",
        "- Artifact QC: `25/25` jobs and `125/125` recorded artifacts verified by SHA256.",
        f"- Analyzer SHA256: `{freeze['analyzer_source_sha256']}`.",
        f"- Metric provenance: `{direct}` direct locked metrics; `{derived}` derived from frozen rollout.",
        "",
        "## Locked decision",
        "",
        f"Primary rule: `{summary['primary_rule']}` using statistical unit `seed` and same-seed pairing.",
        "The secondary distance metric cannot override the primary speed decision.",
        "",
        "| Parameter | Valid seeds | Median paired delta (mm/s) | Direction |",
        "|---:|---:|---:|---|",
    ]
    for row in summary["parameter_summaries"]:
        delta = row["median_paired_delta_speed_mm_s"]
        delta_text = "NA" if delta is None else f"{delta:.12g}"
        direction = "PASS" if row["direction_pass"] else "FAIL"
        lines.append(
            f"| {row['parameter']:.2f} | {row['valid_seed_count']} | {delta_text} | {direction} |"
        )
    lines.extend(
        [
            "",
            f"- Grid decision: `{summary['grid_decision']}`.",
            f"- Prediction freeze SHA256: `{freeze['virtual_prediction_freeze_sha256']}`.",
            "",
            "## Scientific firewall",
            "",
            "- Biological holdout remained `SEALED`; it was not imported or compared.",
            "- Holdout tuning: `false`.",
            "- Post-hoc parameter selection: `false`.",
            "- Biological validation claim: `NOT_ALLOWED_AT_GATE24E`.",
            "- Allowed statement: \"Frozen blinded computational prediction under the preregistered locomotor-direction protocol.\"",
            "",
            "## Validation and handoff",
            "",
            "Static checks and the complete test suite are run after artifact generation; their exact command results are recorded in the task close-out and Git history.",
            "The commit containing this report is identified by Git history; the branch is pushed only after all checks pass.",
            "",
            "Next allowed action: `HUMAN_REVIEW_BEFORE_OPENING_GATE24E_BIOLOGICAL_HOLDOUT`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _assert_fresh_destination(output_dir: Path, freeze_path: Path) -> None:
    protected = [
        output_dir / "virtual_per_seed.csv",
        output_dir / "paired_effects.csv",
        output_dir / "parameter_summary.csv",
        output_dir / "virtual_prediction_summary.json",
        freeze_path,
    ]
    existing = [str(path) for path in protected if path.exists()]
    if existing:
        raise AnalysisError(
            "Virtual prediction is already present; immutable analysis cannot be rerun: "
            + ", ".join(existing)
        )


def analyze(
    *,
    plan_path: Path = SCIENTIFIC_PLAN,
    execution_path: Path = EXECUTION_MANIFEST,
    inventory_path: Path = ARTIFACT_INVENTORY,
    output_dir: Path = DEFAULT_OUTPUT,
    freeze_path: Path = FREEZE_MANIFEST,
    report_path: Path | None = REPORT,
    repository_root: Path = ROOT,
    runs_root: Path = RUNS_ROOT,
    expected_plan_sha256: str = EXPECTED_PLAN_SHA256,
    expected_executor_sha256: str = EXPECTED_EXECUTOR_SHA256,
    analyzer_source_path: Path = Path(__file__),
    starting_head: str = "5569774ebdb0401ab5cb9b37b34f20e6e0e9ab82",
) -> dict[str, Any]:
    _assert_fresh_destination(output_dir, freeze_path)
    plan = load_scientific_plan(plan_path, expected_sha256=expected_plan_sha256)
    expected_job_ids = [str(job["job_id"]) for job in plan["jobs"]]
    validate_execution_manifest(
        execution_path,
        expected_plan_sha256=expected_plan_sha256,
        expected_job_ids=expected_job_ids,
    )
    verified = verify_artifact_inventory(
        inventory_path,
        plan=plan,
        expected_plan_sha256=expected_plan_sha256,
        repository_root=repository_root,
        runs_root=runs_root,
        expected_executor_sha256=expected_executor_sha256,
    )
    virtual_rows, paired_rows, parameter_summaries, summary = compute_prediction(
        plan, verified
    )
    if summary["status"] != COMPUTED_STATUS:
        raise AnalysisError(
            "All 25 jobs passed artifact hashes but the locked metric/QC contract is incomplete."
        )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gate24e-s4j-", dir=output_dir.parent) as temporary:
        stage = Path(temporary)
        staged_artifacts = _write_prediction_outputs(
            stage,
            virtual_rows,
            paired_rows,
            parameter_summaries,
            summary,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        final_artifacts: list[Path] = []
        for staged in staged_artifacts:
            destination = output_dir / staged.name
            shutil.move(str(staged), destination)
            final_artifacts.append(destination)

    freeze = build_freeze_document(
        analysis_artifacts=final_artifacts,
        repository_root=repository_root,
        scientific_plan_sha256=expected_plan_sha256,
        scientific_plan_file_sha256=_sha256(plan_path),
        artifact_inventory_sha256=_sha256(inventory_path),
        execution_manifest_sha256=_sha256(execution_path),
        analyzer_source_sha256=_sha256(analyzer_source_path),
        executor_sha256=expected_executor_sha256,
        runtime_commit=str(plan["runtime_commit"]),
        model_commit=str(plan["model_commit"]),
        grid_decision=str(summary["grid_decision"]),
    )
    freeze_path.parent.mkdir(parents=True, exist_ok=True)
    freeze_path.write_text(
        json.dumps(freeze, ensure_ascii=True, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if report_path is not None:
        _write_report(report_path, summary=summary, freeze=freeze, starting_head=starting_head)
    return {**summary, "virtual_prediction_freeze_sha256": freeze["virtual_prediction_freeze_sha256"]}


def main() -> int:
    try:
        summary = analyze()
    except (AnalysisError, OSError, ValueError, json.JSONDecodeError) as exc:
        status = exc.status if isinstance(exc, AnalysisError) else INCOMPLETE_STATUS
        print(json.dumps({"status": status, "error": str(exc)}, indent=2))
        return 2
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "status",
                    "job_count_expected",
                    "job_count_valid",
                    "grid_decision",
                    "virtual_prediction_freeze_sha256",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
