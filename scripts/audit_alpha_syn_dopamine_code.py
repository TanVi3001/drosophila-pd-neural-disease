#!/usr/bin/env python3
"""Audit the alpha-synuclein/dopamine code contract and run CPU-only tests."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "research" / "alpha_syn_dopamine_preparation"
AUDIT = PREP / "alpha_syn_dopamine_code_audit.json"
TEST_MANIFEST = PREP / "alpha_syn_dopamine_cpu_test_manifest.json"
MODEL = ROOT / "src/drosophila_pd_neural/models.py"
PERTURBATIONS = ROOT / "src/drosophila_pd_neural/perturbations.py"
CONFIG = ROOT / "experiments/gate_12c_computational_proxy_configs/configs/alpha_synuclein_proxy_condition.yaml"
RUNNER_MODULE = ROOT / "src/drosophila_pd_neural/alpha_syn_dopamine_runner.py"
RUNNER_SCRIPT = ROOT / "scripts/run_alpha_syn_dopamine.py"
RUNNER_CONFIG = ROOT / "experiments/alpha_syn_dopamine/configs/alpha_syn_dopamine_runner_v1.yaml"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    model_text = MODEL.read_text(encoding="utf-8")
    perturbation_text = PERTURBATIONS.read_text(encoding="utf-8")
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    runner_text = RUNNER_SCRIPT.read_text(encoding="utf-8")
    runner_module_text = RUNNER_MODULE.read_text(encoding="utf-8")
    runner_config = yaml.safe_load(RUNNER_CONFIG.read_text(encoding="utf-8"))

    checks = {
        "functional_gain_field_present": "presynaptic_gain" in model_text and "postsynaptic_gain" in model_text,
        "structural_survival_field_present": "neuron_survival" in model_text,
        "age_profile_interpolation_present": "class DiseaseProfile" in model_text and "def at_age" in model_text and "def burden_at" in model_text,
        "explicit_neuron_and_edge_ids": "target_neurons" in perturbation_text and "target_edges" in perturbation_text,
        "no_positional_fallback_documented": "fallback theo vi tri" in perturbation_text,
        "proxy_has_no_gene_specific_mapping": config["target_definition"]["gene_specific_mapping"] is False,
        "proxy_has_no_target_ids": not config["target_definition"]["target_neurons"] and not config["target_definition"]["target_edges"],
        "proxy_is_not_calibrated": config["burden"]["calibrated"] is False,
        "proxy_does_not_claim_biological_mapping": config["proxy_operator"]["biological_mapping_claim"] is False,
        "model_specific_runner_module_present": "def resolve_condition" in runner_module_text and "def build_job_matrix" in runner_module_text,
        "runner_has_explicit_execute_guard": "_require_execution_authorization" in runner_text and "gpu_execution_authorized" in runner_text,
        "runner_protocol_not_yet_authorized": runner_config["parameter_lock_status"] == "PROVISIONAL_NO_GPU" and runner_config["protocol_review_status"] == "PENDING_DUAL_HUMAN_RUNNER_PROTOCOL_REVIEW",
        "runner_config_keeps_gene_mapping_non_specific": runner_config["model"]["gene_specific_mapping"] is False and runner_config["model"]["biological_mapping_claim"] is False,
    }

    test_env = os.environ.copy()
    # The audit is deliberately CPU-only.  No simulator or scientific runner
    # is invoked by this script.
    test_env["CUDA_VISIBLE_DEVICES"] = "-1"
    test_result = run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_alpha_syn_dopamine_audit.py", "-p", "no:cacheprovider"],
        env=test_env,
    )
    compile_result = run([sys.executable, "-m", "compileall", "-q", "scripts", "src", "tests"])
    tests_pass = test_result.returncode == 0 and compile_result.returncode == 0
    contract_pass = all(checks.values())
    status = "AUDIT_PASS_WITH_IMPLEMENTATION_BOUNDARY" if tests_pass and contract_pass else "AUDIT_FAIL"

    test_manifest = {
        "schema_version": "alpha-syn-dopamine-cpu-test-v1",
        "status": "PASS" if tests_pass else "FAIL",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "commands": [
            "python -m pytest -q tests/test_alpha_syn_dopamine_audit.py -p no:cacheprovider",
            "python -m compileall -q scripts src tests",
        ],
        "cuda_visible_devices": test_env["CUDA_VISIBLE_DEVICES"],
        "gpu_execution_performed": False,
        "pytest_returncode": test_result.returncode,
        "compileall_returncode": compile_result.returncode,
        "pytest_stdout_tail": test_result.stdout[-4000:],
        "pytest_stderr_tail": test_result.stderr[-4000:],
    }
    TEST_MANIFEST.write_text(json.dumps(test_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    audit = {
        "schema_version": "alpha-syn-dopamine-code-audit-v1",
        "status": status,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "implementation_status": "GENERIC_DISEASE_LAYER_CONTRACT_ONLY_NO_GENE_SPECIFIC_ALPHA_SYNUCLEIN_MAPPING",
        "model_scope": "alpha-synuclein -> dopamine circuit -> locomotion",
        "checks": checks,
        "artifacts": {
            "models_py": {"path": str(MODEL.relative_to(ROOT)), "sha256": sha256(MODEL)},
            "perturbations_py": {"path": str(PERTURBATIONS.relative_to(ROOT)), "sha256": sha256(PERTURBATIONS)},
            "proxy_config": {"path": str(CONFIG.relative_to(ROOT)), "sha256": sha256(CONFIG)},
            "model_specific_runner_module": {"path": str(RUNNER_MODULE.relative_to(ROOT)), "sha256": sha256(RUNNER_MODULE)},
            "model_specific_runner_script": {"path": str(RUNNER_SCRIPT.relative_to(ROOT)), "sha256": sha256(RUNNER_SCRIPT)},
            "model_specific_runner_config": {"path": str(RUNNER_CONFIG.relative_to(ROOT)), "sha256": sha256(RUNNER_CONFIG)},
            "cpu_test_manifest": {"path": str(TEST_MANIFEST.relative_to(ROOT)), "sha256": sha256(TEST_MANIFEST)},
        },
        "test_status": test_manifest["status"],
        "gpu_execution_performed": False,
        "parameter_fitting_performed": False,
        "holdout_opened": False,
        "boundary": [
            "No gene-specific root neuron or edge mapping is asserted.",
            "No alpha-synuclein molecular dynamics or biological causality is asserted.",
            "A scientific GPU runner is not authorized by this audit.",
        ],
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "tests": test_manifest["status"], "gpu_execution_performed": False}, indent=2))
    return 0 if status != "AUDIT_FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
