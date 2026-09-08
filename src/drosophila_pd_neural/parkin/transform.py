"""Pure CPU neural transform applied before brain-to-body action generation."""

from __future__ import annotations

from typing import Iterable

import numpy as np

from .mapping import MappingValidationError
from .protocol import validate_parameter


class NeuralTransformError(ValueError):
    """Raised when a neural transform cannot be applied safely."""


def apply_parkin_neural_transform(
    base_weights: np.ndarray,
    presynaptic_indices: np.ndarray,
    target_indices: Iterable[int],
    parameter: float,
) -> np.ndarray:
    """Return a new weight vector with target outgoing influence attenuated.

    ``presynaptic_indices`` must come from the explicit connectome ordering;
    root IDs are never treated as tensor indices by this function.
    """

    strength = validate_parameter(parameter)
    weights = np.asarray(base_weights)
    presynaptic = np.asarray(presynaptic_indices)
    if weights.ndim != 1 or presynaptic.ndim != 1 or weights.shape != presynaptic.shape:
        raise NeuralTransformError("Weights and presynaptic indices must be matching one-dimensional arrays.")
    if not np.issubdtype(presynaptic.dtype, np.integer):
        raise NeuralTransformError("Presynaptic indices must be integer connectome indices.")
    if not np.isfinite(weights).all():
        raise NeuralTransformError("Healthy neural weights contain NaN or Inf.")
    targets = np.asarray(tuple(target_indices), dtype=np.int64)
    if targets.ndim != 1 or targets.size == 0 or np.unique(targets).size != targets.size:
        raise NeuralTransformError("Target connectome indices must be non-empty and unique.")
    if np.any(targets < 0):
        raise NeuralTransformError("Target connectome indices must be non-negative.")
    if not np.issubdtype(weights.dtype, np.floating):
        raise NeuralTransformError("Neural weights must use a floating-point dtype.")

    result = np.array(weights, copy=True)
    if strength == 0.0:
        return result
    affected = np.isin(presynaptic, targets)
    result[affected] *= np.asarray(1.0 - strength, dtype=result.dtype)
    if not np.isfinite(result).all():
        raise NeuralTransformError("Neural transform produced NaN or Inf.")
    return result


def apply_parkin_transform_from_root_ids(
    base_weights: np.ndarray,
    presynaptic_indices: np.ndarray,
    connectome_root_ids: Iterable[str],
    target_root_ids: Iterable[str],
    parameter: float,
) -> np.ndarray:
    """Resolve root IDs through an explicit completeness ordering, then transform."""

    root_ids = tuple(str(value) for value in connectome_root_ids)
    if len(root_ids) != len(set(root_ids)):
        raise NeuralTransformError("Connectome root-ID ordering must be unique.")
    index = {root_id: position for position, root_id in enumerate(root_ids)}
    target_ids = tuple(str(value) for value in target_root_ids)
    missing = sorted(set(target_ids).difference(index))
    if missing:
        raise NeuralTransformError(f"Reviewed target root IDs missing from connectome ordering: {missing[:5]}")
    target_indices = [index[root_id] for root_id in target_ids]
    return apply_parkin_neural_transform(base_weights, presynaptic_indices, target_indices, parameter)
