from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.finalize_gate24e_validation import (
    EXPECTED_BIOLOGICAL_DIRECTION,
    EXPECTED_CROSS_ASSAY_DECISION,
    EXPECTED_VIRTUAL_DECISION,
    EXPECTED_VIRTUAL_FREEZE_SHA256,
    ClosureError,
    _canonical_sha256,
    build_decision_document,
    validate_locked_evidence,
)


def test_exact_prediction_freeze_is_required() -> None:
    assert EXPECTED_VIRTUAL_FREEZE_SHA256 == "f44e9ad10b9fc4795ae2173d3e8b27fc9ea0d8202925bfc08cdcc72d06b00863"


def test_virtual_decision_is_immutable() -> None:
    assert EXPECTED_VIRTUAL_DECISION == "DIRECTIONAL_VALIDATION_NOT_SUPPORTED"


def test_biological_direction_is_immutable() -> None:
    assert EXPECTED_BIOLOGICAL_DIRECTION == "BIOLOGICAL_IMPAIRMENT_SUPPORTED"


def test_discordance_is_immutable() -> None:
    assert EXPECTED_CROSS_ASSAY_DECISION == "DIRECTIONAL_CROSS_ASSAY_DISCORDANCE"


def test_decision_document_forbids_quantitative_cross_assay_validation() -> None:
    document = build_decision_document({})
    assert document["quantitative_cross_assay_validation"] is False


def test_decision_document_forbids_biological_validation_claim() -> None:
    document = build_decision_document({})
    assert document["biological_validation_supported"] is False


def test_decision_document_forbids_retuning_and_posthoc_selection() -> None:
    document = build_decision_document({})
    assert document["retuning_after_holdout"] is False
    assert document["posthoc_parameter_selection"] is False


def test_negative_result_cannot_be_relabelled() -> None:
    document = build_decision_document({})
    assert document["scientific_result"] == "NEGATIVE_VALIDATION_RESULT"
    assert document["status"] == "GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE"
    assert "biologically validated Parkinson model" in document["forbidden_claims"]


def test_canonical_evidence_hash_is_deterministic_and_changes_on_decision_change() -> None:
    base = {"status": "GATE24E_FINAL_EVIDENCE_FROZEN", "decision": "DISCORDANCE", "items": [1, 2, 3]}
    assert _canonical_sha256(base) == _canonical_sha256(deepcopy(base))
    changed = deepcopy(base)
    changed["decision"] = "CONCORDANCE"
    assert _canonical_sha256(base) != _canonical_sha256(changed)


def test_locked_evidence_validates_current_repository() -> None:
    locked = validate_locked_evidence()
    assert set(locked) == {
        "immutable_virtual_prediction_freeze",
        "virtual_prediction_summary",
        "biological_holdout_opening",
        "cross_assay_validation_summary",
    }


def test_changed_decision_invalidates_locked_evidence(tmp_path: Path) -> None:
    # The validator reads the frozen files from a root; copy the minimum
    # closure tree and change only the immutable virtual decision.
    from scripts import finalize_gate24e_validation as module

    for source in (
        module.PREDICTION_FREEZE,
        module.VIRTUAL_SUMMARY,
        module.OPENING_MANIFEST,
        module.CROSS_ASSAY_SUMMARY,
    ):
        destination = tmp_path / source.relative_to(module.ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    changed = tmp_path / module.PREDICTION_FREEZE.relative_to(module.ROOT)
    document = json.loads(changed.read_text(encoding="utf-8"))
    document["grid_decision"] = "DIRECTIONAL_VALIDATION_PASS"
    changed.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ClosureError):
        validate_locked_evidence(tmp_path)


def test_raw_rollouts_are_not_part_of_the_closure_contract() -> None:
    document = build_decision_document({})
    assert document["future_model_requires_new_prospective_gate"] is True


def test_no_gpu_or_simulation_claims_are_supported_by_closure_constants() -> None:
    locked = validate_locked_evidence()
    assert locked["cross_assay_validation_summary"]["gpu_executed"] is False
    assert locked["cross_assay_validation_summary"]["simulation_executed"] is False
