"""Audit authorization readiness for one new Gate24E technical probe.

This auditor is fail-closed and does not create an attempt directory, launch a
subprocess, run a simulation, open the holdout, or authorize the scientific
batch.
"""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re
import sys
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import audit_gate24e_runtime_amendment

ROOT = Path(__file__).resolve().parents[1]
ATTEMPT_03_MANIFEST = (
    ROOT
    / "experiments/gate_24e_storage_probe/attempt_03/manifests/storage_qualification.json"
)
STORAGE_HISTORY = ROOT / "experiments/gate_24e_storage_probe/manifests/storage_qualification.json"
FIREWALL = (
    ROOT
    / "experiments/gate_24_prospective_validation/manifests/holdout_firewall_manifest.json"
)
SCIENTIFIC_EXECUTION = (
    ROOT
    / "experiments/gate_24e_blinded_parkin_prediction/manifests/execution_manifest.json"
)
SIGNOFF = (
    ROOT
    / "research/validation/prospective/gate24e_attempt04_authorization_reviewer_signoff.json"
)
AUTHORIZATION = ROOT / "experiments/gate_24e_storage_probe/manifests/attempt04_authorization.json"
ATTEMPT_04 = ROOT / "experiments/gate_24e_storage_probe/attempt_04"
EXPECTED_RUNTIME_ROOT = ROOT.parent / "drosophila-pd-flygym-gate24-memorysafe-clean"

PLATFORM_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"
ARTIFACT_PROFILE = "GATE24E_MEMORY_SAFE"
PROBE_SEED = 9001
SCIENTIFIC_SEEDS = (0, 1, 2, 3, 4)
STEPS = 100000
DURATION_S = 10.0
DEVICE = "cuda"


class Attempt04AuthorizationError(RuntimeError):
    """Raised when required authorization evidence cannot be read."""


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Attempt04AuthorizationError(f"Missing required JSON: {path}") from exc
    if not isinstance(value, dict):
        raise Attempt04AuthorizationError(f"Expected JSON object: {path}")
    return value


