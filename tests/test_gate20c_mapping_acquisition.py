import csv
import hashlib
import json
from pathlib import Path

import yaml

from scripts.import_gate20c_mapping_signoff import (
    _config_errors,
    _is_identifier,
    _metadata_errors,
)


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


def test_gate20e_promotes_only_signed_off_parkin_class_mapping() -> None:
    summary = _json(SUMMARY_PATH)
    assert summary["schema_version"] == "gate-20c-mapping-acquisition-summary-v1"
    assert summary["status"] == "MAPPING_ACQUISITION_READY"
    assert summary["approved_condition_count"] == 1
    assert summary["reviewed_condition_count"] == 5
    assert summary["all_five_conditions_approved"] is False
    assert summary["disease_mapping_status"] == "READY_FOR_STEP_06"
    assert summary["no_new_simulation_run"] is True
    assert summary["no_calibration_run"] is True
    assert summary["no_tuning_run"] is True
    assert summary["no_root_id_inference"] is True
    assert summary["data_fabricated"] is False


def test_gate20e_condition_statuses_preserve_class_level_boundary() -> None:
    summary = _json(SUMMARY_PATH)
    assert set(summary["condition_statuses"]) == CONDITIONS
    for condition, result in summary["condition_statuses"].items():
        assert result["condition_id"] == condition
        assert result["no_identifier_inference"] is True
        if condition == "parkin":
            assert result["mapping_identifier_count"] == 330
            assert result["root_id_count"] == 330
            assert result["manual_import_files"]
            assert result["signoff_file"]
            assert result["gene_specific_mapping"] is False
            assert result["mapping_level"] == "DRIVER_OR_CLASS_LEVEL"
            assert result["allowed_rollout_scope"] == "CLASS_LEVEL_EXPLORATORY_ONLY"
            assert result["decision"] == "APPROVED_FOR_CLASS_LEVEL_EXPLORATORY"
            assert result["reviewer_2"] == "To Dang Minh Tuan"
            assert result["review_date"] == "2026-09-07"
            assert result["approved_condition"] is True
            assert result["config_ready"] is True
        else:
            assert result["approved_condition"] is False
            assert result["mapping_identifier_count"] == 0
            assert result["manual_import_files"] == []


def test_gate20c_manifest_hashes_and_boundaries() -> None:
    manifest = _json(MANIFEST_PATH)
    assert manifest["status"] == "MAPPING_ACQUISITION_READY"
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
    assert "approved condition: `1/5`" in text
    assert "class-level exploratory" in text
    assert "not a parkin gene-specific map" in text
    assert "không" in text
    assert "không suy ra root id" in text
    assert "không chạy gpu" in text
    assert "không chạy" in text


def test_gate20e_condition_table_has_one_approved_class_level_row() -> None:
    table = PACKAGE_ROOT / "results/condition_mapping_acquisition.csv"
    with table.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 5
    assert {row["condition_id"] for row in rows} == CONDITIONS
    approved = [row for row in rows if row["approved_condition"].lower() == "true"]
    assert [row["condition_id"] for row in approved] == ["parkin"]
    assert sum(row["approved_condition"].lower() == "true" for row in rows) == 1


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


def test_gate20e_config_materializes_only_manual_parkin_ids() -> None:
    config = yaml.safe_load(
        (ROOT / "configs/conditions/parkin.template.yaml").read_text(encoding="utf-8")
    )
    export_rows = list(
        csv.DictReader(
            (MANUAL_ROOT / "parkin/codex_export.csv").open(
                encoding="utf-8-sig", newline=""
            )
        )
    )
    export_ids = {row["root_id"] for row in export_rows}
    config_ids = {item["root_id"] for item in config["target_neurons"]}

    assert len(config["target_neurons"]) == 330
    assert config_ids == export_ids
    assert config["gene_specific_mapping"] is False
    assert config["mapping_level"] == "DRIVER_OR_CLASS_LEVEL"
    assert config["allowed_rollout_scope"] == "CLASS_LEVEL_EXPLORATORY_ONLY"
    assert _config_errors("parkin", sorted(export_ids), []) == []
    assert any(
        "target trong YAML" in error
        for error in _config_errors("parkin", ["not-an-imported-id"], [])
    )


def test_gate20e_parkin_class_level_signoff_is_explicit() -> None:
    signoff = _json(MANUAL_ROOT / "parkin/reviewer_signoff.json")

    assert signoff["decision"] == "APPROVED_FOR_CLASS_LEVEL_EXPLORATORY"
    assert signoff["mapping_level"] == "DRIVER_OR_CLASS_LEVEL"
    assert signoff["gene_specific_mapping"] is False
    assert signoff["allowed_rollout_scope"] == "CLASS_LEVEL_EXPLORATORY_ONLY"

    assert signoff["reviewer_1"]
    assert signoff["reviewer_2"]
    assert signoff["reviewer_2"] not in {
        "TÊN_NGƯỜI_REVIEW_THẬT",
        "Tên Người Review Thật",
        "TODO",
        "TBD",
        "",
    }
    assert signoff["review_date"] == "2026-09-07"

    notes = (
        signoff.get("human_notes", "")
        + " "
        + signoff.get("human_review_notes", "")
    ).lower()
    assert "not parkin gene-specific" in notes or "not a parkin gene-specific" in notes
    assert "biological parkinson validation" in notes


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
