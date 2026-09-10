from __future__ import annotations

from types import SimpleNamespace

import pytest

from drosophila_pd_neural.causal_trace.schema import (
    NONPERTURBATION_COMPARISONS,
    TRACE_ATOL,
    TRACE_RTOL,
)
from drosophila_pd_neural.causal_trace.validation import (
    TraceValidationError,
    compare_trace_arrays,
)
from scripts import run_gate29_neural_causal_trace as gate29


def test_gate28b_is_closed_and_historical_inventory_is_preserved() -> None:
    closure = gate29.audit_gate28b_closure()
    assert closure["status"] == "GATE28B_CLOSURE_PASS"
    assert closure["gate28b_closed"] is True
    assert closure["historical_inventory_preserved"] is True
    assert closure["paper_assay_equivalence_established"] is False


def test_gate29_manifest_is_computational_only() -> None:
    manifest = gate29._json(gate29.GATE29_MANIFEST)
    assert manifest["trace_scope"] == "COMPUTATIONAL_EXECUTION_PATH_TRACE"
    assert manifest["biological_vnc_neural_model_status"] == "NOT_ESTABLISHED"
    assert manifest["dopamine_neuromodulation_implemented"] is False
    assert manifest["scientific_jobs_run"] == 0
    assert manifest["disease_jobs_run"] == 0
    assert manifest["calibration_run"] is False
    assert manifest["model_fitting_run"] is False
    assert manifest["retuning"] is False
    assert manifest["baseline_execution_locked"] is True
    assert manifest["trace_runner_optimization_status"] == "STATICALLY_QUALIFIED"
    assert manifest["trace_execution_authorization"] == "WAITING_HUMAN_AUTHORIZATION"
    assert manifest["runtime_trace_evidence_available"] is False


def test_gate29_runtime_contract_is_locked() -> None:
    assert gate29.RUNTIME_COMMIT == "655e854544e3d814dfe422883ff0de66b619d6c1"
    assert gate29.HEALTHY_CHECKPOINT_SHA256 == (
        "d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691"
    )
    assert gate29.TECHNICAL_SEED == 9201
    assert gate29.TECHNICAL_DURATION_S == 0.5
    assert gate29.TECHNICAL_STEPS == 5000
    assert gate29.MAX_TECHNICAL_JOBS == 2


def test_execution_path_and_feedback_loop_are_explicit() -> None:
    audit = gate29._json(gate29.RUNTIME_AUDIT)
    operations = [item["operation"].split("(", 1)[0] for item in audit["operations"]]
    assert operations == [
        "brain.step",
        "brain.get_dn_spikes",
        "decoder.update",
        "bridge.compute_drive",
        "HybridControllerObservation.from_sim",
        "controller.step",
        "apply_locomotion_action",
        "simulation.step",
        "recorder.record",
    ]
    assert operations.index("decoder.update") < operations.index("bridge.compute_drive")
    assert operations.index("apply_locomotion_action") < operations.index("simulation.step")
    assert operations.index("simulation.step") < operations.index("recorder.record")
    graph = gate29._json(gate29.ROOT / "experiments/gate_29_neural_causal_trace/manifests/closed_loop_dependency_graph.json")
    assert graph["closed_loop"] is True
    assert graph["biological_causality_established"] is False


def test_all_registered_edges_reject_biological_causality() -> None:
    registry = gate29._json(gate29.EDGE_REGISTRY)
    assert registry["biological_causality_established"] is False
    assert all(edge["biological_causality_established"] is False for edge in registry["edges"])


def test_edges_are_not_runtime_verified_before_trace() -> None:
    registry = gate29._json(gate29.EDGE_REGISTRY)
    assert sum(bool(edge["runtime_verified"]) for edge in registry["edges"]) == 0
    assert sum(bool(edge["source_code_verified"]) for edge in registry["edges"]) == 11
    assay_edge = next(edge for edge in registry["edges"] if edge["edge_id"].startswith("THORAX_"))
    assert assay_edge["source_basis"] == "SOURCE_CODE+INHERITED_GATE28B_ENGINEERING_VALIDATION"
    assert assay_edge["runtime_trace_required"] is False


def test_signal_inventory_keeps_unavailable_full_brain_state_explicit() -> None:
    inventory = gate29._json(gate29.SIGNAL_INVENTORY)
    full_state = next(item for item in inventory["signals"] if item["signal_name"] == "brain_full_neuron_state")
    assert full_state["export_status"] == "NOT_EXPORTED_API_UNVERIFIED"
    assert full_state["public_api_verified"] is False


def test_controller_layer_separates_engineered_cpg_from_biological_vnc() -> None:
    interpretation = gate29._json(gate29.ROOT / "experiments/gate_29_neural_causal_trace/manifests/controller_layer_interpretation.json")
    assert interpretation["engineered_locomotor_cpg_controller"]["status"] == "PRESENT"
    assert interpretation["biologically_grounded_vnc_neural_model"]["status"] == "NOT_ESTABLISHED"


def test_baseline_is_locked_and_hashes_are_current() -> None:
    result = gate29.verify_baseline_execution_lock()
    assert result["status"] == "GATE29_BASELINE_EXECUTION_LOCK_PASS"
    assert result["baseline_rerun_allowed"] is False
    assert result["baseline_hashes"]["rollout.npz"]


def test_trace_authorization_is_pending_and_trace_only_is_guarded() -> None:
    authorization = gate29._json(gate29.TRACE_AUTHORIZATION)
    assert authorization["authorized"] is False
    assert authorization["authorized_jobs"] == 1
    assert authorization["trace_only"] is True
    paths = gate29._resolve_paths(gate29._parser().parse_args([]))
    with pytest.raises(gate29.Gate29Error, match="HUMAN_AUTHORIZATION_REQUIRED"):
        gate29.execute_authorized_trace_only(paths)


