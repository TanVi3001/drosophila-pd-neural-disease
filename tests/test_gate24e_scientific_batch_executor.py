"""Contract tests for the frozen Gate24E scientific batch executor."""

from __future__ import annotations

import copy
import json
import inspect
from pathlib import Path

import pytest

from scripts import run_gate24e_scientific_batch as executor
from scripts.prepare_gate24e_scientific_batch_plan import build_plan


def _plan() -> dict:
    return json.loads(executor.PLAN_PATH.read_text(encoding="utf-8"))


def _initial_manifest() -> dict:
    return json.loads(executor.EXECUTION_MANIFEST.read_text(encoding="utf-8"))


def test_exact_plan_sha_and_job_counts() -> None:
    plan = _plan()
    assert executor.canonical_plan_sha256(plan) == executor.EXPECTED_PLAN_SHA256
    assert plan["job_count"] == 25
    assert plan["healthy_job_count"] == 5
    assert plan["parkin_job_count"] == 20


def test_seed_major_order_and_exact_condition_matrix() -> None:
    jobs = executor.validate_plan(_plan())["jobs"]
    assert [job["job_index"] for job in jobs] == list(range(1, 26))
    for offset, seed in enumerate(range(5)):
        block = jobs[offset * 5 : offset * 5 + 5]
        assert [job["seed"] for job in block] == [seed] * 5
        assert [job["condition"] for job in block] == ["healthy", "parkin", "parkin", "parkin", "parkin"]
        assert [job["parameter"] for job in block] == [0.0, 0.25, 0.5, 0.75, 1.0]


def test_no_p0_parkin_no_technical_seed_and_unique_outputs() -> None:
    jobs = executor.validate_plan(_plan())["jobs"]
    assert not any(job["condition"] == "parkin" and job["parameter"] == 0.0 for job in jobs)
    assert not any(job["seed"] == executor.TECHNICAL_SEED for job in jobs)
    assert len({job["job_id"] for job in jobs}) == 25
    assert len({job["output_directory"] for job in jobs}) == 25


def test_runtime_and_artifact_contract_is_frozen() -> None:
    plan = executor.validate_plan(_plan())
    assert plan["runtime_commit"] == executor.EXPECTED_RUNTIME_COMMIT
    assert plan["runtime_python"] == str(executor.EXPECTED_RUNTIME_PYTHON)
    assert plan["runtime_root"] == str(executor.EXPECTED_RUNTIME_ROOT)
    assert plan["artifact_profile"] == executor.EXPECTED_ARTIFACT_PROFILE


def test_activation_and_initial_execution_state_are_required() -> None:
    plan = executor.validate_plan(_plan())
    activation = json.loads(executor.ACTIVATION_PATH.read_text(encoding="utf-8"))
    executor.validate_activation(activation, plan)
    executor.validate_initial_execution_manifest(_initial_manifest())
    assert _initial_manifest()["status"] == "NOT_EXECUTED"
    assert _initial_manifest()["completed_job_count"] == 0


def test_remaining_storage_formula_reproduces_locked_initial_requirement() -> None:
    assert executor.remaining_storage_requirement(25) == 17_548_739_588
    assert executor.remaining_storage_requirement(0) == 801_228_758


def test_storage_rule_is_strictly_greater_than() -> None:
    required = executor.remaining_storage_requirement(25)
    assert not (required > required)
    assert required + 1 > required


def test_completion_contract_accepts_only_complete_technical_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "output"
    (output / "metrics").mkdir(parents=True)
    (output / "status.json").write_text(
        json.dumps({"status": "PASS", "simulation_run": True}), encoding="utf-8"
    )
    (output / "manifest.json").write_text(
        json.dumps({"artifact_profile": executor.EXPECTED_ARTIFACT_PROFILE}), encoding="utf-8"
    )
    for relative in ("rollout.npz", "metadata.json", "metrics/metrics.json"):
        (output / relative).write_bytes(b"technical placeholder")
    (output / "progress.log").write_text("Progress: 100000/100000\n", encoding="utf-8")
    result = executor.validate_job_output(output)
    assert result["completion_marker_observed"] is True
    assert result["artifact_bytes"] > 0


def test_partial_progress_is_rejected(tmp_path: Path) -> None:
    output = tmp_path / "output"
    (output / "metrics").mkdir(parents=True)
    (output / "status.json").write_text(
        json.dumps({"status": "PASS", "simulation_run": True}), encoding="utf-8"
    )
    (output / "manifest.json").write_text(
        json.dumps({"artifact_profile": executor.EXPECTED_ARTIFACT_PROFILE}), encoding="utf-8"
    )
    for relative in ("rollout.npz", "metadata.json", "metrics/metrics.json"):
        (output / relative).write_bytes(b"x")
    (output / "progress.log").write_text("Progress: 99999/100000\n", encoding="utf-8")
    with pytest.raises(executor.TechnicalStop, match="completion marker"):
        executor.validate_job_output(output)


def test_bad_status_or_artifact_profile_is_rejected(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    (output / "status.json").write_text(
        json.dumps({"status": "FAIL", "simulation_run": False}), encoding="utf-8"
    )
    with pytest.raises(executor.TechnicalStop, match="status contract"):
        executor.validate_job_output(output)


def test_metrics_are_not_read_during_completion_check(tmp_path: Path) -> None:
    output = tmp_path / "output"
    (output / "metrics").mkdir(parents=True)
    (output / "status.json").write_text(
        json.dumps({"status": "PASS", "simulation_run": True}), encoding="utf-8"
    )
    (output / "manifest.json").write_text(
        json.dumps({"artifact_profile": executor.EXPECTED_ARTIFACT_PROFILE}), encoding="utf-8"
    )
    for relative in ("rollout.npz", "metadata.json"):
        (output / relative).write_bytes(b"x")
    (output / "metrics/metrics.json").write_text("not scientific analysis", encoding="utf-8")
    (output / "progress.log").write_text("100000/100000", encoding="utf-8")
    assert executor.validate_job_output(output)["completion_marker_observed"] is True


def test_executor_has_no_resume_retry_or_overwrite_flags() -> None:
    parser = executor._parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--resume"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--retry"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--dry-run", "--execute"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--skip"])


