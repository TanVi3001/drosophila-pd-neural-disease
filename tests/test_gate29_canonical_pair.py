from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import run_gate29_canonical_pair as canonical
from scripts import run_gate29_neural_causal_trace as gate29


def test_canonical_design_identity_and_seed_boundary() -> None:
    design = canonical._json(canonical.DESIGN_PATH)
    assert design["status"] == "COMPLETE"
    assert design["pair_id"] == "GATE29_CANONICAL_PAIR_V1"
    assert design["job_count"] == 2
    assert design["seed_9202_is_not_scientific_replicate"] is True
    assert design["seed_9202_is_not_seed_replacement_for_scientific_result"] is True
    assert design["historical_seed_9201_result_changed"] is False


def test_historical_seed_and_old_artifacts_are_preserved() -> None:
    manifest = gate29._json(gate29.GATE29_MANIFEST)
    assert manifest["historical_pair_seed"] == 9201
    assert manifest["historical_pair_status"] == "UNSUITABLE_SOURCE_NOT_REPRODUCIBLE"
    assert gate29.BASELINE_LOCK.is_file()
    assert gate29.BASELINE_SOURCE_SNAPSHOT.is_file()
    assert gate29.TRACE_ATTEMPT_PROVENANCE.is_file()


def test_canonical_source_manifest_is_outside_git_and_fingerprinted() -> None:
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    assert manifest["source_snapshot_outside_git"] is True
    assert manifest["file_count"] >= 5
    assert len(manifest["canonical_brain_source_tree_sha256"]) == 64
    assert manifest["files"] == sorted(manifest["files"], key=lambda item: item["relative_path"])
    assert all(item["sha256"] for item in manifest["files"])
    assert all(item["size_bytes"] > 0 for item in manifest["files"])


def test_canonical_source_contains_required_files_and_checkpoint() -> None:
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    paths = {item["relative_path"] for item in manifest["files"]}
    assert {
        "brain_body_bridge.py",
        "code/run_pytorch.py",
        "data/plastic_weights.pt",
        "data/2025_Completeness_783.csv",
        "data/2025_Connectivity_783.parquet",
    } <= paths
    assert manifest["checkpoint_sha256"] == canonical.CHECKPOINT_SHA256


def test_snapshot_files_have_matching_hashes() -> None:
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    state = canonical._snapshot_state(manifest)
    assert state["status"] == "PASS"
    assert state["canonical_brain_source_tree_sha256"] == manifest["canonical_brain_source_tree_sha256"]


def test_checkpoint_hash_is_locked() -> None:
    checkpoint = canonical.SNAPSHOT_ROOT / "data/plastic_weights.pt"
    assert canonical._sha256(checkpoint) == canonical.CHECKPOINT_SHA256


def test_snapshot_manifest_roles_are_explicit() -> None:
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    roles = {item["relative_path"]: item["role"] for item in manifest["files"]}
    assert roles["brain_body_bridge.py"] == "CODE"
    assert roles["data/plastic_weights.pt"] == "MODEL"
    assert roles["data/2025_Connectivity_783.parquet"] == "CONNECTIVITY"


def test_pair_has_exactly_two_jobs_and_one_semantic_difference() -> None:
    context = canonical._json(canonical.CONTEXT_PATH)
    assert set(context["jobs"]) == {"baseline", "trace"}
    assert context["normalized_specs_match"] is True
    assert context["allowed_differences"] == list(canonical.ALLOWED_SPEC_DIFFERENCES)
    assert context["jobs"]["baseline"]["instrumentation_enabled"] is False
    assert context["jobs"]["trace"]["instrumentation_enabled"] is True


def test_normalized_specs_are_identical() -> None:
    context = canonical._json(canonical.CONTEXT_PATH)
    result = canonical.verify_job_pair_equivalence(context["jobs"]["baseline"], context["jobs"]["trace"])
    assert result["status"] == "MATCH"
    assert result["mismatches"] == []


