#!/usr/bin/env python3
"""Record explicit GPU authorization after all pre-execution gates pass.

This script only writes the authorization record and preparation manifest.  It
does not start the scientific runner or create a simulation output directory.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "research" / "alpha_syn_dopamine_preparation"
CONFIG = ROOT / "experiments/alpha_syn_dopamine/configs/alpha_syn_dopamine_runner_v1.yaml"
RUNNER = ROOT / "scripts/run_alpha_syn_dopamine.py"
RUNNER_MODULE = ROOT / "src/drosophila_pd_neural/alpha_syn_dopamine_runner.py"
PREREG = PREP / "alpha_syn_dopamine_preregistration_v1.json"
PREREG_MD = PREP / "alpha_syn_dopamine_preregistration_v1.md"
PREREG_SHA = PREP / "alpha_syn_dopamine_preregistration_v1.sha256"
REGISTRY = PREP / "literature_endpoint_registry_v2.csv"
SPLIT = PREP / "alpha_syn_dopamine_study_split_manifest_v1.json"
REVIEW = PREP / "alpha_syn_dopamine_updated_registry_prereg_review_signoff_v1.json"
RUNNER_PACKET = PREP / "alpha_syn_dopamine_runner_protocol_review_packet.md"
RUNNER_AUDIT = PREP / "alpha_syn_dopamine_runner_audit_v1.json"
CODE_AUDIT = PREP / "alpha_syn_dopamine_code_audit.json"
TEST_MANIFEST = PREP / "alpha_syn_dopamine_cpu_test_manifest.json"
DRY_RUN = PREP / "alpha_syn_dopamine_runner_dry_run_manifest.json"
AUTH = PREP / "alpha_syn_dopamine_execution_authorization_v1.json"
PREP_MANIFEST = PREP / "alpha_syn_dopamine_preparation_manifest.json"
AUTHORIZER = ROOT / "scripts/authorize_alpha_syn_dopamine_gpu.py"

EXPECTED_CHECKPOINT_SHA256 = "d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_jobs(jobs: list[dict[str, Any]]) -> str:
    payload = json.dumps(jobs, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return result.stdout.strip()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"AUTHORIZATION_BLOCKED: {message}")


def file_record(path: Path) -> dict[str, str | None]:
    return {"path": str(path), "sha256": sha256(path) if path.is_file() else None}


def main() -> int:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    runner_audit = json.loads(RUNNER_AUDIT.read_text(encoding="utf-8"))
    code_audit = json.loads(CODE_AUDIT.read_text(encoding="utf-8"))
    tests = json.loads(TEST_MANIFEST.read_text(encoding="utf-8"))
    dry_run = json.loads(DRY_RUN.read_text(encoding="utf-8"))
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    prep_manifest = json.loads(PREP_MANIFEST.read_text(encoding="utf-8"))

    require(auth.get("authorized") is not True, "authorization is already active; do not re-authorize")
    require(review.get("status") == "DUAL_HUMAN_UPDATED_REGISTRY_AND_PREREG_REVIEW_PASS", "registry/prereg review is not PASS")
    require(review.get("runner_protocol_status") == "DUAL_HUMAN_RUNNER_PROTOCOL_REVIEW_PASS", "runner protocol review is not PASS")
    require(config.get("protocol_review_status") == "DUAL_HUMAN_RUNNER_PROTOCOL_REVIEW_PASS", "runner protocol status is not PASS")
    require(config.get("parameter_lock_status") == "LOCKED_FOR_EXECUTION", "runner parameters are not locked")
    require(code_audit.get("status") == "AUDIT_PASS_WITH_IMPLEMENTATION_BOUNDARY", "code/model audit is not PASS")
    require(tests.get("status") == "PASS" and tests.get("gpu_execution_performed") is False, "CPU-only tests are not PASS")
    require(runner_audit.get("status") == "READY_FOR_EXPLICIT_HUMAN_GPU_AUTHORIZATION", "runner audit is not ready")
    require(dry_run.get("status") == "DRY_RUN_PASS", "runner dry-run is not PASS")
    require(dry_run.get("job_count") == 15 and len(dry_run.get("jobs", [])) == 15, "dry-run matrix is not exactly 15 jobs")
    require(dry_run.get("gpu_execution_performed") is False, "dry-run reports GPU execution")
    require(prereg.get("gpu_execution_authorized") is False, "frozen preregistration unexpectedly authorizes GPU")
    require(prereg.get("holdout_opened") is False, "holdout is open")

    jobs = dry_run["jobs"]
    job_ids = [job["job_id"] for job in jobs]
    require(len(job_ids) == len(set(job_ids)), "job IDs are not unique")
    matrix_hash = digest_jobs(jobs)
    require(runner_audit.get("job_matrix_count") == 15, "runner audit job count is not 15")
    require(runner_audit.get("job_matrix_sha256") == matrix_hash, "runner audit matrix hash mismatch")
    require(dry_run.get("config_sha256") == sha256(CONFIG), "dry-run config hash mismatch")
    require(runner_audit.get("artifacts", {}).get("runner_config", {}).get("sha256") == sha256(CONFIG), "runner audit config hash mismatch")

    runtime = config.get("runtime") or {}
    brain_root = (ROOT / str(runtime.get("brain_root", ""))).resolve()
    runtime_paths = {
        "brain_root": brain_root,
        "checkpoint": brain_root / "data/plastic_weights.pt",
        "connectivity": brain_root / "data/2025_Connectivity_783.parquet",
        "completeness": brain_root / "data/2025_Completeness_783.csv",
        "annotations": (ROOT / str(runtime.get("annotations", ""))).resolve(),
        "mapping_source": (ROOT / str(config["mapping"]["source_config"])).resolve(),
        "backend": (ROOT / str(runtime.get("backend", ""))).resolve(),
        "platform_runner": (ROOT / str(runtime.get("platform_root", "")) / "scripts/run_brain_body_rollout.py").resolve(),
    }
    require(all(path.exists() for path in runtime_paths.values()), "one or more runtime inputs are missing")
    require(sha256(runtime_paths["checkpoint"]) == EXPECTED_CHECKPOINT_SHA256, "canonical checkpoint SHA256 mismatch")

    prereg_sidecar = PREREG_SHA.read_text(encoding="utf-8").split()[0]
    require(prereg_sidecar == prereg.get("preregistration_sha256"), "preregistration sidecar/document hash mismatch")
    require(sha256(PREREG_MD) == prereg.get("preregistration_sha256"), "preregistration markdown hash changed")

    runtime_records = {key: file_record(path) for key, path in runtime_paths.items()}
    require(
        runner_audit.get("runtime_inputs") == runtime_records,
        "runner-audit runtime input records do not match current files",
    )

    auth.update(
        {
            "authorization_id": "ALPHA_SYN_DOPAMINE_EXECUTION_AUTH_V1",
            "schema_version": "alpha-syn-dopamine-execution-authorization-v1",
            "status": "AUTHORIZED_FOR_SCIENTIFIC_GPU_EXECUTION",
            "authorized": True,
            "explicit_human_authorization": True,
            "gpu_execution_authorized": True,
            "simulation_execution_authorized": True,
            "authorized_at": datetime.now(timezone.utc).isoformat(),
            "git_head_at_authorization": git_head(),
            "runner_status": runner_audit["status"],
            "runner_protocol_status": config["protocol_review_status"],
            "runner_config": str(CONFIG.relative_to(ROOT)),
            "runner_config_sha256": sha256(CONFIG),
            "runner_protocol_packet": str(RUNNER_PACKET.relative_to(ROOT)),
            "runner_protocol_packet_sha256": sha256(RUNNER_PACKET),
            "runner_audit": str(RUNNER_AUDIT.relative_to(ROOT)),
            "runner_audit_sha256": sha256(RUNNER_AUDIT),
            "code_audit": str(CODE_AUDIT.relative_to(ROOT)),
            "code_audit_sha256": sha256(CODE_AUDIT),
            "cpu_test_manifest": str(TEST_MANIFEST.relative_to(ROOT)),
            "cpu_test_manifest_sha256": sha256(TEST_MANIFEST),
            "dry_run_manifest": str(DRY_RUN.relative_to(ROOT)),
            "dry_run_manifest_sha256": sha256(DRY_RUN),
            "job_matrix_count": len(jobs),
            "job_matrix_sha256": matrix_hash,
            "authorized_job_ids": job_ids,
            "runtime_input_hashes": runtime_records,
            "preregistration_sha256": prereg["preregistration_sha256"],
            "preregistration_json_sha256": sha256(PREREG),
            "preregistration_hash_sidecar_sha256": sha256(PREREG_SHA),
            "registry_sha256": sha256(REGISTRY),
            "study_split_sha256": sha256(SPLIT),
            "authorization_script": str(AUTHORIZER.relative_to(ROOT)),
            "authorization_script_sha256": sha256(AUTHORIZER),
            "human_authorizations": [
                {
                    "name": "Le Tan Vi",
                    "status": "CONFIRMED",
                    "scope": "exact locked 15-job alpha-synuclein/dopamine runner matrix on CUDA",
                    "attestation": "Direct authorization recorded from Le Tan Vi in the project conversation on 2026-09-13.",
                },
                {
                    "name": "To Dang Minh Tuan",
                    "status": "CONFIRMED",
                    "scope": "exact locked 15-job alpha-synuclein/dopamine runner matrix on CUDA",
                    "attestation": "Direct authorization recorded from To Dang Minh Tuan in the project conversation on 2026-09-13.",
                },
            ],
            "execution_scope": {
                "runner_id": config["runner_id"],
                "conditions": [item["job_condition_id"] for item in config["job_matrix"]["conditions"]],
                "seeds": config["job_matrix"]["seeds"],
                "job_count": len(jobs),
                "device": runtime["device"],
                "steps": runtime["steps"],
                "timestep_s": runtime["timestep_s"],
                "age_days": runtime["age_days"],
                "stimulus": runtime["stimulus"],
                "no_retry": config["controls"]["no_automatic_retry"],
                "no_overwrite": config["controls"]["no_overwrite_existing_output"],
                "no_calibration": config["controls"]["no_calibration"],
                "no_fitting": config["controls"]["no_fitting"],
                "no_retuning": config["controls"]["no_retuning"],
                "no_holdout": config["controls"]["no_holdout_opening"],
            },
            "prohibitions": [
                "no automatic retry",
                "no rerun of completed jobs",
                "no overwrite of existing output",
                "no calibration",
                "no fitting",
                "no retuning",
                "no burden search after observing results",
                "no holdout opening",
            ],
            "execution_not_started_by_authorization_step": True,
        }
    )
    AUTH.write_text(json.dumps(auth, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    prep_manifest.update(
        {
            "status": "RUNNER_PROTOCOL_LOCKED_GPU_AUTHORIZED_EXECUTION_NOT_STARTED",
            "execution_authorization_status": "AUTHORIZED_FOR_SCIENTIFIC_GPU_EXECUTION",
            "gpu_execution_authorized": True,
            "execution_not_started": True,
            "authorized_jobs": len(jobs),
            "next_required_review": "None before execution; after execution perform QC/integrity and preregistered analysis",
            "runner_status": runner_audit["status"],
            "runner_protocol_status": config["protocol_review_status"],
            "runner_config_sha256": sha256(CONFIG),
            "runner_audit_sha256": sha256(RUNNER_AUDIT),
            "job_matrix_sha256": matrix_hash,
        }
    )
    PREP_MANIFEST.write_text(json.dumps(prep_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": auth["status"],
        "authorized_jobs": auth["authorized_jobs"],
        "job_matrix_sha256": matrix_hash,
        "checkpoint_sha256": runtime_records["checkpoint"]["sha256"],
        "execution_started": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
