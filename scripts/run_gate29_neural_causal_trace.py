"""Audit and optionally trace the healthy Gate29 brain-body execution path.

The default mode is read-only.  The paired technical mode is deliberately
limited to two healthy engineering jobs with seed 9201.  No disease,
calibration, fitting, or dopamine arguments are accepted by this CLI.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np

from drosophila_pd_neural.causal_trace import (
    TRACE_ATOL,
    TRACE_RTOL,
    TraceStep,
    TraceValidationError,
    compare_trace_arrays,
    summarize_trace_arrays,
    validate_trace_steps,
)
from drosophila_pd_neural.causal_trace.schema import (
    DISCRETE_TRACE_KEYS,
    GPU_MONITOR_INTERVAL_S,
    GPU_STOP_TEMPERATURE_C,
    NONPERTURBATION_COMPARISONS,
    TRACE_ARRAY_KEYS,
    TRACE_SCHEMA_VERSION,
)


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"
SOURCE_MAIN_COMMIT = "004b9ee3c8938206e71b9908123f74cd0b7d2c97"
HEALTHY_CHECKPOINT_SHA256 = "d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691"
TECHNICAL_SEED = 9201
TECHNICAL_DURATION_S = 0.5
TECHNICAL_STEPS = 5000
MAX_TECHNICAL_JOBS = 2
GATE_ROOT = ROOT / "experiments/gate_29_neural_causal_trace"
MANIFEST_ROOT = GATE_ROOT / "manifests"
RESULT_ROOT = GATE_ROOT / "results"
ALIGNMENT = MANIFEST_ROOT / "gate28b_human_closure_alignment.json"
GATE28B_MANIFEST = ROOT / "experiments/gate_28b_virtual_assay_adapter/manifests/gate28b_manifest.json"
GATE28B_SIGNOFF = ROOT / "research/validation/prospective/gate28b_virtual_assay_adapter_reviewer_signoff.json"
GATE29_MANIFEST = MANIFEST_ROOT / "gate29_manifest.json"
SIGNAL_INVENTORY = MANIFEST_ROOT / "runtime_signal_inventory.json"
EDGE_REGISTRY = MANIFEST_ROOT / "causal_edge_registry.json"
RUNTIME_AUDIT = MANIFEST_ROOT / "runtime_execution_path_audit.json"
SUMMARY_PATH = RESULT_ROOT / "technical_trace_summary.json"
COMPARISON_PATH = RESULT_ROOT / "nonperturbation_comparison.json"
BASELINE_LOCK = MANIFEST_ROOT / "baseline_execution_lock.json"
TRACE_AUTHORIZATION = MANIFEST_ROOT / "trace_execution_authorization.json"
TRACE_ATTEMPT_PROVENANCE = MANIFEST_ROOT / "trace_attempt_provenance.json"
TRACE_OPTIMIZATION_QUALIFICATION = MANIFEST_ROOT / "trace_runner_optimization_qualification.json"
REPRODUCIBILITY_INVENTORY = MANIFEST_ROOT / "reproducibility_inventory.json"
REPRODUCIBILITY_CHECKSUMS = MANIFEST_ROOT / "checksums.sha256"
AUTHORIZATION_ONLY_PATH = (
    "experiments/gate_29_neural_causal_trace/manifests/"
    "trace_execution_authorization.json"
)
AUTHORIZATION_SCHEMA_VERSION = "gate29-trace-execution-authorization-v2"
EXECUTION_CODE_SNAPSHOT_PATHS = (
    "scripts/run_gate29_neural_causal_trace.py",
    "configs/generation2/gate29_causal_trace_policy.yaml",
    "configs/generation2/gate29_trace_temporal_contract.yaml",
    "experiments/gate_29_neural_causal_trace/manifests/baseline_execution_lock.json",
    "experiments/gate_29_neural_causal_trace/manifests/trace_attempt_provenance.json",
)
OUTPUT_ROOT = ROOT.parent / "gate29_technical_outputs/neural_causal_trace"
RUNTIME_ROOT_DEFAULT = ROOT.parent / "drosophila-pd-flygym-gate24-memorysafe-clean"
BRAIN_ROOT_DEFAULT = ROOT.parent / "drosophila-pd-neural-disease/external/fly-brain"
RUNTIME_PYTHON_DEFAULT = ROOT.parent / "drosophila-pd-flygym/.venv/Scripts/python.exe"


class Gate29Error(RuntimeError):
    """Fail-closed Gate29 error."""


class Gate29JobAbort(Gate29Error):
    """Safety abort for an active technical process."""


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _gate29_reproducibility_paths() -> list[Path]:
    """Return only lightweight, reviewable Gate29 files; never raw trace data."""

    paths = [
        ROOT / "configs/generation2/gate29_causal_trace_policy.yaml",
        ROOT / "configs/generation2/gate29_trace_temporal_contract.yaml",
        ROOT / "docs/research_design/gate29_neural_causal_trace_report.md",
        ROOT / "research/validation/prospective/gate29_neural_causal_trace_reviewer_signoff.json",
        ROOT / "tests/test_gate29_neural_causal_trace.py",
        ROOT / "scripts/run_gate29_neural_causal_trace.py",
        GATE29_MANIFEST,
        ALIGNMENT,
        RUNTIME_AUDIT,
        SIGNAL_INVENTORY,
        EDGE_REGISTRY,
        MANIFEST_ROOT / "controller_layer_interpretation.json",
        BASELINE_LOCK,
        TRACE_AUTHORIZATION,
        TRACE_ATTEMPT_PROVENANCE,
        TRACE_OPTIMIZATION_QUALIFICATION,
        SUMMARY_PATH,
        COMPARISON_PATH,
    ]
    paths.extend(sorted((ROOT / "src/drosophila_pd_neural/causal_trace").glob("*.py")))
    return paths


def write_reproducibility_inventory() -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    missing: list[str] = []
    for path in _gate29_reproducibility_paths():
        if not path.is_file():
            missing.append(path.relative_to(ROOT).as_posix())
            continue
        files.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    if missing:
        raise Gate29Error(f"Gate29 reproducibility files missing: {missing}")
    inventory = {
        "schema_version": "gate29-reproducibility-inventory-v1",
        "scope": "LIGHTWEIGHT_GATE29_METADATA_ONLY",
        "raw_trace_committed": False,
        "file_count": len(files),
        "files": files,
    }
    _write_json(REPRODUCIBILITY_INVENTORY, inventory)
    lines = [
        f"{record['sha256']}  {record['path']}"
        for record in files
    ]
    REPRODUCIBILITY_CHECKSUMS.parent.mkdir(parents=True, exist_ok=True)
    REPRODUCIBILITY_CHECKSUMS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return inventory


def verify_reproducibility_inventory() -> dict[str, Any]:
    inventory = _json(REPRODUCIBILITY_INVENTORY)
    mismatches: list[str] = []
    for record in inventory.get("files", []):
        path = ROOT / record["path"]
        if not path.is_file():
            mismatches.append(f"missing:{record['path']}")
            continue
        if _sha256(path) != record["sha256"]:
            mismatches.append(f"sha256:{record['path']}")
    checksum_lines = {
        line.split("  ", 1)[1]: line.split("  ", 1)[0]
        for line in REPRODUCIBILITY_CHECKSUMS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    if checksum_lines != {record["path"]: record["sha256"] for record in inventory["files"]}:
        mismatches.append("checksums.sha256 does not match inventory")
    return {
        "status": "GATE29_REPRODUCIBILITY_PASS" if not mismatches else "GATE29_REPRODUCIBILITY_FAIL",
        "file_count": len(inventory.get("files", [])),
        "raw_trace_committed": inventory.get("raw_trace_committed"),
        "mismatches": mismatches,
    }


def _baseline_root() -> Path:
    return OUTPUT_ROOT / "baseline"


def _baseline_artifacts() -> tuple[str, ...]:
    return (
        "rollout.npz",
        "metadata.json",
        "manifest.json",
        "rollout_index.json",
        "brain_body_summary.json",
        "brain_body_manifest.json",
        "metrics/metrics.json",
        "metrics/metrics.csv",
        "report/summary.md",
    )


def _baseline_hashes() -> dict[str, str]:
    root = _baseline_root()
    missing = [name for name in _baseline_artifacts() if not (root / name).is_file()]
    if missing:
        raise Gate29Error(f"baseline artifacts missing: {missing}")
    return {name: _sha256(root / name) for name in _baseline_artifacts()}


def verify_baseline_execution_lock() -> dict[str, Any]:
    lock = _json(BASELINE_LOCK)
    root = _baseline_root()
    blockers: list[str] = []
    if lock.get("status") != "GATE29_BASELINE_EXECUTION_LOCKED":
        blockers.append("baseline lock status is not locked")
    if lock.get("baseline_rerun_allowed") is not False:
        blockers.append("baseline rerun is not explicitly blocked")
    if lock.get("baseline_seed") != TECHNICAL_SEED:
        blockers.append("baseline seed does not match technical seed")
    if lock.get("runtime_commit") != RUNTIME_COMMIT:
        blockers.append("baseline runtime commit mismatch")
    if lock.get("healthy_checkpoint_sha256") != HEALTHY_CHECKPOINT_SHA256:
        blockers.append("baseline checkpoint mismatch")
    if not root.is_dir():
        blockers.append("baseline output directory missing")
        return {"status": "GATE29_BASELINE_EXECUTION_LOCK_BLOCKED", "blockers": blockers}
    try:
        hashes = _baseline_hashes()
    except Gate29Error as exc:
        blockers.append(str(exc))
        hashes = {}
    if hashes.get("rollout.npz") != lock.get("baseline_rollout_sha256"):
        blockers.append("baseline rollout SHA256 mismatch")
    if hashes.get("metadata.json") != lock.get("baseline_metadata_sha256"):
        blockers.append("baseline metadata SHA256 mismatch")
    metadata = _json(root / "metadata.json") if (root / "metadata.json").is_file() else {}
    simulation = metadata.get("simulation", {})
    required = {
        "condition_id": "healthy",
        "random_seed": TECHNICAL_SEED,
        "timestep_s": 0.0001,
        "repository_commit": RUNTIME_COMMIT,
        "brain_checkpoint_sha256": HEALTHY_CHECKPOINT_SHA256,
    }
    for key, expected in required.items():
        if simulation.get(key) != expected:
            blockers.append(f"baseline metadata {key} mismatch")
    if metadata.get("timestep_s") != 0.0001:
        blockers.append("baseline top-level timestep mismatch")
    summary = _json(root / "brain_body_summary.json") if (root / "brain_body_summary.json").is_file() else {}
    if summary.get("condition") != "healthy" or summary.get("seed") != TECHNICAL_SEED:
        blockers.append("baseline summary condition/seed mismatch")
    if summary.get("steps") != TECHNICAL_STEPS:
        blockers.append("baseline summary step count mismatch")
    return {
        "status": "GATE29_BASELINE_EXECUTION_LOCK_PASS" if not blockers else "GATE29_BASELINE_EXECUTION_LOCK_BLOCKED",
        "blockers": blockers,
        "baseline_rerun_allowed": False,
        "baseline_hashes": hashes,
    }


def _contains_files(path: Path) -> bool:
    return path.is_dir() and any(item.is_file() for item in path.rglob("*"))


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise Gate29Error(f"git command failed: {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def _git_blob_sha(root: Path, revision: str, relative_path: str) -> str:
    """Return one committed file's blob identity, failing closed if absent."""

    return _git(root, "rev-parse", f"{revision}:{relative_path}")


