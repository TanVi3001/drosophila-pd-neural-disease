"""Contract tests for the frozen Gate24E scientific batch executor."""

from __future__ import annotations

import io
import hashlib
import json
import inspect
from pathlib import Path
import subprocess
import sys
from typing import Sequence

import pytest

from scripts import run_gate24e_scientific_batch as executor
from scripts.prepare_gate24e_scientific_batch_plan import build_plan


_TEST_OUTPUT_ROOT: Path | None = None


def _plan() -> dict:
    plan = json.loads(executor.PLAN_PATH.read_text(encoding="utf-8"))
    if _TEST_OUTPUT_ROOT is not None:
        for job in plan["jobs"]:
            job["output_directory"] = str(_TEST_OUTPUT_ROOT / job["job_id"])
    return plan


def _initial_manifest() -> dict:
    # The repository manifest is now immutable post-execution evidence. Unit
    # tests derive an isolated pre-execution state instead of rewriting or
    # pretending that the completed 25-job record is still NOT_EXECUTED.
    manifest = json.loads(executor.EXECUTION_MANIFEST.read_text(encoding="utf-8"))
    manifest.update(
        status="NOT_EXECUTED",
        executed_job_count=0,
        completed_job_count=0,
        failed_job_count=0,
        gpu_jobs_executed=0,
        simulation_jobs_executed=0,
        completed_job_ids=[],
        artifact_byte_total=0,
        current_job_id=None,
        current_job_index=None,
        current_job_status="NOT_STARTED",
        last_completed_job_id=None,
        last_completed_job_index=None,
    )
    return manifest


def _write_complete_artifacts(
    output: Path,
    *,
    status: str = "PASS",
    simulation_run: bool = True,
    include_rollout: bool = True,
) -> None:
    (output / "metrics").mkdir(parents=True)
    (output / "status.json").write_text(
        json.dumps({"status": status, "simulation_run": simulation_run}),
        encoding="utf-8",
    )
    (output / "manifest.json").write_text(
        json.dumps({"artifact_profile": executor.EXPECTED_ARTIFACT_PROFILE}),
        encoding="utf-8",
    )
    if include_rollout:
        (output / "rollout.npz").write_bytes(b"technical placeholder")
    (output / "metadata.json").write_bytes(b"technical placeholder")
    (output / "metrics/metrics.json").write_text(
        "scientific scalars are intentionally not parsed",
        encoding="utf-8",
    )


def _patch_execution_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    execution_path = tmp_path / "scientific_batch_execution.json"
    execution_path.write_text(json.dumps(_initial_manifest()), encoding="utf-8")
    monkeypatch.setattr(executor, "EXECUTION_MANIFEST", execution_path)
    monkeypatch.setattr(executor, "OUTPUT_ROOT", tmp_path / "runs")
    monkeypatch.setattr(executor, "LOG_PATH", tmp_path / "execution.log")
    monkeypatch.setattr(executor, "validate_plan", lambda plan: dict(plan))
    monkeypatch.setattr(executor, "validate_activation", lambda activation, plan: None)
    monkeypatch.setattr(executor, "run_preflight_audit", lambda: {"status": "READY"})
    monkeypatch.setattr(executor, "validate_runtime_git_contract", lambda: None)
    monkeypatch.setattr(executor, "_live_free_bytes", lambda: 100_000_000_000)
    monkeypatch.setattr(sys.modules[__name__], "_TEST_OUTPUT_ROOT", tmp_path / "runs")
    return execution_path


def _child_result(*, return_code: int = 0, marker: bool = True) -> executor.ChildRunResult:
    return executor.ChildRunResult(
        return_code=return_code,
        started_epoch=1_700_000_000.0,
        ended_epoch=1_700_000_001.0,
        completion_marker_observed=marker,
        captured_output_bytes=128,
    )


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
    execution = _initial_manifest()
    assert execution["status"] == "NOT_EXECUTED"
    assert execution["executed_job_count"] == 0
    assert execution["completed_job_count"] == 0
    assert execution["failed_job_count"] == 0
    assert execution["gpu_jobs_executed"] == 0
    assert execution["simulation_jobs_executed"] == 0


