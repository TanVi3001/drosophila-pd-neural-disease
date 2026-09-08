import csv
import json
from pathlib import Path

import yaml

from scripts.apply_gate23_driver_mapping_signoff import propagate_signoff, validate_signoff


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


def test_gate23_driver_mapping_has_real_root_ids_and_review_propagation() -> None:
    mapping = PARKIN / "driver_to_connectome_mapping.csv"
    with mapping.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 330
    assert all(row["root_id"].isdigit() for row in rows)
    assert all(row["edge_id"] == "" for row in rows)
    assert all(row["mapping_level"] == "GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED" for row in rows)
    assert all("Parkin-expression-specific" in row["notes"] for row in rows)
    assert all(row["reviewer_1"] == "Tuan Le" for row in rows)
    assert all(row["reviewer_2"] == "To Dang Minh Tuan" for row in rows)
    assert all(row["review_date"] == "2026-09-08" for row in rows)


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


def test_gate23_signoff_rejects_missing_second_reviewer() -> None:
    signoff = json.loads((PARKIN / "driver_mapping_reviewer_signoff.json").read_text(encoding="utf-8"))
    invalid = dict(signoff, reviewer_2="")
    try:
        validate_signoff(invalid)
    except ValueError as error:
        assert "invalid_reviewer_2" in str(error)
    else:
        raise AssertionError("missing reviewer_2 was accepted")


def test_gate23_signoff_rejects_direct_expression_claim() -> None:
    signoff = json.loads((PARKIN / "driver_mapping_reviewer_signoff.json").read_text(encoding="utf-8"))
    invalid = dict(signoff, direct_gene_expression_mapping=True)
    try:
        validate_signoff(invalid)
    except ValueError as error:
        assert "direct_gene_expression_mapping_must_be_false" in str(error)
    else:
        raise AssertionError("direct expression mapping was accepted")


def test_gate23_propagation_changes_only_review_fields() -> None:
    mapping = PARKIN / "driver_to_connectome_mapping.csv"
    signoff = json.loads((PARKIN / "driver_mapping_reviewer_signoff.json").read_text(encoding="utf-8"))
    with mapping.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    updated = propagate_signoff(rows, signoff)
    assert len(updated) == 330
    assert {row["root_id"] for row in updated} == {row["root_id"] for row in rows}
    for before, after in zip(rows, updated):
        for field in fieldnames:
            if field not in {"reviewer_1", "reviewer_2", "review_date"}:
                assert before[field] == after[field]


def test_gate23_ready_does_not_promote_gate22_biological_validation() -> None:
    status = json.loads((ROOT / "experiments/gate_22_validation_ladder_status.json").read_text(encoding="utf-8"))
    assert status["gate_23"]["status"] == "GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED_READY"
    assert status["status"] == "WAITING_BIOLOGICAL_VALIDATION_DATA"


def test_gate23_report_keeps_scientific_boundary() -> None:
    report = (ROOT / "docs/validation/gate_23_parkin_driver_defined_validation_report.md").read_text(encoding="utf-8")
    assert "Parkin-expression-specific mapping" in report
    assert "Two-human signoff is complete" in report
    assert "no GPU, simulation, calibration or tuning" in report
