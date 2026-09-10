"""Implement and benchmark the Generation-2 virtual assay observation layer.

The default invocation never launches a GPU or simulation.  The sole execution
mode is an explicitly guarded, healthy-only, four-job engineering benchmark.
"""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for import_root in (ROOT, SRC):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from drosophila_pd_neural.assays.aggregation import (  # noqa: E402
    calculate_trajectory_metrics,
    demonstrate_median_of_medians,
    pool_segment_metrics,
)
from drosophila_pd_neural.assays.riemensperger2011 import (  # noqa: E402
    ADAPTER_ID,
    ADAPTER_VERSION,
    ASSAY_CONTRACT_SHA256,
    Riemensperger2011OpenArenaAdapter,
)
from drosophila_pd_neural.assays.trajectory import (  # noqa: E402
    CANONICAL_ROLLOUT_SCHEMA_MAPPING,
    inspect_npz_schema,
    load_npz_trajectory,
    segment_trajectory,
    sha256_file,
    slice_trajectory,
)
from drosophila_pd_neural.assays.types import (  # noqa: E402
    AdapterProvenance,
    ObservationWindow,
    TrajectoryData,
)
from drosophila_pd_neural.assays.validation import (  # noqa: E402
    AssayValidationError,
    deterministic_fixtures,
    validate_trajectory,
)


SOURCE_MAIN_COMMIT = "5a99a2f5646f754b2f9ed878ad5335bbc1b9b951"
EXPECTED_GATE28A_APPROVED_HEAD = "2bd8bc39337abe37b30acfe305a87123293ccf7c"
EXPECTED_RUNTIME_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"
EXPECTED_HEALTHY_CHECKPOINT_SHA256 = (
    "d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691"
)
TECHNICAL_SEED = 9101
TIMESTEP_S = 0.0001
TECHNICAL_DURATIONS_S = (0.5, 1.0, 2.0, 5.0)
TECHNICAL_STEPS = (5000, 10000, 20000, 50000)
PAPER_DURATION_S = 900.0
PAPER_DURATION_STEPS = 9_000_000
MAX_TECHNICAL_JOBS = 4
GPU_STOP_TEMPERATURE_C = 82.0
GPU_IDLE_MEMORY_LIMIT_MB = 1024.0
GPU_IDLE_UTILIZATION_LIMIT_PERCENT = 50.0
CONSERVATIVE_STORAGE_RESERVE_BYTES = 5 * 1024**3

GATE_ROOT = ROOT / "experiments/gate_28b_virtual_assay_adapter"
MANIFESTS = GATE_ROOT / "manifests"
RESULTS = GATE_ROOT / "results"
GATE28B_MANIFEST = MANIFESTS / "gate28b_manifest.json"
SCHEMA_AUDIT = MANIFESTS / "runtime_rollout_schema_audit.json"
SOURCE_REVIEW = MANIFESTS / "riemensperger_assay_source_review.json"
SOURCE_AMENDMENT = MANIFESTS / "riemensperger_assay_source_review_amendment.json"
GATE28A_TEST_ALIGNMENT = MANIFESTS / "gate28a_human_closure_test_alignment.json"
PREFLIGHT = MANIFESTS / "duration_benchmark_preflight.json"
INVENTORY = MANIFESTS / "reproducibility_inventory.json"
CHECKSUMS = MANIFESTS / "checksums.sha256"
FIXTURE_RESULTS = RESULTS / "synthetic_fixture_validation.json"
BENCHMARK_CSV = RESULTS / "duration_benchmark.csv"
SCALING_SUMMARY = RESULTS / "duration_scaling_summary.json"
SEGMENTATION_SUMMARY = RESULTS / "segmentation_consistency.json"
RUN_OBSERVATIONS = RESULTS / "technical_run_observations.json"
REPORT = ROOT / "docs/research_design/gate28b_virtual_assay_adapter_report.md"
SIGNOFF = ROOT / "research/validation/prospective/gate28b_virtual_assay_adapter_reviewer_signoff.json"

GATE28A_SIGNOFF = (
    ROOT
    / "research/validation/prospective/gate28a_gen2_scope_metric_study_split_reviewer_signoff.json"
)
GATE28A_MANIFEST = (
    ROOT / "experiments/gate_28a_gen2_scope_metric_study_split/manifests/gate28a_manifest.json"
)
STUDY_SPLIT = ROOT / "research/literature_v2/study_split_manifest.yaml"
ASSAY_CONTRACT = ROOT / "configs/generation2/assays/riemensperger_2011_open_arena.yaml"
ADAPTER_CONFIG = (
    ROOT / "configs/generation2/adapters/riemensperger_2011_open_arena_adapter_v1.yaml"
)
STATISTICAL_HIERARCHY = (
    ROOT / "configs/generation2/adapters/statistical_hierarchy_contract.yaml"
)
SEGMENTED_AGGREGATION = (
    ROOT / "configs/generation2/adapters/segmented_aggregation_contract.yaml"
)

PLATFORM_RUNNER = ROOT / "scripts/run_neural_experiment.py"
RUNTIME_CANDIDATES = (
    ROOT.parent / "drosophila-pd-flygym-gate24-memorysafe-clean",
    ROOT.parent / "drosophila-pd-flygym-gate24-memorysafe",
)
RUNTIME_PYTHON = ROOT.parent / "drosophila-pd-flygym/.venv/Scripts/python.exe"
BRAIN_ROOT = ROOT.parent / "external/fly-brain-audit"
HEALTHY_CHECKPOINT = BRAIN_ROOT / "data/plastic_weights.pt"
HISTORICAL_GATE26_ROLLOUT = (
    ROOT.parent
    / "riemensperger-full-completion-worktree"
    / "experiments/gate_21b_riemensperger_healthy/results/seed_000/rollout.npz"
)
EXTERNAL_OUTPUT_ROOT = Path(
    os.environ.get(
        "GATE28B_TECHNICAL_OUTPUT_ROOT",
        str(ROOT.parent / "gate28b_technical_outputs/duration_benchmark"),
    )
).resolve()
EXTERNAL_EXECUTION_STATE = EXTERNAL_OUTPUT_ROOT / "benchmark_execution_state.json"

PROTECTED_GATE28A_PATHS = (
    "experiments/gate_28a_gen2_scope_metric_study_split",
    "configs/generation2/canonical_metric_dictionary.yaml",
    "configs/generation2/statistic_contract.yaml",
    "configs/generation2/experimental_unit_contract.yaml",
    "configs/generation2/duration_policy.yaml",
    "configs/generation2/assays",
    "research/literature_v2",
    "docs/claims/generation2_claim_policy.md",
    "research/validation/prospective/gate28a_gen2_scope_metric_study_split_reviewer_signoff.json",
)


