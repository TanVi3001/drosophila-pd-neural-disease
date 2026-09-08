import csv
import hashlib
from pathlib import Path

import numpy as np
import pytest
import yaml

from drosophila_pd_neural.parkin.mapping import MappingValidationError, load_completeness_root_ids, load_reviewed_mapping
from drosophila_pd_neural.parkin.transform import NeuralTransformError, apply_parkin_neural_transform, apply_parkin_transform_from_root_ids


ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "research/validation/gene_specific/parkin/driver_to_connectome_mapping.csv"
CONTRACT = ROOT / "research/validation/prospective/parkin_neural_transform_contract.yaml"
TRANSFORM_SOURCE = ROOT / "src/drosophila_pd_neural/parkin/transform.py"


def _mapping():
    return load_reviewed_mapping(MAPPING)


def test_exactly_330_reviewed_root_ids_loaded():
    assert _mapping().count == 330


def test_342_riemensperger_set_is_not_used():
    mapping = _mapping()
    assert mapping.count != 342
    assert all("riemensperger" not in root.lower() for root in mapping.root_ids)


def test_target_id_set_is_unchanged_by_loader():
    with MAPPING.open(encoding="utf-8-sig", newline="") as handle:
        source_ids = tuple(row["root_id"] for row in csv.DictReader(handle))
    assert set(_mapping().root_ids) == set(source_ids)


def test_zero_parameter_is_exact_identity_copy():
    weights = np.array([1.0, -2.0, 3.5], dtype=np.float32)
    result = apply_parkin_neural_transform(weights, np.array([0, 1, 2]), [1], 0.0)
    assert np.array_equal(result, weights)
    assert result is not weights


def test_healthy_input_is_not_mutated():
    weights = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    original = weights.copy()
    apply_parkin_neural_transform(weights, np.array([0, 1, 2]), [1], 0.5)
    assert np.array_equal(weights, original)


def test_disease_representation_is_a_separate_array():
    weights = np.ones(3, dtype=np.float32)
    result = apply_parkin_neural_transform(weights, np.array([0, 1, 2]), [1], 0.5)
    assert result is not weights
    assert result[1] == pytest.approx(0.5)


def test_non_target_neural_units_are_unchanged():
    result = apply_parkin_neural_transform(np.ones(4, dtype=np.float32), np.array([0, 1, 2, 3]), [1], 0.5)
    assert np.array_equal(result[[0, 2, 3]], np.ones(3, dtype=np.float32))


def test_only_target_presynaptic_edges_are_affected():
    result = apply_parkin_neural_transform(np.ones(4, dtype=np.float32), np.array([1, 2, 1, 3]), [1], 0.25)
    assert np.array_equal(result, np.array([0.75, 1.0, 0.75, 1.0], dtype=np.float32))


def test_transform_values_are_finite():
    result = apply_parkin_neural_transform(np.ones(3, dtype=np.float32), np.array([0, 1, 2]), [1], 1.0)
    assert np.isfinite(result).all()


def test_transform_is_deterministic():
    weights = np.arange(6, dtype=np.float32)
    pre = np.array([0, 1, 2, 1, 3, 4])
    first = apply_parkin_neural_transform(weights, pre, [1, 3], 0.5)
    second = apply_parkin_neural_transform(weights, pre, [1, 3], 0.5)
    assert np.array_equal(first, second)


def test_transform_has_no_action_or_joint_posthoc_scaling():
    source = TRANSFORM_SOURCE.read_text(encoding="utf-8")
    assert "joint_angles" not in source
    assert "LocomotionAction" not in source
    assert "action *=" not in source


def test_transform_contract_is_before_action_generation():
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert contract["operation_level"] == "NEURAL_PRE_ACTION"
    assert contract["primary_parameter_status"] == "WAITING_PRIMARY_PARKIN_PARAMETER_DECISION"


def test_biological_equivalence_is_not_asserted():
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert contract["biological_equivalence"] == "NOT_ASSERTED"


def test_mapping_sha_verification():
    mapping = _mapping()
    expected = hashlib.sha256(MAPPING.read_bytes()).hexdigest()
    assert mapping.mapping_sha256 == expected
    assert load_reviewed_mapping(MAPPING, expected_mapping_sha256=expected).count == 330


def test_reviewer_verification_and_root_id_resolution():
    mapping = _mapping()
    assert mapping.reviewer_1 == "Tuan Le"
    assert mapping.reviewer_2 == "To Dang Minh Tuan"
    connectome = load_completeness_root_ids(ROOT.parent / "external/fly-brain-audit/data/2025_Completeness_783.csv")
    assert set(mapping.root_ids).issubset(set(connectome))


def test_missing_explicit_connectome_mapping_is_rejected():
    with pytest.raises(NeuralTransformError):
        apply_parkin_transform_from_root_ids(np.ones(2, dtype=np.float32), np.array([0, 1]), ["a", "b"], ["not-reviewed"], 0.5)
