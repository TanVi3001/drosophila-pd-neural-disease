from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import scripts.audit_gate24e_attempt04_authorization as attempt04


FAILURE = json.loads(attempt04.ATTEMPT_03_MANIFEST.read_text(encoding="utf-8"))
HISTORY = json.loads(attempt04.STORAGE_HISTORY.read_text(encoding="utf-8"))
FIREWALL = json.loads(attempt04.FIREWALL.read_text(encoding="utf-8"))
EXECUTION = json.loads(attempt04.SCIENTIFIC_EXECUTION.read_text(encoding="utf-8"))
SIGNOFF = json.loads(attempt04.SIGNOFF.read_text(encoding="utf-8"))
AUTHORIZATION = json.loads(attempt04.AUTHORIZATION.read_text(encoding="utf-8"))


def _runtime() -> dict:
    return {
        "status": "ATTEMPT_03_TECHNICAL_FAILURE_RECORDED",
        "runtime_review_state": "APPROVED",
        "amended_platform_commit": attempt04.PLATFORM_COMMIT,
        "artifact_profile": attempt04.ARTIFACT_PROFILE,
        "scientific_contract_changed": False,
        "scientific_batch_authorized": False,
        "holdout": "SEALED",
        "scientific_jobs_executed": 0,
        "attempt_03_failure_recorded": True,
        "blockers": [],
        "runtime": {
            "head": attempt04.PLATFORM_COMMIT,
            "clean": True,
            "runtime_root": str(attempt04.EXPECTED_RUNTIME_ROOT),
        },
    }


def _documents() -> dict:
    return {
        "failure": deepcopy(FAILURE),
        "history": deepcopy(HISTORY),
        "firewall": deepcopy(FIREWALL),
        "execution": deepcopy(EXECUTION),
        "signoff": deepcopy(SIGNOFF),
        "authorization": deepcopy(AUTHORIZATION),
        "runtime": _runtime(),
        "attempt04_exists": False,
    }


def _audit(**changes: object) -> dict:
    documents = _documents()
    documents.update(changes)
    return attempt04.audit_documents(**documents)


def _approved_documents() -> dict:
    documents = _documents()
    documents["signoff"].update(
        {
            "status": "ATTEMPT04_AUTHORIZATION_APPROVED",
            "reviewer_1": "Human Reviewer One",
            "reviewer_2": "Human Reviewer Two",
            "review_date": "2026-09-09",
            "decision": "APPROVED_FOR_ONE_NEW_GATE24E_STORAGE_ATTEMPT",
            "attempt_04_authorized": True,
        }
    )
    documents["authorization"].update(
        {
            "status": "ATTEMPT04_AUTHORIZATION_APPROVED",
            "attempt_04_authorized": True,
        }
    )
    return documents


def test_01_attempt03_consumed_is_required() -> None:
    failure = deepcopy(FAILURE)
    failure["attempt_03_consumed"] = False
    assert _audit(failure=failure)["status"] == "GATE24E_ATTEMPT04_AUTHORIZATION_INVALID"


def test_02_attempt03_retry_must_remain_false() -> None:
    failure = deepcopy(FAILURE)
    failure["attempt_03_retry_allowed"] = True
    assert _audit(failure=failure)["status"] == "GATE24E_ATTEMPT04_AUTHORIZATION_INVALID"


def test_03_attempt03_simulation_started_is_preserved() -> None:
    assert FAILURE["simulation_started"] is True
    assert FAILURE["gpu_simulation_started"] is True


def test_04_interruption_is_classified_as_technical() -> None:
    assert FAILURE["failure_type"] == "TECHNICAL_INTERRUPTION"
    assert FAILURE["failure_stage"] == "DURING_SIMULATION"
    assert FAILURE["exception"] == "KeyboardInterrupt"


def test_05_exact_executed_step_count_remains_unknown() -> None:
    assert FAILURE["last_confirmed_progress_steps"] == 40000
    assert FAILURE["exact_executed_steps_known"] is False
    assert FAILURE["exact_executed_steps"] is None


def test_06_attempt03_storage_is_invalid() -> None:
    assert FAILURE["storage_measurements_valid"] is False
    assert FAILURE["storage_qualification_valid"] is False


def test_07_holdout_remains_sealed() -> None:
    assert _audit()["holdout"] == "SEALED"


def test_08_scientific_jobs_remain_zero() -> None:
    assert _audit()["scientific_jobs_executed"] == 0


def test_09_attempt04_human_authorization_is_recorded() -> None:
    result = _audit()
    assert SIGNOFF["attempt_04_authorized"] is True
    assert AUTHORIZATION["attempt_04_authorized"] is True
    assert result["attempt_04_authorized"] is True


def test_10_scientific_batch_remains_unauthorized() -> None:
    assert SIGNOFF["scientific_batch_authorized"] is False
    assert AUTHORIZATION["scientific_batch_authorized"] is False
    assert _audit()["scientific_batch_authorized"] is False


def test_11_probe_seed_is_fixed_to_9001() -> None:
    assert attempt04.PROBE_SEED == SIGNOFF["probe_seed"] == AUTHORIZATION["probe_seed"] == 9001


def test_12_probe_seed_is_outside_scientific_seeds() -> None:
    assert list(attempt04.SCIENTIFIC_SEEDS) == [0, 1, 2, 3, 4]
    assert attempt04.PROBE_SEED not in attempt04.SCIENTIFIC_SEEDS


def test_13_steps_are_fixed_to_100000() -> None:
    assert attempt04.STEPS == SIGNOFF["steps"] == AUTHORIZATION["steps"] == 100000


