from __future__ import annotations

import csv
import inspect
import json
import math
import sys
import types
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import yaml

from drosophila_pd_neural.assays.aggregation import (
    aggregate_run_observations,
    aggregate_segment_medians,
    calculate_trajectory_metrics,
    demonstrate_median_of_medians,
    pool_segment_metrics,
)
from drosophila_pd_neural.assays.riemensperger2011 import (
    ADAPTER_ID,
    Riemensperger2011OpenArenaAdapter,
    default_assay_spec,
)
from drosophila_pd_neural.assays.trajectory import (
    load_npz_trajectory,
    segment_trajectory,
    slice_trajectory,
)
from drosophila_pd_neural.assays.types import (
    AdapterProvenance,
    ObservationWindow,
    TrajectoryData,
)
from drosophila_pd_neural.assays.validation import (
    AggregationError,
    AssayValidationError,
    ObservationWindowError,
    PseudoreplicationError,
    require_computational_replicate_unit,
    validate_trajectory,
)
from scripts import run_gate28b_virtual_assay_adapter as gate28b


ROOT = Path(__file__).resolve().parents[1]


def _trajectory() -> TrajectoryData:
    return TrajectoryData(
        np.array([0.0, 1.0, 2.0, 3.0]),
        np.array([[0.0, 0.0], [1.0, 0.0], [4.0, 0.0], [6.0, 0.0]]),
    )


def _observation(seed: int = 1, **changes):
    observation = Riemensperger2011OpenArenaAdapter().observe(
        _trajectory(),
        provenance=AdapterProvenance(
            "a" * 64,
            "b" * 40,
            seed,
            "UNIT_TEST",
            "GATE28B_UNIT_TEST_GROUP",
        ),
    )
    return replace(observation, **changes) if changes else observation


def test_gate28a_is_human_closed() -> None:
    checks = gate28b.verify_gate28a_closure()
    assert checks and all(checks.values())


def test_gate28a_frozen_files_are_unchanged() -> None:
    assert gate28b.verify_gate28a_immutable()["gate28a_changed"] is False


def test_adapter_is_disease_agnostic() -> None:
    signature = inspect.signature(Riemensperger2011OpenArenaAdapter.observe)
    assert "disease" not in signature.parameters
    assert "burden" not in signature.parameters
    assert "checkpoint" not in signature.parameters


def test_timestamp_monotonicity_is_enforced() -> None:
    trajectory = TrajectoryData(
        np.array([0.0, 1.0, 0.5]), np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
    )
    with pytest.raises(AssayValidationError, match="strictly increasing"):
        validate_trajectory(trajectory)


def test_nan_coordinate_is_rejected() -> None:
    trajectory = TrajectoryData(
        np.array([0.0, 1.0]), np.array([[0.0, 0.0], [np.nan, 0.0]])
    )
    with pytest.raises(AssayValidationError, match="NaN or Inf"):
        validate_trajectory(trajectory)


def test_constant_velocity_mean_is_exact() -> None:
    trajectory = TrajectoryData(
        np.array([0.0, 1.0, 2.0]), np.array([[0.0, 0.0], [2.0, 0.0], [4.0, 0.0]])
    )
    assert calculate_trajectory_metrics(trajectory).mean_planar_speed_mm_s == 2.0


def test_distance_is_exact() -> None:
    assert calculate_trajectory_metrics(_trajectory()).distance_traveled_mm == 6.0


def test_displacement_is_exact() -> None:
    turning = TrajectoryData(
        np.array([0.0, 1.0, 2.0]), np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])
    )
    assert math.isclose(
        calculate_trajectory_metrics(turning).displacement_mm, math.sqrt(2.0)
    )


def test_median_framewise_speed_has_explicit_name() -> None:
    observation = _observation()
    assert observation.per_run_median_framewise_speed_mm_s == 2.0
    assert "median_planar_speed_mm_s" not in observation.to_dict()


