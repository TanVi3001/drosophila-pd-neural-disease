import csv
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PARKIN = ROOT / "research/validation/gene_specific/parkin"


def test_gate23_experiment_contract_locks_intervention_and_control() -> None:
    contract = yaml.safe_load((PARKIN / "experiment_contract.yaml").read_text(encoding="utf-8"))
    assert contract["status"] == "EXPERIMENT_LOCKED"
    assert contract["intervention"]["construct"] == "UAS-parkin-HMS01800-RNAi"
    assert contract["intervention"]["driver"] == "TH-GAL4"
    assert contract["control"]["exact_control_locked"] is True
    assert contract["control"]["genotype"] == "UAS-mCD8-GFP; TH-GAL4"
    assert contract["sample_sizes"]["total_activity_flies"] == 145


def test_gate23_driver_mapping_has_real_root_ids_but_pending_review() -> None:
    mapping = PARKIN / "driver_to_connectome_mapping.csv"
    with mapping.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 330
    assert all(row["root_id"].isdigit() for row in rows)
    assert all(row["edge_id"] == "" for row in rows)
    assert all(row["mapping_level"] == "GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED" for row in rows)
    assert all("Parkin-expression-specific" in row["notes"] for row in rows)
    assert all(row["reviewer_2"] == "" for row in rows)


def test_gate23_holdout_is_summary_only_and_not_tuning_data() -> None:
    source = ROOT / "research/validation/biological/parkin_validation_sources.csv"
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "HELD_OUT_VALIDATION_SOURCE_FOUND"
    assert row["data_type"] == "SUMMARY_LEVEL_VALIDATION_EVIDENCE"
    assert row["raw_data_available"] == "false"
    assert row["not_used_for_tuning"] == "true"
    assert row["transfer_status"] == "VALIDATION_ONLY"


def test_gate23_never_claims_direct_gene_expression_mapping() -> None:
    config = yaml.safe_load((ROOT / "configs/validation/gate_23_parkin_driver_defined_validation.yaml").read_text(encoding="utf-8"))
    assert config["intervention_scope"] == "GENE_SPECIFIC_INTERVENTION"
    assert config["connectome_scope"] == "DRIVER_DEFINED_CONNECTOME_MAPPING"
    assert config["direct_expression_scope"] == "GENE_EXPRESSION_DIRECT_MAPPING_NOT_ASSERTED"
    assert config["execution_policy"]["gpu"] is False


def test_gate23_report_keeps_scientific_boundary() -> None:
    report = (ROOT / "docs/validation/gate_23_parkin_driver_defined_validation_report.md").read_text(encoding="utf-8")
    assert "Parkin-expression-specific mapping" in report
    assert "Two-human signoff is still pending" in report
    assert "no GPU, simulation, calibration or tuning" in report
