from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_prospective_prediction_is_not_locked_before_mapping() -> None:
    contract = yaml.safe_load((ROOT / "research/validation/prospective/parkin_prediction_contract.yaml").read_text(encoding="utf-8"))
    assert contract["status"] == "WAITING_GENE_SPECIFIC_MAPPING"
    assert contract["holdout_opened"] is False
    assert contract["calibration_data_reused"] is False
    assert contract["success_threshold"] == "NOT_LOCKED"
