from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/gate_18_movement_verified_rollout"
CONFIG = GATE / "configs/movement_verified_healthy_10s.yaml"
SUMMARY = GATE / "results/movement_verified_summary.json"
SUMMARY_CSV = GATE / "results/movement_verified_summary.csv"
MANIFEST = GATE / "manifests/movement_verified_rollout_manifest.json"
REPORT = ROOT / "docs/movement/gate_18_movement_verified_rollout_report.md"


def test_gate18_control_files_exist() -> None:
    for path in (CONFIG, SUMMARY, SUMMARY_CSV, MANIFEST, REPORT):
        assert path.is_file(), path
        assert path.stat().st_size > 0, path
    assert "camera_mode: tracking" in CONFIG.read_text(encoding="utf-8")


def test_gate18_summary_records_real_movement_and_boundary() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["status"] == "MOVEMENT_VERIFIED_ARTIFACT_PARTIAL"
    assert summary["simulation"] == {
        "completed": True,
        "condition": "healthy",
        "seed": 0,
        "steps": 100000,
        "frame_count": 100001,
        "timestep_s": 0.0001,
        "duration_s": 9.999999999990033,
        "device": "cuda",
        "stimulus": "p9",
        "cpg_frequency_hz": 12.0,
    }
    locomotion = summary["locomotion"]
    assert locomotion["thorax_planar_displacement_mm"] > 0
    assert locomotion["total_distance_mm"] > 0
    assert locomotion["walking_speed_mm_s"] > 0
    assert locomotion["joint_position_max_change"] > 0
    assert locomotion["actuator_max_change"] > 0
    assert summary["quality_gate"]["timestamp_monotonic"] == "PASS"
    assert summary["quality_gate"]["finite_rollout_arrays"] == "PASS"
    assert summary["quality_gate"]["ground_contact_present"] == "PASS"
    assert summary["quality_gate"]["observation_array"] == "NOT_VERIFIED_NOT_RECORDED"
    assert summary["scientific_boundary"]["biological_parkinson_validation"] is False
    assert summary["scientific_boundary"]["clinical_validation"] is False


def test_gate18_manifest_keeps_binary_artifacts_out_of_git() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["status"] == "MOVEMENT_VERIFIED_ARTIFACT_PARTIAL"
    assert manifest["large_artifacts_committed"] is False
    assert manifest["artifacts"]["viewer_bundle"] == "NOT_COMPLETED_VALIDATOR_INTERRUPTED"
    assert "rollout.json" in manifest["artifacts"]["historical_fixed_camera_run_deleted_after_storage_failure"]
    assert manifest["artifacts"]["video"]["visual_qa"] == "PASS_TRACKING_CENTERED"
    assert manifest["artifacts"]["video"]["camera_mode"] == "tracking"
    assert manifest["scientific_boundary"]["biological_parkinson_validation"] is False


def test_gate18_csv_has_movement_and_storage_disclosures() -> None:
    rows = {
        row["metric"]: row
        for row in csv.DictReader(SUMMARY_CSV.open(encoding="utf-8", newline=""))
    }
    assert float(rows["thorax_planar_displacement"]["value"]) > 0
    assert float(rows["walking_speed"]["value"]) > 0
    assert rows["timestamp_dt_min"]["evidence_status"] == "PASS"
    assert rows["observation_array"]["evidence_status"] == "NOT_VERIFIED"
    assert rows["video_visual_tracking"]["evidence_status"] == "PASS"
