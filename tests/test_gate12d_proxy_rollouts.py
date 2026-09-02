from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/gate_12d_proxy_rollouts"
CONFIG = GATE / "configs/proxy_rollout_run_config.yaml"
METRICS = GATE / "results/proxy_disease_metrics.csv"
METRICS_JSON = GATE / "results/proxy_disease_metrics.json"
MANIFEST = GATE / "manifests/proxy_disease_rollout_manifest.json"
REPORT = ROOT / "docs/disease_rollouts/gate_12d_proxy_disease_rollout_report.md"


def test_gate12d_config_declares_the_60_run_proxy_matrix() -> None:
    document = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert document["schema_version"] == "gate-12d-proxy-rollout-run-config-v1"
    assert document["seeds"]["values"] == [0, 1, 2, 3, 4, 5]
    assert [item["condition_id"] for item in document["conditions_to_run"]] == [
        "alpha_synuclein",
        "pink1",
    ]
    assert all(item["burden_levels"] == [0.0, 0.25, 0.5, 0.75, 1.0] for item in document["conditions_to_run"])
    assert sum(len(item["burden_levels"]) * len(document["seeds"]["values"]) for item in document["conditions_to_run"]) == 60
    assert document["forbidden"]["calibration"] is True
    assert document["forbidden"]["holdout_validation"] is True


def test_gate12d_outputs_preserve_blocked_or_real_run_contract() -> None:
    assert METRICS.is_file()
    assert METRICS_JSON.is_file()
    assert MANIFEST.is_file()
    rows = list(csv.DictReader(METRICS.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 60
    assert {row["condition_id"] for row in rows} == {"alpha_synuclein", "pink1"}
    assert {row["burden_level"] for row in rows} == {"0.0", "0.25", "0.5", "0.75", "1.0"}
    for row in rows:
        assert row["scope"] == "organism_level_proxy"
        assert row["gene_specific_mapping"] == "False"
        if row["run_status"] == "PASS":
            for metric in ("mean_planar_speed_mm_s", "distance_traveled_mm", "displacement_mm"):
                assert math.isfinite(float(row[metric]))
            assert row["metric_contract_status"] == "PASS"
        else:
            assert row["skip_reason"].strip()
            for metric in ("mean_planar_speed_mm_s", "distance_traveled_mm", "displacement_mm"):
                assert not row[metric].strip()
        assert "distance_to_speed" not in row


def test_gate12d_manifest_keeps_scope_and_forbids_downstream_fitting() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["planned_runs"] == {"total": 60, "alpha_synuclein": 30, "pink1": 30}
    assert manifest["conditions_run"] == ["alpha_synuclein", "pink1"]
    assert manifest["conditions_skipped"] == ["parkin", "dj1", "lrrk2"]
    assert manifest["no_calibration_run"] is True
    assert manifest["no_holdout_validation_run"] is True
    assert manifest["no_gene_specific_mapping"] is True
    assert manifest["large_artifacts_committed"] is False
    assert "not biological validation" in manifest["scientific_boundary"]
    payload = json.loads(METRICS_JSON.read_text(encoding="utf-8"))
    assert payload["simulation_data_fabricated"] is False
    assert payload["no_calibration_run"] is True
    assert payload["no_holdout_validation_run"] is True
    assert all("calibration" not in path.name.lower() for path in GATE.rglob("*"))
    assert all("holdout" not in path.name.lower() for path in GATE.rglob("*"))


def test_gate12d_report_records_boundary_and_blocked_conditions() -> None:
    report = REPORT.read_text(encoding="utf-8")
    assert "PROXY_DISEASE_ROLLOUTS_" in report
    assert "organism_level_proxy" in report
    assert "parkin" in report and "dj1" in report and "lrrk2" in report
    assert "Không calibration" in report
    assert "không biological validation" in report
