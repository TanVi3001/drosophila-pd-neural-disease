from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.analyze_gate24e_blinded_prediction import (
    AnalysisError,
    PARAMETERS,
    SEEDS,
    analyze,
    decision_for_directions,
    validate_completed_job,
)


def _job(output: Path, *, condition: str, parameter: float, seed: int, index: int) -> dict:
    return {
        "order_index": index,
        "job_id": f"{condition}_{parameter}_{seed}",
        "condition": condition,
        "parameter": parameter,
        "seed": seed,
        "prepared_checkpoint_sha256": None if condition == "healthy" else "disease-checkpoint",
        "healthy_checkpoint_sha256": "healthy-checkpoint",
        "mapping_sha256": "mapping",
        "target_sha256": "target",
        "output_path": str(output),
        "required_metrics": ["median_planar_speed_mm_s", "distance_traveled_mm"],
    }


def _write_completed(job: dict, *, speed: float, distance: float, nan_rollout: bool = False) -> None:
    output = Path(job["output_path"])
    (output / "metrics").mkdir(parents=True, exist_ok=True)
    (output / "status.json").write_text(json.dumps({"status": "PASS"}) + "\n", encoding="utf-8")
    positions = np.asarray([[0.0, 0.0, 0.0], [speed, 0.0, 0.0], [2 * speed, 0.0, 0.0]])
    if nan_rollout:
        positions[1, 0] = np.nan
    np.savez(output / "rollout.npz", thorax=positions, timestamp_s=np.asarray([0.0, 1.0, 2.0]))
    (output / "metrics" / "metrics.json").write_text(
        json.dumps({"scalar_metrics": {"median_planar_speed_mm_s": speed, "distance_traveled_mm": distance}})
        + "\n",
        encoding="utf-8",
    )
    provenance = {
        key: job[key]
        for key in (
            "job_id",
            "condition",
            "parameter",
            "seed",
            "prepared_checkpoint_sha256",
            "healthy_checkpoint_sha256",
            "mapping_sha256",
            "target_sha256",
        )
    }
    (output / "adapter_job_provenance.json").write_text(json.dumps(provenance) + "\n", encoding="utf-8")


def _plan(tmp_path: Path, *, disease_speed_factor: float = 0.5, missing: tuple[str, float, int] | None = None, nan_job: tuple[str, float, int] | None = None) -> tuple[dict, Path]:
    jobs = []
    index = 1
    for seed in SEEDS:
        healthy = _job(tmp_path / f"healthy_{seed}", condition="healthy", parameter=0.0, seed=seed, index=index)
        index += 1
        jobs.append(healthy)
        if missing != ("healthy", 0.0, seed):
            _write_completed(healthy, speed=2.0, distance=4.0, nan_rollout=nan_job == ("healthy", 0.0, seed))
        for parameter in PARAMETERS:
            disease = _job(tmp_path / f"parkin_{parameter}_{seed}", condition="parkin", parameter=parameter, seed=seed, index=index)
            index += 1
            jobs.append(disease)
            if missing != ("parkin", parameter, seed):
                _write_completed(
                    disease,
                    speed=2.0 * disease_speed_factor,
                    distance=4.0 * disease_speed_factor,
                    nan_rollout=nan_job == ("parkin", parameter, seed),
                )
    plan = {
        "status": "READY_FOR_25_BLINDED_GPU_JOBS",
        "job_count": 25,
        "jobs": jobs,
        "holdout_status": "SEALED",
        "holdout_opened": False,
        "tuning_using_holdout": False,
        "posthoc_parameter_selection_allowed": False,
    }
    plan_path = tmp_path / "job_plan.json"
    plan_path.write_text(json.dumps(plan) + "\n", encoding="utf-8")
    return plan, plan_path


def test_all_four_parameter_levels_negative_are_supported(tmp_path: Path) -> None:
    _, plan_path = _plan(tmp_path, disease_speed_factor=0.5)
    summary = analyze(plan_path, tmp_path / "results")
    assert summary["status"] == "GATE24E_COMPLETE"
    assert summary["grid_decision"] == "VIRTUAL_DIRECTIONAL_PREDICTION_SUPPORTED"
    assert all(row["direction_pass"] for row in summary["parameters"])


def test_mixed_direction_is_inconclusive() -> None:
    assert decision_for_directions({0.25: True, 0.5: False, 0.75: True, 1.0: True}) == "DIRECTIONAL_VALIDATION_INCONCLUSIVE"


def test_maximal_level_not_impaired_is_not_supported() -> None:
    assert decision_for_directions({0.25: True, 0.5: True, 0.75: True, 1.0: False}) == "DIRECTIONAL_VALIDATION_NOT_SUPPORTED"


