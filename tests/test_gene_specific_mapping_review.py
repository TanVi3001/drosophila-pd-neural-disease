import json
from pathlib import Path

from scripts.audit_gene_specific_mapping_review import audit


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "research/disease_mapping/gene_specific_mapping_review.csv"


def test_gene_specific_mapping_review_keeps_all_conditions_pending() -> None:
    document = audit(INPUT)

    assert document["status"] == "MAPPING_REVIEW_BLOCKED"
    assert document["approved_mapping_count"] == 0
    assert {row["condition_id"] for row in document["conditions"]} == {
        "alpha_synuclein",
        "pink1",
        "parkin",
        "dj1",
        "lrrk2",
    }


def test_gene_specific_mapping_review_does_not_fabricate_ids() -> None:
    document = audit(INPUT)

    counts = {row["condition_id"]: int(row["mapping_identifier_count"]) for row in document["conditions"]}
    assert counts["parkin"] == 330
    assert all(counts[condition] == 0 for condition in counts if condition != "parkin")
    assert document["approved_mapping_count"] == 0
    assert document["no_root_id_inference"] is True
    assert document["data_fabricated"] is False
    json.dumps(document)


def test_gene_specific_mapping_review_blocks_unapproved_scopes() -> None:
    document = audit(INPUT)
    statuses = {row["condition_id"]: row["mapping_status"] for row in document["conditions"]}

    assert statuses["pink1"] == "MODEL_SCOPE_NOT_CELL_SPECIFIC"
    assert statuses["dj1"] == "NOT_MAPPABLE_FROM_PAPER"
    assert statuses["lrrk2"] == "NOT_MAPPABLE_TO_CURRENT_CONNECTOME"
