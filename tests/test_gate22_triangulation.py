from pathlib import Path

from scripts.analyze_pd_validation_triangulation import triangulate


def test_triangulation_has_no_ratio_without_track_b_data(tmp_path: Path) -> None:
    result = triangulate(track_a=tmp_path / "missing-a.json", track_b=tmp_path / "missing-b.json", output=tmp_path / "triangulation.json")
    assert result["status"] == "WAITING_TRACK_B_DATA"
    assert result["real_effect_ratio"] == "NOT_AVAILABLE"
    assert result["virtual_effect_ratio"] == "NOT_AVAILABLE"
    assert result["data_fabricated"] is False
