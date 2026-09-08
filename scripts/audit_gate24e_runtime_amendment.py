"""Audit the supplemental Gate24E runtime amendment without executing a job.

The command is deliberately fail-closed. It can report readiness for a new
technical storage probe only after the separate runtime amendment object has
two valid human reviewers. It never authorizes the 25-job scientific batch.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = ROOT / "research/validation/prospective/parkin_runtime_provenance_amendment.yaml"
RUNTIME_SIGNOFF = ROOT / "research/validation/prospective/parkin_runtime_amendment_reviewer_signoff.json"
ORIGINAL_SIGNOFF = ROOT / "research/validation/prospective/parkin_prediction_reviewer_signoff.json"
FREEZE = ROOT / "research/validation/prospective/parkin_model_freeze.yaml"
CHECKSUMS = ROOT / "experiments/gate_24e_storage_probe/manifests/runtime_amendment_checksums.json"
FIREWALL = ROOT / "experiments/gate_24_prospective_validation/manifests/holdout_firewall_manifest.json"
EXECUTION = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/execution_manifest.json"
ANALYZER = ROOT / "scripts/analyze_gate24e_blinded_prediction.py"
ATTEMPT_03 = ROOT / "experiments/gate_24e_storage_probe/attempt_03"

ORIGINAL_COMMIT = "3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06"
AMENDED_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"
EXPECTED_FREEZE_SHA256 = "eb370a25c00b39173272468e050e4ab917a0e99df0c3ee3ab73635868dfe916a"
EXPECTED_GATE24D_SIGNOFF_SHA256 = "24e5118a778257887c9541ceb679e9c4d4a87ddd2053a81c000301e6b9d90526"
EXPECTED_ANALYZER_SHA256 = "e179a58cdcf5b6dc9e4a0960be2e25fe792b7356ffdf8cb94754184ae8d2bed4"
EXPECTED_GRID = [0.0, 0.25, 0.5, 0.75, 1.0]
EXPECTED_SEEDS = [0, 1, 2, 3, 4]
EXPECTED_CHANGED_FILES = [
    "scripts/run_brain_body_rollout.py",
    "src/drosophila_pd/analysis/__init__.py",
    "src/drosophila_pd/analysis/memory_safe.py",
    "src/drosophila_pd/flygym_adapter/__init__.py",
    "src/drosophila_pd/flygym_adapter/export.py",
    "tests/test_memory_safe_export.py",
]
EXPECTED_LOCKED_VALUES: dict[str, Any] = {
    "model_commit": "be4b10a80755d9f7bad931f56b8a739bd64e3619",
    "mapping_sha256": "776274356c16eb458ef945e2a5153af4676bbddebef31cdb1b698f1d6aeaaf80",
    "target_neurons_sha256": "e36b0210ea6d2d2b7225f62feba73ae5c9e6535565c8b936558d0eaaf04a2085",
    "target_root_count": 330,
    "healthy_checkpoint_sha256": "d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691",
    "parameter_grid": EXPECTED_GRID,
    "seeds": EXPECTED_SEEDS,
    "neural_transform_sha256": "8f8fe415b9a2d4490783775ef9a4aa45a82bfe624f37d969d89eda1a7bac383b",
    "timestep_s": 0.0001,
    "duration_s": 10.0,
    "simulation_steps": 100000,
    "controller": "HybridTurningController",
    "cpg_frequency_hz": 12.0,
    "primary_metric": "median_planar_speed_mm_s",
    "secondary_metric": "distance_traveled_mm",
    "decision_rule": "VIRTUAL_DIRECTIONAL_PREDICTION_SUPPORTED only when every nonzero parameter passes the primary direction rule and QC",
}
EXPECTED_DISEASE_CHECKPOINTS = {
    "0.25": "dd2a4413d1aa4baed30df96884afdd030bac3a246d1bcc7a241baa955082cb8c",
    "0.5": "f682057bfff2bd523ba9a934970c9986e041ce44cb16fb8781ce2e9c5aebcff1",
    "0.75": "0b73e25620d10e56e293f859fb95c45630c7b798073b482d73f95a7d5c51e802",
    "1.0": "0ecf37ce96b6d4ea09b00204c3f01c6f41b6a2820b5f21170c6856760850e2b1",
}
REQUIRED_INVARIANTS = {
    "model_commit_unchanged",
    "neural_transform_unchanged",
    "mapping_unchanged",
    "target_set_unchanged",
    "checkpoints_unchanged",
    "parameter_grid_unchanged",
    "seeds_unchanged",
    "timestep_unchanged",
    "duration_unchanged",
    "controller_unchanged",
    "cpg_unchanged",
    "primary_metric_definition_unchanged",
    "decision_rule_unchanged",
    "holdout_state_unchanged",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return value


def _git_bytes(runtime_root: Path, arguments: Sequence[str]) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(runtime_root), *arguments],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"Git inspection failed in {runtime_root}: {stderr}")
    return result.stdout


def _git_text(runtime_root: Path, *arguments: str) -> str:
    return _git_bytes(runtime_root, arguments).decode("utf-8", errors="strict").strip()


def _valid_review_date(value: object) -> bool:
    try:
        date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return False
    return True


def _is_placeholder(value: object) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    normalized = text.upper().replace("-", "_").replace(" ", "_")
    markers = (
        "TODO",
        "TBD",
        "PENDING",
        "PLACEHOLDER",
        "REVIEWER_1",
        "REVIEWER_2",
        "TEN_NGUOI",
        "TÊN_NGƯỜI",
    )
    return any(marker in normalized for marker in markers)


def _review_state(signoff: dict[str, Any], amendment_sha256: str) -> tuple[str, list[str]]:
    blockers: list[str] = []
    exact = {
        "schema_version": "gate24e-runtime-amendment-review-v1",
        "study_id": "parkin_prospective_validation",
        "parent_gate24d_decision": "APPROVED_FOR_BLINDED_VIRTUAL_PREDICTION",
        "original_platform_commit": ORIGINAL_COMMIT,
        "amended_platform_commit": AMENDED_COMMIT,
        "runtime_amendment_sha256": amendment_sha256,
        "simulation_semantics_changed": False,
        "scientific_contract_changed": False,
        "holdout_opened": False,
        "scientific_jobs_executed": 0,
        "scientific_batch_authorized": False,
    }
    for key, expected in exact.items():
        if signoff.get(key) != expected:
            blockers.append(f"runtime signoff mismatch: {key}")

    reviewers = [str(signoff.get(key, "")).strip() for key in ("reviewer_1", "reviewer_2")]
    if any(_is_placeholder(value) for value in reviewers):
        blockers.append("reviewer placeholders are forbidden")
    if all(reviewers) and reviewers[0].casefold() == reviewers[1].casefold():
        blockers.append("two distinct human reviewers are required")

    pending = (
        signoff.get("status") == "WAITING_RUNTIME_AMENDMENT_REVIEW"
        and signoff.get("decision") == "PENDING_HUMAN_REVIEW"
    )
    approved = (
        signoff.get("status") == "RUNTIME_AMENDMENT_APPROVED"
        and signoff.get("decision") == "APPROVED_FOR_GATE24E_RUNTIME_AMENDMENT"
    )
    if pending:
        if signoff.get("attempt_03_authorized") is not False:
            blockers.append("attempt_03 must remain blocked while review is pending")
        if signoff.get("review_date") and not _valid_review_date(signoff.get("review_date")):
            blockers.append("partially entered review_date is invalid")
        return "PENDING", blockers
    if approved:
        if not all(reviewers) or not _valid_review_date(signoff.get("review_date")):
            blockers.append("approved amendment requires two reviewers and an ISO review date")
        if signoff.get("attempt_03_authorized") is not True:
            blockers.append("approved amendment must explicitly authorize only attempt_03")
        return "APPROVED", blockers
    blockers.append("runtime amendment decision is neither pending nor approved")
    return "INVALID", blockers


def _invariant_blockers(amendment: dict[str, Any], freeze: dict[str, Any]) -> tuple[list[str], bool]:
    blockers: list[str] = []
    scientific_change = False
    locked = amendment.get("locked_scientific_values") or {}
    for key, expected in EXPECTED_LOCKED_VALUES.items():
        if locked.get(key) != expected:
            blockers.append(f"locked scientific value changed: {key}")
            scientific_change = True
    if locked.get("disease_checkpoint_sha256") != EXPECTED_DISEASE_CHECKPOINTS:
        blockers.append("disease checkpoint grid hashes changed")
        scientific_change = True

    freeze_checks = {
        "model_commit": freeze.get("model_commit"),
        "mapping_sha256": freeze.get("mapping_sha256"),
        "target_neurons_sha256": freeze.get("target_neurons_sha256"),
        "target_root_count": freeze.get("target_root_count"),
        "healthy_checkpoint_sha256": (freeze.get("checkpoint") or {}).get("sha256"),
        "parameter_grid": freeze.get("parameter_grid"),
        "seeds": freeze.get("seed_list"),
        "neural_transform_sha256": (freeze.get("disease_transform") or {}).get("sha256"),
        "timestep_s": (freeze.get("physics") or {}).get("timestep_s"),
        "duration_s": (freeze.get("physics") or {}).get("duration_s"),
        "controller": freeze.get("controller"),
    }
    for key, actual in freeze_checks.items():
        if actual != EXPECTED_LOCKED_VALUES[key]:
            blockers.append(f"parent model freeze changed: {key}")
            scientific_change = True
    if (freeze.get("parkin_checkpoint_grid") or {}).get("checkpoint_sha256") != EXPECTED_DISEASE_CHECKPOINTS:
        blockers.append("parent model freeze disease checkpoints changed")
        scientific_change = True

    invariants = amendment.get("scientific_invariants") or {}
    false_or_missing = sorted(key for key in REQUIRED_INVARIANTS if invariants.get(key) is not True)
    if false_or_missing:
        blockers.append("scientific invariant flags are false/missing: " + ", ".join(false_or_missing))
        scientific_change = True
    runtime_changes = amendment.get("runtime_changes") or {}
    if runtime_changes.get("simulation_semantics_changed") is not False:
        blockers.append("runtime amendment reports changed simulation semantics")
        scientific_change = True
    return blockers, scientific_change


def _runtime_state_blockers(head: str, porcelain: str) -> list[str]:
    blockers: list[str] = []
    if head != AMENDED_COMMIT:
        blockers.append(f"amended platform commit mismatch: {head or 'MISSING'}")
    if porcelain.strip():
        blockers.append("amended platform worktree is dirty")
    return blockers


def _attempt03_has_files() -> bool:
    """Return whether attempt_03 contains an artifact, not just an empty dir."""
    if ATTEMPT_03.is_file():
        return True
    return ATTEMPT_03.is_dir() and any(path.is_file() for path in ATTEMPT_03.rglob("*"))


def _attempt03_review_blockers(review_state: str) -> list[str]:
    """Apply the attempt_03 guard after the human review state is known."""
    if review_state == "PENDING" and ATTEMPT_03.exists():
        return ["attempt_03 exists while runtime amendment review is pending"]
    if review_state == "APPROVED" and _attempt03_has_files():
        return ["attempt_03 already contains execution artifacts"]
    return []


def _source_hash_blockers(runtime_root: Path, checksums: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    sources = checksums.get("amended_executable_sources") or {}
    for relative, evidence in sources.items():
        try:
            content = _git_bytes(runtime_root, ["show", f"{AMENDED_COMMIT}:{relative}"])
        except ValueError as exc:
            blockers.append(str(exc))
            continue
        if hashlib.sha256(content).hexdigest() != evidence.get("git_blob_sha256"):
            blockers.append(f"invalid amended runtime hash: {relative}")
        if len(content) != evidence.get("git_blob_byte_size"):
            blockers.append(f"invalid amended runtime byte size: {relative}")
        path = runtime_root / relative
        if not path.is_file():
            blockers.append(f"amended runtime source missing from worktree: {relative}")
        elif os.name == "nt" and _sha256(path) != evidence.get("windows_worktree_sha256"):
            blockers.append(f"Windows worktree hash mismatch: {relative}")

    test_evidence = checksums.get("equivalence_tests") or {}
    test_path = str(test_evidence.get("path", ""))
    if test_path:
        content = _git_bytes(runtime_root, ["show", f"{AMENDED_COMMIT}:{test_path}"])
        if hashlib.sha256(content).hexdigest() != test_evidence.get("git_blob_sha256"):
            blockers.append("equivalence test source hash mismatch")
    return blockers


def _runtime_provenance(runtime_root: Path, checksums: dict[str, Any]) -> tuple[list[str], bool, dict[str, Any]]:
    blockers: list[str] = []
    scientific_change = False
    evidence: dict[str, Any] = {"runtime_root": str(runtime_root), "clean": False}
    if not runtime_root.is_dir():
        return [f"amended runtime worktree is missing: {runtime_root}"], False, evidence
    try:
        head = _git_text(runtime_root, "rev-parse", "HEAD")
        porcelain = _git_text(runtime_root, "status", "--porcelain")
        _git_text(runtime_root, "cat-file", "-e", f"{ORIGINAL_COMMIT}^{{commit}}")
        _git_text(runtime_root, "cat-file", "-e", f"{AMENDED_COMMIT}^{{commit}}")
    except ValueError as exc:
        return [str(exc)], False, evidence
    blockers.extend(_runtime_state_blockers(head, porcelain))
    evidence.update({"head": head, "clean": not bool(porcelain)})
    blockers.extend(_source_hash_blockers(runtime_root, checksums))

    changed = _git_text(runtime_root, "diff", "--name-only", ORIGINAL_COMMIT, AMENDED_COMMIT).splitlines()
    if changed != EXPECTED_CHANGED_FILES or changed != (checksums.get("source_diff") or {}).get("changed_files"):
        blockers.append("reviewed runtime diff file scope changed")
        scientific_change = True
    diff_bytes = _git_bytes(
        runtime_root,
        ["diff", "--no-ext-diff", "--binary", ORIGINAL_COMMIT, AMENDED_COMMIT, "--", *EXPECTED_CHANGED_FILES],
    )
    if hashlib.sha256(diff_bytes).hexdigest() != (checksums.get("source_diff") or {}).get("sha256"):
        blockers.append("reviewed runtime source diff hash mismatch")
        scientific_change = True

    runner_path = "scripts/run_brain_body_rollout.py"
    old_runner = _git_bytes(runtime_root, ["show", f"{ORIGINAL_COMMIT}:{runner_path}"])
    new_runner = _git_bytes(runtime_root, ["show", f"{AMENDED_COMMIT}:{runner_path}"])
    loop = checksums.get("simulation_loop") or {}
    start = str(loop.get("start_marker", "")).encode()
    old_end = str(loop.get("original_end_marker", "")).encode()
    new_end = str(loop.get("amended_end_marker", "")).encode()
    try:
        old_segment = old_runner[old_runner.index(start):old_runner.index(old_end, old_runner.index(start))].rstrip() + b"\n"
        new_segment = new_runner[new_runner.index(start):new_runner.index(new_end, new_runner.index(start))].rstrip() + b"\n"
    except ValueError:
        blockers.append("simulation loop audit markers are missing")
        scientific_change = True
    else:
        old_hash = hashlib.sha256(old_segment).hexdigest()
        new_hash = hashlib.sha256(new_segment).hexdigest()
        evidence["original_simulation_loop_sha256"] = old_hash
        evidence["amended_simulation_loop_sha256"] = new_hash
        if (
            old_segment != new_segment
            or old_hash != loop.get("original_sha256")
            or new_hash != loop.get("amended_sha256")
            or loop.get("byte_equivalent_after_normalization") is not True
        ):
            blockers.append("simulation loop changed between original and amended runtime")
            scientific_change = True
    return blockers, scientific_change, evidence


def audit(runtime_root: Path | None = None) -> dict[str, Any]:
    amendment = _yaml(AMENDMENT)
    runtime_signoff = _json(RUNTIME_SIGNOFF)
    original_signoff = _json(ORIGINAL_SIGNOFF)
    freeze = _yaml(FREEZE)
    checksums = _json(CHECKSUMS)
    firewall = _json(FIREWALL)
    execution = _json(EXECUTION)
    blockers: list[str] = []
    scientific_change = False

    if _sha256(FREEZE) != EXPECTED_FREEZE_SHA256:
        blockers.append("original model freeze hash changed")
        scientific_change = True
    if _sha256(ORIGINAL_SIGNOFF) != EXPECTED_GATE24D_SIGNOFF_SHA256:
        blockers.append("original Gate24D signoff hash changed")
        scientific_change = True
    if original_signoff.get("status") != "PROSPECTIVE_PREDICTION_LOCKED" or original_signoff.get("decision") != "APPROVED_FOR_BLINDED_VIRTUAL_PREDICTION":
        blockers.append("original Gate24D signoff is no longer valid")
        scientific_change = True
    if (amendment.get("parent_scientific_freeze") or {}).get("sha256") != EXPECTED_FREEZE_SHA256:
        blockers.append("amendment parent freeze hash mismatch")
        scientific_change = True
    if (amendment.get("parent_gate24d_signoff") or {}).get("sha256") != EXPECTED_GATE24D_SIGNOFF_SHA256:
        blockers.append("amendment parent Gate24D signoff hash mismatch")
        scientific_change = True
    if amendment.get("amendment_scope") != "POST_SIMULATION_EXPORT_AND_POSTPROCESS_ONLY":
        blockers.append("runtime amendment scope is not post-simulation only")
        scientific_change = True
    if (amendment.get("original_runtime") or {}).get("platform_commit") != ORIGINAL_COMMIT:
        blockers.append("original platform commit is not preserved")
    if (amendment.get("amended_runtime") or {}).get("platform_commit") != AMENDED_COMMIT:
        blockers.append("amended platform commit mismatch")
    if (amendment.get("amended_runtime") or {}).get("artifact_profile") != "GATE24E_MEMORY_SAFE":
        blockers.append("memory-safe artifact profile is not locked")

    invariant_blockers, invariant_change = _invariant_blockers(amendment, freeze)
    blockers.extend(invariant_blockers)
    scientific_change = scientific_change or invariant_change

    artifact = amendment.get("artifact_contract") or {}
    required_artifact_values = {
        "full_rollout_json_required": False,
        "rollout_npz_required": True,
        "metadata_required": True,
        "manifest_required": True,
        "scalar_metrics_required": True,
        "viewer_required": False,
        "video_required": False,
        "biomarker_required_for_primary_gate24_decision": False,
    }
    for key, expected in required_artifact_values.items():
        if artifact.get(key) != expected:
            blockers.append(f"artifact contract mismatch: {key}")

    equivalence = amendment.get("equivalence_evidence") or {}
    for key, expected in {
        "npz_equivalence": "NPZ_EQUIVALENCE_PASS",
        "primary_metric_equivalence": "PRIMARY_METRIC_EQUIVALENCE_PASS",
        "secondary_metric_equivalence": "SECONDARY_METRIC_EQUIVALENCE_PASS",
        "memory_regression": "MEMORY_REGRESSION_PASS",
    }.items():
        if equivalence.get(key) != expected:
            blockers.append(f"equivalence evidence missing: {key}")
    if _sha256(ANALYZER) != EXPECTED_ANALYZER_SHA256:
        blockers.append("locked Gate24E analyzer source changed")
        scientific_change = True

    parent_hashes = checksums.get("parent_artifacts") or {}
    if parent_hashes.get("model_freeze_sha256") != EXPECTED_FREEZE_SHA256:
        blockers.append("checksum manifest parent freeze hash mismatch")
    if parent_hashes.get("gate24d_signoff_sha256") != EXPECTED_GATE24D_SIGNOFF_SHA256:
        blockers.append("checksum manifest Gate24D hash mismatch")
    if firewall.get("status") != "SEALED" or amendment.get("holdout_status") != "SEALED" or amendment.get("holdout_opened") is not False:
        blockers.append("holdout is not sealed")
        scientific_change = True
    if execution.get("status") != "NOT_EXECUTED" or execution.get("executed_job_count") != 0 or execution.get("gpu_jobs_executed") != 0:
        blockers.append("Gate24E scientific execution is no longer zero")
    if amendment.get("scientific_jobs_executed") != 0:
        blockers.append("amendment reports nonzero scientific jobs")

    # Review must be resolved before applying the attempt guard. An empty
    # approved attempt directory is harmless; any file means a second run
    # must be refused. Pending review remains fail-closed for any directory.
    amendment_sha = _sha256(AMENDMENT)
    review_state, review_blockers = _review_state(runtime_signoff, amendment_sha)
    blockers.extend(review_blockers)
    attempt03_has_files = _attempt03_has_files()
    blockers.extend(_attempt03_review_blockers(review_state))
    if amendment.get("attempt_03_authorized") is not False or amendment.get("scientific_batch_authorized") is not False:
        blockers.append("draft amendment improperly authorizes execution")

    selected_runtime = runtime_root or (ROOT / str((amendment.get("amended_runtime") or {}).get("worktree", ""))).resolve()
    runtime_blockers, runtime_change, runtime_evidence = _runtime_provenance(selected_runtime, checksums)
    blockers.extend(runtime_blockers)
    scientific_change = scientific_change or runtime_change

    if _sha256(RUNTIME_SIGNOFF) == _sha256(ORIGINAL_SIGNOFF):
        blockers.append("original Gate24D signoff was silently reused as amendment approval")

    if not scientific_change and review_state == "APPROVED" and attempt03_has_files:
        status = "ATTEMPT_03_ARTIFACTS_PRESENT"
    elif scientific_change:
        status = "RUNTIME_AMENDMENT_SCIENTIFIC_CHANGE_DETECTED"
    elif blockers:
        status = "RUNTIME_AMENDMENT_INVALID"
    elif review_state == "PENDING":
        status = "WAITING_GATE24E_RUNTIME_AMENDMENT_REVIEW"
    elif review_state == "APPROVED":
        status = "READY_FOR_ATTEMPT_03"
    else:
        status = "RUNTIME_AMENDMENT_INVALID"

    return {
        "schema_version": "gate24e-runtime-amendment-audit-v1",
        "status": status,
        "original_gate24d_status": original_signoff.get("status"),
        "original_model_freeze_preserved": _sha256(FREEZE) == EXPECTED_FREEZE_SHA256,
        "original_platform_commit": ORIGINAL_COMMIT,
        "amended_platform_commit": AMENDED_COMMIT,
        "artifact_profile": (amendment.get("amended_runtime") or {}).get("artifact_profile"),
        "simulation_semantics_changed": scientific_change,
        "scientific_contract_changed": scientific_change,
        "runtime_amendment_sha256": amendment_sha,
        "runtime_review_state": review_state,
        "reviewer_1": runtime_signoff.get("reviewer_1", ""),
        "reviewer_2": runtime_signoff.get("reviewer_2", ""),
        "attempt_03_authorized": status == "READY_FOR_ATTEMPT_03",
        "scientific_batch_authorized": False,
        "holdout": firewall.get("status"),
        "scientific_jobs_executed": execution.get("executed_job_count"),
        "attempt_03_exists": ATTEMPT_03.exists(),
        "attempt_03_has_files": attempt03_has_files,
        "runtime": runtime_evidence,
        "blockers": blockers,
        "next_allowed_action": "HUMAN_REVIEW_GATE24E_RUNTIME_AMENDMENT" if status == "WAITING_GATE24E_RUNTIME_AMENDMENT_REVIEW" else "STOP_AND_REVIEW_AUDIT",
        "gpu_executed_by_audit": False,
        "simulation_executed_by_audit": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        result = audit(args.runtime_root.resolve() if args.runtime_root else None)
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(json.dumps({"status": "RUNTIME_AMENDMENT_INVALID", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in {"WAITING_GATE24E_RUNTIME_AMENDMENT_REVIEW", "READY_FOR_ATTEMPT_03"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
