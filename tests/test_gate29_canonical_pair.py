from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

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


def test_snapshot_expected_files_have_matching_hashes_after_execution() -> None:
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    observed = []
    for record in manifest["files"]:
        path = canonical.SNAPSHOT_ROOT / record["relative_path"]
        assert path.is_file()
        assert canonical._sha256(path) == record["sha256"]
        assert path.stat().st_size == record["size_bytes"]
        observed.append(record)
    assert canonical._tree_fingerprint(observed) == manifest["canonical_brain_source_tree_sha256"]


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


def test_authorization_is_human_approved_and_binds_frozen_inputs() -> None:
    authorization = canonical._json(canonical.AUTHORIZATION_PATH)
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    assert authorization["authorized"] is True
    assert authorization["status"] == "GATE29_CANONICAL_PAIR_HUMAN_AUTHORIZED"
    assert authorization["authorized_execution_code_head"] == "e458c3f8f70c92c28313fa040e9089d44a4d7338"
    assert authorization["authorized_freeze_commit"] == "c42090c3d33cb423e0cef177117b50c1ddb6eaaa"
    assert authorization["authorized_pair_id"] == canonical.PAIR_ID
    assert authorization["authorized_seed"] == 9202
    assert authorization["authorized_jobs"] == 2
    assert authorization["baseline_job_authorized"] is True
    assert authorization["trace_job_authorized"] is True
    assert authorization["authorized_brain_source_tree_sha256"] == manifest["canonical_brain_source_tree_sha256"]
    assert authorization["authorized_runtime_commit"] == canonical.RUNTIME_COMMIT
    assert authorization["scientific_execution_authorized"] is False
    assert authorization["disease_execution_authorized"] is False
    assert authorization["calibration_authorized"] is False
    assert authorization["fitting_authorized"] is False
    assert authorization["retuning_authorized"] is False
    assert authorization["dopamine_authorized"] is False
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


def test_committed_evidence_records_completed_pair_without_scientific_jobs() -> None:
    manifest = canonical._json(
        canonical.ROOT
        / "experiments/gate_29f_canonical_pair_evidence/manifests/"
        "canonical_pair_evidence_manifest.json"
    )
    assert manifest["execution_state"] == "PAIR_COMPLETE"
    assert manifest["jobs_executed"] == 2
    assert manifest["baseline_returncode"] == 0
    assert manifest["trace_returncode"] == 0
    assert manifest["scientific_jobs"] == 0
    assert manifest["disease_jobs"] == 0


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


def test_design_preflight_is_closed_after_authorization_and_execution() -> None:
    result = canonical.canonical_pair_preflight()
    assert result["status"] == "GATE29_CANONICAL_PAIR_PREFLIGHT_BLOCKED"
    assert "canonical pair authorization must remain pending in design gate" in result["blockers"]
    assert result["gpu_execution"] is False
    assert result["simulation_execution"] is False
    assert result["scientific_jobs"] == 0
    assert result["holdout_role"] == "NOT_APPLICABLE_GATE29_ENGINEERING_PAIR"
    assert result["external_biological_evidence_accessed"] is False
    assert result["external_biological_holdout_evaluated"] is False


