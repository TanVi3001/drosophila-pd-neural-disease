import csv
import json
from pathlib import Path

from scripts.evaluate_calibration_holdout import evaluate


def _write_targets(path: Path, *, approved: bool = True) -> None:
    fields = [
        "paper_id", "gene_model", "genotype", "age_days", "sex", "assay", "metric", "value",
        "unit", "variance_type", "variance", "sample_size", "figure_table", "doi_pmid",
        "review_status", "notes",
    ]
    status = "approved" if approved else "pending"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for paper, value, allocation in (("cal", "1.0", "calibration"), ("hold", "2.0", "holdout")):
            writer.writerow({
                "paper_id": paper, "gene_model": "model", "genotype": "genotype", "age_days": "5",
                "sex": "female", "assay": "assay", "metric": "mean_planar_speed_mm_s", "value": value,
                "unit": "mm/s", "variance_type": "sd", "variance": "0.1", "sample_size": "10",
                "figure_table": "Figure 1", "doi_pmid": paper, "review_status": status,
                "notes": f"reviewer=lead;review_date=2026-08-28;allocation={allocation};assay_transfer=allowed;sample_unit=fly",
            })


def test_evaluation_waits_without_approved_targets(tmp_path: Path) -> None:
    targets = tmp_path / "targets.csv"
    _write_targets(targets, approved=False)
    metrics = tmp_path / "metrics.json"
    metrics.write_text(json.dumps({"scalar_metrics": {"mean_planar_speed_mm_s": 1.5}}), encoding="utf-8")
    assert evaluate(metrics, targets, tmp_path / "output") == "WAITING_TARGET_DATA"
    payload = json.loads((tmp_path / "output" / "evaluation.json").read_text(encoding="utf-8"))
    assert payload["status"] == "WAITING_TARGET_DATA"


def test_evaluation_keeps_calibration_and_holdout_separate(tmp_path: Path) -> None:
    targets = tmp_path / "targets.csv"
    _write_targets(targets)
    metrics = tmp_path / "metrics.json"
    metrics.write_text(json.dumps({"scalar_metrics": {"mean_planar_speed_mm_s": 1.5}}), encoding="utf-8")
    output = tmp_path / "output"
    assert evaluate(metrics, targets, output) == "PASS"
    payload = json.loads((output / "evaluation.json").read_text(encoding="utf-8"))
    assert payload["results"]["calibration"]["target_metrics"] == {"mean_planar_speed_mm_s": 1.0}
    assert payload["results"]["holdout"]["target_metrics"] == {"mean_planar_speed_mm_s": 2.0}


def test_evaluation_rejects_missing_target_metric(tmp_path: Path) -> None:
    targets = tmp_path / "targets.csv"
    _write_targets(targets)
    metrics = tmp_path / "metrics.json"
    metrics.write_text(json.dumps({"scalar_metrics": {"mean_planar_speed_mm_s": 1.5}}), encoding="utf-8")
    output = tmp_path / "output"
    assert evaluate(metrics, targets, output) == "PASS"

    # Add a second approved endpoint to each split; partial overlap must not pass.
    rows = list(csv.DictReader(targets.open(encoding="utf-8", newline="")))
    extra_rows = []
    for row in rows:
        extra = dict(row)
        extra["paper_id"] += "-distance"
        extra["metric"] = "distance_traveled_mm"
        extra["unit"] = "mm"
        extra["value"] = "2.0"
        extra["notes"] += ";statistic=mean"
        extra_rows.append(extra)
    with targets.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows + extra_rows)
    assert evaluate(metrics, targets, output) == "INSUFFICIENT_METRICS"


def test_evaluation_rejects_nonfinite_observed_metric(tmp_path: Path) -> None:
    targets = tmp_path / "targets.csv"
    _write_targets(targets)
    metrics = tmp_path / "metrics.json"
    metrics.write_text(json.dumps({"scalar_metrics": {"mean_planar_speed_mm_s": "NaN"}}), encoding="utf-8")
    assert evaluate(metrics, targets, tmp_path / "output") == "INSUFFICIENT_METRICS"
