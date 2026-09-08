from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research/validation/prospective/parkin_assay_compatibility.yaml"


def _config() -> dict:
    return yaml.safe_load(PATH.read_text(encoding="utf-8"))


def test_gate24_assay_lock_is_direction_only() -> None:
    config = _config()
    assert config["status"] == "ASSAY_COMPATIBILITY_LOCKED_DIRECTION_ONLY"
    assert config["quantitative_cross_assay_validation"]["allowed"] is False
    assert config["real_training_context"]["transfer_to_virtual"]["status"] == "NOT_QUANTITATIVELY_EQUIVALENT"
    assert config["heldout_context"]["transfer_to_virtual"]["status"] == "DIRECTIONAL_CROSS_ASSAY_ONLY"


def test_gate24_dam_and_climbing_are_not_speed() -> None:
    config = _config()
    real_endpoint = config["real_training_context"]["endpoint"]
    heldout_endpoint = config["heldout_context"]["endpoint"]
    assert "beam-break" in real_endpoint
    assert "climbing" in heldout_endpoint
    assert "planar_speed" not in real_endpoint
    assert "planar_speed" not in heldout_endpoint


def test_gate24_virtual_metrics_keep_their_own_units() -> None:
    metrics = yaml.safe_load(PATH.read_text(encoding="utf-8"))["virtual_assay"]["metrics"]
    assert "median_planar_speed_mm_s" in metrics
    assert "distance_traveled_mm" in metrics
