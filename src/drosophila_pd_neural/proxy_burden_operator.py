"""Conservative action-level operator for a dimensionless proxy burden.

This module transforms an already-created action without claiming that the
transformation represents a biological gene mechanism.  The caller owns the
runtime hook and must provide a real action from the brain-body controller.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np


def _validate_bounded(name: str, value: float, *, upper: float | None = None) -> float:
    number = float(value)
    if not np.isfinite(number) or number < 0.0 or (upper is not None and number > upper):
        bound = f" within [0, {upper}]" if upper is not None else " and non-negative"
        raise ValueError(f"{name} must be finite{bound}.")
    return number


def _action_values(action: Any) -> tuple[np.ndarray, bool]:
    if hasattr(action, "joint_angles"):
        values = np.asarray(action.joint_angles, dtype=float)
        return values, True
    return np.asarray(action, dtype=float), False


def _copy_action(action: Any, values: np.ndarray) -> Any:
    if not hasattr(action, "joint_angles"):
        return values.copy()
    adhesion = getattr(action, "adhesion_onoff", None)
    copied_adhesion = None if adhesion is None else np.asarray(adhesion, dtype=bool).copy()
    try:
        return type(action)(
            joint_angles=values.copy(),
            adhesion_onoff=copied_adhesion,
        )
    except TypeError:
        try:
            return replace(
                action,
                joint_angles=values.copy(),
                adhesion_onoff=copied_adhesion,
            )
        except (TypeError, ValueError) as exc:
            raise TypeError(
                "Action object must accept joint_angles and adhesion_onoff."
            ) from exc


def apply_proxy_burden_to_action(
    action: Any,
    burden_level: float,
    *,
    mode: str = "amplitude_attenuation",
    attenuation_strength: float = 0.5,
    noise_strength: float = 0.0,
    seed: int | None = None,
    clip_to_input_range: bool = True,
) -> Any:
    """Apply a deterministic, non-mutating computational proxy transform.

    ``burden_level`` is a dimensionless control value in ``[0, 1]``.  With
    ``amplitude_attenuation`` the output is ``action * (1 - strength * burden)``.
    Optional noise is seeded and scaled by burden.  For generic arrays, the
    input min/max are used as a conservative clipping range; a production
    caller should supply an action type with an explicitly documented range.
    """

    burden = _validate_bounded("burden_level", burden_level, upper=1.0)
    attenuation = _validate_bounded("attenuation_strength", attenuation_strength, upper=1.0)
    noise = _validate_bounded("noise_strength", noise_strength)
    mode_name = str(mode).strip().lower()
    if mode_name not in {"amplitude_attenuation", "amplitude_attenuation_only"}:
        raise ValueError(f"Unsupported proxy burden operator mode: {mode}")

    source, is_object = _action_values(action)
    if source.ndim != 1:
        raise ValueError("Action must be a one-dimensional vector.")
    if not np.isfinite(source).all():
        raise ValueError("Action must contain only finite values.")
    if seed is not None and int(seed) < 0:
        raise ValueError("seed must be non-negative when provided.")

    # Preserve an exact identity at zero burden, including the no-mutation
    # guarantee, even when a caller requests optional noise.
    transformed = source.copy()
    if burden > 0.0:
        transformed *= 1.0 - attenuation * burden
        if noise > 0.0:
            rng = np.random.default_rng(seed)
            transformed += noise * burden * rng.normal(0.0, 1.0, size=source.shape)
        if clip_to_input_range:
            lower = float(np.min(source))
            upper = float(np.max(source))
            transformed = np.clip(transformed, lower, upper)
    if not np.isfinite(transformed).all():
        raise ValueError("Proxy operator produced non-finite action values.")
    if is_object:
        return _copy_action(action, transformed)
    return transformed


__all__ = ["apply_proxy_burden_to_action"]
