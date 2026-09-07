"""Regression tests for the analysis-only Gate 22 comparison."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.run_gate22_parkin_healthy_comparison import (
    DEFAULT_CONFIG,
    DEFAULT_OUTPUT,
    _compare,
    _read_csv,
    _validate_config,
)

ROOT = Path(__file__).resolve().parents[1]
HEALTHY = ROOT / "experiments/gate_11_healthy_baseline/results/healthy_baseline_metrics.csv"
PARKIN = ROOT / "experiments/gate_21_parkin_class_level_rollout/manifests/gate21_execution_metrics.csv"


def _config() -> dict:
    return yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))


def test_gate22_config_is_analysis_only() -> None:
    config = _config()
    assert _validate_config(config) == []
    assert config["gene_specific_mapping"] is False
    assert config["analysis"]["calibration"] is False
    assert config["analysis"]["holdout_validation"] is False
    assert config["healthy_seeds_used"] == [0, 1, 2, 3, 4]


def test_gate22_matches_seed_and_burden_grid() -> None:
    rows, summary = _compare(healthy_rows=_read_csv(HEALTHY), parkin_rows=_read_csv(PARKIN), config=_config())
    assert summary["status"] == "PARKIN_HEALTHY_COMPARISON_PASS"
    assert summary["planned_pair_count"] == 25
    assert summary["observed_pair_count"] == 25
    assert summary["passed_comparison_rows"] == len(rows)
    assert len(rows) == 55
    assert {row["n_pairs"] for row in rows} == {5}


def test_gate22_control_burden_has_zero_primary_delta() -> None:
    rows, _ = _compare(healthy_rows=_read_csv(HEALTHY), parkin_rows=_read_csv(PARKIN), config=_config())
    control = [row for row in rows if row["burden_level"] == 0.0 and row["metric"] in _config()["primary_metrics"]]
    assert len(control) == 3
    assert all(abs(float(row["mean_delta_proxy_minus_healthy"])) < 1e-12 for row in control)


def test_gate22_keeps_non_biological_scope_in_generated_manifest_if_present() -> None:
    manifest = DEFAULT_OUTPUT / "gate22_comparison_manifest.json"
    if not manifest.is_file():
        return
    document = json.loads(manifest.read_text(encoding="utf-8"))
    assert document["gene_specific_mapping"] is False
    assert document["calibration_run"] is False
    assert document["holdout_validation_run"] is False
    assert document["gpu_run"] is False
