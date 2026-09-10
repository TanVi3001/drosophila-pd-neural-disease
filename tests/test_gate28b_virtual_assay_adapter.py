from __future__ import annotations

import inspect
import json
import math
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


def _observation(seed: int = 1):
    return Riemensperger2011OpenArenaAdapter().observe(
        _trajectory(),
        provenance=AdapterProvenance("a" * 64, "b" * 40, seed, "UNIT_TEST"),
    )


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
        provenance=AdapterProvenance("a" * 64, "b" * 40, 1, "UNIT_TEST"),
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
