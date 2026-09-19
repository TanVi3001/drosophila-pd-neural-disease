"""FlyGym-platform-compatible computational proxy perturbation.

The platform owns the simulation loop and calls a ``Perturbation`` object at
the controller/action boundary. This module implements that protocol without
importing the platform package, so the neural repository remains independently
testable while remaining compatible with the platform's public contract.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .action_hook_adapter import apply_proxy_operator_to_locomotion_action


COMPUTATIONAL_SCOPE = (
    "A deterministic action-level computational locomotion proxy. It is not a "
    "biological Parkinson model, neural mechanism, clinical prediction, or "
    "treatment-response assessment."
)


@dataclass(frozen=True)
class ProxyBurdenPerturbation:
    """Apply the declared proxy operator through the platform Perturbation API."""

    burden_level: float = 0.0
    operator_config: Mapping[str, Any] = field(default_factory=dict)
    name: str = "proxy_burden"
    config_id: str | None = None
    random_seed: int = 0

    def __post_init__(self) -> None:
        burden = float(self.burden_level)
        if not np.isfinite(burden) or not 0.0 <= burden <= 1.0:
            raise ValueError("burden_level must be finite and within [0, 1].")
        if not isinstance(self.operator_config, Mapping):
            raise TypeError("operator_config must be a mapping.")
        if not str(self.name).strip():
            raise ValueError("name must be a non-empty string.")
        if int(self.random_seed) < 0:
            raise ValueError("random_seed must be non-negative.")
        object.__setattr__(self, "burden_level", burden)
        object.__setattr__(self, "operator_config", dict(self.operator_config))
        object.__setattr__(self, "config_id", None if self.config_id is None else str(self.config_id))
        object.__setattr__(self, "random_seed", int(self.random_seed))

    @property
    def perturbation_type(self) -> str:
        """Return the stable platform perturbation type."""

        return "proxy_burden"

    def apply_to_config(self, config: Any) -> Any:
        """Leave the simulation configuration unchanged."""

        return config

    def apply_to_controller(self, controller: Any, context: Any) -> Any:
        """Leave the platform controller unchanged."""

        return controller

    def apply_to_action(self, action: Any, context: Any) -> Any:
        """Transform one action while preserving adhesion and input immutability."""

        expected = int(getattr(context, "expected_joint_angle_count", 42))
        step_index = int(getattr(context, "step_index", 0))
        context_seed = int(getattr(context, "random_seed", 0))
        seed_state = np.random.SeedSequence(
            [self.random_seed, context_seed, step_index]
        ).generate_state(1)
        seed = int(seed_state[0])
        return apply_proxy_operator_to_locomotion_action(
            action,
            self.burden_level,
            operator_config=self.operator_config,
            seed=seed,
            expected_joint_angle_count=expected if expected > 0 else None,
        )

    def metadata(self) -> dict[str, Any]:
        """Return metadata accepted by the platform's perturbation reports."""

        return {
            "type": self.perturbation_type,
            "name": self.name,
            "config_id": self.config_id,
            "parameters": {
                "burden_level": self.burden_level,
                "random_seed": self.random_seed,
                "operator": dict(self.operator_config),
            },
            "intervention_target": "controller_joint_angle_commands",
            "intervention_stage": "post_controller_pre_simulation_action",
            "deterministic": True,
            "action_validation": "structural_only",
            "adhesion_onoff_modified": False,
            "scientific_scope": COMPUTATIONAL_SCOPE,
            "description": (
                "Dimensionless action-level proxy burden applied through the "
                "canonical FlyGym Perturbation protocol."
            ),
        }


__all__ = ["COMPUTATIONAL_SCOPE", "ProxyBurdenPerturbation"]
