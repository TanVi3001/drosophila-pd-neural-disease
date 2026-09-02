"""Bridge the existing proxy operator to a real FlyGym locomotion action.

The adapter owns no simulation state.  It receives the ``LocomotionAction``
created by the external controller, copies its joint command, and returns a
new action.  This keeps the integration point explicit and makes the adapter
usable with a protocol or a plain mapping during a small integration probe.
"""

from __future__ import annotations

from collections.abc import Mapping
import copy
from dataclasses import replace
from typing import Any

import numpy as np

from .proxy_burden_operator import apply_proxy_burden_to_action


JOINT_ANGLES_SHAPE = (42,)


def _operator_options(operator_config: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(operator_config, Mapping):
        raise TypeError("operator_config must be a mapping.")
    nested = operator_config.get("operator", operator_config)
    if not isinstance(nested, Mapping):
        raise TypeError("operator_config['operator'] must be a mapping.")
    return {
        "mode": str(nested.get("type", "amplitude_attenuation")),
        "attenuation_strength": nested.get("attenuation_strength", 0.5),
        "noise_strength": nested.get("noise_strength", 0.0),
        "clip_to_input_range": bool(
            nested.get("clip_output", nested.get("clip_to_input_range", True))
        ),
    }


def _joint_angles(action: Any) -> np.ndarray:
    if isinstance(action, Mapping):
        if "joint_angles" not in action:
            raise TypeError("Action mapping must contain 'joint_angles'.")
        values = np.asarray(action["joint_angles"], dtype=float)
    elif hasattr(action, "joint_angles"):
        values = np.asarray(action.joint_angles, dtype=float)
    else:
        raise TypeError("Action must expose joint_angles or be a mapping.")
    if values.shape != JOINT_ANGLES_SHAPE:
        raise ValueError(
            "LocomotionAction joint_angles must have shape (42,), "
            f"received {values.shape}."
        )
    if not np.isfinite(values).all():
        raise ValueError("LocomotionAction joint_angles must be finite.")
    return values


def _copy_mapping_action(action: Mapping[str, Any], values: np.ndarray) -> dict[str, Any]:
    result = dict(action)
    result["joint_angles"] = values.copy()
    if "adhesion_onoff" in result and result["adhesion_onoff"] is not None:
        result["adhesion_onoff"] = np.asarray(result["adhesion_onoff"], dtype=bool).copy()
    return result


def _copy_protocol_action(action: Any, values: np.ndarray) -> Any:
    """Rebuild an external action, with a copy-based protocol fallback."""

    try:
        return type(action)(
            joint_angles=values.copy(),
            adhesion_onoff=(
                None
                if getattr(action, "adhesion_onoff", None) is None
                else np.asarray(action.adhesion_onoff, dtype=bool).copy()
            ),
        )
    except (TypeError, ValueError):
        try:
            return replace(action, joint_angles=values.copy())
        except (TypeError, ValueError):
            try:
                result = copy.copy(action)
                result.joint_angles = values.copy()
                if hasattr(action, "adhesion_onoff"):
                    result.adhesion_onoff = (
                        None
                        if action.adhesion_onoff is None
                        else np.asarray(action.adhesion_onoff, dtype=bool).copy()
                    )
                return result
            except (AttributeError, TypeError) as exc:
                raise TypeError(
                    "External LocomotionAction cannot be reconstructed; "
                    "provide a protocol object or mapping with joint_angles."
                ) from exc


def apply_proxy_operator_to_locomotion_action(
    locomotion_action: Any,
    burden_level: float,
    *,
    operator_config: dict[str, Any],
    seed: int | None = None,
) -> Any:
    """Apply the configured proxy operator at the FlyGym action boundary.

    Only ``joint_angles`` are transformed.  ``adhesion_onoff`` is copied and
    preserved exactly; the incoming action and its arrays are never mutated.
    The function is deliberately limited to the 42-DOF locomotion contract
    discovered in Gate 12F-A.
    """

    source = _joint_angles(locomotion_action)
    transformed = apply_proxy_burden_to_action(
        source,
        burden_level,
        seed=seed,
        **_operator_options(operator_config),
    )
    if not np.isfinite(transformed).all():
        raise ValueError("Proxy operator produced non-finite joint angles.")
    if isinstance(locomotion_action, Mapping):
        return _copy_mapping_action(locomotion_action, transformed)
    return _copy_protocol_action(locomotion_action, transformed)


__all__ = ["JOINT_ANGLES_SHAPE", "apply_proxy_operator_to_locomotion_action"]
