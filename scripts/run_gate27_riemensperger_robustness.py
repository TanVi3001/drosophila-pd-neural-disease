"""Run the prospective Riemensperger 2011 burden robustness experiment.

Gate27 is a new sensitivity experiment. It never changes or rescues the
closed Gate26 NOT_REPRODUCED decision, and it never selects a best burden.
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
import statistics
import subprocess
import sys
from typing import Any, Iterable, Sequence

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.riemensperger2011.dopamine_transform import (
    apply_dopamine_class_presynaptic_transform,
    gain_at_burden,
)
from drosophila_pd_neural.riemensperger2011.metrics import rollout_seed_metrics


SOURCE_MAIN = "353ba33eb635138dcee5a65819e8f723d7448efc"
GATE26_FREEZE_SHA = "c4df44002e754f00717c9dc19079cca261e8f25e767612f08a5e3408fc5e779e"
GATE26_RESULT = "NOT_REPRODUCED"
HEALTHY_CHECKPOINT_SHA = "d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691"
RUNTIME_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"
RUNTIME_PROFILE = "GATE24E_MEMORY_SAFE"
RUNTIME_ROOT = Path(r"E:\Drosophila_Parkinson\drosophila-pd-flygym-gate24-memorysafe-clean")
BRAIN_ROOT = Path(r"E:\Drosophila_Parkinson\external\fly-brain-audit")
BRAIN_PYTHON = Path(r"E:\Drosophila_Parkinson\drosophila-pd-flygym\.venv\Scripts\python.exe")
RUNNER = ROOT / "scripts/run_neural_experiment.py"

BURDEN_GRID = (0.0, 0.25, 0.50, 0.75, 1.0)
REUSED_BURDENS = (0.0, 1.0)
NEW_BURDENS = (0.25, 0.50, 0.75)
EXPECTED_GAINS = {0.0: 1.0, 0.25: 0.7875, 0.50: 0.575, 0.75: 0.3625, 1.0: 0.15}
SEEDS = (0, 1, 2, 3, 4)
STEPS = 5000
TIMESTEP_S = 0.0001
VIRTUAL_DURATION_S = 0.5
STIMULUS = "p9"
CPG_HZ = 12.0
WORLD = "flat_terrain_default"
TARGET_COUNT = 342
MAX_NEW_SIMULATIONS = 15
PRIMARY_METRIC = "median_planar_speed_mm_s"
SECONDARY_METRIC = "distance_traveled_mm"
RAW_BYTES_PER_JOB_ESTIMATE = 600_000_000
CHECKPOINT_GRID_BYTES_ESTIMATE = 750_000_000
FREE_SPACE_RESERVE_BYTES = 4_000_000_000

GATE27 = ROOT / "experiments/gate_27_riemensperger_robustness"
MANIFESTS = GATE27 / "manifests"
RESULTS = GATE27 / "results"
METRICS = GATE27 / "metrics"
CHECKPOINTS = GATE27 / "checkpoint_materialization"
RUNS = GATE27 / "runs"
LOGS = GATE27 / "logs"
FREEZE = MANIFESTS / "gate27_execution_freeze.json"
PREFLIGHT = MANIFESTS / "gate27_preflight.json"
EXECUTION_STATE = MANIFESTS / "gate27_execution_state.json"
COMPLETION = MANIFESTS / "gate27_completion_manifest.json"
INVENTORY = MANIFESTS / "reproducibility_inventory.json"
CHECKSUMS = MANIFESTS / "checksums.sha256"
TRANSFORM_AUDIT = RESULTS / "gate27_transform_audit.json"
STORAGE_PREFLIGHT = RESULTS / "storage_preflight.json"
TELEMETRY = RESULTS / "gpu_telemetry.json"
GRID_METRICS = METRICS / "gate27_per_seed_grid.csv"
NEW_JOB_METRICS = METRICS / "gate27_new_job_metrics.csv"
GRID_SUMMARY = RESULTS / "gate27_grid_summary.json"
TRACE_DIAGNOSTIC = RESULTS / "downstream_trace_diagnostic.json"
REPORT = ROOT / "docs/replications/riemensperger_2011/gate27_robustness_report.md"
SIGNOFF = ROOT / "research/validation/prospective/gate27_riemensperger_robustness_reviewer_signoff.json"

GATE26_INVENTORY = ROOT / "experiments/gate_26_riemensperger_full_completion/manifests/reproducibility_inventory.json"
GATE26_CHECKSUMS = ROOT / "experiments/gate_26_riemensperger_full_completion/manifests/checksums.sha256"
GATE26_FREEZE = ROOT / "experiments/gate_26_riemensperger_full_completion/manifests/gate26_execution_freeze.json"
GATE26_COMPLETION = ROOT / "experiments/gate_26_riemensperger_full_completion/manifests/gate26_completion_manifest.json"
GATE26_SIGNOFF = ROOT / "research/validation/prospective/riemensperger_2011_final_reviewer_signoff.json"
HEALTHY_METRICS = ROOT / "experiments/gate_21b_riemensperger_healthy/metrics/healthy_per_seed_metrics.csv"
DISEASE_METRICS = ROOT / "experiments/gate_21e_riemensperger_disease/metrics/disease_per_seed_metrics.csv"
MAPPING_SUMMARY = ROOT / "experiments/gate_21d_riemensperger_dopamine_mapping/results/dopamine_mapping_summary.json"
MAPPING_SPEC = ROOT / "research/replications/riemensperger_2011/mapping/dopamine_mapping_spec.yaml"
TRANSFORM_SPEC = ROOT / "research/replications/riemensperger_2011/mapping/dopamine_transform_hypothesis.yaml"
CONDITION_CONFIG = ROOT / "configs/conditions/dopamine_deficiency.exploratory.yaml"

GRID_FIELDS = (
    "burden", "expected_gain", "seed", "source", "source_gate", "reused_existing_run",
    "status", "median_planar_speed_mm_s", "distance_traveled_mm", "delta_speed_vs_healthy",
    "speed_ratio_vs_healthy", "delta_distance_vs_healthy", "finite_qc", "timestamp_monotonic",
    "contact_detected", "checkpoint_tensor_sha256", "rollout_sha256", "source_artifact_reference",
)


class Gate27Error(RuntimeError):
    """Raised when a locked Gate27 condition is not satisfied."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tensor_sha256(values: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(values)
    return hashlib.sha256(contiguous.view(np.uint8)).hexdigest()


