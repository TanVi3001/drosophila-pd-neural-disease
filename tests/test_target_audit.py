import csv
from pathlib import Path

from scripts.audit_calibration_targets import _write_outputs, audit_targets


ROOT = Path(__file__).resolve().parents[1]


def test_current_targets_wait_for_manual_approval() -> None:
    audit = audit_targets(ROOT / "calibration_targets" / "targets.csv")
    assert audit["status"] == "WAITING_TARGET_DATA"
    assert audit["counts"]["review_status"]["pending"] == 2
    assert audit["counts"]["eligible_approved"] == 0


def test_audit_writes_empty_manifest_until_review_is_complete(tmp_path: Path) -> None:
    audit = audit_targets(ROOT / "calibration_targets" / "targets.csv")
    _write_outputs(audit, tmp_path)
    manifest = (tmp_path / "calibration_manifest.json").read_text(encoding="utf-8")
    assert '"ready_for_calibration": false' in manifest
    assert '"calibration": []' in manifest
    assert '"holdout": []' in manifest


def test_missing_target_file_is_explicit_waiting_state(tmp_path: Path) -> None:
    audit = audit_targets(tmp_path / "missing.csv")
    assert audit["status"] == "WAITING_TARGET_DATA"
    assert "Khong tim thay target file" in audit["blockers"][0]


def test_approved_targets_need_explicit_review_and_allocation(tmp_path: Path) -> None:
    path = tmp_path / "targets.csv"
    fields = [
        "paper_id", "gene_model", "genotype", "age_days", "sex", "assay", "metric", "value",
        "unit", "variance_type", "variance", "sample_size", "figure_table", "doi_pmid",
        "review_status", "notes",
    ]
    row = {
        "paper_id": "paper-a", "gene_model": "model-a", "genotype": "genotype-a", "age_days": "5",
        "sex": "female", "assay": "assay-a", "metric": "mean_planar_speed_mm_s", "value": "1.0",
        "unit": "mm/s", "variance_type": "sd", "variance": "0.1", "sample_size": "10",
        "figure_table": "Figure 1", "doi_pmid": "doi:a", "review_status": "approved",
        "notes": "reviewer=lead;review_date=2026-08-28;allocation=calibration",
    }
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)
    audit = audit_targets(path)
    assert audit["status"] == "WAITING_TARGET_DATA"
    assert audit["counts"]["eligible_approved"] == 1
    assert audit["counts"]["allocation"]["calibration"] == 1
    assert audit["counts"]["allocation"]["holdout"] == 0
    assert any("holdout" in blocker for blocker in audit["blockers"])


def test_calibration_and_holdout_approvals_unlock_readiness(tmp_path: Path) -> None:
    path = tmp_path / "targets.csv"
    fields = [
        "paper_id", "gene_model", "genotype", "age_days", "sex", "assay", "metric", "value",
        "unit", "variance_type", "variance", "sample_size", "figure_table", "doi_pmid",
        "review_status", "notes",
    ]
    common = {
        "gene_model": "model-a", "genotype": "genotype-a", "age_days": "5", "sex": "female",
        "assay": "assay-a", "metric": "mean_planar_speed_mm_s", "unit": "mm/s",
        "variance_type": "sd", "variance": "0.1", "sample_size": "10", "figure_table": "Figure 1",
        "doi_pmid": "doi:a", "review_status": "approved",
    }
    rows = [
        {**common, "paper_id": "paper-a", "value": "1.0", "notes": "reviewer=lead;review_date=2026-08-28;allocation=calibration"},
        {**common, "paper_id": "paper-b", "value": "2.0", "notes": "reviewer=lead;review_date=2026-08-28;allocation=holdout"},
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    audit = audit_targets(path)
    assert audit["status"] == "READY_FOR_CALIBRATION"
    assert audit["counts"]["eligible_approved"] == 2


def test_duplicate_targets_are_not_eligible(tmp_path: Path) -> None:
    source = (ROOT / "calibration_targets" / "targets.csv").read_text(encoding="utf-8")
    path = tmp_path / "targets.csv"
    path.write_text(source + source.split("\n", 1)[1], encoding="utf-8")
    audit = audit_targets(path)
    assert audit["status"] == "WAITING_TARGET_DATA"
    assert any("DUPLICATE_TARGET" in item["code"] for row in audit["rows"] for item in row["issues"])


def test_approved_target_rejects_non_numeric_metadata(tmp_path: Path) -> None:
    path = tmp_path / "targets.csv"
    fields = [
        "paper_id", "gene_model", "genotype", "age_days", "sex", "assay", "metric", "value",
        "unit", "variance_type", "variance", "sample_size", "figure_table", "doi_pmid",
        "review_status", "notes",
    ]
    row = {
        "paper_id": "paper-a", "gene_model": "model-a", "genotype": "genotype-a", "age_days": "5",
        "sex": "female", "assay": "assay-a", "metric": "mean_planar_speed_mm_s", "value": "1.0",
        "unit": "mm/s", "variance_type": "sd", "variance": "not reported", "sample_size": "13",
        "figure_table": "Figure 1", "doi_pmid": "doi:a", "review_status": "approved",
        "notes": "reviewer=lead;review_date=2026-08-28;allocation=calibration",
    }
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)
    audit = audit_targets(path)
    assert audit["status"] == "WAITING_TARGET_DATA"
    codes = {item["code"] for item in audit["rows"][0]["issues"]}
    assert "INVALID_VARIANCE" in codes


def test_approved_median_cannot_be_silently_used_as_mean(tmp_path: Path) -> None:
    path = tmp_path / "targets.csv"
    fields = [
        "paper_id", "gene_model", "genotype", "age_days", "sex", "assay", "metric", "value",
        "unit", "variance_type", "variance", "sample_size", "figure_table", "doi_pmid",
        "review_status", "notes",
    ]
    row = {
        "paper_id": "paper-a", "gene_model": "model-a", "genotype": "genotype-a", "age_days": "5",
        "sex": "female", "assay": "assay-a", "metric": "mean_planar_speed_mm_s", "value": "1.0",
        "unit": "mm/s", "variance_type": "sd", "variance": "0.1", "sample_size": "13",
        "figure_table": "Figure 1", "doi_pmid": "doi:a", "review_status": "approved",
        "notes": "Paper reports median; reviewer=lead;review_date=2026-08-28;allocation=calibration",
    }
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)
    audit = audit_targets(path)
    assert audit["status"] == "WAITING_TARGET_DATA"
    assert any(item["code"] == "STATISTIC_MISMATCH" for item in audit["rows"][0]["issues"])
