from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_neural_experiment import (
    FROZEN_CPG_DEFAULT_HZ,
    FROZEN_FLYGYM_VERSION,
    FROZEN_PLATFORM_COMMIT,
    build_platform_command,
    validate_frozen_cpg_compatibility,
)


ROOT = Path(__file__).resolve().parents[1]
PROBE_ROOT = ROOT / "experiments" / "gate_24e_storage_probe"
COMPATIBILITY = PROBE_ROOT / "manifests" / "cpg_compatibility_fix.json"
QUALIFICATION = PROBE_ROOT / "manifests" / "storage_qualification.json"


def _patched_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, frequency: float = 12.0) -> list[str]:
    monkeypatch.setattr("scripts.run_neural_experiment._git_commit", lambda _path: FROZEN_PLATFORM_COMMIT)
    monkeypatch.setattr(
        "scripts.run_neural_experiment._installed_distribution_version",
        lambda _python, _distribution: FROZEN_FLYGYM_VERSION,
    )
    return build_platform_command(
        brain_python=Path("python.exe"),
        platform_root=tmp_path,
        run_brain_root=tmp_path / "brain",
        seed=9001,
        steps=100000,
        device="cuda",
        output=tmp_path / "run",
        stimulus="p9",
        requested_frequency_hz=frequency,
    )


def test_frozen_platform_does_not_support_cpg_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    command = _patched_command(monkeypatch, tmp_path)
    assert "--cpg-frequency-hz" not in command


def test_exact_12_hz_uses_frozen_intrinsic_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    command = _patched_command(monkeypatch, tmp_path, FROZEN_CPG_DEFAULT_HZ)
    assert command[command.index("--seed") + 1] == "9001"
    assert command[command.index("--steps") + 1] == "100000"


def test_non_equivalent_frequency_is_rejected_not_ignored() -> None:
    with pytest.raises(RuntimeError, match="INCOMPATIBLE_CPG_FREQUENCY"):
        validate_frozen_cpg_compatibility(
            platform_commit=FROZEN_PLATFORM_COMMIT,
            flygym_version=FROZEN_FLYGYM_VERSION,
            requested_frequency_hz=11.999,
        )


def test_platform_contract_is_version_safe() -> None:
    with pytest.raises(RuntimeError, match="INCOMPATIBLE_FLYGYM_PLATFORM_COMMIT"):
        validate_frozen_cpg_compatibility(
            platform_commit="changed",
            flygym_version=FROZEN_FLYGYM_VERSION,
            requested_frequency_hz=12.0,
        )
    with pytest.raises(RuntimeError, match="INCOMPATIBLE_FLYGYM_VERSION"):
        validate_frozen_cpg_compatibility(
            platform_commit=FROZEN_PLATFORM_COMMIT,
            flygym_version="2.2.0",
            requested_frequency_hz=12.0,
        )


def test_external_platform_is_not_modified() -> None:
    platform = ROOT.parent / "drosophila-pd-flygym-gate24-clean"
    if not platform.is_dir():
        pytest.skip("external FlyGym platform worktree is not distributed in Git")
    assert platform.is_dir()
    assert not (platform / ".gate24e_cpg_cli_compatibility_modified").exists()


def test_probe_and_scientific_execution_remain_closed() -> None:
    compatibility = json.loads(COMPATIBILITY.read_text(encoding="utf-8"))
    assert compatibility["probe_retry_authorized"] is False
    assert compatibility["scientific_jobs_authorized"] is False
    assert compatibility["holdout_opened"] is False


def test_storage_history_preserves_attempt01_and_records_attempt04_probe() -> None:
    qualification = json.loads(QUALIFICATION.read_text(encoding="utf-8"))
    assert qualification["qualification_status"] == "GATE24E_STORAGE_NOT_QUALIFIED"
    assert qualification["current_qualification_status"] == "WAITING_GATE24E_STORAGE_CAPACITY"
    assert qualification["storage_measurements_valid"] is True
    assert qualification["storage_measurement_status"] == "VALID_COMPLETED_STORAGE_PROBE"
    assert qualification["attempt_01"]["status"] == "STORAGE_PROBE_TECHNICAL_FAILURE"
    assert qualification["attempt_01"]["valid_for_storage_estimation"] is False
    assert qualification["attempt_04"]["valid_for_storage_estimation"] is True
    assert qualification["probe_seed"] == 9001


def test_frozen_scientific_seed_and_probe_seed_are_disjoint() -> None:
    contract = json.loads(
        (PROBE_ROOT / "manifests" / "storage_probe_contract.json").read_text(encoding="utf-8")
    )
    assert contract["locked_scientific_seeds"] == [0, 1, 2, 3, 4]
    assert contract["probe_seed"] not in contract["locked_scientific_seeds"]


def test_command_contains_no_scientific_or_probe_only_flags(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    command = _patched_command(monkeypatch, tmp_path)
    forbidden = {"--cpg-frequency-hz", "--prepared-checkpoint", "--parameter", "--video"}
    assert not forbidden.intersection(command)
