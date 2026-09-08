from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

import scripts.run_gate24e_storage_probe_attempt03 as attempt03
from scripts.run_neural_experiment import (
    AMENDED_PLATFORM_COMMIT,
    FROZEN_CPG_DEFAULT_HZ,
    FROZEN_FLYGYM_VERSION,
    LEGACY_ARTIFACT_PROFILE,
    MEMORY_SAFE_ARTIFACT_PROFILE,
    build_platform_command,
    validate_runtime_contract,
)


def _ready_audit() -> dict:
    return {
        "status": "READY_FOR_ATTEMPT_03",
        "runtime_review_state": "APPROVED",
        "reviewer_1": "Tuan Le",
        "reviewer_2": "To Dang Minh Tuan",
        "attempt_03_authorized": True,
        "scientific_batch_authorized": False,
        "holdout": "SEALED",
        "scientific_jobs_executed": 0,
        "blockers": [],
    }


def _approved_signoff() -> dict:
    return {
        "status": "RUNTIME_AMENDMENT_APPROVED",
        "decision": "APPROVED_FOR_GATE24E_RUNTIME_AMENDMENT",
        "reviewer_1": "Tuan Le",
        "reviewer_2": "To Dang Minh Tuan",
        "attempt_03_authorized": True,
        "scientific_batch_authorized": False,
    }


def test_01_original_runtime_legacy_is_allowed() -> None:
    validate_runtime_contract(
        platform_commit=attempt03.ORIGINAL_COMMIT,
        artifact_profile=LEGACY_ARTIFACT_PROFILE,
    )


def test_02_amended_runtime_memory_safe_is_allowed() -> None:
    validate_runtime_contract(
        platform_commit=AMENDED_PLATFORM_COMMIT,
        artifact_profile=MEMORY_SAFE_ARTIFACT_PROFILE,
    )


def test_03_unknown_runtime_commit_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="UNKNOWN_PLATFORM_COMMIT"):
        validate_runtime_contract(platform_commit="unknown", artifact_profile=LEGACY_ARTIFACT_PROFILE)


def test_04_wrong_profile_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="INCOMPATIBLE_RUNTIME_PROFILE"):
        validate_runtime_contract(
            platform_commit=AMENDED_PLATFORM_COMMIT,
            artifact_profile=LEGACY_ARTIFACT_PROFILE,
        )


def test_05_amended_commit_is_exact() -> None:
    assert attempt03.PLATFORM_COMMIT == "655e854544e3d814dfe422883ff0de66b619d6c1"


def test_06_amended_worktree_must_be_clean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        attempt03,
        "_git_text",
        lambda _path, *args: AMENDED_PLATFORM_COMMIT if args == ("rev-parse", "HEAD") else "",
    )
    assert attempt03._verify_clean_platform(tmp_path, AMENDED_PLATFORM_COMMIT)["clean"] is True


def test_07_attempt_id_is_exact() -> None:
    assert attempt03.ATTEMPT_ID == "attempt_03"


def test_08_probe_seed_is_9001() -> None:
    assert attempt03.PROBE_SEED == 9001


def test_09_storage_seed_is_excluded_from_scientific_seeds() -> None:
    assert attempt03.PROBE_SEED not in attempt03.SCIENTIFIC_SEEDS
    assert list(attempt03.SCIENTIFIC_SEEDS) == [0, 1, 2, 3, 4]


def test_10_steps_are_locked_to_100000() -> None:
    assert attempt03.STEPS == 100000


def test_11_command_has_no_prepared_parkin_checkpoint() -> None:
    assert "--prepared-checkpoint" not in attempt03.build_attempt_command()


def test_12_command_has_no_parameter_flag() -> None:
    assert "--parameter" not in attempt03.build_attempt_command()


def test_13_command_has_no_video() -> None:
    command = attempt03.build_attempt_command()
    assert "--video" not in command
    assert "--video-output" not in command


def test_14_command_has_no_compare_to() -> None:
    assert "--compare-to" not in attempt03.build_attempt_command()