def test_framewise_median_is_not_paper_group_median() -> None:
    observation = _observation()
    assert "PER_RUN_MEDIAN_FRAMEWISE_SPEED_IS_NOT_PAPER_GROUP_MEDIAN" in observation.limitations
    assert observation.paper_assay_equivalence_established is False


def test_threshold_metrics_unavailable_when_threshold_unknown() -> None:
    observation = _observation()
    assert observation.activity_time_s is None
    assert observation.percent_moving is None
    assert observation.activity_time_unavailable_reason == "NOT_COMPUTED_MISSING_MOVEMENT_THRESHOLD"


def test_threshold_metrics_are_computed_only_when_explicitly_declared() -> None:
    spec = replace(default_assay_spec(), movement_threshold_mm_s=1.5)
    observation = Riemensperger2011OpenArenaAdapter(spec).observe(
        _trajectory(),
        provenance=AdapterProvenance(
            "a" * 64,
            "b" * 40,
            1,
            "UNIT_TEST",
            "GATE28B_UNIT_TEST_GROUP",
        ),
    )
    assert observation.activity_time_s == 2.0
    assert math.isclose(observation.percent_moving, 200.0 / 3.0)
    assert observation.activity_time_unavailable_reason is None


def test_paper_frame_rate_is_not_fabricated() -> None:
    assert _observation().frame_rate_status == "NOT_ASSESSED_SOURCE_UNKNOWN"


def test_exclusion_rule_is_not_fabricated() -> None:
    assert _observation().exclusion_rule_status == "REQUIRES_SOURCE_REVIEW"


def test_observation_window_is_deterministic() -> None:
    first = slice_trajectory(_trajectory(), ObservationWindow(0.5, 2.5))
    second = slice_trajectory(_trajectory(), ObservationWindow(0.5, 2.5))
    np.testing.assert_array_equal(first.timestamps_s, second.timestamps_s)
    np.testing.assert_array_equal(first.planar_position_mm, second.planar_position_mm)


def test_observation_window_overflow_fails() -> None:
    with pytest.raises(ObservationWindowError, match="OBSERVATION_WINDOW_EXCEEDS_ROLLOUT"):
        slice_trajectory(_trajectory(), ObservationWindow(0.0, 4.0))


def test_additive_segment_distance_reconstructs_full_distance() -> None:
    trajectory = TrajectoryData(
        np.linspace(0.0, 5.0, 51),
        np.column_stack((np.linspace(0.0, 10.0, 51), np.zeros(51))),
    )
    full = calculate_trajectory_metrics(trajectory)
    segments = [
        calculate_trajectory_metrics(item)
        for item in segment_trajectory(trajectory, segment_duration_s=0.5)
    ]
    assert pool_segment_metrics(segments)["distance_traveled_mm"] == full.distance_traveled_mm


def test_unequal_segment_means_use_pooled_weighting() -> None:
    first = calculate_trajectory_metrics(
        TrajectoryData(np.array([0.0, 1.0]), np.array([[0.0, 0.0], [1.0, 0.0]]))
    )
    second = calculate_trajectory_metrics(
        TrajectoryData(np.array([0.0, 3.0]), np.array([[0.0, 0.0], [9.0, 0.0]]))
    )
    pooled = pool_segment_metrics([first, second])
    assert pooled["pooled_interval_mean_planar_speed_mm_s"] == 2.5
    assert pooled["pooled_interval_mean_planar_speed_mm_s"] != (1.0 + 3.0) / 2.0


def test_median_of_segment_medians_is_prohibited() -> None:
    segment = calculate_trajectory_metrics(_trajectory())
    with pytest.raises(AggregationError, match="median-of-medians is forbidden"):
        aggregate_segment_medians([segment])
    assert demonstrate_median_of_medians([segment])["status"] == (
        "INVALID_AS_GENERAL_GLOBAL_MEDIAN_AGGREGATOR"
    )


