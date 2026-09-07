"""Connectome-level dopamine-class transform used by the replication protocol.

This transform is a preregistered computational hypothesis.  It uses a
reviewed class-level target set and never identifies a target merely from a
gene name.  It intentionally acts on a connectome edge vector before motor
commands are generated; it is not an action-level attenuation operator.
"""

from __future__ import annotations

from collections.abc import Iterable
import math

import numpy as np


DEFAULT_FULL_PRESYNAPTIC_GAIN = 0.15


def _bounded_burden(burden: float) -> float:
    value = float(burden)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("burden must be finite and within [0, 1].")
    return value


def _full_gain(value: float) -> float:
    gain = float(value)
    if not math.isfinite(gain) or not 0.0 <= gain <= 1.0:
        raise ValueError("full_presynaptic_gain must be finite and within [0, 1].")
    return gain


def gain_at_burden(burden: float, *, full_presynaptic_gain: float = DEFAULT_FULL_PRESYNAPTIC_GAIN) -> float:
    """Interpolate a dimensionless computational gain with identity at zero."""

    bounded = _bounded_burden(burden)
    full_gain = _full_gain(full_presynaptic_gain)
    return 1.0 + bounded * (full_gain - 1.0)


def apply_dopamine_class_presynaptic_transform(
    weights: Iterable[float],
    presynaptic_ids: Iterable[str],
    target_neuron_ids: Iterable[str],
    *,
    burden: float,
    full_presynaptic_gain: float = DEFAULT_FULL_PRESYNAPTIC_GAIN,
) -> np.ndarray:
    """Return transformed edge weights without mutating the input vector.

    For an edge ``i -> j`` whose presynaptic root ID is in the separately
    reviewed dopamine-class set, the rule is:

    ``w'_ij = (1 + b * (g_full - 1)) * w_ij``.

    ``b`` is a dimensionless computational burden, not a measured percentage
    of dopamine loss.  A zero burden returns an exact value copy.
    """

    source = np.asarray(list(weights), dtype=float)
    presynaptic = np.asarray([str(value) for value in presynaptic_ids], dtype=object)
    targets = {str(value) for value in target_neuron_ids}
    if source.ndim != 1 or presynaptic.ndim != 1 or source.shape != presynaptic.shape:
        raise ValueError("weights and presynaptic_ids must be one-dimensional with equal length.")
    if not np.isfinite(source).all():
        raise ValueError("weights must be finite.")
    if not targets:
        raise ValueError("target_neuron_ids must contain reviewed identifiers.")

    gain = gain_at_burden(burden, full_presynaptic_gain=full_presynaptic_gain)
    transformed = source.copy()
    if burden == 0.0:
        return transformed
    transformed[np.isin(presynaptic, list(targets))] *= gain
    if not np.isfinite(transformed).all():
        raise ValueError("dopamine transform produced non-finite weights.")
    return transformed


__all__ = [
    "DEFAULT_FULL_PRESYNAPTIC_GAIN",
    "apply_dopamine_class_presynaptic_transform",
    "gain_at_burden",
]
