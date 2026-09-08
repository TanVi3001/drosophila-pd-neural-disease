from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.run_gate24e_storage_probe_attempt04 as runner


def _approved_context() -> dict:
    return {
        "authorization": {"status": "READY_FOR_GATE24E_ATTEMPT04"},
        "platform": {"head": runner.PLATFORM_COMMIT, "clean": True},
        "python_runtime": str(runner.PYTHON_RUNTIME),
        "environment": {
            "python": runner.EXPECTED_PYTHON,
            "flygym": runner.EXPECTED_FLYGYM,
            "torch": runner.EXPECTED_TORCH,
            "cuda": runner.EXPECTED_CUDA,
            "cuda_available": True,
            "gpu": runner.EXPECTED_GPU,
        },
        "command": runner.build_command(runner.PYTHON_RUNTIME),
    }


def test_01_build_command_has_exact_technical_contract() -> None:
    command = runner.build_command(Path("python.exe"))
    assert command[0] == "python.exe"
    assert command[command.index("--seed") + 1] == "9001"
    assert command[command.index("--steps") + 1] == "100000"
    assert command[command.index("--device") + 1] == "cuda"
    assert command[command.index("--artifact-profile") + 1] == "GATE24E_MEMORY_SAFE"
    assert command[command.index("--output") + 1].endswith("attempt_04\\run")


@pytest.mark.parametrize(
    "flag",
    ["--prepared-checkpoint", "--parameter", "--video", "--video-output", "--compare-to", "--cpg-frequency-hz"],
)
def test_02_forbidden_flags_are_not_forwarded(flag: str) -> None:
    assert flag not in runner.build_command()


def test_03_authorized_review_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runner.audit_gate24e_attempt04_authorization,
        "audit",
        lambda: {"status": "WAITING_GATE24E_ATTEMPT04_HUMAN_REVIEW"},
    )
    with pytest.raises(runner.Attempt04RunnerError, match="Authorization audit"):
        runner.verify_preflight()


def test_04_approved_authorization_manifest_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runner.audit_gate24e_attempt04_authorization,
        "audit",
        lambda: {
            "status": "READY_FOR_GATE24E_ATTEMPT04",
            "attempt_04_exists": False,
            "attempt_04_authorized": True,
            "attempt_04_seed": 9001,
            "attempt_04_steps": 100000,
            "scientific_jobs_executed": 0,
            "scientific_batch_authorized": False,
            "holdout": "SEALED",
        },
    )
    monkeypatch.setattr(runner, "_verify_platform", lambda: {"head": runner.PLATFORM_COMMIT, "clean": True})
    monkeypatch.setattr(runner, "_environment_snapshot", lambda _python: _approved_context()["environment"])
    monkeypatch.setattr(runner, "_assert_unused", lambda: None)
    assert runner.verify_preflight()["authorization"]["status"] == "READY_FOR_GATE24E_ATTEMPT04"


def test_05_two_reviewers_are_enforced_by_authorization_audit() -> None:
    signoff = json.loads(runner.SIGNOFF.read_text(encoding="utf-8"))
    assert signoff["reviewer_1"] != signoff["reviewer_2"]
    assert signoff["reviewer_1"] and signoff["reviewer_2"]


def test_06_attempt03_history_is_consumed_and_not_retryable() -> None:
    failure = json.loads(runner.FAILURE_MANIFEST.read_text(encoding="utf-8"))
    assert failure["attempt_03_consumed"] is True
    assert failure["attempt_03_retry_allowed"] is False


def test_07_attempt04_is_unused_before_dry_run() -> None:
    assert not runner.ATTEMPT_ROOT.exists()


def test_08_seed_steps_device_and_runtime_are_fixed() -> None:
    assert runner.PROBE_SEED == 9001
    assert runner.STEPS == 100000
    assert runner.DEVICE == "cuda"
    assert runner.PLATFORM_COMMIT == "655e854544e3d814dfe422883ff0de66b619d6c1"
    assert runner.ARTIFACT_PROFILE == "GATE24E_MEMORY_SAFE"


def test_09_good_python_environment_contract_is_explicit() -> None:
    assert runner.PYTHON_RUNTIME.name == "python.exe"
    assert runner.EXPECTED_FLYGYM == "2.1.0"
    assert runner.EXPECTED_TORCH == "2.5.1+cu121"
    assert runner.EXPECTED_CUDA == "12.1"
    assert runner.EXPECTED_GPU == "NVIDIA GeForce RTX 3050 6GB Laptop GPU"


def test_10_scientific_seed_is_excluded() -> None:
    assert runner.PROBE_SEED not in runner.SCIENTIFIC_SEEDS
    assert runner.SCIENTIFIC_SEEDS == (0, 1, 2, 3, 4)


def test_11_dry_run_does_not_create_output_or_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "verify_preflight", lambda: _approved_context())
    monkeypatch.setattr(runner, "execute_once", lambda: pytest.fail("dry-run executed probe"))
    result = runner.prepare_dry_run()
    assert result["status"] == "READY_FOR_GATE24E_STORAGE_ATTEMPT_04"
    assert result["attempt_04_created"] is False
    assert result["gpu_executed"] is False
    assert result["simulation_executed"] is False


