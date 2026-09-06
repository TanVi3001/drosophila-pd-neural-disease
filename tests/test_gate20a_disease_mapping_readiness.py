import json
from pathlib import Path

from scripts.audit_disease_mapping_readiness import build_audit


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "experiments/gate_20a_disease_mapping/configs/disease_mapping_review_plan.yaml"
ROOT_AUDIT = ROOT / "datasets/literature_phenotypes/root_id_mapping_audit.csv"
MAPPING_STATUS = ROOT / "research/disease_mapping/mapping_status.csv"


def test_gate20a_allows_signed_class_level_parkin_readiness() -> None:
    audit = build_audit(plan_path=PLAN, root_audit_path=ROOT_AUDIT, mapping_status_path=MAPPING_STATUS)

    assert audit["status"] == "READY_FOR_STEP_06"
    assert audit["requested_ready_count"] == 1
    requested = [row for row in audit["conditions"] if row["requested_for_step_06"]]
    assert len(requested) == 5
    statuses = {row["condition_id"]: row["status"] for row in requested}
    assert statuses["parkin"] == "READY_EXPLORATORY_CLASS_LEVEL"
    assert all(
        statuses[condition] in {"WAITING_REVIEWED_MAPPING", "WAITING_MODEL_SCOPE_REVIEW"}
        for condition in {"alpha_synuclein", "pink1", "dj1", "lrrk2"}
    )
    assert all(row["mapping_review_status"] != "APPROVED" for row in requested)


def test_gate20a_marks_dopamine_reference_exploratory_only() -> None:
    audit = build_audit(plan_path=PLAN, root_audit_path=ROOT_AUDIT, mapping_status_path=MAPPING_STATUS)
    dopamine = next(row for row in audit["conditions"] if row["condition_id"] == "dopamine_deficiency_exploratory")

    assert dopamine["mapping_scope"] == "class_level_exploratory"
    assert dopamine["gene_specific_mapping"] is False
    assert dopamine["data_fabricated"] is False


def test_gate20a_manifest_contract_is_non_simulation() -> None:
    audit = build_audit(plan_path=PLAN, root_audit_path=ROOT_AUDIT, mapping_status_path=MAPPING_STATUS)

    assert audit["no_simulation_run"] is True
    assert audit["no_calibration_run"] is True
    assert audit["no_holdout_validation_run"] is True
    json.dumps(audit)