def test_context_mismatch_is_fail_closed() -> None:
    context = canonical._json(canonical.CONTEXT_PATH)
    altered = dict(context["jobs"]["trace"])
    altered["stimulus"] = "sugar"
    result = canonical.verify_job_pair_equivalence(context["jobs"]["baseline"], altered)
    assert result["status"] == "GATE29_CANONICAL_PAIR_CONTEXT_MISMATCH"
    assert "stimulus" in result["mismatches"]


def test_common_physics_and_runtime_context_are_locked() -> None:
    common = canonical._json(canonical.CONTEXT_PATH)["common"]
    assert common["seed"] == 9202
    assert common["steps"] == 5000
    assert common["duration_s"] == 0.5
    assert common["timestep_s"] == 0.0001
    assert common["stimulus"] == "p9"
    assert common["device"] == "cuda"
    assert common["artifact_profile"] == "GATE24E_MEMORY_SAFE"
    assert common["runtime_commit"] == canonical.RUNTIME_COMMIT


def test_sanitized_environment_has_no_volatile_absolute_paths() -> None:
    environment = canonical._json(canonical.CONTEXT_PATH)["sanitized_environment"]
    assert environment["python_executable"].endswith("Scripts/python.exe")
    assert environment["runtime_root_logical"] == "drosophila-pd-flygym-gate24-memorysafe-clean"
    assert environment["snapshot_root_logical"].startswith("gate29_canonical_inputs/")
    assert "E:\\" not in json.dumps(environment)


def test_runtime_commit_and_clean_state_are_locked() -> None:
    state = canonical._runtime_state()
    assert state["status"] == "PASS"
    assert state["head"] == canonical.RUNTIME_COMMIT
    assert state["dirty"] is False


def test_trace_line_mapping_is_current_and_runtime_unverified() -> None:
    mapping = canonical.verify_trace_line_mapping()
    assert mapping["status"] == "PASS"
    assert mapping["runtime_verified_edge_count"] == 0
    assert mapping["source_code_verified_edge_count"] == 11


def test_authorization_is_pending_and_binds_source_runtime() -> None:
    authorization = canonical._json(canonical.AUTHORIZATION_PATH)
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    assert authorization["authorized"] is False
    assert authorization["authorized_code_head"] == ""
    assert authorization["authorized_pair_id"] == canonical.PAIR_ID
    assert authorization["authorized_seed"] == 9202
    assert authorization["authorized_jobs"] == 2
    assert authorization["authorized_brain_source_tree_sha256"] == manifest["canonical_brain_source_tree_sha256"]
    assert authorization["authorized_runtime_commit"] == canonical.RUNTIME_COMMIT
    assert authorization["scientific_execution_authorized"] is False
    assert authorization["disease_execution_authorized"] is False
    assert authorization["no_auto_sign"] is True


def test_supersession_blocks_old_trace_only_mode() -> None:
    paths = gate29._resolve_paths(gate29._parser().parse_args([]))
    with pytest.raises(gate29.Gate29Error, match="GATE29_TRACE_ONLY_PLAN_SUPERSEDED"):
        gate29.execute_authorized_trace_only(paths)


def test_old_supersession_manifest_is_explicit() -> None:
    supersession = canonical._json(canonical.SUPERSESSION_PATH)
    assert supersession["status"] == "GATE29_TRACE_ONLY_PLAN_SUPERSEDED"
    assert supersession["historical_seed"] == 9201
    assert supersession["historical_baseline_preserved"] is True
    assert supersession["old_trace_only_execution_allowed"] is False


def test_output_skeleton_is_not_executed() -> None:
    state = canonical._json(canonical.CANONICAL_OUTPUT_ROOT / "execution_state/status.json")
    assert state["state"] == "NOT_EXECUTED"
    assert state["gpu_execution"] is False
    assert state["simulation_execution"] is False
    assert state["scientific_jobs"] == 0


def test_design_has_strict_comparison_contract() -> None:
    design = canonical._json(canonical.DESIGN_PATH)
    assert design["comparison_rtol"] == 0.0
    assert design["comparison_atol"] == 1e-12
    assert design["discrete_comparison"] == "EXACT"
    assert design["automatic_retry"] is False


