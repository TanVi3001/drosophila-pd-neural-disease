"""Canonical trajectory loading, validation, windowing, and segmentation."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping

import numpy as np

from .types import ObservationWindow, TrajectoryData
from .validation import AssayValidationError, ObservationWindowError, validate_trajectory


CANONICAL_ROLLOUT_SCHEMA_MAPPING = {
    "timestamps_s": "timestamp_s",
    "planar_position_mm": "thorax",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_npz_trajectory(
    path: Path,
    *,
    schema_mapping: Mapping[str, str] = CANONICAL_ROLLOUT_SCHEMA_MAPPING,
) -> TrajectoryData:
    """Load only the minimum planar arrays from an audited rollout schema."""

    required_mapping = {"timestamps_s", "planar_position_mm"}
    if set(schema_mapping) != required_mapping:
        raise AssayValidationError("Schema mapping must map exactly the two canonical fields.")
    if not path.is_file():
        raise AssayValidationError(f"Rollout does not exist: {path}")
    with np.load(path, allow_pickle=False) as archive:
        missing = [source for source in schema_mapping.values() if source not in archive.files]
        if missing:
            raise AssayValidationError(f"Rollout is missing audited keys: {missing}")
        timestamps = np.asarray(archive[schema_mapping["timestamps_s"]], dtype=np.float64)
        positions = np.asarray(archive[schema_mapping["planar_position_mm"]], dtype=np.float64)
    if positions.ndim != 2 or positions.shape[1] < 2:
        raise AssayValidationError("Mapped planar position must have shape [T, >=2].")
    trajectory = TrajectoryData(timestamps, positions[:, :2])
    validate_trajectory(trajectory)
    return trajectory


def _interpolate_position(trajectory: TrajectoryData, time_s: float) -> np.ndarray:
    timestamps = trajectory.timestamps_s
    positions = trajectory.planar_position_mm
    exact = np.flatnonzero(np.isclose(timestamps, time_s, rtol=0.0, atol=1e-12))
    if exact.size:
        return np.array(positions[int(exact[0])], copy=True)
    right = int(np.searchsorted(timestamps, time_s, side="right"))
    left = right - 1
    fraction = (time_s - timestamps[left]) / (timestamps[right] - timestamps[left])
    return positions[left] + fraction * (positions[right] - positions[left])


def slice_trajectory(trajectory: TrajectoryData, window: ObservationWindow) -> TrajectoryData:
    """Slice exactly, using linear boundary interpolation rather than truncation."""

    validate_trajectory(trajectory)
    lower = float(trajectory.timestamps_s[0])
    upper = float(trajectory.timestamps_s[-1])
    if window.start_time_s < lower - 1e-12 or window.end_time_s > upper + 1e-12:
        raise ObservationWindowError("OBSERVATION_WINDOW_EXCEEDS_ROLLOUT")
    start = max(window.start_time_s, lower)
    end = min(window.end_time_s, upper)
    interior = (trajectory.timestamps_s > start) & (trajectory.timestamps_s < end)
    times = np.concatenate(
        ([start], trajectory.timestamps_s[interior], [end])
    ).astype(np.float64, copy=False)
    positions = np.vstack(
        (
            _interpolate_position(trajectory, start),
            trajectory.planar_position_mm[interior],
            _interpolate_position(trajectory, end),
        )
    )
    result = TrajectoryData(times, positions)
    validate_trajectory(result)
    return result


def segment_trajectory(
    trajectory: TrajectoryData,
    *,
    segment_duration_s: float,
) -> tuple[TrajectoryData, ...]:
    """Create contiguous segments whose shared boundary sample is explicit."""

    validate_trajectory(trajectory)
    if not np.isfinite(segment_duration_s) or segment_duration_s <= 0.0:
        raise ObservationWindowError("Segment duration must be finite and positive.")
    start = float(trajectory.timestamps_s[0])
    end = float(trajectory.timestamps_s[-1])
    duration = end - start
    segment_count = duration / segment_duration_s
    rounded_count = int(round(segment_count))
    if rounded_count < 1 or not np.isclose(
        segment_count, rounded_count, rtol=0.0, atol=1e-9
    ):
        raise ObservationWindowError(
            "Trajectory duration must be an integer multiple of segment duration."
        )
    segments = []
    for index in range(rounded_count):
        left = start + index * segment_duration_s
        right = end if index == rounded_count - 1 else start + (index + 1) * segment_duration_s
        segments.append(slice_trajectory(trajectory, ObservationWindow(left, right)))
    return tuple(segments)


_SCHEMA_SEMANTICS: dict[str, tuple[str, str, str, bool]] = {
    "timestamp_s": ("simulation timestamp", "s", "runtime_metadata:timestep_s", True),
    "step": ("simulation step index", "index", "runtime_export_name", False),
    "thorax": ("thorax Cartesian position", "mm", "existing_repo_metric_contract", True),
    "com": ("center-of-mass Cartesian position", "mm", "existing_repo_metric_contract", False),
    "orientation": ("thorax orientation quaternion", "unitless_wxyz", "runtime_metadata:quaternion_order", False),
    "body_positions": ("body-segment Cartesian positions", "mm", "runtime_body_schema", False),
    "body_orientations": ("body-segment orientation quaternions", "unitless_wxyz", "runtime_metadata:quaternion_order", False),
    "joint_positions": ("joint position observations", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", False),
    "joint_velocity": ("joint velocity observations", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", False),
    "joint_acceleration": ("joint acceleration observations", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", False),
    "time_s": ("legacy simulation timestamp alias", "s", "runtime_export_name", False),
    "thorax_positions": ("legacy thorax-position alias", "mm", "existing_repo_metric_contract", False),
    "thorax_quaternions": ("legacy thorax-orientation alias", "unitless_wxyz", "runtime_metadata:quaternion_order", False),
    "contact_found": ("per-leg contact indicator", "indicator", "runtime_export_name", False),
    "contact_forces": ("per-leg contact force vector", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", False),
    "contact_torques": ("per-leg contact torque vector", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", False),
    "contact_positions": ("per-leg contact position", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", False),
    "contact_normals": ("per-leg contact normal", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", False),
    "contact_tangents": ("per-leg contact tangent", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", "UNKNOWN_REQUIRES_RUNTIME_REVIEW", False),
}


def inspect_npz_schema(path: Path) -> list[dict[str, object]]:
    """Inspect each real NPZ key without assigning undocumented semantics."""

    records: list[dict[str, object]] = []
    with np.load(path, allow_pickle=False) as archive:
        for key in archive.files:
            value = archive[key]
            semantic, unit, unit_source, used = _SCHEMA_SEMANTICS.get(
                key,
                (
                    "UNKNOWN_REQUIRES_RUNTIME_REVIEW",
                    "UNKNOWN_REQUIRES_RUNTIME_REVIEW",
                    "UNKNOWN_REQUIRES_RUNTIME_REVIEW",
                    False,
                ),
            )
            confidence = (
                "HIGH"
                if unit_source.startswith("runtime_metadata")
                or unit_source == "existing_repo_metric_contract"
                else "LOW_REQUIRES_RUNTIME_REVIEW"
            )
            records.append(
                {
                    "name": key,
                    "shape": list(value.shape),
                    "dtype": str(value.dtype),
                    "semantic_interpretation": semantic,
                    "used_by_adapter": used,
                    "unit": unit,
                    "unit_source": unit_source,
                    "confidence": confidence,
                }
            )
            del value
    return records
