"""Validation errors and deterministic synthetic Gate28B fixtures."""

from __future__ import annotations

from typing import Mapping

import numpy as np

from .types import TrajectoryData


class AssayValidationError(ValueError):
    """Raised when a trajectory violates the observation contract."""


class ObservationWindowError(AssayValidationError):
    """Raised when a requested window cannot be represented."""


class AggregationError(ValueError):
    """Raised for mathematically invalid aggregation."""


class PseudoreplicationError(AggregationError):
    """Raised when non-independent observations are treated as replicates."""


FORBIDDEN_REPLICATE_UNITS = frozenset(
    {"frame", "physics_step", "timestep", "segment", "joint_sample"}
)


def validate_trajectory(trajectory: TrajectoryData) -> None:
    timestamps = trajectory.timestamps_s
    planar = trajectory.planar_position_mm
    if trajectory.time_unit != "s" or trajectory.position_unit != "mm":
        raise AssayValidationError("Trajectory units must be declared as seconds and millimetres.")
    if timestamps.size < 2:
        raise AssayValidationError("Trajectory must contain at least two samples.")
    if planar.shape[0] != timestamps.size:
        raise AssayValidationError("Trajectory timestamps and positions must have the same length.")
    if not np.isfinite(timestamps).all():
        raise AssayValidationError("Trajectory timestamps contain NaN or Inf.")
    if not np.isfinite(planar).all():
        raise AssayValidationError("Trajectory planar coordinates contain NaN or Inf.")
    if np.any(np.diff(timestamps) <= 0.0):
        raise AssayValidationError("Trajectory timestamps must be strictly increasing.")


def require_computational_replicate_unit(replicate_unit: str) -> None:
    if replicate_unit in FORBIDDEN_REPLICATE_UNITS:
        raise PseudoreplicationError(
            f"{replicate_unit} is not an independent computational replicate."
        )
    if replicate_unit != "simulation_seed":
        raise PseudoreplicationError(
            "Gate28B group aggregation permits simulation_seed only."
        )


def deterministic_fixtures() -> Mapping[str, TrajectoryData | tuple[np.ndarray, np.ndarray]]:
    """Return analytic fixtures with no unseeded random generation."""

    return {
        "stationary": TrajectoryData(
            np.array([0.0, 1.0, 2.0]), np.array([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]])
        ),
        "constant_straight": TrajectoryData(
            np.array([0.0, 1.0, 2.0]), np.array([[0.0, 0.0], [2.0, 0.0], [4.0, 0.0]])
        ),
        "piecewise_speed": TrajectoryData(
            np.array([0.0, 1.0, 2.0, 3.0]),
            np.array([[0.0, 0.0], [1.0, 0.0], [4.0, 0.0], [6.0, 0.0]]),
        ),
        "turning": TrajectoryData(
            np.array([0.0, 1.0, 2.0]), np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])
        ),
        "irregular_timestamps": TrajectoryData(
            np.array([0.0, 0.5, 2.0]), np.array([[0.0, 0.0], [1.0, 0.0], [4.0, 0.0]])
        ),
        "invalid_nan": (
            np.array([0.0, 1.0, 2.0]),
            np.array([[0.0, 0.0], [np.nan, 0.0], [2.0, 0.0]]),
        ),
    }
