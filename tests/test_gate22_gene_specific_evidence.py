from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_parkin_evidence_is_present_but_not_promoted_without_review() -> None:
    intervention = yaml.safe_load((ROOT / "research/validation/gene_specific/parkin/intervention_evidence.yaml").read_text(encoding="utf-8"))
    assert intervention["status"] == "GENE_SPECIFIC_EVIDENCE_INCOMPLETE"
    assert intervention["exact_intervention"]
    assert intervention["control_genotype"] == "AGE_MATCHED_CONTROL_EXACT_GENOTYPE_NOT_LOCKED"
    assert intervention["rescue_status"] == "RESCUE_EVIDENCE_NOT_AVAILABLE"
