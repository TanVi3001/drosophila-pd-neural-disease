from pathlib import Path

from drosophila_pd_neural.annotations import load_neuron_annotations


def test_empty_template_is_valid_and_contains_no_scientific_data() -> None:
    root = Path(__file__).parents[1]
    annotations = load_neuron_annotations(root / "annotations" / "neuron_annotations.template.csv")
    assert annotations == {}
