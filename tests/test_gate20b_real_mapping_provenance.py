import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = ROOT / "research/disease_mapping/exports"
PACKAGE_ROOT = ROOT / "experiments/gate_20b_real_mapping_provenance"
SUMMARY_PATH = PACKAGE_ROOT / "results/gate20b_mapping_summary.json"
MANIFEST_PATH = PACKAGE_ROOT / "manifests/gate20b_mapping_manifest.json"
REPORT_PATH = ROOT / "docs/disease_mapping/gate_20b_real_mapping_provenance_report.md"
CONDITIONS = {"alpha_synuclein", "pink1", "parkin", "dj1", "lrrk2"}
FORBIDDEN_POSITIVE_CLAIMS = (
    "biologically validated",
    "clinically validated",
    "drug efficacy",
    "therapeutic efficacy",
    "proves parkinson",
    "gene-specific validation achieved",
    "quantitatively validated",
    "disease mechanism validated",
)
PLACEHOLDER_IDS = ("TODO_ROOT_ID", "FAKE_ROOT_ID", "SYNTHETIC_ROOT", "000000", "TBD_ROOT", "MOCK_ROOT")


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_gate20b_package_files_exist_for_all_conditions() -> None:
    assert REPORT_PATH.is_file()
    assert SUMMARY_PATH.is_file()
    assert MANIFEST_PATH.is_file()
    assert {path.name for path in EXPORT_ROOT.iterdir() if path.is_dir()} >= CONDITIONS
    for condition in CONDITIONS:
        directory = EXPORT_ROOT / condition
        assert (directory / "mapping_export.csv").is_file()
        assert (directory / "mapping_review.json").is_file()
        assert (directory / "source_manifest.json").is_file()


def test_gate20b_summary_is_blocked_without_condition_mapping() -> None:
    summary = _json(SUMMARY_PATH)
    assert summary["status"] == "MAPPING_REVIEW_BLOCKED_WITH_PROVENANCE_GAP"
    assert summary["disease_mapping_status"] == "DISEASE_MAPPING_BLOCKED"
    assert summary["reviewed_condition_count"] == 5
    assert summary["approved_condition_count"] == 0
    assert set(summary["condition_statuses"]) == CONDITIONS
    assert summary["no_new_simulation_run"] is True
    assert summary["no_calibration_run"] is True
    assert summary["no_tuning_run"] is True
    assert summary["no_raw_metric_modification"] is True
    assert summary["no_root_id_inference"] is True
    assert summary["data_fabricated"] is False


def test_gate20b_exports_have_conservative_identifier_contract() -> None:
    for condition in CONDITIONS:
        directory = EXPORT_ROOT / condition
        with (directory / "mapping_export.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 1
        row = rows[0]
        assert row["condition_id"] == condition
        assert not row["root_id"]
        assert not row["edge_id"]
        assert row["gene_specific_mapping"].lower() == "false"
        assert row["decision"] != "APPROVED"

        review = _json(directory / "mapping_review.json")
        source = _json(directory / "source_manifest.json")
        assert review["mapping_identifier_count"] == 0
        assert review["decision"] != "APPROVED"
        assert review["human_signoff"] == "PENDING_HUMAN_SIGNOFF"
        assert source["export_sha256"] == hashlib.sha256((directory / "mapping_export.csv").read_bytes()).hexdigest()
        assert source["source_sha256"]
        assert source["source_urls"]
        if source["query_string"].startswith("NOT_EXECUTED"):
            assert not source["query_date"]


def test_gate20b_review_dates_are_real_iso_dates() -> None:
    for condition in CONDITIONS:
        review = _json(EXPORT_ROOT / condition / "mapping_review.json")
        assert review["reviewer_2"] == "Tuan Le"
        datetime.strptime(review["review_date"], "%Y-%m-%d")


def test_gate20b_manifest_hashes_and_scientific_boundaries() -> None:
    manifest = _json(MANIFEST_PATH)
    assert manifest["status"] == "MAPPING_REVIEW_BLOCKED_WITH_PROVENANCE_GAP"
    assert manifest["disease_mapping_status"] == "DISEASE_MAPPING_BLOCKED"
    assert manifest["large_artifacts_committed"] is False
    for relative, expected in manifest["sha256"].items():
        path = ROOT / relative
        assert path.is_file(), relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected

    text = "\n".join(
        [
            REPORT_PATH.read_text(encoding="utf-8"),
            SUMMARY_PATH.read_text(encoding="utf-8"),
            MANIFEST_PATH.read_text(encoding="utf-8"),
        ]
    ).lower()
    assert not any(claim in text for claim in FORBIDDEN_POSITIVE_CLAIMS)
    assert not any(placeholder.lower() in text for placeholder in PLACEHOLDER_IDS)


def test_gate20b_condition_specific_boundaries_are_explicit() -> None:
    summary = _json(SUMMARY_PATH)
    assert summary["condition_statuses"]["alpha_synuclein"]["gene_specific_mapping"] is False
    assert summary["condition_statuses"]["pink1"]["gene_specific_mapping"] is False
    assert summary["condition_statuses"]["parkin"]["rollout_scope"] == "CLASS_LEVEL_EXPLORATORY_ONLY"
    assert summary["condition_statuses"]["dj1"]["decision"] == "NOT_MAPPABLE_FROM_PAPER"
    assert summary["condition_statuses"]["lrrk2"]["decision"] == "WAITING_VNC_CONNECTOME_MAPPING"
