"""Immutable data contracts for virtual assay observations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np


class AssayCompatibility(StrEnum):
    """Allowed Gate28B compatibility labels."""

    COMPUTATIONAL_OBSERVATION_VALID = "COMPUTATIONAL_OBSERVATION_VALID"
    COMPUTATIONAL_OBSERVATION_PARTIAL = "COMPUTATIONAL_OBSERVATION_PARTIAL"
    SOURCE_PROTOCOL_FIELDS_MISSING = "SOURCE_PROTOCOL_FIELDS_MISSING"
    INVALID_ROLLOUT = "INVALID_ROLLOUT"
    WINDOW_INCOMPATIBLE = "WINDOW_INCOMPATIBLE"


@dataclass(frozen=True, slots=True)
class AssaySpec:
    adapter_id: str
    adapter_version: str
    geometry: str
    orientation: str
    stimulus: str
    experimental_unit: str
    paper_duration_s: float
    aggregation_statistic: str
    assay_contract_path: str
    assay_contract_sha256: str
    frame_rate_hz: float | None = None
    movement_threshold_mm_s: float | None = None
    exclusion_rule: str | None = None
    unresolved_source_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ObservationWindow:
    start_time_s: float
    end_time_s: float

    def __post_init__(self) -> None:
        if not np.isfinite((self.start_time_s, self.end_time_s)).all():
            raise ValueError("Observation window bounds must be finite.")
        if self.end_time_s <= self.start_time_s:
            raise ValueError("Observation window end must be greater than start.")

    @classmethod
    def from_duration(cls, start_time_s: float, duration_s: float) -> "ObservationWindow":
        if not np.isfinite(duration_s) or duration_s <= 0.0:
            raise ValueError("Observation duration must be finite and positive.")
        return cls(float(start_time_s), float(start_time_s + duration_s))


def _readonly_float_array(value: np.ndarray, *, dimensions: int, name: str) -> np.ndarray:
    array = np.array(value, dtype=np.float64, copy=True)
    if array.ndim != dimensions:
        raise ValueError(f"{name} must have {dimensions} dimensions.")
    array.flags.writeable = False
    return array


@dataclass(frozen=True, slots=True)
class TrajectoryData:
    timestamps_s: np.ndarray
    planar_position_mm: np.ndarray
    optional_fields: Mapping[str, np.ndarray] = field(default_factory=dict)
    time_unit: str = "s"
    position_unit: str = "mm"

    def __post_init__(self) -> None:
        timestamps = _readonly_float_array(self.timestamps_s, dimensions=1, name="timestamps_s")
        planar = _readonly_float_array(
            self.planar_position_mm, dimensions=2, name="planar_position_mm"
        )
        if planar.shape[1] != 2:
            raise ValueError("planar_position_mm must have shape [T, 2].")
        optional: dict[str, np.ndarray] = {}
        for name, value in self.optional_fields.items():
            array = np.array(value, copy=True)
            array.flags.writeable = False
            optional[str(name)] = array
        object.__setattr__(self, "timestamps_s", timestamps)
        object.__setattr__(self, "planar_position_mm", planar)
        object.__setattr__(self, "optional_fields", MappingProxyType(optional))


@dataclass(frozen=True, slots=True)
class TrajectoryMetrics:
    observed_duration_s: float
    distance_traveled_mm: float
    displacement_mm: float
    mean_planar_speed_mm_s: float
    median_framewise_planar_speed_mm_s: float
    interval_durations_s: np.ndarray
    step_distances_mm: np.ndarray
    framewise_planar_speed_mm_s: np.ndarray

    def __post_init__(self) -> None:
        for name in (
            "interval_durations_s",
            "step_distances_mm",
            "framewise_planar_speed_mm_s",
        ):
            array = _readonly_float_array(getattr(self, name), dimensions=1, name=name)
            object.__setattr__(self, name, array)


@dataclass(frozen=True, slots=True)
class AdapterProvenance:
    source_rollout_sha256: str
    source_runtime_commit: str
    simulation_seed: int
    technical_or_scientific_source: str


@dataclass(frozen=True, slots=True)
class RunObservation:
    adapter_id: str
    adapter_version: str
    assay_contract_sha256: str
    source_rollout_sha256: str
    source_runtime_commit: str
    simulation_seed: int
    technical_or_scientific_source: str
    window_start_s: float
    window_end_s: float
    observed_duration_s: float
    sampling_mode: str
    movement_threshold_status: str
    exclusion_rule_status: str
    frame_rate_status: str
    per_run_mean_planar_speed_mm_s: float
    per_run_median_framewise_speed_mm_s: float
    distance_traveled_mm: float
    displacement_mm: float
    activity_time_s: float | None
    activity_time_unavailable_reason: str | None
    percent_moving: float | None
    percent_moving_unavailable_reason: str | None
    finite_qc: bool
    timestamp_qc: bool
    assay_compatibility_state: str
    paper_assay_equivalence_established: bool
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GroupObservation:
    metric: str
    statistic: str
    value: float
    n_simulation_seeds: int
    simulation_seeds: tuple[int, ...]
    replicate_unit: str
    interpretation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
