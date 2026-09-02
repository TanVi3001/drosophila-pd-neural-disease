"""Run a small action-boundary probe; never starts a FlyGym simulation."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments/gate_12e_proxy_operator/configs/proxy_burden_action_operator.yaml"


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

    external_runner = ROOT.parent / "drosophila-pd-flygym/scripts/run_brain_body_rollout.py"
    patch_marker = "--enable-proxy-burden-operator"
    patch_applied = external_runner.is_file() and patch_marker in external_runner.read_text(
        encoding="utf-8"
    )
    if patch_applied:
        status = "CONNECTED_TO_EXTERNAL_RUNTIME"
    else:
        status = "ADAPTER_PASS_PATCH_PREPARED_NOT_RUNTIME_EXECUTED"
    print(json.dumps({"status": status, "simulation_run": False}, indent=2))
    print(f"ACTION_HOOK_INTEGRATION_SMOKE_TEST_{'PASS' if patch_applied else 'PASS_WITHOUT_RUNTIME_EXECUTION'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
