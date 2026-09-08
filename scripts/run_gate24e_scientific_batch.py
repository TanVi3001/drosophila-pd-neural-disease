"""Freeze and execute the exact Gate24E scientific batch contract.

The default workflow is a read-only ``--dry-run``.  ``--execute`` is kept for
the separately authorized execution gate and is deliberately fail-closed:
there is no retry, resume, skip, overwrite, reordering, or scientific
analysis path in this module.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Sequence

try:
    from scripts.prepare_gate24e_scientific_batch_plan import (
        ARTIFACT_PROFILE,
        RUNTIME_COMMIT,
        canonical_plan_sha256,
    )
except ModuleNotFoundError:  # direct ``python scripts/<tool>.py`` invocation
    from prepare_gate24e_scientific_batch_plan import (
        ARTIFACT_PROFILE,
        RUNTIME_COMMIT,
        canonical_plan_sha256,
    )


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/scientific_batch_plan.json"
ACTIVATION_PATH = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/scientific_batch_activation.json"
EXECUTION_MANIFEST = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/scientific_batch_execution.json"
LOG_PATH = ROOT / "experiments/gate_24e_blinded_parkin_prediction/logs/scientific_batch_execution.log"
OUTPUT_ROOT = ROOT / "experiments/gate_24e_blinded_parkin_prediction/runs"

EXPECTED_PLAN_SHA256 = "4515e1916631b019711154dccb5fb887110d5572e3eb82b7ea5118c643db5aac"
EXPECTED_RUNTIME_PYTHON = Path(r"E:\Drosophila_Parkinson\drosophila-pd-flygym\.venv\Scripts\python.exe")
EXPECTED_RUNTIME_ROOT = Path(r"E:\Drosophila_Parkinson\drosophila-pd-flygym-gate24-memorysafe-clean")
EXPECTED_RUNTIME_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"
EXPECTED_FLYGYM_VERSION = "2.1.0"
EXPECTED_TORCH_VERSION = "2.5.1+cu121"
EXPECTED_CUDA_VERSION = "12.1"
EXPECTED_GPU_NAME = "NVIDIA GeForce RTX 3050 6GB Laptop GPU"
EXPECTED_ARTIFACT_PROFILE = "GATE24E_MEMORY_SAFE"
EXPECTED_HOLDOUT = "SEALED"
EXPECTED_JOB_COUNT = 25
EXPECTED_HEALTHY_COUNT = 5
EXPECTED_PARKIN_COUNT = 20
EXPECTED_SEEDS = [0, 1, 2, 3, 4]
EXPECTED_GRID = [0.0, 0.25, 0.5, 0.75, 1.0]
TECHNICAL_SEED = 9001
FINAL_ARTIFACT_BYTES = 558_250_361
TRANSIENT_BYTES = 667_690_631
RESERVE_FRACTION = 0.20
REQUIRED_STORAGE_BYTES = 17_548_739_588
COMPLETION_MARKER = "100000/100000"


class BatchContractError(RuntimeError):
    """Raised when a frozen technical contract is not satisfied."""


class TechnicalStop(RuntimeError):
    """Raised when one execution job violates the frozen failure policy."""


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise BatchContractError(f"missing JSON artifact: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BatchContractError(f"JSON artifact is not an object: {path}")
    return value


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _live_free_bytes() -> int:
    return int(shutil.disk_usage(ROOT).free)


def remaining_storage_requirement(remaining_job_count: int) -> int:
    """Return the strict technical requirement for remaining jobs."""

    if remaining_job_count < 0:
        raise ValueError("remaining_job_count must be non-negative")
    remaining_final = remaining_job_count * FINAL_ARTIFACT_BYTES
    remaining_peak = remaining_final + TRANSIENT_BYTES
    remaining_reserve = math.ceil(remaining_peak * RESERVE_FRACTION)
    return remaining_peak + remaining_reserve


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the frozen plan without constructing replacement jobs."""

    if canonical_plan_sha256(dict(plan)) != EXPECTED_PLAN_SHA256:
        raise BatchContractError("frozen scientific batch plan SHA256 mismatch")
    if plan.get("job_count") != EXPECTED_JOB_COUNT:
        raise BatchContractError("frozen plan must contain exactly 25 jobs")
    if plan.get("ordering") != "SEED_MAJOR":
        raise BatchContractError("frozen plan ordering is not SEED_MAJOR")
    if plan.get("scientific_seeds") != EXPECTED_SEEDS:
        raise BatchContractError("frozen seed list mismatch")
    if plan.get("parameter_grid") != EXPECTED_GRID:
        raise BatchContractError("frozen parameter grid mismatch")
    if plan.get("technical_seed_excluded") != TECHNICAL_SEED:
        raise BatchContractError("technical seed 9001 is not excluded")
    if plan.get("healthy_job_count") != EXPECTED_HEALTHY_COUNT:
        raise BatchContractError("healthy job count mismatch")
    if plan.get("parkin_job_count") != EXPECTED_PARKIN_COUNT:
        raise BatchContractError("Parkin job count mismatch")
    if plan.get("runtime_commit") != EXPECTED_RUNTIME_COMMIT:
        raise BatchContractError("runtime commit mismatch")
    if plan.get("runtime_python") != str(EXPECTED_RUNTIME_PYTHON):
        raise BatchContractError("runtime Python mismatch")
    if plan.get("runtime_root") != str(EXPECTED_RUNTIME_ROOT):
        raise BatchContractError("runtime root mismatch")
    if plan.get("artifact_profile") != EXPECTED_ARTIFACT_PROFILE:
        raise BatchContractError("artifact profile mismatch")
    if plan.get("holdout") != EXPECTED_HOLDOUT:
        raise BatchContractError("holdout is not sealed in the plan")
    jobs = plan.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != EXPECTED_JOB_COUNT:
        raise BatchContractError("frozen plan jobs are not a 25-item list")

    job_ids: set[str] = set()
    output_paths: set[str] = set()
    healthy_count = 0
    parkin_count = 0
    expected_index = 1
    for seed in EXPECTED_SEEDS:
        seed_jobs = jobs[(seed * 5) : (seed * 5) + 5]
        if len(seed_jobs) != 5:
            raise BatchContractError("seed-major block is incomplete")
        if seed_jobs[0].get("seed") != seed or seed_jobs[0].get("condition") != "healthy":
            raise BatchContractError("healthy job is not first in a seed-major block")
        for job_position, job in enumerate(seed_jobs):
            if not isinstance(job, dict):
                raise BatchContractError("plan job is not an object")
            if job.get("job_index") != expected_index:
                raise BatchContractError("job indices are not immutable sequential 1..25")
            expected_index += 1
            job_id = str(job.get("job_id", ""))
            output = str(job.get("output_directory", ""))
            if not job_id or job_id in job_ids:
                raise BatchContractError("duplicate or missing job ID")
            if not output or output.casefold() in output_paths:
                raise BatchContractError("duplicate or missing output directory")
            job_ids.add(job_id)
            output_paths.add(output.casefold())
            if job.get("seed") != seed:
                raise BatchContractError("seed-major ordering mismatch")
            if job_position == 0:
                if job.get("condition") != "healthy" or job.get("parameter") != 0.0:
                    raise BatchContractError("healthy job contract mismatch")
                healthy_count += 1
            else:
                if job.get("condition") != "parkin":
                    raise BatchContractError("non-healthy job has the wrong condition")
                if job.get("parameter") not in [0.25, 0.5, 0.75, 1.0]:
                    raise BatchContractError("Parkin p=0 or an unregistered parameter exists")
                parkin_count += 1
            command = job.get("command")
            if not isinstance(command, list) or not command:
                raise BatchContractError("job command is missing")
            if str(command[0]) != str(EXPECTED_RUNTIME_PYTHON):
                raise BatchContractError("job command does not use approved Python")
            if "--execute" in command or "--resume" in command or "--retry" in command:
                raise BatchContractError("job command contains a forbidden executor flag")
            if job.get("seed") == TECHNICAL_SEED:
                raise BatchContractError("technical seed appears in scientific jobs")
    if healthy_count != EXPECTED_HEALTHY_COUNT or parkin_count != EXPECTED_PARKIN_COUNT:
        raise BatchContractError("healthy/Parkin counts do not match the frozen contract")
    return dict(plan)


