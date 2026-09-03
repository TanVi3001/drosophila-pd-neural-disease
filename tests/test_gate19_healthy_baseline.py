import json
from pathlib import Path

import pytest

from scripts.run_healthy_baseline_gate19 import (
    _load_config,
    _read_gate19_metrics,
    _runner_supports_tracking,
    build_parser,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments/gate_19_healthy_baseline/configs/healthy_baseline_multiseed.yaml"
PLATFORM = ROOT.parent / "drosophila-pd-flygym"


def test_gate19_config_locks_healthy_protocol() -> None:
    config = _load_config(CONFIG)
    assert config["execution"]["seeds"] == [0, 1, 2, 3, 4]
    assert config["execution"]["steps"] == 100000
    assert config["execution"]["timestep_s"] == 0.0001
    assert config["disease_layer_enabled"] is False
    assert config["calibration_enabled"] is False
    assert config["holdout_enabled"] is False
    assert config["video"]["camera_mode"] == "tracking"


def test_gate19_parser_has_no_disease_switch() -> None:
    args = build_parser().parse_args([])
    assert args.config == CONFIG


def test_gate19_local_platform_has_tracking_hook_when_available() -> None:
    if not PLATFORM.is_dir():
        return
    assert _runner_supports_tracking(PLATFORM) is True


def test_gate19_aggregates_mapping_metrics_without_editing_source_schema(tmp_path: Path) -> None:
    path = tmp_path / "metrics.json"
    path.write_text(
        json.dumps(
            {
                "scalar_metrics": {"walking_speed_mm_s": 2.0},
                "contact_ratio": {"contact_0": 0.8, "contact_1": 1.0},
                "joint_rms_velocity": {"joint_0": 2.0, "joint_1": 4.0},
            }
        ),
        encoding="utf-8",
    )

    metrics = _read_gate19_metrics(path)

    assert metrics["walking_speed_mm_s"] == 2.0
    assert metrics["contact_ratio"] == 0.9
    assert metrics["joint_rms_velocity"] == 3.0


def test_gate19_rejects_nonfinite_mapping_metric(tmp_path: Path) -> None:
    path = tmp_path / "metrics.json"
    path.write_text(
        json.dumps(
            {
                "contact_ratio": {"contact_0": 0.8, "contact_1": float("nan")},
                "joint_rms_velocity": {"joint_0": 2.0},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="NaN or Inf"):
        _read_gate19_metrics(path)
