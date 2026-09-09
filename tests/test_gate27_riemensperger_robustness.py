from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from drosophila_pd_neural.riemensperger2011.dopamine_transform import (
    apply_dopamine_class_presynaptic_transform,
)
from scripts import run_gate27_riemensperger_robustness as gate27


ROOT = Path(__file__).resolve().parents[1]


def test_burden_grid_and_gain_factors_are_frozen() -> None:
    assert gate27.BURDEN_GRID == (0.0, 0.25, 0.50, 0.75, 1.0)
    assert gate27.EXPECTED_GAINS == {0.0: 1.0, 0.25: 0.7875, 0.5: 0.575, 0.75: 0.3625, 1.0: 0.15}
    assert [gate27.expected_gain(value) for value in gate27.BURDEN_GRID] == [1.0, 0.7875, 0.575, 0.3625, 0.15]


def test_transform_identity_and_positive_burdens_modify_only_targets() -> None:
    weights = np.asarray([2.0, -4.0, 3.0])
    presynaptic = ["target", "other", "target"]
    p0 = apply_dopamine_class_presynaptic_transform(weights, presynaptic, ["target"], burden=0.0)
    assert np.array_equal(p0, weights)
    for burden in gate27.NEW_BURDENS + (1.0,):
        transformed = apply_dopamine_class_presynaptic_transform(weights, presynaptic, ["target"], burden=burden)
        assert not np.array_equal(transformed, weights)
        assert transformed[1] == weights[1]
        assert np.allclose(transformed[[0, 2]], weights[[0, 2]] * gate27.expected_gain(burden))


def test_target_count_and_mapping_scope_remain_class_level() -> None:
    mapping = json.loads(gate27.MAPPING_SUMMARY.read_text(encoding="utf-8"))
    config = gate27.yaml.safe_load(gate27.CONDITION_CONFIG.read_text(encoding="utf-8"))
    assert gate27.TARGET_COUNT == mapping["target_count"] == len(config["target_neurons"]) == 342
    assert mapping["mapping_level"] == "DOPAMINE_CLASS_LEVEL_EXPLORATORY"
    assert mapping["gene_specific_mapping"] is False


def test_endpoint_reuse_and_exact_new_job_plan() -> None:
    assert gate27.REUSED_BURDENS == (0.0, 1.0)
    assert gate27.NEW_BURDENS == (0.25, 0.50, 0.75)
    plan = gate27.build_job_plan()
    assert len(plan) == gate27.MAX_NEW_SIMULATIONS == 15
    assert [(row["burden"], row["seed"]) for row in plan] == [
        (burden, seed) for burden in gate27.NEW_BURDENS for seed in gate27.SEEDS
    ]
    assert not any(row["burden"] in gate27.REUSED_BURDENS for row in plan)
    assert {row["seed"] for row in plan} == {0, 1, 2, 3, 4}


def test_protocol_and_endpoint_priority_are_frozen() -> None:
    assert (gate27.STEPS, gate27.TIMESTEP_S, gate27.VIRTUAL_DURATION_S) == (5000, 0.0001, 0.5)
    assert (gate27.STIMULUS, gate27.CPG_HZ, gate27.WORLD) == ("p9", 12.0, "flat_terrain_default")
    assert gate27.RUNTIME_COMMIT == "655e854544e3d814dfe422883ff0de66b619d6c1"
    assert gate27.RUNTIME_PROFILE == "GATE24E_MEMORY_SAFE"
    assert gate27.PRIMARY_METRIC == "median_planar_speed_mm_s"
    assert gate27.SECONDARY_METRIC == "distance_traveled_mm"


def test_classification_rules_are_frozen() -> None:
    all_negative = {burden: burden > 0 for burden in gate27.BURDEN_GRID}
    assert gate27.classify_robustness(all_negative, True) == "ROBUSTNESS_MONOTONIC_IMPAIRMENT_PATTERN"
    assert gate27.classify_robustness(all_negative, False) == "ROBUSTNESS_MIXED_DIRECTIONAL_RESPONSE"
    mixed = {0.0: False, 0.25: True, 0.5: False, 0.75: False, 1.0: False}
    assert gate27.classify_robustness(mixed, False) == "ROBUSTNESS_MIXED_DIRECTIONAL_RESPONSE"
    none = {burden: False for burden in gate27.BURDEN_GRID}
    assert gate27.classify_robustness(none, True) == "ROBUSTNESS_NO_IMPAIRMENT_ACROSS_GRID"
    assert gate27.classify_robustness(none, True, complete=False) == "ROBUSTNESS_INCOMPLETE_TECHNICAL_EXECUTION"


def test_no_optimization_or_retry_contract_in_source() -> None:
    source = Path(gate27.__file__).read_text(encoding="utf-8")
    assert '"retry_count": 0' in source
    assert '"seed_replacement": False' in source
    assert '"parameter_optimization": False' in source
    assert '"best_burden_selected": False' in source
    assert '"paper_ratio_used_for_optimization": False' in source
    assert "closest" not in source.lower()
    assert "argmin" not in source.lower()


def test_gate26_result_and_inventory_are_immutable() -> None:
    assert gate27.GATE26_RESULT == "NOT_REPRODUCED"
    result = gate27.verify_gate26_inventory()
    assert result["verified"] == result["total"] == 37
    assert sum(result["verification_modes"].values()) == 37


def test_human_signoff_is_never_auto_approved() -> None:
    signoff = gate27.build_initial_signoff("ROBUSTNESS_NO_IMPAIRMENT_ACROSS_GRID", "freeze")
    assert signoff["status"] == "WAITING_GATE27_RIEMENSPERGER_ROBUSTNESS_HUMAN_REVIEW"
    assert signoff["decision"] == "PENDING_HUMAN_REVIEW"
    assert signoff["gate27_closed"] is False
    assert not any(signoff[key] for key in (
        "execution_freeze_approved", "endpoint_reuse_approved", "transform_audit_approved",
        "simulation_qc_approved", "robustness_analysis_approved", "claim_boundary_approved",
    ))


def test_default_cli_does_not_select_execution() -> None:
    args = gate27.build_parser().parse_args([])
    assert args.execute is False
    assert args.analyze_existing is False


def test_gate27_claim_boundaries_are_false_when_completion_exists() -> None:
    if gate27.COMPLETION.is_file():
        completion = json.loads(gate27.COMPLETION.read_text(encoding="utf-8"))
        assert completion["gate26_changed"] is False
        assert completion["calibration"] is False
        assert completion["parameter_optimization"] is False
        assert completion["best_burden_selected"] is False
        assert completion["biological_validation_supported"] is False
        assert completion["gene_specific_validation_supported"] is False


def test_gate27_reproducibility_when_completion_exists() -> None:
    if gate27.COMPLETION.is_file():
        result = gate27.verify_gate27_reproducibility()
        assert result["status"] == "PASS"
        assert result["verified"] == result["total"]
