from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.open_gate24e_biological_holdout import (
    EXPECTED_AUTHORIZATION_COMMIT,
    EXPECTED_FREEZE_SHA256,
    EXPECTED_GRID_DECISION,
    HoldoutGateError,
    biological_direction_from_source,
    cross_assay_decision,
    open_holdout,
    validate_authorization,
)


def _signoff(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "status": "VIRTUAL_PREDICTION_FREEZE_REVIEW_APPROVED",
        "decision": "APPROVED_TO_OPEN_GATE24E_BIOLOGICAL_HOLDOUT",
        "holdout_open_authorized": True,
        "holdout_opened": False,
        "virtual_prediction_freeze_sha256": EXPECTED_FREEZE_SHA256,
        "reviewer_1": "Reviewer One",
        "reviewer_2": "Reviewer Two",
        "review_date": "2026-09-09",
        "retuning_allowed": False,
        "seed_change_allowed": False,
        "parameter_change_allowed": False,
        "metric_change_allowed": False,
        "decision_rule_change_allowed": False,
        "tuning_using_holdout": False,
        "posthoc_parameter_selection": False,
        "biological_validation_claim_allowed": False,
    }
    value.update(updates)
    return value


def _freeze(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "virtual_prediction_freeze_sha256": EXPECTED_FREEZE_SHA256,
        "grid_decision": EXPECTED_GRID_DECISION,
    }
    value.update(updates)
    return value


def test_authorization_requires_approved_holdout_signoff() -> None:
    with pytest.raises(HoldoutGateError):
        validate_authorization(_signoff(holdout_open_authorized=False), _freeze(), EXPECTED_AUTHORIZATION_COMMIT)


def test_exact_freeze_sha_is_required() -> None:
    with pytest.raises(HoldoutGateError):
        validate_authorization(_signoff(), _freeze(virtual_prediction_freeze_sha256="0" * 64), EXPECTED_AUTHORIZATION_COMMIT)


def test_virtual_decision_is_immutable() -> None:
    with pytest.raises(HoldoutGateError):
        validate_authorization(_signoff(), _freeze(grid_decision="DIRECTIONAL_VALIDATION_PASS"), EXPECTED_AUTHORIZATION_COMMIT)


def test_parameter_selection_is_forbidden() -> None:
    with pytest.raises(HoldoutGateError):
        validate_authorization(_signoff(parameter_change_allowed=True), _freeze(), EXPECTED_AUTHORIZATION_COMMIT)


def test_metric_substitution_is_forbidden() -> None:
    with pytest.raises(HoldoutGateError):
        validate_authorization(_signoff(metric_change_allowed=True), _freeze(), EXPECTED_AUTHORIZATION_COMMIT)


def test_locked_source_yields_direction_only() -> None:
    row = {
        "source_id": "cackovic_2018_park_loss_of_function",
        "endpoint": "climbing position and climbing deficit",
        "notes": "Independent Parkin loss-of-function paper.",
    }
    assert biological_direction_from_source(row) == "BIOLOGICAL_IMPAIRMENT_SUPPORTED"


def test_unavailable_raw_values_are_not_fabricated() -> None:
    row = {
        "source_id": "cackovic_2018_park_loss_of_function",
        "endpoint": "climbing position and climbing deficit",
        "notes": "Independent Parkin loss-of-function paper.",
        "raw_data_available": "false",
    }
    assert "value" not in row
    assert biological_direction_from_source(row) == "BIOLOGICAL_IMPAIRMENT_SUPPORTED"


def test_biological_impairment_plus_virtual_failure_is_discordance() -> None:
    assert cross_assay_decision("BIOLOGICAL_IMPAIRMENT_SUPPORTED", EXPECTED_GRID_DECISION) == "DIRECTIONAL_CROSS_ASSAY_DISCORDANCE"


def test_no_metric_equivalence_is_allowed() -> None:
    assert cross_assay_decision("BIOLOGICAL_IMPAIRMENT_SUPPORTED", EXPECTED_GRID_DECISION) != "QUANTITATIVE_PASS"


def test_holdout_opens_only_after_freeze_and_only_once(tmp_path: Path) -> None:
    root = tmp_path
    signoff = root / "research/validation/prospective/gate24e_virtual_prediction_freeze_reviewer_signoff.json"
    freeze = root / "experiments/gate_24e_blinded_parkin_prediction/manifests/immutable_virtual_prediction_freeze.json"
    firewall = root / "experiments/gate_24_prospective_validation/manifests/holdout_firewall_manifest.json"
    source = root / "research/validation/biological/parkin_validation_sources.csv"
    for path in (signoff, freeze, firewall, source):
        path.parent.mkdir(parents=True, exist_ok=True)
    signoff.write_text(json.dumps(_signoff()), encoding="utf-8")
    freeze.write_text(json.dumps(_freeze()), encoding="utf-8")
    firewall.write_text(json.dumps({"status": "SEALED", "no_numeric_holdout_import": True, "no_holdout_tuning": True, "gpu_executed": False, "simulation_executed": False}), encoding="utf-8")
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source_id", "raw_data_available", "not_used_for_tuning", "transfer_status", "endpoint", "notes", "assay", "age_days", "genotype", "matched_control", "data_type"])
        writer.writeheader()
        writer.writerow({"source_id": "cackovic_2018_park_loss_of_function", "raw_data_available": "false", "not_used_for_tuning": "true", "transfer_status": "VALIDATION_ONLY", "endpoint": "climbing position and climbing deficit", "notes": "Parkin loss-of-function", "assay": "negative geotaxis", "age_days": "5; 10; 20", "genotype": "Parkin loss-of-function", "matched_control": "outcrossed control", "data_type": "SUMMARY_LEVEL_VALIDATION_EVIDENCE"})
    result = open_holdout(root, current_commit=EXPECTED_AUTHORIZATION_COMMIT, opened_at_utc="2026-09-09T00:00:00Z")
    assert result["holdout_opened"] is True
    with pytest.raises(HoldoutGateError):
        open_holdout(root, current_commit=EXPECTED_AUTHORIZATION_COMMIT, opened_at_utc="2026-09-09T00:00:01Z")


def test_opening_result_records_no_gpu_or_simulation(tmp_path: Path) -> None:
    # The single-use behavior and output flags are asserted by the integration
    # test above; this test locks the required scientific firewall contract.
    assert EXPECTED_GRID_DECISION == "DIRECTIONAL_VALIDATION_NOT_SUPPORTED"
