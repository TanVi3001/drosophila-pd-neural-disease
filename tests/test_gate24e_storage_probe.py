from __future__ import annotations

from pathlib import Path

from scripts.run_gate24e_storage_probe import (
    BRAIN_ROOT,
    DEVICE,
    PLATFORM_ROOT,
    PROBE_RUN,
    PROBE_SEED,
    SCIENTIFIC_SEEDS,
    STEPS,
    build_command,
    build_contract,
    calculate_storage_projection,
)


def test_probe_seed_is_outside_scientific_seed_set() -> None:
    assert PROBE_SEED == 9001
    assert PROBE_SEED not in SCIENTIFIC_SEEDS


def test_probe_directory_is_separate_from_scientific_runs() -> None:
    assert PROBE_RUN.parts[-2:] == ("gate_24e_storage_probe", "run")
    assert "gate_24e_blinded_parkin_prediction" not in PROBE_RUN.parts


def test_contract_is_technical_only() -> None:
    contract = build_contract()
    assert contract["purpose"] == "TECHNICAL_STORAGE_QUALIFICATION_ONLY"
    assert contract["scientific_analysis_allowed"] is False
    assert contract["condition"] == "healthy"
    assert contract["condition_label"] == "TECHNICAL_HEALTHY_STORAGE_PROBE"
    assert contract["prepared_parkin_checkpoint"] is None
    assert contract["holdout_access_allowed"] is False
    assert contract["parameter_selection_allowed"] is False
    assert contract["model_selection_allowed"] is False
    assert contract["threshold_selection_allowed"] is False


def test_command_uses_healthy_runtime_and_no_forbidden_options() -> None:
    command = build_command()
    assert command[1].endswith("run_neural_experiment.py")
    assert command[command.index("--brain-root") + 1] == str(BRAIN_ROOT)
    assert command[command.index("--platform-root") + 1] == str(PLATFORM_ROOT)
    assert command[command.index("--seed") + 1] == "9001"
    assert command[command.index("--steps") + 1] == "100000"
    assert command[command.index("--device") + 1] == DEVICE == "cuda"
    assert not {"--prepared-checkpoint", "--video", "--video-output", "--compare-to", "--parameter"}.intersection(command)


def test_probe_uses_exact_duration_and_steps() -> None:
    contract = build_contract()
    assert contract["steps"] == STEPS == 100000
    assert contract["duration_s"] == 10.0
    assert contract["video"] is False


def test_storage_projection_uses_all_25_jobs_and_fixed_20_percent_reserve() -> None:
    projection = calculate_storage_projection(100, 250)
    assert projection["transient_overhead_bytes"] == 150
    assert projection["projected_final_25_jobs_bytes"] == 2500
    assert projection["projected_peak_requirement_bytes"] == 2650
    assert projection["reserve_fraction"] == 0.20
    assert projection["reserve_bytes"] == 530
    assert projection["required_space_bytes"] == 3180


def test_transient_overhead_never_becomes_negative() -> None:
    projection = calculate_storage_projection(1000, 10)
    assert projection["transient_overhead_bytes"] == 0
    assert projection["required_space_bytes"] == 30000


def test_probe_artifacts_are_not_analyzer_inputs() -> None:
    analyzer_source = Path("scripts/analyze_gate24e_blinded_prediction.py").read_text(encoding="utf-8")
    assert "gate_24e_storage_probe" not in analyzer_source


def test_technical_failure_label_is_not_a_scientific_failure_label() -> None:
    assert "STORAGE_PROBE_TECHNICAL_FAILURE" != "DIRECTIONAL_VALIDATION_NOT_SUPPORTED"


def test_probe_contract_keeps_holdout_and_tuning_closed() -> None:
    contract = build_contract()
    assert contract["holdout_access_allowed"] is False
    assert contract["parameter_selection_allowed"] is False
    assert contract["model_selection_allowed"] is False
    assert contract["threshold_selection_allowed"] is False
