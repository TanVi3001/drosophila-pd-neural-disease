"""Ap dung perturbation vao edge list da co annotation."""

from __future__ import annotations

from collections.abc import Iterable
import math

import numpy as np

from .models import DiseaseCondition


def perturb_edges(
    pre_ids: Iterable[str],
    post_ids: Iterable[str],
    weights: Iterable[float],
    condition: DiseaseCondition,
) -> np.ndarray:
    """Tra ve weights moi, khong mutate mang dau vao.

    Chi edge co pre/post ID nam trong condition moi bi thay doi. Khong co
    fallback theo vi tri tensor; thieu annotation la loi de tranh thay doi
    nham neuron.
    """

    pre = np.asarray(list(pre_ids), dtype=object)
    post = np.asarray(list(post_ids), dtype=object)
    result = np.asarray(list(weights), dtype=float).copy()
    if pre.shape != post.shape or pre.shape != result.shape:
        raise ValueError("pre_ids, post_ids va weights phai cung so phan tu.")
    if not np.isfinite(result).all():
        raise ValueError("weights phai huu han.")

    target_neurons = np.asarray(condition.target_neurons, dtype=object)
    params = condition.parameters
    pre_target = np.isin(pre, target_neurons)
    post_target = np.isin(post, target_neurons)
    factor = np.ones(result.shape, dtype=float)
    factor[pre_target] *= params.presynaptic_gain
    factor[post_target] *= params.postsynaptic_gain
    factor[pre_target | post_target] *= params.neuron_survival
    if condition.target_edges:
        # Match the declared pair as a tuple.  A string sentinel is unsafe
        # here because NumPy string operations may discard NUL separators.
        target_keys = {(str(pre_id), str(post_id)) for pre_id, post_id in condition.target_edges}
        edge_mask = np.fromiter(
            ((str(pre_id), str(post_id)) in target_keys for pre_id, post_id in zip(pre, post)),
            dtype=bool,
            count=result.size,
        )
        factor[edge_mask] *= params.presynaptic_gain
    result *= factor
    if not np.isfinite(result).all():
        raise ValueError("Perturbation tao ra weight khong huu han.")
    return result


def seeded_noise(values: Iterable[float], noise_std: float, seed: int) -> np.ndarray:
    """Them noise co seed cho signal trung gian; khong tao noise neu std = 0."""

    array = np.asarray(list(values), dtype=float)
    if not np.isfinite(array).all():
        raise ValueError("values phai huu han.")
    if not math.isfinite(float(noise_std)) or float(noise_std) < 0:
        raise ValueError("noise_std phai huu han va khong am.")
    if noise_std == 0:
        return array.copy()
    rng = np.random.default_rng(int(seed))
    return array + rng.normal(0.0, float(noise_std), size=array.shape)