def canonical_sha(document: dict[str, Any]) -> str:
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Gate27Error(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{str(key): str(value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fields: Iterable[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode:
        raise Gate27Error(result.stderr.strip() or f"git command failed: {args}")
    return result.stdout.strip()


def expected_gain(burden: float) -> float:
    value = float(burden)
    if value not in EXPECTED_GAINS:
        raise Gate27Error(f"Burden is outside the frozen grid: {value}")
    result = gain_at_burden(value, full_presynaptic_gain=0.15)
    if not math.isclose(result, EXPECTED_GAINS[value], rel_tol=0.0, abs_tol=1e-12):
        raise Gate27Error(f"Gain contract mismatch at burden {value}: {result}")
    return EXPECTED_GAINS[value]


def build_job_plan() -> list[dict[str, Any]]:
    return [
        {"burden": burden, "seed": seed, "expected_gain": expected_gain(burden)}
        for burden in NEW_BURDENS
        for seed in SEEDS
    ]


def _historical_eol_candidates(path: Path) -> list[tuple[str, bytes]]:
    """Return exact byte candidates for Gate26's pre-commit Windows hashes.

    Gate26 recorded working-tree SHA256 values before Git normalized tracked
    text to LF. The immutable manifest therefore contains either CRLF bytes or
    CRLF bytes with a final LF. Reconstructing those serializations from the
    committed blob validates the historical digest without altering Gate26.
    """

    relative = path.relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "show", f"{SOURCE_MAIN}:{relative}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return []
    blob = result.stdout
    normalized = blob.replace(b"\r\n", b"\n")
    crlf = normalized.replace(b"\n", b"\r\n")
    candidates = [("git_blob_exact", blob), ("historical_crlf", crlf)]
    if normalized.endswith(b"\n"):
        candidates.append(("historical_crlf_terminal_lf", crlf[:-2] + b"\n"))
    return candidates


def _portable_text_candidates(path: Path) -> list[bytes]:
    """Accept exact bytes plus the recorded LF/CRLF text serializations."""

    payload = path.read_bytes()
    normalized = payload.replace(b"\r\n", b"\n")
    crlf = normalized.replace(b"\n", b"\r\n")
    candidates = [payload, normalized, crlf]
    if normalized.endswith(b"\n"):
        candidates.append(crlf[:-2] + b"\n")
    return candidates


def verify_gate26_inventory() -> dict[str, Any]:
    inventory = read_json(GATE26_INVENTORY)
    records = inventory.get("records", [])
    if inventory.get("status") != "COMPLETE" or inventory.get("record_count") != 37 or len(records) != 37:
        raise Gate27Error("Gate26 reproducibility inventory is not the approved 37-record closure.")
    bad: list[str] = []
    verification_modes: dict[str, int] = {}
    expected: dict[str, str] = {}
    for record in records:
        path = ROOT / str(record["path"])
        expected[str(record["path"])] = str(record["sha256"])
        matched_mode = ""
        if path.is_file() and sha256_file(path) == record["sha256"] and path.stat().st_size == record["size_bytes"]:
            matched_mode = "working_tree_exact"
        elif path.is_file():
            for mode, payload in _historical_eol_candidates(path):
                if len(payload) == record["size_bytes"] and hashlib.sha256(payload).hexdigest() == record["sha256"]:
                    matched_mode = mode
                    break
        if not matched_mode:
            bad.append(str(record["path"]))
        else:
            verification_modes[matched_mode] = verification_modes.get(matched_mode, 0) + 1
    checksum_rows: dict[str, str] = {}
    for line in GATE26_CHECKSUMS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, relative = line.split(maxsplit=1)
            if relative in checksum_rows:
                raise Gate27Error(f"Duplicate Gate26 checksum path: {relative}")
            checksum_rows[relative] = digest
    if bad or checksum_rows != expected:
        raise Gate27Error(f"Gate26 checksum verification failed: {bad}")
    freeze = read_json(GATE26_FREEZE)
    completion = read_json(GATE26_COMPLETION)
    signoff = read_json(GATE26_SIGNOFF)
    if freeze.get("gate26_execution_freeze_sha256") != GATE26_FREEZE_SHA:
        raise Gate27Error("Gate26 execution freeze changed.")
    if completion.get("final_directional_decision") != GATE26_RESULT:
        raise Gate27Error("Gate26 final result changed.")
    if completion.get("healthy_seeds_passed") != 5 or completion.get("disease_seeds_passed") != 5:
        raise Gate27Error("Gate26 endpoints are incomplete.")
    if signoff.get("status") != "RIEMENSPERGER_FINAL_REVIEW_APPROVED" or not signoff.get("gate26_closed"):
        raise Gate27Error("Gate26 final human signoff is not closed.")
    return {
        "verified": 37,
        "total": 37,
        "verification_modes": verification_modes,
        "historical_eol_note": "Gate26 Windows working-tree hashes are validated against exact deterministic EOL serializations of committed Git blobs; Gate26 files are not modified.",
        "freeze": freeze,
        "completion_manifest_sha256": sha256_file(GATE26_COMPLETION),
        "result": GATE26_RESULT,
    }


def verify_source_state() -> dict[str, Any]:
    origin_main = git("rev-parse", "origin/main")
    if origin_main != SOURCE_MAIN:
        raise Gate27Error(f"origin/main changed: {origin_main}")
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", SOURCE_MAIN, "HEAD"], cwd=ROOT, check=False)
    if ancestor.returncode:
        raise Gate27Error("Gate27 branch is not descended from the approved source main.")
    branch = git("branch", "--show-current")
    if branch != "research/gate27-riemensperger-robustness":
        raise Gate27Error(f"Unexpected branch: {branch}")
    return {"source_main": SOURCE_MAIN, "origin_main": origin_main, "branch": branch}


def verify_runtime_and_brain() -> dict[str, Any]:
    if not RUNTIME_ROOT.is_dir() or not BRAIN_ROOT.is_dir() or not BRAIN_PYTHON.is_file():
        raise Gate27Error("Approved runtime, brain root, or Python is missing.")
    if git("rev-parse", "HEAD", cwd=RUNTIME_ROOT) != RUNTIME_COMMIT:
        raise Gate27Error("Approved runtime commit changed.")
    if git("status", "--porcelain", cwd=RUNTIME_ROOT):
        raise Gate27Error("Approved runtime worktree is dirty.")
    required = (
        "brain_body_bridge.py", "code/run_pytorch.py", "code/benchmark.py",
        "data/2025_Completeness_783.csv", "data/2025_Connectivity_783.parquet", "data/plastic_weights.pt",
    )
    missing = [relative for relative in required if not (BRAIN_ROOT / relative).is_file()]
    if missing:
        raise Gate27Error(f"Brain source is incomplete: {missing}")
    checkpoint = BRAIN_ROOT / "data/plastic_weights.pt"
    if sha256_file(checkpoint) != HEALTHY_CHECKPOINT_SHA:
        raise Gate27Error("Healthy checkpoint SHA256 changed.")
    version = subprocess.run(
        [str(BRAIN_PYTHON), "-c", "from importlib.metadata import version; print(version('flygym'))"],
        capture_output=True, text=True, check=False,
    )
    cuda = subprocess.run(
        [str(BRAIN_PYTHON), "-c", "import torch; print(torch.cuda.is_available())"],
        capture_output=True, text=True, check=False,
    )
    if version.returncode or version.stdout.strip() != "2.1.0":
        raise Gate27Error(f"FlyGym runtime mismatch: {version.stdout.strip() or version.stderr.strip()}")
    if cuda.returncode or cuda.stdout.strip() != "True":
        raise Gate27Error("CUDA is unavailable in the approved Python runtime.")
    return {
        "runtime_commit": RUNTIME_COMMIT,
        "runtime_profile": RUNTIME_PROFILE,
        "flygym_version": "2.1.0",
        "brain_checkpoint_sha256": HEALTHY_CHECKPOINT_SHA,
        "cuda_available": True,
    }


def verify_mapping() -> dict[str, Any]:
    mapping = read_json(MAPPING_SUMMARY)
    if (
        mapping.get("status") != "READY_FOR_RIEMENSPERGER_DISEASE_REPLICATION"
        or mapping.get("mapping_level") != "DOPAMINE_CLASS_LEVEL_EXPLORATORY"
        or mapping.get("target_count") != TARGET_COUNT
        or mapping.get("gene_specific_mapping") is not False
    ):
        raise Gate27Error("The reviewed dopamine-class mapping changed.")
    return {
        "mapping_sha256": sha256_file(MAPPING_SUMMARY),
        "mapping_spec_sha256": sha256_file(MAPPING_SPEC),
        "transform_sha256": sha256_file(TRANSFORM_SPEC),
        "mapping_level": mapping["mapping_level"],
        "target_count": mapping["target_count"],
    }


def verify_endpoint_reuse(gate26: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    freeze = gate26["freeze"]
    expected_fields = {
        "seeds": list(SEEDS), "steps": STEPS, "timestep_s": TIMESTEP_S,
        "stimulus": STIMULUS, "cpg_frequency_hz": CPG_HZ, "world": WORLD,
        "runtime_commit": RUNTIME_COMMIT, "runtime_profile": RUNTIME_PROFILE,
        "healthy_checkpoint_sha256": HEALTHY_CHECKPOINT_SHA,
        "mapping_target_count": TARGET_COUNT,
        "transform_hypothesis_sha256": mapping["transform_sha256"],
    }
    mismatches = {key: {"expected": value, "actual": freeze.get(key)} for key, value in expected_fields.items() if freeze.get(key) != value}
    if mismatches:
        raise Gate27Error(f"GATE27_ENDPOINT_REUSE_NOT_VALID: {mismatches}")
    healthy = read_csv(HEALTHY_METRICS)
    disease = read_csv(DISEASE_METRICS)
    if len(healthy) != 5 or len(disease) != 5:
        raise Gate27Error("GATE27_ENDPOINT_REUSE_NOT_VALID: expected five rows per endpoint.")
    if {int(row["seed"]) for row in healthy} != set(SEEDS) or {int(row["seed"]) for row in disease} != set(SEEDS):
        raise Gate27Error("GATE27_ENDPOINT_REUSE_NOT_VALID: seed mismatch.")
    if any(row["status"] != "PASS" for row in healthy + disease):
        raise Gate27Error("GATE27_ENDPOINT_REUSE_NOT_VALID: endpoint QC failed.")
    if any(float(row["burden"]) != 1.0 for row in disease):
        raise Gate27Error("GATE27_ENDPOINT_REUSE_NOT_VALID: disease burden mismatch.")
    return {
        "status": "GATE27_ENDPOINT_REUSE_VALID",
        "reused_simulations": 10,
        "burden_0_source": HEALTHY_METRICS.relative_to(ROOT).as_posix(),
        "burden_1_source": DISEASE_METRICS.relative_to(ROOT).as_posix(),
        "raw_rollouts_required_for_metric_reuse": False,
    }


def _gpu_telemetry() -> dict[str, Any]:
    command = ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.free", "--format=csv,noheader,nounits"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return {"available": False, "note": "nvidia-smi unavailable"}
    if result.returncode or not result.stdout.strip():
        return {"available": False, "note": "nvidia-smi unavailable"}
    fields = [value.strip() for value in result.stdout.splitlines()[0].split(",")]
    try:
        telemetry = {
            "available": True,
            "temperature_c": float(fields[0]),
            "utilization_percent": float(fields[1]),
            "memory_used_mib": float(fields[2]),
            "memory_free_mib": float(fields[3]),
        }
    except (IndexError, ValueError) as exc:
        raise Gate27Error(f"Could not parse GPU telemetry: {exc}") from exc
    if telemetry["temperature_c"] >= 82.0:
        raise Gate27Error(f"GPU temperature reached safety limit: {telemetry['temperature_c']} C")
    return telemetry


def _assert_gpu_idle() -> dict[str, Any]:
    telemetry = _gpu_telemetry()
    command = ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return telemetry
    active: list[str] = []
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            fields = [value.strip() for value in line.split(",")]
            if len(fields) != 2 or fields[1].upper() in {"N/A", "[N/A]"}:
                continue
            try:
                if float(fields[1]) > 0.0:
                    active.append(line.strip())
            except ValueError:
                continue
    if active:
        raise Gate27Error(f"GPU has a pre-existing compute workload: {active}")
    if telemetry.get("available") and float(telemetry["utilization_percent"]) >= 80.0:
        raise Gate27Error(f"GPU utilization indicates another heavy workload: {telemetry['utilization_percent']}%")
    return telemetry


def storage_preflight() -> dict[str, Any]:
    usage = shutil.disk_usage(GATE27.parent)
    expected_raw = RAW_BYTES_PER_JOB_ESTIMATE * MAX_NEW_SIMULATIONS
    required = expected_raw + CHECKPOINT_GRID_BYTES_ESTIMATE + FREE_SPACE_RESERVE_BYTES
    result = {
        "schema_version": "gate27-storage-preflight-v1",
        "status": "PASS" if usage.free > required else "WAITING_GATE27_STORAGE_CAPACITY",
        "free_bytes": usage.free,
        "expected_raw_bytes": expected_raw,
        "checkpoint_grid_bytes_estimate": CHECKPOINT_GRID_BYTES_ESTIMATE,
        "reserve_bytes": FREE_SPACE_RESERVE_BYTES,
        "required_bytes": required,
        "strict_capacity_rule": "free_bytes > required_bytes",
        "gate24e_archive_copied": False,
        "gate26_raw_duplicated": False,
    }
    write_json(STORAGE_PREFLIGHT, result)
    if result["status"] != "PASS":
        raise Gate27Error(f"Insufficient storage: {usage.free} <= {required}")
    return result


def materialize_transform_grid() -> dict[str, Any]:
    from scripts.prepare_neural_checkpoint import _checkpoint_tensor, _load_torch, _numeric_edges

    config = yaml.safe_load(CONDITION_CONFIG.read_text(encoding="utf-8")) or {}
    target_ids = [str(value) for value in config.get("target_neurons", [])]
    if len(target_ids) != TARGET_COUNT or len(set(target_ids)) != TARGET_COUNT:
        raise Gate27Error("Target set is not the frozen 342-ID mapping.")
    full_gain = float((config.get("full_burden") or {}).get("presynaptic_gain", -1.0))
    if full_gain != 0.15:
        raise Gate27Error(f"Full-burden gain changed: {full_gain}")
    torch = _load_torch()
    edges = _numeric_edges(BRAIN_ROOT)
    parent_path = BRAIN_ROOT / "data/plastic_weights.pt"
    parent_file_before = sha256_file(parent_path)
    parent_tensor = _checkpoint_tensor(torch, parent_path)
    parent = np.asarray(parent_tensor.numpy())
    if parent.size != len(edges["Presynaptic_Index"]):
        raise Gate27Error("Checkpoint length does not match connectome edge count.")
    root_ids = edges["root_ids"]
    presynaptic_ids = root_ids[edges["Presynaptic_Index"]]
    target_mask = np.isin(presynaptic_ids, target_ids)
    targeted_count = int(np.count_nonzero(target_mask))
    if targeted_count <= 0:
        raise Gate27Error("Reviewed targets have no outgoing connectome edges.")
    parent_tensor_hash = tensor_sha256(parent)
    records: list[dict[str, Any]] = []
    for burden in BURDEN_GRID:
        gain = expected_gain(burden)
        # This is the exact reviewed operator, applied directly to the full
        # NumPy tensor to avoid constructing a 15-million-element Python list.
        transformed = parent.copy()
        if burden > 0.0:
            transformed[target_mask] *= gain
        delta = np.abs(transformed.astype(np.float64) - parent.astype(np.float64))
        changed = int(np.count_nonzero(transformed != parent))
        nontarget_unchanged = bool(np.array_equal(transformed[~target_mask], parent[~target_mask]))
        target_scaling_valid = bool(np.allclose(
            transformed[target_mask], parent[target_mask] * gain, rtol=1e-6, atol=1e-7,
        ))
        identity = bool(np.array_equal(transformed, parent))
        if burden == 0.0 and (not identity or float(delta.max(initial=0.0)) != 0.0):
            raise Gate27Error("Burden 0 checkpoint is not tensor-identical to healthy.")
        if burden > 0.0 and (changed <= 0 or not target_scaling_valid or not nontarget_unchanged):
            raise Gate27Error(f"Transform audit failed at burden {burden}.")
        burden_key = f"burden_{int(round(burden * 100)):03d}"
        output = CHECKPOINTS / burden_key
        output.mkdir(parents=True, exist_ok=True)
        child_path = output / "plastic_weights.pt"
        torch.save(torch.as_tensor(transformed, dtype=parent_tensor.dtype), child_path)
        record = {
            "burden": burden,
            "expected_gain": gain,
            "target_count": TARGET_COUNT,
            "number_of_targeted_outgoing_edges": targeted_count,
            "number_of_changed_edges": changed,
            "parent_tensor_sha256": parent_tensor_hash,
            "child_tensor_sha256": tensor_sha256(transformed),
            "parent_checkpoint_file_sha256": parent_file_before,
            "child_checkpoint_file_sha256": sha256_file(child_path),
            "checkpoint_reference": child_path.relative_to(ROOT).as_posix(),
            "max_abs_weight_delta": float(delta.max(initial=0.0)),
            "mean_abs_weight_delta": float(delta.mean()),
            "l1_weight_delta": float(delta.sum()),
            "finite_values": bool(np.isfinite(transformed).all()),
            "healthy_parent_unchanged": sha256_file(parent_path) == parent_file_before,
            "tensor_identity_with_healthy": identity,
            "target_scaling_valid": target_scaling_valid,
            "nontarget_weights_unchanged": nontarget_unchanged,
        }
        write_json(output / "transform_audit.json", record)
        records.append(record)
        del transformed, delta
    parent_file_after = sha256_file(parent_path)
    result = {
        "schema_version": "gate27-transform-grid-audit-v1",
        "status": "PASS",
        "operator": "presynaptic_connectome_weight_gain",
        "burden_grid": list(BURDEN_GRID),
        "target_count": TARGET_COUNT,
        "number_of_targeted_outgoing_edges": targeted_count,
        "parent_checkpoint_sha256_before": parent_file_before,
        "parent_checkpoint_sha256_after": parent_file_after,
        "healthy_parent_unchanged": parent_file_before == parent_file_after == HEALTHY_CHECKPOINT_SHA,
        "records": records,
    }
    if not result["healthy_parent_unchanged"]:
        raise Gate27Error("Healthy checkpoint changed during materialization.")
    write_json(TRANSFORM_AUDIT, result)
    return result


def build_freeze(
    gate26: dict[str, Any], runtime: dict[str, Any], mapping: dict[str, Any], reuse: dict[str, Any],
    transform: dict[str, Any], storage: dict[str, Any],
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": "gate27-riemensperger-robustness-freeze-v1",
        "status": "GATE27_SCIENTIFIC_EXECUTION_FROZEN",
        "source_main_commit": SOURCE_MAIN,
        "gate26_execution_freeze_sha256": GATE26_FREEZE_SHA,
        "gate26_completion_manifest_sha256": gate26["completion_manifest_sha256"],
        "gate26_result": GATE26_RESULT,
        "gate26_changed": False,
        "mapping_sha256": mapping["mapping_sha256"],
        "mapping_spec_sha256": mapping["mapping_spec_sha256"],
        "mapping_level": mapping["mapping_level"],
        "target_count": TARGET_COUNT,
        "transform_sha256": mapping["transform_sha256"],
        "transform_audit_sha256": sha256_file(TRANSFORM_AUDIT),
        "brain_checkpoint_sha256": HEALTHY_CHECKPOINT_SHA,
        "runtime_commit": runtime["runtime_commit"],
        "runtime_profile": runtime["runtime_profile"],
        "burden_grid": list(BURDEN_GRID),
        "expected_gains": {str(key): value for key, value in EXPECTED_GAINS.items()},
        "reused_burdens": list(REUSED_BURDENS),
        "new_burdens": list(NEW_BURDENS),
        "seeds": list(SEEDS),
        "steps": STEPS,
        "virtual_duration_s": VIRTUAL_DURATION_S,
        "timestep_s": TIMESTEP_S,
        "stimulus": STIMULUS,
        "cpg_frequency_hz": CPG_HZ,
        "world": WORLD,
        "controller": "same frozen Gate26 controller for every burden",
        "primary_metric": PRIMARY_METRIC,
        "secondary_metric": SECONDARY_METRIC,
        "statistical_unit": "independent_seed",
        "paired_comparison_rule": "delta_speed(b,s)=speed(b,s)-speed(0,s)",
        "primary_direction_rule": "median_paired_delta_speed < 0",
        "monotonicity_rule": "M0 >= M025 >= M050 >= M075 >= M100 and every nonzero median paired delta speed < 0",
        "classification_rules": {
            "ROBUSTNESS_MONOTONIC_IMPAIRMENT_PATTERN": "all nonzero direction pass and non-increasing median speed",
            "ROBUSTNESS_MIXED_DIRECTIONAL_RESPONSE": "at least one nonzero direction pass but monotonic rule fails",
            "ROBUSTNESS_NO_IMPAIRMENT_ACROSS_GRID": "no nonzero direction passes",
            "ROBUSTNESS_INCOMPLETE_TECHNICAL_EXECUTION": "any required job missing/failed or endpoint reuse invalid",
        },
        "no_retuning": True,
        "calibration": False,
        "parameter_optimization": False,
        "paper_ratio_optimization": False,
        "best_burden_selection": False,
        "new_simulation_count": MAX_NEW_SIMULATIONS,
        "endpoint_reuse_policy": reuse,
        "storage_preflight": storage,
        "data_fabricated": False,
    }
    document["gate27_execution_freeze_sha256"] = canonical_sha(document)
    return document


def verify_frozen_transform() -> dict[str, Any]:
    audit = read_json(TRANSFORM_AUDIT)
    if audit.get("status") != "PASS" or audit.get("target_count") != TARGET_COUNT:
        raise Gate27Error("Transform audit is unavailable or invalid.")
    records = {float(record["burden"]): record for record in audit.get("records", [])}
    if set(records) != set(BURDEN_GRID):
        raise Gate27Error("Transform audit burden grid changed.")
    for burden, record in records.items():
        child = ROOT / record["checkpoint_reference"]
        if not child.is_file() or sha256_file(child) != record["child_checkpoint_file_sha256"]:
            raise Gate27Error(f"Checkpoint artifact is missing or stale at burden {burden}.")
        if burden == 0.0 and not record["tensor_identity_with_healthy"]:
            raise Gate27Error("Burden 0 identity audit failed.")
        if burden > 0.0 and int(record["number_of_changed_edges"]) <= 0:
            raise Gate27Error(f"No targeted edge changed at burden {burden}.")
    return audit


def preflight() -> dict[str, Any]:
    source = verify_source_state()
    gate26 = verify_gate26_inventory()
    runtime = verify_runtime_and_brain()
    mapping = verify_mapping()
    reuse = verify_endpoint_reuse(gate26, mapping)
    storage = storage_preflight()
    idle = _assert_gpu_idle()
    transform = materialize_transform_grid()
    freeze = build_freeze(gate26, runtime, mapping, reuse, transform, storage)
    if FREEZE.is_file() and read_json(FREEZE) != freeze:
        raise Gate27Error("Existing Gate27 freeze differs from the frozen scientific contract.")
    write_json(FREEZE, freeze)
    result = {
        "schema_version": "gate27-preflight-v1",
        "status": "GATE27_ROBUSTNESS_PREFLIGHT_PASS",
        "source": source,
        "gate26_checksum_verification": {"passed": 37, "total": 37},
        "gate26_result": GATE26_RESULT,
        "endpoint_reuse": reuse,
        "runtime": runtime,
        "mapping": mapping,
        "transform_audit_status": transform["status"],
        "storage": storage,
        "gpu_idle_telemetry": idle,
        "new_simulations_authorized": MAX_NEW_SIMULATIONS,
        "simulation_executed": False,
        "data_fabricated": False,
    }
    write_json(PREFLIGHT, result)
    return result


def verify_freeze() -> dict[str, Any]:
    freeze = read_json(FREEZE)
    stored = freeze.get("gate27_execution_freeze_sha256")
    body = dict(freeze)
    body.pop("gate27_execution_freeze_sha256", None)
    if freeze.get("status") != "GATE27_SCIENTIFIC_EXECUTION_FROZEN" or stored != canonical_sha(body):
        raise Gate27Error("Gate27 execution freeze integrity failed.")
    if freeze.get("source_main_commit") != SOURCE_MAIN or freeze.get("gate26_result") != GATE26_RESULT:
        raise Gate27Error("Gate27 execution freeze source changed.")
    return freeze


def _job_output(burden: float, seed: int) -> Path:
    return RUNS / f"burden_{int(round(burden * 100)):03d}" / f"seed_{seed:03d}"


def _checkpoint_record(transform: dict[str, Any], burden: float) -> dict[str, Any]:
    return next(record for record in transform["records"] if float(record["burden"]) == burden)


def _new_metric_row(burden: float, seed: int, metrics: dict[str, Any], rollout: Path, checkpoint: dict[str, Any]) -> dict[str, Any]:
    return {
        "burden": burden,
        "expected_gain": expected_gain(burden),
        "seed": seed,
        "status": "PASS",
        "median_planar_speed_mm_s": metrics[PRIMARY_METRIC],
        "distance_traveled_mm": metrics[SECONDARY_METRIC],
        "finite_qc": metrics["finite_qc"],
        "timestamp_monotonic": metrics["timestamp_monotonic"],
        "contact_detected": metrics["contact_detected"],
        "joint_trajectory_max_delta": metrics["joint_trajectory_max_delta"],
        "action_trajectory_max_delta": metrics["action_trajectory_max_delta"],
        "checkpoint_tensor_sha256": checkpoint["child_tensor_sha256"],
        "checkpoint_file_sha256": checkpoint["child_checkpoint_file_sha256"],
        "rollout_sha256": sha256_file(rollout),
        "source_artifact_reference": rollout.relative_to(ROOT).as_posix(),
    }


def execute() -> dict[str, Any]:
    if not PREFLIGHT.is_file() or read_json(PREFLIGHT).get("status") != "GATE27_ROBUSTNESS_PREFLIGHT_PASS":
        raise Gate27Error("Run Gate27 --preflight successfully before --execute.")
    verify_source_state()
    verify_gate26_inventory()
    verify_runtime_and_brain()
    freeze = verify_freeze()
    transform = verify_frozen_transform()
    plan = build_job_plan()
    if len(plan) != MAX_NEW_SIMULATIONS:
        raise Gate27Error("The frozen plan is not exactly 15 jobs.")
    if EXECUTION_STATE.exists():
        existing = read_json(EXECUTION_STATE)
        if int(existing.get("simulation_jobs_started", 0)) > 0:
            raise Gate27Error("Gate27 scientific execution already started; automatic retry is forbidden.")
    for job in plan:
        output = _job_output(job["burden"], job["seed"])
        if output.exists() and any(output.iterdir()):
            raise Gate27Error(f"Existing job artifacts forbid retry: {output}")
    state: dict[str, Any] = {
        "schema_version": "gate27-execution-state-v1",
        "status": "GATE27_EXECUTION_IN_PROGRESS",
        "gate27_execution_freeze_sha256": freeze["gate27_execution_freeze_sha256"],
        "simulation_jobs_authorized": MAX_NEW_SIMULATIONS,
        "simulation_jobs_started": 0,
        "simulation_jobs_completed": 0,
        "retry_count": 0,
        "seed_replacement": False,
        "jobs": [],
        "started_at_utc": datetime.now(UTC).isoformat(),
    }
    write_json(EXECUTION_STATE, state)
    telemetry_records: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    for index, job in enumerate(plan, start=1):
        burden = float(job["burden"])
        seed = int(job["seed"])
        remaining_including_current = MAX_NEW_SIMULATIONS - (index - 1)
        free = shutil.disk_usage(GATE27.parent).free
        required_remaining = remaining_including_current * RAW_BYTES_PER_JOB_ESTIMATE + FREE_SPACE_RESERVE_BYTES
        if free <= required_remaining:
            state["status"] = "ROBUSTNESS_INCOMPLETE_TECHNICAL_EXECUTION"
            state["blocker"] = f"storage_before_job_{index}:{free}<={required_remaining}"
            write_json(EXECUTION_STATE, state)
            raise Gate27Error(state["blocker"])
        before = _assert_gpu_idle()
        checkpoint = _checkpoint_record(transform, burden)
        checkpoint_path = ROOT / checkpoint["checkpoint_reference"]
        output = _job_output(burden, seed)
        command = [
            str(sys.executable), str(RUNNER),
            "--brain-root", str(BRAIN_ROOT),
            "--platform-root", str(RUNTIME_ROOT),
            "--brain-python", str(BRAIN_PYTHON),
            "--prepared-checkpoint", str(checkpoint_path),
            "--seed", str(seed),
            "--steps", str(STEPS),
            "--device", "cuda",
            "--output", str(output),
            "--stimulus", STIMULUS,
            "--cpg-frequency-hz", str(CPG_HZ),
            "--artifact-profile", RUNTIME_PROFILE,
        ]
        state["simulation_jobs_started"] = index
        job_state = {"index": index, "burden": burden, "seed": seed, "status": "STARTED"}
        state["jobs"].append(job_state)
        write_json(EXECUTION_STATE, state)
        print(f"[{index}/{MAX_NEW_SIMULATIONS}] burden={burden:.2f} seed={seed} starting", flush=True)
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        after = _gpu_telemetry()
        LOGS.mkdir(parents=True, exist_ok=True)
        (LOGS / f"burden_{int(round(burden * 100)):03d}_seed_{seed:03d}.log").write_text(
            result.stdout + result.stderr, encoding="utf-8",
        )
        telemetry_records.append({"index": index, "burden": burden, "seed": seed, "before": before, "after": after})
        write_json(TELEMETRY, {"schema_version": "gate27-gpu-telemetry-v1", "records": telemetry_records})
        rollout = output / "rollout.npz"
        if result.returncode != 0 or not rollout.is_file():
            job_state.update({"status": "FAILED", "return_code": result.returncode})
            state["status"] = "ROBUSTNESS_INCOMPLETE_TECHNICAL_EXECUTION"
            state["failed_job"] = job_state
            write_json(EXECUTION_STATE, state)
            raise Gate27Error(f"Scientific job failed without retry: burden={burden}, seed={seed}, return_code={result.returncode}")
        metrics = rollout_seed_metrics(rollout)
        if (
            not metrics["finite_qc"] or not metrics["timestamp_monotonic"] or not metrics["contact_detected"]
            or float(metrics["joint_trajectory_max_delta"]) <= 0.0
            or float(metrics["action_trajectory_max_delta"]) <= 0.0
        ):
            job_state.update({"status": "FAILED_QC"})
            state["status"] = "ROBUSTNESS_INCOMPLETE_TECHNICAL_EXECUTION"
            state["failed_job"] = job_state
            write_json(EXECUTION_STATE, state)
            raise Gate27Error(f"Scientific job failed QC without retry: burden={burden}, seed={seed}")
        row = _new_metric_row(burden, seed, metrics, rollout, checkpoint)
        metric_rows.append(row)
        write_csv(NEW_JOB_METRICS, row.keys(), metric_rows)
        job_state.update({"status": "PASS", "rollout_sha256": row["rollout_sha256"]})
        state["simulation_jobs_completed"] = index
        write_json(EXECUTION_STATE, state)
        print(f"[{index}/{MAX_NEW_SIMULATIONS}] burden={burden:.2f} seed={seed} PASS", flush=True)
    state["status"] = "GATE27_NEW_SIMULATIONS_PASS"
    state["completed_at_utc"] = datetime.now(UTC).isoformat()
    write_json(EXECUTION_STATE, state)
    return analyze_existing()


def _bool(value: str) -> bool:
    return value.strip().lower() == "true"


def _load_endpoint_rows(path: Path, burden: float, source_gate: str) -> list[dict[str, Any]]:
    rows = []
    for source in read_csv(path):
        rows.append({
            "burden": burden,
            "expected_gain": expected_gain(burden),
            "seed": int(source["seed"]),
            "source": "GATE26_REUSED",
            "source_gate": source_gate,
            "reused_existing_run": True,
            "status": source["status"],
            PRIMARY_METRIC: float(source[PRIMARY_METRIC]),
            SECONDARY_METRIC: float(source[SECONDARY_METRIC]),
            "finite_qc": _bool(source["finite_qc"]),
            "timestamp_monotonic": _bool(source["timestamp_monotonic"]),
            "contact_detected": _bool(source["contact_detected"]),
            "rollout_sha256": "",
            "source_artifact_reference": path.relative_to(ROOT).as_posix(),
        })
    return rows


def classify_robustness(direction_passes: dict[float, bool], monotonic: bool, *, complete: bool = True) -> str:
    if not complete:
        return "ROBUSTNESS_INCOMPLETE_TECHNICAL_EXECUTION"
    nonzero = [direction_passes[burden] for burden in BURDEN_GRID if burden > 0.0]
    if all(nonzero) and monotonic:
        return "ROBUSTNESS_MONOTONIC_IMPAIRMENT_PATTERN"
    if any(nonzero):
        return "ROBUSTNESS_MIXED_DIRECTIONAL_RESPONSE"
    return "ROBUSTNESS_NO_IMPAIRMENT_ACROSS_GRID"


def _median(values: Iterable[float]) -> float:
    return float(statistics.median([float(value) for value in values]))


def analyze_existing() -> dict[str, Any]:
    gate26 = verify_gate26_inventory()
    freeze = verify_freeze()
    transform = verify_frozen_transform()
    mapping = verify_mapping()
    reuse = verify_endpoint_reuse(gate26, mapping)
    state = read_json(EXECUTION_STATE)
    if state.get("status") != "GATE27_NEW_SIMULATIONS_PASS" or state.get("simulation_jobs_completed") != MAX_NEW_SIMULATIONS:
        raise Gate27Error("ROBUSTNESS_INCOMPLETE_TECHNICAL_EXECUTION: all 15 new jobs are required.")
    transform_by_burden = {float(record["burden"]): record for record in transform["records"]}
    all_rows = _load_endpoint_rows(HEALTHY_METRICS, 0.0, "GATE21B_GATE26_FROZEN")
    all_rows.extend(_load_endpoint_rows(DISEASE_METRICS, 1.0, "GATE21E_GATE26_FROZEN"))
    new_rows: list[dict[str, Any]] = []
    for burden in NEW_BURDENS:
        checkpoint = transform_by_burden[burden]
        for seed in SEEDS:
            rollout = _job_output(burden, seed) / "rollout.npz"
            if not rollout.is_file():
                raise Gate27Error(f"ROBUSTNESS_INCOMPLETE_TECHNICAL_EXECUTION: missing {rollout}")
            metrics = rollout_seed_metrics(rollout)
            row = {
                "burden": burden,
                "expected_gain": expected_gain(burden),
                "seed": seed,
                "source": "GATE27_NEW",
                "source_gate": "GATE27",
                "reused_existing_run": False,
                "status": "PASS",
                PRIMARY_METRIC: float(metrics[PRIMARY_METRIC]),
                SECONDARY_METRIC: float(metrics[SECONDARY_METRIC]),
                "finite_qc": bool(metrics["finite_qc"]),
                "timestamp_monotonic": bool(metrics["timestamp_monotonic"]),
                "contact_detected": bool(metrics["contact_detected"]),
                "rollout_sha256": sha256_file(rollout),
                "source_artifact_reference": rollout.relative_to(ROOT).as_posix(),
            }
            new_rows.append(row)
    all_rows.extend(new_rows)
    if len(all_rows) != 25 or {(float(row["burden"]), int(row["seed"])) for row in all_rows} != {(b, s) for b in BURDEN_GRID for s in SEEDS}:
        raise Gate27Error("ROBUSTNESS_INCOMPLETE_TECHNICAL_EXECUTION: full burden/seed grid is incomplete.")
    healthy = {int(row["seed"]): row for row in all_rows if float(row["burden"]) == 0.0}
    output_rows: list[dict[str, Any]] = []
    for row in sorted(all_rows, key=lambda item: (float(item["burden"]), int(item["seed"]))):
        baseline = healthy[int(row["seed"])]
        speed = float(row[PRIMARY_METRIC])
        distance = float(row[SECONDARY_METRIC])
        healthy_speed = float(baseline[PRIMARY_METRIC])
        healthy_distance = float(baseline[SECONDARY_METRIC])
        checkpoint = transform_by_burden[float(row["burden"])]
        output_rows.append({
            **{field: row.get(field, "") for field in GRID_FIELDS},
            "delta_speed_vs_healthy": speed - healthy_speed,
            "speed_ratio_vs_healthy": speed / healthy_speed,
            "delta_distance_vs_healthy": distance - healthy_distance,
            "checkpoint_tensor_sha256": checkpoint["child_tensor_sha256"],
        })
    write_csv(GRID_METRICS, GRID_FIELDS, output_rows)
    per_burden: list[dict[str, Any]] = []
    direction_passes: dict[float, bool] = {}
    medians: list[float] = []
    for burden in BURDEN_GRID:
        rows = [row for row in output_rows if float(row["burden"]) == burden]
        median_speed = _median(row[PRIMARY_METRIC] for row in rows)
        median_delta = _median(row["delta_speed_vs_healthy"] for row in rows)
        direction = median_delta < 0.0 if burden > 0.0 else False
        direction_passes[burden] = direction
        medians.append(median_speed)
        per_burden.append({
            "burden": burden,
            "expected_gain": expected_gain(burden),
            "n_seeds": len(rows),
            "median_speed": median_speed,
            "median_paired_delta_speed": median_delta,
            "median_speed_ratio": _median(row["speed_ratio_vs_healthy"] for row in rows),
            "primary_direction_pass": direction,
            "median_distance": _median(row[SECONDARY_METRIC] for row in rows),
            "median_paired_delta_distance": _median(row["delta_distance_vs_healthy"] for row in rows),
        })
    monotonic = all(left >= right for left, right in zip(medians, medians[1:]))
    all_nonzero = all(direction_passes[burden] for burden in BURDEN_GRID if burden > 0.0)
    classification = classify_robustness(direction_passes, monotonic)
    summary = {
        "schema_version": "gate27-grid-summary-v1",
        "status": "GATE27_RIEMENSPERGER_ROBUSTNESS_COMPLETE",
        "primary_metric": PRIMARY_METRIC,
        "secondary_metric": SECONDARY_METRIC,
        "statistical_unit": "independent_seed",
        "burden_summaries": per_burden,
        "monotonic_nonincreasing_speed": monotonic,
        "all_nonzero_direction_pass": all_nonzero,
        "final_robustness_classification": classification,
        "gate26_result_unchanged": True,
        "gate26_result": GATE26_RESULT,
        "paper_ratio_reference_only": 0.7222222222222222,
        "paper_ratio_used_for_optimization": False,
    }
    write_json(GRID_SUMMARY, summary)
    diagnostic = {
        "schema_version": "gate27-downstream-trace-diagnostic-v1",
        "status": "DOWNSTREAM_TRACE_NOT_AVAILABLE",
        "reason": "Frozen Gate26 endpoint raw rollouts are not committed and were not duplicated; matched action/joint arrays are unavailable for read-only comparison.",
        "primary_classification_affected": False,
    }
    write_json(TRACE_DIAGNOSTIC, diagnostic)
    completion = {
        "schema_version": "gate27-riemensperger-robustness-completion-v1",
        "status": "GATE27_RIEMENSPERGER_ROBUSTNESS_COMPLETE",
        "gate27_execution_freeze_sha256": freeze["gate27_execution_freeze_sha256"],
        "source_main": SOURCE_MAIN,
        "gate26_result": GATE26_RESULT,
        "gate26_changed": False,
        "burden_grid": list(BURDEN_GRID),
        "reused_burdens": list(REUSED_BURDENS),
        "new_burdens": list(NEW_BURDENS),
        "seeds": list(SEEDS),
        "existing_simulations_reused": reuse["reused_simulations"],
        "new_simulations_planned": MAX_NEW_SIMULATIONS,
        "new_simulations_completed": MAX_NEW_SIMULATIONS,
        "checkpoint_transform_audit": transform["status"],
        "final_robustness_classification": classification,
        "calibration": False,
        "parameter_optimization": False,
        "best_burden_selected": False,
        "retuning": False,
        "seed_replacement": False,
        "posthoc_metric_selection": False,
        "quantitative_validation_supported": False,
        "biological_validation_supported": False,
        "gene_specific_validation_supported": False,
        "data_fabricated": False,
    }
    write_json(COMPLETION, completion)
    write_report(summary, transform, diagnostic)
    write_initial_signoff(classification, freeze["gate27_execution_freeze_sha256"])
    write_reproducibility_inventory()
    verify_gate27_reproducibility()
    return completion


def write_report(summary: dict[str, Any], transform: dict[str, Any], diagnostic: dict[str, Any]) -> None:
    rows = "\n".join(
        f"| {item['burden']:.2f} | {item['expected_gain']:.4f} | {item['n_seeds']} | {item['median_speed']:.12g} | {item['median_paired_delta_speed']:.12g} | `{item['primary_direction_pass']}` |"
        for item in summary["burden_summaries"]
    )
    text = f"""# Gate 27 - Riemensperger 2011 prospective robustness

## 1. Purpose

Gate27 kiểm tra độ bền của đáp ứng vận động trên burden grid đã preregister. Đây là thí nghiệm prospective mới, không phải cứu, retune hay diễn giải lại Gate26.

## 2. Relationship to closed Gate26

Gate26 giữ nguyên `NOT_REPRODUCED`, healthy `5/5 PASS`, disease burden 1.0 `5/5 PASS`, real ratio `0.7222222222222222` và virtual ratio `1.0`.

## 3. Prospective robustness question

Primary question: burden tăng có tạo median paired delta của `{PRIMARY_METRIC}` nhỏ hơn 0 một cách nhất quán so với healthy cùng seed hay không?

## 4. Frozen burden grid

Grid: `{list(BURDEN_GRID)}`. Gain: `{EXPECTED_GAINS}`. Burden không đơn vị và không biểu diễn phần trăm dopamine mất, knockdown hay mức độ bệnh sinh học.

## 5. Endpoint reuse

Burden 0.0 dùng lại 5 healthy seeds Gate26; burden 1.0 dùng lại 5 disease seeds Gate26. Không rerun hai endpoint. Chỉ 15 job mới ở burden 0.25, 0.50 và 0.75.

## 6. Transform integrity

Transform audit `{transform['status']}`; target count `{transform['target_count']}`; targeted outgoing edges `{transform['number_of_targeted_outgoing_edges']}`. Burden 0 tensor-identical với healthy; mọi burden dương thay đổi targeted edges theo gain đã khóa.

## 7. Fifteen new simulations

`15/15` job mới hoàn tất tuần tự, không retry và không thay seed. Protocol: 5000 steps, 0.5 s, timestep 0.0001 s, p9, CPG 12 Hz, CUDA, runtime profile `{RUNTIME_PROFILE}`.

## 8. QC

Mỗi rollout đạt finite values, timestamp monotonic, ground contact, joint trajectory và action trajectory thay đổi.

## 9. Seed-level results

Chi tiết 25 burden x seed nằm trong `experiments/gate_27_riemensperger_robustness/metrics/gate27_per_seed_grid.csv`. Seed là đơn vị thống kê; frame không phải replicate.

## 10. Grid summary

| Burden | Gain | n seeds | Median speed (mm/s) | Median paired delta | Direction pass |
| ---: | ---: | ---: | ---: | ---: | --- |
{rows}

## 11. Monotonicity

Median speed non-increasing: `{summary['monotonic_nonincreasing_speed']}`. Tất cả burden dương có median paired delta < 0: `{summary['all_nonzero_direction_pass']}`.

## 12. Final robustness classification

`{summary['final_robustness_classification']}`

Gate26 vẫn là `NOT_REPRODUCED`, bất kể kết quả Gate27.

## 13. Downstream diagnostics

`{diagnostic['status']}`. {diagnostic['reason']}

## 14. Limitations

Rollout ảo dài 0.5 s, khác assay thật 15 phút. Mapping chỉ ở mức dopamine class exploratory. Paper không cung cấp uncertainty phù hợp. Distance chỉ là endpoint mô tả thứ cấp và không được phép ghi đè classification từ speed.

## 15. Claim boundaries

Không calibration, không parameter optimization, không chọn best burden, không quantitative validation, biological Parkinson validation, gene-specific validation, clinical validation hoặc drug validation.

## 16. Reproducibility

Freeze, transform audit, telemetry, seed-level metrics, summary, manifest và SHA256 nhẹ được lưu trong Gate27. Raw `.npz`, checkpoint `.pt` và logs giữ local ngoài Git.

## 17. Human review status

`WAITING_GATE27_RIEMENSPERGER_ROBUSTNESS_HUMAN_REVIEW`. Mã không tự phê duyệt hoặc đóng Gate27.
"""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(text, encoding="utf-8")


def build_initial_signoff(classification: str, freeze_sha: str) -> dict[str, Any]:
    return {
        "schema_version": "gate27-riemensperger-robustness-review-v1",
        "status": "WAITING_GATE27_RIEMENSPERGER_ROBUSTNESS_HUMAN_REVIEW",
        "decision": "PENDING_HUMAN_REVIEW",
        "gate27_execution_freeze_sha256": freeze_sha,
        "execution_freeze_approved": False,
        "endpoint_reuse_approved": False,
        "transform_audit_approved": False,
        "simulation_qc_approved": False,
        "robustness_analysis_approved": False,
        "claim_boundary_approved": False,
        "final_robustness_classification": classification,
        "gate27_closed": False,
        "reviewer_1": "",
        "reviewer_2": "",
        "review_date": "",
    }


def write_initial_signoff(classification: str, freeze_sha: str) -> None:
    candidate = build_initial_signoff(classification, freeze_sha)
    if SIGNOFF.exists() and read_json(SIGNOFF).get("status") != candidate["status"]:
        raise Gate27Error("Refusing to overwrite a non-pending Gate27 human signoff.")
    write_json(SIGNOFF, candidate)


def _inventory_paths() -> list[Path]:
    paths = [
        Path(__file__), ROOT / "tests/test_gate27_riemensperger_robustness.py", ROOT / ".gitignore",
        GATE27 / ".gitattributes",
        FREEZE, PREFLIGHT, EXECUTION_STATE, STORAGE_PREFLIGHT, TRANSFORM_AUDIT, TELEMETRY,
        NEW_JOB_METRICS, GRID_METRICS, GRID_SUMMARY, TRACE_DIAGNOSTIC, COMPLETION, REPORT, SIGNOFF,
    ]
    paths.extend(CHECKPOINTS / f"burden_{int(round(burden * 100)):03d}" / "transform_audit.json" for burden in BURDEN_GRID)
    return paths


def write_reproducibility_inventory() -> None:
    records = []
    for path in _inventory_paths():
        if not path.is_file():
            raise Gate27Error(f"Missing lightweight reproducibility artifact: {path}")
        records.append({
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        })
    inventory = {
        "schema_version": "gate27-reproducibility-inventory-v1",
        "status": "COMPLETE",
        "raw_rollouts_committed": False,
        "raw_checkpoints_committed": False,
        "logs_committed": False,
        "record_count": len(records),
        "records": records,
    }
    write_json(INVENTORY, inventory)
    CHECKSUMS.write_text("".join(f"{record['sha256']}  {record['path']}\n" for record in records), encoding="utf-8")


def verify_gate27_reproducibility() -> dict[str, Any]:
    inventory = read_json(INVENTORY)
    records = inventory.get("records", [])
    checksums: dict[str, str] = {}
    for line in CHECKSUMS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, relative = line.split(maxsplit=1)
            if relative in checksums:
                raise Gate27Error(f"Duplicate Gate27 checksum path: {relative}")
            checksums[relative] = digest
    expected = {str(record["path"]): str(record["sha256"]) for record in records}
    bad = []
    for record in records:
        path = ROOT / str(record["path"])
        matches = (
            path.is_file()
            and any(
                len(payload) == int(record["size_bytes"])
                and hashlib.sha256(payload).hexdigest() == str(record["sha256"])
                for payload in _portable_text_candidates(path)
            )
        )
        if not matches:
            bad.append(str(record["path"]))
    if bad or checksums != expected or len(records) != inventory.get("record_count"):
        raise Gate27Error(f"Gate27 reproducibility verification failed: {bad}")
    return {"status": "PASS", "verified": len(records), "total": len(records)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--analyze-existing", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.execute:
            result = execute()
        elif args.analyze_existing:
            result = analyze_existing()
        else:
            result = preflight()
    except (Gate27Error, OSError, RuntimeError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc), "simulation_retry": False}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
