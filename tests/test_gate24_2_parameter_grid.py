import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
GRID = ROOT / "research/validation/prospective/parkin_checkpoint_grid_manifest.json"
FREEZE = ROOT / "research/validation/prospective/parkin_model_freeze.yaml"
CONTRACT = ROOT / "research/validation/prospective/parkin_prediction_contract.yaml"
SIGNOFF = ROOT / "research/validation/prospective/parkin_prediction_reviewer_signoff.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_gate24_2_locks_complete_grid_without_single_primary_parameter() -> None:
    grid = json.loads(GRID.read_text(encoding="utf-8"))
    freeze = yaml.safe_load(FREEZE.read_text(encoding="utf-8"))
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))

    assert grid["status"] == "GRID_MATERIALIZED"
    assert grid["parameter_policy"] == "PREREGISTERED_GRID_NO_SINGLE_BIOLOGICAL_PARAMETER"
    assert grid["disease_parameters"] == [0.25, 0.5, 0.75, 1.0]
    assert grid["target_count"] == 330
    assert [row["parameter"] for row in grid["checkpoints"]] == [0.25, 0.5, 0.75, 1.0]
    assert freeze["model_commit"] == grid["neural_implementation_commit"]
    assert freeze["parameter_grid"] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert freeze["parameter_policy"] == "PREREGISTERED_GRID_NO_SINGLE_BIOLOGICAL_PARAMETER"
    assert contract["parameter"]["primary_parameter_selected"] is False
    assert contract["parameter_policy"]["disease_parameters"] == [0.25, 0.5, 0.75, 1.0]


def test_gate24_2_grid_checkpoint_hashes_match_external_artifacts() -> None:
    grid = json.loads(GRID.read_text(encoding="utf-8"))
    healthy = (ROOT / grid["healthy_checkpoint"]["path"]).resolve()
    assert healthy.is_file()
    assert _sha256(healthy) == grid["healthy_checkpoint"]["sha256"]
    for row in grid["checkpoints"]:
        checkpoint = (ROOT / row["checkpoint_path"]).resolve()
        assert checkpoint.is_file(), row["checkpoint_path"]
        assert _sha256(checkpoint) == row["checkpoint_sha256"]
        assert row["identity_test_status"] == "PASS"


def test_gate24_2_reviewer_two_is_not_filled_automatically() -> None:
    signoff = json.loads(SIGNOFF.read_text(encoding="utf-8"))
    assert signoff["status"] == "WAITING_PROSPECTIVE_PREDICTION_REVIEW"
    assert signoff["decision"] == "PENDING_HUMAN_SIGNOFF"
    assert signoff["reviewer_2"] == ""
    assert signoff["holdout_opened"] is False
    assert signoff["tuning_using_holdout"] is False
