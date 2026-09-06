import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml

from scripts.run_healthy_baseline_multiseed import _load_config
from scripts.run_healthy_baseline_multiseed import _rollout_quality
from scripts.run_healthy_baseline_multiseed import _discard_raw_artifacts
from scripts.run_healthy_baseline_multiseed import build_parser


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


def test_gate11_discard_raw_writes_hash_manifest_before_removal(tmp_path: Path) -> None:
    output_root = tmp_path / "baseline"
    output = output_root / "results" / "seed_000"
    output.mkdir(parents=True)
    raw = output / "rollout.npz"
    raw.write_bytes(b"raw-rollout")

    manifest_path, count, total_bytes = _discard_raw_artifacts(
        output=output,
        output_root=output_root,
        seed=0,
    )

    assert not output.exists()
    assert manifest_path.is_file()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["deleted_after_qc"] is True
    assert payload["artifacts"] == [{
        "path": "rollout.npz",
        "size_bytes": len(b"raw-rollout"),
        "sha256": _sha256(raw) if raw.exists() else hashlib.sha256(b"raw-rollout").hexdigest(),
    }]
    assert count == 1
    assert total_bytes == len(b"raw-rollout")


def test_gate11_discard_raw_flag_is_opt_in() -> None:
    assert build_parser().parse_args([]).discard_raw is False
    assert build_parser().parse_args(["--discard-raw"]).discard_raw is True


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
