"""Reconstruct Gate29 baseline brain-source provenance without executing it.

This command only reads the frozen baseline, the source tree, and Git metadata.
It deliberately treats a dirty baseline plus a clean commit as insufficient
evidence for the bytes used by that baseline.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
MAIN_REPOSITORY = ROOT.parent / "drosophila-pd-neural-disease"
BRAIN_ROOT = MAIN_REPOSITORY / "external/fly-brain"
BASELINE_ROOT = ROOT.parent / "gate29_technical_outputs/neural_causal_trace/baseline"
MANIFEST_ROOT = ROOT / "experiments/gate_29_neural_causal_trace/manifests"
FORENSIC_MANIFEST = MANIFEST_ROOT / "baseline_brain_source_forensic_reconstruction.json"
FAILURE_DECISION = MANIFEST_ROOT / "baseline_source_reconstruction_failure_decision.json"
BASELINE_SOURCE_SNAPSHOT = MANIFEST_ROOT / "baseline_source_snapshot.json"
BASELINE_LOCK = MANIFEST_ROOT / "baseline_execution_lock.json"
GATE11_AUDIT = MAIN_REPOSITORY / "experiments/gate_11_healthy_baseline/manifests/external_input_audit.json"
GATE11_AUDIT_COMMIT = "26d0fa8a8d172aa2996daf3dc329cfdbaf751511"
BASELINE_COMMIT = "ea00d987edfe65346b36bfa4ce37b628231a5c42"

CRITICAL_FILES = (
    "brain_body_bridge.py",
    "code/run_pytorch.py",
    "data/plastic_weights.pt",
    "data/2025_Completeness_783.csv",
    "data/2025_Connectivity_783.parquet",
)


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


def _git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(MAIN_REPOSITORY), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _git_blob(relative_path: str) -> tuple[str | None, int | None]:
    repository_path = (Path("external/fly-brain") / relative_path).as_posix()
    result = subprocess.run(
        ["git", "-C", str(MAIN_REPOSITORY), "rev-parse", f"{BASELINE_COMMIT}:{repository_path}"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return None, None
    blob = result.stdout.strip()
    size = int(_git("cat-file", "-s", blob))
    return blob, size


def _git_blob_sha256(blob: str | None) -> str | None:
    if not blob:
        return None
    result = subprocess.run(
        ["git", "-C", str(MAIN_REPOSITORY), "cat-file", "blob", blob],
        check=True,
        capture_output=True,
    )
    return hashlib.sha256(result.stdout).hexdigest()


def _git_object_exists(blob: str | None) -> bool:
    if not blob:
        return False
    result = subprocess.run(
        ["git", "-C", str(MAIN_REPOSITORY), "cat-file", "-e", f"{blob}^{{blob}}"],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def _git_commit_exists(commit: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(MAIN_REPOSITORY), "cat-file", "-e", f"{commit}^{{commit}}"],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def _historical_audit() -> dict[str, Any]:
    """Read the committed Gate11 audit, not the possibly modified worktree file."""

    try:
        raw = subprocess.run(
            [
                "git",
                "-C",
                str(MAIN_REPOSITORY),
                "show",
                f"{GATE11_AUDIT_COMMIT}:experiments/gate_11_healthy_baseline/manifests/external_input_audit.json",
            ],
            check=True,
            capture_output=True,
        ).stdout
        return json.loads(raw.decode("utf-8"))
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _audit_file_record(audit: Mapping[str, Any], relative_path: str) -> Mapping[str, Any]:
    return audit.get("brain_source", {}).get("integrity", {}).get("files", {}).get(relative_path, {})


def classify_reconstruction(records: Sequence[Mapping[str, Any]]) -> str:
    """Return the only successful classification when every critical file is proven."""

    if records and all(record.get("historical_content_established") is True for record in records):
        return "GATE29_BASELINE_BRAIN_SOURCE_EXACTLY_RECONSTRUCTED"
    return "GATE29_BASELINE_BRAIN_SOURCE_RECONSTRUCTION_INCOMPLETE"


def deterministic_source_fingerprint(records: Sequence[Mapping[str, Any]]) -> str | None:
    if classify_reconstruction(records) != "GATE29_BASELINE_BRAIN_SOURCE_EXACTLY_RECONSTRUCTED":
        return None
    canonical = [
        {"path": record["path"], "sha256": record["historical_candidate_sha256"]}
        for record in sorted(records, key=lambda item: str(item["path"]))
    ]
    payload = json.dumps(canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_forensic_manifest() -> dict[str, Any]:
    baseline_source = _json(BASELINE_SOURCE_SNAPSHOT)
    baseline_lock = _json(BASELINE_LOCK)
    audit = _historical_audit()
    baseline_metadata = _json(BASELINE_ROOT / "metadata.json")
    baseline_checkpoint_sha = baseline_metadata.get("simulation", {}).get("brain_checkpoint_sha256")
    records: list[dict[str, Any]] = []

    for relative_path in CRITICAL_FILES:
        path = BRAIN_ROOT / relative_path
        current_sha = _sha256(path) if path.is_file() else None
        current_size = path.stat().st_size if path.is_file() else None
        clean_blob, clean_size = _git_blob(relative_path)
        clean_sha = _git_blob_sha256(clean_blob)
        current_git_blob = _git("hash-object", str(path), check=False) if path.is_file() else None
        audit_record = _audit_file_record(audit, relative_path)
        candidate_sha = audit_record.get("sha256")
        candidate_size = audit_record.get("size")
        is_checkpoint = relative_path == "data/plastic_weights.pt"
        checkpoint_match = is_checkpoint and current_sha == baseline_checkpoint_sha == baseline_lock.get("healthy_checkpoint_sha256")

        if checkpoint_match:
            candidate_source = (
                "Gate29 baseline metadata + baseline_execution_lock.json; "
                "checkpoint SHA is independently locked"
            )
            evidence_level = "A_BASELINE_ARTIFACT_DIRECT_SHA"
            established = True
        elif candidate_sha and candidate_sha == current_sha:
            candidate_source = (
                f"Git {GATE11_AUDIT_COMMIT}:experiments/gate_11_healthy_baseline/"
                "manifests/external_input_audit.json; same current path and hash, "
                "but no immutable link to the Gate29 execution"
            )
            evidence_level = "B_CANDIDATE_NOT_TIED_TO_BASELINE"
            established = False
        else:
            candidate_source = None
            evidence_level = "NONE"
            established = False

        records.append(
            {
                "path": relative_path,
                "baseline_commit": BASELINE_COMMIT,
                "repository_path_at_baseline_commit": (Path("external/fly-brain") / relative_path).as_posix(),
                "clean_commit_git_blob_sha": clean_blob,
                "clean_commit_sha256": clean_sha,
                "clean_commit_size": clean_size,
                "current_sha256": current_sha,
                "current_size": current_size,
                "current_git_blob_sha": current_git_blob,
                "current_git_blob_object_present": _git_object_exists(current_git_blob),
                "current_equals_clean_commit": (
                    current_git_blob == clean_blob if clean_blob is not None else None
                ),
                "historical_candidate_sha256": candidate_sha or (baseline_checkpoint_sha if is_checkpoint else None),
                "historical_candidate_size": candidate_size or (current_size if checkpoint_match else None),
                "historical_candidate_source": candidate_source,
                "historical_candidate_immutable": bool(candidate_source),
                "historical_content_established": established,
                "evidence_level": evidence_level,
                "evidence_artifact": (
                    "experiments/gate_29_neural_causal_trace/manifests/baseline_execution_lock.json"
                    if checkpoint_match
                    else "experiments/gate_11_healthy_baseline/manifests/external_input_audit.json"
                    if candidate_sha
                    else None
                ),
                "reason": (
                    "Baseline metadata directly locks the checkpoint SHA."
                    if checkpoint_match
                    else "The baseline recorded brain_source_worktree_dirty=true and no per-file historical hash. "
                    "The matching Gate11 hash is a current-source candidate, not proof of the dirty bytes used by Gate29."
                    if candidate_sha
                    else "No immutable content hash tied to the Gate29 baseline was found."
                ),
            }
        )

    overall = classify_reconstruction(records)
    fingerprint = deterministic_source_fingerprint(records)
    manifest = {
        "schema_version": "gate29-baseline-brain-source-forensic-reconstruction-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scope": "FORENSIC_PROVENANCE_ONLY",
        "baseline_source_root": str(BRAIN_ROOT),
        "baseline_source_commit": BASELINE_COMMIT,
        "baseline_source_worktree_dirty": baseline_source.get("brain_source_worktree_dirty"),
        "historical_dirty_path_set_recovered": False,
        "historical_dirty_path_evidence": [
            "Gate29 baseline metadata records dirty=true but no path set.",
            "Current status/diff and reflog/stash/fsck did not provide an unambiguous baseline-time path-to-blob mapping.",
        ],
        "critical_file_count": len(records),
        "critical_files": records,
        "overall_classification": overall,
        "baseline_brain_execution_source_fingerprint_sha256": fingerprint,
        "fingerprint_encoding": (
            "UTF-8 JSON; sorted records by path; each record contains only path and historical_candidate_sha256; "
            "compact separators; sort_keys=true"
        ) if fingerprint else None,
        "git_forensics": {
            "repository_root": str(MAIN_REPOSITORY),
            "baseline_commit_resolves": _git_commit_exists(BASELINE_COMMIT),
            "critical_paths_tracked_at_baseline_commit": any(
                record["clean_commit_git_blob_sha"] is not None for record in records
            ),
            "current_source_git_blobs_present": all(
                record["current_git_blob_object_present"] for record in records
            ),
            "reflog_stash_fsck_mapping": "NO_UNAMBIGUOUS_CRITICAL_FILE_MAPPING_FOUND",
        },
        "gpu_executed": False,
        "simulation_executed": False,
        "baseline_rerun": False,
        "trace_attempt_02": False,
    }
    return manifest


def write_outputs() -> dict[str, Any]:
    manifest = build_forensic_manifest()
    _write_json(FORENSIC_MANIFEST, manifest)
    if manifest["overall_classification"] != "GATE29_BASELINE_BRAIN_SOURCE_EXACTLY_RECONSTRUCTED":
        _write_json(
            FAILURE_DECISION,
            {
                "schema_version": "gate29-baseline-source-reconstruction-failure-v1",
                "status": "GATE29_OLD_BASELINE_NOT_SUITABLE_FOR_TRACE_ONLY_PAIRING",
                "reason": "EXACT_BASELINE_BRAIN_SOURCE_BYTES_NOT_RECOVERABLE",
                "old_baseline_preserved": True,
                "old_baseline_scientific_evidence": False,
                "recommended_next_action": "DESIGN_NEW_CANONICAL_PAIRED_GATE29_ENGINEERING_RUN",
                "claim_safe_wording": (
                    "The baseline remains a real historical engineering execution, but it cannot serve as the "
                    "cryptographically controlled counterpart for a new trace-only non-perturbation comparison."
                ),
            },
        )
    return manifest


def main() -> int:
    manifest = write_outputs()
    print(json.dumps({
        "status": manifest["overall_classification"],
        "critical_files": manifest["critical_file_count"],
        "established": sum(
            record["historical_content_established"] is True for record in manifest["critical_files"]
        ),
        "historical_dirty_path_set_recovered": manifest["historical_dirty_path_set_recovered"],
        "gpu_executed": False,
        "simulation_executed": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
