"""Riemensperger 2011 open-arena virtual observation adapter."""

from __future__ import annotations

from .aggregation import calculate_trajectory_metrics
from .base import AssayAdapter
from .trajectory import slice_trajectory
from .types import (
    AdapterProvenance,
    AssayCompatibility,
    AssaySpec,
    ObservationWindow,
    RunObservation,
    TrajectoryData,
)
from .validation import validate_trajectory


ADAPTER_ID = "RIEMENSPERGER_2011_OPEN_ARENA_V1"
ADAPTER_VERSION = "1.0.0"
ASSAY_CONTRACT_PATH = "configs/generation2/assays/riemensperger_2011_open_arena.yaml"
ASSAY_CONTRACT_SHA256 = "9c3a86dd0fbe25ccae5e180ba110427298bd34892ae21d312ecd511bd0e5a60f"


def default_assay_spec() -> AssaySpec:
    return AssaySpec(
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        geometry="open_arena",
        orientation="horizontal_surface",
        stimulus="spontaneous_locomotion",
        experimental_unit="individual_fly",
        paper_duration_s=900.0,
        aggregation_statistic="median",
        assay_contract_path=ASSAY_CONTRACT_PATH,
        assay_contract_sha256=ASSAY_CONTRACT_SHA256,
        unresolved_source_fields=(
            "frame_rate",
            "movement_threshold",
            "exclusion_rule",
            "per_fly_speed_computation",
        ),
    )


class Riemensperger2011OpenArenaAdapter(AssayAdapter):
    """Compute native virtual metrics without asserting paper equivalence."""

    def __init__(self, spec: AssaySpec | None = None) -> None:
        self.spec = spec or default_assay_spec()
        if self.spec.adapter_id != ADAPTER_ID:
            raise ValueError("Unexpected assay adapter ID.")

    def observe(
        self,
        trajectory: TrajectoryData,
        *,
        provenance: AdapterProvenance,
        window: ObservationWindow | None = None,
    ) -> RunObservation:
        validate_trajectory(trajectory)
        observed = slice_trajectory(trajectory, window) if window is not None else trajectory
        metrics = calculate_trajectory_metrics(observed)
        threshold = self.spec.movement_threshold_mm_s
        if threshold is None:
            activity_time_s = None
            activity_reason = "NOT_COMPUTED_MISSING_MOVEMENT_THRESHOLD"
            percent_moving = None
            percent_reason = "NOT_COMPUTED_MISSING_MOVEMENT_THRESHOLD"
            threshold_status = "REQUIRES_SOURCE_REVIEW"
        else:
            moving = metrics.framewise_planar_speed_mm_s > threshold
            activity_time_s = float(metrics.interval_durations_s[moving].sum())
            activity_reason = None
            percent_moving = 100.0 * activity_time_s / metrics.observed_duration_s
            percent_reason = None
            threshold_status = "DECLARED_MOVEMENT_THRESHOLD_MM_S"
        return RunObservation(
            adapter_id=self.spec.adapter_id,
            adapter_version=self.spec.adapter_version,
            assay_contract_sha256=self.spec.assay_contract_sha256,
            source_rollout_sha256=provenance.source_rollout_sha256,
            source_runtime_commit=provenance.source_runtime_commit,
            simulation_seed=provenance.simulation_seed,
            technical_or_scientific_source=provenance.technical_or_scientific_source,
            window_start_s=float(observed.timestamps_s[0]),
            window_end_s=float(observed.timestamps_s[-1]),
            observed_duration_s=metrics.observed_duration_s,
            sampling_mode="NATIVE_SIMULATION",
            movement_threshold_status=threshold_status,
            exclusion_rule_status="REQUIRES_SOURCE_REVIEW",
            frame_rate_status="NOT_ASSESSED_SOURCE_UNKNOWN",
            per_run_mean_planar_speed_mm_s=metrics.mean_planar_speed_mm_s,
            per_run_median_framewise_speed_mm_s=metrics.median_framewise_planar_speed_mm_s,
            distance_traveled_mm=metrics.distance_traveled_mm,
            displacement_mm=metrics.displacement_mm,
            activity_time_s=activity_time_s,
            activity_time_unavailable_reason=activity_reason,
            percent_moving=percent_moving,
            percent_moving_unavailable_reason=percent_reason,
            finite_qc=True,
            timestamp_qc=True,
            assay_compatibility_state=AssayCompatibility.SOURCE_PROTOCOL_FIELDS_MISSING.value,
            paper_assay_equivalence_established=False,
            limitations=(
                "UNRESOLVED_SOURCE_PROTOCOL_FIELDS",
                "RIEMENSPERGER_SPEED_STATISTICAL_HIERARCHY_REQUIRES_SOURCE_REVIEW",
                "PER_RUN_MEDIAN_FRAMEWISE_SPEED_IS_NOT_PAPER_GROUP_MEDIAN",
                "DIRECT_15_MINUTE_EXECUTION_NOT_TESTED",
            ),
        )