def test_dry_run_is_read_only_and_prints_no_scientific_metrics(capsys: pytest.CaptureFixture[str]) -> None:
    before = executor.EXECUTION_MANIFEST.read_bytes()
    executor.dry_run(
        _plan(),
        {"status": "READY_FOR_GATE24E_25_JOB_SCIENTIFIC_BATCH"},
        {"python": "3.12.10", "flygym": "2.1.0", "torch": "2.5.1+cu121"},
    )
    captured = capsys.readouterr().out
    assert "READY_TO_EXECUTE_EXACT_GATE24E_25_JOB_BATCH" in captured
    assert "median_planar_speed_mm_s" not in captured
    assert "distance_traveled_mm" not in captured
    assert executor.EXECUTION_MANIFEST.read_bytes() == before
    assert not executor.OUTPUT_ROOT.exists()
    assert not executor.LOG_PATH.exists()


def test_runtime_git_contract_is_frozen_and_clean() -> None:
    executor.validate_runtime_git_contract()


def test_executor_does_not_invoke_the_scientific_analyzer() -> None:
    source = inspect.getsource(executor)
    assert "analyze_gate24e_blinded_prediction" not in source
    assert "analyze_gate24e" not in source


def test_return_code_failure_stops_without_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    execution_path = tmp_path / "scientific_batch_execution.json"
    execution_path.write_text(
        json.dumps(_initial_manifest()), encoding="utf-8"
    )
    output_root = tmp_path / "runs"
    log_path = tmp_path / "execution.log"
    monkeypatch.setattr(executor, "EXECUTION_MANIFEST", execution_path)
    monkeypatch.setattr(executor, "OUTPUT_ROOT", output_root)
    monkeypatch.setattr(executor, "LOG_PATH", log_path)
    monkeypatch.setattr(executor, "run_preflight_audit", lambda: {"status": "READY", "blockers": []})
    monkeypatch.setattr(executor, "validate_runtime_git_contract", lambda: None)
    monkeypatch.setattr(executor, "_live_free_bytes", lambda: 100_000_000_000)
    calls: list[Sequence[str]] = []

    def fail_once(command: Sequence[str]) -> tuple[int, float, float]:
        calls.append(command)
        return 7, 0.0, 1.0

    with pytest.raises(executor.TechnicalStop, match="returned 7"):
        executor.execute_batch(
            _plan(),
            environment={"python": "3.12.10"},
            child_runner=fail_once,
        )
    assert len(calls) == 1
    stopped = json.loads(execution_path.read_text(encoding="utf-8"))
    assert stopped["status"] == "GATE24E_SCIENTIFIC_BATCH_TECHNICAL_STOP"
    assert stopped["failed_job_count"] == 1
    assert stopped["next_allowed_action"] == "HUMAN_REVIEW_GATE24E_SCIENTIFIC_BATCH_TECHNICAL_STOP"


@pytest.mark.parametrize("failure", [KeyboardInterrupt, MemoryError])
def test_runtime_failure_types_stop_without_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: type[BaseException],
) -> None:
    execution_path = tmp_path / "scientific_batch_execution.json"
    execution_path.write_text(json.dumps(_initial_manifest()), encoding="utf-8")
    monkeypatch.setattr(executor, "EXECUTION_MANIFEST", execution_path)
    monkeypatch.setattr(executor, "OUTPUT_ROOT", tmp_path / "runs")
    monkeypatch.setattr(executor, "LOG_PATH", tmp_path / "execution.log")
    monkeypatch.setattr(executor, "run_preflight_audit", lambda: {"status": "READY", "blockers": []})
    monkeypatch.setattr(executor, "validate_runtime_git_contract", lambda: None)
    monkeypatch.setattr(executor, "_live_free_bytes", lambda: 100_000_000_000)

    def fail(command: Sequence[str]) -> tuple[int, float, float]:
        raise failure()

    with pytest.raises(executor.TechnicalStop):
        executor.execute_batch(
            _plan(),
            environment={"python": "3.12.10"},
            child_runner=fail,
        )
    stopped = json.loads(execution_path.read_text(encoding="utf-8"))
    assert stopped["status"] == "GATE24E_SCIENTIFIC_BATCH_TECHNICAL_STOP"
    assert stopped["failed_job_count"] == 1


def test_existing_output_root_blocks_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    execution_path = tmp_path / "scientific_batch_execution.json"
    execution_path.write_text(json.dumps(_initial_manifest()), encoding="utf-8")
    output_root = tmp_path / "runs"
    output_root.mkdir()
    monkeypatch.setattr(executor, "EXECUTION_MANIFEST", execution_path)
    monkeypatch.setattr(executor, "OUTPUT_ROOT", output_root)
    with pytest.raises(executor.BatchContractError, match="output root already exists"):
        executor.execute_batch(_plan(), environment={"python": "3.12.10"})


def test_plan_builder_matches_frozen_plan_shape() -> None:
    generated = build_plan()
    frozen = _plan()
    assert generated == frozen
