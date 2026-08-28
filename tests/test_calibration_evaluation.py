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
                "sex": "female", "assay": "assay", "metric": "speed", "value": value,
                "unit": "mm/s", "variance_type": "sd", "variance": "0.1", "sample_size": "10",
                "figure_table": "Figure 1", "doi_pmid": paper, "review_status": status,
                "notes": f"reviewer=lead;review_date=2026-08-28;allocation={allocation}",
            })


def test_evaluation_waits_without_approved_targets(tmp_path: Path) -> None:
    targets = tmp_path / "targets.csv"
    _write_targets(targets, approved=False)
    metrics = tmp_path / "metrics.json"
    metrics.write_text(json.dumps({"scalar_metrics": {"speed": 1.5}}), encoding="utf-8")
    assert evaluate(metrics, targets, tmp_path / "output") == "WAITING_TARGET_DATA"
    payload = json.loads((tmp_path / "output" / "evaluation.json").read_text(encoding="utf-8"))
    assert payload["status"] == "WAITING_TARGET_DATA"


def test_evaluation_keeps_calibration_and_holdout_separate(tmp_path: Path) -> None:
    targets = tmp_path / "targets.csv"
    _write_targets(targets)
    metrics = tmp_path / "metrics.json"
    metrics.write_text(json.dumps({"scalar_metrics": {"speed": 1.5}}), encoding="utf-8")
    output = tmp_path / "output"
    assert evaluate(metrics, targets, output) == "PASS"
    payload = json.loads((output / "evaluation.json").read_text(encoding="utf-8"))
    assert payload["results"]["calibration"]["target_metrics"] == {"speed": 1.0}
    assert payload["results"]["holdout"]["target_metrics"] == {"speed": 2.0}


def test_evaluation_rejects_missing_target_metric(tmp_path: Path) -> None:
    targets = tmp_path / "targets.csv"
    _write_targets(targets)
    metrics = tmp_path / "metrics.json"
    metrics.write_text(json.dumps({"scalar_metrics": {"speed": 1.5}}), encoding="utf-8")
    output = tmp_path / "output"
    assert evaluate(metrics, targets, output) == "PASS"

    # Add a second approved target to each split; partial overlap must not pass.
    rows = list(csv.DictReader(targets.open(encoding="utf-8", newline="")))
    for row in rows:
        row["paper_id"] += "-extra"
        row["metric"] = "pause_fraction"
        row["value"] = "0.2"
    with targets.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    assert evaluate(metrics, targets, output) == "INSUFFICIENT_METRICS"


def test_evaluation_rejects_nonfinite_observed_metric(tmp_path: Path) -> None:
    targets = tmp_path / "targets.csv"
    _write_targets(targets)
    metrics = tmp_path / "metrics.json"
    metrics.write_text(json.dumps({"scalar_metrics": {"speed": "NaN"}}), encoding="utf-8")
    assert evaluate(metrics, targets, tmp_path / "output") == "INSUFFICIENT_METRICS"
