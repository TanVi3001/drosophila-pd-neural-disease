"""Regression tests for the evidence-gated Gate 20F mapping batch."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "experiments/gate_20f_batch_mapping_promotion/results/gate20f_batch_mapping_summary.json"
MANIFEST = ROOT / "experiments/gate_20f_batch_mapping_promotion/manifests/gate20f_batch_mapping_manifest.json"
REPORT = ROOT / "docs/disease_mapping/gate_20f_batch_mapping_promotion_report.md"
PARKIN_SIGNOFF = ROOT / "research/disease_mapping/manual_imports/parkin/reviewer_signoff.json"
CONDITION_DIR = ROOT / "configs/conditions"
CONDITIONS = {"alpha_synuclein", "pink1", "parkin", "dj1", "lrrk2"}
FAKE_IDS = {
    "todo_root_id",
    "fake_root_id",
    "synthetic_root",
    "tbd_root",
    "mock_root",
    "000000",
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_gate20f_preserves_parkin_signoff() -> None:
    signoff = _json(PARKIN_SIGNOFF)
    parkin = _json(SUMMARY)["condition_statuses"]["parkin"]

    assert signoff["reviewer_2"] == "To Dang Minh Tuan"
    assert signoff["review_date"] == "2026-09-07"
    assert signoff["gene_specific_mapping"] is False
    assert signoff["decision"] == "APPROVED_FOR_CLASS_LEVEL_EXPLORATORY"
    assert parkin["approved_condition"] is True
    assert parkin["mapping_identifier_count"] == 330


def test_gate20f_count_and_five_condition_flag_match_statuses() -> None:
    summary = _json(SUMMARY)
    statuses = summary["condition_statuses"]
    approved = [item for item in statuses.values() if item["approved_condition"]]

    assert set(statuses) == CONDITIONS
    assert summary["reviewed_condition_count"] == 5
    assert summary["approved_condition_count"] == len(approved)
    assert summary["all_five_conditions_approved"] is (len(approved) == 5)
    assert summary["approved_condition_count"] == 1
    assert summary["status"] == "MAPPING_ACQUISITION_READY"
    assert summary["disease_mapping_status"] == "READY_FOR_STEP_06"


def test_gate20f_zero_identifier_conditions_are_not_approved() -> None:
    summary = _json(SUMMARY)
    for condition, result in summary["condition_statuses"].items():
        if result["mapping_identifier_count"] == 0:
            assert result["approved_condition"] is False, condition
            assert result["reviewer_signoff"] is None, condition


def test_gate20f_approved_parkin_config_has_real_ids_and_boundary() -> None:
    config = yaml.safe_load((CONDITION_DIR / "parkin.template.yaml").read_text(encoding="utf-8"))
    targets = config["target_neurons"]

    assert len(targets) == 330
    assert config["gene_specific_mapping"] is False
    assert config["allowed_rollout_scope"] == "CLASS_LEVEL_EXPLORATORY_ONLY"
    assert config["mapping_level"] == "DRIVER_OR_CLASS_LEVEL"
    assert config["provenance"]["source_sha256"]
    for target in targets:
        root_id = str(target["root_id"]).strip()
        assert root_id.isdigit()
        assert root_id.lower() not in FAKE_IDS


def test_gate20f_does_not_introduce_fake_mapping_ids() -> None:
    for path in (ROOT / "research/disease_mapping/manual_imports").glob("**/*"):
        if path.suffix.lower() not in {".csv", ".tsv"}:
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t" if path.suffix.lower() == ".tsv" else ","):
                for field in ("root_id", "edge_id"):
                    value = row.get(field, "").strip().lower()
                    assert value not in FAKE_IDS, f"{path}: {field}"


def test_gate20f_manifest_checksums_and_boundaries() -> None:
    manifest = _json(MANIFEST)
    summary = _json(SUMMARY)
    assert manifest["status"] == summary["status"]
    assert manifest["approved_condition_count"] == summary["approved_condition_count"]
    assert manifest["all_five_conditions_approved"] is False
    for field in (
        "no_new_simulation_run",
        "no_calibration_run",
        "no_tuning_run",
        "no_raw_metric_modification",
        "no_root_id_inference",
    ):
        assert manifest[field] is True
    assert manifest["data_fabricated"] is False
    for relative, expected in manifest["source_inputs_sha256"].items():
        path = ROOT / relative
        assert path.is_file(), relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative


def test_gate20f_report_is_claim_safe() -> None:
    text = " ".join(REPORT.read_text(encoding="utf-8").lower().split())
    assert "approved_condition_count = 1/5" in text
    assert "khong co condition nao" in text
    assert "this gate promotes only evidence-supported mapping readiness" in text
    assert "does not establish biological parkinson validation" in text
    assert "gene-specific disease validation" in text