def test_executor_amendment_records_exact_old_and_new_hashes() -> None:
    amendment_path = (
        executor.ROOT
        / "experiments/gate_24e_blinded_parkin_prediction/manifests/"
        "scientific_batch_executor_amendment.json"
    )
    amendment = json.loads(amendment_path.read_text(encoding="utf-8"))
    script_sha256 = hashlib.sha256(Path(executor.__file__).read_bytes()).hexdigest()
    assert amendment["status"] == "EXECUTOR_TECHNICAL_AMENDMENT_COMPLETE"
    assert amendment["previous_executor_commit"] == "f0b41f97171e81a296967f026a7370c1a56f3290"
    assert amendment["previous_executor_sha256"] == (
        "8cab483f60e0cd3a45d43196d5c1401c77ff68b2e430bd2bed82043308192f84"
    )
    assert amendment["amended_executor_sha256"] == script_sha256
    assert amendment["scientific_plan_sha256"] == executor.EXPECTED_PLAN_SHA256
    assert amendment["scientific_contract_changed"] is False
    assert amendment["holdout"] == "SEALED"
    assert amendment["holdout_opened"] is False
    assert amendment["scientific_jobs_executed"] == 0
    assert amendment["gpu_executed"] is False
    assert amendment["simulation_executed"] is False


def test_remaining_storage_formula_reproduces_locked_initial_requirement() -> None:
    assert executor.remaining_storage_requirement(25) == 17_548_739_588
    assert executor.remaining_storage_requirement(0) == 801_228_758


def test_storage_rule_is_strictly_greater_than() -> None:
    required = executor.remaining_storage_requirement(25)
    assert not (required > required)
    assert required + 1 > required


def test_completion_contract_accepts_only_complete_technical_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "output"
    _write_complete_artifacts(output)
    result = executor.validate_job_output(output, completion_marker_observed=True)
    assert result["completion_marker_observed"] is True
    assert result["artifact_bytes"] > 0
    assert not list(output.rglob("*.log"))


def test_partial_progress_is_rejected(tmp_path: Path) -> None:
    output = tmp_path / "output"
    _write_complete_artifacts(output)
    marker, _ = executor._stream_marker_result(io.BytesIO(b"Progress: 80000/100000\n"))
    assert marker is False
    with pytest.raises(executor.TechnicalStop, match="completion marker"):
        executor.validate_job_output(output, completion_marker_observed=marker)


def test_exact_captured_stdout_marker_is_accepted() -> None:
    marker, captured_bytes = executor._stream_marker_result(
        io.BytesIO(b"runtime output\nProgress: 100000/100000\n")
    )
    assert marker is True
    assert captured_bytes == len(b"runtime output\nProgress: 100000/100000\n")


def test_missing_captured_stdout_marker_is_rejected(tmp_path: Path) -> None:
    output = tmp_path / "output"
    _write_complete_artifacts(output)
    marker, _ = executor._stream_marker_result(io.BytesIO(b"runtime output without progress\n"))
    assert marker is False
    with pytest.raises(executor.TechnicalStop, match="captured child output"):
        executor.validate_job_output(output, completion_marker_observed=marker)