@pytest.mark.parametrize("unit", ["segment", "frame", "timestep", "physics_step", "joint_sample"])
def test_nonindependent_units_are_not_replicates(unit: str) -> None:
    with pytest.raises(PseudoreplicationError):
        require_computational_replicate_unit(unit)


def test_unique_seed_may_be_computational_replicate() -> None:
    first = _observation(seed=1)
    second = _observation(seed=2)
    group = aggregate_run_observations(
        [first, second],
        metric="distance_traveled_mm",
        statistic="median",
    )
    assert group.replicate_unit == "simulation_seed"
    assert group.n_simulation_seeds == 2
    assert group.interpretation == "COMPUTATIONAL_GROUP_MEDIAN"
    assert group.aggregation_group_id == "GATE28B_UNIT_TEST_GROUP"
    assert group.like_with_like_verified is True
    assert len(group.aggregation_signature_sha256) == 64


def test_aggregation_group_id_is_required() -> None:
    with pytest.raises(ValueError, match="aggregation_group_id must be non-empty"):
        AdapterProvenance("a" * 64, "b" * 40, 1, "UNIT_TEST", "")


@pytest.mark.parametrize(
    ("field", "incompatible_value"),
    [
        ("adapter_id", "OTHER_ADAPTER"),
        ("adapter_version", "9.9.9"),
        ("assay_contract_sha256", "c" * 64),
        ("source_runtime_commit", "d" * 40),
        ("aggregation_group_id", "OTHER_GROUP"),
        ("technical_or_scientific_source", "OTHER_SOURCE"),
        ("observed_duration_s", 4.0),
        ("window_start_s", 0.25),
        ("window_end_s", 3.25),
        ("sampling_mode", "OTHER_SAMPLING"),
        ("movement_threshold_status", "OTHER_THRESHOLD"),
        ("exclusion_rule_status", "OTHER_EXCLUSION"),
        ("frame_rate_status", "OTHER_FRAME_RATE"),
        ("assay_compatibility_state", "OTHER_COMPATIBILITY"),
        ("paper_assay_equivalence_established", True),
    ],
)
def test_level2_aggregation_rejects_each_protocol_difference(
    field: str, incompatible_value: object
) -> None:
    first = _observation(seed=1)
    second = _observation(seed=2, **{field: incompatible_value})
    with pytest.raises(
        AggregationError,
        match=rf"LIKE_WITH_LIKE_AGGREGATION_VIOLATION:.*{field}",
    ):
        aggregate_run_observations(
            [first, second], metric="distance_traveled_mm", statistic="median"
        )


def test_level2_time_signature_uses_strict_absolute_tolerance() -> None:
    first = _observation(seed=1)
    within_tolerance = _observation(
        seed=2,
        window_end_s=first.window_end_s + 5e-10,
        observed_duration_s=first.observed_duration_s + 5e-10,
    )
    group = aggregate_run_observations(
        [first, within_tolerance],
        metric="distance_traveled_mm",
        statistic="median",
    )
    assert group.like_with_like_verified is True

    outside_tolerance = _observation(
        seed=2, observed_duration_s=first.observed_duration_s + 2e-9
    )
    with pytest.raises(AggregationError, match="observed_duration_s"):
        aggregate_run_observations(
            [first, outside_tolerance],
            metric="distance_traveled_mm",
            statistic="median",
        )


def test_same_seed_and_different_duration_is_not_a_replicate() -> None:
    with pytest.raises(AggregationError, match="observed_duration_s"):
        aggregate_run_observations(
            [_observation(seed=1), _observation(seed=1, observed_duration_s=4.0)],
            metric="distance_traveled_mm",
            statistic="median",
        )


def test_duplicate_seed_is_rejected() -> None:
    with pytest.raises(AggregationError, match="Duplicate simulation seed"):
        aggregate_run_observations(
            [_observation(seed=1), _observation(seed=1)],
            metric="distance_traveled_mm",
            statistic="median",
        )