def _validate_authorization_commit_structure(
    root: Path, authorization: Mapping[str, Any]
) -> dict[str, str]:
    """Validate the Git parent proof for a committed authorization transition."""

    if _git(root, "status", "--porcelain"):
        raise Gate29Error("GATE29_TRACE_EXECUTION_DIRTY_WORKTREE")

    authorized_code_head = authorization.get("authorized_code_head")
    if not isinstance(authorized_code_head, str) or not re.fullmatch(
        r"[0-9a-f]{40}", authorized_code_head
    ):
        raise Gate29Error("GATE29_TRACE_EXECUTION_AUTHORIZATION_CODE_HEAD_INVALID")
    try:
        object_type = _git(root, "cat-file", "-t", authorized_code_head)
    except Gate29Error as exc:
        raise Gate29Error("GATE29_TRACE_EXECUTION_AUTHORIZATION_CODE_HEAD_INVALID") from exc
    if object_type != "commit":
        raise Gate29Error("GATE29_TRACE_EXECUTION_AUTHORIZATION_CODE_HEAD_INVALID")

    current_head = _git(root, "rev-parse", "HEAD")
    parent_record = _git(root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    if len(parent_record) != 2:
        raise Gate29Error("GATE29_TRACE_EXECUTION_AUTHORIZATION_MERGE_COMMIT_REJECTED")
    if parent_record[1] != authorized_code_head:
        raise Gate29Error("GATE29_TRACE_EXECUTION_AUTHORIZATION_PARENT_MISMATCH")

    changed_paths = _git(
        root, "diff", "--name-only", f"{authorized_code_head}..HEAD"
    ).splitlines()
    if changed_paths != [AUTHORIZATION_ONLY_PATH]:
        raise Gate29Error("GATE29_TRACE_EXECUTION_AUTHORIZATION_COMMIT_SCOPE_INVALID")

    for relative_path in EXECUTION_CODE_SNAPSHOT_PATHS:
        try:
            authorized_blob = _git_blob_sha(root, authorized_code_head, relative_path)
            current_blob = _git_blob_sha(root, current_head, relative_path)
        except Gate29Error as exc:
            raise Gate29Error(
                f"GATE29_TRACE_EXECUTION_AUTHORIZATION_CODE_DRIFT:{relative_path}"
            ) from exc
        if authorized_blob != current_blob:
            raise Gate29Error(
                f"GATE29_TRACE_EXECUTION_AUTHORIZATION_CODE_DRIFT:{relative_path}"
            )

    return {
        "authorized_code_head": authorized_code_head,
        "authorization_commit": current_head,
    }


def _resolve_paths(args: argparse.Namespace) -> dict[str, Path]:
    return {
        "runtime_root": Path(args.runtime_root or RUNTIME_ROOT_DEFAULT).expanduser().resolve(),
        "brain_root": Path(args.brain_root or BRAIN_ROOT_DEFAULT).expanduser().resolve(),
        "runtime_python": Path(args.runtime_python or RUNTIME_PYTHON_DEFAULT).expanduser().resolve(),
        "output_root": Path(args.output_root or OUTPUT_ROOT).expanduser().resolve(),
    }


def _existing_disk_path(path: Path) -> Path:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    if not candidate.exists():
        raise Gate29Error(f"Cannot resolve an existing path for disk usage: {path}")
    return candidate


def audit_gate28b_closure() -> dict[str, Any]:
    signoff = _json(GATE28B_SIGNOFF)
    gate_manifest = _json(GATE28B_MANIFEST)
    alignment = _json(ALIGNMENT)
    blockers: list[str] = []
    required_signoff = {
        "status": "GATE28B_VIRTUAL_ASSAY_ADAPTER_REVIEW_APPROVED",
        "decision": "APPROVED_GATE28B_VIRTUAL_ASSAY_ADAPTER_CLOSURE",
    }
    for key, expected in required_signoff.items():
        if signoff.get(key) != expected:
            blockers.append(f"Gate28B signoff {key} is not {expected}")
    if signoff.get("gate28b_closed") is not True:
        blockers.append("Gate28B signoff is not closed")
    if signoff.get("paper_assay_equivalence_established") is not False:
        blockers.append("Gate28B paper equivalence boundary changed")
    unresolved = {
        "frame_rate",
        "movement_threshold",
        "exclusion_rule",
        "per_fly_speed_computation",
    }
    if set(signoff.get("unresolved_source_fields", [])) != unresolved:
        blockers.append("Gate28B unresolved source-field set changed")
    if gate_manifest.get("technical_benchmark_seed") != 9101:
        blockers.append("Gate28B technical seed is not 9101")
    current_sha = _sha256(GATE28B_SIGNOFF)
    if alignment.get("current_approved_signoff", {}).get("file_sha256") != current_sha:
        blockers.append("Gate28B approved signoff SHA does not match current file")
    if alignment.get("historical_inventory_preserved") is not True:
        blockers.append("Gate28B historical inventory is not marked preserved")
    return {
        "status": "GATE28B_CLOSURE_PASS" if not blockers else "GATE28B_CLOSURE_BLOCKED",
        "blockers": blockers,
        "signoff_status": signoff.get("status"),
        "signoff_decision": signoff.get("decision"),
        "gate28b_closed": signoff.get("gate28b_closed"),
        "paper_assay_equivalence_established": signoff.get(
            "paper_assay_equivalence_established"
        ),
        "technical_seed": gate_manifest.get("technical_benchmark_seed"),
        "historical_inventory_preserved": alignment.get("historical_inventory_preserved"),
    }


def audit_runtime_contract(paths: Mapping[str, Path]) -> dict[str, Any]:
    runner = paths["runtime_root"] / "scripts/run_brain_body_rollout.py"
    blockers: list[str] = []
    if not runner.is_file():
        blockers.append(f"runtime runner missing: {runner}")
    else:
        runtime_head = _git(paths["runtime_root"], "rev-parse", "HEAD")
        if runtime_head != RUNTIME_COMMIT:
            blockers.append(f"runtime commit is {runtime_head}, expected {RUNTIME_COMMIT}")
    required_brain_files = (
        paths["brain_root"] / "brain_body_bridge.py",
        paths["brain_root"] / "code/run_pytorch.py",
        paths["brain_root"] / "data/2025_Completeness_783.csv",
        paths["brain_root"] / "data/2025_Connectivity_783.parquet",
        paths["brain_root"] / "data/plastic_weights.pt",
    )
    missing = [str(path) for path in required_brain_files if not path.is_file()]
    blockers.extend(f"brain file missing: {path}" for path in missing)
    checkpoint = paths["brain_root"] / "data/plastic_weights.pt"
    if checkpoint.is_file() and _sha256(checkpoint) != HEALTHY_CHECKPOINT_SHA256:
        blockers.append("healthy checkpoint SHA256 mismatch")
    return {
        "status": "RUNTIME_CONTRACT_PASS" if not blockers else "RUNTIME_CONTRACT_BLOCKED",
        "blockers": blockers,
        "runtime_commit": RUNTIME_COMMIT if runner.is_file() else None,
        "runtime_runner": str(runner),
        "healthy_checkpoint_sha256": HEALTHY_CHECKPOINT_SHA256,
    }


def _gpu_snapshot() -> dict[str, float]:
    query = "temperature.gpu,memory.used,utilization.gpu"
    result = subprocess.run(
        ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise Gate29Error(f"nvidia-smi failed: {result.stderr.strip()}")
    fields = [item.strip() for item in result.stdout.splitlines()[0].split(",")]
    if len(fields) != 3:
        raise Gate29Error("nvidia-smi telemetry could not be parsed")
    return {
        "temperature_c": float(fields[0]),
        "memory_used_mb": float(fields[1]),
        "utilization_percent": float(fields[2]),
    }


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    try:
        import psutil
    except ImportError:
        psutil = None
    if psutil is not None:
        try:
            root = psutil.Process(process.pid)
            children = root.children(recursive=True)
            for child in reversed(children):
                child.terminate()
            root.terminate()
            _, alive = psutil.wait_procs([*children, root], timeout=5.0)
            for child in alive:
                child.kill()
            if alive:
                psutil.wait_procs(alive, timeout=5.0)
        except (psutil.Error, OSError):
            pass
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5.0)


def _run_guarded(command: Sequence[str], log_path: Path, paths: Mapping[str, Path]) -> dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    source_path = str(ROOT / "src")
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_path
        if not existing_pythonpath
        else os.pathsep.join((source_path, existing_pythonpath))
    )
    with log_path.open("wb") as log:
        process = subprocess.Popen(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=ROOT,
            env=environment,
        )
        max_temperature: float | None = None
        peak_memory: float | None = None
        while process.poll() is None:
            try:
                snapshot = _gpu_snapshot()
            except (Gate29Error, OSError, ValueError, IndexError) as exc:
                _terminate_process_tree(process)
                raise Gate29JobAbort(
                    "GATE29_TECHNICAL_TRACE_ABORTED_GPU_MONITOR_FAILURE"
                ) from exc
            max_temperature = snapshot["temperature_c"] if max_temperature is None else max(
                max_temperature, snapshot["temperature_c"]
            )
            peak_memory = snapshot["memory_used_mb"] if peak_memory is None else max(
                peak_memory, snapshot["memory_used_mb"]
            )
            if snapshot["temperature_c"] >= GPU_STOP_TEMPERATURE_C:
                _terminate_process_tree(process)
                raise Gate29JobAbort("GATE29_TECHNICAL_TRACE_ABORTED_GPU_TEMPERATURE")
            time.sleep(GPU_MONITOR_INTERVAL_S)
        return_code = process.wait()
    if return_code != 0:
        raise Gate29Error(f"technical job failed with exit code {return_code}: {log_path}")
    return {
        "return_code": return_code,
        "max_observed_gpu_temperature_c": max_temperature,
        "device_peak_memory_used_mb": peak_memory,
        "temperature_monitor_interval_s": GPU_MONITOR_INTERVAL_S,
        "gpu_temperature_abort_threshold_c": GPU_STOP_TEMPERATURE_C,
        "log_path": str(log_path),
        "command": list(command),
    }


