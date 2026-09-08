from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_biological_contract_rejects_synthetic_sources_and_calibration_reuse() -> None:
    contract = yaml.safe_load((ROOT / "research/validation/biological/parkin_biological_data_contract.yaml").read_text(encoding="utf-8"))
    assert set(contract["rejected_source_types"]) == {"SYNTHETIC", "GENERATED", "SIMULATION_AS_REAL"}
    assert contract["policy"]["used_for_calibration"] is False
    assert contract["policy"]["used_for_validation"] is True
    assert contract["policy"]["unit_of_analysis"] == "biological_replicate"