def test_paper_equivalence_remains_false() -> None:
    config = yaml.safe_load(gate28b.ADAPTER_CONFIG.read_text(encoding="utf-8"))
    assert config["paper_equivalence_policy"]["paper_assay_equivalence_established"] is False
    assert _observation().paper_assay_equivalence_established is False


def test_execution_cli_has_no_disease_or_burden_arguments() -> None:
    options = gate28b._parser().format_help()
    assert "--disease" not in options
    assert "--burden" not in options
    assert "--calibration" not in options
    assert "--parameter-grid" not in options


def test_technical_command_is_healthy_only() -> None:
    command = gate28b._technical_command(Path("runtime"), Path("output"), 5000)
    assert "--config" not in command
    assert "--prepared-checkpoint" not in command
    assert "--compare-to" not in command
    assert command[command.index("--seed") + 1] == "9101"


def test_technical_seed_is_fixed() -> None:
    assert gate28b.TECHNICAL_SEED == 9101


def test_technical_duration_grid_is_fixed() -> None:
    assert gate28b.TECHNICAL_DURATIONS_S == (0.5, 1.0, 2.0, 5.0)
    assert gate28b.TECHNICAL_STEPS == (5000, 10000, 20000, 50000)


def test_maximum_four_technical_jobs() -> None:
    assert gate28b.MAX_TECHNICAL_JOBS == 4
    assert len(gate28b.TECHNICAL_DURATIONS_S) == 4


def test_no_automatic_retry_policy() -> None:
    source = (ROOT / "scripts/run_gate28b_virtual_assay_adapter.py").read_text(encoding="utf-8")
    assert '"automatic_retry": False' in source
    assert "for retry" not in source.lower()


def test_direct_15_minute_execution_is_forbidden() -> None:
    assert gate28b.PAPER_DURATION_STEPS == 9_000_000
    assert gate28b.PAPER_DURATION_STEPS not in gate28b.TECHNICAL_STEPS
    assert max(gate28b.TECHNICAL_DURATIONS_S) == 5.0


def test_extrapolation_is_labeled_engineering_only() -> None:
    source = (ROOT / "scripts/run_gate28b_virtual_assay_adapter.py").read_text(encoding="utf-8")
    assert "ENGINEERING_EXTRAPOLATION_ONLY" in source
    assert "DIRECT_15_MINUTE_EXECUTION_NOT_TESTED" in source