def load_and_validate_plan(path: Path = PLAN_PATH) -> dict[str, Any]:
    return validate_plan(_load_json(path))


def validate_activation(activation: Mapping[str, Any], plan: Mapping[str, Any]) -> None:
    if activation.get("status") != "READY_FOR_GATE24E_25_JOB_SCIENTIFIC_BATCH":
        raise BatchContractError("scientific batch activation is not READY")
    if activation.get("plan_sha256") != EXPECTED_PLAN_SHA256:
        raise BatchContractError("activation plan SHA mismatch")
    if activation.get("job_count") != EXPECTED_JOB_COUNT:
        raise BatchContractError("activation job count mismatch")
    if activation.get("scientific_batch_authorized") is not True:
        raise BatchContractError("scientific batch authorization is not true")
    if activation.get("holdout") != EXPECTED_HOLDOUT:
        raise BatchContractError("activation holdout is not sealed")
    if activation.get("scientific_jobs_executed") != 0:
        raise BatchContractError("activation already records scientific execution")
    if activation.get("output_root_exists") is not False:
        raise BatchContractError("activation output root state is not unused")
    if plan.get("job_count") != activation.get("job_count"):
        raise BatchContractError("activation does not match the loaded plan")


def validate_initial_execution_manifest(execution: Mapping[str, Any]) -> None:
    required = {
        "schema_version": "gate24e-scientific-batch-execution-v1",
        "status": "NOT_EXECUTED",
        "plan_sha256": EXPECTED_PLAN_SHA256,
        "planned_job_count": EXPECTED_JOB_COUNT,
        "executed_job_count": 0,
        "completed_job_count": 0,
        "failed_job_count": 0,
        "gpu_jobs_executed": 0,
        "simulation_jobs_executed": 0,
        "scientific_batch_authorized": True,
        "holdout": EXPECTED_HOLDOUT,
        "analysis_performed": False,
        "scientific_interpretation_performed": False,
    }
    for key, expected in required.items():
        if execution.get(key) != expected:
            raise BatchContractError(f"execution manifest field {key!r} is not initial")
    if execution.get("completed_job_ids") not in (None, []):
        raise BatchContractError("execution manifest already contains completed jobs")


