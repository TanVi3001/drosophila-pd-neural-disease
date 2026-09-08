"""Reviewed Parkin driver-defined neural transform primitives.

This package represents a computational intervention on a reviewed target
population. It does not claim a biological synaptic mechanism.
"""

from .mapping import MappingValidationError, ReviewedParkinMapping, load_completeness_root_ids, load_reviewed_mapping
from .protocol import PARAMETER_GRID, TRANSFORM_ID, build_transform_contract
from .transform import NeuralTransformError, apply_parkin_neural_transform, apply_parkin_transform_from_root_ids

__all__ = [
    "MappingValidationError",
    "NeuralTransformError",
    "PARAMETER_GRID",
    "TRANSFORM_ID",
    "ReviewedParkinMapping",
    "apply_parkin_neural_transform",
    "apply_parkin_transform_from_root_ids",
    "build_transform_contract",
    "load_completeness_root_ids",
    "load_reviewed_mapping",
]