def test_bad_status_or_artifact_profile_is_rejected(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    (output / "status.json").write_text(
        json.dumps({"status": "FAIL", "simulation_run": False}), encoding="utf-8"
    )
    with pytest.raises(executor.TechnicalStop, match="status contract"):
        executor.validate_job_output(output, completion_marker_observed=True)


def test_missing_rollout_is_rejected_after_marker_capture(tmp_path: Path) -> None:
    output = tmp_path / "output"
    _write_complete_artifacts(output, include_rollout=False)
    with pytest.raises(executor.TechnicalStop, match="required output missing"):
        executor.validate_job_output(output, completion_marker_observed=True)


def test_simulation_run_false_is_rejected_after_marker_capture(tmp_path: Path) -> None:
    output = tmp_path / "output"
    _write_complete_artifacts(output, simulation_run=False)
    with pytest.raises(executor.TechnicalStop, match="status contract"):
        executor.validate_job_output(output, completion_marker_observed=True)


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
    assert executor.validate_job_output(
        output, completion_marker_observed=True
    )["completion_marker_observed"] is True


def test_child_capture_is_silent_and_success_output_is_not_persisted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    original_temporary_file = executor.tempfile.TemporaryFile

    def temporary_file(**kwargs):
        return original_temporary_file(dir=tmp_path, **kwargs)

    monkeypatch.setattr(executor.tempfile, "TemporaryFile", temporary_file)
    result = executor._run_child(
        [sys.executable, "-c", "print('Progress: 100000/100000')"]
    )
    captured = capsys.readouterr()
    assert result.return_code == 0
    assert result.completion_marker_observed is True
    assert result.captured_output_bytes > 0
    assert captured.out == ""
    assert captured.err == ""
    assert list(tmp_path.iterdir()) == []


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


def test_dry_run_is_read_only_and_prints_no_scientific_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    execution_path = _patch_execution_paths(tmp_path, monkeypatch)
    before = execution_path.read_bytes()
    executor.dry_run(
        _plan(),
        {"status": "READY_FOR_GATE24E_25_JOB_SCIENTIFIC_BATCH"},
        {"python": "3.12.10", "flygym": "2.1.0", "torch": "2.5.1+cu121"},
    )
    captured = capsys.readouterr().out
    assert "READY_TO_EXECUTE_EXACT_GATE24E_25_JOB_BATCH" in captured
    assert "median_planar_speed_mm_s" not in captured
    assert "distance_traveled_mm" not in captured
    assert execution_path.read_bytes() == before
    assert not executor.OUTPUT_ROOT.exists()
    assert not executor.LOG_PATH.exists()


def test_runtime_git_contract_is_frozen_and_clean() -> None:
    executor.validate_runtime_git_contract()


def test_executor_does_not_invoke_the_scientific_analyzer() -> None:
    source = inspect.getsource(executor)
    assert "analyze_gate24e_blinded_prediction" not in source
    assert "analyze_gate24e" not in source


def test_return_code_failure_stops_without_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    execution_path = _patch_execution_paths(tmp_path, monkeypatch)
    calls: list[Sequence[str]] = []

    def fail_once(command: Sequence[str]) -> executor.ChildRunResult:
        calls.append(command)
        launched = json.loads(execution_path.read_text(encoding="utf-8"))
        assert launched["executed_job_count"] == 1
        assert launched["current_job_index"] == 1
        assert launched["current_job_id"] == "seed00_healthy"
        assert launched["current_job_status"] == "LAUNCHED"
        return _child_result(return_code=7, marker=False)

    with pytest.raises(executor.TechnicalStop, match="returned 7"):
        executor.execute_batch(
            _plan(),
            environment={"python": "3.12.10"},
            child_runner=fail_once,
        )
    assert len(calls) == 1
    stopped = json.loads(execution_path.read_text(encoding="utf-8"))
    assert stopped["status"] == "GATE24E_SCIENTIFIC_BATCH_TECHNICAL_STOP"
    assert stopped["executed_job_count"] == 1
    assert stopped["completed_job_count"] == 0
    assert stopped["failed_job_count"] == 1
    assert stopped["current_job_status"] == "FAILED"
    assert stopped["next_allowed_action"] == "HUMAN_REVIEW_GATE24E_SCIENTIFIC_BATCH_TECHNICAL_STOP"


@pytest.mark.parametrize(
    "failure",
    [
        executor.TechnicalStop("KeyboardInterrupt: current child terminated; no retry"),
        MemoryError(),
    ],
)
def test_converted_child_failure_types_stop_without_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
) -> None:
    execution_path = _patch_execution_paths(tmp_path, monkeypatch)

    def fail(command: Sequence[str]) -> executor.ChildRunResult:
        raise failure

    with pytest.raises(executor.TechnicalStop):
        executor.execute_batch(
            _plan(),
            environment={"python": "3.12.10"},
            child_runner=fail,
        )
    stopped = json.loads(execution_path.read_text(encoding="utf-8"))
    assert stopped["status"] == "GATE24E_SCIENTIFIC_BATCH_TECHNICAL_STOP"
    assert stopped["executed_job_count"] == 1
    assert stopped["failed_job_count"] == 1
    assert stopped["gpu_jobs_executed"] == 0
    assert stopped["simulation_jobs_executed"] == 0