def test_15_downstream_command_contains_memory_safe_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "scripts.run_neural_experiment._git_commit",
        lambda _path: AMENDED_PLATFORM_COMMIT,
    )
    monkeypatch.setattr(
        "scripts.run_neural_experiment._installed_distribution_version",
        lambda _python, _distribution: FROZEN_FLYGYM_VERSION,
    )
    command = build_platform_command(
        brain_python=Path("python.exe"),
        platform_root=tmp_path,
        run_brain_root=tmp_path / "brain",
        seed=attempt03.PROBE_SEED,
        steps=attempt03.STEPS,
        device=attempt03.DEVICE,
        output=tmp_path / "run",
        stimulus="p9",
        requested_frequency_hz=FROZEN_CPG_DEFAULT_HZ,
        artifact_profile=MEMORY_SAFE_ARTIFACT_PROFILE,
    )
    assert command[command.index("--artifact-profile") + 1] == MEMORY_SAFE_ARTIFACT_PROFILE


def test_16_downstream_command_omits_cpg_frequency_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("scripts.run_neural_experiment._git_commit", lambda _path: AMENDED_PLATFORM_COMMIT)
    monkeypatch.setattr(
        "scripts.run_neural_experiment._installed_distribution_version",
        lambda _python, _distribution: FROZEN_FLYGYM_VERSION,
    )
    command = build_platform_command(
        brain_python=Path("python.exe"),
        platform_root=tmp_path,
        run_brain_root=tmp_path / "brain",
        seed=attempt03.PROBE_SEED,
        steps=attempt03.STEPS,
        device=attempt03.DEVICE,
        output=tmp_path / "run",
        stimulus="p9",
        requested_frequency_hz=FROZEN_CPG_DEFAULT_HZ,
        artifact_profile=MEMORY_SAFE_ARTIFACT_PROFILE,
    )
    assert "--cpg-frequency-hz" not in command


def test_17_human_amendment_approval_is_required() -> None:
    pending = _approved_signoff()
    pending["status"] = "WAITING_RUNTIME_AMENDMENT_REVIEW"
    pending["decision"] = "PENDING_HUMAN_REVIEW"
    pending["attempt_03_authorized"] = False
    with pytest.raises(attempt03.Attempt03Error, match="signoff is not approved"):
        attempt03._validate_approval_documents(_ready_audit(), pending, attempt03.AMENDMENT_SHA256)


def test_18_two_reviewers_are_required() -> None:
    signoff = _approved_signoff()
    signoff["reviewer_2"] = ""
    with pytest.raises(attempt03.Attempt03Error, match="Two distinct"):
        attempt03._validate_approval_documents(_ready_audit(), signoff, attempt03.AMENDMENT_SHA256)


def test_19_holdout_must_be_sealed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(attempt03, "_read_json", lambda _path: {"status": "OPEN"})
    with pytest.raises(attempt03.Attempt03Error, match="not sealed"):
        attempt03._verify_sealed_holdout()


def test_20_scientific_batch_remains_unauthorized() -> None:
    signoff = _approved_signoff()
    signoff["scientific_batch_authorized"] = True
    with pytest.raises(attempt03.Attempt03Error, match="Scientific batch"):
        attempt03._validate_approval_documents(_ready_audit(), signoff, attempt03.AMENDMENT_SHA256)


def test_21_existing_attempt03_output_blocks_execution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "run").mkdir()
    (tmp_path / "run" / "status.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(attempt03, "ATTEMPT_ROOT", tmp_path)
    with pytest.raises(attempt03.Attempt03Error, match="already contains output"):
        attempt03._ensure_attempt_is_unused()


def test_22_dry_run_launches_zero_simulation(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    plan = {"status": "READY_FOR_GATE24E_STORAGE_ATTEMPT_03", "simulation_executed": False}
    monkeypatch.setattr(attempt03, "prepare_dry_run", lambda: plan)
    monkeypatch.setattr(attempt03, "execute_once", lambda: pytest.fail("dry-run executed probe"))
    assert attempt03.main(["--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["simulation_executed"] is False


def test_23_attempt01_is_not_reused() -> None:
    assert attempt03.ATTEMPT_ROOT.name != "attempt_01"
    assert (attempt03.ROOT / "scripts/run_gate24e_storage_probe.py").is_file()


def test_24_attempt02_runner_is_preserved() -> None:
    assert attempt03.ATTEMPT_ROOT.name != "attempt_02"
    assert (attempt03.ROOT / "scripts/run_gate24e_storage_probe_retry.py").is_file()
