"""Paper-guided computational replication utilities for Riemensperger et al.

The package deliberately models a reviewed *computational hypothesis*, not a
biological disease mechanism or a gene-specific intervention.
"""

from .dopamine_transform import apply_dopamine_class_presynaptic_transform
from .metrics import rollout_seed_metrics

__all__ = ["apply_dopamine_class_presynaptic_transform", "rollout_seed_metrics"]
