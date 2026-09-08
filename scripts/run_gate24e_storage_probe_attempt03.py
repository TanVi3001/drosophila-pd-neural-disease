"""Authorize exactly one future Gate24E storage probe without running it.

The default invocation is a dry-run.  It verifies the human-approved runtime
amendment, both platform worktrees, the sealed holdout, and the wrapper
contract, then prints the one command that a later operator may execute.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Sequence

# ``python scripts/<file>.py`` places only ``scripts/`` on sys.path. Add the
# repository root before importing sibling package modules so the documented
# command works both as a file and as a module.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import audit_gate24e_runtime_amendment
from scripts.run_neural_experiment import (
    AMENDED_PLATFORM_COMMIT,
    FROZEN_CPG_DEFAULT_HZ,
    FROZEN_FLYGYM_VERSION,
    LEGACY_ARTIFACT_PROFILE,
    MEMORY_SAFE_ARTIFACT_PROFILE,
    _brain_python,
    _installed_distribution_version,
    validate_runtime_contract,
)

ROOT = Path(__file__).resolve().parents[1]
ATTEMPT_ID = "attempt_03"
ATTEMPT_ROOT = ROOT / "experiments" / "gate_24e_storage_probe" / ATTEMPT_ID
ATTEMPT_RUN = ATTEMPT_ROOT / "run"
ATTEMPT_LOGS = ATTEMPT_ROOT / "logs"
ATTEMPT_MANIFESTS = ATTEMPT_ROOT / "manifests"
RUNNER = ROOT / "scripts" / "run_neural_experiment.py"
BRAIN_ROOT = ROOT.parent / "external" / "fly-brain-audit"
PLATFORM_ROOT = ROOT.parent / "drosophila-pd-flygym-gate24-memorysafe-clean"
ORIGINAL_PLATFORM_ROOT = ROOT.parent / "drosophila-pd-flygym-gate24-clean"
PLATFORM_COMMIT = AMENDED_PLATFORM_COMMIT
ARTIFACT_PROFILE = MEMORY_SAFE_ARTIFACT_PROFILE
PROBE_SEED = 9001
SCIENTIFIC_SEEDS = (0, 1, 2, 3, 4)
STEPS = 100000
DURATION_S = 10.0
DEVICE = "cuda"
ORIGINAL_COMMIT = "3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06"
AMENDMENT_SHA256 = "d2fcb187dd5609169d52f7e499a0570a83bedc45b687d6c9b8fe3ab72790be0a"
RUNTIME_SIGNOFF = ROOT / "research/validation/prospective/parkin_runtime_amendment_reviewer_signoff.json"
FIREWALL = ROOT / "experiments/gate_24_prospective_validation/manifests/holdout_firewall_manifest.json"


class Attempt03Error(RuntimeError):
    """Raised when the one-shot technical probe contract is not satisfied."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Attempt03Error(f"Missing required JSON: {path}") from exc
    if not isinstance(value, dict):
        raise Attempt03Error(f"Expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_text(path: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise Attempt03Error(f"Git inspection failed in {path}: {result.stderr.strip()}")
    return result.stdout.strip()


def _verify_clean_platform(path: Path, expected_commit: str) -> dict[str, Any]:
    if not path.is_dir():
        raise Attempt03Error(f"Missing platform worktree: {path}")
    head = _git_text(path, "rev-parse", "HEAD")
    status = _git_text(path, "status", "--porcelain")
    if head != expected_commit:
        raise Attempt03Error(f"Platform commit mismatch in {path}: {head} != {expected_commit}")
    if status:
        raise Attempt03Error(f"Platform worktree is dirty: {path}: {status}")
    return {"path": str(path), "commit": head, "clean": True}


def _validate_approval_documents(
    amendment_audit: dict[str, Any],
    signoff: dict[str, Any],
    amendment_sha256: str,
) -> None:
    required_audit = {
        "status": "READY_FOR_ATTEMPT_03",
        "runtime_review_state": "APPROVED",
        "reviewer_1": "Tuan Le",
        "reviewer_2": "To Dang Minh Tuan",
        "attempt_03_authorized": True,
        "scientific_batch_authorized": False,
        "holdout": "SEALED",
        "scientific_jobs_executed": 0,
        "blockers": [],
    }
    for key, expected in required_audit.items():
        if amendment_audit.get(key) != expected:
            raise Attempt03Error(f"Amendment audit mismatch: {key}={amendment_audit.get(key)!r}")

    if signoff.get("status") != "RUNTIME_AMENDMENT_APPROVED":
        raise Attempt03Error("Runtime amendment signoff is not approved")
    if signoff.get("decision") != "APPROVED_FOR_GATE24E_RUNTIME_AMENDMENT":
        raise Attempt03Error("Runtime amendment decision is not approved")
    reviewers = [str(signoff.get(name, "")).strip() for name in ("reviewer_1", "reviewer_2")]
    if not all(reviewers) or reviewers[0].casefold() == reviewers[1].casefold():
        raise Attempt03Error("Two distinct non-empty human reviewers are required")
    if signoff.get("attempt_03_authorized") is not True:
        raise Attempt03Error("attempt_03 is not authorized by the signoff")
    if signoff.get("scientific_batch_authorized") is not False:
        raise Attempt03Error("Scientific batch authorization must remain false")
    if amendment_sha256 != AMENDMENT_SHA256:
        raise Attempt03Error("Runtime amendment SHA256 does not match the signed record")


def _verify_approval() -> dict[str, Any]:
    amendment_audit = audit_gate24e_runtime_amendment.audit()
    signoff = _read_json(RUNTIME_SIGNOFF)
    _validate_approval_documents(
        amendment_audit,
        signoff,
        _sha256(audit_gate24e_runtime_amendment.AMENDMENT),
    )
    return {"audit": amendment_audit, "signoff": signoff}


def _verify_sealed_holdout() -> dict[str, Any]:
    firewall = _read_json(FIREWALL)
    if firewall.get("status") != "SEALED":
        raise Attempt03Error(f"Holdout is not sealed: {firewall.get('status')!r}")
    return firewall


def _ensure_attempt_is_unused() -> None:
    if ATTEMPT_ROOT.is_dir() and any(path.is_file() for path in ATTEMPT_ROOT.rglob("*")):
        raise Attempt03Error("attempt_03 already contains output; refusing overwrite or retry")


def build_attempt_command(python: Path | None = None, output: Path = ATTEMPT_RUN) -> list[str]:
    """Build the only command authorized for the future technical probe."""
    command = [
        str(python or Path(sys.executable)),
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
        str(output),
    ]
    forbidden = {"--prepared-checkpoint", "--parameter", "--video", "--video-output", "--compare-to"}
    if forbidden.intersection(command) or "--cpg-frequency-hz" in command:
        raise Attempt03Error("Attempt command contains a forbidden option")
    return command


def _verify_wrapper_contract() -> dict[str, Any]:
    validate_runtime_contract(platform_commit=PLATFORM_COMMIT, artifact_profile=ARTIFACT_PROFILE)
    brain_python = _brain_python(BRAIN_ROOT, None)
    if not brain_python.is_file():
        raise Attempt03Error(f"Brain runtime Python is missing: {brain_python}")
    environment_verified = True
    try:
        flygym_version = _installed_distribution_version(brain_python, "flygym")
    except RuntimeError:
        # A repository checkout may intentionally lack the simulation venv.
        # Dry-run can still validate the locked dependency declaration and CLI
        # contract; execute mode will re-check the installed distribution.
        requirements = PLATFORM_ROOT / "requirements-colab.txt"
        pyproject = PLATFORM_ROOT / "pyproject.toml"
        declared = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (requirements, pyproject)
            if path.is_file()
        )
        if not re.search(r"flygym(?:==|\s*=\s*)2\.1\.0", declared):
            raise Attempt03Error("FlyGym 2.1.0 is neither installed nor declared by amended platform")
        flygym_version = FROZEN_FLYGYM_VERSION
        environment_verified = False
    if flygym_version != FROZEN_FLYGYM_VERSION:
        raise Attempt03Error(f"Expected FlyGym {FROZEN_FLYGYM_VERSION}, got {flygym_version}")
    platform_runner = PLATFORM_ROOT / "scripts" / "run_brain_body_rollout.py"
    if not platform_runner.is_file():
        raise Attempt03Error(f"Amended runner is missing: {platform_runner}")
    runner_source = platform_runner.read_text(encoding="utf-8")
    if '"--artifact-profile"' not in runner_source:
        raise Attempt03Error("Amended runner does not declare --artifact-profile")
    downstream = [
        str(brain_python),
        str(platform_runner),
        "--brain-root",
        str(BRAIN_ROOT),
        "--condition",
        "healthy",
        "--seed",
        str(PROBE_SEED),
        "--steps",
        str(STEPS),
        "--device",
        DEVICE,
        "--output",
        str(ATTEMPT_RUN),
        "--stimulus",
        "p9",
        "--artifact-profile",
        ARTIFACT_PROFILE,
    ]
    if "--artifact-profile" not in downstream:
        raise Attempt03Error("Amended downstream command lacks the memory-safe artifact profile")
    if "--cpg-frequency-hz" in downstream:
        raise Attempt03Error("Unsupported CPG CLI flag was forwarded")
    return {
        "brain_python": str(brain_python),
        "flygym_version": flygym_version,
        "environment_verified": environment_verified,
        "downstream_command": downstream,
        "cpg_frequency_hz": FROZEN_CPG_DEFAULT_HZ,
    }


