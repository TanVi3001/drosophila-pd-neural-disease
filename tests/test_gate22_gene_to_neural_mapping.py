from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_class_level_ids_cannot_become_parkin_gene_specific_automatically() -> None:
    mapping = yaml.safe_load((ROOT / "research/validation/gene_specific/parkin/mapping_spec.yaml").read_text(encoding="utf-8"))
    signoff = (ROOT / "research/validation/gene_specific/parkin/reviewer_signoff.json").read_text(encoding="utf-8")
    assert mapping["mapping_level"] == "UNRESOLVED"
    assert mapping["gene_specific_mapping"] is False
    assert mapping["directly_supported_root_ids"] == []
    assert '"decision": "PENDING_HUMAN_SIGNOFF"' in signoff
