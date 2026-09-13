"""CPU-only contract tests for the alpha-synuclein/dopamine research gate."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from drosophila_pd_neural.models import DiseaseProfile, NeuralParameters
from drosophila_pd_neural.perturbations import perturb_edges
from drosophila_pd_neural.alpha_syn_dopamine_runner import build_job_matrix, load_spec, resolve_condition
from scripts.run_alpha_syn_dopamine import _require_execution_authorization


ROOT = Path(__file__).resolve().parents[1]
PROXY_CONFIG = ROOT / "experiments/gate_12c_computational_proxy_configs/configs/alpha_synuclein_proxy_condition.yaml"


def test_functional_and_structural_states_are_separate_and_age_interpolates() -> None:
    profile = DiseaseProfile(
        condition_id="alpha_synuclein",
        gene_model="human_alpha_synuclein",
        seed=29001,
        full_burden=NeuralParameters(
            presynaptic_gain=0.6,
            neuron_survival=0.4,
            noise_std=0.2,
        ),
        burden_curve=((0.0, 0.0), (10.0, 1.0)),
    )

    zero = profile.at_age(0.0)
    half = profile.at_age(5.0)
    full = profile.at_age(10.0)

    assert zero is not None and half is not None and full is not None
    assert zero.parameters.presynaptic_gain == 1.0
    assert zero.parameters.neuron_survival == 1.0
    assert np.isclose(half.parameters.presynaptic_gain, 0.8)
    assert np.isclose(half.parameters.neuron_survival, 0.7)
    assert np.isclose(half.parameters.noise_std, 0.1)
    assert full.parameters.presynaptic_gain == 0.6
    assert full.parameters.neuron_survival == 0.4


def test_perturbation_requires_explicit_ids_and_does_not_use_position() -> None:
    condition = DiseaseProfile(
        condition_id="alpha_synuclein",
        gene_model="human_alpha_synuclein",
        seed=0,
        target_neurons=("N2",),
        target_edges=(("N3", "N4"),),
        full_burden=NeuralParameters(presynaptic_gain=0.5, neuron_survival=0.8),
        burden_curve=((0.0, 1.0),),
    ).at_age(0.0)
    assert condition is not None

    original = np.array([10.0, 20.0, 30.0, 40.0])
    changed = perturb_edges(
        ["N0", "N1", "N3", "N5"],
        ["N1", "N0", "N4", "N5"],
        original,
        condition,
    )

    # The first two rows are not silently changed merely because they occupy
    # a particular tensor position.  Only the explicitly named edge changes.
    assert np.array_equal(changed[:2], original[:2])
    assert changed[2] != original[2]
    assert changed[3] == original[3]


def test_alpha_syn_config_is_exploratory_and_has_no_gene_specific_mapping() -> None:
    config = yaml.safe_load(PROXY_CONFIG.read_text(encoding="utf-8"))

    assert config["condition_id"] == "alpha_synuclein"
    assert config["target_definition"]["gene_specific_mapping"] is False
    assert config["target_definition"]["target_neurons"] == []
    assert config["target_definition"]["target_edges"] == []
    assert config["burden"]["calibrated"] is False
    assert config["proxy_operator"]["biological_mapping_claim"] is False


def test_alpha_syn_dopamine_runner_resolves_locked_shape_without_simulation() -> None:
    spec = load_spec(
        ROOT / "experiments/alpha_syn_dopamine/configs/alpha_syn_dopamine_runner_v1.yaml",
        project_root=ROOT,
    )
    jobs = build_job_matrix(spec)

    assert len(jobs) == 15
    assert len({job.job_id for job in jobs}) == 15
    assert spec.condition_id == "alpha_synuclein"
    assert spec.gene_specific_mapping is False
    assert spec.protocol_review_status == "DUAL_HUMAN_RUNNER_PROTOCOL_REVIEW_PASS"
    assert spec.parameter_lock_status == "LOCKED_FOR_EXECUTION"

    functional = resolve_condition(spec, "functional_state", seed=0)
    structural = resolve_condition(spec, "structural_comparator", seed=0)
    assert len(functional.target_neurons) > 0
    assert functional.parameters.presynaptic_gain < 1.0
    assert structural.parameters.presynaptic_gain == 1.0
    assert structural.parameters.neuron_survival < 1.0


def test_alpha_syn_dopamine_execute_guard_rejects_without_explicit_gpu_authorization() -> None:
    spec = load_spec(
        ROOT / "experiments/alpha_syn_dopamine/configs/alpha_syn_dopamine_runner_v1.yaml",
        project_root=ROOT,
    )

    with pytest.raises(RuntimeError, match="GPU execution authorization is not active"):
        _require_execution_authorization(spec)