def validate_runtime_environment(*, enforce_current_python: bool = True) -> dict[str, Any]:
    current_python = Path(sys.executable).resolve()
    expected_python = EXPECTED_RUNTIME_PYTHON.resolve()
    if enforce_current_python and current_python != expected_python:
        raise BatchContractError(f"wrong Python executable: {current_python}")
    python_version = ".".join(str(part) for part in sys.version_info[:3])
    if python_version != "3.12.10":
        raise BatchContractError(f"wrong Python version: {python_version}")
    flygym_version = importlib.metadata.version("flygym")
    if flygym_version != EXPECTED_FLYGYM_VERSION:
        raise BatchContractError(f"wrong FlyGym version: {flygym_version}")
    import torch

    torch_version = torch.__version__
    cuda_version = str(torch.version.cuda)
    cuda_available = bool(torch.cuda.is_available())
    gpu_name = torch.cuda.get_device_name(0) if cuda_available else "NONE"
    if torch_version != EXPECTED_TORCH_VERSION:
        raise BatchContractError(f"wrong Torch version: {torch_version}")
    if cuda_version != EXPECTED_CUDA_VERSION or not cuda_available:
        raise BatchContractError("CUDA runtime is not the approved available runtime")
    if gpu_name != EXPECTED_GPU_NAME:
        raise BatchContractError(f"wrong GPU: {gpu_name}")

    runtime_root = EXPECTED_RUNTIME_ROOT
    if not runtime_root.is_dir():
        raise BatchContractError("approved runtime root is missing")
    head = subprocess.check_output(
        ["git", "-C", str(runtime_root), "rev-parse", "HEAD"], text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "-C", str(runtime_root), "status", "--porcelain"], text=True
    ).strip()
    if head != EXPECTED_RUNTIME_COMMIT or status:
        raise BatchContractError("approved runtime worktree is not clean/frozen")
    return {
        "python": python_version,
        "python_executable": str(current_python),
        "flygym": flygym_version,
        "torch": torch_version,
        "cuda": cuda_version,
        "cuda_available": cuda_available,
        "gpu": gpu_name,
        "runtime_commit": head,
        "runtime_clean": not bool(status),
    }


