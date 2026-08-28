import numpy as np

from drosophila_pd_neural.models import DiseaseCondition, NeuralParameters
from drosophila_pd_neural.perturbations import perturb_edges, seeded_noise


def test_only_annotated_edges_change_and_input_is_not_mutated() -> None:
    original = np.array([1.0, 2.0, 3.0])
    condition = DiseaseCondition(
        condition_id="c",
        gene_model="test",
        age_days=1,
        seed=0,
        target_neurons=("A",),
        parameters=NeuralParameters(
            presynaptic_gain=0.5,
            postsynaptic_gain=0.8,
            neuron_survival=0.9,
        ),
    )
    changed = perturb_edges(["A", "B", "C"], ["B", "A", "D"], original, condition)
    np.testing.assert_allclose(changed, [0.45, 1.44, 3.0])
    np.testing.assert_array_equal(original, [1.0, 2.0, 3.0])


def test_seeded_noise_is_reproducible() -> None:
    first = seeded_noise([1.0, 2.0], 0.1, 12)
    second = seeded_noise([1.0, 2.0], 0.1, 12)
    np.testing.assert_array_equal(first, second)
