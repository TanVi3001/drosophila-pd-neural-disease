from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/gate_12g_integrated_proxy_rollouts"
CONFIG = GATE / "configs/integrated_proxy_rollout_config.yaml"
RESULTS = GATE / "results"
METRICS = RESULTS / "integrated_proxy_disease_metrics.csv"
METRICS_JSON = RESULTS / "integrated_proxy_disease_metrics.json"
SUMMARY = RESULTS / "integrated_proxy_disease_summary.csv"
MANIFEST = GATE / "manifests/integrated_proxy_rollout_manifest.json"
REPORT = ROOT / "docs/disease_rollouts/gate_12g_integrated_proxy_rollout_report.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_gate12g_config_declares_the_real_60_run_matrix() -> None:
    document = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert document["schema_version"] == "gate-12g-integrated-proxy-rollout-config-v1"
    assert document["runtime"]["step_count"] == 5000
    assert document["runtime"]["timestep_s"] == 0.0001
    assert document["seeds"]["values"] == [0, 1, 2, 3, 4, 5]
    assert [item["condition_id"] for item in document["conditions_to_run"]] == [
        "alpha_synuclein",
        "pink1",
    ]
    assert all(
        item["burden_levels"] == [0.0, 0.25, 0.5, 0.75, 1.0]
        for item in document["conditions_to_run"]
    )
    assert sum(
        len(item["burden_levels"]) * len(document["seeds"]["values"])
        for item in document["conditions_to_run"]
    ) == 60
    assert document["operator"]["apply_to"] == "joint_angles"
    assert document["operator"]["modifies_adhesion_onoff"] is False
    assert document["forbidden"]["calibration"] is True
    assert document["forbidden"]["holdout_validation"] is True


def test_gate12g_artifacts_are_real_or_truthfully_blocked() -> None:
    assert METRICS.is_file()
    assert METRICS_JSON.is_file()
    assert SUMMARY.is_file()
    assert MANIFEST.is_file()
    assert REPORT.is_file()

    rows = list(csv.DictReader(METRICS.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 60
    assert {row["condition_id"] for row in rows} == {"alpha_synuclein", "pink1"}
    assert {row["burden_level"] for row in rows} == {"0.0", "0.25", "0.5", "0.75", "1.0"}
    required = ("mean_planar_speed_mm_s", "distance_traveled_mm", "displacement_mm")
    for row in rows:
        assert row["scope"] == "organism_level_proxy"
        assert row["gene_specific_mapping"] == "False"
        if row["run_status"] == "PASS":
            for metric in required:
                assert math.isfinite(float(row[metric]))
            assert row["metric_contract_status"] == "PASS"
            assert row["operator_applied"] == "True"
            assert row["adhesion_onoff_unchanged"] == "PASS"
            if float(row["burden_level"]) == 0.0:
                assert row["burden_zero_identity_pass"] == "PASS"
            else:
                assert row["action_changed_for_positive_burden"] == "True"
        else:
            assert row["skip_reason"].strip()
            for metric in required:
                assert not row[metric].strip()


def test_gate12g_manifest_has_provenance_and_forbids_downstream_fitting() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["planned_runs"] == {
        "total": 60,
        "alpha_synuclein": 30,
        "pink1": 30,
    }
    assert manifest["conditions_run"] == ["alpha_synuclein", "pink1"]
    assert manifest["conditions_skipped"] == ["parkin", "dj1", "lrrk2"]
    assert manifest["no_calibration_run"] is True
    assert manifest["no_holdout_validation_run"] is True
    assert manifest["no_gene_specific_mapping"] is True
    assert manifest["no_biological_validation_claim"] is True
    assert manifest["large_artifacts_committed"] is False
    assert manifest["metrics_csv_sha256"] == _sha256(METRICS)
    assert manifest["metrics_json_sha256"] == _sha256(METRICS_JSON)
    assert manifest["summary_csv_sha256"] == _sha256(SUMMARY)

    payload = json.loads(METRICS_JSON.read_text(encoding="utf-8"))
    assert payload["simulation_data_fabricated"] is False
    assert payload["no_calibration_run"] is True
    assert payload["no_holdout_validation_run"] is True
    report = REPORT.read_text(encoding="utf-8")
    assert "organism-level computational proxy" in report
    assert "không phải biological parkinson validation" in report.lower()
