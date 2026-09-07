"""Regression tests for the Gate 23 Pozo holdout verification package."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.verify_gate23_pozo_holdout_validation import (
    DEFAULT_CONFIG,
    DEFAULT_OUTPUT,
    _summarize,
    _verify_config,
    _verify_sources,
)

ROOT = Path(__file__).resolve().parents[1]


def _config() -> dict:
    return yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))


def test_gate23_locks_pozo_as_distance_holdout() -> None:
    config = _config()
    _verify_config(config)
    assert config["holdout"]["metric"] == "distance_traveled_mm"
    assert config["holdout"]["not_speed_target"] is True
    assert config["holdout"]["allocation"] == "holdout"
    assert config["locked_calibration"]["selected_value"] == 0.5


def test_gate23_accepts_only_locked_gate14b_artifacts() -> None:
    config = _config()
    summary, manifest, confirmation, metrics, _ = _verify_sources(config)
    assert summary["execution_status"] == "POZO_HOLDOUT_RUNTIME_PASS"
    assert manifest["successful_runs"] == 12
    assert confirmation["status"] == "CHEN_CALIBRATED_CONFIRMATION_PASS"
    assert len(metrics) == 12


def test_gate23_reports_directional_concordance_but_quantitative_mismatch() -> None:
    config = _config()
    summary, _, _, metrics, _ = _verify_sources(config)
    result = _summarize(summary, metrics)
    assert result["status"] == "POZO_HOLDOUT_MISMATCH"
    assert result["runtime_status"] == "PASS"
    assert result["holdout_interpretation"] == "MISMATCH"
    assert result["directionality_pass"] is True
    assert result["quantitative_ratio_match"] is False
    assert result["simulated_distance_ratio"] == 0.9470070897697126
    assert result["pozo_target_ratio"] == 0.19203837612811836


def test_gate23_generated_manifest_if_present_preserves_boundaries() -> None:
    path = DEFAULT_OUTPUT / "gate23_pozo_holdout_manifest.json"
    if not path.is_file():
        return
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["no_pozo_tuning"] is True
    assert document["no_new_simulation_run"] is True
    assert document["biological_validation_claim"] is False
