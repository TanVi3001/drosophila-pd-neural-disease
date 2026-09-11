"""Design and statically preflight the Gate29 canonical healthy pair.

This module deliberately separates design/preflight from execution.  The
canonical brain snapshot is an engineering input outside Git; the committed
manifests describe its identity without copying heavy neural data into the
repository.  No function in this module starts FlyGym, MuJoCo, CUDA, or a
scientific job during the design gate.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_INPUT_ROOT = ROOT.parent / "gate29_canonical_inputs/canonical_pair_v1"
SNAPSHOT_ROOT = CANONICAL_INPUT_ROOT / "brain_source"
CANONICAL_OUTPUT_ROOT = ROOT.parent / "gate29_technical_outputs/canonical_pair_v1"
GATE_ROOT = ROOT / "experiments/gate_29_neural_causal_trace"
MANIFEST_ROOT = GATE_ROOT / "manifests"
SOURCE_MANIFEST = MANIFEST_ROOT / "canonical_pair_brain_source_manifest.json"
DESIGN_PATH = MANIFEST_ROOT / "canonical_pair_design.json"
CONTEXT_PATH = MANIFEST_ROOT / "canonical_pair_execution_context.json"
AUTHORIZATION_PATH = MANIFEST_ROOT / "canonical_pair_execution_authorization.json"
FREEZE_PATH = MANIFEST_ROOT / "canonical_pair_execution_freeze.json"
SUPERSESSION_PATH = MANIFEST_ROOT / "trace_only_plan_supersession.json"

PAIR_ID = "GATE29_CANONICAL_PAIR_V1"
ATTEMPT = "01"
SEED = 9202
STEPS = 5000
DURATION_S = 0.5
TIMESTEP_S = 0.0001
STIMULUS = "p9"
CONDITION = "healthy"
DEVICE = "cuda"
ARTIFACT_PROFILE = "GATE24E_MEMORY_SAFE"
RUNTIME_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"
CHECKPOINT_SHA256 = "d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691"
RUNTIME_ROOT = ROOT.parent / "drosophila-pd-flygym-gate24-memorysafe-clean"
RUNTIME_PYTHON = ROOT.parent / "drosophila-pd-flygym/.venv/Scripts/python.exe"
SOURCE_ROOT = ROOT.parent / "drosophila-pd-neural-disease/external/fly-brain"
EXPECTED_REPOSITORY_HEAD = "a45fa582c6cff4541e69312f661d4d2f3349f64b"
SOURCE_MAIN_COMMIT = "004b9ee3c8938206e71b9908123f74cd0b7d2c97"
ALLOWED_SPEC_DIFFERENCES = ("instrumentation_enabled", "output_directory", "job_label")
FREEZE_RELATIVE_PATH = "experiments/gate_29_neural_causal_trace/manifests/canonical_pair_execution_freeze.json"
AUTHORIZATION_RELATIVE_PATH = "experiments/gate_29_neural_causal_trace/manifests/canonical_pair_execution_authorization.json"
CONTEXT_RELATIVE_PATH = "experiments/gate_29_neural_causal_trace/manifests/canonical_pair_execution_context.json"
DESIGN_RELATIVE_PATH = "experiments/gate_29_neural_causal_trace/manifests/canonical_pair_design.json"
GATE29_MANIFEST_RELATIVE_PATH = "experiments/gate_29_neural_causal_trace/manifests/gate29_manifest.json"
REPORT_RELATIVE_PATH = "docs/research_design/gate29_neural_causal_trace_report.md"
REPRO_INVENTORY_RELATIVE_PATH = "experiments/gate_29_neural_causal_trace/manifests/reproducibility_inventory.json"
REPRO_CHECKSUMS_RELATIVE_PATH = "experiments/gate_29_neural_causal_trace/manifests/checksums.sha256"
POST_FREEZE_METADATA_PATHS = frozenset({
    FREEZE_RELATIVE_PATH,
    AUTHORIZATION_RELATIVE_PATH,
    CONTEXT_RELATIVE_PATH,
    DESIGN_RELATIVE_PATH,
    GATE29_MANIFEST_RELATIVE_PATH,
    REPORT_RELATIVE_PATH,
    REPRO_INVENTORY_RELATIVE_PATH,
    REPRO_CHECKSUMS_RELATIVE_PATH,
    "experiments/gate_29_neural_causal_trace/manifests/canonical_pair_brain_source_manifest.json",
    "experiments/gate_29_neural_causal_trace/manifests/trace_only_plan_supersession.json",
})
TRACE_LINE_TARGETS = {
    317: "brain.step()",
    318: "decoder.update(brain.get_dn_spikes())",
    319: "drive = bridge.compute_drive(dt=float(simulation.timestep))",
    320: "controller_action = controller.step(",
    323: "action = controller_action",
    324: "if layer is not None:",
    325: "action = layer.apply_to_action(",
    338: "apply_locomotion_action(simulation, fly.name, action)",
    339: "simulation.step()",
    340: "recorder.record()",
    341: "if (step_index + 1) % max(steps // 5, 1) == 0:",
}
EXCLUDED_DIR_NAMES = {
    ".git", ".venv", "__pycache__", ".pytest_cache", "cache", "caches",
    "log", "logs", "video", "videos", "output", "outputs", "temporary",
}
EXCLUDED_FILE_NAMES = {"*.log", "*.mp4", "*.avi", "*.mov"}


class CanonicalPairError(RuntimeError):
    """Fail-closed canonical pair error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise CanonicalPairError(f"git command failed: {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def _logical_snapshot_path(relative_path: str) -> str:
    return f"gate29_canonical_inputs/canonical_pair_v1/brain_source/{relative_path}"


def _should_exclude(path: Path, source_root: Path) -> bool:
    relative_parts = set(path.relative_to(source_root).parts)
    if relative_parts & EXCLUDED_DIR_NAMES:
        return True
    return any(path.match(pattern) for pattern in EXCLUDED_FILE_NAMES)


def collect_source_files(source_root: Path = SOURCE_ROOT) -> list[Path]:
    if not source_root.is_dir():
        raise CanonicalPairError(f"canonical brain source is missing: {source_root}")
    files = [
        path for path in source_root.rglob("*")
        if path.is_file() and not _should_exclude(path, source_root)
    ]
    if not files:
        raise CanonicalPairError("canonical brain source contains no usable files")
    return sorted(files, key=lambda path: path.relative_to(source_root).as_posix())


def _role(relative_path: str) -> str:
    suffix = Path(relative_path).suffix.lower()
    if suffix == ".py":
        return "CODE"
    if suffix in {".pt", ".pth", ".pkl", ".pickle"}:
        return "MODEL" if suffix in {".pt", ".pth"} else "AUXILIARY"
    if suffix in {".csv", ".tsv", ".parquet", ".feather"}:
        return "CONNECTIVITY"
    if suffix in {".json", ".md", ".txt", ".yaml", ".yml"} or Path(relative_path).name.upper() == "LICENSE":
        return "METADATA"
    return "AUXILIARY"


def _tree_fingerprint(records: Iterable[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        line = (
            str(record["relative_path"]).encode("utf-8")
            + b"\0"
            + str(record["sha256"]).encode("ascii")
            + b"\0"
            + str(record["size_bytes"]).encode("ascii")
            + b"\n"
        )
        digest.update(line)
    return digest.hexdigest()


def build_snapshot_manifest(source_root: Path = SOURCE_ROOT, snapshot_root: Path = SNAPSHOT_ROOT) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for source_path in collect_source_files(source_root):
        relative = source_path.relative_to(source_root).as_posix()
        snapshot_path = snapshot_root / Path(relative)
        if not snapshot_path.is_file():
            raise CanonicalPairError(f"snapshot file missing: {relative}")
        source_sha = _sha256(source_path)
        snapshot_sha = _sha256(snapshot_path)
        if source_sha != snapshot_sha:
            raise CanonicalPairError(f"snapshot hash mismatch: {relative}")
        if source_path.stat().st_size != snapshot_path.stat().st_size:
            raise CanonicalPairError(f"snapshot size mismatch: {relative}")
        records.append(
            {
                "relative_path": relative,
                "sha256": snapshot_sha,
                "size_bytes": snapshot_path.stat().st_size,
                "source_original_path": f"external/fly-brain/{relative}",
                "snapshot_path": _logical_snapshot_path(relative),
                "role": _role(relative),
            }
        )
    records.sort(key=lambda item: item["relative_path"])
    total_size = sum(int(item["size_bytes"]) for item in records)
    return {
        "schema_version": "gate29-canonical-brain-source-manifest-v1",
        "status": "CANONICAL_SOURCE_FROZEN",
        "pair_id": PAIR_ID,
        "source_root_logical": "external/fly-brain",
        "snapshot_root_logical": "gate29_canonical_inputs/canonical_pair_v1/brain_source",
        "source_snapshot_outside_git": True,
        "file_count": len(records),
        "total_size_bytes": total_size,
        "fingerprint_encoding": "UTF-8(relative_path) NUL ASCII(sha256) NUL ASCII(size_bytes) LF; sorted relative_path",
        "canonical_brain_source_tree_sha256": _tree_fingerprint(records),
        "checkpoint_relative_path": "data/plastic_weights.pt",
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "files": records,
    }


def verify_frozen_snapshot(snapshot_root: Path = SNAPSHOT_ROOT, manifest: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Verify only the immutable snapshot against the committed manifest.

    This is the execution-time check.  It intentionally never reads
    ``SOURCE_ROOT``; the mutable original checkout is design-time input only.
    """

    manifest = manifest or _json(SOURCE_MANIFEST)
    expected_records = list(manifest.get("files", []))
    expected = {record.get("relative_path"): record for record in expected_records}
    if len(expected) != len(expected_records):
        return {"status": "BLOCKED", "blockers": ["canonical source manifest has duplicate paths"]}
    actual_paths = {
        path.relative_to(snapshot_root).as_posix()
        for path in snapshot_root.rglob("*")
        if path.is_file()
    } if snapshot_root.is_dir() else set()
    missing = sorted(set(expected) - actual_paths)
    unexpected = sorted(actual_paths - set(expected))
    blockers = [f"snapshot missing:{path}" for path in missing]
    blockers.extend(f"snapshot unexpected:{path}" for path in unexpected)
    observed_records: list[dict[str, Any]] = []
    if not blockers:
        for relative in sorted(expected):
            path = snapshot_root / relative
            observed_sha = _sha256(path)
            observed_size = path.stat().st_size
            record = expected[relative]
            if observed_sha != record.get("sha256"):
                blockers.append(f"snapshot hash mismatch:{relative}")
            if observed_size != record.get("size_bytes"):
                blockers.append(f"snapshot size mismatch:{relative}")
            observed_records.append({"relative_path": relative, "sha256": observed_sha, "size_bytes": observed_size})
    tree_sha = _tree_fingerprint(observed_records) if not blockers else None
    if tree_sha != manifest.get("canonical_brain_source_tree_sha256"):
        blockers.append("GATE29_CANONICAL_SOURCE_MUTATION_DETECTED")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "blockers": blockers,
        "file_count": len(actual_paths),
        "expected_file_count": len(expected),
        "total_size_bytes": sum(item["size_bytes"] for item in observed_records),
        "canonical_brain_source_tree_sha256": tree_sha,
        "source_snapshot_execution_input": True,
        "mutable_original_source_execution_input": False,
    }


def _runtime_versions() -> dict[str, Any]:
    if not RUNTIME_PYTHON.is_file():
        raise CanonicalPairError(f"runtime Python is missing: {RUNTIME_PYTHON}")
    code = (
        "import importlib.metadata as m, json, sys; "
        "names=['torch','flygym','mujoco']; "
        "out={'python':sys.version.split()[0]}; "
        "out.update({n: (m.version(n) if any(d.metadata.get('Name','').lower()==n for d in m.distributions()) else None) for n in names}); "
        "print(json.dumps(out, sort_keys=True))"
    )
    result = subprocess.run([str(RUNTIME_PYTHON), "-c", code], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise CanonicalPairError(f"runtime version query failed: {result.stderr.strip()}")
    return json.loads(result.stdout.strip())


def _sanitized_environment(snapshot_manifest: Mapping[str, Any], repository_head: str) -> dict[str, Any]:
    return {
        "python_executable": "drosophila-pd-flygym/.venv/Scripts/python.exe",
        "pythonpath": os.environ.get("PYTHONPATH"),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "pytorch_cuda_alloc_conf": os.environ.get("PYTORCH_CUDA_ALLOC_CONF"),
        "cwd_logical": "repository root",
        "runtime_root_logical": "drosophila-pd-flygym-gate24-memorysafe-clean",
        "snapshot_root_logical": snapshot_manifest["snapshot_root_logical"],
        "runtime_commit": RUNTIME_COMMIT,
        "execution_code_head": repository_head,
        "historical_design_base_head": EXPECTED_REPOSITORY_HEAD,
        "seed": SEED,
        "steps": STEPS,
        "stimulus": STIMULUS,
        "device": DEVICE,
        "artifact_profile": ARTIFACT_PROFILE,
    }


def _job_spec(*, instrumentation_enabled: bool, output_directory: str, job_label: str, snapshot_manifest: Mapping[str, Any], repository_head: str) -> dict[str, Any]:
    return {
        "pair_id": PAIR_ID,
        "attempt": ATTEMPT,
        "job_label": job_label,
        "instrumentation_enabled": instrumentation_enabled,
        "output_directory": output_directory,
        "condition": CONDITION,
        "seed": SEED,
        "steps": STEPS,
        "duration_s": DURATION_S,
        "timestep_s": TIMESTEP_S,
        "stimulus": STIMULUS,
        "device": DEVICE,
        "artifact_profile": ARTIFACT_PROFILE,
        "runtime_commit": RUNTIME_COMMIT,
        "execution_code_head": repository_head,
        "historical_design_base_head": EXPECTED_REPOSITORY_HEAD,
        "brain_source_tree_sha256": snapshot_manifest["canonical_brain_source_tree_sha256"],
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "retry": False,
    }


def normalize_job_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in spec.items() if key not in ALLOWED_SPEC_DIFFERENCES}


def verify_job_pair_equivalence(baseline: Mapping[str, Any], trace: Mapping[str, Any]) -> dict[str, Any]:
    baseline_normalized = normalize_job_spec(baseline)
    trace_normalized = normalize_job_spec(trace)
    mismatches = sorted(
        key for key in set(baseline_normalized) | set(trace_normalized)
        if baseline_normalized.get(key) != trace_normalized.get(key)
    )
    return {
        "status": "MATCH" if not mismatches else "GATE29_CANONICAL_PAIR_CONTEXT_MISMATCH",
        "allowed_differences": list(ALLOWED_SPEC_DIFFERENCES),
        "mismatches": mismatches,
        "baseline_normalized": baseline_normalized,
        "trace_normalized": trace_normalized,
    }


def verify_trace_line_mapping(runtime_root: Path = RUNTIME_ROOT) -> dict[str, Any]:
    path = runtime_root / "scripts/run_brain_body_rollout.py"
    if not path.is_file():
        return {"status": "GATE29_TRACE_LINE_MAPPING_STALE", "path": "runtime/scripts/run_brain_body_rollout.py", "mismatches": ["runtime runner missing"]}
    lines = path.read_text(encoding="utf-8").splitlines()
    mismatches = []
    observed = {}
    for number, expected in TRACE_LINE_TARGETS.items():
        actual = lines[number - 1].strip() if len(lines) >= number else None
        observed[str(number)] = actual
        if actual != expected:
            mismatches.append({"line": number, "expected": expected, "actual": actual})
    return {
        "status": "PASS" if not mismatches else "GATE29_TRACE_LINE_MAPPING_STALE",
        "source_path": "runtime/scripts/run_brain_body_rollout.py",
        "runtime_commit": RUNTIME_COMMIT,
        "targets": {str(key): value for key, value in TRACE_LINE_TARGETS.items()},
        "observed": observed,
        "mismatches": mismatches,
        "runtime_verified_edge_count": 0,
        "source_code_verified_edge_count": 11,
    }


def _runtime_state() -> dict[str, Any]:
    if not RUNTIME_ROOT.is_dir():
        return {"status": "BLOCKED", "head": None, "dirty": None, "blockers": ["runtime root missing"]}
    head = _git(RUNTIME_ROOT, "rev-parse", "HEAD")
    dirty = _git(RUNTIME_ROOT, "status", "--porcelain")
    blockers = []
    if head != RUNTIME_COMMIT:
        blockers.append("runtime commit mismatch")
    if dirty:
        blockers.append("runtime worktree dirty")
    return {"status": "PASS" if not blockers else "BLOCKED", "head": head, "dirty": bool(dirty), "blockers": blockers}


def _execution_code_freeze_state() -> dict[str, Any]:
    """Validate the immutable execution-code layer and post-freeze metadata."""

    if not FREEZE_PATH.is_file():
        return {
            "status": "GATE29_CANONICAL_PAIR_EXECUTION_CODE_FREEZE_MISSING",
            "blockers": ["canonical_pair_execution_freeze.json is missing"],
            "execution_code_head": None,
        }
    freeze = _json(FREEZE_PATH)
    blockers: list[str] = []
    required = {
        "schema_version": "gate29-canonical-pair-execution-freeze-v1",
        "status": "GATE29_CANONICAL_PAIR_EXECUTION_FROZEN",
        "pair_id": PAIR_ID,
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "seed": SEED,
        "jobs": 2,
        "condition": CONDITION,
        "steps": STEPS,
        "duration_s": DURATION_S,
        "timestep_s": TIMESTEP_S,
        "stimulus": STIMULUS,
        "runtime_commit": RUNTIME_COMMIT,
        "brain_source_tree_sha256": "cb01029b77112c39a11554aeb1c6610de65439b822b291e62830a3c566e2ed08",
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "comparison_rtol": 0.0,
        "comparison_atol": 1e-12,
        "discrete_comparison": "EXACT",
        "automatic_retry": False,
        "scientific_execution": False,
        "disease_execution": False,
        "calibration": False,
        "fitting": False,
        "retuning": False,
        "dopamine": False,
        "human_authorization_required": True,
        "execution_status": "NOT_EXECUTED",
    }
    for key, expected in required.items():
        if freeze.get(key) != expected:
            blockers.append(f"freeze field mismatch:{key}")
    execution_code_head = freeze.get("execution_code_head")
    if not isinstance(execution_code_head, str) or not re.fullmatch(r"[0-9a-f]{40}", execution_code_head):
        blockers.append("freeze execution_code_head is invalid")
        execution_code_head = None
    current_head = _git(ROOT, "rev-parse", "HEAD")
    dirty = _git(ROOT, "status", "--porcelain")
    if dirty:
        blockers.append("GATE29_CANONICAL_PAIR_EXECUTION_DIRTY_WORKTREE")
    if execution_code_head:
        ancestor = subprocess.run(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", execution_code_head, current_head],
            capture_output=True,
            check=False,
        )
        if ancestor.returncode != 0:
            blockers.append("GATE29_CANONICAL_PAIR_EXECUTION_CODE_HEAD_NOT_ANCESTOR")
        changed = _git(ROOT, "diff", "--name-only", f"{execution_code_head}..{current_head}").splitlines()
        unexpected = sorted(set(changed) - POST_FREEZE_METADATA_PATHS)
        if unexpected:
            blockers.append("GATE29_CANONICAL_PAIR_EXECUTION_CODE_DRIFT")
            blockers.extend(f"post-freeze source/config changed:{path}" for path in unexpected)
    return {
        "status": "PASS" if not blockers else "GATE29_CANONICAL_PAIR_EXECUTION_CODE_DRIFT",
        "blockers": blockers,
        "execution_code_head": execution_code_head,
        "current_head": current_head,
        "worktree_clean": not bool(dirty),
        "allowed_post_freeze_paths": sorted(POST_FREEZE_METADATA_PATHS),
    }


def _snapshot_state(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return verify_frozen_snapshot(SNAPSHOT_ROOT, manifest)


def _create_output_skeleton() -> None:
    for name in ("baseline", "trace", "logs", "execution_state"):
        (CANONICAL_OUTPUT_ROOT / name).mkdir(parents=True, exist_ok=True)
    _write_json(
        CANONICAL_OUTPUT_ROOT / "execution_state/status.json",
        {
            "schema_version": "gate29-canonical-pair-execution-state-v1",
            "state": "NOT_EXECUTED",
            "pair_id": PAIR_ID,
            "attempt": ATTEMPT,
            "scientific_jobs": 0,
            "gpu_execution": False,
            "simulation_execution": False,
        },
    )


def _supersession_manifest() -> dict[str, Any]:
    return {
        "schema_version": "gate29-trace-only-plan-supersession-v1",
        "status": "GATE29_TRACE_ONLY_PLAN_SUPERSEDED",
        "reason": "HISTORICAL_BASELINE_SOURCE_NOT_CRYPTOGRAPHICALLY_REPRODUCIBLE",
        "historical_seed": 9201,
        "historical_baseline_preserved": True,
        "historical_baseline_scientific_evidence": False,
        "old_trace_only_execution_allowed": False,
        "replacement_strategy": "NEW_CANONICAL_PAIRED_ENGINEERING_RUN",
    }


def design_canonical_pair() -> dict[str, Any]:
    current_head = _git(ROOT, "rev-parse", "HEAD")
    # The task start was verified at EXPECTED_REPOSITORY_HEAD.  Once the
    # design implementation itself is edited, only the declared Gate29 files
    # may be dirty; unrelated worktree changes remain a hard stop.
    allowed_dirty = {
        "scripts/run_gate29_canonical_pair.py",
        "scripts/run_gate29_neural_causal_trace.py",
        "tests/test_gate29_canonical_pair.py",
        "tests/test_gate29_neural_causal_trace.py",
        "docs/research_design/gate29_neural_causal_trace_report.md",
        "experiments/gate_29_neural_causal_trace/manifests/gate29_manifest.json",
    }
    dirty_paths: set[str] = set()
    for line in _git(ROOT, "status", "--porcelain", "--untracked-files=all").splitlines():
        if not line.strip():
            continue
        # _git() strips leading whitespace from the complete stdout string,
        # so the first porcelain record can start at column zero.
        dirty_paths.add(line[2:].strip() if line[:2] != "??" else line[3:].strip())
    unexpected = sorted(dirty_paths - allowed_dirty)
    if unexpected:
        raise CanonicalPairError(f"unrelated worktree changes block design: {unexpected}")
    runtime_state = _runtime_state()
    if runtime_state["status"] != "PASS":
        raise CanonicalPairError(f"runtime is not clean/locked: {runtime_state}")
    if SNAPSHOT_ROOT.exists():
        raise CanonicalPairError("canonical snapshot already exists; refusing to overwrite it")
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)
    for source_path in collect_source_files(SOURCE_ROOT):
        relative = source_path.relative_to(SOURCE_ROOT)
        destination = SNAPSHOT_ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        if _sha256(source_path) != _sha256(destination):
            raise CanonicalPairError(f"copy verification failed: {relative.as_posix()}")
        try:
            destination.chmod(0o444)
        except OSError:
            pass
    snapshot_manifest = build_snapshot_manifest(SOURCE_ROOT, SNAPSHOT_ROOT)
    checkpoint = SNAPSHOT_ROOT / "data/plastic_weights.pt"
    if _sha256(checkpoint) != CHECKPOINT_SHA256:
        raise CanonicalPairError("canonical checkpoint SHA256 mismatch")
    _write_json(SOURCE_MANIFEST, snapshot_manifest)
    baseline = _job_spec(instrumentation_enabled=False, output_directory="baseline", job_label="CANONICAL_UNTRACED_HEALTHY_BASELINE", snapshot_manifest=snapshot_manifest, repository_head=current_head)
    trace = _job_spec(instrumentation_enabled=True, output_directory="trace", job_label="CANONICAL_TRACE_INSTRUMENTED_HEALTHY", snapshot_manifest=snapshot_manifest, repository_head=current_head)
    equivalence = verify_job_pair_equivalence(baseline, trace)
    if equivalence["status"] != "MATCH":
        raise CanonicalPairError(equivalence["status"])
    environment = _sanitized_environment(snapshot_manifest, current_head)
    context = {
        "schema_version": "gate29-canonical-pair-execution-context-v1",
        "status": "FROZEN_COMMON_CONTEXT",
        "pair_id": PAIR_ID,
        "attempt": ATTEMPT,
        "common": {
            "condition": CONDITION,
            "seed": SEED,
            "steps": STEPS,
            "duration_s": DURATION_S,
            "timestep_s": TIMESTEP_S,
            "stimulus": STIMULUS,
            "device": DEVICE,
            "artifact_profile": ARTIFACT_PROFILE,
            "runtime_commit": RUNTIME_COMMIT,
            "checkpoint_sha256": CHECKPOINT_SHA256,
            "brain_source_tree_sha256": snapshot_manifest["canonical_brain_source_tree_sha256"],
        },
        "jobs": {"baseline": baseline, "trace": trace},
        "allowed_differences": list(ALLOWED_SPEC_DIFFERENCES),
        "normalized_specs_match": equivalence["status"] == "MATCH",
        "normalized_spec_comparison": equivalence,
        "sanitized_environment": environment,
        "runtime_versions": _runtime_versions(),
    }
    _write_json(CONTEXT_PATH, context)
    _write_json(SUPERSESSION_PATH, _supersession_manifest())
    _write_json(
        AUTHORIZATION_PATH,
        {
            "schema_version": "gate29-canonical-pair-execution-authorization-v1",
            "status": "WAITING_GATE29_CANONICAL_PAIR_HUMAN_AUTHORIZATION",
            "authorized": False,
            "authorized_execution_code_head": "",
            "authorized_freeze_commit": "",
            "authorized_pair_id": PAIR_ID,
            "authorized_seed": SEED,
            "authorized_jobs": 2,
            "authorized_brain_source_tree_sha256": snapshot_manifest["canonical_brain_source_tree_sha256"],
            "authorized_runtime_commit": RUNTIME_COMMIT,
            "baseline_job_authorized": False,
            "trace_job_authorized": False,
            "automatic_retry_authorized": False,
            "scientific_execution_authorized": False,
            "disease_execution_authorized": False,
            "calibration_authorized": False,
            "fitting_authorized": False,
            "retuning_authorized": False,
            "dopamine_authorized": False,
            "reviewer": "",
            "review_date": "",
            "no_auto_sign": True,
        },
    )
    design = {
        "schema_version": "gate29-canonical-pair-design-v1",
        "status": "COMPLETE",
        "execution_code_head": current_head,
        "historical_design_base_head": EXPECTED_REPOSITORY_HEAD,
        "pair_id": PAIR_ID,
        "attempt": ATTEMPT,
        "scope": "HEALTHY_ENGINEERING_NONPERTURBATION_ONLY",
        "historical_seed_9201_preserved": True,
        "seed_9202_is_not_scientific_replicate": True,
        "seed_9202_is_not_seed_replacement_for_scientific_result": True,
        "historical_seed_9201_result_changed": False,
        "jobs": [baseline["job_label"], trace["job_label"]],
        "job_count": 2,
        "condition": CONDITION,
        "steps": STEPS,
        "duration_s": DURATION_S,
        "timestep_s": TIMESTEP_S,
        "stimulus": STIMULUS,
        "device": DEVICE,
        "runtime_commit": RUNTIME_COMMIT,
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "brain_source_tree_sha256": snapshot_manifest["canonical_brain_source_tree_sha256"],
        "brain_source_file_count": snapshot_manifest["file_count"],
        "brain_source_total_size_bytes": snapshot_manifest["total_size_bytes"],
        "common_runner": True,
        "common_runner_function": "_run_canonical_pair_job",
        "common_pipeline_components": [
            "brain_loader",
            "neural_step",
            "decoder",
            "brain_body_bridge",
            "controller",
            "cpg",
            "stimulus",
            "physics",
            "recorder",
            "memory_safe_export",
        ],
        "only_semantic_difference": "TRACE_INSTRUMENTATION_ENABLED",
        "allowed_spec_differences": list(ALLOWED_SPEC_DIFFERENCES),
        "comparison_rtol": 0.0,
        "comparison_atol": 1e-12,
        "discrete_comparison": "EXACT",
        "automatic_retry": False,
        "execution_state_machine": [
            "NOT_EXECUTED",
            "BASELINE_RUNNING",
            "BASELINE_COMPLETE",
            "TRACE_RUNNING",
            "PAIR_COMPLETE",
        ],
        "trace_scope": "AUDITED_RUNTIME_SCRIPT_ONLY",
        "runtime_trace_line_events_target": 53,
        "non_runtime_line_events_target": 0,
        "minimum_aliases": {
            "timestamp_s": "post_time_s",
            "thorax": "post_thorax_position_mm",
            "joint_positions": "post_joint_positions",
            "actuator_position": "post_actuator_position",
            "contact_found": "post_contact_found",
        },
        "no_gpu_execution": True,
        "no_simulation_execution": True,
        "scientific_jobs": 0,
        "disease_jobs": 0,
        "calibration": False,
        "fitting": False,
        "retuning": False,
        "dopamine": False,
        "runtime_line_mapping": verify_trace_line_mapping(RUNTIME_ROOT),
        "authorization_status": "WAITING_GATE29_CANONICAL_PAIR_HUMAN_AUTHORIZATION",
        "execution_status": "NOT_EXECUTED",
    }
    _write_json(DESIGN_PATH, design)
    _create_output_skeleton()
    return design


def canonical_pair_preflight(*, allow_authorized: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    if not SOURCE_MANIFEST.is_file() or not DESIGN_PATH.is_file() or not CONTEXT_PATH.is_file() or not AUTHORIZATION_PATH.is_file():
        blockers.append("canonical pair design artifacts are incomplete")
        return {"status": "GATE29_CANONICAL_PAIR_PREFLIGHT_BLOCKED", "blockers": blockers, "gpu_execution": False, "simulation_execution": False}
    manifest = _json(SOURCE_MANIFEST)
    design = _json(DESIGN_PATH)
    context = _json(CONTEXT_PATH)
    authorization = _json(AUTHORIZATION_PATH)
    snapshot = _snapshot_state(manifest)
    blockers.extend(snapshot.get("blockers", []))
    freeze_state = _execution_code_freeze_state()
    if freeze_state["status"] != "PASS":
        blockers.extend(freeze_state.get("blockers", []))
    runtime = _runtime_state()
    blockers.extend(runtime.get("blockers", []))
    mapping = verify_trace_line_mapping(RUNTIME_ROOT)
    if mapping["status"] != "PASS":
        blockers.append("GATE29_TRACE_LINE_MAPPING_STALE")
    equivalence = context.get("normalized_spec_comparison", {})
    if equivalence.get("status") != "MATCH":
        blockers.append("GATE29_CANONICAL_PAIR_CONTEXT_MISMATCH")
    if not allow_authorized and authorization.get("authorized") is not False:
        blockers.append("canonical pair authorization must remain pending in design gate")
    if design.get("status") != "COMPLETE" or design.get("execution_status") != "NOT_EXECUTED":
        blockers.append("canonical pair design status is not complete/not executed")
    if design.get("runtime_verified_edge_count", 0) != 0:
        blockers.append("runtime edge verification must remain zero before execution")
    disk = shutil.disk_usage(CANONICAL_OUTPUT_ROOT.parent if CANONICAL_OUTPUT_ROOT.parent.exists() else ROOT)
    required = 2 * 120 * 1024 * 1024 + 120 * 1024 * 1024 + 16 * 1024 * 1024 + 5 * 1024**3
    if disk.free <= required:
        blockers.append("insufficient storage reservation for future pair")
    output_artifacts = [path for path in (CANONICAL_OUTPUT_ROOT / name for name in ("baseline", "trace", "logs")) if path.is_dir() and any(path.rglob("*"))]
    if output_artifacts:
        blockers.append("canonical output directory already contains execution artifacts")
    return {
        "status": "GATE29_CANONICAL_PAIR_PREFLIGHT_READY_FOR_HUMAN_AUTHORIZATION" if not blockers else "GATE29_CANONICAL_PAIR_PREFLIGHT_BLOCKED",
        "blockers": blockers,
        "pair_id": PAIR_ID,
        "attempt": ATTEMPT,
        "seed": SEED,
        "jobs": 2,
        "authorization": authorization,
        "snapshot": snapshot,
        "execution_code_freeze": freeze_state,
        "runtime": runtime,
        "runtime_line_mapping": mapping,
        "storage": {"free_bytes": disk.free, "required_bytes": required, "capacity_rule": "free_bytes > required_bytes"},
        "gpu_telemetry": "DEFERRED_TO_EXECUTION_PREFLIGHT",
        "gpu_execution": False,
        "simulation_execution": False,
        "scientific_jobs": 0,
        "disease_jobs": 0,
        "holdout_role": "NOT_APPLICABLE_GATE29_ENGINEERING_PAIR",
        "external_biological_evidence_accessed": False,
        "external_biological_holdout_evaluated": False,
    }


def _validate_authorization(authorization: Mapping[str, Any]) -> None:
    if authorization.get("authorized") is not True:
        raise CanonicalPairError("WAITING_GATE29_CANONICAL_PAIR_HUMAN_AUTHORIZATION")
    if authorization.get("schema_version") != "gate29-canonical-pair-execution-authorization-v1":
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_AUTHORIZATION_SCHEMA_INVALID")
    if authorization.get("status") != "GATE29_CANONICAL_PAIR_HUMAN_AUTHORIZED":
        raise CanonicalPairError("WAITING_GATE29_CANONICAL_PAIR_HUMAN_AUTHORIZATION")
    if authorization.get("authorized_pair_id") != PAIR_ID or authorization.get("authorized_seed") != SEED:
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_AUTHORIZATION_IDENTITY_MISMATCH")
    if authorization.get("authorized_jobs") != 2:
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_AUTHORIZATION_JOB_COUNT_MISMATCH")
    if authorization.get("baseline_job_authorized") is not True or authorization.get("trace_job_authorized") is not True:
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_AUTHORIZATION_SCOPE_INVALID")
    if authorization.get("automatic_retry_authorized") is not False:
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_RETRY_NOT_ALLOWED")
    if any(authorization.get(key) is not False for key in (
        "scientific_execution_authorized",
        "disease_execution_authorized",
        "calibration_authorized",
        "fitting_authorized",
        "retuning_authorized",
        "dopamine_authorized",
    )):
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_SCIENTIFIC_SCOPE_INVALID")
    reviewer = authorization.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_REVIEWER_REQUIRED")
    review_date = authorization.get("review_date")
    if not isinstance(review_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", review_date):
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_REVIEW_DATE_REQUIRED")
    if authorization.get("no_auto_sign") is not True:
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_NO_AUTO_SIGN_REQUIRED")
    manifest = _json(SOURCE_MANIFEST)
    if authorization.get("authorized_brain_source_tree_sha256") != manifest["canonical_brain_source_tree_sha256"]:
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_SOURCE_FINGERPRINT_MISMATCH")
    if authorization.get("authorized_runtime_commit") != RUNTIME_COMMIT:
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_RUNTIME_COMMIT_MISMATCH")
    freeze_state = _execution_code_freeze_state()
    if freeze_state["status"] != "PASS":
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_EXECUTION_CODE_DRIFT")
    freeze = _json(FREEZE_PATH)
    if authorization.get("authorized_execution_code_head") != freeze["execution_code_head"]:
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_EXECUTION_CODE_HEAD_MISMATCH")
    freeze_commit = authorization.get("authorized_freeze_commit")
    if not isinstance(freeze_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", freeze_commit):
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_FREEZE_COMMIT_REQUIRED")
    if _git(ROOT, "cat-file", "-t", freeze_commit) != "commit":
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_FREEZE_COMMIT_INVALID")
    current_head = _git(ROOT, "rev-parse", "HEAD")
    ancestor = subprocess.run(
        ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", freeze_commit, current_head],
        capture_output=True,
        check=False,
    )
    if ancestor.returncode != 0:
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_FREEZE_COMMIT_NOT_ANCESTOR")
    freeze_blob = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "blob", f"{freeze_commit}:{FREEZE_RELATIVE_PATH}"],
        capture_output=True,
        check=False,
    )
    if freeze_blob.returncode != 0 or hashlib.sha256(freeze_blob.stdout).hexdigest() != _sha256(FREEZE_PATH):
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_FREEZE_CONTENT_MISMATCH")


def _job_commands() -> dict[str, list[str]]:
    runtime_script = RUNTIME_ROOT / "scripts/run_brain_body_rollout.py"
    baseline_output = CANONICAL_OUTPUT_ROOT / "baseline"
    trace_output = CANONICAL_OUTPUT_ROOT / "trace"
    baseline = [
        str(RUNTIME_PYTHON), str(runtime_script),
        "--brain-root", str(SNAPSHOT_ROOT), "--brain-python", str(RUNTIME_PYTHON),
        "--condition", CONDITION, "--seed", str(SEED), "--steps", str(STEPS),
        "--stimulus", STIMULUS, "--device", DEVICE, "--output", str(baseline_output),
        "--artifact-profile", ARTIFACT_PROFILE,
    ]
    trace = [
        str(RUNTIME_PYTHON), str(ROOT / "scripts/run_gate29_neural_causal_trace.py"),
        "--internal-trace", "--internal-trace-seed", str(SEED),
        "--runtime-root", str(RUNTIME_ROOT), "--brain-root", str(SNAPSHOT_ROOT),
        "--runtime-python", str(RUNTIME_PYTHON), "--output-root", str(trace_output),
    ]
    return {"baseline": baseline, "trace": trace}


def _run_canonical_pair_job(*, instrumentation_enabled: bool, output: Path, authorization: Mapping[str, Any]) -> dict[str, Any]:
    """Run one member of the authorized pair with no retry or hidden mutation."""

    _validate_authorization(authorization)
    key = "trace" if instrumentation_enabled else "baseline"
    command = _job_commands()[key]
    output.mkdir(parents=True, exist_ok=True)
    log = CANONICAL_OUTPUT_ROOT / "logs" / f"{key}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise CanonicalPairError(f"GATE29_CANONICAL_PAIR_{key.upper()}_FAILED")
    if not any(output.rglob("*")):
        raise CanonicalPairError(f"GATE29_CANONICAL_PAIR_{key.upper()}_NO_ARTIFACTS")
    return {"job": key, "returncode": result.returncode, "log": str(log), "instrumentation_enabled": instrumentation_enabled}


def execute_authorized_canonical_pair() -> dict[str, Any]:
    authorization = _json(AUTHORIZATION_PATH)
    _validate_authorization(authorization)
    preflight = canonical_pair_preflight(allow_authorized=True)
    if preflight["status"] != "GATE29_CANONICAL_PAIR_PREFLIGHT_READY_FOR_HUMAN_AUTHORIZATION":
        raise CanonicalPairError(json.dumps(preflight, sort_keys=True))
    state_path = CANONICAL_OUTPUT_ROOT / "execution_state/status.json"
    state = _json(state_path) if state_path.is_file() else {}
    if state.get("state") != "NOT_EXECUTED":
        raise CanonicalPairError("GATE29_CANONICAL_PAIR_ALREADY_EXECUTED_OR_TERMINAL")
    for name in ("baseline", "trace", "logs"):
        directory = CANONICAL_OUTPUT_ROOT / name
        if any(directory.rglob("*")):
            raise CanonicalPairError("GATE29_CANONICAL_PAIR_OUTPUT_ALREADY_CONTAINS_ARTIFACTS")
    try:
        _write_json(state_path, {**state, "state": "BASELINE_RUNNING"})
        baseline = _run_canonical_pair_job(instrumentation_enabled=False, output=CANONICAL_OUTPUT_ROOT / "baseline", authorization=authorization)
        _write_json(state_path, {**state, "state": "BASELINE_COMPLETE", "baseline": baseline})
        _write_json(state_path, {**state, "state": "TRACE_RUNNING", "baseline": baseline})
        trace = _run_canonical_pair_job(instrumentation_enabled=True, output=CANONICAL_OUTPUT_ROOT / "trace", authorization=authorization)
    except CanonicalPairError as exc:
        current = _json(state_path) if state_path.is_file() else {}
        terminal = "BASELINE_FAILED" if current.get("state") == "BASELINE_RUNNING" else "TRACE_FAILED"
        _write_json(state_path, {**current, "state": terminal, "error": str(exc), "retry": False})
        raise
    final = {
        **state,
        "state": "PAIR_COMPLETE",
        "baseline": baseline,
        "trace": trace,
        "scientific_jobs": 0,
        "disease_jobs": 0,
        "gpu_execution": True,
        "simulation_execution": True,
        "retry": False,
    }
    _write_json(state_path, final)
    return final


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--design-canonical-pair", action="store_true")
    modes.add_argument("--canonical-pair-preflight", "--preflight", dest="canonical_pair_preflight", action="store_true")
    modes.add_argument("--execute-authorized-canonical-pair", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = design_canonical_pair() if args.design_canonical_pair else canonical_pair_preflight() if args.canonical_pair_preflight else execute_authorized_canonical_pair()
    except CanonicalPairError as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc), "gpu_execution": False, "simulation_execution": False}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