def test_gate26_result_remains_not_reproduced() -> None:
    manifest = json.loads(
        (
            ROOT
            / "experiments/gate_26_riemensperger_full_completion/manifests/gate26_completion_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["final_directional_decision"] == "NOT_REPRODUCED"


def test_no_calibration_or_model_fitting_in_gate28b_manifest() -> None:
    manifest = json.loads(gate28b.GATE28B_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["calibration_run"] is False
    assert manifest["model_fitting_run"] is False
    assert manifest["retuning"] is False


def test_no_biological_validation_claim() -> None:
    report = gate28b.REPORT.read_text(encoding="utf-8")
    assert "does not reproduce the Riemensperger assay" in report
    assert "paper assay equivalence: `false`" in report


def test_human_signoff_cannot_auto_approve() -> None:
    signoff = json.loads(gate28b.SIGNOFF.read_text(encoding="utf-8"))
    assert signoff["status"] == "WAITING_GATE28B_HUMAN_REVIEW"
    assert signoff["decision"] == "PENDING_HUMAN_REVIEW"
    assert signoff["gate28b_closed"] is False
    assert signoff["no_auto_sign"] is True
    assert not signoff["reviewer_1"] and not signoff["reviewer_2"]


def test_npz_loader_uses_explicit_audited_mapping(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.npz"
    np.savez(
        rollout,
        timestamp_s=np.array([0.0, 1.0]),
        thorax=np.array([[0.0, 0.0, 1.0], [2.0, 0.0, 1.0]]),
        unrelated=np.array([1.0]),
    )
    trajectory = load_npz_trajectory(rollout)
    np.testing.assert_array_equal(trajectory.planar_position_mm, [[0.0, 0.0], [2.0, 0.0]])


def test_trajectory_arrays_are_immutable() -> None:
    trajectory = _trajectory()
    assert trajectory.timestamps_s.flags.writeable is False
    assert trajectory.planar_position_mm.flags.writeable is False
    with pytest.raises(ValueError):
        trajectory.planar_position_mm[0, 0] = 99.0


def test_adapter_identity_is_frozen() -> None:
    assert ADAPTER_ID == "RIEMENSPERGER_2011_OPEN_ARENA_V1"
    assert Riemensperger2011OpenArenaAdapter().spec.paper_duration_s == 900.0


def test_source_protocol_gaps_are_preserved() -> None:
    review = json.loads(gate28b.SOURCE_REVIEW.read_text(encoding="utf-8"))
    assert review["source_review_complete"] is False
    assert set(review["unresolved_fields"]) == {
        "frame_rate",
        "movement_threshold",
        "exclusion_rule",
        "per_fly_speed_computation",
    }


def test_statistical_hierarchy_has_four_levels() -> None:
    contract = yaml.safe_load(gate28b.STATISTICAL_HIERARCHY.read_text(encoding="utf-8"))
    assert list(contract["levels"]) == [
        "LEVEL_0_FRAME",
        "LEVEL_1_RUN",
        "LEVEL_2_COMPUTATIONAL_GROUP",
        "LEVEL_3_BIOLOGICAL_STUDY",
    ]


def test_segmented_biological_validity_is_not_claimed() -> None:
    contract = yaml.safe_load(gate28b.SEGMENTED_AGGREGATION.read_text(encoding="utf-8"))
    assert contract["biological_validity"]["segmented_15_min_biological_equivalence_established"] is False


def test_technical_observations_use_duration_specific_group_ids() -> None:
    document = json.loads(gate28b.RUN_OBSERVATIONS.read_text(encoding="utf-8"))
    expected = {
        0.5: "GATE28B_ENGINEERING_HEALTHY_DURATION_0_5S",
        1.0: "GATE28B_ENGINEERING_HEALTHY_DURATION_1_0S",
        2.0: "GATE28B_ENGINEERING_HEALTHY_DURATION_2_0S",
        5.0: "GATE28B_ENGINEERING_HEALTHY_DURATION_5_0S",
    }
    for item in document["runs"]:
        assert item["observation"]["aggregation_group_id"] == expected[item["duration_s"]]
    assert document["execution_guard_version_at_original_run"] == (
        "PRE_ACTIVE_THERMAL_ABORT_GUARD"
    )
    assert document["current_code_guard"] == "ACTIVE_THERMAL_ABORT_GUARD"


def test_active_gpu_monitor_aborts_at_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    temperatures = iter((75.0, 78.0, 82.0))
    terminated: list[object] = []
    process = object()
    monkeypatch.setattr(
        gate28b,
        "_gpu_snapshot",
        lambda: {"temperature_c": next(temperatures), "memory_used_mb": 1096.0},
    )
    monkeypatch.setattr(
        gate28b, "_terminate_process_tree", lambda value: terminated.append(value)
    )
    max_temperature = None
    device_peak = None
    for expected in (75.0, 78.0):
        max_temperature, device_peak = gate28b._active_gpu_monitor_sample(
            process,
            max_temperature_c=max_temperature,
            device_peak_memory_used_mb=device_peak,
        )
        assert max_temperature == expected
    with pytest.raises(
        gate28b.Gate28BJobAbort,
        match="GATE28B_TECHNICAL_BENCHMARK_ABORTED_GPU_TEMPERATURE",
    ) as captured:
        gate28b._active_gpu_monitor_sample(
            process,
            max_temperature_c=max_temperature,
            device_peak_memory_used_mb=device_peak,
        )
    assert terminated == [process]
    assert captured.value.diagnostics["thermal_abort_triggered"] is True
    assert captured.value.diagnostics["max_observed_gpu_temperature_c"] == 82.0


def test_active_gpu_monitor_aborts_above_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminated: list[object] = []
    process = object()
    monkeypatch.setattr(
        gate28b,
        "_gpu_snapshot",
        lambda: {"temperature_c": 83.0, "memory_used_mb": 1096.0},
    )
    monkeypatch.setattr(
        gate28b, "_terminate_process_tree", lambda value: terminated.append(value)
    )
    with pytest.raises(gate28b.Gate28BJobAbort):
        gate28b._active_gpu_monitor_sample(
            process,
            max_temperature_c=None,
            device_peak_memory_used_mb=None,
        )
    assert terminated == [process]


def test_active_gpu_monitor_failure_aborts_process_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminated: list[object] = []
    process = object()
    samples = iter(
        (
            {"temperature_c": 75.0, "memory_used_mb": 1096.0},
            gate28b.Gate28BError("nvidia-smi unavailable"),
        )
    )

    def intermittent_snapshot() -> dict[str, object]:
        sample = next(samples)
        if isinstance(sample, Exception):
            raise sample
        return sample

    monkeypatch.setattr(gate28b, "_gpu_snapshot", intermittent_snapshot)
    monkeypatch.setattr(
        gate28b, "_terminate_process_tree", lambda value: terminated.append(value)
    )
    max_temperature, device_peak = gate28b._active_gpu_monitor_sample(
        process,
        max_temperature_c=None,
        device_peak_memory_used_mb=None,
    )
    assert max_temperature == 75.0
    assert device_peak == 1096.0
    with pytest.raises(
        gate28b.Gate28BJobAbort,
        match="GATE28B_TECHNICAL_BENCHMARK_ABORTED_GPU_MONITOR_FAILURE",
    ) as captured:
        gate28b._active_gpu_monitor_sample(
            process,
            max_temperature_c=max_temperature,
            device_peak_memory_used_mb=device_peak,
        )
    assert terminated == [process]
    assert captured.value.diagnostics["gpu_monitor_failure_triggered"] is True


def test_process_tree_termination_targets_children_and_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeNode:
        def __init__(self) -> None:
            self.terminated = False
            self.killed = False

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True

    child = FakeNode()
    root = FakeNode()
    root.children = lambda recursive: [child]  # type: ignore[attr-defined]
    module = types.ModuleType("psutil")
    module.Error = RuntimeError  # type: ignore[attr-defined]
    module.Process = lambda pid: root  # type: ignore[attr-defined]
    wait_calls = 0

    def wait_procs(processes, timeout):
        nonlocal wait_calls
        wait_calls += 1
        values = list(processes)
        return ([], values) if wait_calls == 1 else (values, [])

    module.wait_procs = wait_procs  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "psutil", module)

    class FakePopen:
        pid = 42

        @staticmethod
        def poll() -> int:
            return 0

    gate28b._terminate_process_tree(FakePopen())  # type: ignore[arg-type]
    assert child.terminated is True
    assert root.terminated is True
    assert child.killed is True
    assert root.killed is True


def test_thermal_abort_stops_batch_before_next_duration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_root = tmp_path / "duration_benchmark"
    monkeypatch.setattr(gate28b, "EXTERNAL_OUTPUT_ROOT", output_root)
    monkeypatch.setattr(
        gate28b, "EXTERNAL_EXECUTION_STATE", output_root / "benchmark_execution_state.json"
    )
    monkeypatch.setattr(
        gate28b,
        "benchmark_preflight",
        lambda: {"status": "GATE28B_TECHNICAL_BENCHMARK_PREFLIGHT_PASS"},
    )
    monkeypatch.setattr(gate28b, "_runtime_root", lambda: tmp_path)
    calls: list[float] = []

    def abort_first_job(runtime: Path, *, duration_s: float, steps: int) -> dict:
        calls.append(duration_s)
        raise gate28b.Gate28BJobAbort(
            "GATE28B_TECHNICAL_BENCHMARK_ABORTED_GPU_TEMPERATURE",
            {"thermal_abort_triggered": True},
        )

    monkeypatch.setattr(gate28b, "_run_one_technical_job", abort_first_job)
    with pytest.raises(gate28b.Gate28BJobAbort):
        gate28b.execute_technical_duration_benchmark()
    assert calls == [0.5]
    state = json.loads((output_root / "benchmark_execution_state.json").read_text())
    assert state["status"] == "GATE28B_TECHNICAL_BENCHMARK_ABORTED_GPU_TEMPERATURE"
    assert state["technical_jobs_completed"] == 0


def test_gpu_memory_metric_is_explicitly_device_wide() -> None:
    canonical = gate28b._canonical_benchmark_record({"gpu_peak_memory_mb": 1096.0})
    assert canonical["device_peak_memory_used_mb"] == 1096.0
    assert canonical["device_gpu_memory_measurement_semantics"] == (
        "PEAK_DEVICE_WIDE_NVIDIA_SMI_MEMORY_USED_DURING_JOB"
    )
    assert canonical["process_gpu_peak_memory_mb"] is None
    assert canonical["process_gpu_memory_measurement_status"] == (
        "NOT_MEASURED_RELIABLY"
    )
    assert canonical["legacy_field_name"] == "gpu_peak_memory_mb"
    with gate28b.BENCHMARK_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames is not None
    assert "gpu_peak_memory_mb" not in reader.fieldnames
    assert "device_peak_memory_used_mb" in reader.fieldnames
    assert "process_gpu_peak_memory_mb" in reader.fieldnames
    assert len(rows) == 4
    assert all(float(row["device_peak_memory_used_mb"]) == 1096.0 for row in rows)
    assert all(not row["process_gpu_peak_memory_mb"] for row in rows)


def test_pre_signoff_hardening_manifest_preserves_evidence_and_claims() -> None:
    manifest = json.loads(gate28b.HARDENING_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["status"] == "GATE28B_PRE_SIGNOFF_HARDENING_COMPLETE"
    assert manifest["finding_1_resolved"] is True
    assert manifest["finding_2_resolved"] is True
    assert manifest["finding_3_resolved"] is True
    assert manifest["technical_jobs_rerun"] is False
    assert manifest["raw_rollouts_modified"] is False
    assert manifest["benchmark_numeric_results_changed"] is False
    assert manifest["paper_assay_equivalence_established"] is False


def test_original_benchmark_numbers_and_extrapolation_are_preserved() -> None:
    with gate28b.BENCHMARK_CSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    observed = [
        (
            float(row["duration_s"]),
            int(row["steps"]),
            float(row["wall_clock_s"]),
            int(row["raw_output_bytes"]),
        )
        for row in rows
    ]
    assert observed == [
        (0.5, 5000, 67.51762969999982, 28023873),
        (1.0, 10000, 92.44256029999815, 56050266),
        (2.0, 20000, 167.53782119999232, 112024563),
        (5.0, 50000, 346.002891799988, 279739173),
    ]
    scaling = json.loads(gate28b.SCALING_SUMMARY.read_text(encoding="utf-8"))
    assert scaling["projected_15_minute_wall_clock_s_median_scaling"] == (
        79295.16190499743
    )
    assert scaling["projected_15_minute_wall_clock_s_conservative_max_scaling"] == (
        121531.73345999967
    )
    assert scaling["projected_15_minute_storage_bytes_median_scaling"] == 50427012375
    assert scaling[
        "projected_15_minute_storage_bytes_conservative_max_scaling"
    ] == 50445239400
