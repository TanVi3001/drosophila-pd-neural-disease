from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

import yaml

from scripts.audit_gate24e_runtime_amendment import (
    AMENDED_COMMIT,
    AMENDMENT,
    ANALYZER,
    CHECKSUMS,
    EXECUTION,
    EXPECTED_ANALYZER_SHA256,
    EXPECTED_DISEASE_CHECKPOINTS,
    EXPECTED_FREEZE_SHA256,
    EXPECTED_GATE24D_SIGNOFF_SHA256,
    EXPECTED_GRID,
    EXPECTED_LOCKED_VALUES,
    EXPECTED_SEEDS,
    FIREWALL,
    FREEZE,
    ORIGINAL_COMMIT,
    ORIGINAL_SIGNOFF,
    ROOT,
    RUNTIME_SIGNOFF,
    _invariant_blockers,
    _review_state,
    _runtime_state_blockers,
    _sha256,
    _source_hash_blockers,
)


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


AMENDMENT_DOCUMENT = _yaml(AMENDMENT)
FREEZE_DOCUMENT = _yaml(FREEZE)
CHECKSUM_DOCUMENT = _json(CHECKSUMS)
ORIGINAL_SIGNOFF_DOCUMENT = _json(ORIGINAL_SIGNOFF)
RUNTIME_SIGNOFF_DOCUMENT = _json(RUNTIME_SIGNOFF)


def test_01_original_gate24d_signoff_remains_unchanged() -> None:
    assert _sha256(ORIGINAL_SIGNOFF) == EXPECTED_GATE24D_SIGNOFF_SHA256
    assert ORIGINAL_SIGNOFF_DOCUMENT["status"] == "PROSPECTIVE_PREDICTION_LOCKED"
    assert ORIGINAL_SIGNOFF_DOCUMENT["decision"] == "APPROVED_FOR_BLINDED_VIRTUAL_PREDICTION"


def test_02_parent_freeze_hash_is_preserved() -> None:
    assert _sha256(FREEZE) == EXPECTED_FREEZE_SHA256
    assert AMENDMENT_DOCUMENT["parent_scientific_freeze"]["sha256"] == EXPECTED_FREEZE_SHA256


def test_03_mapping_is_unchanged() -> None:
    assert AMENDMENT_DOCUMENT["locked_scientific_values"]["mapping_sha256"] == FREEZE_DOCUMENT["mapping_sha256"]
    assert AMENDMENT_DOCUMENT["scientific_invariants"]["mapping_unchanged"] is True


def test_04_target_root_set_is_unchanged() -> None:
    locked = AMENDMENT_DOCUMENT["locked_scientific_values"]
    assert locked["target_neurons_sha256"] == FREEZE_DOCUMENT["target_neurons_sha256"]
    assert locked["target_root_count"] == FREEZE_DOCUMENT["target_root_count"] == 330


def test_05_checkpoint_hashes_are_unchanged() -> None:
    locked = AMENDMENT_DOCUMENT["locked_scientific_values"]
    assert locked["healthy_checkpoint_sha256"] == FREEZE_DOCUMENT["checkpoint"]["sha256"]
    assert locked["disease_checkpoint_sha256"] == EXPECTED_DISEASE_CHECKPOINTS
    assert locked["disease_checkpoint_sha256"] == FREEZE_DOCUMENT["parkin_checkpoint_grid"]["checkpoint_sha256"]


def test_06_parameter_grid_is_unchanged() -> None:
    assert AMENDMENT_DOCUMENT["locked_scientific_values"]["parameter_grid"] == EXPECTED_GRID
    assert AMENDMENT_DOCUMENT["locked_scientific_values"]["parameter_grid"] == FREEZE_DOCUMENT["parameter_grid"]


def test_07_seeds_are_unchanged() -> None:
    assert AMENDMENT_DOCUMENT["locked_scientific_values"]["seeds"] == EXPECTED_SEEDS
    assert AMENDMENT_DOCUMENT["locked_scientific_values"]["seeds"] == FREEZE_DOCUMENT["seed_list"]


def test_08_neural_transform_is_unchanged() -> None:
    assert (
        AMENDMENT_DOCUMENT["locked_scientific_values"]["neural_transform_sha256"]
        == FREEZE_DOCUMENT["disease_transform"]["sha256"]
    )


