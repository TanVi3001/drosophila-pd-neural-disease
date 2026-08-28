import pytest

from drosophila_pd_neural.calibration import compute_loss, require_targets


def test_compute_loss_returns_all_declared_measures() -> None:
    result = compute_loss({"speed": 2.0, "pause": 0.5}, {"speed": 1.0, "pause": 0.0})
    assert result["metric_count"] == 2
    assert result["rmse"] > 0
    assert result["mae"] > 0
    assert 0 <= result["cosine"] <= 1
    assert result["huber"] > 0


def test_empty_targets_are_a_gate() -> None:
    with pytest.raises(RuntimeError, match="WAITING_TARGET_DATA"):
        require_targets([])
