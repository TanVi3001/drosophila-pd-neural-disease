#!/usr/bin/env python3
"""Run or dry-run the gated alpha-synuclein/dopamine job matrix.

The default action is a CPU-only dry run.  ``--execute`` is intentionally
guarded by the reviewed runner protocol and the separate human execution
authorization.  It performs exactly one subprocess attempt per job and never
retries or overwrites an existing output root.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from drosophila_pd_neural.alpha_syn_dopamine_runner import (  # noqa: E402
    AlphaSynDopamineJob,
    AlphaSynDopamineSpec,
    build_job_matrix,
    load_spec,
    resolve_condition,
)


DEFAULT_CONFIG = ROOT / "experiments/alpha_syn_dopamine/configs/alpha_syn_dopamine_runner_v1.yaml"
PREP = ROOT / "research/alpha_syn_dopamine_preparation"
REVIEW_SIGNOFF = PREP / "alpha_syn_dopamine_updated_registry_prereg_review_signoff_v1.json"
AUTH = PREP / "alpha_syn_dopamine_execution_authorization_v1.json"
RUNNER_AUDIT = PREP / "alpha_syn_dopamine_runner_audit_v1.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(UTC).isoformat()


def _job_record(spec: AlphaSynDopamineSpec, job: AlphaSynDopamineJob) -> dict[str, Any]:
    condition = resolve_condition(spec, job.state, seed=job.seed)
    target_digest = hashlib.sha256("\n".join(condition.target_neurons).encode("utf-8")).hexdigest()
    return {
        "job_id": job.job_id,
        "state": job.state,
        "seed": job.seed,
        "condition_id": condition.condition_id,
        "gene_model": condition.gene_model,
        "age_days": condition.age_days,
        "target_neuron_count": len(condition.target_neurons),
        "target_neurons_sha256": target_digest,
        "target_edge_count": len(condition.target_edges),
        "parameters": condition.parameters.to_dict(),
        "simulation_executed": False,
    }


def dry_run(spec: AlphaSynDopamineSpec, output: Path) -> dict[str, Any]:
    jobs = build_job_matrix(spec)
    payload = {
        "schema_version": "alpha-syn-dopamine-runner-dry-run-v1",
        "created_at_utc": now(),
        "status": "DRY_RUN_PASS",
        "runner_id": "ALPHA_SYN_DOPAMINE_RUNNER_V1",
        "config": str(spec.config_path),
        "config_sha256": sha256(spec.config_path),
        "model_scope": spec.model_scope,
        "gene_specific_mapping": spec.gene_specific_mapping,
        "protocol_review_status": spec.protocol_review_status,
        "parameter_lock_status": spec.parameter_lock_status,
        "job_count": len(jobs),
        "jobs": [_job_record(spec, job) for job in jobs],
        "simulation_executed": False,
        "gpu_execution_performed": False,
        "parameter_fitting_performed": False,
        "holdout_opened": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _require_execution_authorization(spec: AlphaSynDopamineSpec) -> dict[str, Any]:
    review = json.loads(REVIEW_SIGNOFF.read_text(encoding="utf-8"))
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    runner_audit = json.loads(RUNNER_AUDIT.read_text(encoding="utf-8"))
    if review.get("status") != "DUAL_HUMAN_UPDATED_REGISTRY_AND_PREREG_REVIEW_PASS":
        raise RuntimeError("Dual-human registry/preregistration review is not PASS.")
    if spec.protocol_review_status != "DUAL_HUMAN_RUNNER_PROTOCOL_REVIEW_PASS":
        raise RuntimeError("Runner protocol review is not PASS.")
    if spec.parameter_lock_status != "LOCKED_FOR_EXECUTION":
        raise RuntimeError("Runner parameters are not locked for execution.")
    if runner_audit.get("status") != "READY_FOR_EXPLICIT_HUMAN_GPU_AUTHORIZATION":
        raise RuntimeError(f"Runner audit is not ready: {runner_audit.get('status')}.")
    if auth.get("authorized") is not True or auth.get("gpu_execution_authorized") is not True:
        raise RuntimeError("Explicit human GPU execution authorization is not active.")
    if auth.get("authorized_jobs") != len(build_job_matrix(spec)):
        raise RuntimeError("Authorization job count does not match the locked matrix.")
    return auth


def _runtime_python(spec: AlphaSynDopamineSpec) -> Path:
    candidate = spec.platform_root / ".venv/Scripts/python.exe"
    if candidate.is_file():
        return candidate
    candidate = spec.platform_root / ".venv/bin/python"
    if candidate.is_file():
        return candidate
    return Path(sys.executable)


def _job_config(spec: AlphaSynDopamineSpec, job: AlphaSynDopamineJob) -> dict[str, Any]:
    condition = resolve_condition(spec, job.state, seed=job.seed)
    return {
        "condition_id": condition.condition_id,
        "gene_model": condition.gene_model,
        "seed": condition.seed,
        "target_neurons": list(condition.target_neurons),
        "target_edges": [{"pre": pre, "post": post} for pre, post in condition.target_edges],
        "full_burden": condition.parameters.to_dict(),
        "burden_curve": [{"age_days": condition.age_days, "burden": 1.0}],
        "provenance": ["ALPHA_SYN_DOPAMINE_RUNNER_V1", str(spec.config_path)],
        "notes": condition.notes,
    }


def execute(spec: AlphaSynDopamineSpec, output_root: Path) -> dict[str, Any]:
    auth = _require_execution_authorization(spec)
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError(f"Refusing to overwrite non-empty output root: {output_root}")
    if not spec.backend.is_file():
        raise RuntimeError(f"Backend runner not found: {spec.backend}")
    for path in (spec.brain_root, spec.platform_root, spec.annotations):
        if not path.exists():
            raise RuntimeError(f"Runtime input missing: {path}")

    output_root.mkdir(parents=True, exist_ok=False)
    jobs = build_job_matrix(spec)
    runtime_python = _runtime_python(spec)
    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="alpha-syn-dopamine-configs-") as temp_dir:
        temp_root = Path(temp_dir)
        for job in jobs:
            output = output_root / job.job_id
            if output.exists():
                raise RuntimeError(f"Refusing to overwrite existing job output: {output}")
            output.mkdir(parents=True)
            job_config = temp_root / f"{job.job_id}.yaml"
            job_config.write_text(yaml.safe_dump(_job_config(spec, job), sort_keys=False), encoding="utf-8")
            command = [
                str(runtime_python),
                str(spec.backend),
                "--brain-root", str(spec.brain_root),
                "--platform-root", str(spec.platform_root),
                "--brain-python", str(runtime_python),
                "--config", str(job_config),
                "--annotations", str(spec.annotations),
                "--age-days", str(spec.age_days),
                "--seed", str(job.seed),
                "--steps", str(spec.steps),
                "--device", spec.device,
                "--output", str(output),
            ]
            log = output / "runner.log"
            with log.open("w", encoding="utf-8") as handle:
                result = subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=False, env=os.environ.copy())
            record = {
                "job_id": job.job_id,
                "seed": job.seed,
                "state": job.state,
                "return_code": result.returncode,
                "output": str(output),
                "command": command,
                "automatic_retry": False,
            }
            records.append(record)
            if result.returncode != 0:
                summary = {
                    "schema_version": "alpha-syn-dopamine-runner-execution-v1",
                    "created_at_utc": now(),
                    "status": "FAILED_NO_RETRY",
                    "authorization_id": auth["authorization_id"],
                    "jobs": records,
                    "simulation_executed": True,
                    "gpu_execution_performed": spec.device == "cuda",
                    "automatic_retry": False,
                }
                (output_root / "execution_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
                return summary

    summary = {
        "schema_version": "alpha-syn-dopamine-runner-execution-v1",
        "created_at_utc": now(),
        "status": "COMPLETE",
        "authorization_id": auth["authorization_id"],
        "job_count": len(records),
        "jobs": records,
        "simulation_executed": True,
        "gpu_execution_performed": spec.device == "cuda",
        "automatic_retry": False,
    }
    (output_root / "execution_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Resolve the 15-job matrix without simulation/GPU.")
    parser.add_argument("--execute", action="store_true", help="Run only after all authorization guards pass.")
    args = parser.parse_args(argv)
    if args.dry_run and args.execute:
        parser.error("Choose either --dry-run or --execute.")
    try:
        spec = load_spec(args.config.resolve(), project_root=ROOT)
        if args.execute:
            output = (args.output or spec.output_root).resolve()
            result = execute(spec, output)
        else:
            output = (args.output or (PREP / "alpha_syn_dopamine_runner_dry_run_manifest.json")).resolve()
            result = dry_run(spec, output)
        print(json.dumps({"status": result["status"], "output": str(output), "gpu_execution_performed": result.get("gpu_execution_performed", False)}, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError, KeyError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
