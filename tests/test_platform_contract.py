from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import yaml

from drosophila_pd_neural.platform_contract import inspect_platform
from drosophila_pd_neural.platform_perturbation import ProxyBurdenPerturbation


ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT.parent / "drosophila-pd-flygym"
OPERATOR_CONFIG = ROOT / "experiments/gate_12e_proxy_operator/configs/proxy_burden_action_operator.yaml"


def test_current_platform_matches_required_source_contract() -> None:
    if not PLATFORM.is_dir():
        import pytest

        pytest.skip("external FlyGym platform worktree is not distributed in Git")
    contract = inspect_platform(PLATFORM)

    assert contract.ready
    assert contract.package_name == "drosophila-pd-flygym"
    assert contract.package_version == "1.0.0"
    assert contract.git_commit
    assert {
        "perturbation_protocol",
        "healthy_baseline",
        "brain_driven_bridge",
        "canonical_locomotion_hook",
    }.issubset(contract.capabilities)


def test_missing_platform_is_an_explicit_waiting_state(tmp_path: Path) -> None:
    contract = inspect_platform(tmp_path / "missing-platform")

    assert contract.ready is False
    assert contract.status == "WAITING_PLATFORM_CAPABILITY"
    assert "platform_root_missing" in contract.blockers


def test_proxy_perturbation_implements_platform_action_boundary() -> None:
    operator_config = yaml.safe_load(OPERATOR_CONFIG.read_text(encoding="utf-8"))
    source = {
        "joint_angles": np.linspace(-1.0, 1.0, 42),
        "adhesion_onoff": np.asarray([True, False, True, False, True, False]),
    }
    original = source["joint_angles"].copy()
    perturbation = ProxyBurdenPerturbation(
        burden_level=0.5,
        operator_config=operator_config,
        random_seed=11,
    )
    context = SimpleNamespace(
        step_index=4,
        random_seed=2,
        expected_joint_angle_count=42,
    )

    first = perturbation.apply_to_action(source, context)
    second = perturbation.apply_to_action(source, context)

    assert np.array_equal(source["joint_angles"], original)
    assert np.array_equal(first["adhesion_onoff"], source["adhesion_onoff"])
    assert np.array_equal(first["joint_angles"], second["joint_angles"])
    assert first["joint_angles"].shape == (42,)
    assert np.isfinite(first["joint_angles"]).all()
    assert perturbation.metadata()["intervention_stage"] == "post_controller_pre_simulation_action"
    assert perturbation.metadata()["adhesion_onoff_modified"] is False
