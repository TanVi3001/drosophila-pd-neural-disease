"""Ap dung perturbation vao edge list da co annotation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
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

    target_neurons = set(condition.target_neurons)
    target_edges = set(condition.target_edges)
    params = condition.parameters
    for index, (pre_id, post_id) in enumerate(zip(pre.tolist(), post.tolist())):
        factor = 1.0
        pre_target = str(pre_id) in target_neurons
        post_target = str(post_id) in target_neurons
        if pre_target:
            factor *= params.presynaptic_gain
        if post_target:
            factor *= params.postsynaptic_gain
        if pre_target or post_target:
            factor *= params.neuron_survival
        if (str(pre_id), str(post_id)) in target_edges:
            factor *= params.presynaptic_gain
        result[index] *= factor
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
