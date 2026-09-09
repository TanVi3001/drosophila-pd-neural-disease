"""Audit the frozen Gate24E scientific batch without executing any job."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

import yaml

try:
    from scripts.prepare_gate24e_scientific_batch_plan import (
        AUTHORIZATION_PATH,
        BRAIN_ROOT,
        CHECKSUM_PATH,
        DISEASE_CHECKPOINT_SHA256,
        HEALTHY_CHECKPOINT_SHA256,
        MODEL_COMMIT,
        MAPPING_SHA256,
        NEURAL_TRANSFORM_SHA256,
        OUTPUT_ROOT,
        PLAN_PATH,
        PLATFORM_ROOT,
        RUNTIME_COMMIT,
        build_plan,
        canonical_plan_sha256,
        _checkpoint_path,
    )
except ModuleNotFoundError:  # direct ``python scripts/<tool>.py`` invocation
    from prepare_gate24e_scientific_batch_plan import (
        AUTHORIZATION_PATH,
        BRAIN_ROOT,
        CHECKSUM_PATH,
        DISEASE_CHECKPOINT_SHA256,
        HEALTHY_CHECKPOINT_SHA256,
        MODEL_COMMIT,
        MAPPING_SHA256,
        NEURAL_TRANSFORM_SHA256,
        OUTPUT_ROOT,
        PLAN_PATH,
        PLATFORM_ROOT,
        RUNTIME_COMMIT,
        build_plan,
        canonical_plan_sha256,
        _checkpoint_path,
    )


ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "research/validation/gene_specific/parkin/driver_to_connectome_mapping.csv"
STORAGE_HISTORY = ROOT / "experiments/gate_24e_storage_probe/manifests/storage_qualification.json"
ATTEMPT_04 = ROOT / "experiments/gate_24e_storage_probe/attempt_04"
ATTEMPT_04_MANIFEST = ATTEMPT_04 / "manifests/storage_qualification.json"
EXECUTION_MANIFEST = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/execution_manifest.json"
HOLDOUT_MANIFEST = ROOT / "experiments/gate_24_prospective_validation/manifests/holdout_firewall_manifest.json"
MODEL_FREEZE = ROOT / "research/validation/prospective/parkin_model_freeze.yaml"
NEURAL_TRANSFORM = ROOT / "src/drosophila_pd_neural/parkin/transform.py"
ATTEMPT_05 = ROOT / "experiments/gate_24e_storage_probe/attempt_05"
REQUIRED_STORAGE_BYTES = 17_548_739_588
TECHNICAL_SEED = 9001


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _root_set_sha256(path: Path) -> tuple[int, str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    root_ids = sorted(str(row.get("root_id", "")).strip() for row in rows)
    return len(rows), hashlib.sha256(("\n".join(root_ids) + "\n").encode("utf-8")).hexdigest()


def _portable_plan(value: Any, repository_root: str) -> Any:
    """Normalize checkout-specific paths before comparing a frozen plan."""

    if isinstance(value, dict):
        return {key: _portable_plan(item, repository_root) for key, item in value.items()}
    if isinstance(value, list):
        return [_portable_plan(item, repository_root) for item in value]
    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        root = repository_root.replace("\\", "/").rstrip("/")
        return normalized.replace(root, "<REPOSITORY_ROOT>")
    return value


def _plan_repository_root(plan: dict[str, Any]) -> str:
    output_root = str(plan.get("output_root", "")).replace("\\", "/")
    marker = "/experiments/"
    if marker in output_root:
        return output_root.split(marker, maxsplit=1)[0]
    return str(ROOT)


def get_live_free_bytes(path: Path = ROOT) -> int:
    """Return free space on the volume containing the repository."""

    return int(shutil.disk_usage(path).free)


def _runtime_evidence(blockers: list[str]) -> dict[str, Any]:
    runtime_root = Path(PLATFORM_ROOT)
    evidence: dict[str, Any] = {
        "path": str(runtime_root),
        "exists": runtime_root.is_dir(),
        "head": None,
        "expected_head": RUNTIME_COMMIT,
        "clean": False,
    }
    if not runtime_root.is_dir():
        blockers.append("RUNTIME_WORKTREE_MISSING")
        return evidence
    try:
        evidence["head"] = subprocess.check_output(
            ["git", "-C", str(runtime_root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
        status = subprocess.check_output(
            ["git", "-C", str(runtime_root), "status", "--porcelain"],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        blockers.append(f"RUNTIME_WORKTREE_AUDIT_FAILED:{type(exc).__name__}")
        return evidence
    evidence["clean"] = not status.strip()
    if evidence["head"] != RUNTIME_COMMIT:
        blockers.append("RUNTIME_COMMIT_MISMATCH")
    if not evidence["clean"]:
        blockers.append("RUNTIME_WORKTREE_DIRTY")
    return evidence


def _authorization_is_valid(document: dict[str, Any], plan_sha: str) -> bool:
    if document.get("status") != "SCIENTIFIC_BATCH_AUTHORIZATION_APPROVED":
        return False
    if document.get("decision") != "APPROVED_FOR_EXACT_GATE24E_25_JOB_BATCH":
        return False
    if document.get("scientific_batch_plan_sha256") != plan_sha:
        return False
    if document.get("storage_capacity_resolved") is not True:
        return False
    if document.get("scientific_batch_authorized") is not True:
        return False
    reviewers = {str(document.get("reviewer_1", "")).strip(), str(document.get("reviewer_2", "")).strip()}
    if len(reviewers) != 2 or "" in reviewers:
        return False
    try:
        date.fromisoformat(str(document.get("review_date", "")))
    except ValueError:
        return False
    return True


def audit(*, live_free_bytes: int | None = None) -> dict[str, Any]:
    blockers: list[str] = []
    plan = _json(PLAN_PATH)
    expected_plan = build_plan()
    plan_sha = canonical_plan_sha256(plan) if plan else "MISSING"
    expected_sha = plan_sha

    if not plan:
        blockers.append("SCIENTIFIC_BATCH_PLAN_MISSING")
    elif _portable_plan(plan, _plan_repository_root(plan)) != _portable_plan(expected_plan, str(ROOT)):
        blockers.append("FROZEN_BATCH_PLAN_MISMATCH")
    if not CHECKSUM_PATH.is_file() or CHECKSUM_PATH.read_text(encoding="ascii").strip() != f"{expected_sha}  scientific_batch_plan.json":
        blockers.append("SCIENTIFIC_BATCH_PLAN_CHECKSUM_MISMATCH")

    if not MAPPING.is_file():
        blockers.append("MAPPING_MISSING")
        mapping_count, mapping_sha = 0, "MISSING"
        root_sha = "MISSING"
    else:
        mapping_count, root_sha = _root_set_sha256(MAPPING)
        mapping_sha = _sha256(MAPPING)
        if mapping_count != 330:
            blockers.append("TARGET_ROOT_COUNT_MISMATCH")
        if mapping_sha != MAPPING_SHA256:
            blockers.append("MAPPING_SHA256_MISMATCH")
        if root_sha != plan.get("target_roots_sha256"):
            blockers.append("TARGET_ROOTS_SHA256_MISMATCH")

    if not MODEL_FREEZE.is_file():
        blockers.append("MODEL_FREEZE_MISSING")
        freeze: dict[str, Any] = {}
    else:
        loaded_freeze = yaml.safe_load(MODEL_FREEZE.read_text(encoding="utf-8"))
        freeze = loaded_freeze if isinstance(loaded_freeze, dict) else {}
    if freeze.get("status") != "MODEL_FREEZE_COMPLETE":
        blockers.append("MODEL_FREEZE_NOT_COMPLETE")
    if freeze.get("model_commit") != MODEL_COMMIT:
        blockers.append("MODEL_COMMIT_MISMATCH")
    if freeze.get("mapping_sha256") != MAPPING_SHA256:
        blockers.append("MODEL_FREEZE_MAPPING_MISMATCH")
    if freeze.get("target_neurons_sha256") != plan.get("target_roots_sha256"):
        blockers.append("MODEL_FREEZE_TARGET_ROOTS_MISMATCH")
    if freeze.get("target_root_count") != 330:
        blockers.append("MODEL_FREEZE_TARGET_COUNT_MISMATCH")
    transform = freeze.get("disease_transform") or {}
    if transform.get("sha256") != NEURAL_TRANSFORM_SHA256:
        blockers.append("MODEL_FREEZE_TRANSFORM_MISMATCH")
    if not NEURAL_TRANSFORM.is_file() or _sha256(NEURAL_TRANSFORM) != NEURAL_TRANSFORM_SHA256:
        blockers.append("NEURAL_TRANSFORM_SOURCE_MISMATCH")

    checkpoint_results: dict[str, bool] = {}
    for parameter, expected in {"healthy": HEALTHY_CHECKPOINT_SHA256, **DISEASE_CHECKPOINT_SHA256}.items():
        path = _checkpoint_path(0.0 if parameter == "healthy" else float(parameter))
        actual = _sha256(Path(path)) if Path(path).is_file() else "MISSING"
        checkpoint_results[parameter] = actual == expected
        if actual != expected:
            blockers.append(f"CHECKPOINT_HASH_MISMATCH:{parameter}")

    runtime = _runtime_evidence(blockers)
    storage_history = _json(STORAGE_HISTORY)
    attempt04 = _json(ATTEMPT_04_MANIFEST)
    attempt04_storage = attempt04.get("storage") or {}
    required = int(attempt04_storage.get("required_bytes", REQUIRED_STORAGE_BYTES))
    if required != REQUIRED_STORAGE_BYTES:
        blockers.append("LOCKED_STORAGE_REQUIREMENT_MISMATCH")
    if attempt04.get("status") != "ATTEMPT_04_STORAGE_PROBE_PASS":
        blockers.append("ATTEMPT_04_NOT_PASS")
    if attempt04.get("storage_measurements_valid") is not True:
        blockers.append("ATTEMPT_04_STORAGE_MEASUREMENTS_INVALID")
    if storage_history.get("current_estimate_source") != "attempt_04":
        blockers.append("STORAGE_ESTIMATE_SOURCE_NOT_ATTEMPT_04")
    if storage_history.get("current_qualification_status") != "WAITING_GATE24E_STORAGE_CAPACITY":
        blockers.append("STORAGE_QUALIFICATION_STATE_CHANGED")
    live = get_live_free_bytes() if live_free_bytes is None else int(live_free_bytes)
    capacity_pass = live > required
    if not capacity_pass:
        blockers.append("STORAGE_CAPACITY_NOT_RESOLVED")

    execution = _json(EXECUTION_MANIFEST)
    execution_zero = (
        execution.get("status") == "NOT_EXECUTED"
        and execution.get("executed_job_count") == 0
        and execution.get("gpu_jobs_executed") == 0
        and execution.get("simulation_jobs_executed") == 0
    )
    if not execution_zero:
        blockers.append("SCIENTIFIC_EXECUTION_NOT_ZERO")
    output_root_exists = OUTPUT_ROOT.exists()
    if output_root_exists:
        blockers.append("SCIENTIFIC_OUTPUT_ROOT_ALREADY_EXISTS")
    if ATTEMPT_05.exists():
        blockers.append("ATTEMPT_05_EXISTS")

    holdout = _json(HOLDOUT_MANIFEST)
    holdout_sealed = (
        holdout.get("status") == "SEALED"
        and holdout.get("no_numeric_holdout_import") is True
        and holdout.get("no_holdout_tuning") is True
    )
    if not holdout_sealed:
        blockers.append("HOLDOUT_NOT_SEALED")

    authorization = _json(AUTHORIZATION_PATH)
    authorization_valid = _authorization_is_valid(authorization, expected_sha)
    if not authorization_valid:
        blockers.append("SCIENTIFIC_BATCH_HUMAN_REVIEW_PENDING")

    # The expected current state is intentionally blocked. This is an audit
    # result, not a failed command, so CI can verify the firewall.
    status = (
        "READY_FOR_GATE24E_25_JOB_SCIENTIFIC_BATCH"
        if not blockers
        else "BLOCKED_GATE24E_SCIENTIFIC_BATCH_PREFLIGHT"
    )
    next_action = (
        "RESOLVE_STORAGE_CAPACITY_ONLY"
        if "STORAGE_CAPACITY_NOT_RESOLVED" in blockers
        else "SCIENTIFIC_BATCH_AUTHORIZATION_REVIEW"
        if "SCIENTIFIC_BATCH_HUMAN_REVIEW_PENDING" in blockers
        else "STOP_AND_REVIEW_PREFLIGHT_BLOCKERS"
    )
    return {
        "schema_version": "gate24e-scientific-batch-preflight-v1",
        "status": status,
        "blockers": blockers,
        "next_allowed_action": next_action,
        "plan_sha256": expected_sha,
        "job_count": plan.get("job_count"),
        "healthy_job_count": plan.get("healthy_job_count"),
        "parkin_job_count": plan.get("parkin_job_count"),
        "mapping_count": mapping_count,
        "mapping_sha256": mapping_sha,
        "target_roots_sha256": root_sha,
        "checkpoint_hashes_pass": all(checkpoint_results.values()),
        "checkpoint_results": checkpoint_results,
        "runtime": runtime,
        "attempt_04": {
            "status": attempt04.get("status"),
            "storage_measurements_valid": attempt04.get("storage_measurements_valid"),
            "storage_qualified": attempt04.get("storage_qualified"),
            "preserved": ATTEMPT_04.is_dir() and ATTEMPT_04_MANIFEST.is_file(),
        },
        "current_free_bytes": live,
        "required_bytes": required,
        "capacity_pass": capacity_pass,
        "output_root_exists": output_root_exists,
        "scientific_jobs_executed": 0 if execution_zero else execution.get("executed_job_count"),
        "scientific_batch_authorized": False,
        "authorization_status": authorization.get("status"),
        "authorization_valid": authorization_valid,
        "holdout": "SEALED" if holdout_sealed else holdout.get("status"),
        "gpu_executed": False,
        "simulation_executed": False,
    }


def main() -> int:
    result = audit()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