def test_missing_seed_is_incomplete(tmp_path: Path) -> None:
    _, plan_path = _plan(tmp_path, missing=("parkin", 0.5, 3))
    summary = analyze(plan_path, tmp_path / "results")
    assert summary["status"] == "GATE24E_INCOMPLETE_TECHNICAL_EXECUTION"
    assert summary["grid_decision"] == "GATE24E_INCOMPLETE_TECHNICAL_EXECUTION"
    assert summary["job_count_valid"] == 24


def test_nan_rollout_is_incomplete(tmp_path: Path) -> None:
    _, plan_path = _plan(tmp_path, nan_job=("parkin", 0.25, 0))
    summary = analyze(plan_path, tmp_path / "results")
    assert summary["status"] == "GATE24E_INCOMPLETE_TECHNICAL_EXECUTION"
    assert summary["job_count_valid"] == 24


def test_frames_do_not_increase_statistical_sample_size(tmp_path: Path) -> None:
    _, plan_path = _plan(tmp_path)
    summary = analyze(plan_path, tmp_path / "results")
    assert summary["statistical_unit"] == "seed"
    assert summary["frame_is_statistical_replicate"] is False
    assert summary["job_count_valid"] == 25


def test_secondary_distance_cannot_override_speed_failure(tmp_path: Path) -> None:
    plan, plan_path = _plan(tmp_path, disease_speed_factor=1.5)
    for job in plan["jobs"]:
        if job["condition"] == "parkin":
            _write_completed(job, speed=3.0, distance=1.0)
    plan_path.write_text(json.dumps(plan) + "\n", encoding="utf-8")
    summary = analyze(plan_path, tmp_path / "results")
    assert summary["grid_decision"] == "DIRECTIONAL_VALIDATION_NOT_SUPPORTED"


def test_analysis_does_not_select_a_best_parameter(tmp_path: Path) -> None:
    _, plan_path = _plan(tmp_path)
    summary = analyze(plan_path, tmp_path / "results")
    assert [row["parameter"] for row in summary["parameters"]] == list(PARAMETERS)
    assert "selected_parameter" not in summary


def test_exact_locked_seeds_and_parameters_are_reported(tmp_path: Path) -> None:
    _, plan_path = _plan(tmp_path)
    summary = analyze(plan_path, tmp_path / "results")
    assert summary["seed_list"] == list(SEEDS)
    assert [row["parameter"] for row in summary["parameters"]] == list(PARAMETERS)


def test_storage_probe_seed_9001_is_rejected_from_scientific_analysis(tmp_path: Path) -> None:
    plan, plan_path = _plan(tmp_path)
    plan["jobs"][0]["seed"] = 9001
    plan_path.write_text(json.dumps(plan) + "\n", encoding="utf-8")
    with pytest.raises(AnalysisError, match="locked seeds"):
        analyze(plan_path, tmp_path / "results")


def test_holdout_remains_sealed_and_biological_claim_is_forbidden(tmp_path: Path) -> None:
    _, plan_path = _plan(tmp_path)
    summary = analyze(plan_path, tmp_path / "results")
    assert summary["holdout_opened"] is False
    assert summary["tuning_using_holdout"] is False
    assert summary["posthoc_parameter_selection"] is False
    assert summary["biological_validation_claim"] == "NOT_ALLOWED_AT_GATE24E"


def test_observed_magnitude_cannot_edit_grid_label() -> None:
    assert decision_for_directions({parameter: False for parameter in PARAMETERS}) == "DIRECTIONAL_VALIDATION_NOT_SUPPORTED"


def test_completed_job_requires_provenance_and_pass_status(tmp_path: Path) -> None:
    job = _job(tmp_path / "job", condition="healthy", parameter=0.0, seed=0, index=1)
    _write_completed(job, speed=1.0, distance=2.0)
    row, errors = validate_completed_job(job)
    assert errors == []
    assert row is not None and row["qc_pass"] is True
    Path(job["output_path"], "adapter_job_provenance.json").unlink()
    row, errors = validate_completed_job(job)
    assert row is None
    assert "missing adapter_job_provenance.json" in errors


def test_derived_metric_does_not_use_runner_mean_field(tmp_path: Path) -> None:
    job = _job(tmp_path / "job", condition="healthy", parameter=0.0, seed=0, index=1)
    _write_completed(job, speed=1.0, distance=2.0)
    metrics_path = Path(job["output_path"], "metrics", "metrics.json")
    metrics_path.write_text(
        json.dumps({"scalar_metrics": {"walking_speed_mm_s": 99.0, "total_distance_mm": 2.0}}) + "\n",
        encoding="utf-8",
    )
    row, errors = validate_completed_job(job)
    assert errors == []
    assert row is not None and row["median_planar_speed_mm_s"] == 1.0