def _valid_review_date(value: object) -> bool:
    text = str(value or "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return False
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _is_placeholder(value: object) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    normalized = text.upper().replace("-", "_").replace(" ", "_")
    markers = (
        "TODO",
        "TBD",
        "PENDING",
        "PLACEHOLDER",
        "REVIEWER_1",
        "REVIEWER_2",
        "REVIEWER_NAME",
        "TEN_NGUOI",
        "TÊN_NGƯỜI",
        "UNKNOWN",
    )
    return any(marker in normalized for marker in markers)


def _exact_blockers(document: dict[str, Any], expected: dict[str, Any], label: str) -> list[str]:
    return [
        f"{label} mismatch: {key}"
        for key, value in expected.items()
        if document.get(key) != value
    ]


def _attempt03_blockers(failure: dict[str, Any], history: dict[str, Any]) -> list[str]:
    blockers = _exact_blockers(
        failure,
        {
            "status": "STORAGE_PROBE_ATTEMPT_03_TECHNICAL_FAILURE",
            "failure_type": "TECHNICAL_INTERRUPTION",
            "failure_stage": "DURING_SIMULATION",
            "exception": "KeyboardInterrupt",
            "simulation_started": True,
            "gpu_simulation_started": True,
            "requested_steps": STEPS,
            "last_confirmed_progress_steps": 40000,
            "exact_executed_steps_known": False,
            "exact_executed_steps": None,
            "simulation_completed": False,
            "storage_measurements_valid": False,
            "storage_qualification_valid": False,
            "attempt_03_consumed": True,
            "attempt_03_retry_allowed": False,
            "automatic_retry": False,
            "attempt_04_authorized": False,
            "scientific_jobs_executed": 0,
            "scientific_results_generated": False,
            "holdout": "SEALED",
            "holdout_opened": False,
        },
        "attempt_03 failure record",
    )
    blockers.extend(
        _exact_blockers(
            history,
            {
                "current_qualification_status": "GATE24E_STORAGE_NOT_QUALIFIED",
                "current_qualification_reason": "NO_VALID_COMPLETED_STORAGE_PROBE",
                "storage_measurements_valid": False,
                "storage_qualification_valid": False,
                "scientific_jobs_executed": 0,
                "holdout": "SEALED",
                "holdout_opened": False,
                "automatic_retry": False,
                "attempt_04_authorized": False,
            },
            "storage history",
        )
    )
    attempt = history.get("attempt_03") or {}
    blockers.extend(
        _exact_blockers(
            attempt,
            {
                "status": "STORAGE_PROBE_ATTEMPT_03_TECHNICAL_FAILURE",
                "failure_type": "TECHNICAL_INTERRUPTION",
                "failure_stage": "DURING_SIMULATION",
                "simulation_started": True,
                "simulation_completed": False,
                "last_confirmed_progress_steps": 40000,
                "exact_executed_steps_known": False,
                "valid_for_storage_estimation": False,
                "attempt_consumed": True,
                "retry_allowed": False,
            },
            "storage history attempt_03",
        )
    )
    return blockers


def _review_state(signoff: dict[str, Any]) -> tuple[str, list[str]]:
    blockers = _exact_blockers(
        signoff,
        {
            "schema_version": "gate24e-attempt04-authorization-review-v1",
            "study_id": "parkin_prospective_validation",
            "previous_attempt": "attempt_03",
            "previous_attempt_status": "STORAGE_PROBE_ATTEMPT_03_TECHNICAL_FAILURE",
            "previous_failure_type": "TECHNICAL_INTERRUPTION",
            "previous_failure_stage": "DURING_SIMULATION",
            "previous_exception": "KeyboardInterrupt",
            "previous_attempt_consumed": True,
            "previous_attempt_retry_allowed": False,
            "new_attempt": "attempt_04",
            "probe_seed": PROBE_SEED,
            "steps": STEPS,
            "device": DEVICE,
            "platform_commit": PLATFORM_COMMIT,
            "artifact_profile": ARTIFACT_PROFILE,
            "scientific_contract_changed": False,
            "holdout_opened": False,
            "scientific_jobs_executed": 0,
            "scientific_batch_authorized": False,
        },
        "attempt_04 reviewer signoff",
    )
    reviewers = [str(signoff.get(key, "")).strip() for key in ("reviewer_1", "reviewer_2")]
    if any(_is_placeholder(value) for value in reviewers):
        blockers.append("reviewer placeholders are forbidden")
    if all(reviewers) and reviewers[0].casefold() == reviewers[1].casefold():
        blockers.append("two distinct human reviewers are required")

    pending = (
        signoff.get("status") == "WAITING_ATTEMPT04_AUTHORIZATION_REVIEW"
        and signoff.get("decision") == "PENDING_HUMAN_REVIEW"
    )
    approved = (
        signoff.get("status") == "ATTEMPT04_AUTHORIZATION_APPROVED"
        and signoff.get("decision") == "APPROVED_FOR_ONE_NEW_GATE24E_STORAGE_ATTEMPT"
    )
    if pending:
        if signoff.get("attempt_04_authorized") is not False:
            blockers.append("pending review cannot authorize attempt_04")
        if signoff.get("review_date") and not _valid_review_date(signoff.get("review_date")):
            blockers.append("partially entered review_date is invalid")
        return "PENDING", blockers
    if approved:
        if not all(reviewers):
            blockers.append("approved attempt_04 requires two real human reviewers")
        if not _valid_review_date(signoff.get("review_date")):
            blockers.append("approved attempt_04 requires a valid ISO review_date")
        if signoff.get("attempt_04_authorized") is not True:
            blockers.append("approved review must explicitly authorize attempt_04")
        return "APPROVED", blockers
    blockers.append("attempt_04 review decision is neither pending nor approved")
    return "INVALID", blockers


def _authorization_blockers(
    authorization: dict[str, Any], review_state: str
) -> tuple[str, list[str]]:
    blockers = _exact_blockers(
        authorization,
        {
            "schema_version": "gate24e-storage-attempt04-authorization-v1",
            "previous_attempt": "attempt_03",
            "previous_attempt_consumed": True,
            "previous_attempt_retry_allowed": False,
            "authorization_type": "NEW_TECHNICAL_ATTEMPT",
            "attempt_id": "attempt_04",
            "probe_seed": PROBE_SEED,
            "steps": STEPS,
            "duration_s": DURATION_S,
            "device": DEVICE,
            "platform_commit": PLATFORM_COMMIT,
            "artifact_profile": ARTIFACT_PROFILE,
            "automatic_retry": False,
            "scientific_analysis_allowed": False,
            "scientific_jobs_authorized": False,
            "scientific_batch_authorized": False,
            "holdout_access_allowed": False,
            "tuning_allowed": False,
            "parameter_change_allowed": False,
            "seed_change_allowed": False,
            "steps_change_allowed": False,
        },
        "attempt_04 authorization manifest",
    )
    if review_state == "PENDING":
        if authorization.get("status") != "WAITING_HUMAN_REVIEW":
            blockers.append("pending authorization manifest has an invalid status")
        if authorization.get("attempt_04_authorized") is not False:
            blockers.append("pending authorization manifest cannot authorize attempt_04")
        return "PENDING", blockers
    if review_state == "APPROVED":
        if authorization.get("status") != "ATTEMPT04_AUTHORIZATION_APPROVED":
            blockers.append("approved signoff requires a reviewed authorization manifest")
        if authorization.get("attempt_04_authorized") is not True:
            blockers.append("authorization manifest does not authorize attempt_04")
        return "APPROVED", blockers
    return "INVALID", blockers


def _runtime_blockers(runtime: dict[str, Any]) -> list[str]:
    blockers = _exact_blockers(
        runtime,
        {
            "status": "ATTEMPT_03_TECHNICAL_FAILURE_RECORDED",
            "runtime_review_state": "APPROVED",
            "amended_platform_commit": PLATFORM_COMMIT,
            "artifact_profile": ARTIFACT_PROFILE,
            "scientific_contract_changed": False,
            "scientific_batch_authorized": False,
            "holdout": "SEALED",
            "scientific_jobs_executed": 0,
            "attempt_03_failure_recorded": True,
        },
        "runtime amendment audit",
    )
    if runtime.get("blockers") != []:
        blockers.append("runtime amendment audit has blockers")
    evidence = runtime.get("runtime") or {}
    if evidence.get("head") != PLATFORM_COMMIT:
        blockers.append("amended runtime HEAD does not match the locked commit")
    if evidence.get("clean") is not True:
        blockers.append("amended runtime worktree is not clean")
    runtime_root = evidence.get("runtime_root")
    if not runtime_root or Path(str(runtime_root)).resolve() != EXPECTED_RUNTIME_ROOT.resolve():
        blockers.append("amended runtime path does not match the reviewed worktree")
    return blockers


def audit_documents(
    *,
    failure: dict[str, Any],
    history: dict[str, Any],
    firewall: dict[str, Any],
    execution: dict[str, Any],
    signoff: dict[str, Any],
    authorization: dict[str, Any],
    runtime: dict[str, Any],
    attempt04_exists: bool,
) -> dict[str, Any]:
    """Audit already-loaded evidence without filesystem or process side effects."""
    blockers = _attempt03_blockers(failure, history)
    blockers.extend(_runtime_blockers(runtime))
    blockers.extend(
        _exact_blockers(
            firewall,
            {
                "status": "SEALED",
                "no_numeric_holdout_import": True,
                "no_holdout_tuning": True,
                "gpu_executed": False,
                "simulation_executed": False,
            },
            "holdout firewall",
        )
    )
    blockers.extend(
        _exact_blockers(
            execution,
            {
                "status": "NOT_EXECUTED",
                "executed_job_count": 0,
                "gpu_jobs_executed": 0,
                "simulation_jobs_executed": 0,
                "holdout_status": "SEALED",
                "holdout_opened": False,
            },
            "scientific execution manifest",
        )
    )
    review_state, review_blockers = _review_state(signoff)
    blockers.extend(review_blockers)
    authorization_state, authorization_blockers = _authorization_blockers(
        authorization, review_state
    )
    blockers.extend(authorization_blockers)
    if PROBE_SEED in SCIENTIFIC_SEEDS:
        blockers.append("technical seed overlaps the scientific seed set")
    attempt04_history = history.get("attempt_04")
    attempt04_recorded = isinstance(attempt04_history, dict) and bool(attempt04_history)
    if attempt04_recorded:
        blockers.append("attempt_04 is already recorded as consumed in storage history")
    if attempt04_exists:
        blockers.append("attempt_04 output directory already exists")

    if blockers:
        status = "GATE24E_ATTEMPT04_AUTHORIZATION_INVALID"
    elif review_state == "PENDING" and authorization_state == "PENDING":
        status = "WAITING_GATE24E_ATTEMPT04_HUMAN_REVIEW"
    elif review_state == "APPROVED" and authorization_state == "APPROVED":
        status = "READY_FOR_GATE24E_ATTEMPT04"
    else:
        status = "GATE24E_ATTEMPT04_AUTHORIZATION_INVALID"

    return {
        "schema_version": "gate24e-attempt04-authorization-audit-v1",
        "status": status,
        "previous_attempt_status": failure.get("status"),
        "previous_failure_type": failure.get("failure_type"),
        "attempt_03_consumed": failure.get("attempt_03_consumed"),
        "attempt_03_retry_allowed": failure.get("attempt_03_retry_allowed"),
        "attempt_03_storage_valid": failure.get("storage_qualification_valid"),
        "attempt_04_exists": attempt04_exists,
        "attempt_04_recorded": attempt04_recorded,
        "attempt_04_consumed": attempt04_exists or attempt04_recorded,
        "attempt_04_authorized": status == "READY_FOR_GATE24E_ATTEMPT04",
        "attempt_04_seed": authorization.get("probe_seed"),
        "attempt_04_steps": authorization.get("steps"),
        "runtime_commit": runtime.get("amended_platform_commit"),
        "artifact_profile": runtime.get("artifact_profile"),
        "scientific_contract_changed": runtime.get("scientific_contract_changed"),
        "scientific_jobs_executed": execution.get("executed_job_count"),
        "scientific_batch_authorized": False,
        "holdout": firewall.get("status"),
        "reviewer_1": signoff.get("reviewer_1", ""),
        "reviewer_2": signoff.get("reviewer_2", ""),
        "review_date": signoff.get("review_date", ""),
        "review_state": review_state,
        "authorization_manifest_state": authorization_state,
        "blockers": blockers,
        "gpu_executed_by_audit": False,
        "simulation_executed_by_audit": False,
        "next_allowed_action": (
            "HUMAN_REVIEW_GATE24E_ATTEMPT04_AUTHORIZATION"
            if status == "WAITING_GATE24E_ATTEMPT04_HUMAN_REVIEW"
            else "IMPLEMENT_SINGLE_USE_GATE24E_ATTEMPT04_RUNNER"
            if status == "READY_FOR_GATE24E_ATTEMPT04"
            else "STOP_AND_REVIEW_ATTEMPT04_AUTHORIZATION"
        ),
    }


def audit(runtime_root: Path | None = None) -> dict[str, Any]:
    runtime = audit_gate24e_runtime_amendment.audit(runtime_root)
    return audit_documents(
        failure=_json(ATTEMPT_03_MANIFEST),
        history=_json(STORAGE_HISTORY),
        firewall=_json(FIREWALL),
        execution=_json(SCIENTIFIC_EXECUTION),
        signoff=_json(SIGNOFF),
        authorization=_json(AUTHORIZATION),
        runtime=runtime,
        attempt04_exists=ATTEMPT_04.exists(),
    )


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    try:
        result = audit()
    except (Attempt04AuthorizationError, OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "status": "GATE24E_ATTEMPT04_AUTHORIZATION_INVALID",
            "error": str(exc),
            "gpu_executed_by_audit": False,
            "simulation_executed_by_audit": False,
        }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in {
        "WAITING_GATE24E_ATTEMPT04_HUMAN_REVIEW",
        "READY_FOR_GATE24E_ATTEMPT04",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
