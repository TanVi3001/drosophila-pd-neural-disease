import csv
import json
from pathlib import Path

import numpy as np
import yaml

from scripts.run_healthy_baseline_multiseed import _load_config
from scripts.run_healthy_baseline_multiseed import _rollout_quality


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments" / "gate_11_healthy_baseline" / "configs" / "healthy_baseline_multiseed.yaml"
METRICS_CSV = ROOT / "experiments" / "gate_11_healthy_baseline" / "results" / "healthy_baseline_metrics.csv"
METRICS_JSON = ROOT / "experiments" / "gate_11_healthy_baseline" / "results" / "healthy_baseline_metrics.json"
MANIFEST = ROOT / "experiments" / "gate_11_healthy_baseline" / "manifests" / "healthy_baseline_manifest.json"


def test_gate11_config_is_healthy_only_and_uses_planned_seeds() -> None:
    config = _load_config(CONFIG)
    assert config["condition"]["name"] == "healthy_baseline"
    assert config["condition"]["disease_layer_enabled"] is False
    assert config["condition"]["perturbation_config"] is None
    assert config["condition"]["calibration_enabled"] is False
    assert config["execution"]["seeds"] == [0, 1, 2, 3, 4, 5]
    assert config["output"]["include_video"] is False


def test_gate11_yaml_is_parseable() -> None:
    document = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert document["status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert "mean_planar_speed_mm_s" in document["required_metrics"]
    assert "distance_traveled_mm" in document["required_metrics"]


def test_gate11_rollout_quality_checks_real_state_channels(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.npz"
    np.savez(
        rollout,
        timestamp_s=np.array([0.0, 0.1, 0.2]),
        thorax=np.array([[0.0, 0.0, 1.0], [0.1, 0.0, 1.0], [0.2, 0.0, 1.0]]),
        com=np.array([[0.0, 0.0, 1.0], [0.1, 0.0, 1.0], [0.2, 0.0, 1.0]]),
        orientation=np.tile([1.0, 0.0, 0.0, 0.0], (3, 1)),
        joint_positions=np.array([[0.0], [0.1], [0.2]]),
        joint_velocity=np.ones((3, 1)),
        contact_found=np.ones((3, 6)),
        actuator_position=np.array([[0.0], [0.1], [0.2]]),
    )

    quality = _rollout_quality(
        rollout,
        expected_frames=3,
        expected_timestep_s=0.1,
        metrics={"walking_speed_mm_s": 1.0},
    )

    assert quality["timestamp_monotonic"] == "PASS"
    assert quality["timestep_consistent"] == "PASS"
    assert quality["locomotion_detected"] == "PASS"
    assert quality["contact_detected"] == "PASS"
    assert quality["joint_trajectory_changes"] == "PASS"
    assert quality["action_trajectory_valid"] == "PASS"
    assert quality["observation_state_valid"] == "PASS"
    assert quality["quaternion_valid"] == "PASS"


def test_gate11_aggregate_has_canonical_metrics_and_provenance() -> None:
    assert METRICS_CSV.is_file()
    assert METRICS_JSON.is_file()
    assert MANIFEST.is_file()

    with METRICS_CSV.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [int(row["seed"]) for row in rows] == [0, 1, 2, 3, 4, 5]
    for row in rows:
        for metric in ("mean_planar_speed_mm_s", "distance_traveled_mm", "displacement_mm"):
            value = float(row[metric])
            assert np.isfinite(value)
        assert row["no_nan_inf"] == "PASS"
        assert row["locomotion_detected"] == "PASS"
        assert row["contact_detected"] == "PASS"

    payload = json.loads(METRICS_JSON.read_text(encoding="utf-8"))
    assert payload["metric_contract_status"] == "PASS"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["metric_contract"]["status"] == "PASS"
    for metric in ("mean_planar_speed_mm_s", "distance_traveled_mm", "displacement_mm"):
        detail = manifest["metric_contract"]["canonical_metrics"][metric]
        assert detail["source"]
        assert detail["formula"]