def test_09_timestep_and_duration_are_unchanged() -> None:
    locked = AMENDMENT_DOCUMENT["locked_scientific_values"]
    assert locked["timestep_s"] == FREEZE_DOCUMENT["physics"]["timestep_s"] == 0.0001
    assert locked["duration_s"] == FREEZE_DOCUMENT["physics"]["duration_s"] == 10.0
    assert locked["simulation_steps"] == 100000


def test_10_original_platform_commit_is_recorded() -> None:
    assert AMENDMENT_DOCUMENT["original_runtime"]["platform_commit"] == ORIGINAL_COMMIT
    assert CHECKSUM_DOCUMENT["original_platform_commit"] == ORIGINAL_COMMIT


def test_11_amended_platform_commit_is_recorded() -> None:
    assert AMENDMENT_DOCUMENT["amended_runtime"]["platform_commit"] == AMENDED_COMMIT
    assert CHECKSUM_DOCUMENT["amended_platform_commit"] == AMENDED_COMMIT


def test_12_amended_runtime_is_pinned_clean_or_portably_recorded() -> None:
    runtime = (ROOT / AMENDMENT_DOCUMENT["amended_runtime"]["worktree"]).resolve()
    assert CHECKSUM_DOCUMENT["amended_clean_worktree_status"] == "CLEAN"
    if runtime.is_dir():
        head = subprocess.run(
            ["git", "-C", str(runtime), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(runtime), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert _runtime_state_blockers(head, status) == []


def test_13_artifact_profile_is_memory_safe() -> None:
    assert AMENDMENT_DOCUMENT["amended_runtime"]["artifact_profile"] == "GATE24E_MEMORY_SAFE"
    assert CHECKSUM_DOCUMENT["artifact_profile"] == "GATE24E_MEMORY_SAFE"


def test_14_simulation_semantics_are_declared_unchanged() -> None:
    assert AMENDMENT_DOCUMENT["runtime_changes"]["simulation_semantics_changed"] is False
    assert CHECKSUM_DOCUMENT["source_diff"]["simulation_semantics_changed"] is False
    assert CHECKSUM_DOCUMENT["simulation_loop"]["byte_equivalent_after_normalization"] is True


def test_15_primary_analysis_source_and_definition_are_unchanged() -> None:
    assert _sha256(ANALYZER) == EXPECTED_ANALYZER_SHA256
    contract = CHECKSUM_DOCUMENT["analysis_contract"]
    assert contract["definition_changed"] is False
    assert contract["primary_metric"] == "median_planar_speed_mm_s"
    assert contract["secondary_metric"] == "distance_traveled_mm"


def test_16_holdout_remains_sealed() -> None:
    assert _json(FIREWALL)["status"] == "SEALED"
    assert AMENDMENT_DOCUMENT["holdout_status"] == "SEALED"
    assert AMENDMENT_DOCUMENT["holdout_opened"] is False


def test_17_scientific_jobs_remain_zero() -> None:
    execution = _json(EXECUTION)
    assert execution["status"] == "NOT_EXECUTED"
    assert execution["executed_job_count"] == 0
    assert AMENDMENT_DOCUMENT["scientific_jobs_executed"] == 0


def test_18_attempt_03_is_blocked_before_human_approval() -> None:
    assert AMENDMENT_DOCUMENT["attempt_03_authorized"] is False
    assert RUNTIME_SIGNOFF_DOCUMENT["attempt_03_authorized"] is False
    assert not (ROOT / "experiments/gate_24e_storage_probe/attempt_03").exists()


def test_19_scientific_batch_is_blocked_before_human_approval() -> None:
    assert AMENDMENT_DOCUMENT["scientific_batch_authorized"] is False
    assert RUNTIME_SIGNOFF_DOCUMENT["scientific_batch_authorized"] is False


def test_20_original_signoff_is_not_reused_as_amendment_approval() -> None:
    assert RUNTIME_SIGNOFF != ORIGINAL_SIGNOFF
    assert _sha256(RUNTIME_SIGNOFF) != _sha256(ORIGINAL_SIGNOFF)
    assert RUNTIME_SIGNOFF_DOCUMENT["schema_version"] == "gate24e-runtime-amendment-review-v1"
    assert RUNTIME_SIGNOFF_DOCUMENT["decision"] == "PENDING_HUMAN_REVIEW"


def test_21_two_human_reviewers_are_required_for_approval() -> None:
    candidate = deepcopy(RUNTIME_SIGNOFF_DOCUMENT)
    candidate.update(
        status="RUNTIME_AMENDMENT_APPROVED",
        decision="APPROVED_FOR_GATE24E_RUNTIME_AMENDMENT",
        reviewer_1="Reviewer One",
        reviewer_2="",
        review_date="2026-09-08",
        attempt_03_authorized=True,
    )
    state, blockers = _review_state(candidate, _sha256(AMENDMENT))
    assert state == "APPROVED"
    assert "approved amendment requires two reviewers and an ISO review date" in blockers


def test_22_reviewer_placeholders_are_rejected() -> None:
    candidate = deepcopy(RUNTIME_SIGNOFF_DOCUMENT)
    candidate["reviewer_1"] = "REVIEWER_1"
    state, blockers = _review_state(candidate, _sha256(AMENDMENT))
    assert state == "PENDING"
    assert "reviewer placeholders are forbidden" in blockers


def test_23_invalid_runtime_hash_is_rejected(tmp_path: Path, monkeypatch) -> None:
    relative = "scripts/run_brain_body_rollout.py"
    content = b"reviewed-runtime-source\n"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    evidence = {
        "amended_executable_sources": {
            relative: {
                "git_blob_sha256": "0" * 64,
                "git_blob_byte_size": len(content),
                "windows_worktree_sha256": hashlib.sha256(content).hexdigest(),
            }
        },
        "equivalence_tests": {},
    }
    monkeypatch.setattr(
        "scripts.audit_gate24e_runtime_amendment._git_bytes",
        lambda _root, _arguments: content,
    )
    blockers = _source_hash_blockers(tmp_path, evidence)
    assert f"invalid amended runtime hash: {relative}" in blockers


def test_24_platform_commit_mismatch_is_rejected() -> None:
    assert _runtime_state_blockers("0" * 40, "") == [
        "amended platform commit mismatch: " + ("0" * 40)
    ]


def test_25_scientific_invariant_change_rejects_amendment() -> None:
    candidate = deepcopy(AMENDMENT_DOCUMENT)
    candidate["scientific_invariants"]["mapping_unchanged"] = False
    blockers, scientific_change = _invariant_blockers(candidate, FREEZE_DOCUMENT)
    assert scientific_change is True
    assert any("mapping_unchanged" in blocker for blocker in blockers)


def test_npz_and_metric_equivalence_evidence_is_locked() -> None:
    evidence = AMENDMENT_DOCUMENT["equivalence_evidence"]
    assert evidence["npz_equivalence"] == "NPZ_EQUIVALENCE_PASS"
    assert evidence["primary_metric_equivalence"] == "PRIMARY_METRIC_EQUIVALENCE_PASS"
    assert evidence["secondary_metric_equivalence"] == "SECONDARY_METRIC_EQUIVALENCE_PASS"
    assert evidence["memory_regression"] == "MEMORY_REGRESSION_PASS"


def test_current_runtime_review_is_pending_without_placeholders() -> None:
    state, blockers = _review_state(RUNTIME_SIGNOFF_DOCUMENT, _sha256(AMENDMENT))
    assert state == "PENDING"
    assert blockers == []
    assert RUNTIME_SIGNOFF_DOCUMENT["reviewer_1"] == ""
    assert RUNTIME_SIGNOFF_DOCUMENT["reviewer_2"] == ""


def test_all_expected_locked_values_are_materialized() -> None:
    locked = AMENDMENT_DOCUMENT["locked_scientific_values"]
    for key, expected in EXPECTED_LOCKED_VALUES.items():
        assert locked[key] == expected


def test_amendment_scope_has_no_scientific_claim_effect() -> None:
    assert AMENDMENT_DOCUMENT["amendment_scope"] == "POST_SIMULATION_EXPORT_AND_POSTPROCESS_ONLY"
    assert AMENDMENT_DOCUMENT["scientific_claim_effect"] == "NONE"
    assert AMENDMENT_DOCUMENT["requires_human_review"] is True