def _public_body_snapshot(simulation: Any, fly: Any, fly_name: str) -> dict[str, Any]:
    body_positions = np.asarray(simulation.get_body_positions(fly_name), dtype=float).copy()
    body_order = fly.get_bodysegs_order()
    names = [getattr(item, "name", str(item)) for item in body_order]
    thorax = body_positions[names.index("c_thorax")].copy()
    joint_positions = np.asarray(simulation.get_joint_angles(fly_name), dtype=float).copy()
    joint_velocity = np.asarray(simulation.get_joint_velocities(fly_name), dtype=float).copy()
    contact = simulation.get_ground_contact_info(fly_name)
    contact_found = np.asarray(contact[0], dtype=float).copy()
    from flygym.compose import ActuatorType

    actuator_position = np.asarray(
        simulation.get_actuator_forces(fly_name, ActuatorType.POSITION), dtype=float
    ).copy()
    return {
        "post_time_s": float(simulation.mj_data.time),
        "post_thorax_position_mm": thorax,
        "post_joint_positions": joint_positions,
        "post_joint_velocity": joint_velocity,
        "post_actuator_position": actuator_position,
        "post_contact_found": contact_found,
    }


class _RuntimeTraceCollector:
    """Read-only line tracer around the already-audited runtime loop."""

    STEP_LINES = {317, 319, 320, 323, 324, 340, 341}

    def __init__(self, runtime_script: Path) -> None:
        self.runtime_script = runtime_script.resolve()
        self.rows: list[dict[str, Any]] = []
        self.current: dict[str, Any] | None = None
        self._inside_capture = False
        self.runtime_line_events = 0
        self.non_runtime_line_events = 0

    def _capture(self, frame: Any, line: int) -> None:
        if self._inside_capture:
            return
        local = frame.f_locals
        if "step_index" not in local:
            return
        self._inside_capture = True
        try:
            simulation = local["simulation"]
            fly = local["fly"]
            fly_name = fly.name
            if line == 317:
                self.current = {
                    "step_index": int(local["step_index"]),
                    "pre_time_s": float(simulation.mj_data.time),
                }
            elif self.current is None:
                return
            elif line == 319:
                spikes = local["brain"].get_dn_spikes()
                names = list(spikes)
                self.current["dn_names"] = names
                self.current["dn_spikes"] = np.asarray([spikes[name] for name in names], dtype=float)
                decoder = local["decoder"]
                self.current["decoder_rates_hz"] = np.asarray(
                    [decoder.get_rate(name) for name in decoder.dn_names], dtype=float
                )
            elif line == 320:
                self.current["brain_body_drive"] = np.asarray(local["drive"], dtype=float).copy()
            elif line == 323:
                from flygym_demo.complex_terrain import HybridControllerObservation

                observation = HybridControllerObservation.from_sim(simulation, fly_name)
                self.current["controller_observation_thorax_z"] = float(observation.thorax_z)
                self.current["controller_observation_tarsus5_z"] = np.asarray(
                    observation.tarsus5_z, dtype=float
                ).copy()
                self.current["controller_observation_stumbling_contact_forces"] = np.asarray(
                    observation.stumbling_contact_forces, dtype=float
                ).copy()
                self.current["controller_observation_fly_heading"] = np.asarray(
                    observation.fly_heading, dtype=float
                ).copy()
                action = local["controller_action"]
                self.current["controller_action_joint_angles"] = np.asarray(
                    action.joint_angles, dtype=float
                ).copy()
                adhesion = action.adhesion_onoff
                self.current["controller_action_adhesion"] = np.asarray(
                    adhesion if adhesion is not None else np.zeros(6, dtype=bool)
                ).copy()
            elif line == 324:
                action = local["action"]
                self.current["applied_action_joint_angles"] = np.asarray(
                    action.joint_angles, dtype=float
                ).copy()
                adhesion = action.adhesion_onoff
                self.current["applied_action_adhesion"] = np.asarray(
                    adhesion if adhesion is not None else np.zeros(6, dtype=bool)
                ).copy()
            elif line == 340:
                self.current.update(_public_body_snapshot(simulation, fly, fly_name))
            elif line == 341:
                required = (
                    "dn_spikes",
                    "decoder_rates_hz",
                    "brain_body_drive",
                    "controller_action_joint_angles",
                    "controller_action_adhesion",
                    "post_time_s",
                    "post_thorax_position_mm",
                    "post_joint_positions",
                    "post_joint_velocity",
                    "post_actuator_position",
                    "post_contact_found",
                )
                missing = [name for name in required if name not in self.current]
                if missing:
                    raise Gate29Error(f"trace step missing signals: {missing}")
                self.rows.append(self.current)
                self.current = None
        finally:
            self._inside_capture = False

    def __call__(self, frame: Any, event: str, arg: Any) -> Any:
        if event == "call":
            # Keep tracing observational and bounded: only the audited runtime
            # frame needs line events. Returning the tracer for every imported
            # module makes startup prohibitively expensive without adding
            # signal-path evidence.
            return self if Path(frame.f_code.co_filename).resolve() == self.runtime_script else None
        if event == "line":
            if Path(frame.f_code.co_filename).resolve() != self.runtime_script:
                self.non_runtime_line_events += 1
                return None
            self.runtime_line_events += 1
            if frame.f_lineno in self.STEP_LINES:
                self._capture(frame, frame.f_lineno)
            return self
        return None


