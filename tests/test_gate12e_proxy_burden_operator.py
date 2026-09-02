from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from drosophila_pd_neural import apply_proxy_burden_to_action
from scripts import run_disease_conditions_multiseed as runner


ROOT = Path(__file__).resolve().parents[1]
OPERATOR_CONFIG = ROOT / "experiments/gate_12e_proxy_operator/configs/proxy_burden_action_operator.yaml"
PROXY_CONFIG = ROOT / "experiments/gate_12c_computational_proxy_configs/configs/alpha_synuclein_proxy_condition.yaml"


def _operator_kwargs() -> dict[str, object]:
    document = yaml.safe_load(OPERATOR_CONFIG.read_text(encoding="utf-8"))
    operator = document["operator"]
    return {
        "mode": operator["type"],
        "attenuation_strength": operator["attenuation_strength"],
        "noise_strength": operator["noise_strength"],
        "clip_to_input_range": operator["clip_output"],
    }


def test_operator_import_and_zero_burden_identity_without_mutation() -> None:
    source = np.asarray([-1.0, -0.25, 0.5, 1.0])
    before = source.copy()
    result = apply_proxy_burden_to_action(source, 0.0, seed=3, **_operator_kwargs())

    assert np.array_equal(result, source)
    assert np.array_equal(source, before)
    assert result is not source


@pytest.mark.parametrize("burden", [-0.01, 1.01, np.nan, np.inf])
def test_operator_rejects_invalid_burden(burden: float) -> None:
    with pytest.raises(ValueError):
        apply_proxy_burden_to_action(np.ones(3), burden, **_operator_kwargs())


def test_operator_full_burden_attenuates_using_configured_strength() -> None:
    source = np.asarray([-1.0, -0.25, 0.5, 1.0])
    result = apply_proxy_burden_to_action(source, 1.0, **_operator_kwargs())

    assert result.shape == source.shape
    assert np.allclose(result, source * 0.5)
    assert np.isfinite(result).all()


def test_operator_noise_is_deterministic_for_same_seed() -> None:
    source = np.asarray([-0.5, 0.0, 0.5])
    kwargs = _operator_kwargs() | {"noise_strength": 0.2}

    first = apply_proxy_burden_to_action(source, 0.75, seed=42, **kwargs)
    second = apply_proxy_burden_to_action(source, 0.75, seed=42, **kwargs)

    assert np.array_equal(first, second)
    assert np.isfinite(first).all()


def test_operator_config_is_valid_and_contains_no_target_tuning() -> None:
    blockers, document = runner._proxy_operator_config_blockers(OPERATOR_CONFIG)

    assert blockers == []
    assert document["status"] == "OPERATOR_IMPLEMENTED"
    assert document["forbidden"]["chen_tuning"] is True
    assert document["forbidden"]["pozo_tuning"] is True
    config_text = OPERATOR_CONFIG.read_text(encoding="utf-8").lower()
    assert "chen" in config_text and "pozo" in config_text


def test_organism_proxy_does_not_require_neural_targets() -> None:
    document = yaml.safe_load(PROXY_CONFIG.read_text(encoding="utf-8"))

    blockers = runner._proxy_config_blockers(
        condition_id="alpha_synuclein",
        document=document,
        initial_blockers=[],
    )

    assert "target_neurons_or_edges_missing" not in blockers


def test_gene_specific_proxy_still_requires_neural_targets() -> None:
    document = yaml.safe_load(PROXY_CONFIG.read_text(encoding="utf-8"))
    document["scope"] = "gene_specific"
    document["target_definition"]["gene_specific_mapping"] = True

    blockers = runner._proxy_config_blockers(
        condition_id="alpha_synuclein",
        document=document,
        initial_blockers=[],
    )

    assert "target_neurons_or_edges_missing" in blockers


def test_gate12d_runner_preserves_blocked_status_without_action_hook() -> None:
    source = (ROOT / "scripts/run_disease_conditions_multiseed.py").read_text(encoding="utf-8")
    manifest = json_load(ROOT / "experiments/gate_12d_proxy_rollouts/manifests/proxy_disease_rollout_manifest.json")

    assert "proxy_burden_to_action_operator_not_connected_to_current_brain_body_runner" in source
    assert '"operator_applied": False' in source
    assert manifest["status"].endswith("ROLLOUTS_BLOCKED")


def json_load(path: Path) -> dict[str, object]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))