def test_run_child_converts_keyboard_interrupt_and_terminates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class InterruptedProcess:
        terminated = False
        killed = False
        wait_count = 0

        def wait(self, timeout=None):
            self.wait_count += 1
            if self.wait_count == 1:
                raise KeyboardInterrupt
            return -15

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True

    process = InterruptedProcess()
    monkeypatch.setattr(executor.subprocess, "Popen", lambda *args, **kwargs: process)
    with pytest.raises(executor.TechnicalStop, match="KeyboardInterrupt"):
        executor._run_child(["technical-test-child"])
    assert process.terminated is True
    assert process.killed is False


def test_run_child_kills_only_after_termination_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StuckProcess:
        terminated = False
        killed = False
        first_wait = True

        def wait(self, timeout=None):
            if self.first_wait:
                self.first_wait = False
                raise KeyboardInterrupt
            if timeout is not None and not self.killed:
                raise subprocess.TimeoutExpired(cmd="technical-test-child", timeout=timeout)
            return -9

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True

    process = StuckProcess()
    monkeypatch.setattr(executor.subprocess, "Popen", lambda *args, **kwargs: process)
    with pytest.raises(executor.TechnicalStop, match="KeyboardInterrupt"):
        executor._run_child(["technical-test-child"])
    assert process.terminated is True
    assert process.killed is True


def test_one_valid_job_updates_all_completion_counters_before_prelaunch_stop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution_path = _patch_execution_paths(tmp_path, monkeypatch)
    runtime_checks = 0

    def runtime_contract() -> None:
        nonlocal runtime_checks
        runtime_checks += 1
        if runtime_checks == 2:
            raise executor.BatchContractError("test runtime drift")

    monkeypatch.setattr(executor, "validate_runtime_git_contract", runtime_contract)
    monkeypatch.setattr(
        executor,
        "validate_job_output",
        lambda output, **kwargs: {
            "artifact_bytes": 10,
            "completion_marker_observed": True,
            "simulation_run": True,
        },
    )
    with pytest.raises(executor.TechnicalStop, match="runtime provenance drift"):
        executor.execute_batch(
            _plan(),
            environment={"python": "3.12.10"},
            child_runner=lambda command: _child_result(),
        )
    stopped = json.loads(execution_path.read_text(encoding="utf-8"))
    assert stopped["executed_job_count"] == 1
    assert stopped["completed_job_count"] == 1
    assert stopped["failed_job_count"] == 0
    assert stopped["gpu_jobs_executed"] == 1
    assert stopped["simulation_jobs_executed"] == 1


def test_second_launched_job_failure_preserves_truthful_counters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution_path = _patch_execution_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(
        executor,
        "validate_job_output",
        lambda output, **kwargs: {
            "artifact_bytes": 10,
            "completion_marker_observed": True,
            "simulation_run": True,
        },
    )
    calls = 0

    def second_fails(command: Sequence[str]) -> executor.ChildRunResult:
        nonlocal calls
        calls += 1
        return _child_result(return_code=0 if calls == 1 else 9)

    with pytest.raises(executor.TechnicalStop, match="returned 9"):
        executor.execute_batch(
            _plan(),
            environment={"python": "3.12.10"},
            child_runner=second_fails,
        )
    stopped = json.loads(execution_path.read_text(encoding="utf-8"))
    assert calls == 2
    assert stopped["executed_job_count"] == 2
    assert stopped["completed_job_count"] == 1
    assert stopped["failed_job_count"] == 1
    assert stopped["gpu_jobs_executed"] == 1
    assert stopped["simulation_jobs_executed"] == 1