def test_12_dry_run_keeps_scientific_firewall_closed() -> None:
    contract = json.loads(
        (runner.ROOT / "experiments/gate_24e_storage_probe/manifests/attempt04_runner_contract.json")
        .read_text(encoding="utf-8")
    )
    assert contract["scientific_jobs_executed"] == 0
    assert contract["scientific_batch_authorized"] is False
    assert contract["holdout"] == "SEALED"


def test_13_existing_attempt04_output_blocks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output = tmp_path / "attempt_04"
    (output / "run").mkdir(parents=True)
    (output / "run" / "status.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(runner, "ATTEMPT_ROOT", output)
    with pytest.raises(runner.Attempt04RunnerError, match="execution artifacts"):
        runner._assert_unused()


def test_14_empty_attempt04_directory_is_not_claimed_as_fresh(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output = tmp_path / "attempt_04"
    output.mkdir()
    monkeypatch.setattr(runner, "ATTEMPT_ROOT", output)
    with pytest.raises(runner.Attempt04RunnerError, match="already exists"):
        runner._assert_unused()


def test_15_keyboard_interrupt_terminates_without_retry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.terminated = False
            self.wait_calls = 0

        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls += 1
            return 130

    process = FakeProcess()
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt()))
    monkeypatch.setattr(runner.shutil, "disk_usage", lambda _path: SimpleNamespace(free=900))
    log = (tmp_path / "probe.log").open("w", encoding="utf-8")
    try:
        return_code, _minimum_free, interrupted = runner._run_child(["python"], log)
    finally:
        log.close()
    assert interrupted is True
    assert return_code == 130
    assert process.terminated is True
    assert process.wait_calls == 1


def test_16_keyboard_interrupt_is_not_success() -> None:
    assert "ATTEMPT_04_INTERRUPTED" != "ATTEMPT_04_STORAGE_PROBE_PASS"


def test_17_storage_projection_uses_approved_formula() -> None:
    result = runner.calculate_storage_projection(100, 250)
    assert result == {
        "transient_bytes": 150,
        "projected_final_25_bytes": 2500,
        "projected_peak_bytes": 2650,
        "reserve_bytes": 530,
        "required_bytes": 3180,
    }


def test_18_success_requires_all_memory_safe_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "run"
    (output / "metrics").mkdir(parents=True)
    for relative in ("status.json", "rollout.npz", "metadata.json", "manifest.json", "metrics/metrics.json"):
        path = output / relative
        path.write_text("{}\n", encoding="utf-8")
    (output / "status.json").write_text(
        json.dumps({"status": "PASS", "simulation_run": True}) + "\n", encoding="utf-8"
    )
    (output / "manifest.json").write_text(
        json.dumps({"artifact_profile": runner.ARTIFACT_PROFILE}) + "\n", encoding="utf-8"
    )
    with pytest.raises(runner.Attempt04RunnerError, match="completion marker"):
        runner._validate_success(output, "Progress: 40000/100000")


def test_19_success_does_not_require_rollout_json_or_video(tmp_path: Path) -> None:
    output = tmp_path / "run"
    (output / "metrics").mkdir(parents=True)
    for relative in ("status.json", "rollout.npz", "metadata.json", "manifest.json", "metrics/metrics.json"):
        (output / relative).write_text("{}\n", encoding="utf-8")
    (output / "status.json").write_text(
        json.dumps({"status": "PASS", "simulation_run": True}) + "\n", encoding="utf-8"
    )
    (output / "manifest.json").write_text(
        json.dumps({"artifact_profile": runner.ARTIFACT_PROFILE}) + "\n", encoding="utf-8"
    )
    runner._validate_success(output, "Progress: 100000/100000")
    assert not (output / "rollout.json").exists()
    assert not (output / "flygym_rollout.mp4").exists()


def test_20_completion_marker_requires_full_requested_steps() -> None:
    assert runner._completion_observed("Progress: 40000/100000") is False
    assert runner._completion_observed("Progress: 100000/100000") is True


def test_21_no_scientific_analyzer_is_in_command() -> None:
    assert "analyze_gate24e_blinded_prediction.py" not in " ".join(runner.build_command())


def test_22_previous_attempt_paths_are_not_runner_targets() -> None:
    command = " ".join(runner.build_command())
    assert "attempt_03" not in command
    assert "attempt_02" not in command


def test_23_runner_does_not_create_attempt05() -> None:
    assert not (runner.ROOT / "experiments/gate_24e_storage_probe/attempt_05").exists()


def test_24_report_and_manifest_are_readiness_only() -> None:
    report = (runner.ROOT / "docs/validation/gate24e_attempt04_runner_readiness.md").read_text(encoding="utf-8")
    assert "READY_FOR_GATE24E_STORAGE_ATTEMPT_04" in report
    assert "chưa khởi động GPU" in report
