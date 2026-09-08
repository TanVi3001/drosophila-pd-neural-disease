from __future__ import annotations

import json

from scripts.audit_gate24e_storage_attempt03 import (
    ATTEMPT_04,
    FAILURE_MANIFEST,
    LOG,
    REPORT,
    TOP_LEVEL_MANIFEST,
    parse_log,
)
from scripts.audit_gate24e_runtime_amendment import _attempt03_failure_recorded


FAILURE = json.loads(FAILURE_MANIFEST.read_text(encoding="utf-8"))
HISTORY = json.loads(TOP_LEVEL_MANIFEST.read_text(encoding="utf-8"))
LOG_EVIDENCE = parse_log(LOG.read_text(encoding="utf-8", errors="replace"))


def test_01_progress_markers_prove_simulation_started() -> None:
    assert LOG_EVIDENCE["progress_markers"] == [20000, 40000]
    assert FAILURE["simulation_started"] is True


def test_02_cuda_evidence_proves_gpu_simulation_started() -> None:
    assert LOG_EVIDENCE["gpu_simulation_started"] is True
    assert FAILURE["gpu_simulation_started"] is True


def test_03_keyboard_interrupt_is_classified_as_technical() -> None:
    assert LOG_EVIDENCE["keyboard_interrupt_observed"] is True
    assert FAILURE["exception"] == "KeyboardInterrupt"
    assert FAILURE["failure_type"] == "TECHNICAL_INTERRUPTION"
    assert FAILURE["failure_stage"] == "DURING_SIMULATION"


def test_04_missing_completion_marker_means_not_completed() -> None:
    assert LOG_EVIDENCE["completion_marker_observed"] is False
    assert FAILURE["simulation_completed"] is False


def test_05_last_confirmed_progress_is_40000() -> None:
    assert FAILURE["requested_steps"] == 100000
    assert FAILURE["last_confirmed_progress_steps"] == 40000


def test_06_manifest_does_not_claim_exact_executed_steps() -> None:
    assert FAILURE["exact_executed_steps_known"] is False
    assert FAILURE["exact_executed_steps"] is None
    assert "executed_steps" not in FAILURE


def test_07_storage_estimates_are_invalid() -> None:
    assert FAILURE["storage_measurements_valid"] is False
    assert FAILURE["storage_qualification_valid"] is False
    assert FAILURE["final_artifact_estimation_allowed"] is False


def test_08_attempt03_is_consumed() -> None:
    assert FAILURE["attempt_03_consumed"] is True
    assert HISTORY["attempt_03"]["attempt_consumed"] is True


def test_09_attempt03_retry_is_forbidden() -> None:
    assert FAILURE["attempt_03_retry_allowed"] is False
    assert FAILURE["automatic_retry"] is False
    assert HISTORY["attempt_03"]["retry_allowed"] is False


def test_10_attempt04_is_consumed_and_not_authorized_for_retry() -> None:
    assert FAILURE["attempt_04_authorized"] is False
    assert HISTORY["attempt_04_authorized"] is False
    assert ATTEMPT_04.is_dir()
    assert (ATTEMPT_04 / "manifests/attempt_04_execution.json").is_file()


def test_11_scientific_jobs_remain_zero() -> None:
    assert FAILURE["scientific_jobs_executed"] == 0
    assert HISTORY["scientific_jobs_executed"] == 0


def test_12_holdout_remains_sealed() -> None:
    assert FAILURE["holdout"] == "SEALED"
    assert FAILURE["holdout_opened"] is False
    assert HISTORY["holdout"] == "SEALED"


def test_13_interrupted_probe_has_no_scientific_interpretation() -> None:
    assert FAILURE["scientific_results_generated"] is False
    assert FAILURE["scientific_analysis_allowed"] is False
    assert FAILURE["probe_included_in_scientific_analysis"] is False
    assert "không có scientific result" in REPORT.read_text(encoding="utf-8").casefold()


def test_14_prior_attempts_are_preserved_with_attempt04_estimate() -> None:
    assert HISTORY["attempt_01"]["failure_stage"] == "PRE_SIMULATION_CLI_ARGUMENT_PARSE"
    assert HISTORY["attempt_02"]["failure_stage"] == "POST_SIMULATION_EXPORT_MEMORY_ERROR"
    assert HISTORY["current_qualification_status"] == "WAITING_GATE24E_STORAGE_CAPACITY"
    assert HISTORY["current_qualification_reason"] == "FREE_AFTER_NOT_GREATER_THAN_REQUIRED"
    assert HISTORY["current_estimate_source"] == "attempt_04"
    assert HISTORY["attempt_04"]["valid_for_storage_estimation"] is True


def test_runtime_amendment_auditor_recognizes_recorded_failure() -> None:
    assert _attempt03_failure_recorded() is True
