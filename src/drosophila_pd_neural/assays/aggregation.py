"""Metric and aggregation rules that preserve statistical hierarchy."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from typing import Iterable, Sequence

import numpy as np

from .types import GroupObservation, RunObservation, TrajectoryData, TrajectoryMetrics
from .validation import AggregationError, require_computational_replicate_unit, validate_trajectory


LIKE_WITH_LIKE_TIME_ABS_TOLERANCE_S = 1e-9
_TIME_SIGNATURE_FIELDS = frozenset(
    {"window_start_s", "window_end_s", "observed_duration_s"}
)
_AGGREGATION_SIGNATURE_FIELDS = (
    "aggregation_group_id",
    "adapter_id",
    "adapter_version",
    "assay_contract_sha256",
    "source_runtime_commit",
    "technical_or_scientific_source",
    "sampling_mode",
    "movement_threshold_status",
    "exclusion_rule_status",
    "frame_rate_status",
    "assay_compatibility_state",
    "paper_assay_equivalence_established",
    "window_start_s",
    "window_end_s",
    "observed_duration_s",
)


def calculate_trajectory_metrics(trajectory: TrajectoryData) -> TrajectoryMetrics:
    validate_trajectory(trajectory)
    interval_durations = np.diff(trajectory.timestamps_s)
    planar_deltas = np.diff(trajectory.planar_position_mm, axis=0)
    step_distances = np.linalg.norm(planar_deltas, axis=1)
    framewise_speed = step_distances / interval_durations
    if not np.isfinite(framewise_speed).all():
        raise AggregationError("Computed framewise speed contains NaN or Inf.")
    duration = float(trajectory.timestamps_s[-1] - trajectory.timestamps_s[0])
    distance = float(np.sum(step_distances))
    displacement = float(
        np.linalg.norm(trajectory.planar_position_mm[-1] - trajectory.planar_position_mm[0])
    )
    return TrajectoryMetrics(
        observed_duration_s=duration,
        distance_traveled_mm=distance,
        displacement_mm=displacement,
        mean_planar_speed_mm_s=distance / duration,
        median_framewise_planar_speed_mm_s=float(np.median(framewise_speed)),
        interval_durations_s=interval_durations,
        step_distances_mm=step_distances,
        framewise_planar_speed_mm_s=framewise_speed,
    )


def pool_segment_metrics(segments: Sequence[TrajectoryMetrics]) -> dict[str, float]:
    """Pool compatible interval observations; never average unequal run means."""

    if not segments:
        raise AggregationError("At least one segment metric is required.")
    duration = float(sum(item.observed_duration_s for item in segments))
    distance = float(sum(item.distance_traveled_mm for item in segments))
    if duration <= 0.0:
        raise AggregationError("Pooled duration must be positive.")
    speeds = np.concatenate([item.framewise_planar_speed_mm_s for item in segments])
    return {
        "distance_traveled_mm": distance,
        "observed_duration_s": duration,
        "pooled_interval_mean_planar_speed_mm_s": distance / duration,
        "pooled_framewise_median_planar_speed_mm_s": float(np.median(speeds)),
    }


def demonstrate_median_of_medians(segments: Sequence[TrajectoryMetrics]) -> dict[str, float | str]:
    if not segments:
        raise AggregationError("At least one segment metric is required.")
    value = float(statistics.median(item.median_framewise_planar_speed_mm_s for item in segments))
    return {
        "value": value,
        "status": "INVALID_AS_GENERAL_GLOBAL_MEDIAN_AGGREGATOR",
    }


def aggregate_segment_medians(_: Sequence[TrajectoryMetrics]) -> float:
    """Fail closed: a median of segment medians is not a global median."""

    raise AggregationError(
        "median-of-medians is forbidden; pool compatible observations instead."
    )


def _run_metric(observation: RunObservation, metric: str) -> float:
    allowed = {
        "per_run_mean_planar_speed_mm_s",
        "per_run_median_framewise_speed_mm_s",
        "distance_traveled_mm",
        "displacement_mm",
    }
    if metric not in allowed:
        raise AggregationError(f"Unsupported run-level metric: {metric}")
    return float(getattr(observation, metric))


def run_aggregation_signature(observation: RunObservation) -> dict[str, object]:
    """Return the explicit protocol identity used for LEVEL_2 aggregation."""

    return {
        field: getattr(observation, field) for field in _AGGREGATION_SIGNATURE_FIELDS
    }


def _signature_differences(
    reference: dict[str, object], candidate: dict[str, object]
) -> tuple[str, ...]:
    differences: list[str] = []
    for field in _AGGREGATION_SIGNATURE_FIELDS:
        first = reference[field]
        second = candidate[field]
        if field in _TIME_SIGNATURE_FIELDS:
            compatible = math.isclose(
                float(first),
                float(second),
                rel_tol=0.0,
                abs_tol=LIKE_WITH_LIKE_TIME_ABS_TOLERANCE_S,
            )
        else:
            compatible = first == second
        if not compatible:
            differences.append(field)
    return tuple(differences)


def _signature_sha256(signature: dict[str, object]) -> str:
    payload = json.dumps(
        signature, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def aggregate_run_observations(
    observations: Iterable[RunObservation],
    *,
    metric: str,
    statistic: str,
    replicate_unit: str = "simulation_seed",
) -> GroupObservation:
    """Aggregate independent simulation seeds at LEVEL_2 only."""

    require_computational_replicate_unit(replicate_unit)
    rows = tuple(observations)
    if not rows:
        raise AggregationError("At least one run observation is required.")
    reference_signature = run_aggregation_signature(rows[0])
    violations: list[str] = []
    for index, observation in enumerate(rows[1:], start=1):
        differences = _signature_differences(
            reference_signature, run_aggregation_signature(observation)
        )
        if differences:
            violations.append(f"run_index={index}:fields={','.join(differences)}")
    if violations:
        raise AggregationError(
            "LIKE_WITH_LIKE_AGGREGATION_VIOLATION: " + "; ".join(violations)
        )
    seeds = tuple(item.simulation_seed for item in rows)
    if len(seeds) != len(set(seeds)):
        raise AggregationError("Duplicate simulation seed is not an independent replicate.")
    values = [_run_metric(item, metric) for item in rows]
    if statistic == "median":
        value = float(statistics.median(values))
    elif statistic == "mean":
        value = float(statistics.fmean(values))
    else:
        raise AggregationError("Only explicitly requested mean or median is supported.")
    return GroupObservation(
        metric=metric,
        statistic=statistic,
        value=value,
        aggregation_group_id=rows[0].aggregation_group_id,
        adapter_id=rows[0].adapter_id,
        adapter_version=rows[0].adapter_version,
        assay_contract_sha256=rows[0].assay_contract_sha256,
        source_runtime_commit=rows[0].source_runtime_commit,
        observed_duration_s=rows[0].observed_duration_s,
        n_simulation_seeds=len(rows),
        simulation_seeds=tuple(sorted(seeds)),
        replicate_unit=replicate_unit,
        interpretation="COMPUTATIONAL_GROUP_MEDIAN" if statistic == "median" else "COMPUTATIONAL_GROUP_MEAN",
        like_with_like_verified=True,
        aggregation_signature_sha256=_signature_sha256(reference_signature),
    )
