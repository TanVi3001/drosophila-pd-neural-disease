"""Build and execute the reviewed Gate24E Parkin runtime job matrix.

Dry-run is the default review path. It validates all frozen provenance and
writes a deterministic 25-job plan without launching the canonical runner.
Execution is deliberately explicit and stops at the first technical failure;
it never retries or selects jobs from observed results.
"""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RUNNER = ROOT / "scripts" / "run_neural_experiment.py"
FREEZE = ROOT / "research/validation/prospective/parkin_model_freeze.yaml"
CONTRACT = ROOT / "research/validation/prospective/parkin_prediction_contract.yaml"
GRID = ROOT / "research/validation/prospective/parkin_checkpoint_grid_manifest.json"
SIGNOFF = ROOT / "research/validation/prospective/parkin_prediction_reviewer_signoff.json"
CONFIG = ROOT / "experiments/gate_24_prospective_validation/configs/gate24_execution_config.yaml"
PLAN = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/job_plan.json"
COMMAND_MANIFEST = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/command_manifest.json"
EXECUTION_MANIFEST = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/execution_manifest.json"
MAPPING = ROOT / "research/validation/gene_specific/parkin/driver_to_connectome_mapping.csv"
BRAIN_ROOT = ROOT.parent / "external" / "fly-brain-audit"
PLATFORM_ROOT = ROOT.parent / "drosophila-pd-flygym-gate24-clean"
EXPECTED_PLATFORM_COMMIT = "3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06"
REQUIRED_BRAIN_FILES = (
    "brain_body_bridge.py",
    "code/run_pytorch.py",
    "data/2025_Completeness_783.csv",
    "data/2025_Connectivity_783.parquet",
    "data/plastic_weights.pt",
)
REQUIRED_PRIMARY_METRICS = ("median_planar_speed_mm_s", "distance_traveled_mm")