def test_trace_only_command_has_one_job_and_no_baseline_command() -> None:
    paths = gate29._resolve_paths(gate29._parser().parse_args([]))
    command = gate29._prepare_trace_only_command(paths, paths["output_root"] / "trace_attempt_02")
    assert command.count("--internal-trace") == 1
    assert "--execute-paired-technical-trace" not in command
    assert "--condition" not in command


def test_trace_attempt_provenance_preserves_aborted_attempt() -> None:
    provenance = gate29._json(gate29.TRACE_ATTEMPT_PROVENANCE)
    assert provenance["attempt_01"]["status"] == "ABORTED_BEFORE_TRACE_ARTIFACT"
    assert provenance["attempt_01"]["preserved"] is True
    assert provenance["attempt_02"]["status"] == "NOT_EXECUTED"


def test_optimization_qualification_is_static_and_non_gpu() -> None:
    qualification = gate29._json(gate29.TRACE_OPTIMIZATION_QUALIFICATION)
    assert qualification["status"] == "GATE29_TRACE_RUNNER_OPTIMIZATION_STATICALLY_QUALIFIED"
    assert qualification["current_tracer_scope"] == "AUDITED_RUNTIME_SCRIPT_ONLY"
    assert qualification["non_runtime_line_events"] == 0
    assert qualification["gpu_execution_in_qualification"] is False
    assert qualification["real_simulation_execution"] is False


def test_collector_traces_only_the_runtime_frame() -> None:
    collector = gate29._RuntimeTraceCollector(gate29.ROOT / "scripts/run_brain_body_rollout.py")
    runtime_code = SimpleNamespace(co_filename=str(gate29.ROOT / "scripts/run_brain_body_rollout.py"))
    other_code = SimpleNamespace(co_filename=str(gate29.ROOT / "tests/test_gate29_neural_causal_trace.py"))
    assert collector(SimpleNamespace(f_code=runtime_code), "call", None) is collector
    assert collector(SimpleNamespace(f_code=other_code), "call", None) is None
    assert collector(SimpleNamespace(f_code=runtime_code, f_lineno=999), "line", None) is collector
    assert collector(SimpleNamespace(f_code=other_code, f_lineno=1), "line", None) is None
    assert collector.non_runtime_line_events == 1


def test_collector_capture_guard_and_array_copy_are_non_mutating() -> None:
    collector = gate29._RuntimeTraceCollector(gate29.ROOT / "scripts/run_brain_body_rollout.py")
    collector._inside_capture = True
    collector._capture(SimpleNamespace(f_locals={}), 317)
    assert collector.current is None
    source = [1.0, 2.0]
    copied = gate29.np.asarray(source, dtype=float).copy()
    copied[0] = 9.0
    assert source == [1.0, 2.0]


def test_only_audited_step_lines_trigger_capture() -> None:
    collector = gate29._RuntimeTraceCollector(gate29.ROOT / "scripts/run_brain_body_rollout.py")
    assert 317 in collector.STEP_LINES
    assert 319 in collector.STEP_LINES
    assert 341 in collector.STEP_LINES
    assert 999 not in collector.STEP_LINES


def test_trace_contract_uses_post_step_timestamp_and_frozen_tolerance() -> None:
    assert TRACE_ATOL == 1e-12
    assert TRACE_RTOL == 0.0
    assert ("timestamp_s", "post_time_s", False) in NONPERTURBATION_COMPARISONS
    assert ("contact_found", "post_contact_found", True) in NONPERTURBATION_COMPARISONS


def test_trace_comparison_fails_closed_on_float_mismatch_and_exact_discrete_mismatch() -> None:
    baseline = {"x": [1.0, 2.0], "contact": [True, False]}
    traced = {"y": [1.0 + 1e-10, 2.0], "contact_trace": [True, True]}
    result = compare_trace_arrays(
        baseline,
        traced,
        (("x", "y", False), ("contact", "contact_trace", True)),
    )
    assert result["status"] == "TRACE_OBSERVATION_NONPERTURBING_FAIL"
    assert result["comparisons"]["x"]["passed"] is False
    assert result["comparisons"]["contact"]["passed"] is False


def test_trace_comparison_passes_at_locked_float_tolerance() -> None:
    result = compare_trace_arrays(
        {"x": [1.0, 2.0]},
        {"y": [1.0 + 1e-13, 2.0]},
        (("x", "y", False),),
    )
    assert result["status"] == "TRACE_OBSERVATION_NONPERTURBING_PASS"


def test_runtime_cli_rejects_disease_and_defaults_to_no_execution() -> None:
    parser = gate29._parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--disease", "parkin"])
    assert gate29.main([]) == 0


def test_reproducibility_scope_excludes_raw_trace_npz() -> None:
    paths = [path.as_posix() for path in gate29._gate29_reproducibility_paths()]
    assert not any(path.endswith("trace_arrays.npz") for path in paths)
    assert all("gate29_technical_outputs" not in path for path in paths)
    verification = gate29.verify_reproducibility_inventory()
    assert verification["status"] == "GATE29_REPRODUCIBILITY_PASS"
    assert verification["mismatches"] == []


def test_report_contains_claim_lock_and_human_review_boundary() -> None:
    report = (gate29.ROOT / "docs/research_design/gate29_neural_causal_trace_report.md").read_text(encoding="utf-8")
    assert "computational execution-path trace" in report
    assert "biological causal" in report
    assert "WAITING_GATE29_HUMAN_REVIEW" in report
    assert "HUMAN_REVIEW_GATE29_NEURAL_CAUSAL_TRACE" in report