def prepare_dry_run() -> dict[str, Any]:
    approval = _verify_approval()
    platforms = {
        "original": _verify_clean_platform(ORIGINAL_PLATFORM_ROOT, ORIGINAL_COMMIT),
        "amended": _verify_clean_platform(PLATFORM_ROOT, PLATFORM_COMMIT),
    }
    firewall = _verify_sealed_holdout()
    _ensure_attempt_is_unused()
    wrapper = _verify_wrapper_contract()
    command = build_attempt_command()
    return {
        "status": "READY_FOR_GATE24E_STORAGE_ATTEMPT_03",
        "attempt_id": ATTEMPT_ID,
        "attempt_root": str(ATTEMPT_ROOT),
        "platform_commit": PLATFORM_COMMIT,
        "artifact_profile": ARTIFACT_PROFILE,
        "seed": PROBE_SEED,
        "steps": STEPS,
        "duration_s": DURATION_S,
        "device": DEVICE,
        "holdout": firewall.get("status"),
        "scientific_jobs_executed": approval["audit"].get("scientific_jobs_executed"),
        "scientific_batch_authorized": approval["audit"].get("scientific_batch_authorized"),
        "scientific_seeds_excluded": list(SCIENTIFIC_SEEDS),
        "platforms": platforms,
        "wrapper": wrapper,
        "command": command,
        "executed": False,
        "gpu_executed": False,
        "simulation_executed": False,
        "created_at_utc": datetime.now(UTC).isoformat(),
    }


