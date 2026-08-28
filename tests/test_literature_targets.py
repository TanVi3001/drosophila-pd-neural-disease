import csv
from pathlib import Path

from scripts.compare_literature_targets import compare


ROOT = Path(__file__).resolve().parents[1]


def test_imported_targets_remain_pending_until_manual_approval() -> None:
    path = ROOT / "calibration_targets" / "targets.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert {row["review_status"] for row in rows} == {"pending"}
    assert {row["unit"] for row in rows} == {"mm/s"}
    assert all(row["doi_pmid"] for row in rows)


def test_pending_targets_keep_comparison_at_waiting_gate(tmp_path: Path) -> None:
    metrics = tmp_path / "metrics.json"
    metrics.write_text('{"scalar_metrics": {"mean_planar_speed_mm_s": 4.8}}\n', encoding="utf-8")
    status = compare(
        metrics,
        ROOT / "calibration_targets" / "targets.csv",
        tmp_path / "comparison",
    )
    assert status == "WAITING_TARGET_DATA"
