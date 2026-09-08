import csv
import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "research/validation/prospective/parkin_model_freeze.yaml"
MAPPING = ROOT / "research/validation/gene_specific/parkin/driver_to_connectome_mapping.csv"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _root_hash() -> str:
    with MAPPING.open("r", encoding="utf-8-sig", newline="") as handle:
        ids = sorted(row["root_id"] for row in csv.DictReader(handle))
    return hashlib.sha256(("\n".join(ids) + "\n").encode()).hexdigest()


def test_gate24_freezes_330_reviewed_roots_and_hashes() -> None:
    freeze = yaml.safe_load(FREEZE.read_text(encoding="utf-8"))
    assert freeze["status"] == "MODEL_FREEZE_COMPLETE"
    assert freeze["target_root_count"] == 330
    assert freeze["mapping_sha256"] == _sha256(MAPPING)
    assert freeze["target_neurons_sha256"] == _root_hash()
    assert freeze["seed_list"] == [0, 1, 2, 3, 4]


def test_gate24_checkpoint_is_external_and_not_fabricated() -> None:
    freeze = yaml.safe_load(FREEZE.read_text(encoding="utf-8"))
    checkpoint = (ROOT / freeze["checkpoint"]["path"]).resolve()
    assert checkpoint.is_file()
    assert freeze["checkpoint"]["sha256"] == _sha256(checkpoint)
    assert freeze["checkpoint"]["committed_to_repository"] is False


def test_gate24_mapping_has_no_edges_or_gene_expression_assertion() -> None:
    with MAPPING.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 330
    assert all(not row["edge_id"].strip() for row in rows)
    assert all(row["mapping_level"] == "GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED" for row in rows)
    assert all("Parkin-expression-specific" in row["notes"] for row in rows)
