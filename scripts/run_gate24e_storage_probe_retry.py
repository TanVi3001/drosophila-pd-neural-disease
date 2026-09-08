"""Execute exactly one separately recorded Gate24E technical storage retry."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROBE_ROOT = ROOT / "experiments" / "gate_24e_storage_probe"
ATTEMPT_ROOT = PROBE_ROOT / "attempt_02"
ATTEMPT_RUN = ATTEMPT_ROOT / "run"
ATTEMPT_LOGS = ATTEMPT_ROOT / "logs"
ATTEMPT_MANIFESTS = ATTEMPT_ROOT / "manifests"
ATTEMPT_MANIFEST = ATTEMPT_MANIFESTS / "storage_qualification.json"
AUTHORIZATION = PROBE_ROOT / "manifests" / "storage_probe_retry_authorization.json"
COMPATIBILITY = PROBE_ROOT / "manifests" / "cpg_compatibility_fix.json"
TOP_LEVEL_MANIFEST = PROBE_ROOT / "manifests" / "storage_qualification.json"
RUNNER = ROOT / "scripts" / "run_neural_experiment.py"
BRAIN_ROOT = ROOT.parent / "external" / "fly-brain-audit"
PLATFORM_ROOT = ROOT.parent / "drosophila-pd-flygym-gate24-clean"
PROBE_SEED = 9001
SCIENTIFIC_SEEDS = [0, 1, 2, 3, 4]
STEPS = 100000
DURATION_S = 10.0
DEVICE = "cuda"
POLL_INTERVAL_S = 1.0
COMPATIBILITY_COMMIT = "8ee587f"


class RetryError(RuntimeError):
    """Raised when the one-shot retry contract is not satisfied."""


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RetryError(f"Expected JSON object: {path}")
    return value


def _free_space() -> int:
    return int(shutil.disk_usage(ROOT).free)


def _directory_size(path: Path) -> int:
    if not path.is_dir():
        return 0
    return int(sum(item.stat().st_size for item in path.rglob("*") if item.is_file()))


def _largest_files(path: Path, limit: int = 10) -> list[dict[str, Any]]:
    files = sorted(
        (item for item in path.rglob("*") if item.is_file()),
        key=lambda item: item.stat().st_size,
        reverse=True,
    ) if path.is_dir() else []
    return [
        {"path": str(item.relative_to(path)).replace("\\", "/"), "bytes": item.stat().st_size}
        for item in files[:limit]
    ]


def _git_commit(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RetryError(f"Cannot read platform commit: {result.stderr.strip()}")
    return result.stdout.strip()


def _cuda_preflight(python: Path) -> dict[str, Any]:
    code = (
        "import json, torch; ok=bool(torch.cuda.is_available()); "
        "print(json.dumps({'torch':torch.__version__, 'cuda':torch.version.cuda, "
        "'available':ok, 'device':torch.cuda.get_device_name(0) if ok else 'NO_GPU'}))"
    )
    result = subprocess.run([str(python), "-c", code], capture_output=True, text=True, check=False)
    if result.returncode:
        raise RetryError(f"CUDA preflight failed: {result.stderr.strip()}")
    value = json.loads(result.stdout.strip().splitlines()[-1])
    if value.get("available") is not True:
        raise RetryError(f"CUDA is unavailable; CPU fallback is forbidden: {value}")
    return value


def _validate_authorization() -> tuple[dict[str, Any], dict[str, Any]]:
    authorization = _read_json(AUTHORIZATION)
    compatibility = _read_json(COMPATIBILITY)
    exact = {
        "previous_attempt": "attempt_01",
        "previous_probe_seed": PROBE_SEED,
        "previous_status": "STORAGE_PROBE_TECHNICAL_FAILURE",
        "previous_failure_stage": "PRE_SIMULATION_CLI_ARGUMENT_PARSE",
        "previous_result_scientifically_valid": False,
        "previous_storage_measurements_valid": False,
        "compatibility_fix_commit": COMPATIBILITY_COMMIT,
        "retry_seed": PROBE_SEED,
        "retry_count_authorized": 1,
        "automatic_retry": False,
        "scientific_analysis_allowed": False,
        "scientific_jobs_authorized": False,
        "holdout_access_allowed": False,
        "tuning_allowed": False,
        "parameter_change_allowed": False,
        "seed_change_allowed": False,
        "steps_change_allowed": False,
    }
    for key, expected in exact.items():
        if authorization.get(key) != expected:
            raise RetryError(f"Retry authorization mismatch: {key}={authorization.get(key)!r}")
    compatibility_exact = {
        "previous_probe_status": "STORAGE_PROBE_TECHNICAL_FAILURE",
        "previous_failure_stage": "PRE_SIMULATION_CLI_ARGUMENT_PARSE",
        "previous_storage_measurements_valid": False,
        "compatibility_audit_status": "CPG_CLI_OMISSION_SEMANTICALLY_EQUIVALENT",
        "platform_commit": "3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06",
        "verified_default_cpg_frequency_hz": 12.0,
        "wrapper_requested_cpg_frequency_hz": 12.0,
        "semantic_equivalence": True,
        "wrapper_fix_applied": True,
        "holdout_opened": False,
    }
    for key, expected in compatibility_exact.items():
        if compatibility.get(key) != expected:
            raise RetryError(f"CPG compatibility mismatch: {key}={compatibility.get(key)!r}")
    return authorization, compatibility


def build_retry_command(python: Path) -> list[str]:
    return [
        str(python),
        str(RUNNER),
        "--brain-root",
        str(BRAIN_ROOT),
        "--platform-root",
        str(PLATFORM_ROOT),
        "--brain-python",
        str(python),
        "--seed",
        str(PROBE_SEED),
        "--steps",
        str(STEPS),
        "--device",
        DEVICE,
        "--output",
        str(ATTEMPT_RUN),
    ]


def _probe_valid() -> tuple[bool, list[str]]:
    errors: list[str] = []
    status_path = ATTEMPT_RUN / "status.json"
    metrics_path = ATTEMPT_RUN / "metrics" / "metrics.json"
    if not status_path.is_file():
        errors.append("missing status.json")
    if not metrics_path.is_file():
        errors.append("missing metrics/metrics.json")
    if not any((ATTEMPT_RUN / name).is_file() for name in ("rollout.json", "rollout.npz")):
        errors.append("missing rollout artifact")
    video_files = [
        path for path in ATTEMPT_RUN.rglob("*")
        if path.is_file() and path.suffix.casefold() == ".mp4"
    ] if ATTEMPT_RUN.is_dir() else []
    if video_files:
        errors.append("video artifact was generated")
    if errors:
        return False, errors
    status = _read_json(status_path)
    command = [str(item) for item in status.get("command", [])]
    if status.get("status") != "PASS":
        errors.append(f"status={status.get('status')}")
    if status.get("simulation_run") is not True:
        errors.append("simulation_run is not true")
    for flag, expected in (("--seed", str(PROBE_SEED)), ("--steps", str(STEPS))):
        if flag not in command or command[command.index(flag) + 1] != expected:
            errors.append(f"{flag} mismatch")
    forbidden = {"--prepared-checkpoint", "--parameter", "--video", "--video-output", "--compare-to", "--cpg-frequency-hz"}
    if forbidden.intersection(command):
        errors.append("forbidden command option present")
    return not errors, errors


def _simulation_started(log_path: Path) -> bool:
    if not log_path.is_file():
        return False
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return (
        "Running healthy: 100000 FlyGym steps" in text
        or "Progress: 100000/100000" in text
    )


def _projection(final_bytes: int, peak_consumption: int) -> dict[str, int | float]:
    transient = max(0, peak_consumption - final_bytes)
    projected_final = final_bytes * 25
    projected_peak = projected_final + transient
    reserve_fraction = 0.20
    reserve_bytes = int(math.ceil(projected_peak * reserve_fraction))
    return {
        "transient_overhead_bytes": transient,
        "projected_final_25_jobs_bytes": projected_final,
        "projected_peak_requirement_bytes": projected_peak,
        "reserve_fraction": reserve_fraction,
        "reserve_bytes": reserve_bytes,
        "required_space_bytes": projected_peak + reserve_bytes,
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _update_top_level(attempt_document: dict[str, Any]) -> None:
    current = _read_json(TOP_LEVEL_MANIFEST) if TOP_LEVEL_MANIFEST.is_file() else {}
    attempt_01 = {
        "status": "STORAGE_PROBE_TECHNICAL_FAILURE",
        "valid_for_storage_estimation": False,
    }
    attempt_02_valid = attempt_document["probe_status"] == "PASS" and attempt_document["simulation_started"] is True
    current.update(
        {
            "attempt_01": attempt_01,
            "attempt_02": {
                "status": attempt_document["probe_status"],
                "valid_for_storage_estimation": attempt_02_valid,
                "manifest": "experiments/gate_24e_storage_probe/attempt_02/manifests/storage_qualification.json",
            },
            "current_qualification_status": attempt_document["qualification_status"],
        }
    )
    if attempt_02_valid:
        current["current_estimate_source"] = "attempt_02"
    else:
        current.pop("current_estimate_source", None)
    _write_json(TOP_LEVEL_MANIFEST, current)


def execute_retry(python: Path) -> dict[str, Any]:
    authorization, compatibility = _validate_authorization()
    if ATTEMPT_ROOT.exists() and any(ATTEMPT_ROOT.iterdir()):
        raise RetryError("attempt_02 already exists; exactly one retry is authorized")
    if (PROBE_ROOT / "attempt_03").exists():
        raise RetryError("attempt_03 exists; automatic retry is forbidden")
    if _git_commit(PLATFORM_ROOT) != compatibility["platform_commit"]:
        raise RetryError("Frozen FlyGym platform commit changed")
    cuda = _cuda_preflight(python)
    ATTEMPT_RUN.mkdir(parents=True, exist_ok=True)
    ATTEMPT_LOGS.mkdir(parents=True, exist_ok=True)
    command = build_retry_command(python)
    forbidden_wrapper_flags = {"--prepared-checkpoint", "--parameter", "--video", "--compare-to"}
    if forbidden_wrapper_flags.intersection(command):
        raise RetryError("Retry command contains a forbidden option")
    free_before = _free_space()
    minimum_free = free_before
    started = datetime.now(UTC).isoformat()
    return_code: int | None = None
    try:
        with (ATTEMPT_LOGS / "storage_probe_retry.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, text=True)
            while process.poll() is None:
                minimum_free = min(minimum_free, _free_space())
                time.sleep(POLL_INTERVAL_S)
            return_code = process.returncode
            minimum_free = min(minimum_free, _free_space())
    except OSError as exc:
        return_code = None
        (ATTEMPT_RUN / "retry_failure.json").write_text(
            json.dumps({"status": "STORAGE_PROBE_RETRY_TECHNICAL_FAILURE", "error": str(exc)}, indent=2) + "\n",
            encoding="utf-8",
        )
    free_after = _free_space()
    final_bytes = _directory_size(ATTEMPT_RUN)
    peak_consumption = max(0, free_before - minimum_free)
    projection = _projection(final_bytes, peak_consumption)
    valid, errors = _probe_valid() if return_code == 0 else (False, [f"return_code={return_code}"])
    simulation_started = _simulation_started(ATTEMPT_LOGS / "storage_probe_retry.log")
    if simulation_started and not valid:
        errors.append("failure_stage=POST_SIMULATION_EXPORT")
    if not valid:
        qualification = "STORAGE_PROBE_RETRY_TECHNICAL_FAILURE"
    elif free_after > projection["required_space_bytes"]:
        qualification = "GATE24E_STORAGE_QUALIFIED"
    else:
        qualification = "WAITING_GATE24E_STORAGE_CAPACITY"
    document: dict[str, Any] = {
        "schema_version": "gate24e-storage-qualification-v2",
        "attempt_id": "attempt_02",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "started_at_utc": started,
        "probe_seed": PROBE_SEED,
        "probe_condition": "TECHNICAL_HEALTHY_STORAGE_PROBE",
        "probe_status": "PASS" if valid else "TECHNICAL_FAILURE",
        "simulation_started": simulation_started,
        "probe_errors": errors,
        "return_code": return_code,
        "steps": STEPS,
        "duration_s": DURATION_S,
        "compatibility_fix_commit": COMPATIBILITY_COMMIT,
        "gpu_preflight": cuda,
        "free_space_before_bytes": free_before,
        "minimum_free_space_during_run_bytes": minimum_free,
        "free_space_after_bytes": free_after,
        "final_probe_artifact_bytes": final_bytes,
        "peak_disk_consumption_bytes": peak_consumption,
        **projection,
        "largest_files": _largest_files(ATTEMPT_RUN),
        "qualification_status": qualification,
        "scientific_jobs_executed": 0,
        "scientific_results_generated": False,
        "scientific_analysis_allowed": False,
        "holdout_opened": False,
        "tuning_performed": False,
        "posthoc_selection_performed": False,
        "attempt_01_included": False,
        "automatic_retry": False,
        "authorization": {
            "retry_count_authorized": authorization["retry_count_authorized"],
            "retry_seed": authorization["retry_seed"],
        },
    }
    _write_json(ATTEMPT_MANIFEST, document)
    _update_top_level(document)
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--brain-python", type=Path, default=Path(sys.executable))
    args = parser.parse_args(argv)
    try:
        document = execute_retry(args.brain_python.resolve())
    except (RetryError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({key: document[key] for key in ("attempt_id", "probe_status", "simulation_started", "qualification_status")}, indent=2))
    return 0 if document["qualification_status"] == "GATE24E_STORAGE_QUALIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
