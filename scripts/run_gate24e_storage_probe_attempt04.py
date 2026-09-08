"""Run the one-shot Gate24E attempt_04 storage probe.

The default workflow is explicit: pass ``--dry-run`` for a side-effect-free
preflight or ``--execute`` for the separately authorized technical probe. This
module never starts the scientific batch and never opens the holdout.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import audit_gate24e_attempt04_authorization

ROOT = Path(__file__).resolve().parents[1]
ATTEMPT_ID = "attempt_04"
ATTEMPT_ROOT = ROOT / "experiments/gate_24e_storage_probe/attempt_04"
ATTEMPT_RUN = ATTEMPT_ROOT / "run"
ATTEMPT_LOGS = ATTEMPT_ROOT / "logs"
ATTEMPT_MANIFESTS = ATTEMPT_ROOT / "manifests"
AUTHORIZATION = ROOT / "experiments/gate_24e_storage_probe/manifests/attempt04_authorization.json"
SIGNOFF = ROOT / "research/validation/prospective/gate24e_attempt04_authorization_reviewer_signoff.json"
FAILURE_MANIFEST = ROOT / "experiments/gate_24e_storage_probe/attempt_03/manifests/storage_qualification.json"
HISTORY = ROOT / "experiments/gate_24e_storage_probe/manifests/storage_qualification.json"
FIREWALL = ROOT / "experiments/gate_24_prospective_validation/manifests/holdout_firewall_manifest.json"
EXECUTION_MANIFEST = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/execution_manifest.json"

BRAIN_ROOT = ROOT.parent / "external/fly-brain-audit"
PLATFORM_ROOT = ROOT.parent / "drosophila-pd-flygym-gate24-memorysafe-clean"
PYTHON_RUNTIME = ROOT.parent / "drosophila-pd-flygym/.venv/Scripts/python.exe"
PLATFORM_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"
ARTIFACT_PROFILE = "GATE24E_MEMORY_SAFE"
PROBE_SEED = 9001
SCIENTIFIC_SEEDS = (0, 1, 2, 3, 4)
STEPS = 100000
DURATION_S = 10.0
DEVICE = "cuda"
POLL_INTERVAL_S = 1.0
EXPECTED_PYTHON = "3.12.10"
EXPECTED_FLYGYM = "2.1.0"
EXPECTED_TORCH = "2.5.1+cu121"
EXPECTED_CUDA = "12.1"
EXPECTED_GPU = "NVIDIA GeForce RTX 3050 6GB Laptop GPU"
RUNNER = ROOT / "scripts/run_neural_experiment.py"
LOG = ATTEMPT_LOGS / "storage_probe_attempt_04.log"
EXECUTION_RECORD = ATTEMPT_MANIFESTS / "attempt_04_execution.json"
STORAGE_RECORD = ATTEMPT_MANIFESTS / "storage_qualification.json"


class Attempt04RunnerError(RuntimeError):
    """Raised when the single-use technical runner cannot proceed safely."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Attempt04RunnerError(f"Missing required JSON: {path}") from exc
    if not isinstance(value, dict):
        raise Attempt04RunnerError(f"Expected JSON object: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _git_text(path: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise Attempt04RunnerError(f"Git inspection failed in {path}: {result.stderr.strip()}")
    return result.stdout.strip()


def _environment_snapshot(python: Path = PYTHON_RUNTIME) -> dict[str, Any]:
    """Read versions and CUDA availability without allocating a tensor."""
    code = (
        "import json, platform, torch; "
        "available=bool(torch.cuda.is_available()); "
        "name=torch.cuda.get_device_name(0) if available else None; "
        "print(json.dumps({'python': platform.python_version(), "
        "'flygym': __import__('importlib.metadata', fromlist=['version']).version('flygym'), "
        "'torch': torch.__version__, 'cuda': torch.version.cuda, "
        "'cuda_available': available, 'gpu': name}))"
    )
    result = subprocess.run(
        [str(python), "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise Attempt04RunnerError(
            f"Runtime preflight failed for {python}: {result.stderr.strip()}"
        )
    try:
        snapshot = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise Attempt04RunnerError("Runtime preflight returned invalid JSON") from exc
    if not isinstance(snapshot, dict):
        raise Attempt04RunnerError("Runtime preflight did not return an object")
    return snapshot


def _verify_environment(snapshot: dict[str, Any]) -> None:
    expected = {
        "python": EXPECTED_PYTHON,
        "flygym": EXPECTED_FLYGYM,
        "torch": EXPECTED_TORCH,
        "cuda": EXPECTED_CUDA,
        "cuda_available": True,
        "gpu": EXPECTED_GPU,
    }
    mismatches = [
        f"{key}={snapshot.get(key)!r} (expected {value!r})"
        for key, value in expected.items()
        if snapshot.get(key) != value
    ]
    if mismatches:
        raise Attempt04RunnerError("Runtime environment mismatch: " + "; ".join(mismatches))


def _verify_platform() -> dict[str, Any]:
    if not PLATFORM_ROOT.is_dir():
        raise Attempt04RunnerError(f"Missing approved platform runtime: {PLATFORM_ROOT}")
    head = _git_text(PLATFORM_ROOT, "rev-parse", "HEAD")
    status = _git_text(PLATFORM_ROOT, "status", "--porcelain")
    if head != PLATFORM_COMMIT:
        raise Attempt04RunnerError(f"Platform commit mismatch: {head} != {PLATFORM_COMMIT}")
    if status:
        raise Attempt04RunnerError(f"Platform worktree is dirty: {status}")
    return {"path": str(PLATFORM_ROOT), "head": head, "clean": True}


def _assert_unused() -> None:
    if ATTEMPT_ROOT.exists():
        files = [path for path in ATTEMPT_ROOT.rglob("*") if path.is_file()]
        if files:
            raise Attempt04RunnerError(
                "attempt_04 already contains execution artifacts; refusing overwrite or retry"
            )
        raise Attempt04RunnerError("attempt_04 directory already exists; refusing to claim a fresh attempt")


def build_command(python: Path = PYTHON_RUNTIME) -> list[str]:
    """Build the only command permitted for attempt_04."""
    command = [
        str(python),
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
        "--artifact-profile",
        ARTIFACT_PROFILE,
        "--output",
        str(ATTEMPT_RUN),
    ]
    forbidden = {
        "--prepared-checkpoint",
        "--parameter",
        "--video",
        "--video-output",
        "--compare-to",
        "--cpg-frequency-hz",
    }
    if forbidden.intersection(command):
        raise Attempt04RunnerError("Attempt command contains a forbidden option")
    return command


def verify_preflight() -> dict[str, Any]:
    """Verify all approved documents and runtime facts without creating output."""
    authorization_audit = audit_gate24e_attempt04_authorization.audit()
    if authorization_audit.get("status") != "READY_FOR_GATE24E_ATTEMPT04":
        raise Attempt04RunnerError(
            "Authorization audit is not ready: "
            f"{authorization_audit.get('status')}: {authorization_audit.get('blockers', [])}"
        )
    if authorization_audit.get("attempt_04_exists") is not False:
        raise Attempt04RunnerError("attempt_04 is not unused")
    if authorization_audit.get("attempt_04_authorized") is not True:
        raise Attempt04RunnerError("attempt_04 is not human-authorized")
    if authorization_audit.get("attempt_04_seed") != PROBE_SEED:
        raise Attempt04RunnerError("attempt_04 seed does not match authorization")
    if authorization_audit.get("attempt_04_steps") != STEPS:
        raise Attempt04RunnerError("attempt_04 steps do not match authorization")
    if authorization_audit.get("scientific_jobs_executed") != 0:
        raise Attempt04RunnerError("Scientific jobs are nonzero")
    if authorization_audit.get("scientific_batch_authorized") is not False:
        raise Attempt04RunnerError("Scientific batch is authorized")
    if authorization_audit.get("holdout") != "SEALED":
        raise Attempt04RunnerError("Holdout is not sealed")
    if PROBE_SEED in SCIENTIFIC_SEEDS:
        raise Attempt04RunnerError("Technical probe seed overlaps scientific seeds")

    _assert_unused()
    platform = _verify_platform()
    if not PYTHON_RUNTIME.is_file():
        raise Attempt04RunnerError(f"Missing approved Python runtime: {PYTHON_RUNTIME}")
    environment = _environment_snapshot(PYTHON_RUNTIME)
    _verify_environment(environment)
    command = build_command(PYTHON_RUNTIME)
    return {
        "authorization": authorization_audit,
        "platform": platform,
        "python_runtime": str(PYTHON_RUNTIME),
        "environment": environment,
        "command": command,
        "attempt_04_created": False,
        "gpu_executed": False,
        "simulation_executed": False,
        "scientific_jobs": 0,
        "scientific_batch_authorized": False,
        "holdout": "SEALED",
    }


def prepare_dry_run() -> dict[str, Any]:
    context = verify_preflight()
    return {
        "status": "READY_FOR_GATE24E_STORAGE_ATTEMPT_04",
        "environment_verified": True,
        "attempt_04_created": False,
        "gpu_executed": False,
        "simulation_executed": False,
        "scientific_jobs": 0,
        "scientific_batch_authorized": False,
        "holdout": "SEALED",
        "command": context["command"],
        "runtime": context["platform"],
        "python_runtime": context["python_runtime"],
        "environment": context["environment"],
    }


def _completion_observed(log_text: str) -> bool:
    return bool(re.search(r"(?:Progress:\s*)?100000\s*/\s*100000", log_text))


def _artifact_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def calculate_storage_projection(final_artifact_bytes: int, peak_consumption: int) -> dict[str, int]:
    transient = max(0, peak_consumption - final_artifact_bytes)
    projected_final_25 = final_artifact_bytes * 25
    projected_peak = projected_final_25 + transient
    reserve = math.ceil(projected_peak * 0.20)
    return {
        "transient_bytes": transient,
        "projected_final_25_bytes": projected_final_25,
        "projected_peak_bytes": projected_peak,
        "reserve_bytes": reserve,
        "required_bytes": projected_peak + reserve,
    }


def _validate_success(output: Path, log_text: str) -> None:
    required = (
        output / "status.json",
        output / "rollout.npz",
        output / "metadata.json",
        output / "manifest.json",
        output / "metrics/metrics.json",
    )
    missing = [str(path) for path in required if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise Attempt04RunnerError("Successful probe artifacts are missing: " + ", ".join(missing))
    status = _read_json(output / "status.json")
    if status.get("status") != "PASS" or status.get("simulation_run") is not True:
        raise Attempt04RunnerError("status.json does not report PASS with simulation_run=true")
    if status.get("artifact_profile", ARTIFACT_PROFILE) != ARTIFACT_PROFILE:
        raise Attempt04RunnerError("status.json artifact profile is not memory-safe")
    manifest = _read_json(output / "manifest.json")
    if manifest.get("artifact_profile") != ARTIFACT_PROFILE:
        raise Attempt04RunnerError("manifest artifact profile is not memory-safe")
    if not _completion_observed(log_text):
        raise Attempt04RunnerError("100000/100000 completion marker is missing")


def _terminate_after_interrupt(process: subprocess.Popen[str]) -> int:
    try:
        process.terminate()
        return process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.wait(timeout=10)


def _run_child(command: list[str], log_handle: Any) -> tuple[int, int, bool]:
    free_before = shutil.disk_usage(ROOT).free
    minimum_free = free_before
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    interrupted = False
    try:
        while process.poll() is None:
            minimum_free = min(minimum_free, shutil.disk_usage(ROOT).free)
            time.sleep(POLL_INTERVAL_S)
        return_code = process.wait()
    except KeyboardInterrupt:
        interrupted = True
        log_handle.write("\nKeyboardInterrupt received by attempt_04 runner.\n")
        log_handle.flush()
        return_code = _terminate_after_interrupt(process)
    minimum_free = min(minimum_free, shutil.disk_usage(ROOT).free)
    return return_code, minimum_free, interrupted


def _execution_record(
    *,
    context: dict[str, Any],
    command: list[str],
    return_code: int,
    interrupted: bool,
    storage: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    return {
        "schema_version": "gate24e-storage-attempt04-execution-v1",
        "attempt_id": ATTEMPT_ID,
        "status": status,
        "attempt_consumed": True,
        "simulation_launched": True,
        "return_code": return_code,
        "keyboard_interrupt": interrupted,
        "command": command,
        "probe_seed": PROBE_SEED,
        "steps": STEPS,
        "duration_s": DURATION_S,
        "device": DEVICE,
        "platform_commit": PLATFORM_COMMIT,
        "artifact_profile": ARTIFACT_PROFILE,
        "scientific_jobs_executed": 0,
        "scientific_batch_authorized": False,
        "holdout": "SEALED",
        "authorization_audit_status": context["authorization"]["status"],
        "storage": storage,
        "recorded_at_utc": datetime.now(UTC).isoformat(),
    }


def execute_once() -> dict[str, Any]:
    context = verify_preflight()
    ATTEMPT_ROOT.mkdir(parents=True, exist_ok=False)
    ATTEMPT_LOGS.mkdir()
    ATTEMPT_MANIFESTS.mkdir()
    command = context["command"]
    _write_json(
        ATTEMPT_MANIFESTS / "authorization_snapshot.json",
        {
            "schema_version": "gate24e-storage-attempt04-authorization-snapshot-v1",
            "authorization": context["authorization"],
            "command": command,
            "scientific_batch_authorized": False,
            "holdout": "SEALED",
        },
    )
    free_before = shutil.disk_usage(ROOT).free
    with LOG.open("w", encoding="utf-8") as log_handle:
        try:
            return_code, minimum_free, interrupted = _run_child(command, log_handle)
        except BaseException:
            log_handle.write("\nRunner failed before a normal child result was recorded.\n")
            log_handle.flush()
            raise
    free_after = shutil.disk_usage(ROOT).free
    log_text = LOG.read_text(encoding="utf-8", errors="replace")
    final_artifact = _artifact_bytes(ATTEMPT_RUN)
    peak_consumption = max(0, free_before - minimum_free)
    storage = {
        "free_before_bytes": free_before,
        "minimum_free_during_run_bytes": minimum_free,
        "free_after_bytes": free_after,
        "final_artifact_bytes": final_artifact,
        "peak_disk_consumption_bytes": peak_consumption,
        "poll_interval_s": POLL_INTERVAL_S,
        **calculate_storage_projection(final_artifact, peak_consumption),
    }
    status = "ATTEMPT_04_INTERRUPTED" if interrupted else "ATTEMPT_04_FAILED"
    if not interrupted and return_code == 0:
        _validate_success(ATTEMPT_RUN, log_text)
        status = "ATTEMPT_04_STORAGE_PROBE_PASS"
    record = _execution_record(
        context=context,
        command=command,
        return_code=return_code,
        interrupted=interrupted,
        storage=storage,
        status=status,
    )
    _write_json(EXECUTION_RECORD, record)
    _write_json(
        STORAGE_RECORD,
        {
            "schema_version": "gate24e-storage-attempt04-qualification-v1",
            "attempt_id": ATTEMPT_ID,
            "status": status,
            "storage_measurements_valid": status == "ATTEMPT_04_STORAGE_PROBE_PASS",
            "storage_qualification_valid": status == "ATTEMPT_04_STORAGE_PROBE_PASS",
            "completion_marker_observed": _completion_observed(log_text),
            "artifact_profile": ARTIFACT_PROFILE,
            "scientific_jobs_executed": 0,
            "scientific_batch_authorized": False,
            "holdout": "SEALED",
            "storage": storage,
        },
    )
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--execute", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = prepare_dry_run() if args.dry_run else execute_once()
    except (Attempt04RunnerError, OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "status": "GATE24E_STORAGE_ATTEMPT_04_BLOCKED",
            "error": str(exc),
            "gpu_executed": False,
            "simulation_executed": False,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") in {
        "READY_FOR_GATE24E_STORAGE_ATTEMPT_04",
        "ATTEMPT_04_STORAGE_PROBE_PASS",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
