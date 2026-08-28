"""Loss va calibration primitives, khong tu chay simulation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math

import numpy as np


def _paired(observed: Mapping[str, float], target: Mapping[str, float]) -> tuple[np.ndarray, np.ndarray]:
    keys = [key for key in target if key in observed]
    if not keys:
        raise ValueError("Khong co metric trung nhau de calibration.")
    actual = np.asarray([float(observed[key]) for key in keys], dtype=float)
    expected = np.asarray([float(target[key]) for key in keys], dtype=float)
    if not np.isfinite(actual).all() or not np.isfinite(expected).all():
        raise ValueError("Metric calibration phai huu han.")
    return actual, expected


def compute_loss(
    observed: Mapping[str, float],
    target: Mapping[str, float],
    *,
    huber_delta: float = 1.0,
) -> dict[str, float | int]:
    """Tinh RMSE, MAE, cosine va Huber tren metric giao nhau."""

    actual, expected = _paired(observed, target)
    residual = actual - expected
    absolute = np.abs(residual)
    quadratic = np.where(absolute <= huber_delta, 0.5 * residual**2, huber_delta * (absolute - 0.5 * huber_delta))
    denominator = float(np.linalg.norm(actual) * np.linalg.norm(expected))
    cosine = float(np.dot(actual, expected) / denominator) if denominator else 0.0
    return {
        "metric_count": int(actual.size),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "mae": float(np.mean(absolute)),
        "cosine": cosine,
        "huber": float(np.mean(quadratic)),
    }


def require_targets(targets: Sequence[Mapping[str, object]]) -> None:
    """Dung ro rang neu chua co target literature duoc duyet."""

    if not targets:
        raise RuntimeError("WAITING_TARGET_DATA: chua co literature target duoc phe duyet.")
