from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_prospective_prediction_is_drafted_but_not_human_locked() -> None:
    contract = yaml.safe_load((ROOT / "research/validation/prospective/parkin_prediction_contract.yaml").read_text(encoding="utf-8"))
    assert contract["status"] == "PROSPECTIVE_PREDICTION_DRAFTED"
    assert contract["primary_validation_axis"] == "LOCOMOTOR_IMPAIRMENT_DIRECTION"
    assert contract["expected_direction"] == "VIRTUAL_PARKIN_IMPAIRED_RELATIVE_TO_VIRTUAL_CONTROL"
    assert contract["holdout_opened"] is False
    assert contract["calibration_data_reused"] is False
    assert contract["tuning_using_holdout"] is False
    assert contract["quantitative_cross_assay_threshold"] == "NOT_APPLICABLE_ASSAY_MISMATCH"
