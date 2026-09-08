"""Gate24.1 preregistered neural transform contract helpers."""

from __future__ import annotations

from typing import Any


TRANSFORM_ID = "gate24_parkin_driver_defined_neural_outgoing_attenuation_v1"
PARAMETER_GRID = (0.0, 0.25, 0.5, 0.75, 1.0)


def validate_parameter(value: float) -> float:
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("Neural perturbation strength must be finite.")
    if not 0.0 <= value <= 1.0:
        raise ValueError("Neural perturbation strength must be between 0 and 1.")
    return value


def build_transform_contract(*, mapping_sha256: str, root_set_sha256: str, source_code_sha256: str) -> dict[str, Any]:
    return {
        "transform_id": TRANSFORM_ID,
        "target_population": "330 reviewed Parkin TH-GAL4 driver-defined FlyWire root IDs",
        "target_count": 330,
        "target_sha256": root_set_sha256,
        "mapping_sha256": mapping_sha256,
        "operation_level": "NEURAL_PRE_ACTION",
        "mathematical_definition": "w_prime[e] = w[e] * (1 - p) when presynaptic_root[e] is in T; otherwise w_prime[e] = w[e]",
        "parameter_name": "neural_perturbation_strength",
        "parameter_domain": "dimensionless [0, 1]",
        "identity_condition": "p = 0 returns an exact copy of the healthy neural representation",
        "deterministic_policy": "CPU deterministic array transform; no random noise",
        "healthy_checkpoint_policy": "immutable input; never overwritten",
        "disease_checkpoint_policy": "new artifact with independent SHA256 and manifest",
        "expected_computational_effect": "attenuate outgoing synaptic influence from the reviewed target population before action generation",
        "biological_equivalence": "NOT_ASSERTED",
        "limitations": [
            "The parameter is not a biological knockdown percentage.",
            "Driver-defined mapping is not direct Parkin expression in FlyWire.",
            "The transform does not establish biological Parkinson validation.",
        ],
        "sensitivity_grid": list(PARAMETER_GRID),
        "primary_parameter_status": "WAITING_PRIMARY_PARKIN_PARAMETER_DECISION",
        "source_code_sha256": source_code_sha256,
    }
