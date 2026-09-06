import hashlib
import json
from pathlib import Path

import numpy as np

from scripts.analyze_healthy_baseline import audit_run, bootstrap_ci, summarize


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_bootstrap_summary_is_deterministic() -> None:
    low_a, high_a = bootstrap_ci([1.0, 2.0, 3.0], samples=1000, seed=7)
    low_b, high_b = bootstrap_ci([1.0, 2.0, 3.0], samples=1000, seed=7)
    assert (low_a, high_a) == (low_b, high_b)
    rows = [{metric: float(index + 1) for metric in (
        "thorax_planar_displacement_mm",
        "walking_speed_mm_s",
        "planar_path_length_mm",
        "trajectory_efficiency",
        "heading_variance_rad2",
        "joint_velocity_rms_rad_s",
        "body_orientation_variance_rad2",
        "foot_contact_frame_fraction",
    )} for index in range(3)]
    assert summarize(rows, bootstrap_samples=100)[0]["n"] == 3


def test_audit_run_accepts_valid_minimal_rollout_and_warns_for_raw_action(tmp_path: Path) -> None:
    run = tmp_path / "seed_000"
    (run / "metrics").mkdir(parents=True)
    timestamp = np.array([0.0, 0.1, 0.2])
    thorax = np.array([[0.0, 0.0, 1.0], [0.1, 0.0, 1.0], [0.2, 0.0, 1.0]])
    np.savez_compressed(
        run / "rollout.npz",
        timestamp_s=timestamp,
        thorax=thorax,
        com=thorax,
        orientation=np.tile([1.0, 0.0, 0.0, 0.0], (3, 1)),
        joint_positions=np.array([[0.0], [0.1], [0.2]]),
        joint_velocity=np.array([[1.0], [1.0], [1.0]]),
        contact_found=np.ones((3, 6), dtype=bool),
        actuator_position=np.array([[0.0], [0.1], [0.2]]),
    )
    (run / "status.json").write_text(
        json.dumps({
            "status": "PASS",
            "simulation_run": True,
            "command": [
                "python",
                "runner.py",
                "--condition",
                "healthy",
                "--seed",
                "0",
                "--steps",
                "2",
                "--stimulus",
                "p9",
                "--cpg-frequency-hz",
                "12.0",
                "--device",
                "cuda",
            ],
        }),
        encoding="utf-8",
    )
    (run / "metadata.json").write_text("{}", encoding="utf-8")
    (run / "metrics" / "metrics.json").write_text(
        json.dumps({"scalar_metrics": {
            "walking_speed_mm_s": 1.0,
            "heading_variance_rad2": 0.01,
            "body_orientation_variance_rad2": 0.02,
        }}),
        encoding="utf-8",
    )
    files = {}
    for name, relative in {
        "rollout_npz": "rollout.npz",
        "metadata": "metadata.json",
        "metrics": "metrics/metrics.json",
    }.items():
        path = run / relative
        files[name] = {"path": relative, "byte_size": path.stat().st_size, "sha256": _sha256(path)}
    (run / "manifest.json").write_text(json.dumps({"files": files}), encoding="utf-8")

    row, checks = audit_run(
        run,
        seed=0,
        expected_steps=2,
        expected_timestep_s=0.1,
        video_expected=False,
    )
    assert row["status"] == "PASS_WITH_LIMITATIONS"
    assert not [check for check in checks if check["status"] == "FAIL"]
    assert [check for check in checks if check["check"] == "raw_action_command"][0]["status"] == "WARN"