def test_completed_pair_cannot_be_executed_again(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(canonical, "_validate_authorization", lambda _: None)
    monkeypatch.setattr(
        canonical,
        "canonical_pair_preflight",
        lambda **_: {"status": "GATE29_CANONICAL_PAIR_PREFLIGHT_READY_FOR_HUMAN_AUTHORIZATION"},
    )
    with pytest.raises(canonical.CanonicalPairError, match="ALREADY_EXECUTED_OR_TERMINAL"):
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


def test_execution_snapshot_verification_does_not_need_original_source(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    monkeypatch.setattr(canonical, "SOURCE_ROOT", Path("E:/missing-mutated-original-source"))
    for record in manifest["files"]:
        path = canonical.SNAPSHOT_ROOT / record["relative_path"]
        assert canonical._sha256(path) == record["sha256"]


def test_snapshot_missing_file_fails_closed(tmp_path: Path) -> None:
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    result = canonical.verify_frozen_snapshot(snapshot, manifest)
    assert result["status"] == "BLOCKED"
    assert any(item.startswith("snapshot missing:") for item in result["blockers"])


def test_snapshot_hash_mutation_fails_closed(tmp_path: Path) -> None:
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    snapshot = tmp_path / "snapshot"
    for record in manifest["files"]:
        path = snapshot / record["relative_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"mutated")
    result = canonical.verify_frozen_snapshot(snapshot, manifest)
    assert result["status"] == "BLOCKED"
    assert any("snapshot hash mismatch:" in item for item in result["blockers"])


def test_snapshot_unexpected_file_fails_closed(tmp_path: Path) -> None:
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "unexpected.bin").write_bytes(b"unexpected")
    result = canonical.verify_frozen_snapshot(snapshot, manifest)
    assert result["status"] == "BLOCKED"
    assert "snapshot unexpected:unexpected.bin" in result["blockers"]


def test_freeze_is_fail_closed_before_commit_b(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(canonical, "FREEZE_PATH", tmp_path / "missing-freeze.json")
    result = canonical._execution_code_freeze_state()
    assert result["status"] == "GATE29_CANONICAL_PAIR_EXECUTION_CODE_FREEZE_MISSING"


def test_authorization_template_has_no_self_referential_head() -> None:
    authorization = canonical._json(canonical.AUTHORIZATION_PATH)
    assert "authorized_code_head" not in authorization
    assert authorization["authorized"] is True
    assert authorization["authorized_execution_code_head"] == "e458c3f8f70c92c28313fa040e9089d44a4d7338"


class _FakeProcess:
    def __init__(self) -> None:
        self.pid = 4242
        self.poll_count = 0
        self.returncode = 0
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        self.poll_count += 1
        return None if self.poll_count == 1 else self.returncode

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


def _guarded_job_fakes(monkeypatch: pytest.MonkeyPatch, snapshot: dict[str, float | str]) -> tuple[_FakeProcess, list[dict[str, object]]]:
    process = _FakeProcess()
    popen_calls: list[dict[str, object]] = []

    def fake_popen(command: list[str], **kwargs: object) -> _FakeProcess:
        popen_calls.append({"command": command, **kwargs})
        return process

    monkeypatch.setattr(canonical.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(canonical, "_gpu_snapshot", lambda: snapshot)
    monkeypatch.setattr(canonical, "_terminate_process_tree", lambda current: setattr(current, "terminated", True))
    monkeypatch.setattr(canonical.time, "sleep", lambda _: None)
    return process, popen_calls


def test_gpu_snapshot_uses_device_wide_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        canonical.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="81, 1024, 50\n", stderr=""),
    )
    snapshot = canonical._gpu_snapshot()
    assert snapshot["temperature_c"] == 81.0
    assert snapshot["memory_used_mb"] == 1024.0
    assert snapshot["memory_scope"] == "DEVICE_WIDE"


def test_guarded_job_at_81c_does_not_abort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    process, _ = _guarded_job_fakes(
        monkeypatch,
        {"temperature_c": 81.0, "memory_used_mb": 1024.0, "utilization_percent": 50.0, "memory_scope": "DEVICE_WIDE"},
    )
    result = canonical._run_guarded_canonical_job(["fake-runtime"], tmp_path / "job.log")
    assert result["returncode"] == 0
    assert result["max_observed_gpu_temperature_c"] == 81.0
    assert result["device_memory_scope"] == "DEVICE_WIDE"
    assert process.terminated is False


@pytest.mark.parametrize("temperature", [82.0, 82.1])
def test_guarded_job_at_or_above_82c_aborts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, temperature: float) -> None:
    process, _ = _guarded_job_fakes(
        monkeypatch,
        {"temperature_c": temperature, "memory_used_mb": 1024.0, "utilization_percent": 50.0, "memory_scope": "DEVICE_WIDE"},
    )
    with pytest.raises(canonical.CanonicalPairError, match="GATE29_CANONICAL_PAIR_ABORTED_GPU_TEMPERATURE"):
        canonical._run_guarded_canonical_job(["fake-runtime"], tmp_path / "job.log")
    assert process.terminated is True


def test_guarded_job_telemetry_failure_aborts_and_terminates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    process = _FakeProcess()
    monkeypatch.setattr(canonical.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(
        canonical,
        "_gpu_snapshot",
        lambda: (_ for _ in ()).throw(canonical.CanonicalPairError("GATE29_CANONICAL_PAIR_ABORTED_GPU_MONITOR_FAILURE")),
    )
    monkeypatch.setattr(canonical, "_terminate_process_tree", lambda current: setattr(current, "terminated", True))
    with pytest.raises(canonical.CanonicalPairError, match="GATE29_CANONICAL_PAIR_ABORTED_GPU_MONITOR_FAILURE"):
        canonical._run_guarded_canonical_job(["fake-runtime"], tmp_path / "job.log")
    assert process.terminated is True


def test_guarded_job_safety_contract_constants() -> None:
    assert canonical.GPU_MONITOR_INTERVAL_S == 1.0
    assert canonical.GPU_STOP_TEMPERATURE_C == 82.0


def test_pre_execution_gpu_check_rejects_unsafe_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(canonical, "_gpu_snapshot", lambda: {"temperature_c": 82.0, "memory_used_mb": 1.0, "utilization_percent": 0.0, "memory_scope": "DEVICE_WIDE"})
    with pytest.raises(canonical.CanonicalPairError, match="GATE29_CANONICAL_PAIR_ABORTED_GPU_TEMPERATURE"):
        canonical._pre_execution_gpu_check()


def test_baseline_failure_prevents_trace_and_is_terminal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    auth_path = tmp_path / "authorization.json"
    output_root = tmp_path / "outputs"
    auth_path.write_text(json.dumps({"authorized": True}), encoding="utf-8")
    monkeypatch.setattr(canonical, "AUTHORIZATION_PATH", auth_path)
    monkeypatch.setattr(canonical, "CANONICAL_OUTPUT_ROOT", output_root)
    monkeypatch.setattr(canonical, "_validate_authorization", lambda _: None)
    monkeypatch.setattr(canonical, "canonical_pair_preflight", lambda **_: {"status": "GATE29_CANONICAL_PAIR_PREFLIGHT_READY_FOR_HUMAN_AUTHORIZATION"})
    monkeypatch.setattr(canonical, "_pre_execution_gpu_check", lambda: {"status": "PASS"})
    canonical._create_output_skeleton()
    calls: list[bool] = []

    def fail_baseline(*, instrumentation_enabled: bool, **kwargs: object) -> dict[str, object]:
        calls.append(instrumentation_enabled)
        raise canonical.CanonicalPairError("GATE29_CANONICAL_PAIR_ABORTED_GPU_TEMPERATURE")

    monkeypatch.setattr(canonical, "_run_canonical_pair_job", fail_baseline)
    with pytest.raises(canonical.CanonicalPairError):
        canonical.execute_authorized_canonical_pair()
    state = canonical._json(output_root / "execution_state/status.json")
    assert calls == [False]
    assert state["state"] == "BASELINE_FAILED"
    assert state["retry"] is False


def test_trace_failure_preserves_baseline_and_disallows_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    auth_path = tmp_path / "authorization.json"
    output_root = tmp_path / "outputs"
    auth_path.write_text(json.dumps({"authorized": True}), encoding="utf-8")
    monkeypatch.setattr(canonical, "AUTHORIZATION_PATH", auth_path)
    monkeypatch.setattr(canonical, "CANONICAL_OUTPUT_ROOT", output_root)
    monkeypatch.setattr(canonical, "_validate_authorization", lambda _: None)
    monkeypatch.setattr(canonical, "canonical_pair_preflight", lambda **_: {"status": "GATE29_CANONICAL_PAIR_PREFLIGHT_READY_FOR_HUMAN_AUTHORIZATION"})
    monkeypatch.setattr(canonical, "_pre_execution_gpu_check", lambda: {"status": "PASS"})
    canonical._create_output_skeleton()
    calls: list[bool] = []

    def fail_trace(*, instrumentation_enabled: bool, output: Path, **kwargs: object) -> dict[str, object]:
        calls.append(instrumentation_enabled)
        if not instrumentation_enabled:
            output.mkdir(parents=True, exist_ok=True)
            (output / "baseline.json").write_text("{}", encoding="utf-8")
            return {"job": "baseline", "returncode": 0}
        raise canonical.CanonicalPairError("GATE29_CANONICAL_PAIR_ABORTED_GPU_MONITOR_FAILURE")

    monkeypatch.setattr(canonical, "_run_canonical_pair_job", fail_trace)
    with pytest.raises(canonical.CanonicalPairError):
        canonical.execute_authorized_canonical_pair()
    state = canonical._json(output_root / "execution_state/status.json")
    assert calls == [False, True]
    assert state["state"] == "TRACE_FAILED"
    assert state["retry"] is False
    assert (output_root / "baseline/baseline.json").is_file()
    with pytest.raises(canonical.CanonicalPairError, match="ALREADY_EXECUTED_OR_TERMINAL"):
        canonical.execute_authorized_canonical_pair()
    assert calls == [False, True]


def test_pair_has_exactly_two_jobs_and_no_automatic_retry() -> None:
    assert set(canonical._job_commands()) == {"baseline", "trace"}
    assert canonical._json(canonical.DESIGN_PATH)["automatic_retry"] is False


def test_snapshot_does_not_include_cache_or_output_names() -> None:
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    for record in manifest["files"]:
        assert not any(part in {".git", ".venv", "__pycache__", ".pytest_cache", "cache", "logs", "videos", "outputs", "temporary"} for part in Path(record["relative_path"]).parts)


def test_runtime_source_is_not_the_canonical_snapshot() -> None:
    manifest = canonical._json(canonical.SOURCE_MANIFEST)
    assert manifest["source_root_logical"] == "external/fly-brain"
    assert manifest["snapshot_root_logical"] != manifest["source_root_logical"]


def test_gate29_design_manifest_is_historical_and_gate29f_locks_result() -> None:
    design_manifest = gate29._json(gate29.GATE29_MANIFEST)
    assert design_manifest["status"] == "GATE29_CANONICAL_PAIR_EXECUTION_FROZEN"
    assert design_manifest["canonical_pair_runtime_verified_edge_count"] == 0
    result_manifest = gate29._json(
        gate29.ROOT
        / "experiments/gate_29f_canonical_pair_evidence/manifests/"
        "canonical_pair_evidence_manifest.json"
    )
    assert result_manifest["status"] == "GATE29F_CANONICAL_PAIR_EVIDENCE_LOCKED"
    assert result_manifest["execution_state"] == "PAIR_COMPLETE"


def test_gate29_scientific_flags_remain_false() -> None:
    manifest = gate29._json(gate29.GATE29_MANIFEST)
    assert manifest["scientific_jobs_run"] == 0
    assert manifest["disease_jobs_run"] == 0
    assert manifest["calibration_run"] is False
    assert manifest["model_fitting_run"] is False
    assert manifest["retuning"] is False
    assert manifest["dopamine_neuromodulation_implemented"] is False