def validate_runtime_git_contract() -> None:
    """Check the frozen platform commit and clean worktree without GPU work."""

    runtime_root = EXPECTED_RUNTIME_ROOT
    if not runtime_root.is_dir():
        raise BatchContractError("approved runtime root is missing")
    head = subprocess.check_output(
        ["git", "-C", str(runtime_root), "rev-parse", "HEAD"], text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "-C", str(runtime_root), "status", "--porcelain"], text=True
    ).strip()
    if head != EXPECTED_RUNTIME_COMMIT or status:
        raise BatchContractError("runtime provenance drift detected")


def run_preflight_audit() -> dict[str, Any]:
    try:
        from scripts import audit_gate24e_scientific_batch_preflight as preflight
    except ModuleNotFoundError:  # direct ``python scripts/<tool>.py`` invocation
        import audit_gate24e_scientific_batch_preflight as preflight

    result = preflight.audit()
    required = {
        "status": "READY_FOR_GATE24E_25_JOB_SCIENTIFIC_BATCH",
        "blockers": [],
        "authorization_valid": True,
        "capacity_pass": True,
        "checkpoint_hashes_pass": True,
        "holdout": EXPECTED_HOLDOUT,
    }
    for key, expected in required.items():
        if result.get(key) != expected:
            raise BatchContractError(f"preflight field {key!r} mismatch: {result.get(key)!r}")
    return result


def validate_job_output(output: Path, *, required_steps: int = 100_000) -> dict[str, Any]:
    status_path = output / "status.json"
    if not status_path.is_file():
        raise TechnicalStop(f"missing status.json: {output}")
    status = _load_json(status_path)
    if status.get("status") != "PASS" or status.get("simulation_run") is not True:
        raise TechnicalStop(f"status contract failed: {output}")
    required_files = (
        "rollout.npz",
        "metadata.json",
        "manifest.json",
        "metrics/metrics.json",
    )
    for relative in required_files:
        if not (output / relative).is_file():
            raise TechnicalStop(f"required output missing: {output / relative}")
    manifest = _load_json(output / "manifest.json")
    if manifest.get("artifact_profile") != EXPECTED_ARTIFACT_PROFILE:
        raise TechnicalStop(f"artifact profile failed: {output}")
    marker = False
    for log in output.rglob("*.log"):
        if COMPLETION_MARKER in log.read_text(encoding="utf-8", errors="ignore"):
            marker = True
            break
    if not marker:
        raise TechnicalStop(f"completion marker missing: {output}")
    artifact_bytes = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
    return {"artifact_bytes": artifact_bytes, "completion_marker_observed": True}


def _append_technical_log(record: Mapping[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), sort_keys=True) + "\n")


def _technical_stop_manifest(execution: dict[str, Any], *, reason: str, job: Mapping[str, Any] | None) -> None:
    execution.update(
        {
            "status": "GATE24E_SCIENTIFIC_BATCH_TECHNICAL_STOP",
            "technical_stop_reason": reason,
            "failed_job_count": 1 if job else 0,
            "failed_job_id": job.get("job_id") if job else None,
            "next_allowed_action": "HUMAN_REVIEW_GATE24E_SCIENTIFIC_BATCH_TECHNICAL_STOP",
            "updated_at_utc": _utc_now(),
        }
    )
    _write_json_atomic(EXECUTION_MANIFEST, execution)