def _load_runtime_module(runtime_script: Path) -> Any:
    spec = importlib.util.spec_from_file_location("gate29_runtime_runner", runtime_script)
    if spec is None or spec.loader is None:
        raise Gate29Error(f"Cannot import runtime runner: {runtime_script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_trace_arrays(rows: Sequence[Mapping[str, Any]], output: Path) -> Path:
    if not rows:
        raise Gate29Error("Trace produced no per-step rows")
    output.mkdir(parents=True, exist_ok=True)
    arrays: dict[str, Any] = {
        "step_index": np.asarray([row["step_index"] for row in rows], dtype=np.int64),
        "pre_time_s": np.asarray([row["pre_time_s"] for row in rows], dtype=float),
        "post_time_s": np.asarray([row["post_time_s"] for row in rows], dtype=float),
        "dn_spikes": np.stack([row["dn_spikes"] for row in rows]),
        "decoder_rates_hz": np.stack([row["decoder_rates_hz"] for row in rows]),
        "brain_body_drive": np.stack([row["brain_body_drive"] for row in rows]),
        "controller_action_joint_angles": np.stack(
            [row["controller_action_joint_angles"] for row in rows]
        ),
        "controller_action_adhesion": np.stack(
            [row["controller_action_adhesion"] for row in rows]
        ),
        "applied_action_joint_angles": np.stack(
            [row["applied_action_joint_angles"] for row in rows]
        ),
        "applied_action_adhesion": np.stack([row["applied_action_adhesion"] for row in rows]),
        "post_joint_positions": np.stack([row["post_joint_positions"] for row in rows]),
        "post_joint_velocity": np.stack([row["post_joint_velocity"] for row in rows]),
        "post_actuator_position": np.stack([row["post_actuator_position"] for row in rows]),
        "post_contact_found": np.stack([row["post_contact_found"] for row in rows]),
        "post_thorax_position_mm": np.stack(
            [row["post_thorax_position_mm"] for row in rows]
        ),
        "controller_observation_thorax_z": np.asarray(
            [row["controller_observation_thorax_z"] for row in rows], dtype=float
        ),
        "controller_observation_tarsus5_z": np.stack(
            [row["controller_observation_tarsus5_z"] for row in rows]
        ),
        "controller_observation_stumbling_contact_forces": np.stack(
            [row["controller_observation_stumbling_contact_forces"] for row in rows]
        ),
        "controller_observation_fly_heading": np.stack(
            [row["controller_observation_fly_heading"] for row in rows]
        ),
    }
    path = output / "trace_arrays.npz"
    np.savez_compressed(path, **arrays)
    metadata = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "step_count": len(rows),
        "dn_order": rows[0].get("dn_names", []),
        "trace_arrays": sorted(arrays),
        "instrumentation": "READ_ONLY_SYS_TRACE_AROUND_AUDITED_RUNTIME_LINES",
        "biological_causality_established": False,
    }
    _write_json(output / "trace_metadata.json", metadata)
    return path


