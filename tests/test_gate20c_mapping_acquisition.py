import csv
import hashlib
import json
from pathlib import Path

from scripts.import_gate20c_mapping_signoff import _is_identifier, _metadata_errors


ROOT = Path(__file__).resolve().parents[1]
MANUAL_ROOT = ROOT / "research/disease_mapping/manual_imports"
PACKAGE_ROOT = ROOT / "experiments/gate_20c_mapping_acquisition"
SUMMARY_PATH = PACKAGE_ROOT / "results/gate20c_mapping_acquisition_summary.json"
MANIFEST_PATH = PACKAGE_ROOT / "manifests/gate20c_mapping_acquisition_manifest.json"
REPORT_PATH = ROOT / "docs/disease_mapping/gate_20c_mapping_acquisition_report.md"
CONDITIONS = {"alpha_synuclein", "pink1", "parkin", "dj1", "lrrk2"}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_gate20c_package_and_manual_import_slots_exist() -> None:
    assert REPORT_PATH.is_file()
    assert SUMMARY_PATH.is_file()
    assert MANIFEST_PATH.is_file()
    for condition in CONDITIONS:
        directory = MANUAL_ROOT / condition
        assert directory.is_dir()
        assert (directory / "README.md").is_file()


def test_gate20c_keeps_valid_zero_approval_state_without_human_signoff() -> None:
    summary = _json(SUMMARY_PATH)
    assert summary["schema_version"] == "gate-20c-mapping-acquisition-summary-v1"
    assert summary["status"] == "MAPPING_ACQUISITION_BLOCKED"
    assert summary["approved_condition_count"] == 0
    assert summary["reviewed_condition_count"] == 5
    assert summary["all_five_conditions_approved"] is False
    assert summary["disease_mapping_status"] == "DISEASE_MAPPING_BLOCKED"
    assert summary["no_new_simulation_run"] is True
    assert summary["no_calibration_run"] is True
    assert summary["no_tuning_run"] is True
    assert summary["no_root_id_inference"] is True
    assert summary["data_fabricated"] is False


def test_gate20c_each_condition_has_no_approved_mapping_without_import() -> None:
    summary = _json(SUMMARY_PATH)
    assert set(summary["condition_statuses"]) == CONDITIONS
    for condition, result in summary["condition_statuses"].items():
        assert result["condition_id"] == condition
        assert result["approved_condition"] is False
        assert result["no_identifier_inference"] is True
        if condition == "parkin":
            assert result["mapping_identifier_count"] == 330
            assert result["root_id_count"] == 330
            assert result["manual_import_files"]
            assert result["signoff_file"]
            assert result["status"] == "BLOCKED_SIGNOFF_NOT_APPROVED"
            assert result["decision"] == "PENDING_HUMAN_SIGNOFF"
        else:
            assert result["mapping_identifier_count"] == 0
            assert result["manual_import_files"] == []


def test_gate20c_manifest_hashes_and_boundaries() -> None:
    manifest = _json(MANIFEST_PATH)
    assert manifest["status"] == "MAPPING_ACQUISITION_BLOCKED"
    assert manifest["large_external_dumps_committed"] is False
    assert manifest["no_new_simulation_run"] is True
    assert manifest["no_calibration_run"] is True
    assert manifest["no_tuning_run"] is True
    assert manifest["no_raw_metric_modification"] is True
    assert manifest["no_root_id_inference"] is True
    assert manifest["data_fabricated"] is False
    for relative, expected in manifest["source_inputs_sha256"].items():
        path = ROOT / relative
        assert path.is_file(), relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected


def test_gate20c_report_does_not_overclaim() -> None:
    text = REPORT_PATH.read_text(encoding="utf-8").lower()
    assert "approved condition: `0/5`" in text
    assert "không" in text
    assert "không suy ra root id" in text
    assert "không chạy gpu" in text
    assert "không chạy" in text


def test_gate20c_condition_table_has_five_blocked_rows() -> None:
    table = PACKAGE_ROOT / "results/condition_mapping_acquisition.csv"
    with table.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 5
    assert {row["condition_id"] for row in rows} == CONDITIONS
    assert all(row["approved_condition"].lower() == "false" for row in rows)


def test_gate20d_parkin_export_contains_real_class_level_ids_only() -> None:
    path = MANUAL_ROOT / "parkin/codex_export.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 330
    assert all(row["condition_id"] == "parkin" for row in rows)
    assert all(row["root_id"] and row["cell_class"] == "DAN" for row in rows)
    assert all(not row["edge_id"] for row in rows)
    assert all(row["source_sha256"] and len(row["source_sha256"]) == 64 for row in rows)
    assert all("not a Parkin gene-specific mapping" in row["notes"] for row in rows)


def test_gate20d_pending_signoff_cannot_be_promoted() -> None:
    signoff = _json(MANUAL_ROOT / "parkin/reviewer_signoff.json")
    assert signoff["decision"] == "PENDING_HUMAN_SIGNOFF"
    assert signoff["reviewer_2"] == ""
    assert signoff["review_date"] == ""
    assert signoff["gene_specific_mapping"] is False


def test_gate20c_rejects_placeholder_and_incomplete_mapping_evidence() -> None:
    assert _is_identifier("TODO_ROOT_ID") is False
    assert _is_identifier("NOT_CELL_SPECIFIC") is False
    row = {
        "condition_id": "parkin",
        "root_id": "123456789",
        "edge_id": "",
        "cell_type": "dopaminergic neuron",
        "cell_class": "TH-GAL4 scope",
        "driver_scope": "TH-GAL4",
        "anatomy_scope": "brain",
        "connectome_name": "FlyWire",
        "connectome_version": "v783",
        "source_url": "https://example.org/source",
        "query_string": "driver_scope=TH-GAL4",
        "query_date": "2026-09-07",
        "exported_by": "reviewer",
        "notes": "manual review",
    }
    errors = _metadata_errors("parkin", [row])
    assert any("source_sha256" in error for error in errors)
