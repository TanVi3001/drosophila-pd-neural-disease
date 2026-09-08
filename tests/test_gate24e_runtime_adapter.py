from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.run_gate24e_runtime_adapter import (
    AdapterError,
    build_job_plan,
    execute_jobs,
    valid_pass_result,
    write_command_manifest,
    write_execution_manifest,
    write_job_plan,
)


PLAN = build_job_plan()


def _jobs() -> list[dict]:
    return PLAN["jobs"]


def _temporary_job(tmp_path: Path, index: int = 0) -> dict:
    job = deepcopy(_jobs()[index])
    job["output_path"] = str(tmp_path / job["job_id"])
    return job


def _write_valid_result(job: dict, *, speed: float = 1.0, distance: float = 2.0) -> None:
    output = Path(job["output_path"])
    (output / "metrics").mkdir(parents=True)
    (output / "status.json").write_text(json.dumps({"status": "PASS"}) + "\n", encoding="utf-8")
    (output / "rollout.json").write_text("{}\n", encoding="utf-8")
    (output / "metrics" / "metrics.json").write_text(
        json.dumps(
            {
                "scalar_metrics": {
                    "median_planar_speed_mm_s": speed,
                    "distance_traveled_mm": distance,
                }
            }
        )
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
    (output / "adapter_job_provenance.json").write_text(
        json.dumps(provenance) + "\n", encoding="utf-8"
    )


def test_job_count_is_exactly_25() -> None:
    assert PLAN["job_count"] == 25
    assert len(_jobs()) == 25


def test_job_counts_are_five_healthy_and_twenty_parkin() -> None:
    assert PLAN["healthy_job_count"] == 5
    assert PLAN["parkin_job_count"] == 20


def test_each_seed_has_one_healthy_and_four_parkin_jobs() -> None:
    for seed in PLAN["seed_list"]:
        jobs = [job for job in _jobs() if job["seed"] == seed]
        assert len(jobs) == 5
        assert [job["condition"] for job in jobs] == ["healthy", "parkin", "parkin", "parkin", "parkin"]


def test_parameter_grid_is_read_from_frozen_manifest() -> None:
    assert PLAN["parameter_grid"] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert sorted({job["parameter"] for job in _jobs()}) == PLAN["parameter_grid"]


def test_no_separate_zero_parameter_parkin_job_exists() -> None:
    assert not any(job["condition"] == "parkin" and job["parameter"] == 0.0 for job in _jobs())
    assert all(job["condition"] == "healthy" for job in _jobs() if job["parameter"] == 0.0)


def test_execution_order_is_seed_major() -> None:
    expected = []
    for seed in PLAN["seed_list"]:
        expected.extend(
            [(seed, "healthy", 0.0), (seed, "parkin", 0.25), (seed, "parkin", 0.5), (seed, "parkin", 0.75), (seed, "parkin", 1.0)]
        )
    actual = [(job["seed"], job["condition"], job["parameter"]) for job in _jobs()]
    assert actual == expected
    assert [job["order_index"] for job in _jobs()] == list(range(1, 26))


def test_healthy_jobs_use_no_prepared_disease_checkpoint() -> None:
    for job in _jobs():
        if job["condition"] == "healthy":
            assert job["prepared_checkpoint_path"] is None
            assert job["prepared_checkpoint_sha256"] is None
            assert "--prepared-checkpoint" not in job["command"]


def test_parkin_jobs_select_checkpoint_from_grid_and_record_sha() -> None:
    for job in _jobs():
        if job["condition"] != "parkin":
            continue
        checkpoint = Path(job["prepared_checkpoint_path"])
        assert checkpoint.is_file()
        assert "--prepared-checkpoint" in job["command"]
        assert job["prepared_checkpoint_sha256"]
        assert len(job["prepared_checkpoint_sha256"]) == 64


def test_all_commands_use_canonical_runner_without_parameter_argument() -> None:
    for job in _jobs():
        assert "run_neural_experiment.py" in job["command"][1]
        assert "--parameter" not in job["command"]


def test_all_jobs_share_frozen_runtime_and_physics() -> None:
    assert {job["device"] for job in _jobs()} == {"cuda"}
    assert {job["steps"] for job in _jobs()} == {100000}
    assert {job["duration_s"] for job in _jobs()} == {10.0}
    assert {job["timestep_s"] for job in _jobs()} == {0.0001}
    assert len({job["platform_commit"] for job in _jobs()}) == 1


def test_all_jobs_share_mapping_target_and_healthy_checkpoint_provenance() -> None:
    assert len({job["mapping_sha256"] for job in _jobs()}) == 1
    assert len({job["target_sha256"] for job in _jobs()}) == 1
    assert len({job["healthy_checkpoint_sha256"] for job in _jobs()}) == 1


def test_output_paths_and_job_ids_are_unique_and_parameter_labeled() -> None:
    assert len({job["output_path"] for job in _jobs()}) == 25
    assert len({job["job_id"] for job in _jobs()}) == 25
    assert all(
        (f"parkin_{job['parameter']:.2f}".replace(".", "_") in Path(job["output_path"]).parts)
        if job["condition"] == "parkin"
        else "healthy" in Path(job["output_path"]).parts
        for job in _jobs()
    )


def test_plan_records_holdout_and_posthoc_locks() -> None:
    assert PLAN["holdout_status"] == "SEALED"
    assert PLAN["holdout_opened"] is False
    assert PLAN["tuning_using_holdout"] is False
    assert PLAN["posthoc_parameter_selection_allowed"] is False


def test_dry_run_plan_records_zero_execution_and_no_video() -> None:
    assert PLAN["gpu_jobs_executed"] == 0
    assert PLAN["simulation_jobs_executed"] == 0
    assert PLAN["video"] is False


def test_required_metrics_are_taken_from_frozen_contract() -> None:
    assert PLAN["required_metrics"] == ["median_planar_speed_mm_s", "distance_traveled_mm"]
    assert all(job["required_metrics"] == PLAN["required_metrics"] for job in _jobs())


def test_valid_pass_result_requires_finite_primary_metrics_and_provenance(tmp_path: Path) -> None:
    job = _temporary_job(tmp_path)
    _write_valid_result(job)
    assert valid_pass_result(job)
    Path(job["output_path"], "adapter_job_provenance.json").write_text(
        json.dumps({"job_id": "wrong"}) + "\n", encoding="utf-8"
    )
    assert not valid_pass_result(job)


def test_valid_pass_result_rejects_nonfinite_metric(tmp_path: Path) -> None:
    job = _temporary_job(tmp_path)
    _write_valid_result(job, speed=float("nan"))
    assert not valid_pass_result(job)


def test_valid_pass_result_requires_rollout_artifact(tmp_path: Path) -> None:
    job = _temporary_job(tmp_path)
    _write_valid_result(job)
    Path(job["output_path"], "rollout.json").unlink()
    assert not valid_pass_result(job)


def test_existing_valid_pass_is_never_overwritten(tmp_path: Path) -> None:
    job = _temporary_job(tmp_path)
    _write_valid_result(job)
    calls: list[list[str]] = []

    def forbidden_runner(command: list[str], **_: object) -> SimpleNamespace:
        calls.append(command)
        raise AssertionError("valid PASS must not be rerun")

    execute_jobs({"status": PLAN["status"], "jobs": [job]}, runner=forbidden_runner)
    assert calls == []


def test_technical_failure_stops_batch_without_retry(tmp_path: Path) -> None:
    first = _temporary_job(tmp_path, 0)
    second = _temporary_job(tmp_path, 1)
    calls: list[list[str]] = []

    def failing_runner(command: list[str], **_: object) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(returncode=17)

    with pytest.raises(AdapterError, match="TECHNICAL_FAILURE"):
        execute_jobs({"status": PLAN["status"], "jobs": [first, second]}, runner=failing_runner)
    assert len(calls) == 1
    assert json.loads(Path(first["output_path"], "adapter_failure.json").read_text(encoding="utf-8"))["automatic_retry"] is False

    with pytest.raises(AdapterError, match="already recorded"):
        execute_jobs({"status": PLAN["status"], "jobs": [first, second]}, runner=failing_runner)
    assert len(calls) == 1


def test_existing_nonpass_status_is_not_retried(tmp_path: Path) -> None:
    job = _temporary_job(tmp_path)
    output = Path(job["output_path"])
    output.mkdir(parents=True)
    (output / "status.json").write_text(json.dumps({"status": "FAILED"}) + "\n", encoding="utf-8")

    with pytest.raises(AdapterError, match="refusing automatic retry"):
        execute_jobs({"status": PLAN["status"], "jobs": [job]}, runner=lambda *_args, **_kwargs: None)


def test_job_plan_and_manifests_are_immutable_by_matrix_hash(tmp_path: Path) -> None:
    job_path = tmp_path / "job_plan.json"
    command_path = tmp_path / "command_manifest.json"
    execution_path = tmp_path / "execution_manifest.json"
    write_job_plan(PLAN, job_path)
    write_command_manifest(PLAN, command_path)
    write_execution_manifest(PLAN, path=execution_path)
    write_job_plan(PLAN, job_path)
    write_command_manifest(PLAN, command_path)
    write_execution_manifest(PLAN, path=execution_path)
    assert json.loads(job_path.read_text(encoding="utf-8"))["job_count"] == 25
    assert json.loads(command_path.read_text(encoding="utf-8"))["commands_executed"] is False
    assert json.loads(execution_path.read_text(encoding="utf-8"))["status"] == "NOT_EXECUTED"


def test_parameter_grid_has_no_posthoc_seed_or_parameter_selection() -> None:
    assert PLAN["seed_list"] == [0, 1, 2, 3, 4]
    assert PLAN["parameter_policy"] == "PREREGISTERED_GRID_NO_SINGLE_BIOLOGICAL_PARAMETER"


def test_no_job_is_marked_as_holdout_or_calibration() -> None:
    assert all(job["condition"] in {"healthy", "parkin"} for job in _jobs())
    assert "holdout" not in json.dumps(PLAN["jobs"]).lower()
