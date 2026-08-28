from types import SimpleNamespace

import numpy as np
import pytest

from scripts.prepare_neural_checkpoint import _perturb_numeric


def _condition() -> SimpleNamespace:
    return SimpleNamespace(
        target_neurons=("neuron-a",),
        target_edges=(),
        parameters=SimpleNamespace(
            presynaptic_gain=0.5,
            postsynaptic_gain=0.25,
            neuron_survival=0.8,
        ),
    )


def test_checkpoint_perturbation_preserves_unrelated_weights() -> None:
    edges = {
        "root_ids": np.asarray(["neuron-a", "neuron-b", "neuron-c"], dtype=object),
        "Presynaptic_Index": np.asarray([0, 1, 2], dtype=np.int64),
        "Postsynaptic_Index": np.asarray([1, 0, 1], dtype=np.int64),
        "Excitatory x Connectivity": np.asarray([100.0, 200.0, 300.0], dtype=np.float32),
    }
    checkpoint = np.asarray([10.0, 20.0, 30.0], dtype=np.float32)

    result = _perturb_numeric(edges, _condition(), checkpoint)

    assert result.tolist() == pytest.approx([4.0, 4.0, 30.0])
    assert checkpoint.tolist() == [10.0, 20.0, 30.0]


def test_checkpoint_perturbation_rejects_shape_mismatch() -> None:
    edges = {
        "root_ids": np.asarray(["neuron-a", "neuron-b"], dtype=object),
        "Presynaptic_Index": np.asarray([0, 1], dtype=np.int64),
        "Postsynaptic_Index": np.asarray([1, 0], dtype=np.int64),
        "Excitatory x Connectivity": np.asarray([1.0, 1.0], dtype=np.float32),
    }

    with pytest.raises(RuntimeError, match="khong khop shape"):
        _perturb_numeric(edges, _condition(), np.asarray([1.0], dtype=np.float32))