def test_design_has_scientific_firewall() -> None:
    design = canonical._json(canonical.DESIGN_PATH)
    assert design["no_gpu_execution"] is True
    assert design["no_simulation_execution"] is True
    assert design["scientific_jobs"] == 0
    assert design["disease_jobs"] == 0
    assert design["calibration"] is False
    assert design["fitting"] is False
    assert design["retuning"] is False
    assert design["dopamine"] is False


def test_pair_preflight_is_ready_only_for_human_authorization() -> None:
    result = canonical.canonical_pair_preflight()
    assert result["status"] == "GATE29_CANONICAL_PAIR_PREFLIGHT_READY_FOR_HUMAN_AUTHORIZATION"
    assert result["gpu_execution"] is False
    assert result["simulation_execution"] is False
    assert result["scientific_jobs"] == 0
    assert result["holdout"] == "SEALED"


def test_execution_requires_human_authorization() -> None:
    with pytest.raises(canonical.CanonicalPairError, match="WAITING_GATE29_CANONICAL_PAIR_HUMAN_AUTHORIZATION"):
        canonical.execute_authorized_canonical_pair()


def test_common_runner_requires_authorization() -> None:
    with pytest.raises(canonical.CanonicalPairError, match="WAITING_GATE29_CANONICAL_PAIR_HUMAN_AUTHORIZATION"):
        canonical._run_canonical_pair_job(
            instrumentation_enabled=False,
            output=canonical.CANONICAL_OUTPUT_ROOT / "baseline",
            authorization={"authorized": False},
        )


def test_no_disease_or_calibration_fields_in_pair_jobs() -> None:
    context = canonical._json(canonical.CONTEXT_PATH)
    for job in context["jobs"].values():
        assert job["condition"] == "healthy"
        assert "disease_config" not in job
        assert "calibration_target" not in job
        assert "holdout" not in job


def test_canonical_pair_is_not_the_historical_output_root() -> None:
    assert canonical.CANONICAL_OUTPUT_ROOT.name == "canonical_pair_v1"
    assert "neural_causal_trace" not in str(canonical.CANONICAL_OUTPUT_ROOT)


def test_manifest_fingerprint_recomputes_deterministically() -> None:
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    rebuilt = canonical.build_snapshot_manifest(canonical.SOURCE_ROOT, canonical.SNAPSHOT_ROOT)
    assert rebuilt["canonical_brain_source_tree_sha256"] == manifest["canonical_brain_source_tree_sha256"]
    assert rebuilt["files"] == manifest["files"]


def test_snapshot_does_not_include_cache_or_output_names() -> None:
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    for record in manifest["files"]:
        assert not any(part in {".git", ".venv", "__pycache__", ".pytest_cache", "cache", "logs", "videos", "outputs", "temporary"} for part in Path(record["relative_path"]).parts)


def test_runtime_source_is_not_the_canonical_snapshot() -> None:
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    assert manifest["source_root_logical"] == "external/fly-brain"
    assert manifest["snapshot_root_logical"] != manifest["source_root_logical"]


def test_gate29_manifest_keeps_execution_blocked() -> None:
    manifest = gate29._json(gate29.GATE29_MANIFEST)
    assert manifest["status"] == "GATE29_TRACE_ARCHITECTURE_COMPLETE_TECHNICAL_EXECUTION_BLOCKED"
    assert manifest["canonical_pair_execution_status"] == "NOT_EXECUTED"
    assert manifest["canonical_pair_authorization"] == "WAITING_GATE29_CANONICAL_PAIR_HUMAN_AUTHORIZATION"
    assert manifest["canonical_pair_runtime_verified_edge_count"] == 0


def test_gate29_scientific_flags_remain_false() -> None:
    manifest = gate29._json(gate29.GATE29_MANIFEST)
    assert manifest["scientific_jobs_run"] == 0
    assert manifest["disease_jobs_run"] == 0
    assert manifest["calibration_run"] is False
    assert manifest["model_fitting_run"] is False
    assert manifest["retuning"] is False
    assert manifest["dopamine_neuromodulation_implemented"] is False
