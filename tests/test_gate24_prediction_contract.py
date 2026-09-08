from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "research/validation/prospective/parkin_prediction_contract.yaml"
SIGNOFF = ROOT / "research/validation/prospective/parkin_prediction_reviewer_signoff.json"


def _contract() -> dict:
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


def test_gate24_contract_is_preregistered_without_holdout_access() -> None:
    contract = _contract()
    assert contract["status"] == "PROSPECTIVE_PREDICTION_DRAFTED"
    assert contract["primary_validation_axis"] == "LOCOMOTOR_IMPAIRMENT_DIRECTION"
    assert contract["expected_direction"] == "VIRTUAL_PARKIN_IMPAIRED_RELATIVE_TO_VIRTUAL_CONTROL"
    assert contract["holdout_opened"] is False
    assert contract["calibration_data_reused"] is False
    assert contract["tuning_using_holdout"] is False
    assert contract["seed_list"] == [0, 1, 2, 3, 4]


def test_gate24_burden_grid_is_sensitivity_not_biological_percentage() -> None:
    parameter = _contract()["parameter"]
    assert parameter["values"] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert parameter["biological_percentage_mapping"] == "NOT_ALLOWED"


def test_gate24_signoff_records_two_human_reviewers_before_execution() -> None:
    import json

    signoff = json.loads(SIGNOFF.read_text(encoding="utf-8"))
    assert signoff["status"] == "PROSPECTIVE_PREDICTION_LOCKED"
    assert signoff["decision"] == "APPROVED_FOR_BLINDED_VIRTUAL_PREDICTION"
    assert signoff["reviewer_1"] == "Tuan Le"
    assert signoff["reviewer_2"] == "To Dang Minh Tuan"
    assert signoff["review_date"] == "2026-09-08"
    assert signoff["holdout_opened"] is False
