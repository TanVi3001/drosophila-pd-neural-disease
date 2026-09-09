"""Create and audit the Gate25-R2 freeze for the closed Gate24E Parkin track.

This module is deliberately file-only.  It never imports FlyGym, CUDA, torch,
or a simulator.  The raw rollout archive is verified in place and is never
copied back into the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
R2_ROOT = ROOT / "experiments/gate_25_r2_parkin_reproducibility"
R2_MANIFESTS = R2_ROOT / "manifests"
INVENTORY_PATH = R2_MANIFESTS / "reproducibility_inventory.json"
CHECKSUMS_PATH = R2_MANIFESTS / "checksums.sha256"
FREEZE_PATH = R2_MANIFESTS / "gate25_r2_reproducibility_freeze.json"
REPORT_PATH = ROOT / "docs/reproducibility/gate25_r2_parkin_reproducibility_freeze_report.md"
README_PATH = ROOT / "README.md"

HISTORICAL_REPORT = ROOT / "docs/reproducibility/gate_25_reproducibility_freeze_report.md"
HISTORICAL_REPORT_SHA256 = "e09347664edbc069c8d8bdd0340811cbaf8a4b9f75a25d1e356a24086cb309f0"
ANCHOR_COMMIT = "ad87e6b45af4a8e10a4180956af4844e5e33e393"
PREVIOUS_R2_FREEZE_SHA256 = "5aa0d5bf05dac950761b8636fdea001072f27c8226139ec1dac9066be6146d05"
REFRESH_REASON = "CROSS_PLATFORM_FROZEN_ARTIFACT_TRANSPORT_FIX"

ARCHIVE_EVIDENCE = Path("D:/EHouse/Drosophila_Archive/Gate24E_Final_Raw_Evidence")
ARCHIVE_RUNS = ARCHIVE_EVIDENCE / "runs"
ARCHIVE_MANIFEST = ARCHIVE_EVIDENCE / "manifests/gate24e_raw_runs_archive_manifest.json"
ARCHIVE_CHECKSUMS = ARCHIVE_EVIDENCE / "manifests/raw_runs_checksums.sha256"
REPOSITORY_RUNS = ROOT / "experiments/gate_24e_blinded_parkin_prediction/runs"
RELOCATION_MANIFEST = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_raw_runs_relocation.json"
FINAL_SIGNOFF = ROOT / "research/validation/prospective/gate24e_final_validation_reviewer_signoff.json"
FINAL_EVIDENCE = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_final_evidence_freeze.json"
FINAL_DECISION = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_final_validation_decision.json"
VIRTUAL_FREEZE = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/immutable_virtual_prediction_freeze.json"

EXPECTED_PLAN_SHA256 = "4515e1916631b019711154dccb5fb887110d5572e3eb82b7ea5118c643db5aac"
EXPECTED_VIRTUAL_FREEZE_SHA256 = "f44e9ad10b9fc4795ae2173d3e8b27fc9ea0d8202925bfc08cdcc72d06b00863"
EXPECTED_FINAL_EVIDENCE_SHA256 = "2f056bf5b73ecc4b4de27f714bda681134050c5d82eb2f0f3170b67a5286e967"
EXPECTED_RAW_TREE_SHA256 = "f6e3de6e96cbe3be0f447ea8eeca463087a9381d1c2d2965807d04df1655faff"
EXPECTED_EXECUTOR_SHA256 = "4d10edecbc8d987285ea82eb36a7bcfd686da3abde3b5160a3dcec23a2e78f3f"
EXPECTED_MODEL_COMMIT = "be4b10a80755d9f7bad931f56b8a739bd64e3619"
EXPECTED_RUNTIME_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"

CRITICAL_SCRIPTS = (
    "scripts/run_gate24e_scientific_batch.py",
    "scripts/run_neural_experiment.py",
    "scripts/prepare_gate24e_scientific_batch_plan.py",
    "scripts/audit_gate24e_scientific_batch_preflight.py",
    "scripts/analyze_gate24e_blinded_prediction.py",
    "scripts/open_gate24e_biological_holdout.py",
    "scripts/finalize_gate24e_validation.py",
    "scripts/relocate_gate24e_raw_runs.py",
    "scripts/audit_gate24e_runtime_amendment.py",
    "scripts/run_gate24e_runtime_adapter.py",
    "scripts/audit_holdout_firewall.py",
    "scripts/run_gate25_r2_reproducibility_freeze.py",
    "tests/test_gate25_r2_reproducibility_freeze.py",
    "tests/test_gate25_r2_public_surface_alignment.py",
)

REQUIRED_CORE_FILES = (
    "research/validation/prospective/parkin_model_freeze.yaml",
    "research/validation/prospective/parkin_neural_transform_contract.yaml",
    "research/validation/prospective/parkin_checkpoint_grid_manifest.json",
    "research/validation/prospective/parkin_prediction_contract.yaml",
    "research/validation/prospective/parkin_runtime_provenance_amendment.yaml",
    "research/validation/prospective/parkin_runtime_amendment_reviewer_signoff.json",
    "research/validation/prospective/parkin_scientific_batch_authorization_reviewer_signoff.json",
    "research/validation/prospective/gate24e_virtual_prediction_freeze_reviewer_signoff.json",
    "research/validation/prospective/gate24e_final_validation_reviewer_signoff.json",
    "experiments/gate_24e_blinded_parkin_prediction/manifests/scientific_batch_plan.json",
    "experiments/gate_24e_blinded_parkin_prediction/manifests/scientific_batch_plan.sha256",
    "experiments/gate_24e_blinded_parkin_prediction/manifests/scientific_batch_execution.json",
    "experiments/gate_24e_blinded_parkin_prediction/manifests/scientific_batch_artifact_inventory.json",
    "experiments/gate_24e_blinded_parkin_prediction/manifests/immutable_virtual_prediction_freeze.json",
    "experiments/gate_24e_blinded_parkin_prediction/manifests/biological_holdout_opening.json",
    "experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_final_validation_decision.json",
    "experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_final_evidence_freeze.json",
    "experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_raw_runs_relocation.json",
    "experiments/gate_24e_blinded_parkin_prediction/results/virtual_per_seed.csv",
    "experiments/gate_24e_blinded_parkin_prediction/results/paired_effects.csv",
    "experiments/gate_24e_blinded_parkin_prediction/results/parameter_summary.csv",
    "experiments/gate_24e_blinded_parkin_prediction/results/virtual_prediction_summary.json",
    "experiments/gate_24e_blinded_parkin_prediction/results/biological_holdout_direction.csv",
    "experiments/gate_24e_blinded_parkin_prediction/results/cross_assay_validation_summary.json",
)


class ReproducibilityFreezeError(ValueError):
    """Raised when the closed Gate24E contract cannot be frozen safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ReproducibilityFreezeError(f"Path is outside repository: {path}") from exc


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReproducibilityFreezeError(f"Invalid JSON: {_relative(path)}") from exc
    if not isinstance(value, dict):
        raise ReproducibilityFreezeError(f"Expected JSON object: {_relative(path)}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReproducibilityFreezeError(message)


def _record(path: Path, role: str) -> dict[str, Any]:
    _require(path.is_file(), f"Missing required freeze artifact: {_relative(path)}")
    return {
        "path": _relative(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "role": role,
    }


def _validate_historical_gate25() -> None:
    _require(HISTORICAL_REPORT.is_file(), "Historical Gate25 report is missing")
    _require(
        sha256_file(HISTORICAL_REPORT) == HISTORICAL_REPORT_SHA256,
        "Historical Gate25 report changed; Gate25-R2 will not overwrite it",
    )


def _validate_closed_gate24e() -> dict[str, Any]:
    signoff = _json(FINAL_SIGNOFF)
    evidence = _json(FINAL_EVIDENCE)
    decision = _json(FINAL_DECISION)
    virtual = _json(VIRTUAL_FREEZE)
    relocation = _json(RELOCATION_MANIFEST)

    _require(signoff.get("status") == "GATE24E_FINAL_VALIDATION_REVIEW_APPROVED", "Final human signoff is not approved")
    _require(signoff.get("decision") == "APPROVED_GATE24E_DIRECTIONAL_DISCORDANCE_CLOSURE", "Final closure decision is not approved")
    _require(signoff.get("accepted_negative_result") is True, "Negative result is not human-accepted")
    _require(signoff.get("gate24e_closed") is True, "Gate24E is not closed")
    _require(signoff.get("retuning_allowed") is False, "Retuning is allowed by final signoff")
    _require(signoff.get("gate24e_final_evidence_freeze_sha256") == EXPECTED_FINAL_EVIDENCE_SHA256, "Final signoff freeze SHA changed")

    _require(evidence.get("gate24e_final_evidence_freeze_sha256") == EXPECTED_FINAL_EVIDENCE_SHA256, "Final evidence freeze SHA changed")
    _require(evidence.get("scientific_result") == "NEGATIVE_VALIDATION_RESULT", "Scientific result changed")
    _require(evidence.get("runtime_commit") == EXPECTED_RUNTIME_COMMIT, "Runtime provenance changed")
    _require(evidence.get("model_commit") == EXPECTED_MODEL_COMMIT, "Model provenance changed")
    _require(decision.get("status") == "GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE", "Final Gate24E status changed")
    _require(decision.get("scientific_result") == "NEGATIVE_VALIDATION_RESULT", "Final decision is not negative")
    _require(decision.get("cross_assay_decision") == "DIRECTIONAL_CROSS_ASSAY_DISCORDANCE", "Cross-assay decision changed")
    _require(decision.get("biological_validation_supported") is False, "Biological validation claim is enabled")
    _require(decision.get("quantitative_cross_assay_validation") is False, "Quantitative cross-assay validation is enabled")
    _require(virtual.get("virtual_prediction_freeze_sha256") == EXPECTED_VIRTUAL_FREEZE_SHA256, "Virtual prediction freeze SHA changed")
    _require(virtual.get("holdout") == "SEALED", "Virtual prediction holdout is not sealed")
    _require(virtual.get("holdout_opened") is False, "Virtual prediction freeze says holdout was opened")

    locked = {
        "scientific_plan_sha256": EXPECTED_PLAN_SHA256,
        "virtual_prediction_freeze_sha256": EXPECTED_VIRTUAL_FREEZE_SHA256,
        "final_evidence_freeze_sha256": EXPECTED_FINAL_EVIDENCE_SHA256,
        "raw_runs_tree_sha256": EXPECTED_RAW_TREE_SHA256,
        "executor_sha256": EXPECTED_EXECUTOR_SHA256,
        "model_commit": EXPECTED_MODEL_COMMIT,
        "runtime_commit": EXPECTED_RUNTIME_COMMIT,
    }
    _require(relocation.get("status") == "RAW_RUNS_RELOCATED_AND_VERIFIED", "Raw relocation is not verified")
    _require(relocation.get("job_count") == 25, "Relocation job count is not 25")
    _require(relocation.get("source_file_count") == 275, "Relocation source file count is not 275")
    _require(relocation.get("source_total_bytes") == 13958129260, "Relocation source byte total changed")
    _require(relocation.get("required_scientific_artifacts_verified") == 125, "Required scientific artifact count changed")
    _require(relocation.get("copy_verified") is True, "Raw archive copy was not verified")
    _require(relocation.get("original_local_copy_deleted") is True, "Original raw copy is not recorded deleted")
    _require(relocation.get("raw_scientific_evidence_preserved") is True, "Raw scientific evidence is not preserved")
    _require(relocation.get("relocation_changes_scientific_result") is False, "Relocation changes scientific result")
    _require(not REPOSITORY_RUNS.exists(), "Raw runs were restored into the repository")
    return {"signoff": signoff, "evidence": evidence, "decision": decision, "virtual": virtual, "relocation": relocation, "locked": locked}


def _archive_records() -> list[dict[str, Any]]:
    _require(ARCHIVE_RUNS.is_dir(), f"External raw archive is unavailable: {ARCHIVE_RUNS}")
    _require(ARCHIVE_CHECKSUMS.is_file(), "External raw checksum manifest is missing")
    records: list[dict[str, Any]] = []
    for line in ARCHIVE_CHECKSUMS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            expected, relative = line.split("  ", maxsplit=1)
        except ValueError as exc:
            raise ReproducibilityFreezeError("Malformed external raw checksum line") from exc
        relative_path = Path(relative.strip())
        _require(not relative_path.is_absolute() and ".." not in relative_path.parts, "Unsafe external archive path")
        path = ARCHIVE_RUNS / relative_path
        _require(path.is_file() and not path.is_symlink(), f"Missing external raw artifact: {relative}")
        records.append({"relative_path": relative_path.as_posix(), "size_bytes": path.stat().st_size, "sha256": expected.lower()})
    records.sort(key=lambda item: item["relative_path"])
    _require(len(records) == 275, "External raw checksum manifest does not contain 275 files")
    return records


def _tree_sha256(records: Iterable[Mapping[str, Any]]) -> str:
    canonical = sorted((dict(record) for record in records), key=lambda item: item["relative_path"])
    return hashlib.sha256(canonical_json(canonical)).hexdigest()


def verify_external_archive(*, complete: bool = False) -> dict[str, Any]:
    """Verify the external archive without copying it into the repository."""
    records = _archive_records()
    archive_manifest = _json(ARCHIVE_MANIFEST)
    _require(archive_manifest.get("status") == "GATE24E_RAW_RUNS_ARCHIVE_VERIFIED", "External archive manifest is not verified")
    _require(archive_manifest.get("source_file_count") == 275, "External archive manifest file count changed")
    _require(archive_manifest.get("source_total_bytes") == 13958129260, "External archive manifest byte total changed")
    _require(archive_manifest.get("source_raw_runs_tree_sha256") == EXPECTED_RAW_TREE_SHA256, "External archive source tree SHA changed")
    _require(archive_manifest.get("destination_raw_runs_tree_sha256") == EXPECTED_RAW_TREE_SHA256, "External archive destination tree SHA changed")
    _require(archive_manifest.get("scientific_required_artifact_verified") == 125, "External archive required artifact count changed")
    _require(archive_manifest.get("scientific_job_count") == 25, "External archive job count changed")
    _require(archive_manifest.get("gate24e_closed") is True, "External archive is not linked to closed Gate24E")
    _require(sum(item["size_bytes"] for item in records) == 13958129260, "External archive byte sum changed")
    _require(_tree_sha256(records) == EXPECTED_RAW_TREE_SHA256, "External archive tree SHA does not match")
    if complete:
        for item in records:
            actual = sha256_file(ARCHIVE_RUNS / item["relative_path"])
            _require(actual == item["sha256"], f"External raw checksum mismatch: {item['relative_path']}")
        status = "COMPLETE_SHA256"
        method = "metadata_checksum_manifest_and_full_file_hash"
    else:
        status = "METADATA_AND_CHECKSUM_MANIFEST"
        method = "metadata_checksum_manifest_and_tree_hash"
    return {
        "external_raw_archive_live_verification": status,
        "verification_method": method,
        "archive_path": str(ARCHIVE_RUNS),
        "checksum_manifest_path": str(ARCHIVE_CHECKSUMS),
        "file_count": 275,
        "total_bytes": 13958129260,
        "tree_sha256": EXPECTED_RAW_TREE_SHA256,
    }


def _add_directory(files: set[Path], directory: Path, *, suffixes: set[str] | None = None) -> None:
    if not directory.is_dir():
        return
    for path in directory.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if suffixes is None or path.suffix.lower() in suffixes:
            files.add(path)


def build_inventory() -> list[dict[str, Any]]:
    files: set[Path] = set()
    _add_directory(files, ROOT / "research/validation/prospective")
    _add_directory(files, ROOT / "research/validation/gene_specific/parkin")
    _add_directory(files, ROOT / "src/drosophila_pd_neural/parkin", suffixes={".py"})
    _add_directory(files, ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests", suffixes={".json", ".sha256"})
    _add_directory(files, ROOT / "experiments/gate_24e_blinded_parkin_prediction/results", suffixes={".json", ".csv"})
    _add_directory(files, ROOT / "docs/validation", suffixes={".md"})
    files = {path for path in files if path.name.startswith("gate24e_") or "validation" not in path.parts or path.parent.name != "validation"}
    for relative in CRITICAL_SCRIPTS:
        files.add(ROOT / relative)
    for relative in (
        "pyproject.toml",
        ".github/workflows/tests.yml",
        ".gitattributes",
        "docs/claims/current_claim_lock.md",
        "docs/claims/public_abstract.md",
        "docs/project_summary.md",
        "README.md",
    ):
        files.add(ROOT / relative)
    for relative in REQUIRED_CORE_FILES:
        files.add(ROOT / relative)

    records: list[dict[str, Any]] = []
    for path in sorted(files, key=lambda item: _relative(item)):
        relative = _relative(path)
        if relative.startswith("experiments/gate_25_r2_parkin_reproducibility/"):
            continue
        if relative.startswith("docs/validation/"):
            role = "Gate24E validation and provenance document"
        elif relative.startswith("research/validation/prospective/"):
            role = "Reviewed prospective Parkin protocol, signoff, and runtime provenance"
        elif relative.startswith("research/validation/gene_specific/parkin/"):
            role = "Reviewed Parkin driver-defined mapping and evidence"
        elif relative.startswith("experiments/gate_24e_blinded_parkin_prediction/manifests/"):
            role = "Gate24E execution, freeze, holdout, and relocation manifest"
        elif relative.startswith("experiments/gate_24e_blinded_parkin_prediction/results/"):
            role = "Gate24E frozen analysis result"
        elif relative.startswith("src/drosophila_pd_neural/parkin/"):
            role = "Parkin neural model implementation"
        elif relative.startswith("scripts/"):
            role = "Gate24E execution or audit source"
        elif relative in {
            "README.md",
            "docs/claims/current_claim_lock.md",
            "docs/claims/public_abstract.md",
            "docs/project_summary.md",
        }:
            role = "Current public claim surface"
        else:
            role = "Runtime or claim contract"
        records.append(_record(path, role))
    records.sort(key=lambda item: item["path"])
    _require(records, "Reproducibility inventory is empty")
    required_paths = {str(item) for item in REQUIRED_CORE_FILES}
    found_paths = {record["path"] for record in records}
    _require(required_paths.issubset(found_paths), "Required Gate24E core artifact is absent from inventory")
    return records


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def _report(freeze_sha256: str, inventory_count: int, archive: Mapping[str, Any]) -> str:
    return f"""# Gate25-R2: Parkin reproducibility freeze

**Status:** `GATE25_R2_REPRODUCIBILITY_FREEZE_COMPLETE`

## Purpose

Gate25-R2 is a new reproducibility freeze for the closed Gate24E Parkin
track. The historical pre-Parkin Gate25 report is preserved unchanged. This
freeze audits existing contracts, manifests, checksums, and relocation
provenance only; it does not rerun Gate24E or create new scientific evidence.

## Frozen result

- Gate24E status: `GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE`.
- Scientific result: `NEGATIVE_VALIDATION_RESULT`.
- Cross-assay decision: `DIRECTIONAL_CROSS_ASSAY_DISCORDANCE`.
- Inventory entries: `{inventory_count}` deterministic lightweight files.
- Gate25-R2 canonical freeze SHA256: `{freeze_sha256}`.
- Previous Gate25-R2 freeze SHA256: `{PREVIOUS_R2_FREEZE_SHA256}`.
- Historical Gate25 report SHA256: `{HISTORICAL_REPORT_SHA256}`.
- Refresh reason: `{REFRESH_REASON}`.

The allowed primary claim is: **The frozen Parkin computational perturbation
did not reproduce the held-out biological locomotor impairment direction under
the preregistered cross-assay validation protocol.** Gate24E therefore records
a negative prospective directional validation result.

## Exact provenance lock

- Scientific plan: `4515e1916631b019711154dccb5fb887110d5572e3eb82b7ea5118c643db5aac`.
- Virtual prediction freeze: `f44e9ad10b9fc4795ae2173d3e8b27fc9ea0d8202925bfc08cdcc72d06b00863`.
- Final evidence freeze: `2f056bf5b73ecc4b4de27f714bda681134050c5d82eb2f0f3170b67a5286e967`.
- Raw-run tree: `f6e3de6e96cbe3be0f447ea8eeca463087a9381d1c2d2965807d04df1655faff`.
- Executor SHA256: `{EXPECTED_EXECUTOR_SHA256}`.
- Model commit: `{EXPECTED_MODEL_COMMIT}`.
- External runtime commit: `{EXPECTED_RUNTIME_COMMIT}` (`GATE24E_MEMORY_SAFE`).

The main repository code and the external FlyGym runtime are distinct. The
runtime is not vendored into this repository.

## Raw evidence boundary

The 25-job raw rollout evidence is not committed to Git. It is preserved at
the external archive path recorded in the relocation manifest with 275 files,
13,958,129,260 bytes, and the locked tree SHA256. Current live archive check:
`{archive['external_raw_archive_live_verification']}` using
`{archive['verification_method']}`. This does not make the raw data publicly
available; public availability requires a separately authorized archive
release.

## Reproducibility audit

From the repository root, run:

```powershell
py -3.12 scripts/run_gate25_r2_reproducibility_freeze.py --verify-only
py -3.12 -m compileall -q src scripts tests
py -3.12 -m pytest -q -rs -p no:cacheprovider
git diff --check
```

These commands verify repository hashes, the locked plans and manifests, the
external relocation metadata, the deterministic inventory, and the checksum
manifest. They do not require a new 25-job scientific rerun. A future
intentional replication is a new experiment and must receive a new gate.

## Claim boundary and limitations

This freeze does not support claims of a biologically validated Parkinson
model, a validated Parkinson mechanism, Parkin-expression-specific connectome
root mapping, human or clinical validation, drug validation, successful
phenotype replication, or quantitative biological validation. The biological
holdout supports only the recorded directional cross-assay interpretation;
the quantitative mismatch remains explicit.

## Merge readiness

`READY_FOR_RESEARCH_BRANCH_MERGE_REVIEW` when Gate24E remains closed, the R2
freeze and tests pass, no critical Gate24E changes are uncommitted, and the
historical Gate25 report remains unchanged. This task does not merge `main`.
"""


def _canonical_freeze_payload(
    inventory: Mapping[str, Any],
    archive: Mapping[str, Any],
    inventory_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "gate25-r2-parkin-reproducibility-freeze-v1",
        "status": "GATE25_R2_REPRODUCIBILITY_FREEZE_COMPLETE",
        "track": "PARKIN_GATE24E_DIRECTIONAL_VALIDATION",
        "gate24e_final_status": "GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE",
        "scientific_result": "NEGATIVE_VALIDATION_RESULT",
        "cross_assay_decision": "DIRECTIONAL_CROSS_ASSAY_DISCORDANCE",
        "biological_validation_supported": False,
        "clinical_validation_supported": False,
        "quantitative_cross_assay_validation": False,
        "gpu": False,
        "simulation": False,
        "new_scientific_analysis": False,
        "historical_gate25_preserved": True,
        "historical_gate25_report_sha256": HISTORICAL_REPORT_SHA256,
        "previous_gate25_r2_freeze_sha256": PREVIOUS_R2_FREEZE_SHA256,
        "refresh_reason": REFRESH_REASON,
        "scientific_result_changed": False,
        "gate24e_evidence_changed": False,
        "raw_archive_changed": False,
        "anchor_commit": ANCHOR_COMMIT,
        "locked_identifiers": {
            "scientific_plan_sha256": EXPECTED_PLAN_SHA256,
            "virtual_prediction_freeze_sha256": EXPECTED_VIRTUAL_FREEZE_SHA256,
            "final_evidence_freeze_sha256": EXPECTED_FINAL_EVIDENCE_SHA256,
            "raw_runs_tree_sha256": EXPECTED_RAW_TREE_SHA256,
            "executor_sha256": EXPECTED_EXECUTOR_SHA256,
            "model_commit": EXPECTED_MODEL_COMMIT,
            "runtime_commit": EXPECTED_RUNTIME_COMMIT,
        },
        "inventory": {
            "path": _relative(INVENTORY_PATH),
            "file_count": inventory["inventory_file_count"],
            "sha256": inventory_sha256,
        },
        "raw_archive": dict(archive),
        "raw_archive_policy": {
            "committed_to_git": False,
            "externally_preserved": True,
            "publicly_available": False,
            "relocation_changes_scientific_result": False,
        },
        "runtime": {
            "repository_code_and_external_runtime_are_distinct": True,
            "runtime_artifact_profile": "GATE24E_MEMORY_SAFE",
            "runtime_is_vendored": False,
        },
        "claim_boundary": {
            "allowed_primary_claim": "The frozen Parkin computational perturbation did not reproduce the held-out biological locomotor impairment direction under the preregistered cross-assay validation protocol.",
            "forbidden": [
                "biologically validated Parkinson model",
                "validated Parkinson mechanism",
                "Parkin-expression-specific connectome root mapping",
                "human/clinical validation",
                "drug validation",
                "successful phenotype replication",
                "quantitative biological validation",
            ],
        },
        "reproducibility_scope": [
            "scientific question",
            "model implementation",
            "driver-defined mapping",
            "neural transform",
            "checkpoint grid",
            "runtime provenance",
            "scientific plan",
            "executor",
            "execution provenance",
            "artifact inventory",
            "frozen virtual prediction",
            "biological holdout opening",
            "directional comparison",
            "final negative decision",
            "human review",
            "raw archive relocation provenance",
        ],
    }


def _expected_checksum_records(inventory: Mapping[str, Any], freeze: Mapping[str, Any], report: Path) -> dict[str, str]:
    records = {item["path"]: item["sha256"] for item in inventory["files"]}
    records[_relative(INVENTORY_PATH)] = sha256_file(INVENTORY_PATH)
    records[_relative(FREEZE_PATH)] = sha256_file(FREEZE_PATH)
    records[_relative(report)] = sha256_file(report)
    return records


def run(*, verify_archive: bool = False) -> dict[str, Any]:
    """Create the deterministic R2 package from already-closed evidence."""
    _validate_historical_gate25()
    closure = _validate_closed_gate24e()
    archive = verify_external_archive(complete=verify_archive)
    records = build_inventory()
    inventory = {
        "schema_version": "gate25-r2-parkin-reproducibility-inventory-v1",
        "status": "REPRODUCIBILITY_INVENTORY_COMPLETE",
        "anchor_commit": ANCHOR_COMMIT,
        "track": "PARKIN_GATE24E_DIRECTIONAL_VALIDATION",
        "gate24e_closed": True,
        "scientific_result": "NEGATIVE_VALIDATION_RESULT",
        "cross_assay_decision": "DIRECTIONAL_CROSS_ASSAY_DISCORDANCE",
        "inventory_file_count": len(records),
        "files": records,
        "raw_archive": {
            "committed_to_git": False,
            "externally_preserved": True,
            "publicly_available": False,
            "file_count": 275,
            "total_bytes": 13958129260,
            "tree_sha256": EXPECTED_RAW_TREE_SHA256,
            "live_verification": archive["external_raw_archive_live_verification"],
        },
        "locked_gate24e_identifiers": closure["locked"],
    }
    _write_json(INVENTORY_PATH, inventory)
    inventory_sha256 = sha256_file(INVENTORY_PATH)
    payload = _canonical_freeze_payload(inventory, archive, inventory_sha256)
    freeze_sha256 = hashlib.sha256(canonical_json({"freeze": payload, "inventory": inventory})).hexdigest()
    freeze = dict(payload)
    freeze["gate25_r2_freeze_sha256"] = freeze_sha256
    _write_json(FREEZE_PATH, freeze)
    _write_text(REPORT_PATH, _report(freeze_sha256, len(records), archive))
    checksums = _expected_checksum_records(inventory, freeze, REPORT_PATH)
    _write_text(CHECKSUMS_PATH, "\n".join(f"{digest}  {path}" for path, digest in sorted(checksums.items())))
    return freeze


def _verify_inventory(inventory: Mapping[str, Any]) -> None:
    files = inventory.get("files")
    _require(isinstance(files, list) and files, "R2 inventory files are missing")
    paths = [item.get("path") for item in files if isinstance(item, dict)]
    _require(paths == sorted(paths), "R2 inventory is not sorted deterministically")
    _require(len(paths) == len(set(paths)), "R2 inventory contains duplicate paths")
    for item in files:
        _require(isinstance(item, dict), "R2 inventory contains an invalid record")
        path = ROOT / str(item["path"])
        _require(path.is_file(), f"Inventory artifact is missing: {item['path']}")
        _require(path.stat().st_size == item["size_bytes"], f"Inventory size changed: {item['path']}")
        _require(sha256_file(path) == item["sha256"], f"Inventory checksum changed: {item['path']}")


def _verify_checksum_manifest(inventory: Mapping[str, Any]) -> None:
    _require(CHECKSUMS_PATH.is_file(), "R2 checksum manifest is missing")
    expected = {item["path"]: item["sha256"] for item in inventory["files"]}
    expected[_relative(INVENTORY_PATH)] = sha256_file(INVENTORY_PATH)
    expected[_relative(FREEZE_PATH)] = sha256_file(FREEZE_PATH)
    expected[_relative(REPORT_PATH)] = sha256_file(REPORT_PATH)
    observed: dict[str, str] = {}
    for line in CHECKSUMS_PATH.read_text(encoding="utf-8").splitlines():
        digest, path = line.split("  ", maxsplit=1)
        _require(path not in observed, f"Duplicate checksum path: {path}")
        observed[path] = digest
    _require(list(observed) == sorted(observed), "R2 checksum manifest is not sorted")
    _require(observed == expected, "R2 checksum manifest does not match frozen artifacts")
    for path, digest in observed.items():
        _require(sha256_file(ROOT / path) == digest, f"Checksum manifest mismatch: {path}")


def audit() -> dict[str, Any]:
    """Audit the committed R2 package without writing or running science."""
    _validate_historical_gate25()
    closure = _validate_closed_gate24e()
    archive = verify_external_archive(complete=False)
    inventory = _json(INVENTORY_PATH)
    freeze = _json(FREEZE_PATH)
    _require(inventory.get("status") == "REPRODUCIBILITY_INVENTORY_COMPLETE", "R2 inventory status changed")
    _require(freeze.get("status") == "GATE25_R2_REPRODUCIBILITY_FREEZE_COMPLETE", "R2 freeze status changed")
    _require(freeze.get("gate24e_final_status") == "GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE", "R2 Gate24E status changed")
    _require(freeze.get("scientific_result") == "NEGATIVE_VALIDATION_RESULT", "R2 negative result changed")
    _require(freeze.get("biological_validation_supported") is False, "R2 biological validation claim changed")
    _require(freeze.get("raw_archive_policy", {}).get("publicly_available") is False, "R2 incorrectly claims raw archive is public")
    _require(freeze.get("previous_gate25_r2_freeze_sha256") == PREVIOUS_R2_FREEZE_SHA256, "Previous R2 freeze SHA is missing")
    _require(freeze.get("refresh_reason") == REFRESH_REASON, "R2 refresh reason changed")
    _require(freeze.get("scientific_result_changed") is False, "R2 claims a scientific result change")
    _require(freeze.get("gate24e_evidence_changed") is False, "R2 claims Gate24E evidence changed")
    _require(freeze.get("raw_archive_changed") is False, "R2 claims raw archive changed")
    _require(inventory.get("anchor_commit") == ANCHOR_COMMIT, "R2 anchor commit changed")
    _require(inventory.get("raw_archive", {}).get("tree_sha256") == EXPECTED_RAW_TREE_SHA256, "R2 raw tree SHA changed")
    _verify_inventory(inventory)
    payload = dict(freeze)
    stored_hash = payload.pop("gate25_r2_freeze_sha256", None)
    recomputed = hashlib.sha256(canonical_json({"freeze": payload, "inventory": inventory})).hexdigest()
    _require(stored_hash == recomputed, "R2 canonical freeze hash is stale")
    _verify_checksum_manifest(inventory)
    return {
        "status": freeze["status"],
        "gate25_r2_freeze_sha256": stored_hash,
        "inventory_file_count": inventory["inventory_file_count"],
        "external_raw_archive_live_verification": archive["external_raw_archive_live_verification"],
        "gate24e_final_status": closure["decision"]["status"],
        "gpu": False,
        "simulation": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-archive", action="store_true", help="hash all 275 files in the external D archive")
    parser.add_argument("--verify-only", action="store_true", help="audit the committed R2 package without writing files")
    args = parser.parse_args(argv)
    try:
        result = audit() if args.verify_only else run(verify_archive=args.verify_archive)
    except (OSError, ReproducibilityFreezeError, KeyError, ValueError) as exc:
        print(f"Status: GATE25_R2_REPRODUCIBILITY_FREEZE_BLOCKED\nReason: {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
