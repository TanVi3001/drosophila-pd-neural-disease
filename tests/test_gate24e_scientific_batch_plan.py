from __future__ import annotations

from copy import deepcopy
import json

from scripts import audit_gate24e_scientific_batch_preflight as preflight
from scripts.prepare_gate24e_scientific_batch_plan import (
    DISEASE_CHECKPOINT_SHA256,
    DISEASE_PARAMETERS,
    HEALTHY_CHECKPOINT_SHA256,
    PARAMETER_GRID,
    SEEDS,
    build_plan,
    canonical_plan_sha256,
)


def test_exact_25_job_seed_major_matrix() -> None:
    plan = build_plan()
    jobs = plan["jobs"]
    assert len(jobs) == 25
    assert plan["job_count"] == 25
    assert sum(job["condition"] == "healthy" for job in jobs) == 5
    assert sum(job["condition"] == "parkin" for job in jobs) == 20
    assert [job["seed"] for job in jobs[::5]] == SEEDS
    assert all(
        [job["condition"] for job in jobs[index : index + 5]]
        == ["healthy", "parkin", "parkin", "parkin", "parkin"]
        for index in range(0, 25, 5)
    )
    assert [job["parameter"] for job in jobs[:5]] == PARAMETER_GRID
    assert all(job["condition"] != "parkin" or job["parameter"] != 0.0 for job in jobs)
    assert all(job["seed"] != 9001 for job in jobs)


def test_job_ids_and_output_paths_are_unique_and_deterministic() -> None:
    existed_before = preflight.OUTPUT_ROOT.exists()
    jobs = build_plan()["jobs"]
    assert len({job["job_id"] for job in jobs}) == 25
    assert len({job["output_directory"] for job in jobs}) == 25
    assert jobs[0]["job_id"] == "seed00_healthy"
    assert jobs[1]["job_id"] == "seed00_parkin_p025"
    assert jobs[-1]["job_id"] == "seed04_parkin_p100"
    assert preflight.OUTPUT_ROOT.exists() is existed_before


def test_checkpoint_paths_and_hashes_are_locked() -> None:
    plan = build_plan()
    assert plan["healthy_checkpoint_sha256"] == HEALTHY_CHECKPOINT_SHA256
    assert plan["disease_checkpoint_sha256"] == DISEASE_CHECKPOINT_SHA256
    for job in plan["jobs"]:
        expected = HEALTHY_CHECKPOINT_SHA256 if job["condition"] == "healthy" else DISEASE_CHECKPOINT_SHA256[str(job["parameter"])]
        assert job["checkpoint_sha256"] == expected
        assert "--prepared-checkpoint" not in job["command"] if job["condition"] == "healthy" else "--prepared-checkpoint" in job["command"]


def test_plan_checksum_changes_when_order_or_checkpoint_changes() -> None:
    original = build_plan()
    original_sha = canonical_plan_sha256(original)

    reordered = deepcopy(original)
    reordered["jobs"][0], reordered["jobs"][1] = reordered["jobs"][1], reordered["jobs"][0]
    assert canonical_plan_sha256(reordered) != original_sha

    changed_checkpoint = deepcopy(original)
    changed_checkpoint["jobs"][1]["checkpoint_sha256"] = "0" * 64
    assert canonical_plan_sha256(changed_checkpoint) != original_sha


def test_scientific_firewall_is_closed_in_plan_and_authorization_template() -> None:
    plan = build_plan()
    authorization = json.loads(preflight.AUTHORIZATION_PATH.read_text(encoding="utf-8"))
    assert plan["scientific_jobs_executed"] == 0
    assert plan["scientific_batch_authorized"] is False
    assert plan["holdout"] == "SEALED"
    assert plan["gpu_executed"] is False
    assert plan["simulation_executed"] is False
    assert authorization["decision"] == "APPROVED_FOR_EXACT_GATE24E_25_JOB_BATCH"
    assert authorization["scientific_batch_authorized"] is True


def test_all_commands_are_non_video_cuda_contracts_without_forbidden_flags() -> None:
    forbidden = {"--video", "--video-output", "--compare-to", "--cpg-frequency-hz"}
    for job in build_plan()["jobs"]:
        command = job["command"]
        assert command[0].endswith(r".venv\Scripts\python.exe")
        assert command[1].replace("\\", "/").endswith("scripts/run_neural_experiment.py")
        assert "--device" in command and command[command.index("--device") + 1] == "cuda"
        assert not forbidden.intersection(command)
        assert "--steps" in command and command[command.index("--steps") + 1] == "100000"


def test_current_preflight_is_blocked_without_running_a_job() -> None:
    result = preflight.audit(live_free_bytes=preflight.REQUIRED_STORAGE_BYTES)
    assert result["status"] == "BLOCKED_GATE24E_SCIENTIFIC_BATCH_PREFLIGHT"
    assert "STORAGE_CAPACITY_NOT_RESOLVED" in result["blockers"]
    assert "SCIENTIFIC_BATCH_HUMAN_REVIEW_PENDING" not in result["blockers"]
    assert result["scientific_jobs_executed"] == 0
    assert result["scientific_batch_authorized"] is False
    assert result["holdout"] == "SEALED"
    assert result["gpu_executed"] is False
    assert result["simulation_executed"] is False
    assert result["attempt_04"]["preserved"] is True


def test_storage_component_uses_strict_greater_than_rule() -> None:
    equal = preflight.audit(live_free_bytes=preflight.REQUIRED_STORAGE_BYTES)
    above = preflight.audit(live_free_bytes=preflight.REQUIRED_STORAGE_BYTES + 1)
    assert equal["capacity_pass"] is False
    assert above["capacity_pass"] is True
    assert "STORAGE_CAPACITY_NOT_RESOLVED" in equal["blockers"]
    assert "STORAGE_CAPACITY_NOT_RESOLVED" not in above["blockers"]


def test_human_authorization_rejects_duplicate_reviewers_and_invalid_date() -> None:
    document = {
        "status": "SCIENTIFIC_BATCH_AUTHORIZATION_APPROVED",
        "decision": "APPROVED_FOR_EXACT_GATE24E_25_JOB_BATCH",
        "scientific_batch_plan_sha256": canonical_plan_sha256(build_plan()),
        "storage_capacity_resolved": True,
        "scientific_batch_authorized": True,
        "reviewer_1": "same",
        "reviewer_2": "same",
        "review_date": "2026-09-08",
    }
    assert preflight._authorization_is_valid(document, document["scientific_batch_plan_sha256"]) is False
    document["reviewer_2"] = "other"
    document["review_date"] = "not-a-date"
    assert preflight._authorization_is_valid(document, document["scientific_batch_plan_sha256"]) is False


def test_no_attempt05_and_no_job_runner_side_effects() -> None:
    assert not preflight.ATTEMPT_05.exists()
    output_existed_before = preflight.OUTPUT_ROOT.exists()
    source = preflight.ROOT / "scripts/preview_gate24e_scientific_batch.py"
    text = source.read_text(encoding="utf-8")
    assert "subprocess.run" not in text
    assert "subprocess.Popen" not in text
    assert preflight.OUTPUT_ROOT.exists() is output_existed_before
