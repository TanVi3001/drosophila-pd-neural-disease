"""Metric extraction for virtual Riemensperger 2011 seed replicates."""

from __future__ import annotations

import math
from pathlib import Path
import statistics
from typing import Any

import numpy as np


def _finite_array(name: str, value: np.ndarray) -> None:
    if not np.isfinite(value).all():
        raise RuntimeError(f"{name} contains NaN or Inf.")


def rollout_seed_metrics(rollout_path: Path) -> dict[str, Any]:
    """Derive one seed-level median speed and distance from a real rollout.

    Frames are observations within a seed, never independent experimental
    replicates.  The returned ``median_planar_speed_mm_s`` is the median of
    framewise planar speeds for that *one* seed.
    """

    with np.load(rollout_path, allow_pickle=False) as archive:
        required = ("timestamp_s", "thorax", "joint_positions", "actuator_position", "contact_found")
        missing = [key for key in required if key not in archive.files]
        if missing:
            raise RuntimeError(f"rollout is missing required arrays: {missing}")
        timestamps = np.asarray(archive["timestamp_s"], dtype=float)
        thorax = np.asarray(archive["thorax"], dtype=float)
        joints = np.asarray(archive["joint_positions"], dtype=float)
        actuators = np.asarray(archive["actuator_position"], dtype=float)
        contacts = np.asarray(archive["contact_found"], dtype=float)

    if timestamps.ndim != 1 or timestamps.size < 2:
        raise RuntimeError("timestamp_s must contain at least two frames.")
    if thorax.ndim != 2 or thorax.shape[0] != timestamps.size or thorax.shape[1] < 2:
        raise RuntimeError("thorax must have shape (frames, >=2).")
    if joints.ndim != 2 or joints.shape[0] != timestamps.size:
        raise RuntimeError("joint_positions shape is incompatible with timestamps.")
    if actuators.ndim != 2 or actuators.shape != (timestamps.size, 42):
        raise RuntimeError("actuator_position must have shape (frames, 42).")
    for name, values in (("timestamp_s", timestamps), ("thorax", thorax), ("joint_positions", joints), ("actuator_position", actuators), ("contact_found", contacts)):
        _finite_array(name, values)

    deltas_t = np.diff(timestamps)
    if np.any(deltas_t <= 0.0):
        raise RuntimeError("timestamps must increase strictly.")
    planar_steps = np.linalg.norm(np.diff(thorax[:, :2], axis=0), axis=1)
    framewise_speeds = planar_steps / deltas_t
    _finite_array("framewise planar speed", framewise_speeds)
    joint_delta = float(np.max(np.abs(np.diff(joints, axis=0))))
    action_delta = float(np.max(np.abs(np.diff(actuators, axis=0))))
    if joint_delta <= 0.0 and action_delta <= 0.0:
        raise RuntimeError("joint and actuator trajectories are both static.")

    duration_s = float(timestamps[-1] - timestamps[0])
    distance_mm = float(np.sum(planar_steps))
    displacement_mm = float(np.linalg.norm(thorax[-1, :2] - thorax[0, :2]))
    return {
        "frame_count": int(timestamps.size),
        "duration_s": duration_s,
        "median_planar_speed_mm_s": float(statistics.median(framewise_speeds.tolist())),
        "distance_traveled_mm": distance_mm,
        "displacement_mm": displacement_mm,
        "mean_framewise_planar_speed_mm_s": float(np.mean(framewise_speeds)),
        "timestamp_monotonic": True,
        "finite_qc": True,
        "contact_detected": bool(np.any(contacts > 0.0)),
        "joint_trajectory_max_delta": joint_delta,
        "action_trajectory_max_delta": action_delta,
    }


def sample_summary(values: list[float]) -> dict[str, float | int | None]:
    """Summarise independent seeds; frame values never enter this aggregation."""

    if not values:
        raise ValueError("values must contain at least one seed-level metric.")
    finite = [float(value) for value in values]
    if not all(math.isfinite(value) for value in finite):
        raise ValueError("seed-level metric values must be finite.")
    count = len(finite)
    sample_sd = statistics.stdev(finite) if count > 1 else None
    return {
        "n_seeds": count,
        "median": float(statistics.median(finite)),
        "mean": float(statistics.fmean(finite)),
        "sample_sd": float(sample_sd) if sample_sd is not None else None,
        "sample_se": float(sample_sd / math.sqrt(count)) if sample_sd is not None else None,
    }