class AdapterError(RuntimeError):
    """Raised when the frozen runtime plan cannot be built or continued."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AdapterError(f"Missing JSON artifact: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AdapterError(f"Expected JSON object: {path}")
    return value


def _yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AdapterError(f"Missing YAML artifact: {path}")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AdapterError(f"Expected YAML mapping: {path}")
    return value


def _resolve_repo_path(value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else (ROOT / path).resolve()


def _git(platform: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(platform), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise AdapterError(f"Git command failed in {platform}: {result.stderr.strip()}")
    return result.stdout.strip()


def _root_set_sha256(path: Path) -> tuple[int, str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    roots = sorted(str(row.get("root_id", "")).strip() for row in rows)
    if not roots or any(not root.isdigit() for root in roots) or len(roots) != len(set(roots)):
        raise AdapterError("Reviewed mapping root IDs are missing, non-numeric, or duplicated.")
    return len(roots), hashlib.sha256(("\n".join(roots) + "\n").encode("utf-8")).hexdigest()


def _cuda_preflight() -> dict[str, Any]:
    code = (
        "import json, torch; "
        "ok=bool(torch.cuda.is_available()); "
        "print(json.dumps({'torch':torch.__version__, 'cuda':torch.version.cuda, "
        "'available':ok, 'device':torch.cuda.get_device_name(0) if ok else 'NO_GPU'}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        return {
            "available": False,
            "device": "NO_GPU",
            "torch": "UNAVAILABLE",
            "cuda": "UNAVAILABLE",
            "error": result.stderr.strip(),
        }
    try:
        value = json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise AdapterError(f"Unable to parse CUDA preflight: {result.stdout!r}") from exc
    return value


def _validate_runtime(freeze: dict[str, Any], grid: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    if not RUNNER.is_file():
        raise AdapterError(f"Canonical runner is missing: {RUNNER}")
    runtime = freeze.get("runtime") or {}
    platform_commit = _git(PLATFORM_ROOT, "rev-parse", "HEAD")
    if _git(PLATFORM_ROOT, "status", "--porcelain"):
        raise AdapterError("Clean FlyGym runtime worktree is dirty.")
    locked_prefix = str(runtime.get("flygym_commit", "")).strip()
    if not locked_prefix or not platform_commit.startswith(locked_prefix) or platform_commit != EXPECTED_PLATFORM_COMMIT:
        raise AdapterError(f"FlyGym commit mismatch: locked={locked_prefix}, actual={platform_commit}")
    missing = [str(BRAIN_ROOT / relative) for relative in REQUIRED_BRAIN_FILES if not (BRAIN_ROOT / relative).is_file()]
    if missing:
        raise AdapterError("Brain runtime is incomplete: " + ", ".join(missing))
    if config.get("execution_policy", {}).get("holdout_opened") is not False:
        raise AdapterError("Execution config opens the holdout.")
    if config.get("execution_policy", {}).get("run_simulation") is not False:
        raise AdapterError("Execution config must remain pre-GPU and simulation-off.")
    if config.get("execution_policy", {}).get("run_gpu") is True:
        raise AdapterError("Execution config must remain pre-GPU and GPU-off.")
    if config.get("execution_policy", {}).get("run_calibration") is not False:
        raise AdapterError("Execution config must not run calibration.")
    if config.get("execution_policy", {}).get("run_tuning") is not False:
        raise AdapterError("Execution config must not run tuning.")
    return {
        "platform_commit": platform_commit,
        "platform_worktree_clean": True,
        "brain_root_exists": BRAIN_ROOT.is_dir(),
        "runner_sha256": _sha256(RUNNER),
    }


def _validate_frozen_inputs() -> dict[str, Any]:
    from scripts.audit_gate24_prediction_readiness import audit
    from scripts.audit_holdout_firewall import audit as audit_firewall

    freeze = _yaml(FREEZE)
    contract = _yaml(CONTRACT)
    grid = _json(GRID)
    signoff = _json(SIGNOFF)
    config = _yaml(CONFIG)
    readiness = audit()
    firewall = audit_firewall()
    if readiness.get("gate24e_status") != "READY_FOR_BLINDED_GPU_PREDICTION":
        raise AdapterError(f"Gate24E is not ready: {readiness.get('blockers')}")
    if readiness.get("gate24d_status") != "PROSPECTIVE_PREDICTION_LOCKED":
        raise AdapterError("Gate24D is not locked.")
    if readiness.get("holdout_status") != "SEALED" or firewall.get("status") != "SEALED":
        raise AdapterError("Holdout firewall is not sealed.")
    if readiness.get("holdout_opened") is not False or readiness.get("holdout_used_for_tuning") is not False:
        raise AdapterError("Readiness audit reports holdout access.")
    if signoff.get("holdout_opened") is not False or signoff.get("tuning_using_holdout") is not False:
        raise AdapterError("Reviewer signoff reports holdout access.")
    if contract.get("action_proxy_primary") is not False:
        raise AdapterError("Action-level proxy cannot be primary.")
    if freeze.get("parameter_policy") != "PREREGISTERED_GRID_NO_SINGLE_BIOLOGICAL_PARAMETER":
        raise AdapterError("Frozen parameter policy is not the reviewed grid policy.")
    if config.get("execution_policy", {}).get("gpu") != "cuda":
        raise AdapterError("Frozen execution device is not CUDA.")

    config_seeds = list(config.get("seed_list", []))
    if config_seeds != list(freeze.get("seed_list", [])) or config_seeds != list(contract.get("seed_list", [])):
        raise AdapterError("Seed list differs between frozen config, freeze, and prediction contract.")
    physics = config.get("physics") or {}
    frozen_physics = freeze.get("physics") or {}
    for key in ("steps", "duration_s", "timestep_s"):
        if key in frozen_physics and physics.get(key) != frozen_physics.get(key):
            raise AdapterError(f"Frozen physics mismatch for {key}.")
    configured_primary = list((config.get("metrics") or {}).get("primary_virtual", []))
    contract_primary = [contract.get("virtual_primary_metric"), contract.get("virtual_secondary_metric")]
    if configured_primary != contract_primary:
        raise AdapterError("Primary metric contract differs from execution config.")

    mapping_count, root_hash = _root_set_sha256(MAPPING)
    mapping_sha = _sha256(MAPPING)
    if mapping_count != grid.get("target_count") or mapping_count != 330:
        raise AdapterError(f"Mapping count mismatch: {mapping_count}")
    if mapping_sha != grid.get("mapping_sha256") or root_hash != grid.get("target_sha256"):
        raise AdapterError("Mapping or target root-set SHA256 does not match the grid manifest.")

    healthy = grid.get("healthy_checkpoint") or {}
    healthy_path = _resolve_repo_path(healthy.get("path", ""))
    if not healthy_path.is_file() or _sha256(healthy_path) != healthy.get("sha256"):
        raise AdapterError("Healthy checkpoint SHA256 verification failed.")
    disease_rows = grid.get("checkpoints") or []
    if grid.get("disease_parameters") != [row.get("parameter") for row in disease_rows]:
        raise AdapterError("Disease checkpoint order does not match the frozen grid.")
    for row in disease_rows:
        checkpoint = _resolve_repo_path(row.get("checkpoint_path", ""))
        if not checkpoint.is_file() or _sha256(checkpoint) != row.get("checkpoint_sha256"):
            raise AdapterError(f"Disease checkpoint SHA256 verification failed for {row.get('parameter')}.")
        if row.get("identity_test_status") != "PASS":
            raise AdapterError(f"Identity test is not PASS for {row.get('parameter')}.")
        manifest_path = _resolve_repo_path(row.get("manifest_path", ""))
        manifest = _json(manifest_path)
        disease_manifest = manifest.get("disease_checkpoint") or {}
        if (
            manifest.get("parameter") != row.get("parameter")
            or disease_manifest.get("sha256") != row.get("checkpoint_sha256")
            or manifest.get("mapping_sha256") != mapping_sha
            or manifest.get("target_neurons_sha256") != root_hash
            or manifest.get("healthy_checkpoint_modified") is not False
        ):
            raise AdapterError(f"Checkpoint manifest provenance mismatch for {row.get('parameter')}.")

    runtime = _validate_runtime(freeze, grid, config)
    cuda = _cuda_preflight()
    free_bytes = shutil.disk_usage(ROOT).free
    comparable_runs = list((ROOT / "experiments" / "gate_24e_blinded_parkin_prediction" / "runs").glob("**/status.json"))
    prior_bytes = 0
    for status_path in comparable_runs:
        if json.loads(status_path.read_text(encoding="utf-8")).get("status") == "PASS":
            prior_bytes += sum(path.stat().st_size for path in status_path.parent.rglob("*") if path.is_file())
    return {
        "freeze": freeze,
        "contract": contract,
        "grid": grid,
        "config": config,
        "readiness": readiness,
        "firewall": firewall,
        "runtime": runtime,
        "cuda": cuda,
        "free_space_before_run_bytes": free_bytes,
        "prior_comparable_artifact_bytes": prior_bytes or None,
        "storage_requirement_status": "EMPIRICAL_PRIOR_ARTIFACTS_FOUND" if prior_bytes else "STORAGE_REQUIREMENT_NOT_EMPIRICALLY_ESTIMATED",
        "mapping_sha256": mapping_sha,
        "target_sha256": root_hash,
        "healthy_checkpoint_path": healthy_path,
        "healthy_checkpoint_sha256": healthy.get("sha256"),
        "disease_rows": disease_rows,
        "required_metrics": contract_primary,
    }


def _parameter_label(value: float) -> str:
    return f"{value:.2f}".replace(".", "_")


def _command(*, brain_root: Path, platform_root: Path, output: Path, seed: int, steps: int, device: str, checkpoint: Path | None) -> list[str]:
    command = [
        str(sys.executable),
        str(RUNNER),
        "--brain-root",
        str(brain_root),
        "--platform-root",
        str(platform_root),
        "--seed",
        str(seed),
        "--steps",
        str(steps),
        "--device",
        device,
        "--output",
        str(output),
    ]
    if checkpoint is not None:
        command.extend(["--prepared-checkpoint", str(checkpoint)])
    if "--parameter" in command:
        raise AdapterError("Canonical command must not contain --parameter.")
    return command


def _job_hash(jobs: list[dict[str, Any]]) -> str:
    payload = json.dumps(jobs, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_job_plan() -> dict[str, Any]:
    context = _validate_frozen_inputs()
    freeze = context["freeze"]
    config = context["config"]
    grid = context["grid"]
    seeds = list(config["seed_list"])
    steps = int(config["physics"]["steps"])
    duration_s = float(config["physics"]["duration_s"])
    timestep_s = float(config["physics"]["timestep_s"])
    device = str(config["execution_policy"]["gpu"])
    required_metrics = list(context["required_metrics"])
    jobs: list[dict[str, Any]] = []
    order_index = 1
    for seed in seeds:
        conditions = [("healthy", float(grid["healthy_checkpoint"]["identity_parameter"]), None, None)]
        for row in context["disease_rows"]:
            conditions.append(("parkin", float(row["parameter"]), row, _resolve_repo_path(row["checkpoint_path"])))
        for condition, parameter, row, checkpoint in conditions:
            condition_label = "healthy" if condition == "healthy" else f"parkin_{_parameter_label(parameter)}"
            output = ROOT / "experiments" / "gate_24e_blinded_parkin_prediction" / "runs" / condition_label / f"seed_{seed}"
            job_id = f"{condition_label}_seed_{seed}"
            jobs.append(
                {
                    "order_index": order_index,
                    "job_id": job_id,
                    "condition": condition,
                    "parameter": parameter,
                    "seed": seed,
                    "prepared_checkpoint_path": str(checkpoint) if checkpoint else None,
                    "prepared_checkpoint_sha256": row.get("checkpoint_sha256") if row else None,
                    "healthy_checkpoint_sha256": context["healthy_checkpoint_sha256"],
                    "mapping_sha256": context["mapping_sha256"],
                    "target_sha256": context["target_sha256"],
                    "steps": steps,
                    "duration_s": duration_s,
                    "timestep_s": timestep_s,
                    "device": device,
                    "brain_root": str(BRAIN_ROOT),
                    "platform_root": str(PLATFORM_ROOT),
                    "platform_commit": context["runtime"]["platform_commit"],
                    "output_path": str(output),
                    "command": _command(
                        brain_root=BRAIN_ROOT,
                        platform_root=PLATFORM_ROOT,
                        output=output,
                        seed=seed,
                        steps=steps,
                        device=device,
                        checkpoint=checkpoint,
                    ),
                    "required_metrics": required_metrics,
                }
            )
            order_index += 1
    if len(jobs) != 25:
        raise AdapterError(f"Expected 25 jobs, built {len(jobs)}")
    return {
        "schema_version": "gate24e-runtime-job-plan-v1",
        "status": "READY_FOR_25_BLINDED_GPU_JOBS",
        "job_count": len(jobs),
        "healthy_job_count": sum(job["condition"] == "healthy" for job in jobs),
        "parkin_job_count": sum(job["condition"] == "parkin" for job in jobs),
        "parameter_grid": [float(grid["healthy_checkpoint"]["identity_parameter"])] + [float(row["parameter"]) for row in context["disease_rows"]],
        "seed_list": seeds,
        "execution_order": "seed-major: healthy then Parkin grid levels for each seed",
        "job_matrix_sha256": _job_hash(jobs),
        "jobs": jobs,
        "holdout_opened": False,
        "holdout_status": "SEALED",
        "tuning_using_holdout": False,
        "posthoc_parameter_selection_allowed": False,
        "video": False,
        "gpu_jobs_executed": 0,
        "simulation_jobs_executed": 0,
        "free_space_before_run_bytes": context["free_space_before_run_bytes"],
        "storage_requirement_status": context["storage_requirement_status"],
        "prior_comparable_artifact_bytes": context["prior_comparable_artifact_bytes"],
        "cuda_preflight": context["cuda"],
        "runtime": context["runtime"],
        "neural_implementation_commit": freeze["model_commit"],
        "parameter_policy": freeze["parameter_policy"],
        "required_metrics": required_metrics,
        "command_manifest_path": str(COMMAND_MANIFEST),
        "execution_manifest_path": str(EXECUTION_MANIFEST),
    }


def write_job_plan(plan: dict[str, Any], path: Path = PLAN) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        existing = _json(path)
        if existing.get("job_matrix_sha256") != plan.get("job_matrix_sha256") or existing.get("jobs") != plan.get("jobs"):
            raise AdapterError("Existing job plan differs; refusing to overwrite an immutable plan.")
        return
    path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")


def write_command_manifest(plan: dict[str, Any], path: Path = COMMAND_MANIFEST) -> None:
    """Persist the exact command matrix without launching any command."""

    document = {
        "schema_version": "gate24e-command-manifest-v1",
        "status": "READY_FOR_25_BLINDED_GPU_JOBS",
        "job_matrix_sha256": plan["job_matrix_sha256"],
        "job_count": plan["job_count"],
        "holdout_status": plan["holdout_status"],
        "commands_executed": False,
        "jobs": [
            {
                "order_index": job["order_index"],
                "job_id": job["job_id"],
                "condition": job["condition"],
                "parameter": job["parameter"],
                "seed": job["seed"],
                "output_path": job["output_path"],
                "command": job["command"],
            }
            for job in plan["jobs"]
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        existing = _json(path)
        if existing.get("job_matrix_sha256") != document["job_matrix_sha256"] or existing.get("jobs") != document["jobs"]:
            raise AdapterError("Existing command manifest differs; refusing to overwrite it.")
        return
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def write_execution_manifest(
    plan: dict[str, Any],
    *,
    status: str = "NOT_EXECUTED",
    executed_job_count: int = 0,
    gpu_jobs_executed: int = 0,
    simulation_jobs_executed: int = 0,
    path: Path = EXECUTION_MANIFEST,
) -> None:
    """Record execution state and parameter identity for every planned job."""

    document = {
        "schema_version": "gate24e-execution-manifest-v1",
        "status": status,
        "job_matrix_sha256": plan["job_matrix_sha256"],
        "job_count": plan["job_count"],
        "executed_job_count": executed_job_count,
        "gpu_jobs_executed": gpu_jobs_executed,
        "simulation_jobs_executed": simulation_jobs_executed,
        "holdout_status": plan["holdout_status"],
        "holdout_opened": False,
        "tuning_using_holdout": False,
        "posthoc_parameter_selection_allowed": False,
        "jobs": [
            {
                "order_index": job["order_index"],
                "job_id": job["job_id"],
                "condition": job["condition"],
                "parameter": job["parameter"],
                "seed": job["seed"],
                "prepared_checkpoint_sha256": job["prepared_checkpoint_sha256"],
                "output_path": job["output_path"],
            }
            for job in plan["jobs"]
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        existing = _json(path)
        if existing.get("job_matrix_sha256") != document["job_matrix_sha256"]:
            raise AdapterError("Existing execution manifest belongs to a different job matrix.")
        existing_status = existing.get("status")
        if existing_status in {"COMPLETED", "TECHNICAL_FAILURE"} and status != existing_status:
            raise AdapterError("Existing execution manifest is already finalized; refusing automatic retry or reset.")
        if existing_status == "EXECUTION_IN_PROGRESS" and status == "EXECUTION_IN_PROGRESS":
            raise AdapterError("Execution manifest already records an in-progress batch.")
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _finite_metric(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _valid_core_result(job: dict[str, Any]) -> bool:
    output = Path(job["output_path"])
    status_path = output / "status.json"
    metrics_path = output / "metrics" / "metrics.json"
    rollout_exists = any((output / name).is_file() for name in ("rollout.json", "rollout.npz"))
    if not status_path.is_file() or not metrics_path.is_file() or not rollout_exists:
        return False
    status = _json(status_path)
    metrics = _json(metrics_path)
    scalar = metrics.get("scalar_metrics", metrics)
    required_metrics = tuple(job.get("required_metrics", REQUIRED_PRIMARY_METRICS))
    return status.get("status") == "PASS" and all(_finite_metric(scalar.get(field)) for field in required_metrics)


def valid_pass_result(job: dict[str, Any]) -> bool:
    if not _valid_core_result(job):
        return False
    provenance_path = Path(job["output_path"]) / "adapter_job_provenance.json"
    if not provenance_path.is_file():
        return False
    provenance = _json(provenance_path)
    return (
        provenance.get("job_id") == job["job_id"]
        and provenance.get("condition") == job["condition"]
        and provenance.get("parameter") == job["parameter"]
        and provenance.get("seed") == job["seed"]
        and provenance.get("prepared_checkpoint_sha256") == job["prepared_checkpoint_sha256"]
        and provenance.get("healthy_checkpoint_sha256") == job["healthy_checkpoint_sha256"]
        and provenance.get("mapping_sha256") == job["mapping_sha256"]
        and provenance.get("target_sha256") == job["target_sha256"]
    )


def execute_jobs(plan: dict[str, Any], runner: Callable[..., Any] | None = None) -> None:
    if plan.get("status") != "READY_FOR_25_BLINDED_GPU_JOBS":
        raise AdapterError("Job plan is not ready.")
    runner = runner or subprocess.run
    for job in plan["jobs"]:
        output = Path(job["output_path"])
        if valid_pass_result(job):
            continue
        if (output / "adapter_failure.json").is_file():
            raise AdapterError(f"TECHNICAL_FAILURE already recorded for {job['job_id']}; retry requires a new audited task.")
        if (output / "status.json").is_file():
            raise AdapterError(f"Existing non-valid status for {job['job_id']}; refusing automatic retry.")
        output.mkdir(parents=True, exist_ok=True)
        log_path = output / "adapter_execution.log"
        with log_path.open("w", encoding="utf-8") as log:
            result = runner(job["command"], cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT, check=False, text=True)
        if result.returncode != 0 or not _valid_core_result(job):
            failure = {
                "status": "TECHNICAL_FAILURE",
                "job_id": job["job_id"],
                "returncode": result.returncode,
                "automatic_retry": False,
                "message": "Runner failed or did not produce a valid PASS artifact.",
            }
            (output / "adapter_failure.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
            raise AdapterError(f"TECHNICAL_FAILURE at {job['job_id']}; batch stopped.")
        provenance = {key: job[key] for key in ("job_id", "condition", "parameter", "seed", "prepared_checkpoint_sha256", "healthy_checkpoint_sha256", "mapping_sha256", "target_sha256")}
        (output / "adapter_job_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
        if not valid_pass_result(job):
            raise AdapterError(f"TECHNICAL_FAILURE at {job['job_id']}; provenance validation failed.")


def _load_existing_plan(path: Path = PLAN) -> dict[str, Any]:
    plan = _json(path)
    if plan.get("job_count") != 25 or plan.get("status") != "READY_FOR_25_BLINDED_GPU_JOBS":
        raise AdapterError("Existing job plan is not the reviewed 25-job plan.")
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.dry_run:
            plan = build_job_plan()
            write_job_plan(plan)
            write_command_manifest(plan)
            write_execution_manifest(plan)
            summary = {
                key: plan[key]
                for key in (
                    "status",
                    "job_count",
                    "healthy_job_count",
                    "parkin_job_count",
                    "gpu_jobs_executed",
                    "simulation_jobs_executed",
                    "holdout_status",
                    "holdout_opened",
                    "storage_requirement_status",
                    "cuda_preflight",
                )
            }
            print(json.dumps(summary, indent=2))
            return 0
        plan = _load_existing_plan()
        current = build_job_plan()
        if current["job_matrix_sha256"] != plan["job_matrix_sha256"] or current["jobs"] != plan["jobs"]:
            raise AdapterError("Frozen job plan changed; refusing execution.")
        write_command_manifest(plan)
        write_execution_manifest(plan, status="EXECUTION_IN_PROGRESS")
        try:
            execute_jobs(plan)
        except AdapterError:
            write_execution_manifest(plan, status="TECHNICAL_FAILURE")
            raise
        write_execution_manifest(
            plan,
            status="COMPLETED",
            executed_job_count=plan["job_count"],
            gpu_jobs_executed=plan["job_count"],
            simulation_jobs_executed=plan["job_count"],
        )
        return 0
    except (AdapterError, OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