def _run_internal_trace(paths: Mapping[str, Path]) -> int:
    runtime_script = paths["runtime_root"] / "scripts/run_brain_body_rollout.py"
    module = _load_runtime_module(runtime_script)
    collector = _RuntimeTraceCollector(runtime_script)
    original_trace = sys.gettrace()
    sys.settrace(collector)
    try:
        module._run_simulation(
            root=paths["brain_root"],
            output=paths["output_root"],
            condition="healthy",
            seed=TECHNICAL_SEED,
            steps=TECHNICAL_STEPS,
            stimulus="p9",
            device="cuda",
            disease_config=ROOT / "configs/generation2/gate29_causal_trace_policy.yaml",
            artifact_profile="GATE24E_MEMORY_SAFE",
        )
    finally:
        sys.settrace(original_trace)
    path = _write_trace_arrays(collector.rows, paths["output_root"])
    print(json.dumps({"status": "TRACE_CAPTURE_PASS", "steps": len(collector.rows), "trace": str(path)}))
    return 0


def _prepare_commands(paths: Mapping[str, Path]) -> tuple[list[str], list[str]]:
    baseline_output = paths["output_root"] / "baseline"
    trace_output = paths["output_root"] / "trace"
    baseline_command = [
        str(paths["runtime_python"]),
        str(paths["runtime_root"] / "scripts/run_brain_body_rollout.py"),
        "--brain-root",
        str(paths["brain_root"]),
        "--condition",
        "healthy",
        "--seed",
        str(TECHNICAL_SEED),
        "--steps",
        str(TECHNICAL_STEPS),
        "--stimulus",
        "p9",
        "--device",
        "cuda",
        "--output",
        str(baseline_output),
        "--artifact-profile",
        "GATE24E_MEMORY_SAFE",
    ]
    trace_command = [
        str(paths["runtime_python"]),
        str(Path(__file__).resolve()),
        "--internal-trace",
        "--runtime-root",
        str(paths["runtime_root"]),
        "--brain-root",
        str(paths["brain_root"]),
        "--runtime-python",
        str(paths["runtime_python"]),
        "--output-root",
        str(trace_output),
    ]
    return baseline_command, trace_command


