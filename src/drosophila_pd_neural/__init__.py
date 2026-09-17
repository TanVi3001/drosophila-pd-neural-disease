"""Evidence-constrained neural perturbations for Drosophila locomotion.

The package is an additive extension to the canonical
``drosophila-pd-flygym`` platform. It owns neural-condition data preparation,
provenance, and platform-compatible action perturbations; it does not own the
FlyGym simulation, connectome source, checkpoint source, or scientific claims.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("drosophila-pd-neural-disease")
except PackageNotFoundError:
    __version__ = "0+unknown"

from .calibration import compute_loss
from .action_hook_adapter import apply_proxy_operator_to_locomotion_action
from .models import DiseaseCondition, DiseaseProfile, NeuralParameters
from .platform_contract import (
    PLATFORM_REQUIRED_FILES,
    PlatformContract,
    default_platform_root,
    inspect_platform,
)
from .platform_perturbation import ProxyBurdenPerturbation
from .perturbations import perturb_edges
from .proxy_burden_operator import apply_proxy_burden_to_action

__all__ = [
    "__version__",
    "DiseaseCondition",
    "DiseaseProfile",
    "NeuralParameters",
    "PLATFORM_REQUIRED_FILES",
    "PlatformContract",
    "ProxyBurdenPerturbation",
    "compute_loss",
    "default_platform_root",
    "apply_proxy_operator_to_locomotion_action",
    "inspect_platform",
    "perturb_edges",
    "apply_proxy_burden_to_action",
]
