import json
from pathlib import Path

from scripts.audit_gene_specific_mapping_review import audit
from scripts.run_gate20b_mapping_adjudication import DEFAULT_PLAN


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "research/disease_mapping/gene_specific_mapping_review.csv"


def test_gate20b_plan_and_review_are_present() -> None:
    assert DEFAULT_PLAN.is_file()
    document = audit(INPUT)

    assert document["status"] == "MAPPING_REVIEW_BLOCKED"
    assert document["approved_mapping_count"] == 0
    assert document["no_root_id_inference"] is True


def test_gate20b_has_no_simulation_side_effects() -> None:
    document = audit(INPUT)

    assert document["no_simulation_run"] is True
    assert document["no_calibration_run"] is True
    assert document["no_holdout_validation_run"] is True
    assert document["data_fabricated"] is False
    json.dumps(document)