def _prepare_trace_only_command(paths: Mapping[str, Path], trace_output: Path) -> list[str]:
    """Build the single future trace command without a baseline command."""

    return [
        str(paths["runtime_python"]),
        str(Path(__file__).resolve()),
        "--internal-trace",
        "--runtime-root",
        str(paths["runtime_root"]),
        "--brain-root",
        str(paths["brain_root"]),
        "--runtime-python",
        str(paths["runtime_python"]),
        "--output-root",
        str(trace_output),
    ]


def qualify_tracer_scope() -> dict[str, Any]:
    """Qualify tracer scope with a deterministic non-GPU synthetic loop."""

    runtime_script = ROOT / "scripts/run_brain_body_rollout.py"
    collector = _RuntimeTraceCollector(runtime_script)

    def unrelated_nested_function(value: int) -> int:
        return value + 1

    namespace: dict[str, Any] = {"unrelated_nested_function": unrelated_nested_function}
    source = (
        "def synthetic_runtime_target():\n"
        "    total = 0\n"
        "    for value in range(25):\n"
        "        total += unrelated_nested_function(value)\n"
        "    return total\n"
    )
    exec(compile(source, str(runtime_script), "exec"), namespace)
    previous_trace = sys.gettrace()
    sys.settrace(collector)
    try:
        result = namespace["synthetic_runtime_target"]()
    finally:
        sys.settrace(previous_trace)
    passed = (
        result == sum(value + 1 for value in range(25))
        and collector.runtime_line_events > 0
        and collector.non_runtime_line_events == 0
    )
    payload = {
        "status": "PASS" if passed else "FAIL",
        "current_tracer_scope": "AUDITED_RUNTIME_SCRIPT_ONLY",
        "runtime_line_events": collector.runtime_line_events,
        "non_runtime_line_events": collector.non_runtime_line_events,
        "synthetic_result": result,
        "gpu_execution_in_qualification": False,
        "real_simulation_execution": False,
    }
    _write_json(TRACE_OPTIMIZATION_QUALIFICATION, {
        "schema_version": "gate29-trace-runner-optimization-qualification-v1",
        "previous_trace_execution": "ABORTED_STARTUP_OVERHEAD",
        "previous_trace_artifact_written": False,
        "current_tracer_scope": "AUDITED_RUNTIME_SCRIPT_ONLY",
        "non_runtime_line_events": collector.non_runtime_line_events,
        "synthetic_scope_test": "PASS" if passed else "FAIL",
        "gpu_execution_in_qualification": False,
        "real_simulation_execution": False,
        "status": "GATE29_TRACE_RUNNER_OPTIMIZATION_STATICALLY_QUALIFIED" if passed else "GATE29_TRACE_RUNNER_OPTIMIZATION_BLOCKED",
        "measurement": payload,
    })
    return payload


def _validate_trace_authorization(paths: Mapping[str, Path]) -> tuple[dict[str, Any], Path]:
    authorization = _json(TRACE_AUTHORIZATION)
    if (
        authorization.get("schema_version") != AUTHORIZATION_SCHEMA_VERSION
        or "authorized_head" in authorization
    ):
        raise Gate29Error("GATE29_TRACE_EXECUTION_AUTHORIZATION_SCHEMA_INVALID")
    if authorization.get("authorized") is not True:
        raise Gate29Error("GATE29_TRACE_EXECUTION_HUMAN_AUTHORIZATION_REQUIRED")
    authorization_commit = _validate_authorization_commit_structure(ROOT, authorization)
    if authorization.get("authorized_seed") != TECHNICAL_SEED:
        raise Gate29Error("GATE29_TRACE_EXECUTION_AUTHORIZATION_SEED_MISMATCH")
    if authorization.get("authorized_jobs") != 1 or authorization.get("trace_only") is not True:
        raise Gate29Error("GATE29_TRACE_EXECUTION_AUTHORIZATION_SCOPE_INVALID")
    baseline_lock = verify_baseline_execution_lock()
    if baseline_lock["status"] != "GATE29_BASELINE_EXECUTION_LOCK_PASS":
        raise Gate29Error(json.dumps(baseline_lock, sort_keys=True))
    trace_output = paths["output_root"] / "trace_attempt_02"
    if (paths["output_root"] / "trace" / "trace_arrays.npz").is_file():
        raise Gate29Error("GATE29_TRACE_ALREADY_EXECUTED")
    if _contains_files(trace_output) or trace_output.exists():
        raise Gate29Error("GATE29_TRACE_ATTEMPT_02_ALREADY_EXISTS")
    authorization["authorization_commit"] = authorization_commit["authorization_commit"]
    return authorization, trace_output