def _cuda_preflight(python: Path) -> dict[str, Any]:
    code = (
        "import json, torch; ok=bool(torch.cuda.is_available()); "
        "print(json.dumps({'available':ok, 'torch':torch.__version__, "
        "'cuda':torch.version.cuda, 'device':torch.cuda.get_device_name(0) if ok else 'NO_GPU'}))"
    )
    result = subprocess.run([str(python), "-c", code], capture_output=True, text=True, check=False)
    if result.returncode:
        raise Attempt03Error(f"CUDA preflight failed: {result.stderr.strip()}")
    value = json.loads(result.stdout.strip().splitlines()[-1])
    if value.get("available") is not True:
        raise Attempt03Error(f"CUDA is unavailable; CPU fallback is forbidden: {value}")
    return value


def execute_once() -> int:
    plan = prepare_dry_run()
    brain_python = Path(plan["wrapper"]["brain_python"])
    cuda = _cuda_preflight(brain_python)
    ATTEMPT_LOGS.mkdir(parents=True, exist_ok=True)
    ATTEMPT_MANIFESTS.mkdir(parents=True, exist_ok=True)
    authorization = dict(plan)
    authorization.update({"execution_authorized": True, "cuda": cuda})
    (ATTEMPT_MANIFESTS / "attempt_03_authorization.json").write_text(
        json.dumps(authorization, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    command = plan["command"]
    with (ATTEMPT_LOGS / "storage_probe_attempt_03.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.dry_run:
            print(json.dumps(prepare_dry_run(), indent=2, ensure_ascii=False))
            return 0
        return execute_once()
    except (Attempt03Error, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
