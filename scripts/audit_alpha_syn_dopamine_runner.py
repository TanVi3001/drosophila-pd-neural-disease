#!/usr/bin/env python3
"""Create a separate pre-execution runner audit and keep authorization closed."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "research" / "alpha_syn_dopamine_preparation"
PREREG = PREP / "alpha_syn_dopamine_preregistration_v1.json"
PREREG_SHA = PREP / "alpha_syn_dopamine_preregistration_v1.sha256"
SPLIT = PREP / "alpha_syn_dopamine_study_split_manifest_v1.json"
CODE_AUDIT = PREP / "alpha_syn_dopamine_code_audit.json"
TEST_MANIFEST = PREP / "alpha_syn_dopamine_cpu_test_manifest.json"
AUTH = PREP / "alpha_syn_dopamine_execution_authorization_v1.json"
RUNNER_AUDIT = PREP / "alpha_syn_dopamine_runner_audit_v1.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    prereg_sha = sha256(PREREG_SHA)  # hash of the signed hash sidecar, for artifact traceability
    prereg_document_hash = prereg.get("preregistration_sha256", "")

    # There is intentionally no alpha-synuclein scientific runner in the
    # current repository.  The generic proxy config is not promoted into one.
    runner_candidates = []
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
        "no_gene_specific_runner_claimed": model_boundary_ok,
        "no_execution_authorization": prereg.get("gpu_execution_authorized") is False,
    }
    status = "NOT_READY_MODEL_SPECIFIC_RUNNER_MISSING" if all(audit_checks.values()) else "RUNNER_AUDIT_FAIL"

    audit = {
        "schema_version": "alpha-syn-dopamine-runner-audit-v1",
        "status": status,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "git_head_at_audit": git_output("rev-parse", "HEAD"),
        "runner_candidates": runner_candidates,
        "audit_checks": audit_checks,
        "model_implementation_status": code_audit.get("implementation_status"),
        "preregistration_sha256": prereg_document_hash,
        "preregistration_hash_sidecar_sha256": prereg_sha,
        "artifacts": {
            "preregistration_json": {"path": str(PREREG.relative_to(ROOT)), "sha256": sha256(PREREG)},
            "preregistration_hash_sidecar": {"path": str(PREREG_SHA.relative_to(ROOT)), "sha256": sha256(PREREG_SHA)},
            "study_split": {"path": str(SPLIT.relative_to(ROOT)), "sha256": sha256(SPLIT)},
            "code_audit": {"path": str(CODE_AUDIT.relative_to(ROOT)), "sha256": sha256(CODE_AUDIT)},
            "cpu_tests": {"path": str(TEST_MANIFEST.relative_to(ROOT)), "sha256": sha256(TEST_MANIFEST)},
        },
        "scientific_gpu_execution": {
            "allowed_now": False,
            "reason": "No model-specific alpha-synuclein runner and no dual-human review/execution authorization.",
            "required": [
                "implement and audit the declared alpha-synuclein/dopamine runner",
                "freeze exact condition/mapping/transform/seed/QC/analysis/claim configuration",
                "record exact job matrix and checkpoint/config hashes",
                "obtain dual-human review signoff and separate explicit execution authorization",
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
    write_json(AUTH, auth)

    print(json.dumps({"status": status, "gpu_execution_authorized": False, "authorized_jobs": 0}, indent=2))
    return 0 if status != "RUNNER_AUDIT_FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