def _run_child(command: Sequence[str]) -> tuple[int, float, float]:
    started = time.time()
    process = subprocess.Popen(
        list(command),
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        return_code = process.wait()
    except KeyboardInterrupt as exc:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise TechnicalStop("KeyboardInterrupt: current child terminated; no retry") from exc
    return return_code, started, time.time()


def execute_batch(
    plan: Mapping[str, Any],
    *,
    environment: Mapping[str, Any] | None = None,
    child_runner: Callable[[Sequence[str]], tuple[int, float, float]] = _run_child,
) -> dict[str, Any]:
    """Execute sequentially after all gates pass; never retry or resume."""

    validate_plan(plan)
    validate_activation(_load_json(ACTIVATION_PATH), plan)
    execution = _load_json(EXECUTION_MANIFEST)
    validate_initial_execution_manifest(execution)
    if OUTPUT_ROOT.exists():
        raise BatchContractError("scientific output root already exists; overwrite forbidden")
    run_preflight_audit()
    environment = environment or validate_runtime_environment()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    execution.update(
        {
            "status": "EXECUTION_IN_PROGRESS",
            "started_at_utc": _utc_now(),
            "executed_job_count": 0,
            "completed_job_count": 0,
            "failed_job_count": 0,
            "completed_job_ids": [],
            "runtime_environment": dict(environment),
        }
    )
    _write_json_atomic(EXECUTION_MANIFEST, execution)

    for job in plan["jobs"]:
        validate_runtime_git_contract()
        output = Path(str(job["output_directory"]))
        if output.exists():
            _technical_stop_manifest(execution, reason="output overwrite forbidden", job=job)
            raise TechnicalStop(f"output already exists: {output}")
        remaining = EXPECTED_JOB_COUNT - int(job["job_index"]) + 1
        free_before = _live_free_bytes()
        required = remaining_storage_requirement(remaining)
        if free_before <= required:
            _technical_stop_manifest(execution, reason="insufficient storage before job", job=job)
            raise TechnicalStop(f"storage safety check failed before {job['job_id']}")
        started_at = _utc_now()
        try:
            return_code, started_epoch, ended_epoch = child_runner(job["command"])
        except KeyboardInterrupt as exc:
            reason = "KeyboardInterrupt: current child terminated; no retry"
            _append_technical_log(
                {
                    "timestamp": _utc_now(),
                    "job_index": job["job_index"],
                    "job_id": job["job_id"],
                    "seed": job["seed"],
                    "condition": job["condition"],
                    "parameter": job["parameter"],
                    "process_start": started_at,
                    "process_end": _utc_now(),
                    "return_code": None,
                    "completion_marker_observed": False,
                    "artifact_validation": "FAIL",
                    "free_bytes_before": free_before,
                    "free_bytes_after": _live_free_bytes(),
                    "output_artifact_bytes": 0,
                    "technical_stop": reason,
                }
            )
            _technical_stop_manifest(execution, reason=reason, job=job)
            raise TechnicalStop(reason) from exc
        except MemoryError as exc:
            reason = "MemoryError: technical stop; no retry"
            _append_technical_log(
                {
                    "timestamp": _utc_now(),
                    "job_index": job["job_index"],
                    "job_id": job["job_id"],
                    "seed": job["seed"],
                    "condition": job["condition"],
                    "parameter": job["parameter"],
                    "process_start": started_at,
                    "process_end": _utc_now(),
                    "return_code": None,
                    "completion_marker_observed": False,
                    "artifact_validation": "FAIL",
                    "free_bytes_before": free_before,
                    "free_bytes_after": _live_free_bytes(),
                    "output_artifact_bytes": 0,
                    "technical_stop": reason,
                }
            )
            _technical_stop_manifest(execution, reason=reason, job=job)
            raise TechnicalStop(reason) from exc
        except TechnicalStop as exc:
            _append_technical_log(
                {
                    "timestamp": _utc_now(),
                    "job_index": job["job_index"],
                    "job_id": job["job_id"],
                    "seed": job["seed"],
                    "condition": job["condition"],
                    "parameter": job["parameter"],
                    "process_start": started_at,
                    "process_end": _utc_now(),
                    "return_code": None,
                    "completion_marker_observed": False,
                    "artifact_validation": "FAIL",
                    "free_bytes_before": free_before,
                    "free_bytes_after": _live_free_bytes(),
                    "output_artifact_bytes": 0,
                    "technical_stop": str(exc),
                }
            )
            _technical_stop_manifest(execution, reason=str(exc), job=job)
            raise
        free_after = _live_free_bytes()
        technical = {
            "timestamp": _utc_now(),
            "job_index": job["job_index"],
            "job_id": job["job_id"],
            "seed": job["seed"],
            "condition": job["condition"],
            "parameter": job["parameter"],
            "process_start": started_at,
            "process_end": _utc_now(),
            "return_code": return_code,
            "completion_marker_observed": False,
            "artifact_validation": "FAIL",
            "free_bytes_before": free_before,
            "free_bytes_after": free_after,
            "output_artifact_bytes": 0,
        }
        if return_code != 0:
            _append_technical_log(technical)
            _technical_stop_manifest(execution, reason=f"return code {return_code}", job=job)
            raise TechnicalStop(f"job {job['job_id']} returned {return_code}")
        try:
            completion = validate_job_output(output)
        except (TechnicalStop, OSError, ValueError) as exc:
            technical["technical_stop"] = str(exc)
            _append_technical_log(technical)
            _technical_stop_manifest(execution, reason=str(exc), job=job)
            raise
        technical["completion_marker_observed"] = True
        technical["artifact_validation"] = "PASS"
        technical["output_artifact_bytes"] = completion["artifact_bytes"]
        _append_technical_log(technical)
        completed_ids = list(execution.get("completed_job_ids", []))
        completed_ids.append(job["job_id"])
        execution.update(
            {
                "executed_job_count": job["job_index"],
                "completed_job_count": len(completed_ids),
                "completed_job_ids": completed_ids,
                "last_completed_job_index": job["job_index"],
                "last_completed_job_id": job["job_id"],
                "free_bytes": free_after,
                "artifact_byte_total": sum(
                    int(item.get("artifact_byte_total", 0)) for item in [execution]
                )
                + completion["artifact_bytes"],
                "updated_at_utc": _utc_now(),
            }
        )
        _write_json_atomic(EXECUTION_MANIFEST, execution)

    execution.update(
        {
            "status": "GATE24E_25_JOB_SCIENTIFIC_BATCH_COMPLETE_UNANALYZED",
            "failed_job_count": 0,
            "analysis_performed": False,
            "scientific_interpretation_performed": False,
            "next_allowed_action": "FREEZE_IMMUTABLE_VIRTUAL_PREDICTION_BEFORE_HOLDOUT",
            "updated_at_utc": _utc_now(),
        }
    )
    _write_json_atomic(EXECUTION_MANIFEST, execution)
    return execution


def dry_run(plan: Mapping[str, Any], preflight: Mapping[str, Any], environment: Mapping[str, Any]) -> None:
    validate_plan(plan)
    validate_activation(_load_json(ACTIVATION_PATH), plan)
    validate_initial_execution_manifest(_load_json(EXECUTION_MANIFEST))
    if OUTPUT_ROOT.exists():
        raise BatchContractError("scientific output root must not exist for dry-run")
    if preflight.get("status") != "READY_FOR_GATE24E_25_JOB_SCIENTIFIC_BATCH":
        raise BatchContractError("dry-run preflight is not READY")
    remaining_required = remaining_storage_requirement(EXPECTED_JOB_COUNT)
    print("READY_TO_EXECUTE_EXACT_GATE24E_25_JOB_BATCH")
    print(f"plan_sha256: {EXPECTED_PLAN_SHA256}")
    print(f"job_count: {EXPECTED_JOB_COUNT}")
    print(f"healthy_job_count: {EXPECTED_HEALTHY_COUNT}")
    print(f"parkin_job_count: {EXPECTED_PARKIN_COUNT}")
    print(f"ordering: {plan['ordering']}")
    print(f"runtime: {plan['runtime_root']}")
    print(f"runtime_commit: {EXPECTED_RUNTIME_COMMIT}")
    print(f"remaining_storage_requirement_bytes: {remaining_required}")
    print(f"live_free_bytes: {_live_free_bytes()}")
    print(f"holdout: {EXPECTED_HOLDOUT}")
    print(f"python: {environment['python']}")
    print(f"flygym: {environment['flygym']}")
    print(f"torch: {environment['torch']}")
    print("gpu_executed: false")
    print("simulation_executed: false")
    print("scientific_jobs_executed: 0")
    print("execution_manifest_status: NOT_EXECUTED")
    print("output_root_created: false")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--execute", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        plan = load_and_validate_plan()
        validate_activation(_load_json(ACTIVATION_PATH), plan)
        validate_initial_execution_manifest(_load_json(EXECUTION_MANIFEST))
        if OUTPUT_ROOT.exists():
            raise BatchContractError("scientific output root already exists")
        preflight = run_preflight_audit()
        environment = validate_runtime_environment()
        if args.dry_run:
            dry_run(plan, preflight, environment)
            return 0
        execute_batch(plan, environment=environment)
        return 0
    except (BatchContractError, TechnicalStop) as exc:
        print(f"GATE24E_EXECUTOR_STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
