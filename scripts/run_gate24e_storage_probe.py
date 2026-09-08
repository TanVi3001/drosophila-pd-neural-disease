"""Run one excluded technical rollout to qualify Gate24E storage capacity."""

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
RUNNER = ROOT / "scripts" / "run_neural_experiment.py"
PROBE_ROOT = ROOT / "experiments" / "gate_24e_storage_probe"
PROBE_RUN = PROBE_ROOT / "run"
PROBE_MANIFESTS = PROBE_ROOT / "manifests"
PROBE_LOGS = PROBE_ROOT / "logs"
CONTRACT_PATH = PROBE_MANIFESTS / "storage_probe_contract.json"
QUALIFICATION_PATH = PROBE_MANIFESTS / "storage_qualification.json"
BRAIN_ROOT = ROOT.parent / "external" / "fly-brain-audit"
PLATFORM_ROOT = ROOT.parent / "drosophila-pd-flygym-gate24-clean"
PROBE_SEED = 9001
SCIENTIFIC_SEEDS = [0, 1, 2, 3, 4]
STEPS = 100000
DURATION_S = 10.0
DEVICE = "cuda"
POLL_INTERVAL_S = 1.0


class StorageProbeError(RuntimeError):
    """Raised when the technical storage probe cannot be safely run."""


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise StorageProbeError(f"Expected JSON object: {path}")
    return value


def build_contract() -> dict[str, Any]:
    return {
        "schema_version": "gate24e-storage-probe-contract-v1",
        "purpose": "TECHNICAL_STORAGE_QUALIFICATION_ONLY",
        "scientific_analysis_allowed": False,
        "scientific_seed": False,
        "probe_seed": PROBE_SEED,
        "locked_scientific_seeds": SCIENTIFIC_SEEDS,
        "condition": "healthy",
        "condition_label": "TECHNICAL_HEALTHY_STORAGE_PROBE",
        "steps": STEPS,
        "duration_s": DURATION_S,
        "timestep_s": 0.0001,
        "device": DEVICE,
        "video": False,
        "prepared_parkin_checkpoint": None,
        "holdout_access_allowed": False,
        "parameter_selection_allowed": False,
        "model_selection_allowed": False,
        "threshold_selection_allowed": False,
        "probe_output": "experiments/gate_24e_storage_probe/run",
    }


def _write_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = build_contract()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and _json(path) != contract:
        raise StorageProbeError("Existing storage-probe contract differs; refusing overwrite.")
    if not path.is_file():
        path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    return contract


def build_command() -> list[str]:
    command = [
        str(sys.executable),
        str(RUNNER),
        "--brain-root",
        str(BRAIN_ROOT),
        "--platform-root",
        str(PLATFORM_ROOT),
        "--seed",
        str(PROBE_SEED),
        "--steps",
        str(STEPS),
        "--device",
        DEVICE,
        "--output",
        str(PROBE_RUN),
    ]
    forbidden = {"--prepared-checkpoint", "--video", "--video-output", "--compare-to", "--parameter"}
    if forbidden.intersection(command):
        raise StorageProbeError("Storage probe command contains a forbidden scientific option.")
    return command


def _free_space() -> int:
    return int(shutil.disk_usage(ROOT).free)


def _directory_size(path: Path) -> int:
    return int(sum(item.stat().st_size for item in path.rglob("*") if item.is_file())) if path.is_dir() else 0


def _largest_files(path: Path, limit: int = 10) -> list[dict[str, Any]]:
    files = sorted((item for item in path.rglob("*") if item.is_file()), key=lambda item: item.stat().st_size, reverse=True)
    return [{"path": str(item.relative_to(path)).replace("\\", "/"), "bytes": item.stat().st_size} for item in files[:limit]]


