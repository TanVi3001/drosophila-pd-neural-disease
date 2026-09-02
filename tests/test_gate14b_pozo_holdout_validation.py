from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import yaml

from scripts.run_pozo_holdout_validation import (
    CONFIG,
    MANIFEST,
    METRICS_CSV,
    METRICS_JSON,
    PLANNED_RUNS,
    REPORT,
    RESULT_SUMMARY,
    SUMMARY_CSV,
    RUNTIME_BLOCKED,
    RUNTIME_PARTIAL,
    RUNTIME_PASS,
    SCIENTIFIC_CONCORDANCE_REPORTED,
    SCIENTIFIC_NOT_CONCORDANT,
    SCIENTIFIC_REVIEW,
)


ROOT = Path(__file__).resolve().parents[1]


def test_gate14b_artifacts_exist() -> None:
    paths = (CONFIG, METRICS_CSV, METRICS_JSON, SUMMARY_CSV, RESULT_SUMMARY, MANIFEST, REPORT)
    assert all((ROOT / path).is_file() for path in paths)


def test_gate14b_config_locks_pozo_holdout_contract() -> None:
    config = yaml.safe_load((ROOT / CONFIG).read_text(encoding="utf-8"))
    assert config["holdout_scope"]["condition_id"] == "pink1"
    assert config["holdout_scope"]["proxy_scope"] == "organism_level_proxy"
    assert config["holdout_scope"]["gene_specific_mapping"] is False
    assert config["locked_parameter"]["selected_value"] == 0.5
    assert config["locked_parameter"]["no_parameter_reselection"] is True
    assert config["locked_parameter"]["no_pozo_tuning"] is True
    assert config["pozo_target"]["primary_metric"] == "distance_traveled_mm"
    assert config["pozo_target"]["not_speed_target"] is True
    assert config["pozo_target"]["target_ratio"] == 0.19203837612811836


def test_gate14b_rows_are_only_locked_conditions_and_burdens() -> None:
    rows = list(csv.DictReader((ROOT / METRICS_CSV).open(encoding="utf-8", newline="")))
    assert len(rows) == PLANNED_RUNS
    assert {row["condition_id"] for row in rows} == {"pink1"}
    assert {float(row["burden_level"]) for row in rows} == {0.0, 0.5}
    assert all(row["condition_id"] != "alpha_synuclein" for row in rows)
    for row in rows:
        assert row["metric_contract_status"] in {"", "PASS"}
        if row["run_status"] == "PASS":
            for field in ("distance_traveled_mm", "mean_planar_speed_mm_s", "displacement_mm"):
                assert math.isfinite(float(row[field]))
        if row["run_status"] == "PASS" and float(row["burden_level"]) == 0.5:
            assert row["operator_applied"] == "true"


def test_gate14b_summary_has_control_and_holdout_rows() -> None:
    rows = list(csv.DictReader((ROOT / SUMMARY_CSV).open(encoding="utf-8", newline="")))
    assert len(rows) == 2
    assert {float(row["burden_level"]) for row in rows} == {0.0, 0.5}
    assert {row["condition_id"] for row in rows} == {"pink1"}


def test_gate14b_boundary_flags_are_true() -> None:
    manifest = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))
    result = json.loads((ROOT / RESULT_SUMMARY).read_text(encoding="utf-8"))
    for payload in (manifest, result):
        assert payload["no_parameter_reselection"] is True
        assert payload["no_pozo_tuning"] is True
        assert payload["no_calibration_run"] is True
        assert payload["no_distance_to_speed_conversion"] is True
        assert payload["no_spread_to_se_conversion"] is True
        assert payload["no_biological_validation_claim"] is True
    assert manifest["no_gene_specific_mapping"] is True
    assert result["gene_specific_mapping"] is False
    assert result["biological_validation_claim"] is False


def test_gate14b_result_status_is_conservative() -> None:
    result = json.loads((ROOT / RESULT_SUMMARY).read_text(encoding="utf-8"))
    assert result["execution_status"] in {RUNTIME_BLOCKED, RUNTIME_PARTIAL, RUNTIME_PASS}
    assert result["scientific_status"] in {
        SCIENTIFIC_REVIEW,
        SCIENTIFIC_NOT_CONCORDANT,
        SCIENTIFIC_CONCORDANCE_REPORTED,
    }
    if result["execution_status"] == RUNTIME_PASS:
        assert result["planned_runs"] == PLANNED_RUNS
        assert result["successful_runs"] == PLANNED_RUNS
        assert math.isfinite(float(result["simulated_distance_ratio"]))
