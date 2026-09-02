import csv
from pathlib import Path

from scripts.audit_calibration_targets import _write_outputs, audit_targets


ROOT = Path(__file__).resolve().parents[1]


def test_current_targets_reflect_gate_09b_approval() -> None:
    audit = audit_targets(ROOT / "calibration_targets" / "targets.csv")
    assert audit["status"] == "READY_FOR_CALIBRATION"
    assert audit["counts"]["review_status"]["pending"] == 2
    assert audit["counts"]["review_status"]["approved"] == 2
    assert audit["counts"]["eligible_approved"] == 2
    assert audit["counts"]["allocation"] == {"calibration": 1, "holdout": 1}


def test_audit_writes_gate_09b_manifest(tmp_path: Path) -> None:
    audit = audit_targets(ROOT / "calibration_targets" / "targets.csv")
    _write_outputs(audit, tmp_path)
    manifest = (tmp_path / "calibration_manifest.json").read_text(encoding="utf-8")
    policy_report = (tmp_path / "target_policy_upgrade_report.md").read_text(encoding="utf-8")
    assert '"ready_for_calibration": true' in manifest
    assert '"calibration": [' in manifest
    assert '"holdout": [' in manifest
    assert "READY_FOR_CALIBRATION" in policy_report
    assert "Pokrzywa" in policy_report
    assert "Pozo" in policy_report


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
        "notes": "reviewer=lead;review_date=2026-08-28;allocation=calibration;assay_transfer=allowed;sample_unit=fly",
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
        {**common, "paper_id": "paper-a", "value": "1.0", "notes": "reviewer=lead;review_date=2026-08-28;allocation=calibration;assay_transfer=allowed;sample_unit=fly"},
        {**common, "paper_id": "paper-b", "value": "2.0", "notes": "reviewer=lead;review_date=2026-08-28;allocation=holdout;assay_transfer=allowed;sample_unit=fly"},
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
        "notes": "reviewer=lead;review_date=2026-08-28;allocation=calibration;assay_transfer=allowed;sample_unit=fly",
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
        "notes": "Paper reports median; reviewer=lead;review_date=2026-08-28;allocation=calibration;assay_transfer=allowed;sample_unit=fly",
    }
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)
    audit = audit_targets(path)
    assert audit["status"] == "WAITING_TARGET_DATA"
    assert any(item["code"] == "STATISTIC_MISMATCH" for item in audit["rows"][0]["issues"])


