"""Run a small platform-protocol probe; never starts a FlyGym simulation."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments/gate_12e_proxy_operator/configs/proxy_burden_action_operator.yaml"
PLATFORM_ROOT = ROOT.parent / "drosophila-pd-flygym"


def _action(values: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "joint_angles": values.copy(),
        "adhesion_onoff": np.asarray([True, False, True, False, True, False], dtype=bool),
    }


def main() -> int:
    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from drosophila_pd_neural.action_hook_adapter import (
        apply_proxy_operator_to_locomotion_action,
    )
    from drosophila_pd_neural.platform_contract import inspect_platform
    from drosophila_pd_neural.platform_perturbation import ProxyBurdenPerturbation

    document = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    source = np.linspace(-1.0, 1.0, 42, dtype=float)
    original = _action(source)
    before = original["joint_angles"].copy()
    zero = apply_proxy_operator_to_locomotion_action(
        original, 0.0, operator_config=document, seed=7
    )
    full = apply_proxy_operator_to_locomotion_action(
        original, 1.0, operator_config=document, seed=7
    )
    repeat = apply_proxy_operator_to_locomotion_action(
        original, 1.0, operator_config=document, seed=7
    )

    assert np.array_equal(original["joint_angles"], before)
    assert np.array_equal(zero["joint_angles"], source)
    assert np.allclose(full["joint_angles"], source * 0.5)
    assert np.array_equal(full["adhesion_onoff"], original["adhesion_onoff"])
    assert np.array_equal(full["joint_angles"], repeat["joint_angles"])
    assert full["joint_angles"].shape == (42,)
    assert full["adhesion_onoff"].shape == (6,)
    assert np.isfinite(full["joint_angles"]).all()

    perturbation = ProxyBurdenPerturbation(
        burden_level=0.5,
        operator_config=document,
        name="smoke_proxy_burden",
        random_seed=7,
    )
    protocol_result = perturbation.apply_to_action(
        original,
        SimpleNamespace(step_index=0, random_seed=7, expected_joint_angle_count=42),
    )
    assert np.array_equal(protocol_result["adhesion_onoff"], original["adhesion_onoff"])
    contract = inspect_platform(PLATFORM_ROOT)
    status = "PLATFORM_PROTOCOL_READY" if contract.ready else contract.status
    print(json.dumps({
        "status": status,
        "simulation_run": False,
        "platform_contract": contract.as_dict(),
        "perturbation": perturbation.metadata(),
    }, indent=2, ensure_ascii=False))
    print(f"ACTION_HOOK_INTEGRATION_SMOKE_TEST_{'PASS' if contract.ready else 'WAITING_PLATFORM_CAPABILITY'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