def _cuda_preflight() -> dict[str, Any]:
    code = (
        "import json, torch; ok=bool(torch.cuda.is_available()); "
        "print(json.dumps({'torch':torch.__version__, 'cuda':torch.version.cuda, "
        "'available':ok, 'device':torch.cuda.get_device_name(0) if ok else 'NO_GPU'}))"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    if result.returncode:
        raise StorageProbeError(f"CUDA preflight failed: {result.stderr.strip()}")
    value = json.loads(result.stdout.strip().splitlines()[-1])
    if value.get("available") is not True or "RTX 3050" not in str(value.get("device")):
        raise StorageProbeError(f"CUDA preflight is not an RTX 3050 GPU: {value}")
    return value


def _probe_valid() -> tuple[bool, list[str]]:
    errors: list[str] = []
    status_path = PROBE_RUN / "status.json"
    metrics_path = PROBE_RUN / "metrics" / "metrics.json"
    if not status_path.is_file():
        errors.append("missing status.json")
    if not metrics_path.is_file():
        errors.append("missing metrics/metrics.json")
    if not any((PROBE_RUN / name).is_file() for name in ("rollout.json", "rollout.npz")):
        errors.append("missing rollout artifact")
    video_files = [path for path in PROBE_RUN.rglob("*") if path.is_file() and path.suffix.casefold() == ".mp4"] if PROBE_RUN.is_dir() else []
    if video_files:
        errors.append("video artifact was generated")
    if errors:
        return False, errors
    status = _json(status_path)
    command = [str(item) for item in status.get("command", [])]
    if status.get("status") != "PASS":
        errors.append(f"status={status.get('status')}")
    if "--seed" not in command or command[command.index("--seed") + 1] != str(PROBE_SEED):
        errors.append("seed mismatch")
    if "--steps" not in command or command[command.index("--steps") + 1] != str(STEPS):
        errors.append("step count mismatch")
    forbidden = {"--prepared-checkpoint", "--video", "--video-output", "--compare-to", "--parameter"}
    if forbidden.intersection(command):
        errors.append("forbidden command option present")
    return not errors, errors


def _write_qualification(document: dict[str, Any]) -> None:
    PROBE_MANIFESTS.mkdir(parents=True, exist_ok=True)
    QUALIFICATION_PATH.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def calculate_storage_projection(final_probe_bytes: int, peak_consumption_bytes: int) -> dict[str, int | float]:
    transient = max(0, peak_consumption_bytes - final_probe_bytes)
    projected_final = final_probe_bytes * 25
    projected_peak = projected_final + transient
    reserve_fraction = 0.20
    reserve_bytes = int(math.ceil(projected_peak * reserve_fraction))
    required_space = projected_peak + reserve_bytes
    return {
        "transient_overhead_bytes": transient,
        "projected_final_25_jobs_bytes": projected_final,
        "projected_peak_requirement_bytes": projected_peak,
        "reserve_fraction": reserve_fraction,
        "reserve_bytes": reserve_bytes,
        "required_space_bytes": required_space,
    }


def execute_probe() -> dict[str, Any]:
    contract = _write_contract()
    if PROBE_RUN.exists() and any(PROBE_RUN.iterdir()):
        raise StorageProbeError("Storage-probe output already exists; automatic retry is forbidden.")
    _cuda_preflight()
    PROBE_RUN.mkdir(parents=True, exist_ok=True)
    PROBE_LOGS.mkdir(parents=True, exist_ok=True)
    free_before = _free_space()
    minimum_free = free_before
    command = build_command()
    started = datetime.now(UTC).isoformat()
    log_path = PROBE_LOGS / "storage_probe.log"
    process: subprocess.Popen[str] | None = None
    return_code = 1
    try:
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, text=True)
            while process.poll() is None:
                minimum_free = min(minimum_free, _free_space())
                time.sleep(POLL_INTERVAL_S)
            return_code = process.returncode
            minimum_free = min(minimum_free, _free_space())
    except OSError as exc:
        failure = {
            "status": "STORAGE_PROBE_TECHNICAL_FAILURE",
            "return_code": None,
            "error": str(exc),
            "automatic_retry": False,
        }
        (PROBE_RUN / "probe_failure.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
    free_after = _free_space()
    final_bytes = _directory_size(PROBE_RUN)
    peak_consumption = max(0, free_before - minimum_free)
    projection = calculate_storage_projection(final_bytes, peak_consumption)
    probe_ok, probe_errors = _probe_valid() if return_code == 0 else (False, [f"return_code={return_code}"])
    qualification = "GATE24E_STORAGE_QUALIFIED" if probe_ok and free_after > projection["required_space_bytes"] else "WAITING_GATE24E_STORAGE_CAPACITY"
    if not probe_ok:
        qualification = "STORAGE_PROBE_TECHNICAL_FAILURE"
    document = {
        "schema_version": "gate24e-storage-qualification-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "started_at_utc": started,
        "probe_seed": PROBE_SEED,
        "probe_condition": contract["condition_label"],
        "probe_status": "PASS" if probe_ok else "TECHNICAL_FAILURE",
        "probe_errors": probe_errors,
        "return_code": return_code,
        "steps": STEPS,
        "duration_s": DURATION_S,
        "free_space_before_bytes": free_before,
        "minimum_free_space_during_run_bytes": minimum_free,
        "free_space_after_bytes": free_after,
        "final_probe_artifact_bytes": final_bytes,
        "peak_disk_consumption_bytes": peak_consumption,
        **projection,
        "largest_files": _largest_files(PROBE_RUN),
        "qualification_status": qualification,
        "scientific_jobs_executed": 0,
        "scientific_results_generated": False,
        "holdout_opened": False,
        "tuning_performed": False,
        "probe_included_in_scientific_analysis": False,
        "automatic_retry": False,
    }
    _write_qualification(document)
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        document = execute_probe()
    except (StorageProbeError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({key: document[key] for key in ("probe_status", "final_probe_artifact_bytes", "qualification_status")}, indent=2))
    return 0 if document["qualification_status"] == "GATE24E_STORAGE_QUALIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