def execute_authorized_trace_only(paths: Mapping[str, Path]) -> dict[str, Any]:
    """Run exactly one future trace after an explicit human authorization."""

    authorization, trace_output = _validate_trace_authorization(paths)
    command = _prepare_trace_only_command(paths, trace_output)
    trace_output.parent.mkdir(parents=True, exist_ok=True)
    result = _run_guarded(command, paths["output_root"] / "logs/trace_attempt_02.log", paths)
    analysis_paths = dict(paths)
    analysis_paths["trace_root"] = trace_output
    summary = analyze_trace(analysis_paths)
    summary["trace_execution"] = result
    summary["trace_only"] = True
    summary["authorized_code_head"] = authorization["authorized_code_head"]
    summary["execution_head"] = authorization["authorization_commit"]
    _write_json(SUMMARY_PATH, summary)
    _update_gate29_manifest(summary, completed=2)
    write_reproducibility_inventory()
    return summary


def _preflight(paths: Mapping[str, Path]) -> dict[str, Any]:
    closure = audit_gate28b_closure()
    runtime = audit_runtime_contract(paths)
    try:
        gpu = _gpu_snapshot()
        gpu_status = "AVAILABLE"
    except (Gate29Error, OSError, ValueError, IndexError) as exc:
        gpu = {"error": str(exc)}
        gpu_status = "UNAVAILABLE"
    free_bytes = shutil.disk_usage(_existing_disk_path(paths["output_root"])).free
    estimated_output_bytes = 2 * 120 * 1024 * 1024
    trace_overhead_bytes = 120 * 1024 * 1024
    reserve_bytes = 5 * 1024**3
    required_free_bytes = estimated_output_bytes + trace_overhead_bytes + reserve_bytes
    blockers = [*closure["blockers"], *runtime["blockers"]]
    if gpu_status != "AVAILABLE":
        blockers.append("GPU telemetry unavailable")
    if free_bytes <= required_free_bytes:
        blockers.append("insufficient storage for two technical outputs and reserve")
    if paths["output_root"].exists() and any(paths["output_root"].iterdir()):
        blockers.append("technical output root is non-empty; no retry is allowed")
    return {
        "status": "GATE29_TECHNICAL_TRACE_PREFLIGHT_PASS" if not blockers else "GATE29_TECHNICAL_TRACE_PREFLIGHT_BLOCKED",
        "blockers": blockers,
        "condition": "healthy",
        "technical_seed": TECHNICAL_SEED,
        "technical_seed_scope": "GATE29_ENGINEERING_ONLY",
        "duration_s": TECHNICAL_DURATION_S,
        "steps": TECHNICAL_STEPS,
        "timestep_s": 0.0001,
        "maximum_jobs": MAX_TECHNICAL_JOBS,
        "automatic_retry": False,
        "disease_jobs": 0,
        "scientific_jobs": 0,
        "calibration_run": False,
        "model_fitting_run": False,
        "retuning": False,
        "closure": closure,
        "runtime": runtime,
        "gpu_status": gpu_status,
        "gpu": gpu,
        "storage": {
            "free_bytes": free_bytes,
            "estimated_output_bytes": estimated_output_bytes,
            "trace_overhead_bytes": trace_overhead_bytes,
            "conservative_reserve_bytes": reserve_bytes,
            "required_free_bytes": required_free_bytes,
        },
    }


def _load_trace_arrays(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        return {key: np.array(data[key], copy=True) for key in data.files}


def analyze_trace(paths: Mapping[str, Path]) -> dict[str, Any]:
    baseline = paths["output_root"] / "baseline" / "rollout.npz"
    trace_root = paths.get("trace_root", paths["output_root"] / "trace")
    trace_rollout = trace_root / "rollout.npz"
    trace_arrays_path = trace_root / "trace_arrays.npz"
    if not baseline.is_file() or not trace_rollout.is_file() or not trace_arrays_path.is_file():
        raise Gate29Error("baseline rollout, trace rollout, and trace_arrays.npz are required")
    baseline_arrays = _load_trace_arrays(baseline)
    trace_arrays = _load_trace_arrays(trace_arrays_path)
    baseline_aligned = {
        "timestamp_s": baseline_arrays["timestamp_s"][1:],
        "thorax": baseline_arrays["thorax_positions"][1:],
        "joint_positions": baseline_arrays["joint_positions"][1:],
        "actuator_position": baseline_arrays["actuator_position"][1:],
        "contact_found": baseline_arrays["contact_found"][1:],
    }
    comparison = compare_trace_arrays(
        baseline_aligned,
        trace_arrays,
        NONPERTURBATION_COMPARISONS,
    )
    _write_json(COMPARISON_PATH, comparison)
    steps = tuple(
        TraceStep(int(index), float(pre), float(post))
        for index, pre, post in zip(
            trace_arrays["step_index"], trace_arrays["pre_time_s"], trace_arrays["post_time_s"], strict=True
        )
    )
    validate_trace_steps(steps)
    summary = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "status": comparison["status"],
        "technical_seed": TECHNICAL_SEED,
        "technical_seed_scope": "GATE29_ENGINEERING_ONLY",
        "steps": len(steps),
        "duration_s": TECHNICAL_DURATION_S,
        "runtime_commit": RUNTIME_COMMIT,
        "healthy_checkpoint_sha256": HEALTHY_CHECKPOINT_SHA256,
        "baseline_rollout_sha256": _sha256(baseline),
        "trace_rollout_sha256": _sha256(trace_rollout),
        "raw_trace_sha256": _sha256(trace_arrays_path),
        "signal_summary": summarize_trace_arrays(trace_arrays),
        "nonperturbation_comparison": comparison,
        "edge_verification_summary": {
            "registered_edges": len(_json(EDGE_REGISTRY)["edges"]),
            "runtime_verified_edges": sum(
                bool(item["runtime_verified"]) for item in _json(EDGE_REGISTRY)["edges"]
            ),
            "biological_causal_edges_claimed": 0,
        },
        "scientific_jobs": 0,
        "disease_jobs": 0,
        "calibration_run": False,
        "model_fitting_run": False,
        "retuning": False,
        "paper_assay_equivalence_established": False,
        "biological_vnc_neural_model_status": "NOT_ESTABLISHED",
    }
    _write_json(SUMMARY_PATH, summary)
    return summary


