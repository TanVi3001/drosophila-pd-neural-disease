from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
import yaml

from scripts.prepare_pozo_holdout_protocol import (
    BLOCKED,
    CONFIG,
    MANIFEST,
    READY,
    REPORT,
    REVIEW_REQUIRED,
    SUMMARY,
    _status_for_checks,
)


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/gate_14a_pozo_holdout_protocol"


def test_gate14a_protocol_artifacts_exist() -> None:
    assert all((ROOT / path).is_file() for path in (CONFIG, SUMMARY, MANIFEST, REPORT))


def test_gate14a_locks_pozo_distance_as_holdout_only() -> None:
    config = yaml.safe_load((ROOT / CONFIG).read_text(encoding="utf-8"))
    summary = list(csv.DictReader((ROOT / SUMMARY).open(encoding="utf-8", newline="")))
    manifest = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))

    assert config["pozo_target"]["metric"] == "distance_traveled_mm"
    assert config["pozo_target"]["not_speed_target"] is True
    assert config["pozo_target"]["allocation"] == "holdout"
    assert config["locked_calibration"]["selected_value"] == 0.5
    assert summary[0]["metric"] == "distance_traveled_mm"
    assert summary[0]["allocation"] == "holdout"
    assert manifest["pozo_target"]["not_speed_target"] is True


def test_gate14a_forbids_simulation_calibration_and_holdout() -> None:
    manifest = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))
    assert manifest["no_simulation_run"] is True
    assert manifest["no_calibration_run"] is True
    assert manifest["no_holdout_validation_run"] is True
    assert manifest["no_pozo_tuning"] is True
    assert manifest["no_parameter_reselection"] is True
    assert manifest["no_distance_to_speed_conversion"] is True
    assert manifest["no_spread_to_se_conversion"] is True
    assert manifest["no_gene_specific_mapping"] is True
    assert manifest["no_biological_validation_claim"] is True


def test_gate14a_ready_requires_matched_control_provenance() -> None:
    assert _status_for_checks(
        pozo_target_valid=True,
        locked_parameter_valid=True,
        gate13c_valid=True,
        pink1_config_valid=True,
        control_provenance_valid=True,
    ) == READY
    assert _status_for_checks(
        pozo_target_valid=True,
        locked_parameter_valid=True,
        gate13c_valid=True,
        pink1_config_valid=True,
        control_provenance_valid=False,
    ) == REVIEW_REQUIRED


def test_gate14a_blocks_when_required_upstream_input_is_invalid() -> None:
    assert _status_for_checks(
        pozo_target_valid=False,
        locked_parameter_valid=True,
        gate13c_valid=True,
        pink1_config_valid=True,
        control_provenance_valid=True,
    ) == BLOCKED
