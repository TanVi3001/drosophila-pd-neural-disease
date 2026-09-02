from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

from drosophila_pd_neural.action_hook_adapter import (
    apply_proxy_operator_to_locomotion_action,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments/gate_12f_b_action_hook_integration/configs/action_hook_integration_config.yaml"
MANIFEST = ROOT / "experiments/gate_12f_b_action_hook_integration/manifests/action_hook_integration_manifest.json"
PATCH = ROOT / "experiments/gate_12f_b_action_hook_integration/patches/flygym_proxy_burden_hook.patch"
REPORT = ROOT / "docs/disease_rollouts/gate_12f_b_action_hook_integration_report.md"
OPERATOR_CONFIG = ROOT / "experiments/gate_12e_proxy_operator/configs/proxy_burden_action_operator.yaml"


def _action() -> dict[str, np.ndarray]:
    return {
        "joint_angles": np.linspace(-1.0, 1.0, 42),
        "adhesion_onoff": np.asarray([True, False, True, False, True, False]),
    }


def test_adapter_does_not_mutate_input_and_preserves_adhesion() -> None:
    config = yaml.safe_load(OPERATOR_CONFIG.read_text(encoding="utf-8"))
    source = _action()
    before = source["joint_angles"].copy()
    result = apply_proxy_operator_to_locomotion_action(source, 0.75, operator_config=config, seed=4)

    assert np.array_equal(source["joint_angles"], before)
    assert np.array_equal(result["adhesion_onoff"], source["adhesion_onoff"])
    assert result["joint_angles"].shape == (42,)
    assert np.isfinite(result["joint_angles"]).all()
    assert result is not source


def test_burden_zero_is_identity_and_burden_one_attenuates() -> None:
    config = yaml.safe_load(OPERATOR_CONFIG.read_text(encoding="utf-8"))
    source = _action()
    zero = apply_proxy_operator_to_locomotion_action(source, 0.0, operator_config=config, seed=4)
    full = apply_proxy_operator_to_locomotion_action(source, 1.0, operator_config=config, seed=4)

    assert np.array_equal(zero["joint_angles"], source["joint_angles"])
    assert np.allclose(full["joint_angles"], source["joint_angles"] * 0.5)


def test_adapter_is_deterministic_for_same_seed() -> None:
    config = yaml.safe_load(OPERATOR_CONFIG.read_text(encoding="utf-8"))
    source = _action()
    first = apply_proxy_operator_to_locomotion_action(source, 0.5, operator_config=config, seed=9)
    second = apply_proxy_operator_to_locomotion_action(source, 0.5, operator_config=config, seed=9)

    assert np.array_equal(first["joint_angles"], second["joint_angles"])


def test_gate12f_b_artifacts_preserve_boundary() -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    report = REPORT.read_text(encoding="utf-8")

    assert config["hook"]["joint_angles_shape"] == [42]
    assert config["operator"]["modifies_adhesion_onoff"] is False
    assert manifest["patch_applied_to_external_runtime"] is True
    assert manifest["no_full_rollout_run"] is True
    assert manifest["no_calibration_run"] is True
    assert manifest["no_holdout_validation_run"] is True
    assert manifest["no_disease_metrics_created"] is True
    assert PATCH.is_file()
    assert "--enable-proxy-burden-operator" in PATCH.read_text(encoding="utf-8")
    assert "CONNECTED_TO_EXTERNAL_RUNTIME" in report
    assert "Không full disease rollout" in report
