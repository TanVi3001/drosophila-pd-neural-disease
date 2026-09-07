import numpy as np
import pytest

from drosophila_pd_neural.riemensperger2011.dopamine_transform import (
    apply_dopamine_class_presynaptic_transform,
    gain_at_burden,
)


def test_zero_burden_is_exact_identity_and_does_not_mutate() -> None:
    source = np.asarray([1.0, -2.0, 3.0])
    result = apply_dopamine_class_presynaptic_transform(source, ["a", "b", "a"], ["a"], burden=0.0)
    assert np.array_equal(result, source)
    assert np.array_equal(source, np.asarray([1.0, -2.0, 3.0]))


def test_positive_burden_only_changes_reviewed_presynaptic_population() -> None:
    result = apply_dopamine_class_presynaptic_transform([1.0, 2.0, 3.0], ["a", "b", "a"], ["a"], burden=1.0)
    assert np.allclose(result, [0.15, 2.0, 0.45])


def test_transform_is_deterministic_finite_and_bounded() -> None:
    first = apply_dopamine_class_presynaptic_transform([1.0, 2.0], ["a", "b"], ["a"], burden=0.5)
    second = apply_dopamine_class_presynaptic_transform([1.0, 2.0], ["a", "b"], ["a"], burden=0.5)
    assert np.array_equal(first, second)
    assert np.isfinite(first).all()
    assert gain_at_burden(0.0) == 1.0
    with pytest.raises(ValueError):
        apply_dopamine_class_presynaptic_transform([1.0], ["a"], ["a"], burden=1.1)
