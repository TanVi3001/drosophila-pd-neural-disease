"""Provenance-first integration helpers for Drosophila connectome sources.

The connectome repositories are analysis inputs, not an implicit neural runtime.
This package validates their registry metadata and makes promotion decisions
explicit before an artifact can be used for target selection, checkpoint
preparation, or a rollout.
"""

from .consumer import PromotionDecision, evaluate_promotion
from .registry import ConnectomeRegistry, RegistryError, load_registry

__all__ = [
    "ConnectomeRegistry",
    "PromotionDecision",
    "RegistryError",
    "evaluate_promotion",
    "load_registry",
]
