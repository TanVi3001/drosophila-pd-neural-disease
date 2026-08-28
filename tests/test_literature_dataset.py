import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "datasets"


def _csv_rows(relative_path: str) -> list[dict[str, str]]:
    with (DATASETS / relative_path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_dataset_manifest_hashes_tracked_sources() -> None:
    manifest = json.loads(
        (DATASETS / "dataset_manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["status"] == "CANDIDATE_REVIEW_REQUIRED"
    assert manifest["records"]["approved_calibration_targets"] == 0
    for record in manifest["files"]:
        path = DATASETS / record["path"]
        assert path.is_file(), record["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]


def test_source_report_is_preserved_but_not_promoted_to_dataset() -> None:
    manifest = json.loads(
        (DATASETS / "source_intake/manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["classification"] == "SOURCE_REPORT_NOT_DATASET"
    assert manifest["review_status"] == "AUDITED_NOT_AUTHORITATIVE"
    report = DATASETS / "source_intake/DATASET_SOURCES_DETAILED_REPORT.md"
    assert report.stat().st_size == manifest["size_bytes"]
    assert hashlib.sha256(report.read_bytes()).hexdigest() == manifest["sha256"]


def test_phenotype_records_have_primary_provenance_and_remain_pending() -> None:
    papers = {row["paper_id"]: row for row in _csv_rows("literature_phenotypes/paper_registry.csv")}
    records = _csv_rows("literature_phenotypes/phenotype_records.csv")

    assert len(papers) == 6
    assert len(records) == 14
    assert not any(row["review_status"] == "approved" for row in records)
    for record in records:
        paper = papers[record["paper_id"]]
        assert paper["doi"]
        assert paper["pmid"]
        assert record["source_url"] == paper["source_url"]
        assert record["figure_table"]
        assert record["sample_size"]


def test_extracted_numeric_values_keep_assay_and_unit_boundaries() -> None:
    records = {
        row["record_id"]: row
        for row in _csv_rows("literature_phenotypes/phenotype_records.csv")
    }

    assert records["pokrzywa_alpha_speed_day1"]["value"] == "5.6"
    assert records["pokrzywa_alpha_speed_day21"]["value"] == "2.5"
    assert records["pokrzywa_control_speed_day1"]["value"] == "6.0"
    assert records["pokrzywa_control_speed_day21"]["value"] == "5.0"
    assert records["pokrzywa_alpha_speed_day21"]["unit"] == "mm/s"

    parkin = records["dumitrescu_parkin_activity_day45"]
    assert parkin["value"] == "85"
    assert parkin["unit"] == "percent_vs_age_matched_control"
    assert parkin["calibration_compatibility"] == "NOT_DIRECTLY_COMPARABLE_DAM_COUNTS"

    pink1 = records["pozo_pink1_distance_day28"]
    assert pink1["value"] == "62.091"
    assert pink1["unit"] == "mm"
    assert records["pozo_control_distance_day28"]["value"] == "323.326"


def test_figure_only_records_do_not_contain_invented_values() -> None:
    records = {
        row["record_id"]: row
        for row in _csv_rows("literature_phenotypes/phenotype_records.csv")
    }

    for record_id in (
        "hwang_dj1_climbing_day5",
        "godena_lrrk2_r1441c_climbing",
        "godena_lrrk2_y1699c_climbing",
    ):
        record = records[record_id]
        assert record["value"] == ""
        assert record["review_status"] == "waiting_manual_figure_review"
        assert record["calibration_compatibility"] == "WAITING_NUMERIC_EXTRACTION"


def test_gene_conditions_are_not_claimed_as_reviewed_root_id_mappings() -> None:
    mappings = _csv_rows("literature_phenotypes/gene_condition_mapping.csv")

    gene_specific = [row for row in mappings if row["condition_id"] != "dopamine_deficiency_exploratory"]
    assert gene_specific
    assert all(row["usable_now"] == "no" for row in gene_specific)
    assert all("WAITING" in row["neural_mapping_status"] for row in gene_specific)


def test_second_review_audit_covers_every_candidate_without_auto_approval() -> None:
    records = _csv_rows("literature_phenotypes/phenotype_records.csv")
    audit = _csv_rows("literature_phenotypes/second_review_audit.csv")

    assert {row["record_id"] for row in audit} == {
        row["record_id"] for row in records
    }
    assert all(row["decision"] == "PENDING_HUMAN_SIGNOFF" for row in audit)
    assert all(row["reviewer_2"] == "NOT_ASSIGNED" for row in audit)
    assert all(row["review_date"] == "2026-08-28" for row in audit)
    assert all(row["uncertainty_status"] for row in audit)
    assert all(row["assay_transfer_status"] for row in audit)
    assert all(row["root_id_mapping_status"] for row in audit)


def test_root_id_mapping_audit_does_not_infer_gene_specific_ids() -> None:
    mappings = _csv_rows("literature_phenotypes/root_id_mapping_audit.csv")

    assert len(mappings) == 6
    assert mappings[0]["root_id_status"] == "CLASS_LEVEL_EXPLORATORY_ONLY"
    assert all(row["reviewer_2"] == "PENDING" for row in mappings)
    assert all(row["review_date"] == "2026-08-28" for row in mappings)
    assert all(
        row["mapping_decision"] != "APPROVED_GENE_SPECIFIC"
        for row in mappings
    )
    assert all(row["root_id_source"] for row in mappings)


def test_second_pass_source_register_covers_all_papers() -> None:
    papers = {
        row["paper_id"]
        for row in _csv_rows("literature_phenotypes/paper_registry.csv")
    }
    sources = _csv_rows("source_intake/second_pass_sources.csv")

    assert {row["paper_id"] for row in sources} == papers
    assert all(row["primary_source_status"].startswith("VERIFIED_") for row in sources)
    assert all(row["review_boundary"] for row in sources)


def test_automated_paper_analysis_covers_all_records_without_approval() -> None:
    records = _csv_rows("literature_phenotypes/phenotype_records.csv")
    analysis = _csv_rows("../research/paper_review/paper_analysis_vi.csv")

    assert {row["record_id"] for row in analysis} == {
        row["record_id"] for row in records
    }
    assert len(analysis) == 14
    assert all(row["reviewer_2"] == "NOT_ASSIGNED" for row in analysis)
    assert all(row["decision"] == "PENDING_HUMAN_SIGNOFF" for row in analysis)
    assert all(row["review_date"] == "2026-08-28" for row in analysis)
    assert all(row["analysis_vi"] and row["notes_vi"] for row in analysis)


def test_paper_review_manifest_covers_six_sources_and_preserves_pdf_boundaries() -> None:
    manifest = _csv_rows("../research/paper_review/paper_pdf_manifest.csv")
    information = json.loads(
        (ROOT / "research/paper_review/paper_information.json")
        .read_text(encoding="utf-8")
    )

    assert len(manifest) == 6
    assert {row["paper_id"] for row in manifest} == {
        paper["paper_id"] for paper in information["papers"]
    }
    downloaded = [row for row in manifest if row["status"].startswith("DOWNLOADED_")]
    unavailable = [row for row in manifest if row["status"].startswith("PDF_NOT_")]
    assert len(downloaded) == 5
    assert len(unavailable) == 1
    assert all(len(row["sha256"]) == 64 for row in downloaded)
    assert all(row["filename"] for row in downloaded)
    assert unavailable[0]["paper_id"] == "dumitrescu_2023_parkin_rnai"
