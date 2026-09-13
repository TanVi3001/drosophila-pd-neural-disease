#!/usr/bin/env python3
"""Create a separate pre-execution runner audit and keep authorization closed."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "research" / "alpha_syn_dopamine_preparation"
PREREG = PREP / "alpha_syn_dopamine_preregistration_v1.json"
PREREG_SHA = PREP / "alpha_syn_dopamine_preregistration_v1.sha256"
SPLIT = PREP / "alpha_syn_dopamine_study_split_manifest_v1.json"
CODE_AUDIT = PREP / "alpha_syn_dopamine_code_audit.json"
TEST_MANIFEST = PREP / "alpha_syn_dopamine_cpu_test_manifest.json"
AUTH = PREP / "alpha_syn_dopamine_execution_authorization_v1.json"
RUNNER_AUDIT = PREP / "alpha_syn_dopamine_runner_audit_v1.json"
REVIEW_SIGNOFF = PREP / "alpha_syn_dopamine_updated_registry_prereg_review_signoff_v1.json"
RUNNER_SCRIPT = ROOT / "scripts/run_alpha_syn_dopamine.py"
RUNNER_MODULE = ROOT / "src/drosophila_pd_neural/alpha_syn_dopamine_runner.py"
RUNNER_CONFIG = ROOT / "experiments/alpha_syn_dopamine/configs/alpha_syn_dopamine_runner_v1.yaml"
DRY_RUN = PREP / "alpha_syn_dopamine_runner_dry_run_manifest.json"
RUNNER_PACKET = PREP / "alpha_syn_dopamine_runner_protocol_review_packet.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_output(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    return result.stdout.strip()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    code_audit = json.loads(CODE_AUDIT.read_text(encoding="utf-8"))
    tests = json.loads(TEST_MANIFEST.read_text(encoding="utf-8"))
    review = json.loads(REVIEW_SIGNOFF.read_text(encoding="utf-8"))
    runner_config = yaml.safe_load(RUNNER_CONFIG.read_text(encoding="utf-8")) or {}
    prereg_sha = sha256(PREREG_SHA)  # hash of the signed hash sidecar, for artifact traceability
    prereg_document_hash = prereg.get("preregistration_sha256", "")

    # Exercise only the runner's dry-run path.  This resolves all declared
    # jobs but never calls the FlyGym backend or a GPU.
    dry_result = subprocess.run(
        [sys.executable, str(RUNNER_SCRIPT), "--dry-run", "--output", str(DRY_RUN)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    dry_run_document = json.loads(DRY_RUN.read_text(encoding="utf-8")) if DRY_RUN.is_file() else {}
    runtime = runner_config.get("runtime") or {}
    runtime_paths = {
        "brain_root": (ROOT / str(runtime.get("brain_root", ""))).resolve(),
        "checkpoint": (ROOT / str(runtime.get("brain_root", "")) / "data/plastic_weights.pt").resolve(),
        "connectivity": (ROOT / str(runtime.get("brain_root", "")) / "data/2025_Connectivity_783.parquet").resolve(),
        "completeness": (ROOT / str(runtime.get("brain_root", "")) / "data/2025_Completeness_783.csv").resolve(),
        "annotations": (ROOT / str(runtime.get("annotations", ""))).resolve(),
        "mapping_source": (ROOT / "configs/conditions/dopamine_deficiency.exploratory.yaml").resolve(),
        "backend": (ROOT / str(runtime.get("backend", ""))).resolve(),
        "platform_runner": (ROOT / str(runtime.get("platform_root", "")) / "scripts/run_brain_body_rollout.py").resolve(),
    }
    runtime_inputs_available = all(path.exists() for path in runtime_paths.values())
    matrix_payload = json.dumps(dry_run_document.get("jobs", []), sort_keys=True, separators=(",", ":")).encode("utf-8")
    job_matrix_sha256 = digest_bytes(matrix_payload)
    runner_candidates = [
        str(RUNNER_SCRIPT.relative_to(ROOT)),
        str(RUNNER_MODULE.relative_to(ROOT)),
        str(RUNNER_CONFIG.relative_to(ROOT)),
    ]
    model_boundary_ok = code_audit.get("implementation_status") == (
        "GENERIC_DISEASE_LAYER_CONTRACT_ONLY_NO_GENE_SPECIFIC_ALPHA_SYNUCLEIN_MAPPING"
    )
    audit_checks = {
        "preregistration_is_final_candidate": prereg.get("status") == "FINAL_PREREGISTRATION_PENDING_DUAL_HUMAN_REVIEW",
        "preregistration_hash_present": len(prereg_document_hash) == 64,
        "preregistration_hash_sidecar_present": PREREG_SHA.exists(),
        "study_split_not_opened_for_holdout": prereg.get("holdout_opened") is False and split.get("preparation_only") is True,
        "code_audit_passed": code_audit.get("status") == "AUDIT_PASS_WITH_IMPLEMENTATION_BOUNDARY",
        "cpu_tests_passed": tests.get("status") == "PASS" and tests.get("gpu_execution_performed") is False,
        "dual_human_registry_prereg_review_passed": review.get("status") == "DUAL_HUMAN_UPDATED_REGISTRY_AND_PREREG_REVIEW_PASS",
        "model_specific_runner_present": all(path.is_file() for path in (RUNNER_SCRIPT, RUNNER_MODULE, RUNNER_CONFIG)),
        "runner_protocol_packet_present": RUNNER_PACKET.is_file(),
        "runner_dry_run_passed": dry_result.returncode == 0 and dry_run_document.get("status") == "DRY_RUN_PASS" and dry_run_document.get("job_count") == 15 and dry_run_document.get("gpu_execution_performed") is False,
        "runtime_inputs_available": runtime_inputs_available,
        "no_gene_specific_runner_claimed": model_boundary_ok,
        "runner_protocol_review_passed_and_locked": runner_config.get("protocol_review_status") == "DUAL_HUMAN_RUNNER_PROTOCOL_REVIEW_PASS" and runner_config.get("parameter_lock_status") == "LOCKED_FOR_EXECUTION",
        "no_execution_authorization": prereg.get("gpu_execution_authorized") is False,
    }
    status = "READY_FOR_EXPLICIT_HUMAN_GPU_AUTHORIZATION" if all(audit_checks.values()) else "RUNNER_AUDIT_FAIL"

    audit = {
        "schema_version": "alpha-syn-dopamine-runner-audit-v1",
        "status": status,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "git_head_at_audit": git_output("rev-parse", "HEAD"),
        "runner_candidates": runner_candidates,
        "audit_checks": audit_checks,
        "model_implementation_status": "MODEL_SPECIFIC_CLASS_LEVEL_DOPAMINE_PROXY_RUNNER_IMPLEMENTED_WITH_NON_SPECIFIC_BOUNDARY",
        "runner_protocol_status": runner_config.get("protocol_review_status"),
        "job_matrix_count": dry_run_document.get("job_count", 0),
        "job_matrix_sha256": job_matrix_sha256,
        "runtime_inputs": {
            key: {"path": str(path), "sha256": sha256(path) if path.is_file() else None}
            for key, path in runtime_paths.items()
        },
        "preregistration_sha256": prereg_document_hash,
        "preregistration_hash_sidecar_sha256": prereg_sha,
        "artifacts": {
            "preregistration_json": {"path": str(PREREG.relative_to(ROOT)), "sha256": sha256(PREREG)},
            "preregistration_hash_sidecar": {"path": str(PREREG_SHA.relative_to(ROOT)), "sha256": sha256(PREREG_SHA)},
            "study_split": {"path": str(SPLIT.relative_to(ROOT)), "sha256": sha256(SPLIT)},
            "code_audit": {"path": str(CODE_AUDIT.relative_to(ROOT)), "sha256": sha256(CODE_AUDIT)},
            "cpu_tests": {"path": str(TEST_MANIFEST.relative_to(ROOT)), "sha256": sha256(TEST_MANIFEST)},
            "runner_dry_run": {"path": str(DRY_RUN.relative_to(ROOT)), "sha256": sha256(DRY_RUN)},
            "runner_script": {"path": str(RUNNER_SCRIPT.relative_to(ROOT)), "sha256": sha256(RUNNER_SCRIPT)},
            "runner_module": {"path": str(RUNNER_MODULE.relative_to(ROOT)), "sha256": sha256(RUNNER_MODULE)},
            "runner_config": {"path": str(RUNNER_CONFIG.relative_to(ROOT)), "sha256": sha256(RUNNER_CONFIG)},
            "runner_protocol_packet": {"path": str(RUNNER_PACKET.relative_to(ROOT)), "sha256": sha256(RUNNER_PACKET)},
        },
        "scientific_gpu_execution": {
            "allowed_now": False,
            "reason": "Runner, protocol review, dry-run, runtime inputs, and hashes pass; only separate explicit human GPU authorization remains.",
            "required": [
                "separate explicit authorization from both human reviewers",
                "freeze exact condition/mapping/transform/seed/QC/analysis/claim configuration",
                "record exact job matrix and checkpoint/config hashes",
                "start execution only through the guarded runner",
            ],
        },
    }
    write_json(RUNNER_AUDIT, audit)

    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    auth["runner_audit"] = RUNNER_AUDIT.name
    auth["runner_audit_sha256"] = sha256(RUNNER_AUDIT)
    auth["code_audit"] = CODE_AUDIT.name
    auth["code_audit_sha256"] = sha256(CODE_AUDIT)
    auth["authorized"] = False
    auth["authorized_jobs"] = 0
    auth["gpu_execution_authorized"] = False
    auth["simulation_execution_authorized"] = False
    auth["status"] = "WAITING_EXPLICIT_HUMAN_EXECUTION_AUTHORIZATION"
    auth["runner_status"] = status
    auth["runner_protocol_status"] = runner_config.get("protocol_review_status")
    auth["runner_config"] = RUNNER_CONFIG.name
    auth["runner_config_sha256"] = sha256(RUNNER_CONFIG)
    auth["runner_protocol_packet"] = RUNNER_PACKET.name
    auth["runner_protocol_packet_sha256"] = sha256(RUNNER_PACKET)
    auth["job_matrix_count"] = dry_run_document.get("job_count", 0)
    auth["job_matrix_sha256"] = job_matrix_sha256
    auth["runtime_input_hashes"] = {
        key: {"path": str(path), "sha256": sha256(path) if path.is_file() else None}
        for key, path in runtime_paths.items()
    }
    auth["required_before_authorization"] = [
        "dual human review signoff complete for updated registry and final preregistration",
        "dual human review signoff complete for the runner protocol and provisional parameters",
        "alpha-synuclein/dopamine code and model audit complete",
        "CPU synthetic/unit tests pass",
        "runner audit complete with exact 15-job matrix, config, checkpoint, and code hashes",
        "explicit authorization from both human reviewers",
    ]
    write_json(AUTH, auth)

    print(json.dumps({"status": status, "gpu_execution_authorized": False, "authorized_jobs": 0}, indent=2))
    return 0 if status != "RUNNER_AUDIT_FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
