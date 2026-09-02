from __future__ import annotations

import math
from pathlib import Path
import csv
import json

import pytest

from scripts.run_calibrated_confirmation_rerun import (
    METRICS_FIELDS,
    SUMMARY_FIELDS,
    _ratio,
    _validate_locked_inputs,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments/gate_13c_calibrated_confirmation/configs/calibrated_confirmation_run_config.yaml"
OUTPUT = ROOT / "experiments/gate_13c_calibrated_confirmation"


def test_gate13c_config_locks_gate13b_selected_burden() -> None:
    import yaml

    plan = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    _, condition, locked, *_ = _validate_locked_inputs(plan)
    assert condition["condition_id"] == "alpha_synuclein"
    assert condition["gene_specific_mapping"] is False
    assert locked["locked"] is True
    assert math.isclose(float(locked["selected_value"]), 0.5)
    assert plan["confirmation_design"]["control_burden_level"] == 0.0
    assert plan["confirmation_design"]["calibrated_burden_level"] == 0.5


def test_gate13c_rejects_reselection() -> None:
    import yaml

    plan = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    plan["locked_parameter"]["selected_value"] = 0.25
    with pytest.raises(ValueError, match="requires the Gate 13B selected burden 0.5"):
        _validate_locked_inputs(plan)


def test_confirmation_ratio_uses_only_pass_rows() -> None:
    rows = [
        {"run_status": "PASS", "burden_level": 0.0, "mean_planar_speed_mm_s": 10.0},
        {"run_status": "FAILED", "burden_level": 0.0, "mean_planar_speed_mm_s": 999.0},
        {"run_status": "PASS", "burden_level": 0.5, "mean_planar_speed_mm_s": 5.0},
    ]
    assert _ratio(rows, 0.0) == 10.0
    assert _ratio(rows, 0.5) == 5.0
    assert _ratio(rows, 0.5) / _ratio(rows, 0.0) == 0.5


def test_gate13c_metric_contract_is_explicit() -> None:
    assert "mean_planar_speed_mm_s" in METRICS_FIELDS
    assert "distance_traveled_mm" in METRICS_FIELDS
    assert "displacement_mm" in METRICS_FIELDS
    assert "metric_contract_status" in METRICS_FIELDS
    assert "n_failed" in SUMMARY_FIELDS
    assert "operator_applied_count" in SUMMARY_FIELDS


def test_gate13c_generated_artifacts_are_present_and_scoped() -> None:
    metrics_path = OUTPUT / "results/calibrated_confirmation_metrics.csv"
    metrics_json_path = OUTPUT / "results/calibrated_confirmation_metrics.json"
    summary_path = OUTPUT / "results/calibrated_confirmation_summary.csv"
    manifest_path = OUTPUT / "manifests/calibrated_confirmation_manifest.json"
    report_path = ROOT / "docs/calibration/gate_13c_calibrated_confirmation_rerun_report.md"
    assert all(path.is_file() for path in (metrics_path, metrics_json_path, summary_path, manifest_path, report_path))
    rows = list(csv.DictReader(metrics_path.open(encoding="utf-8", newline="")))
    payload = json.loads(metrics_json_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(rows) == 12
    assert {row["condition_id"] for row in rows} == {"alpha_synuclein"}
    assert {float(row["burden_level"]) for row in rows} == {0.0, 0.5}
    assert all(row["run_status"] == "PASS" for row in rows)
    for row in rows:
        if row["run_status"] == "PASS":
            for field in ("mean_planar_speed_mm_s", "distance_traveled_mm", "displacement_mm"):
                assert math.isfinite(float(row[field]))
    assert payload["planned_runs"] == payload["successful_runs"] == 12
    assert manifest["status"] == "CHEN_CALIBRATED_CONFIRMATION_PASS"
    assert manifest["no_parameter_reselection"] is True
    assert manifest["no_holdout_validation_run"] is True
    assert manifest["no_gene_specific_mapping"] is True
    assert manifest["biological_validation_claim"] is False
    assert manifest["chen_ratio_target"] == 0.6701030927835051
    assert manifest["gate13b_selected_ratio"] == 0.5856211861021032
    assert payload["locked_parameter"]["selected_value"] == 0.5
    assert payload["no_ci95_to_se"] is True