def test_14_device_is_fixed_to_cuda() -> None:
    assert attempt04.DEVICE == SIGNOFF["device"] == AUTHORIZATION["device"] == "cuda"


def test_15_runtime_commit_is_fixed() -> None:
    assert SIGNOFF["platform_commit"] == AUTHORIZATION["platform_commit"] == attempt04.PLATFORM_COMMIT


def test_16_memory_safe_profile_is_fixed() -> None:
    assert SIGNOFF["artifact_profile"] == AUTHORIZATION["artifact_profile"] == "GATE24E_MEMORY_SAFE"


@pytest.mark.parametrize("placeholder", ["TODO", "Reviewer 1", "TÊN NGƯỜI REVIEW", "pending"])
def test_17_reviewer_placeholders_are_rejected(placeholder: str) -> None:
    signoff = deepcopy(SIGNOFF)
    signoff["reviewer_1"] = placeholder
    result = _audit(signoff=signoff)
    assert "reviewer placeholders are forbidden" in result["blockers"]


def test_18_duplicate_reviewers_are_rejected() -> None:
    documents = _approved_documents()
    documents["signoff"]["reviewer_2"] = documents["signoff"]["reviewer_1"]
    result = attempt04.audit_documents(**documents)
    assert "two distinct human reviewers are required" in result["blockers"]


def test_19_pending_review_cannot_authorize_attempt04() -> None:
    signoff = deepcopy(SIGNOFF)
    signoff["status"] = "WAITING_ATTEMPT04_AUTHORIZATION_REVIEW"
    signoff["decision"] = "PENDING_HUMAN_REVIEW"
    signoff["attempt_04_authorized"] = True
    result = _audit(signoff=signoff)
    assert result["status"] == "GATE24E_ATTEMPT04_AUTHORIZATION_INVALID"
    assert "pending review cannot authorize attempt_04" in result["blockers"]


def test_20_valid_future_review_can_become_ready() -> None:
    result = attempt04.audit_documents(**_approved_documents())
    assert result["status"] == "READY_FOR_GATE24E_ATTEMPT04"
    assert result["attempt_04_authorized"] is True


def test_21_attempt04_output_directory_is_not_created() -> None:
    assert not attempt04.ATTEMPT_04.exists()
    assert (attempt04.ROOT / "scripts/run_gate24e_storage_probe_attempt04.py").is_file()


def test_22_auditor_executes_no_gpu() -> None:
    assert _audit()["gpu_executed_by_audit"] is False


def test_23_auditor_executes_no_simulation() -> None:
    assert _audit()["simulation_executed_by_audit"] is False


def test_24_attempt03_artifacts_are_unchanged() -> None:
    expected = {
        attempt04.ATTEMPT_03_MANIFEST: "fb6170244e17211d3b5a46fbdb7b26002ea6b81e2cb1182c2a2b170e7cdea58b",
        attempt04.ATTEMPT_03_MANIFEST.parent / "attempt_03_authorization.json":
            "294ec453cc4df032147553c2b7957d81fbec3f8d52351edf0de1bb4e955563dc",
        attempt04.ATTEMPT_03_MANIFEST.parents[1] / "logs/storage_probe_attempt_03.log":
            "7a12053b0b81086f4b544c11c654f9b1cb21c05169a0448a305b5b309bda35a9",
    }
    for path, digest in expected.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


@pytest.mark.parametrize(
    ("document_name", "field", "invalid_value"),
    [
        ("authorization", "probe_seed", 9002),
        ("authorization", "steps", 50000),
        ("authorization", "device", "cpu"),
        ("authorization", "artifact_profile", "LEGACY"),
        ("authorization", "automatic_retry", True),
        ("authorization", "scientific_batch_authorized", True),
        ("authorization", "holdout_access_allowed", True),
        ("failure", "attempt_03_retry_allowed", True),
        ("firewall", "status", "OPEN"),
        ("execution", "executed_job_count", 1),
        ("runtime", "amended_platform_commit", "wrong"),
    ],
)
def test_25_fail_closed_on_contract_changes(
    document_name: str, field: str, invalid_value: object
) -> None:
    documents = _documents()
    documents[document_name][field] = invalid_value
    result = attempt04.audit_documents(**documents)
    assert result["status"] == "GATE24E_ATTEMPT04_AUTHORIZATION_INVALID"
    assert result["blockers"]


def test_26_invalid_review_date_is_rejected() -> None:
    documents = _approved_documents()
    documents["signoff"]["review_date"] = "2026-02-30"
    result = attempt04.audit_documents(**documents)
    assert "approved attempt_04 requires a valid ISO review_date" in result["blockers"]


def test_27_current_state_waits_for_human_review() -> None:
    result = _audit()
    assert result["status"] == "READY_FOR_GATE24E_ATTEMPT04"
    assert result["reviewer_1"] == "Tuan Le"
    assert result["reviewer_2"] == "To Dang Minh Tuan"
    assert result["next_allowed_action"] == "IMPLEMENT_SINGLE_USE_GATE24E_ATTEMPT04_RUNNER"


def test_28_review_packet_preserves_claim_boundary() -> None:
    packet = (
        attempt04.ROOT
        / "docs/validation/gate24e_attempt03_technical_interruption_review_packet.md"
    ).read_text(encoding="utf-8")
    assert "does not authorize biological or scientific interpretation" in packet
    assert "no biological validation claim" in packet
    assert "UNRESOLVED_FROM_AVAILABLE_EVIDENCE" in packet
