"""Chay smoke test nho cho proxy burden operator, khong chay simulation."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from drosophila_pd_neural.proxy_burden_operator import apply_proxy_burden_to_action


def main() -> int:
    config_path = ROOT / "experiments/gate_12e_proxy_operator/configs/proxy_burden_action_operator.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    operator = config["operator"]
    source = np.asarray([-1.0, -0.25, 0.0, 0.5, 1.0], dtype=float)
    before = source.copy()
    zero = apply_proxy_burden_to_action(
        source,
        0.0,
        mode=operator["type"],
        attenuation_strength=operator["attenuation_strength"],
        noise_strength=operator["noise_strength"],
        seed=0,
        clip_to_input_range=operator["clip_output"],
    )
    full = apply_proxy_burden_to_action(
        source,
        1.0,
        mode=operator["type"],
        attenuation_strength=operator["attenuation_strength"],
        noise_strength=operator["noise_strength"],
        seed=0,
        clip_to_input_range=operator["clip_output"],
    )
    repeat = apply_proxy_burden_to_action(
        source,
        1.0,
        mode=operator["type"],
        attenuation_strength=operator["attenuation_strength"],
        noise_strength=0.1,
        seed=17,
        clip_to_input_range=operator["clip_output"],
    )
    repeat_again = apply_proxy_burden_to_action(
        source,
        1.0,
        mode=operator["type"],
        attenuation_strength=operator["attenuation_strength"],
        noise_strength=0.1,
        seed=17,
        clip_to_input_range=operator["clip_output"],
    )
    assert np.array_equal(source, before)
    assert np.array_equal(zero, source)
    assert np.allclose(full, source * 0.5)
    assert np.array_equal(repeat, repeat_again)
    assert full.shape == source.shape
    assert np.isfinite(full).all() and np.isfinite(repeat).all()
    print("PROXY_BURDEN_OPERATOR_SMOKE_TEST_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