def _write_policy_targets(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "paper_id", "gene_model", "genotype", "age_days", "sex", "assay", "metric", "value",
        "unit", "variance_type", "variance", "sample_size", "figure_table", "doi_pmid",
        "review_status", "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _approved_policy_row(*, paper_id: str, allocation: str, metric: str, unit: str) -> dict[str, str]:
    return {
        "paper_id": paper_id,
        "gene_model": "model-a",
        "genotype": "genotype-a",
        "age_days": "5",
        "sex": "female",
        "assay": "assay-a",
        "metric": metric,
        "value": "1.0",
        "unit": unit,
        "variance_type": "sd",
        "variance": "0.1",
        "sample_size": "10",
        "figure_table": "Figure 1",
        "doi_pmid": f"doi:{paper_id}",
        "review_status": "approved",
        "notes": f"reviewer=lead;review_date=2026-08-30;allocation={allocation};assay_transfer=allowed;sample_unit=fly",
    }


def test_median_endpoint_requires_iqr_or_range(tmp_path: Path) -> None:
    path = tmp_path / "targets.csv"
    rows = [
        _approved_policy_row(
            paper_id="median-cal",
            allocation="calibration",
            metric="median_planar_speed_mm_s",
            unit="mm/s",
        ),
        _approved_policy_row(
            paper_id="median-hold",
            allocation="holdout",
            metric="median_planar_speed_mm_s",
            unit="mm/s",
        ),
    ]
    _write_policy_targets(path, rows)
    audit = audit_targets(path)
    assert audit["status"] == "WAITING_TARGET_DATA"
    assert all(
        any(item["code"] == "MEDIAN_SPREAD_REQUIRED" for item in row["issues"])
        for row in audit["rows"]
    )

    for row in rows:
        row["variance_type"] = "IQR"
    _write_policy_targets(path, rows)
    assert audit_targets(path)["status"] == "READY_FOR_CALIBRATION"


def test_distance_endpoint_is_separate_from_speed(tmp_path: Path) -> None:
    path = tmp_path / "targets.csv"
    rows = [
        _approved_policy_row(
            paper_id="distance-cal",
            allocation="calibration",
            metric="distance_traveled_mm",
            unit="mm",
        ),
        _approved_policy_row(
            paper_id="distance-hold",
            allocation="holdout",
            metric="distance_traveled_mm",
            unit="mm",
        ),
    ]
    for row in rows:
        row["notes"] += ";statistic=mean"
    _write_policy_targets(path, rows)
    audit = audit_targets(path)
    assert audit["status"] == "WAITING_TARGET_DATA"
    assert any(
        item["code"] == "DISTANCE_HOLDOUT_ONLY"
        for item in audit["rows"][0]["issues"]
    )
    assert audit["rows"][1]["eligible"]
    assert not any(
        item["code"] == "UNSUPPORTED_ENDPOINT"
        for audited in audit["rows"]
        for item in audited["issues"]
    )


def test_ci95_and_paper_reported_center_follow_gate_policy(tmp_path: Path) -> None:
    path = tmp_path / "targets.csv"
    fields = [
        "paper_id", "gene_model", "genotype", "age_days", "sex", "assay", "metric", "value",
        "unit", "variance_type", "variance", "sample_size", "figure_table", "doi_pmid",
        "review_status", "notes",
    ]
    rows = [
        {
            "paper_id": "chen", "gene_model": "human_alpha_synuclein", "genotype": "A30P",
            "age_days": "30", "sex": "male", "assay": "adult horizontal walking",
            "metric": "mean_planar_speed_mm_s", "value": "4.875", "unit": "mm/s",
            "variance_type": "CI95", "variance": "0.525", "sample_size": "20",
            "figure_table": "Figure 4f", "doi_pmid": "doi:chen", "review_status": "approved",
            "notes": "reviewer=lead;review_date=2026-09-02;allocation=calibration;assay_transfer=allowed;sample_unit=fly;statistic=mean",
        },
        {
            "paper_id": "pozo", "gene_model": "pink1", "genotype": "Pink1B9", "age_days": "28",
            "sex": "not_reported", "assay": "open field", "metric": "distance_traveled_mm",
            "value": "62.091", "unit": "mm", "variance_type": "IQR_with_min_max_ranges_reported",
            "variance": "61.288", "sample_size": "21", "figure_table": "Figure 3B",
            "doi_pmid": "doi:pozo", "review_status": "approved",
            "notes": "reviewer=lead;review_date=2026-09-02;allocation=holdout;assay_transfer=allowed;sample_unit=fly;statistic=paper_reported_center",
        },
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    audit = audit_targets(path)
    assert audit["status"] == "READY_FOR_CALIBRATION"
    assert all(row["eligible"] for row in audit["rows"])


def test_paper_reported_center_is_holdout_only(tmp_path: Path) -> None:
    path = tmp_path / "targets.csv"
    row = _approved_policy_row(
        paper_id="distance-cal", allocation="calibration", metric="distance_traveled_mm", unit="mm"
    )
    row["notes"] += ";statistic=paper_reported_center"
    _write_policy_targets(path, [row])
    audit = audit_targets(path)
    assert audit["status"] == "WAITING_TARGET_DATA"
    assert any(item["code"] == "PAPER_CENTER_HOLDOUT_ONLY" for item in audit["rows"][0]["issues"])


def test_climbing_and_dam_endpoints_remain_validation_only(tmp_path: Path) -> None:
    path = tmp_path / "targets.csv"
    rows = [
        _approved_policy_row(
            paper_id="climbing",
            allocation="calibration",
            metric="climbing_score",
            unit="score",
        ),
        _approved_policy_row(
            paper_id="dam",
            allocation="holdout",
            metric="DAM_activity",
            unit="count",
        ),
    ]
    _write_policy_targets(path, rows)
    audit = audit_targets(path)
    assert audit["status"] == "WAITING_TARGET_DATA"
    assert all(
        any(item["code"] == "VALIDATION_ONLY_ENDPOINT" for item in row["issues"])
        for row in audit["rows"]
    )


def test_approved_target_requires_assay_transfer_and_sample_unit(tmp_path: Path) -> None:
    path = tmp_path / "targets.csv"
    row = _approved_policy_row(
        paper_id="missing-policy-metadata",
        allocation="calibration",
        metric="mean_planar_speed_mm_s",
        unit="mm/s",
    )
    row["notes"] = "reviewer=lead;review_date=2026-08-30;allocation=calibration"
    _write_policy_targets(path, [row])
    audit = audit_targets(path)
    codes = {item["code"] for item in audit["rows"][0]["issues"]}
    assert "MISSING_ASSAY_TRANSFER" in codes
    assert "MISSING_SAMPLE_UNIT" in codes


def test_center_statistic_does_not_replace_uncertainty_type(tmp_path: Path) -> None:
    path = tmp_path / "targets.csv"
    row = _approved_policy_row(
        paper_id="mean-without-uncertainty-type",
        allocation="calibration",
        metric="mean_planar_speed_mm_s",
        unit="mm/s",
    )
    row["variance_type"] = "mean"
    _write_policy_targets(path, [row])
    audit = audit_targets(path)
    assert any(
        item["code"] == "MISSING_UNCERTAINTY_STATISTIC"
        for item in audit["rows"][0]["issues"]
    )


def test_candidate_staging_is_non_approved_and_policy_documented() -> None:
    policy = ROOT / "docs" / "target_approval_policy.md"
    staging = ROOT / "calibration_targets" / "candidate_targets_reviewed.csv"
    assert policy.is_file()
    assert "median_planar_speed_mm_s" in policy.read_text(encoding="utf-8")
    with staging.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 8
    assert all(None not in row for row in rows)
    assert not any(row["review_status"] == "approved" for row in rows)
    assert {row["review_status"] for row in rows} == {
        "pending",
        "validation_only",
        "not_comparable",
    }
