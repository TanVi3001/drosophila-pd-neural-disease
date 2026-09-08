from __future__ import annotations

import json
from pathlib import Path

from scripts.run_gate24e_storage_probe_retry import (
    ATTEMPT_ROOT,
    PROBE_SEED,
    SCIENTIFIC_SEEDS,
    STEPS,
    _projection,
    _simulation_started,
    build_retry_command,
)


ROOT = Path(__file__).resolve().parents[1]
PROBE_ROOT = ROOT / "experiments" / "gate_24e_storage_probe"


def test_attempt_01_is_preserved_and_invalid() -> None:
    old = json.loads((PROBE_ROOT / "manifests" / "storage_qualification.json").read_text(encoding="utf-8"))
    assert old["attempt_01"]["status"] == "STORAGE_PROBE_TECHNICAL_FAILURE"
    assert old["attempt_01"]["valid_for_storage_estimation"] is False


def test_attempt_02_records_simulation_start_but_invalid_export() -> None:
    top = json.loads((PROBE_ROOT / "manifests" / "storage_qualification.json").read_text(encoding="utf-8"))
    attempt = json.loads(
        (PROBE_ROOT / "attempt_02/manifests/storage_qualification.json").read_text(encoding="utf-8")
    )
    assert top["attempt_02"]["simulation_started"] is True
    assert attempt["simulation_started"] is True
    assert attempt["simulation_completed_steps"] == 100000
    assert attempt["valid_for_storage_estimation"] is False
    assert "POST_SIMULATION_EXPORT_MEMORY_ERROR" in attempt["probe_errors"][-1]


def test_simulation_started_detection_uses_preserved_log(tmp_path: Path) -> None:
    log = tmp_path / "retry.log"
    log.write_text("Progress: 100000/100000\nMemoryError", encoding="utf-8")
    assert _simulation_started(log) is True


def test_attempt_02_is_separate_from_attempt_01() -> None:
    assert ATTEMPT_ROOT.name == "attempt_02"
    assert ATTEMPT_ROOT != PROBE_ROOT / "run"


def test_authorization_allows_exactly_one_retry() -> None:
    auth = json.loads((PROBE_ROOT / "manifests" / "storage_probe_retry_authorization.json").read_text(encoding="utf-8"))
    assert auth["retry_count_authorized"] == 1
    assert auth["retry_seed"] == PROBE_SEED == 9001
    assert auth["automatic_retry"] is False


def test_retry_seed_is_not_scientific_seed() -> None:
    assert PROBE_SEED not in SCIENTIFIC_SEEDS


def test_retry_command_has_no_disease_video_or_parameter_flags() -> None:
    command = build_retry_command(Path("python.exe"))
    assert command[command.index("--seed") + 1] == "9001"
    assert command[command.index("--steps") + 1] == str(STEPS)
    assert {"--prepared-checkpoint", "--parameter", "--video", "--compare-to"}.isdisjoint(command)


def test_retry_command_is_healthy_storage_only() -> None:
    command = build_retry_command(Path("python.exe"))
    assert command[command.index("--brain-root") + 1].endswith("external\\fly-brain-audit")
    assert command[command.index("--output") + 1].endswith("gate_24e_storage_probe\\attempt_02\\run")


def test_projection_uses_fixed_20_percent_reserve() -> None:
    result = _projection(100, 250)
    assert result == {
        "transient_overhead_bytes": 150,
        "projected_final_25_jobs_bytes": 2500,
        "projected_peak_requirement_bytes": 2650,
        "reserve_fraction": 0.20,
        "reserve_bytes": 530,
        "required_space_bytes": 3180,
    }


def test_retry_manifest_contract_closes_scientific_paths() -> None:
    auth = json.loads((PROBE_ROOT / "manifests" / "storage_probe_retry_authorization.json").read_text(encoding="utf-8"))
    assert auth["scientific_jobs_authorized"] is False
    assert auth["holdout_access_allowed"] is False
    assert auth["tuning_allowed"] is False
    assert auth["parameter_change_allowed"] is False


def test_analyzer_rejects_probe_seed_and_excludes_probe_directory() -> None:
    analyzer = (ROOT / "scripts/analyze_gate24e_blinded_prediction.py").read_text(encoding="utf-8")
    assert "gate_24e_storage_probe" not in analyzer
    assert "seeds 0 through 4" in analyzer


def test_no_attempt_03_is_created_by_contract() -> None:
    assert not (PROBE_ROOT / "attempt_03").exists()