class Gate28BError(RuntimeError):
    """Fail-closed Gate28B contract violation."""


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Gate28BError(f"Invalid or missing JSON: {path}") from exc
    if not isinstance(value, dict):
        raise Gate28BError(f"Expected JSON object: {path}")
    return value


def _yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise Gate28BError(f"Invalid or missing YAML: {path}") from exc
    if not isinstance(value, dict):
        raise Gate28BError(f"Expected YAML mapping: {path}")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def _git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise Gate28BError(result.stderr.strip() or f"Git failed: {' '.join(args)}")
    return result.stdout.strip()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def verify_gate28a_closure() -> dict[str, Any]:
    signoff = _json(GATE28A_SIGNOFF)
    manifest = _json(GATE28A_MANIFEST)
    split = _yaml(STUDY_SPLIT)
    checks = {
        "status": signoff.get("status")
        == "GATE28A_GEN2_SCIENTIFIC_CONTRACT_REVIEW_APPROVED",
        "decision": signoff.get("decision")
        == "APPROVED_GATE28A_GEN2_SCIENTIFIC_CONTRACT_CLOSURE",
        "closed": signoff.get("gate28a_closed") is True,
        "approved_head": signoff.get("approved_head") == EXPECTED_GATE28A_APPROVED_HEAD,
        "first_track": manifest.get("first_track")
        == "RIEMENSPERGER_2011_DOPAMINE_FUNCTIONAL_DEFICIENCY",
        "pozo_future_holdout_false": split.get("pozo_2022", {}).get("future_sealed_holdout")
        is False,
        "riemensperger_external_validation_false": split.get("riemensperger_2011", {}).get(
            "external_validation"
        )
        is False,
        "alpha_syn_loso_unfrozen": split.get("alpha_syn_final_loso_allocation")
        == "NOT_YET_FROZEN",
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise Gate28BError(f"Gate28A closure check failed: {failed}")
    return checks


def verify_gate28a_immutable() -> dict[str, Any]:
    changed_output = _git(
        "diff", "--name-only", SOURCE_MAIN_COMMIT, "--", *PROTECTED_GATE28A_PATHS
    )
    changed = [line for line in changed_output.splitlines() if line]
    if changed:
        raise Gate28BError(f"Gate28A protected artifacts changed: {changed}")
    if sha256_file(ASSAY_CONTRACT) != ASSAY_CONTRACT_SHA256:
        raise Gate28BError("Frozen Riemensperger assay contract SHA256 changed.")
    return {
        "gate28a_changed": False,
        "protected_path_count": len(PROTECTED_GATE28A_PATHS),
        "assay_contract_sha256": ASSAY_CONTRACT_SHA256,
    }


def validate_synthetic_fixtures() -> dict[str, Any]:
    fixtures = deterministic_fixtures()
    cases: dict[str, dict[str, Any]] = {}
    expected = {
        "stationary": (0.0, 0.0, 0.0, 0.0),
        "constant_straight": (4.0, 4.0, 2.0, 2.0),
        "piecewise_speed": (6.0, 6.0, 2.0, 2.0),
        "turning": (2.0, math.sqrt(2.0), 1.0, 1.0),
        "irregular_timestamps": (4.0, 4.0, 2.0, 2.0),
    }
    for name, values in expected.items():
        trajectory = fixtures[name]
        if not isinstance(trajectory, TrajectoryData):
            raise Gate28BError(f"Fixture {name} is not a trajectory.")
        metrics = calculate_trajectory_metrics(trajectory)
        observed = (
            metrics.distance_traveled_mm,
            metrics.displacement_mm,
            metrics.mean_planar_speed_mm_s,
            metrics.median_framewise_planar_speed_mm_s,
        )
        passed = all(
            math.isclose(actual, target, rel_tol=0.0, abs_tol=1e-12)
            for actual, target in zip(observed, values, strict=True)
        )
        cases[name] = {"status": "PASS" if passed else "FAIL", "observed": observed}
        if not passed:
            raise Gate28BError(f"Synthetic fixture failed: {name}")

    nan_time, nan_position = fixtures["invalid_nan"]
    try:
        validate_trajectory(TrajectoryData(nan_time, nan_position))
    except AssayValidationError:
        cases["invalid_nan"] = {"status": "PASS_REJECTED_AS_INVALID"}
    else:
        raise Gate28BError("NaN fixture was not rejected.")

    straight = fixtures["constant_straight"]
    assert isinstance(straight, TrajectoryData)
    sliced = slice_trajectory(straight, ObservationWindow(0.5, 1.5))
    sliced_metrics = calculate_trajectory_metrics(sliced)
    if not math.isclose(sliced_metrics.distance_traveled_mm, 2.0, abs_tol=1e-12):
        raise Gate28BError("Deterministic window slicing failed.")
    cases["window_slicing"] = {
        "status": "PASS",
        "distance_traveled_mm": sliced_metrics.distance_traveled_mm,
    }

    long_straight = TrajectoryData(
        np.linspace(0.0, 5.0, 51),
        np.column_stack((np.linspace(0.0, 10.0, 51), np.zeros(51))),
    )
    full = calculate_trajectory_metrics(long_straight)
    segment_metrics = [
        calculate_trajectory_metrics(segment)
        for segment in segment_trajectory(long_straight, segment_duration_s=0.5)
    ]
    pooled = pool_segment_metrics(segment_metrics)
    if not math.isclose(
        pooled["distance_traveled_mm"], full.distance_traveled_mm, abs_tol=1e-12
    ):
        raise Gate28BError("Segment distance reconstruction failed.")
    if not math.isclose(
        pooled["pooled_interval_mean_planar_speed_mm_s"],
        full.mean_planar_speed_mm_s,
        abs_tol=1e-12,
    ):
        raise Gate28BError("Segment pooled mean reconstruction failed.")
    cases["segment_reconstruction"] = {
        "status": "PASS",
        "segment_count": len(segment_metrics),
        "median_of_medians": demonstrate_median_of_medians(segment_metrics),
    }
    result = {
        "schema_version": "gate28b-synthetic-fixture-validation-v1",
        "status": "PASS",
        "deterministic": True,
        "unseeded_random_generation": False,
        "case_count": len(cases),
        "cases": cases,
        "gpu": False,
        "simulation": False,
    }
    _write_json(FIXTURE_RESULTS, result)
    refresh_gate28b_package()
    return result


def inspect_rollout(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise Gate28BError(f"Rollout not available: {path}")
    metadata_path = path.parent / "metadata.json"
    metadata = _json(metadata_path) if metadata_path.is_file() else {}
    records = inspect_npz_schema(path)
    available = {str(item["name"]) for item in records}
    required = set(CANONICAL_ROLLOUT_SCHEMA_MAPPING.values())
    result = {
        "schema_version": "gate28b-runtime-rollout-schema-audit-v1",
        "status": "RUNTIME_ROLLOUT_SCHEMA_AUDITED",
        "source_kind": "HISTORICAL_GATE26_HEALTHY_SEED_000_READ_ONLY",
        "source_raw_committed_to_git": False,
        "source_rollout_sha256": sha256_file(path),
        "source_frame_count": next(
            (item["shape"][0] for item in records if item["name"] == "timestamp_s"), None
        ),
        "source_runtime_commit": metadata.get("simulation", {}).get("repository_commit"),
        "schema_mapping": dict(CANONICAL_ROLLOUT_SCHEMA_MAPPING),
        "required_trajectory_keys_resolved": required.issubset(available),
        "key_count": len(records),
        "keys": records,
        "raw_artifact_modified": False,
        "raw_artifact_copied_to_git": False,
    }
    if not result["required_trajectory_keys_resolved"]:
        raise Gate28BError("Required trajectory keys were not resolved from the real rollout.")
    _write_json(SCHEMA_AUDIT, result)
    refresh_gate28b_package()
    return result


def _metadata_provenance(rollout: Path, source_label: str) -> AdapterProvenance:
    metadata_path = rollout.parent / "metadata.json"
    metadata = _json(metadata_path) if metadata_path.is_file() else {}
    simulation = metadata.get("simulation", {})
    seed = simulation.get("random_seed")
    runtime_commit = simulation.get("repository_commit")
    if not isinstance(seed, int) or not isinstance(runtime_commit, str):
        raise Gate28BError("Rollout metadata does not identify seed and runtime commit.")
    return AdapterProvenance(
        source_rollout_sha256=sha256_file(rollout),
        source_runtime_commit=runtime_commit,
        simulation_seed=seed,
        technical_or_scientific_source=source_label,
    )


def observe_rollout(
    rollout: Path,
    *,
    source_label: str = "READ_ONLY_ROLLOUT_OBSERVATION",
    window: ObservationWindow | None = None,
) -> dict[str, Any]:
    rollout = rollout.resolve()
    trajectory = load_npz_trajectory(rollout)
    provenance = _metadata_provenance(rollout, source_label)
    adapter = Riemensperger2011OpenArenaAdapter()
    return adapter.observe(trajectory, provenance=provenance, window=window).to_dict()


def _runtime_root() -> Path:
    for candidate in RUNTIME_CANDIDATES:
        if not candidate.is_dir():
            continue
        try:
            head = _git("rev-parse", "HEAD", cwd=candidate)
            dirty = _git("status", "--porcelain", cwd=candidate)
        except Gate28BError:
            continue
        if head == EXPECTED_RUNTIME_COMMIT and not dirty:
            return candidate.resolve()
    raise Gate28BError(
        "GATE28B_TECHNICAL_DURATION_BENCHMARK_BLOCKED_RUNTIME_UNAVAILABLE"
    )


def _gpu_snapshot() -> dict[str, Any]:
    query = (
        "name,temperature.gpu,utilization.gpu,memory.used,memory.free,memory.total"
    )
    result = subprocess.run(
        ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise Gate28BError(f"nvidia-smi failed: {result.stderr.strip()}")
    line = next((value.strip() for value in result.stdout.splitlines() if value.strip()), "")
    fields = [value.strip() for value in line.split(",")]
    if len(fields) != 6:
        raise Gate28BError(f"Unable to parse nvidia-smi output: {line!r}")
    snapshot = {
        "name": fields[0],
        "temperature_c": float(fields[1]),
        "utilization_percent": float(fields[2]),
        "memory_used_mb": float(fields[3]),
        "memory_free_mb": float(fields[4]),
        "memory_total_mb": float(fields[5]),
    }
    process_result = subprocess.run(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    snapshot["compute_process_query"] = [
        line.strip() for line in process_result.stdout.splitlines() if line.strip()
    ]
    return snapshot


def _validate_gpu_idle(snapshot: Mapping[str, Any]) -> None:
    if float(snapshot["temperature_c"]) >= GPU_STOP_TEMPERATURE_C:
        raise Gate28BError("GATE28B_TECHNICAL_BENCHMARK_BLOCKED_GPU_TEMPERATURE")
    if (
        float(snapshot["memory_used_mb"]) >= GPU_IDLE_MEMORY_LIMIT_MB
        or float(snapshot["utilization_percent"]) >= GPU_IDLE_UTILIZATION_LIMIT_PERCENT
    ):
        raise Gate28BError("GATE28B_TECHNICAL_BENCHMARK_BLOCKED_HEAVY_GPU_PROCESS")


def _cuda_runtime_check() -> dict[str, Any]:
    if not RUNTIME_PYTHON.is_file():
        raise Gate28BError(f"Approved runtime Python is unavailable: {RUNTIME_PYTHON}")
    code = (
        "import json,torch; ok=bool(torch.cuda.is_available()); "
        "print(json.dumps({'available':ok,'torch':torch.__version__,"
        "'cuda':torch.version.cuda,'device':torch.cuda.get_device_name(0) if ok else None}))"
    )
    result = subprocess.run(
        [str(RUNTIME_PYTHON), "-c", code], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise Gate28BError(f"CUDA runtime check failed: {result.stderr.strip()}")
    value = json.loads(result.stdout.strip().splitlines()[-1])
    if value.get("available") is not True:
        raise Gate28BError("Approved runtime Python cannot access CUDA.")
    return value


def _storage_requirement() -> dict[str, Any]:
    if HISTORICAL_GATE26_ROLLOUT.is_file():
        historical_bytes = HISTORICAL_GATE26_ROLLOUT.stat().st_size
        basis_steps = 5000
        bytes_per_step = historical_bytes / basis_steps
        basis = "HISTORICAL_GATE26_HEALTHY_0_5S_ROLLOUT"
    else:
        historical_bytes = None
        bytes_per_step = 6000.0
        basis_steps = None
        basis = "CONSERVATIVE_6000_BYTES_PER_STEP_FALLBACK"
    projected_raw = math.ceil(bytes_per_step * sum(TECHNICAL_STEPS))
    required = projected_raw + CONSERVATIVE_STORAGE_RESERVE_BYTES
    EXTERNAL_OUTPUT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(EXTERNAL_OUTPUT_ROOT.parent).free
    return {
        "basis": basis,
        "historical_rollout_bytes": historical_bytes,
        "historical_rollout_steps": basis_steps,
        "estimated_bytes_per_step": bytes_per_step,
        "projected_four_job_raw_bytes": projected_raw,
        "conservative_reserve_bytes": CONSERVATIVE_STORAGE_RESERVE_BYTES,
        "required_free_bytes": required,
        "available_free_bytes": free,
        "strict_capacity_rule": "available_free_bytes > required_free_bytes",
        "capacity_pass": free > required,
    }


def benchmark_preflight() -> dict[str, Any]:
    if _git("rev-parse", SOURCE_MAIN_COMMIT) != SOURCE_MAIN_COMMIT:
        raise Gate28BError("Source main commit is unavailable.")
    closure = verify_gate28a_closure()
    immutable = verify_gate28a_immutable()
    fixture = validate_synthetic_fixtures()
    runtime = _runtime_root()
    if not PLATFORM_RUNNER.is_file():
        raise Gate28BError("Canonical brain-body wrapper is missing.")
    if not HEALTHY_CHECKPOINT.is_file():
        raise Gate28BError("Healthy checkpoint is unavailable.")
    checkpoint_sha = sha256_file(HEALTHY_CHECKPOINT)
    if checkpoint_sha != EXPECTED_HEALTHY_CHECKPOINT_SHA256:
        raise Gate28BError("Healthy checkpoint SHA256 mismatch.")
    if EXTERNAL_OUTPUT_ROOT.exists():
        raise Gate28BError(
            "Technical output root already exists; execution is single-use and no retry is allowed."
        )
    storage = _storage_requirement()
    if storage["capacity_pass"] is not True:
        raise Gate28BError("GATE28B_TECHNICAL_BENCHMARK_BLOCKED_STORAGE")
    gpu = _gpu_snapshot()
    _validate_gpu_idle(gpu)
    cuda = _cuda_runtime_check()
    result = {
        "schema_version": "gate28b-duration-benchmark-preflight-v1",
        "status": "GATE28B_TECHNICAL_BENCHMARK_PREFLIGHT_PASS",
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "adapter_implementation_commit": _git("rev-parse", "HEAD"),
        "gate28a_closure": closure,
        "gate28a_immutability": immutable,
        "fixture_status": fixture["status"],
        "runtime_commit": EXPECTED_RUNTIME_COMMIT,
        "runtime_profile": "GATE24E_MEMORY_SAFE",
        "runtime_worktree_clean": True,
        "runtime_python": str(RUNTIME_PYTHON),
        "healthy_checkpoint_sha256": checkpoint_sha,
        "condition": "HEALTHY",
        "disease_perturbation": "NONE",
        "technical_seed": TECHNICAL_SEED,
        "durations_s": list(TECHNICAL_DURATIONS_S),
        "steps": list(TECHNICAL_STEPS),
        "technical_jobs_planned": MAX_TECHNICAL_JOBS,
        "storage": storage,
        "gpu_before_benchmark": gpu,
        "cuda_runtime": cuda,
        "calibration": False,
        "model_fitting": False,
        "scientific_jobs": 0,
        "disease_jobs": 0,
        "automatic_retry": False,
        "direct_15_minute_execution": False,
    }
    _write_json(PREFLIGHT, result)
    refresh_gate28b_package()
    return result


def _technical_output_name(duration_s: float) -> str:
    return f"duration_{str(duration_s).replace('.', '_')}s"


def _technical_command(runtime: Path, output: Path, steps: int) -> list[str]:
    command = [
        str(RUNTIME_PYTHON),
        str(PLATFORM_RUNNER),
        "--brain-root",
        str(BRAIN_ROOT),
        "--platform-root",
        str(runtime),
        "--brain-python",
        str(RUNTIME_PYTHON),
        "--seed",
        str(TECHNICAL_SEED),
        "--steps",
        str(steps),
        "--device",
        "cuda",
        "--output",
        str(output),
        "--stimulus",
        "p9",
        "--artifact-profile",
        "GATE24E_MEMORY_SAFE",
    ]
    forbidden = {"--config", "--prepared-checkpoint", "--age-days", "--compare-to"}
    if forbidden.intersection(command):
        raise Gate28BError("Technical command contains a disease or comparison argument.")
    return command


def _process_tree_rss_mb(process: subprocess.Popen[bytes]) -> float | None:
    try:
        import psutil
    except ImportError:
        return None
    try:
        root = psutil.Process(process.pid)
        processes = [root, *root.children(recursive=True)]
        return sum(item.memory_info().rss for item in processes if item.is_running()) / 1024**2
    except (psutil.Error, OSError):
        return None


def _run_one_technical_job(
    runtime: Path,
    *,
    duration_s: float,
    steps: int,
) -> dict[str, Any]:
    before_gpu = _gpu_snapshot()
    _validate_gpu_idle(before_gpu)
    output = EXTERNAL_OUTPUT_ROOT / _technical_output_name(duration_s)
    if output.exists():
        raise Gate28BError(f"Technical output already exists; no retry: {output}")
    free_before = shutil.disk_usage(EXTERNAL_OUTPUT_ROOT.parent).free
    log_path = EXTERNAL_OUTPUT_ROOT / "logs" / f"{_technical_output_name(duration_s)}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = _technical_command(runtime, output, steps)
    environment = os.environ.copy()
    environment.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    started_utc = datetime.now(UTC).isoformat()
    started = time.perf_counter()
    peak_ram_mb: float | None = None
    peak_gpu_memory_mb: float | None = None
    with log_path.open("wb") as log:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=environment,
        )
        while process.poll() is None:
            rss = _process_tree_rss_mb(process)
            if rss is not None:
                peak_ram_mb = rss if peak_ram_mb is None else max(peak_ram_mb, rss)
            try:
                gpu_memory = float(_gpu_snapshot()["memory_used_mb"])
                peak_gpu_memory_mb = (
                    gpu_memory
                    if peak_gpu_memory_mb is None
                    else max(peak_gpu_memory_mb, gpu_memory)
                )
            except Gate28BError:
                pass
            time.sleep(1.0)
        return_code = process.wait()
    wall_clock_s = time.perf_counter() - started
    ended_utc = datetime.now(UTC).isoformat()
    if return_code != 0:
        raise Gate28BError(
            f"TECHNICAL_DURATION_BENCHMARK_INCOMPLETE: duration={duration_s}, "
            f"return_code={return_code}, log={log_path}"
        )
    status_path = output / "status.json"
    rollout = output / "rollout.npz"
    status = _json(status_path)
    if status.get("status") != "PASS" or status.get("simulation_run") is not True:
        raise Gate28BError(f"Technical job did not produce PASS status: {output}")
    if not rollout.is_file():
        raise Gate28BError(f"Technical job did not produce rollout.npz: {output}")
    raw_output_bytes = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
    free_after = shutil.disk_usage(EXTERNAL_OUTPUT_ROOT.parent).free
    after_gpu = _gpu_snapshot()
    return {
        "duration_s": duration_s,
        "steps": steps,
        "wall_clock_s": wall_clock_s,
        "steps_per_wall_second": steps / wall_clock_s,
        "raw_output_bytes": raw_output_bytes,
        "bytes_per_step": raw_output_bytes / steps,
        "peak_process_ram_mb": peak_ram_mb,
        "gpu_peak_memory_mb": peak_gpu_memory_mb,
        "starting_free_disk_bytes": free_before,
        "ending_free_disk_bytes": free_after,
        "rollout_sha256": sha256_file(rollout),
        "status": "PASS",
        "started_at_utc": started_utc,
        "ended_at_utc": ended_utc,
        "gpu_before": before_gpu,
        "gpu_after": after_gpu,
        "output_directory": str(output),
        "log_path": str(log_path),
        "command": command,
    }


def execute_technical_duration_benchmark() -> dict[str, Any]:
    preflight = benchmark_preflight()
    if preflight.get("status") != "GATE28B_TECHNICAL_BENCHMARK_PREFLIGHT_PASS":
        raise Gate28BError("Technical benchmark preflight is not PASS.")
    if len(TECHNICAL_DURATIONS_S) != MAX_TECHNICAL_JOBS:
        raise Gate28BError("Technical benchmark must contain exactly four jobs.")
    if tuple(int(duration / TIMESTEP_S) for duration in TECHNICAL_DURATIONS_S) != TECHNICAL_STEPS:
        raise Gate28BError("Frozen duration-to-step mapping changed.")
    runtime = _runtime_root()
    EXTERNAL_OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    state: dict[str, Any] = {
        "schema_version": "gate28b-duration-benchmark-execution-v1",
        "status": "EXECUTION_IN_PROGRESS",
        "adapter_implementation_commit": _git("rev-parse", "HEAD"),
        "condition": "HEALTHY",
        "disease_perturbation": "NONE",
        "technical_seed": TECHNICAL_SEED,
        "automatic_retry": False,
        "technical_jobs_planned": MAX_TECHNICAL_JOBS,
        "technical_jobs_completed": 0,
        "records": [],
        "scientific_jobs_run": 0,
        "disease_jobs_run": 0,
        "calibration_run": False,
        "model_fitting_run": False,
    }
    _write_json(EXTERNAL_EXECUTION_STATE, state)
    for duration_s, steps in zip(TECHNICAL_DURATIONS_S, TECHNICAL_STEPS, strict=True):
        try:
            record = _run_one_technical_job(
                runtime, duration_s=duration_s, steps=steps
            )
        except Gate28BError as exc:
            state["status"] = "TECHNICAL_DURATION_BENCHMARK_INCOMPLETE"
            state["failure"] = str(exc)
            _write_json(EXTERNAL_EXECUTION_STATE, state)
            raise
        state["records"].append(record)
        state["technical_jobs_completed"] = len(state["records"])
        _write_json(EXTERNAL_EXECUTION_STATE, state)
    state["status"] = "TECHNICAL_DURATION_BENCHMARK_COMPLETE"
    state["gpu_jobs_run"] = MAX_TECHNICAL_JOBS
    state["simulation_jobs_run"] = MAX_TECHNICAL_JOBS
    _write_json(EXTERNAL_EXECUTION_STATE, state)
    return analyze_technical_benchmark()


def _write_benchmark_csv(records: Sequence[Mapping[str, Any]]) -> None:
    fields = (
        "duration_s",
        "steps",
        "wall_clock_s",
        "steps_per_wall_second",
        "raw_output_bytes",
        "bytes_per_step",
        "peak_process_ram_mb",
        "gpu_peak_memory_mb",
        "starting_free_disk_bytes",
        "ending_free_disk_bytes",
        "rollout_sha256",
        "status",
    )
    BENCHMARK_CSV.parent.mkdir(parents=True, exist_ok=True)
    with BENCHMARK_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field) for field in fields})


def _segmentation_analysis(rollout: Path) -> dict[str, Any]:
    trajectory = load_npz_trajectory(rollout)
    full = calculate_trajectory_metrics(trajectory)
    segments = segment_trajectory(trajectory, segment_duration_s=0.5)
    segment_metrics = [calculate_trajectory_metrics(item) for item in segments]
    pooled = pool_segment_metrics(segment_metrics)
    distance_delta = pooled["distance_traveled_mm"] - full.distance_traveled_mm
    mean_delta = (
        pooled["pooled_interval_mean_planar_speed_mm_s"]
        - full.mean_planar_speed_mm_s
    )
    median_delta = (
        pooled["pooled_framewise_median_planar_speed_mm_s"]
        - full.median_framewise_planar_speed_mm_s
    )
    tolerance = 1e-9
    return {
        "schema_version": "gate28b-segmentation-consistency-v1",
        "status": "SEGMENTED_METRIC_AGGREGATION_IMPLEMENTED",
        "full_duration_s": full.observed_duration_s,
        "segment_duration_s": 0.5,
        "segment_count": len(segments),
        "boundary_policy": "SHARED_BOUNDARY_SAMPLE_NO_EDGE_LOSS_OR_DOUBLE_COUNT",
        "full_distance_mm": full.distance_traveled_mm,
        "sum_segment_distance_mm": pooled["distance_traveled_mm"],
        "distance_delta_mm": distance_delta,
        "distance_consistent": abs(distance_delta) <= tolerance,
        "full_mean_planar_speed_mm_s": full.mean_planar_speed_mm_s,
        "pooled_interval_mean_planar_speed_mm_s": pooled[
            "pooled_interval_mean_planar_speed_mm_s"
        ],
        "mean_delta_mm_s": mean_delta,
        "pooled_mean_consistent": abs(mean_delta) <= tolerance,
        "full_median_framewise_planar_speed_mm_s": full.median_framewise_planar_speed_mm_s,
        "pooled_framewise_median_planar_speed_mm_s": pooled[
            "pooled_framewise_median_planar_speed_mm_s"
        ],
        "pooled_framewise_median_delta_mm_s": median_delta,
        "pooled_framewise_median_consistent": abs(median_delta) <= tolerance,
        "median_of_segment_medians_demonstration": demonstrate_median_of_medians(
            segment_metrics
        ),
        "segment_is_replicate": False,
        "segmented_biological_validity_claimed": False,
        "continuous_15_minute_equivalence_established": False,
        "long_horizon_state_dependence": "UNRESOLVED",
    }


def analyze_technical_benchmark() -> dict[str, Any]:
    state = _json(EXTERNAL_EXECUTION_STATE)
    records = state.get("records")
    if (
        state.get("status") != "TECHNICAL_DURATION_BENCHMARK_COMPLETE"
        or not isinstance(records, list)
        or len(records) != MAX_TECHNICAL_JOBS
    ):
        raise Gate28BError("TECHNICAL_DURATION_BENCHMARK_INCOMPLETE")
    observed_durations = tuple(float(item["duration_s"]) for item in records)
    if observed_durations != TECHNICAL_DURATIONS_S:
        raise Gate28BError("Technical duration grid differs from frozen order.")
    _write_benchmark_csv(records)

    observations = []
    for record in records:
        output = Path(str(record["output_directory"]))
        rollout = output / "rollout.npz"
        observation = observe_rollout(
            rollout, source_label="GATE28B_ENGINEERING_ONLY_SEED_9101"
        )
        if observation["simulation_seed"] != TECHNICAL_SEED:
            raise Gate28BError("Technical rollout seed differs from 9101.")
        observations.append(
            {"duration_s": record["duration_s"], "observation": observation}
        )
    _write_json(
        RUN_OBSERVATIONS,
        {
            "schema_version": "gate28b-technical-run-observations-v1",
            "status": "COMPUTATIONAL_OBSERVATIONS_VALID_SOURCE_FIELDS_MISSING",
            "technical_seed": TECHNICAL_SEED,
            "scientific_evidence": False,
            "paper_assay_equivalence_established": False,
            "runs": observations,
        },
    )

    wall_per_step = [float(item["wall_clock_s"]) / int(item["steps"]) for item in records]
    bytes_per_step = [float(item["bytes_per_step"]) for item in records]
    median_wall = statistics.median(wall_per_step)
    maximum_wall = max(wall_per_step)
    median_bytes = statistics.median(bytes_per_step)
    maximum_bytes = max(bytes_per_step)
    scaling = {
        "schema_version": "gate28b-duration-scaling-summary-v1",
        "status": "ENGINEERING_EXTRAPOLATION_ONLY",
        "technical_seed": TECHNICAL_SEED,
        "completed_duration_s": list(observed_durations),
        "median_observed_wall_seconds_per_step": median_wall,
        "maximum_observed_wall_seconds_per_step": maximum_wall,
        "median_observed_bytes_per_step": median_bytes,
        "maximum_observed_bytes_per_step": maximum_bytes,
        "wall_seconds_per_step_min_max_ratio": max(wall_per_step) / min(wall_per_step),
        "bytes_per_step_min_max_ratio": max(bytes_per_step) / min(bytes_per_step),
        "nonlinear_resource_scaling_status": "REPORTED_WITHOUT_POSTHOC_ACCEPTANCE_THRESHOLD",
        "projected_15_minute_rollout_steps": PAPER_DURATION_STEPS,
        "projected_15_minute_wall_clock_s_median_scaling": median_wall
        * PAPER_DURATION_STEPS,
        "projected_15_minute_wall_clock_s_conservative_max_scaling": maximum_wall
        * PAPER_DURATION_STEPS,
        "projected_15_minute_storage_bytes_median_scaling": math.ceil(
            median_bytes * PAPER_DURATION_STEPS
        ),
        "projected_15_minute_storage_bytes_conservative_max_scaling": math.ceil(
            maximum_bytes * PAPER_DURATION_STEPS
        ),
        "direct_15_minute_execution_tested": False,
        "direct_15_minute_execution_status": "DIRECT_15_MINUTE_EXECUTION_NOT_TESTED",
        "extrapolation_validated": False,
    }
    _write_json(SCALING_SUMMARY, scaling)

    five_second_output = Path(str(records[-1]["output_directory"]))
    segmentation = _segmentation_analysis(five_second_output / "rollout.npz")
    if not segmentation["distance_consistent"] or not segmentation["pooled_mean_consistent"]:
        raise Gate28BError("Five-second segmentation consistency failed.")
    _write_json(SEGMENTATION_SUMMARY, segmentation)
    refresh_gate28b_package()
    return {
        "status": "GATE28B_VIRTUAL_ASSAY_ADAPTER_ENGINEERING_COMPLETE",
        "technical_jobs_completed": len(records),
        "scaling": scaling,
        "segmentation": segmentation,
    }


def _benchmark_rows() -> list[dict[str, str]]:
    if not BENCHMARK_CSV.is_file():
        return []
    with BENCHMARK_CSV.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _gate_status() -> tuple[str, int]:
    rows = _benchmark_rows()
    if len(rows) == MAX_TECHNICAL_JOBS and all(row.get("status") == "PASS" for row in rows):
        return "GATE28B_VIRTUAL_ASSAY_ADAPTER_ENGINEERING_COMPLETE", len(rows)
    if FIXTURE_RESULTS.is_file() and SCHEMA_AUDIT.is_file():
        return "GATE28B_ADAPTER_COMPLETE_DURATION_BENCHMARK_PENDING", 0
    return "GATE28B_INCOMPLETE", 0


def _manifest_document() -> dict[str, Any]:
    status, completed = _gate_status()
    unresolved = _json(SOURCE_REVIEW).get("unresolved_fields", [])
    return {
        "schema_version": "gate28b-generation2-manifest-v1",
        "status": status,
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "generation": 2,
        "gate": "28B",
        "Gate28A_closed": True,
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "first_assay": "RIEMENSPERGER_2011_OPEN_ARENA_V1",
        "assay_contract_sha256": ASSAY_CONTRACT_SHA256,
        "paper_assay_equivalence_established": False,
        "unresolved_source_fields": unresolved,
        "statistical_hierarchy_status": "RIEMENSPERGER_SPEED_STATISTICAL_HIERARCHY_REQUIRES_SOURCE_REVIEW",
        "synthetic_fixture_validation": _json(FIXTURE_RESULTS).get("status")
        if FIXTURE_RESULTS.is_file()
        else "NOT_RUN",
        "runtime_schema_audit": _json(SCHEMA_AUDIT).get("status")
        if SCHEMA_AUDIT.is_file()
        else "NOT_RUN",
        "technical_benchmark_authorized": True,
        "technical_benchmark_seed": TECHNICAL_SEED,
        "technical_jobs_planned": MAX_TECHNICAL_JOBS,
        "technical_jobs_completed": completed,
        "scientific_jobs_run": 0,
        "disease_jobs_run": 0,
        "calibration_run": False,
        "model_fitting_run": False,
        "retuning": False,
        "direct_15_minute_execution_tested": False,
        "segmented_biological_validity_claimed": False,
        "Gate24E_changed": False,
        "Gate25_changed": False,
        "Gate26_changed": False,
        "Gate28A_changed": False,
        "data_fabricated": False,
        "human_review_status": _json(SIGNOFF).get("status"),
    }


def _report_text(manifest: Mapping[str, Any]) -> str:
    rows = _benchmark_rows()
    benchmark_lines = (
        [
            "| Duration (s) | Steps | Wall clock (s) | Steps/s | Bytes | Bytes/step |",
            "|---:|---:|---:|---:|---:|---:|",
            *[
                f"| {row['duration_s']} | {row['steps']} | {float(row['wall_clock_s']):.3f} | "
                f"{float(row['steps_per_wall_second']):.3f} | {row['raw_output_bytes']} | "
                f"{float(row['bytes_per_step']):.3f} |"
                for row in rows
            ],
        ]
        if rows
        else ["No technical GPU benchmark has been executed yet."]
    )
    scaling_lines = ["Engineering extrapolation is not available before all four jobs pass."]
    if SCALING_SUMMARY.is_file():
        scaling = _json(SCALING_SUMMARY)
        scaling_lines = [
            f"- Median wall-clock projection: `{scaling['projected_15_minute_wall_clock_s_median_scaling']:.3f} s`.",
            f"- Conservative wall-clock projection: `{scaling['projected_15_minute_wall_clock_s_conservative_max_scaling']:.3f} s`.",
            f"- Median storage projection: `{scaling['projected_15_minute_storage_bytes_median_scaling']} bytes`.",
            f"- Conservative storage projection: `{scaling['projected_15_minute_storage_bytes_conservative_max_scaling']} bytes`.",
            "- Label: `ENGINEERING_EXTRAPOLATION_ONLY`.",
            "- Direct 15-minute execution: `DIRECT_15_MINUTE_EXECUTION_NOT_TESTED`.",
        ]
    return f"""# Gate28B virtual assay adapter report

**Status:** `{manifest['status']}`
**Human review:** `WAITING_GATE28B_HUMAN_REVIEW`

## 1. Purpose

Gate28B implements a disease-agnostic computational observation layer and,
when explicitly requested, benchmarks healthy rollout duration scaling. It
does not implement or validate a disease mechanism.

## 2. Relationship to Gate28A

The adapter references the human-closed Gate28A contracts without modifying
them. Gate24E, Gate25, Gate26, and Gate28A scientific content remains frozen.
The first track remains
`RIEMENSPERGER_2011_DOPAMINE_FUNCTIONAL_DEFICIENCY`; Pozo is not a future
sealed holdout and alpha-synuclein LOSO allocation remains unfrozen.

## 3. Assay observation architecture

Raw timestamps and thorax XY positions are mapped explicitly into an immutable
`TrajectoryData`. The `RIEMENSPERGER_2011_OPEN_ARENA_V1` adapter converts one
trajectory into one run-level observation. Disease parameters are absent from
the assay package.

## 4. Statistical hierarchy

The contract separates `LEVEL_0_FRAME`, `LEVEL_1_RUN`,
`LEVEL_2_COMPUTATIONAL_GROUP`, and `LEVEL_3_BIOLOGICAL_STUDY`. Frames, physics
steps, joints, and segments are not replicates. A unique simulation seed may
be a computational replicate. Per-run median framewise speed is not silently
equated to a paper group median.

## 5. Riemensperger adapter

The frozen source contract describes individual flight-disabled flies walking
in a horizontal open arena for 15 minutes. The adapter computes native virtual
distance, displacement, path-derived mean speed, and explicitly named median
framewise speed.

## 6. Known source gaps

The available primary PDF does not report the frame rate, movement threshold,
exclusion rule, or exact per-fly speed algorithm. Therefore:

- status: `RIEMENSPERGER_SPEED_STATISTICAL_HIERARCHY_REQUIRES_SOURCE_REVIEW`;
- paper assay equivalence: `false`;
- strongest claim: `VIRTUAL_ASSAY_ADAPTER_IMPLEMENTED`.

## 7. Metric definitions

- Interval speed is planar step distance divided by its positive time delta.
- Distance is the sum of interval distances.
- Displacement is the norm between first and last XY positions.
- Per-run mean speed is total distance divided by observed duration.
- Median framewise speed is descriptive and is not a paper-level alias.
- Threshold-dependent activity metrics remain
  `NOT_COMPUTED_MISSING_MOVEMENT_THRESHOLD`.

## 8. Window semantics

Windows have explicit start/end bounds. Boundary positions use exact samples
or deterministic linear interpolation. Out-of-range windows fail with
`OBSERVATION_WINDOW_EXCEEDS_ROLLOUT`; no silent truncation occurs.

## 9. Segmented aggregation

Contiguous segments share the boundary sample. Additive metrics are summed,
and rate metrics pool numerator/denominator. Median-of-medians is marked
`INVALID_AS_GENERAL_GLOBAL_MEDIAN_AGGREGATOR`. A segment is never a replicate.

## 10. Synthetic validation

Deterministic stationary, constant-speed, piecewise-speed, turning, irregular
timestamp, and invalid-NaN fixtures test analytic metrics and failure paths.
Current result: `{manifest['synthetic_fixture_validation']}`.

## 11. Runtime schema audit

Exactly one historical Gate26 healthy seed is inspected read-only. The audited
runtime keys map `timestamp_s` to canonical time and `thorax` to planar XY.
Unknown optional-field units remain `UNKNOWN_REQUIRES_RUNTIME_REVIEW`. Raw data
is neither changed nor copied into Git.

## 12. Technical duration benchmark

The only authorized execution is Healthy, no perturbation, technical seed
`9101`, and durations `0.5, 1.0, 2.0, 5.0 s`. This is engineering evidence,
not a scientific replicate.

{chr(10).join(benchmark_lines)}

## 13. 15-minute engineering extrapolation

{chr(10).join(scaling_lines)}

## 14. What is NOT validated

This gate does not reproduce the Riemensperger assay, validate a 15-minute
assay, reproduce Parkinson phenotypes, validate dopamine biology, establish
biological equivalence, calibrate parameters, fit a model, or run disease
jobs.

## 15. Implications for Gate29 and Gate31

Gate29 may review unresolved assay semantics and duration engineering evidence.
Gate31 must compare like with like, use scientific seeds distinct from `9101`,
and obtain a separately reviewed long-horizon protocol before replication.

## 16. Claim boundaries

Allowed: "Gate28B implements and validates a computational assay-observation
layer for virtual Drosophila locomotion and characterizes the engineering
scaling of longer healthy embodied rollouts." Segmented metric consistency
does not establish biological equivalence to one continuous 15-minute assay.

## 17. Human review status

The reviewer template remains `PENDING_HUMAN_REVIEW`; no field is auto-signed.
Exact next action after engineering completion:
`HUMAN_REVIEW_GATE28B_VIRTUAL_ASSAY_ADAPTER`.
"""


def _inventory_paths() -> list[Path]:
    paths = [
        ADAPTER_CONFIG,
        STATISTICAL_HIERARCHY,
        SEGMENTED_AGGREGATION,
        SOURCE_REVIEW,
        SOURCE_AMENDMENT,
        GATE28A_TEST_ALIGNMENT,
        SCHEMA_AUDIT,
        PREFLIGHT,
        FIXTURE_RESULTS,
        BENCHMARK_CSV,
        SCALING_SUMMARY,
        SEGMENTATION_SUMMARY,
        RUN_OBSERVATIONS,
        GATE28B_MANIFEST,
        REPORT,
        SIGNOFF,
        ROOT / "scripts/run_gate28b_virtual_assay_adapter.py",
        ROOT / "tests/test_gate28b_virtual_assay_adapter.py",
        ROOT / "tests/test_gate28a_gen2_scientific_contract.py",
    ]
    paths.extend(sorted((ROOT / "src/drosophila_pd_neural/assays").glob("*.py")))
    return sorted({path for path in paths if path.is_file()}, key=_relative)


def refresh_gate28b_package() -> dict[str, Any]:
    manifest = _manifest_document()
    _write_json(GATE28B_MANIFEST, manifest)
    _write_text(REPORT, _report_text(manifest))
    records = [
        {
            "path": _relative(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in _inventory_paths()
        if path not in {INVENTORY, CHECKSUMS}
    ]
    inventory = {
        "schema_version": "gate28b-reproducibility-inventory-v1",
        "status": "GATE28B_REPRODUCIBILITY_INVENTORY_COMPLETE",
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "raw_rollouts_committed": False,
        "file_count": len(records),
        "files": records,
    }
    _write_json(INVENTORY, inventory)
    checksum_records = {
        item["path"]: item["sha256"] for item in records
    }
    checksum_records[_relative(INVENTORY)] = sha256_file(INVENTORY)
    _write_text(
        CHECKSUMS,
        "\n".join(
            f"{digest}  {path}" for path, digest in sorted(checksum_records.items())
        ),
    )
    return manifest


def verify_gate28b_reproducibility() -> dict[str, Any]:
    inventory = _json(INVENTORY)
    records = inventory.get("files")
    if not isinstance(records, list) or inventory.get("file_count") != len(records):
        raise Gate28BError("Gate28B inventory record count is invalid.")
    observed: dict[str, str] = {}
    for line in CHECKSUMS.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", maxsplit=1)
        if relative in observed:
            raise Gate28BError(f"Duplicate Gate28B checksum path: {relative}")
        observed[relative] = digest
    expected = {str(item["path"]): str(item["sha256"]) for item in records}
    expected[_relative(INVENTORY)] = sha256_file(INVENTORY)
    if observed != dict(sorted(expected.items())):
        raise Gate28BError("Gate28B checksum manifest differs from inventory.")
    for relative, expected_sha in observed.items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_sha:
            raise Gate28BError(f"Gate28B reproducibility mismatch: {relative}")
    return {
        "status": "GATE28B_REPRODUCIBILITY_VERIFICATION_PASS",
        "verified_files": len(observed),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--validate-fixtures", action="store_true")
    modes.add_argument("--inspect-rollout", type=Path)
    modes.add_argument("--observe", type=Path)
    modes.add_argument("--benchmark-preflight", action="store_true")
    modes.add_argument("--execute-technical-duration-benchmark", action="store_true")
    modes.add_argument("--analyze-technical-benchmark", action="store_true")
    modes.add_argument("--verify-reproducibility", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--start-time-s", type=float, default=None)
    parser.add_argument("--end-time-s", type=float, default=None)
    parser.add_argument("--duration-s", type=float, default=None)
    return parser


def _window_from_args(args: argparse.Namespace) -> ObservationWindow | None:
    values = (args.start_time_s, args.end_time_s, args.duration_s)
    if all(value is None for value in values):
        return None
    if args.start_time_s is None:
        raise Gate28BError("Windowed observation requires --start-time-s.")
    if args.end_time_s is not None and args.duration_s is not None:
        raise Gate28BError("Use --end-time-s or --duration-s, not both.")
    if args.end_time_s is not None:
        return ObservationWindow(args.start_time_s, args.end_time_s)
    if args.duration_s is not None:
        return ObservationWindow.from_duration(args.start_time_s, args.duration_s)
    raise Gate28BError("Windowed observation requires an end or duration.")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        verify_gate28a_closure()
        verify_gate28a_immutable()
        if args.validate_fixtures:
            result = validate_synthetic_fixtures()
        elif args.inspect_rollout:
            result = inspect_rollout(args.inspect_rollout)
        elif args.observe:
            result = observe_rollout(args.observe, window=_window_from_args(args))
        elif args.benchmark_preflight:
            result = benchmark_preflight()
        elif args.execute_technical_duration_benchmark:
            result = execute_technical_duration_benchmark()
        elif args.analyze_technical_benchmark:
            result = analyze_technical_benchmark()
        elif args.verify_reproducibility:
            result = verify_gate28b_reproducibility()
        else:
            result = {
                "status": "NO_GPU_NO_SIMULATION",
                "message": "Select an explicit Gate28B mode; execution is never the default.",
            }
        if args.output:
            _write_json(args.output.resolve(), result)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    except (Gate28BError, AssayValidationError, ValueError, OSError) as exc:
        print(f"GATE28B_STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