@pytest.mark.parametrize(
    "reason",
    [
        "required output missing: rollout.npz",
        "status contract failed",
        "completion marker missing from captured child output",
    ],
)
def test_completion_contract_failure_stops_before_later_job_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reason: str,
) -> None:
    execution_path = _patch_execution_paths(tmp_path, monkeypatch)
    calls = 0

    def child(command: Sequence[str]) -> executor.ChildRunResult:
        nonlocal calls
        calls += 1
        return _child_result(marker="completion marker" not in reason)

    monkeypatch.setattr(
        executor,
        "validate_job_output",
        lambda output, **kwargs: (_ for _ in ()).throw(executor.TechnicalStop(reason)),
    )
    with pytest.raises(executor.TechnicalStop, match=reason.split(":", 1)[0]):
        executor.execute_batch(
            _plan(), environment={"python": "3.12.10"}, child_runner=child
        )
    stopped = json.loads(execution_path.read_text(encoding="utf-8"))
    assert calls == 1
    assert stopped["executed_job_count"] == 1
    assert stopped["completed_job_count"] == 0
    assert stopped["failed_job_count"] == 1
    assert stopped["gpu_jobs_executed"] == 0
    assert stopped["simulation_jobs_executed"] == 0


def test_full_mocked_batch_reaches_exact_counter_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution_path = _patch_execution_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(
        executor,
        "validate_job_output",
        lambda output, **kwargs: {
            "artifact_bytes": 10,
            "completion_marker_observed": True,
            "simulation_run": True,
        },
    )
    completed = executor.execute_batch(
        _plan(),
        environment={"python": "3.12.10"},
        child_runner=lambda command: _child_result(),
    )
    persisted = json.loads(execution_path.read_text(encoding="utf-8"))
    assert completed == persisted
    assert persisted["status"] == "GATE24E_25_JOB_SCIENTIFIC_BATCH_COMPLETE_UNANALYZED"
    assert persisted["executed_job_count"] == 25
    assert persisted["completed_job_count"] == 25
    assert persisted["failed_job_count"] == 0
    assert persisted["gpu_jobs_executed"] == 25
    assert persisted["simulation_jobs_executed"] == 25


def test_storage_equality_blocks_before_any_child_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution_path = _patch_execution_paths(tmp_path, monkeypatch)
    required = executor.remaining_storage_requirement(25)
    monkeypatch.setattr(executor, "_live_free_bytes", lambda: required)
    calls = 0

    def child(command: Sequence[str]) -> executor.ChildRunResult:
        nonlocal calls
        calls += 1
        return _child_result()

    with pytest.raises(executor.TechnicalStop, match="storage safety"):
        executor.execute_batch(
            _plan(), environment={"python": "3.12.10"}, child_runner=child
        )
    stopped = json.loads(execution_path.read_text(encoding="utf-8"))
    assert calls == 0
    assert stopped["executed_job_count"] == 0
    assert stopped["completed_job_count"] == 0
    assert stopped["failed_job_count"] == 0


def test_runtime_drift_blocks_before_any_child_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution_path = _patch_execution_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(
        executor,
        "validate_runtime_git_contract",
        lambda: (_ for _ in ()).throw(executor.BatchContractError("drift")),
    )
    calls = 0

    def child(command: Sequence[str]) -> executor.ChildRunResult:
        nonlocal calls
        calls += 1
        return _child_result()

    with pytest.raises(executor.TechnicalStop, match="runtime provenance drift"):
        executor.execute_batch(
            _plan(), environment={"python": "3.12.10"}, child_runner=child
        )
    stopped = json.loads(execution_path.read_text(encoding="utf-8"))
    assert calls == 0
    assert stopped["executed_job_count"] == 0
    assert stopped["failed_job_count"] == 0


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
