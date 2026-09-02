import csv
from pathlib import Path

from scripts.compare_literature_targets import compare


ROOT = Path(__file__).resolve().parents[1]


def test_gate_09b_targets_include_approved_and_pending_rows() -> None:
    path = ROOT / "calibration_targets" / "targets.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    assert {row["review_status"] for row in rows} == {"approved", "pending"}
    assert {row["unit"] for row in rows} == {"mm/s", "mm"}
    assert all(row["doi_pmid"] for row in rows)
    approved = [row for row in rows if row["review_status"] == "approved"]
    assert {row["paper_id"] for row in approved} == {
        "chen_2014_adult_walking",
        "pozo_2022_pink1_serotonin",
    }


def test_approved_targets_require_all_metrics_for_comparison(tmp_path: Path) -> None:
    metrics = tmp_path / "metrics.json"
    metrics.write_text('{"scalar_metrics": {"mean_planar_speed_mm_s": 4.8}}\n', encoding="utf-8")
    status = compare(
        metrics,
        ROOT / "calibration_targets" / "targets.csv",
        tmp_path / "comparison",
    )
    assert status == "INSUFFICIENT_METRICS"


def test_comparison_rejects_partial_or_nonfinite_observations(tmp_path: Path) -> None:
    targets = tmp_path / "targets.csv"
    source = (ROOT / "calibration_targets" / "targets.csv").read_text(encoding="utf-8")
    fields = source.splitlines()[0]
    row = "paper,model,g,5,female,assay,speed,1.0,mm/s,sd,0.1,10,Figure 1,doi,approved,reviewer=lead;review_date=2026-08-28;allocation=calibration"
    targets.write_text(fields + "\n" + row + "\n", encoding="utf-8")
    metrics = tmp_path / "metrics.json"
    metrics.write_text('{"scalar_metrics": {"other": 1.0}}', encoding="utf-8")
    assert compare(metrics, targets, tmp_path / "partial") == "INSUFFICIENT_METRICS"
    metrics.write_text('{"scalar_metrics": {"speed": NaN}}'.replace("NaN", '"NaN"'), encoding="utf-8")
    assert compare(metrics, targets, tmp_path / "nonfinite") == "INSUFFICIENT_METRICS"