def _update_gate29_manifest(summary: Mapping[str, Any], completed: int) -> None:
    manifest = _json(GATE29_MANIFEST)
    manifest["technical_jobs_completed"] = completed
    manifest["technical_trace_summary_status"] = summary.get("status")
    manifest["nonperturbation_status"] = summary.get("status")
    manifest["registered_edges"] = summary.get("edge_verification_summary", {}).get(
        "registered_edges", 0
    )
    manifest["status"] = (
        "GATE29_NEURAL_CAUSAL_TRACE_ENGINEERING_COMPLETE"
        if completed == MAX_TECHNICAL_JOBS and summary.get("status") == "TRACE_OBSERVATION_NONPERTURBING_PASS"
        else "GATE29_BLOCKED_TRACE_INSTRUMENTATION_PERTURBS_RUNTIME"
    )
    _write_json(GATE29_MANIFEST, manifest)


def execute_paired_trace(paths: Mapping[str, Path]) -> dict[str, Any]:
    preflight = _preflight(paths)
    if preflight["status"] != "GATE29_TECHNICAL_TRACE_PREFLIGHT_PASS":
        raise Gate29Error(json.dumps(preflight, sort_keys=True))
    baseline_command, trace_command = _prepare_commands(paths)
    paths["output_root"].mkdir(parents=True, exist_ok=False)
    baseline_result = _run_guarded(
        baseline_command, paths["output_root"] / "logs/baseline.log", paths
    )
    trace_result = _run_guarded(trace_command, paths["output_root"] / "logs/trace.log", paths)
    summary = analyze_trace(paths)
    summary["baseline_execution"] = baseline_result
    summary["trace_execution"] = trace_result
    _write_json(SUMMARY_PATH, summary)
    _update_gate29_manifest(summary, completed=2)
    inventory = write_reproducibility_inventory()
    reproducibility = verify_reproducibility_inventory()
    if reproducibility["status"] != "GATE29_REPRODUCIBILITY_PASS":
        raise Gate29Error(json.dumps(reproducibility, sort_keys=True))
    summary["reproducibility"] = {
        "file_count": inventory["file_count"],
        "status": reproducibility["status"],
    }
    _write_json(SUMMARY_PATH, summary)
    write_reproducibility_inventory()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def validate_fixtures() -> dict[str, Any]:
    steps = (TraceStep(0, 0.0, 0.0001), TraceStep(1, 0.0001, 0.0002))
    from drosophila_pd_neural.causal_trace import TraceEdge, validate_edge_registry
    from drosophila_pd_neural.causal_trace.types import DependencyClass

    validate_trace_steps(steps)
    validate_edge_registry(
        [
            TraceEdge(
                "FIXTURE_EDGE",
                "A",
                "x",
                "B",
                "y",
                DependencyClass.DIRECT_ARGUMENT_DEPENDENCY,
                "SOURCE_CODE",
                True,
            )
        ]
    )
    return {
        "status": "GATE29_TRACE_FIXTURES_PASS",
        "trace_atol": TRACE_ATOL,
        "trace_rtol": TRACE_RTOL,
        "discrete_keys": list(DISCRETE_TRACE_KEYS),
    }


def audit_only() -> dict[str, Any]:
    return {
        "status": "GATE29_STATIC_AUDIT_PASS",
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "gate28b": audit_gate28b_closure(),
        "runtime_execution_path": _json(RUNTIME_AUDIT),
        "signal_inventory": _json(SIGNAL_INVENTORY),
        "causal_edges": _json(EDGE_REGISTRY),
        "gate29_manifest": _json(GATE29_MANIFEST),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--audit-only", action="store_true")
    modes.add_argument("--validate-fixtures", action="store_true")
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--execute-paired-technical-trace", action="store_true")
    modes.add_argument("--execute-authorized-trace-only", action="store_true", help=argparse.SUPPRESS)
    modes.add_argument("--analyze-trace", action="store_true")
    modes.add_argument("--write-reproducibility", action="store_true")
    modes.add_argument("--verify-reproducibility", action="store_true")
    modes.add_argument("--validate-optimization", action="store_true")
    modes.add_argument("--internal-trace", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--runtime-root", type=Path, default=None)
    parser.add_argument("--brain-root", type=Path, default=None)
    parser.add_argument("--runtime-python", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    paths = _resolve_paths(args)
    if args.internal_trace:
        return _run_internal_trace(paths)
    if args.audit_only:
        print(json.dumps(audit_only(), indent=2, sort_keys=True))
        return 0
    if args.validate_fixtures:
        print(json.dumps(validate_fixtures(), indent=2, sort_keys=True))
        return 0
    if args.validate_optimization:
        print(json.dumps(qualify_tracer_scope(), indent=2, sort_keys=True))
        return 0
    if args.preflight:
        print(json.dumps(_preflight(paths), indent=2, sort_keys=True))
        return 0
    if args.analyze_trace:
        print(json.dumps(analyze_trace(paths), indent=2, sort_keys=True))
        return 0
    if args.write_reproducibility:
        print(json.dumps(write_reproducibility_inventory(), indent=2, sort_keys=True))
        return 0
    if args.verify_reproducibility:
        print(json.dumps(verify_reproducibility_inventory(), indent=2, sort_keys=True))
        return 0
    if args.execute_paired_technical_trace:
        execute_paired_trace(paths)
        return 0
    if args.execute_authorized_trace_only:
        print(json.dumps(execute_authorized_trace_only(paths), indent=2, sort_keys=True))
        return 0
    print(json.dumps({"status": "GATE29_NO_EXECUTION_DEFAULT", "gpu": False, "simulation": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
