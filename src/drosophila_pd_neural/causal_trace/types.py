"""Small immutable records for the Gate29 computational trace."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping


class DependencyClass(StrEnum):
    DIRECT_ARGUMENT_DEPENDENCY = "DIRECT_ARGUMENT_DEPENDENCY"
    STATE_UPDATE_DEPENDENCY = "STATE_UPDATE_DEPENDENCY"
    DECODER_DEPENDENCY = "DECODER_DEPENDENCY"
    CONTROL_FEEDBACK_DEPENDENCY = "CONTROL_FEEDBACK_DEPENDENCY"
    ACTUATION_DEPENDENCY = "ACTUATION_DEPENDENCY"
    PHYSICS_TRANSITION_DEPENDENCY = "PHYSICS_TRANSITION_DEPENDENCY"
    OBSERVATIONAL_DERIVATION = "OBSERVATIONAL_DERIVATION"
    SOURCE_CODE_SUPPORTED_STRUCTURE = "SOURCE_CODE_SUPPORTED_STRUCTURE"
    UNKNOWN_UNVERIFIED_EDGE = "UNKNOWN_UNVERIFIED_EDGE"


def _mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True, slots=True)
class TraceLayer:
    layer_id: str
    label: str
    status: str
    source_basis: str


@dataclass(frozen=True, slots=True)
class TraceEdge:
    edge_id: str
    source_layer: str
    source_signal: str
    target_layer: str
    target_signal: str
    dependency_class: DependencyClass
    source_basis: str
    runtime_verified: bool
    biological_causality_established: bool = False
    notes: str = ""


@dataclass(frozen=True, slots=True)
class TraceStep:
    step_index: int
    pre_time_s: float
    post_time_s: float
    signals: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "signals", _mapping(self.signals))


@dataclass(frozen=True, slots=True)
class TraceProvenance:
    source_main_commit: str
    runtime_commit: str
    brain_checkpoint_sha256: str
    technical_seed: int
    instrumentation_mode: str
    raw_trace_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class SignalAvailability:
    signal_name: str
    source_object: str
    public_api: str
    public_api_verified: bool
    shape: str
    dtype: str
    unit: str
    unit_source: str
    capture_timing: str
    required_for_gate29: bool
    export_status: str
    semantic_confidence: str


@dataclass(frozen=True, slots=True)
class TraceSummary:
    status: str
    steps: int
    signal_availability: tuple[SignalAvailability, ...]
    edge_count: int
    nonperturbation_status: str
    scientific_jobs: int = 0
    disease_jobs: int = 0
    calibration_run: bool = False
    model_fitting_run: bool = False
    retuning: bool = False
