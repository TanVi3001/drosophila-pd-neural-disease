import csv
from pathlib import Path

import yaml

from drosophila_pd_neural.annotations import load_neuron_annotations


ROOT = Path(__file__).parents[1]


def test_exploratory_dopamine_mapping_uses_known_connectome_ids() -> None:
    config_path = ROOT / "configs" / "conditions" / "dopamine_deficiency.exploratory.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    annotations = load_neuron_annotations(ROOT / "annotations" / "neuron_annotations.csv")

    targets = config["target_neurons"]
    assert len(targets) == 342
    assert len(set(targets)) == len(targets)
    assert set(targets).issubset(annotations)
    assert all(annotations[target].neurotransmitter == "dopamine" for target in targets)
    assert config["status"] == "EXPLORATORY_NOT_CALIBRATED"


def test_mapping_status_keeps_unmapped_gene_conditions_blocked() -> None:
    path = ROOT / "research" / "disease_mapping" / "mapping_status.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 6
    assert rows[0]["mapping_status"] == "MAPPED_EXPLORATORY"
    assert all(
        row["mapping_status"] == "WAITING_NEURON_EVIDENCE"
        for row in rows[1:]
    )
