"""Verify, archive, and safely relocate the completed Gate24E raw runs.

The executable path is storage-only. It never imports scientific metrics or
starts a simulator. Deletion is allowed only after complete source and
destination verification and requires the explicit ``--execute`` flag.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
RUNS_RELATIVE = Path("experiments/gate_24e_blinded_parkin_prediction/runs")
SOURCE = ROOT / RUNS_RELATIVE
ARCHIVE_EVIDENCE = Path("D:/EHouse/Drosophila_Archive/Gate24E_Final_Raw_Evidence")
DESTINATION = ARCHIVE_EVIDENCE / "runs"
ARCHIVE_MANIFEST = ARCHIVE_EVIDENCE / "manifests/gate24e_raw_runs_archive_manifest.json"
ARCHIVE_CHECKSUMS = ARCHIVE_EVIDENCE / "manifests/raw_runs_checksums.sha256"
RELOCATION_MANIFEST = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_raw_runs_relocation.json"
RELOCATION_REPORT = ROOT / "docs/validation/gate24e_raw_runs_verified_relocation.md"
FAILURE_REPORT = ROOT / "docs/validation/gate24e_raw_runs_relocation_failure.md"
EXECUTION_MANIFEST = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/scientific_batch_execution.json"
ARTIFACT_INVENTORY = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/scientific_batch_artifact_inventory.json"
FINAL_SIGNOFF = ROOT / "research/validation/prospective/gate24e_final_validation_reviewer_signoff.json"
FINAL_EVIDENCE_FREEZE = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_final_evidence_freeze.json"
FINAL_DECISION = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_final_validation_decision.json"

EXPECTED_FINAL_STATUS = "GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE"
EXPECTED_FINAL_FREEZE = "2f056bf5b73ecc4b4de27f714bda681134050c5d82eb2f0f3170b67a5286e967"
EXPECTED_VIRTUAL_FREEZE = "f44e9ad10b9fc4795ae2173d3e8b27fc9ea0d8202925bfc08cdcc72d06b00863"
EXPECTED_PLAN = "4515e1916631b019711154dccb5fb887110d5572e3eb82b7ea5118c643db5aac"
TWO_GIB = 2 * 1024 * 1024 * 1024


class ArchiveError(RuntimeError):
    """Raised before deletion when an archive precondition fails."""


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ArchiveError(f"Expected JSON object: {path}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ArchiveError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory_tree(root: Path) -> list[dict[str, Any]]:
    _require(root.is_dir(), f"source/destination directory is missing: {root}")
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_symlink():
            raise ArchiveError(f"symbolic links are not allowed in raw archive: {path}")
        if path.is_file():
            records.append(
                {
                    "relative_path": path.relative_to(root).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return records


def tree_sha256(records: Iterable[Mapping[str, Any]]) -> str:
    canonical = [dict(record) for record in records]
    canonical.sort(key=lambda item: item["relative_path"])
    payload = json.dumps(canonical, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_final_closure(root: Path = ROOT) -> None:
    signoff = _json(root / FINAL_SIGNOFF.relative_to(ROOT))
    freeze = _json(root / FINAL_EVIDENCE_FREEZE.relative_to(ROOT))
    decision = _json(root / FINAL_DECISION.relative_to(ROOT))
    _require(signoff.get("status") == "GATE24E_FINAL_VALIDATION_REVIEW_APPROVED", "final human signoff is not approved")
    _require(signoff.get("decision") == "APPROVED_GATE24E_DIRECTIONAL_DISCORDANCE_CLOSURE", "final closure decision is not approved")
    _require(signoff.get("accepted_negative_result") is True, "negative result was not accepted")
    _require(signoff.get("gate24e_closed") is True, "Gate24E is not closed")
    _require(signoff.get("retuning_allowed") is False, "retuning is allowed in signoff")
    _require(signoff.get("gate24e_final_evidence_freeze_sha256") == EXPECTED_FINAL_FREEZE, "final evidence freeze SHA mismatch")
    _require(freeze.get("gate24e_final_evidence_freeze_sha256") == EXPECTED_FINAL_FREEZE, "final evidence freeze is not locked")
    _require(decision.get("status") == EXPECTED_FINAL_STATUS, "final decision status changed")
    _require(decision.get("scientific_result") == "NEGATIVE_VALIDATION_RESULT", "scientific result changed")
    _require(freeze.get("virtual_prediction_freeze_sha256") is None, "unexpected mutable virtual freeze field")
    _require(decision.get("virtual_prediction_freeze_sha256") == EXPECTED_VIRTUAL_FREEZE, "prediction freeze identifier is missing")


def validate_execution_manifests(root: Path = ROOT) -> None:
    execution = _json(root / EXECUTION_MANIFEST.relative_to(ROOT))
    inventory = _json(root / ARTIFACT_INVENTORY.relative_to(ROOT))
    _require(execution.get("planned_job_count") == 25, "planned scientific job count is not 25")
    _require(execution.get("executed_job_count") == 25, "executed scientific job count is not 25")
    _require(execution.get("completed_job_count") == 25, "completed scientific job count is not 25")
    _require(execution.get("failed_job_count") == 0, "scientific execution contains failed jobs")
    _require(execution.get("gpu_jobs_executed") == 25, "GPU job count is not 25")
    _require(execution.get("simulation_jobs_executed") == 25, "simulation job count is not 25")
    _require(inventory.get("job_count") == 25, "artifact inventory job count is not 25")
    _require(inventory.get("artifact_count") == 125, "artifact inventory count is not 125")
    _require(inventory.get("technical_artifact_qc") == "PASS", "scientific artifact inventory QC is not PASS")
    _require(inventory.get("scientific_plan_sha256") == EXPECTED_PLAN, "scientific plan SHA mismatch")


def required_artifacts(inventory: Mapping[str, Any], root: Path = ROOT) -> list[dict[str, Any]]:
    required: list[dict[str, Any]] = []
    prefix = RUNS_RELATIVE.as_posix() + "/"
    for job in inventory.get("jobs", []):
        for artifact in (job.get("artifacts") or {}).values():
            relative = artifact.get("path", "")
            _require(relative.startswith(prefix), f"inventory artifact is outside runs tree: {relative}")
            required.append(
                {
                    "relative_path": relative[len(prefix):],
                    "size_bytes": artifact.get("size_bytes"),
                    "sha256": artifact.get("sha256"),
                }
            )
    _require(len(required) == 125, "inventory does not enumerate exactly 125 required artifacts")
    return required


def verify_required_artifacts(
    root: Path,
    records: Iterable[Mapping[str, Any]],
    actual_records: Iterable[Mapping[str, Any]] | None = None,
) -> None:
    actual = {item["relative_path"]: item for item in (actual_records if actual_records is not None else inventory_tree(root))}
    failures = []
    for expected in records:
        path = expected["relative_path"]
        found = actual.get(path)
        if found is None:
            failures.append(f"missing:{path}")
        elif found["size_bytes"] != expected["size_bytes"] or found["sha256"] != expected["sha256"]:
            failures.append(f"mismatch:{path}")
    _require(not failures, "required scientific artifact verification failed: " + ",".join(failures[:5]))


def compare_inventories(source: list[dict[str, Any]], destination: list[dict[str, Any]]) -> None:
    _require(len(source) == len(destination), "source and destination file counts differ")
    _require(source == destination, "source and destination raw tree inventories differ")


def copy_tree(source: Path, destination: Path) -> None:
    _require(not destination.exists(), f"archive destination already exists: {destination}")
    destination.mkdir(parents=True)
    for record in inventory_tree(source):
        source_file = source / Path(record["relative_path"])
        destination_file = destination / Path(record["relative_path"])
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination_file)


def write_archive_metadata(
    source_records: list[dict[str, Any]],
    destination_records: list[dict[str, Any]],
    source_total_bytes: int,
    e_free_before: int,
    d_free_before: int,
    destination: Path,
    required_count: int,
) -> None:
    archive_manifest = {
        "schema_version": "gate24e-raw-runs-archive-v1",
        "status": "GATE24E_RAW_RUNS_ARCHIVE_VERIFIED",
        "source_original_path": str(SOURCE),
        "destination_archive_path": str(destination),
        "source_file_count": len(source_records),
        "source_total_bytes": source_total_bytes,
        "source_raw_runs_tree_sha256": tree_sha256(source_records),
        "destination_raw_runs_tree_sha256": tree_sha256(destination_records),
        "scientific_required_artifact_count": 125,
        "scientific_required_artifact_verified": required_count,
        "scientific_job_count": 25,
        "scientific_plan_sha256": EXPECTED_PLAN,
        "virtual_prediction_freeze_sha256": EXPECTED_VIRTUAL_FREEZE,
        "gate24e_final_evidence_freeze_sha256": EXPECTED_FINAL_FREEZE,
        "gate24e_closed": True,
        "scientific_result": "NEGATIVE_VALIDATION_RESULT",
        "copy_verified": True,
        "source_deletion_authorized": True,
        "GPU": False,
        "simulation": False,
        "e_free_before": e_free_before,
        "d_free_before": d_free_before,
    }
    ARCHIVE_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE_MANIFEST.write_text(json.dumps(archive_manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    checksum_lines = [f"{item['sha256']}  {item['relative_path']}" for item in destination_records]
    ARCHIVE_CHECKSUMS.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8", newline="\n")


def safe_delete_source(root: Path = ROOT) -> None:
    expected = (root / RUNS_RELATIVE).resolve()
    source = SOURCE.resolve() if SOURCE.exists() else expected
    _require(source == expected, f"refusing to delete unexpected path: {source}")
    _require(source.name == "runs" and source.parent.name == "gate_24e_blinded_parkin_prediction", "refusing to delete non-runs path")
    _require(source.is_dir(), "source runs directory is already absent")
    shutil.rmtree(source)


def write_relocation_artifacts(summary: Mapping[str, Any], root: Path = ROOT) -> None:
    relocation = dict(summary)
    relocation.update(
        {
            "schema_version": "gate24e-raw-runs-relocation-v1",
            "status": "RAW_RUNS_RELOCATED_AND_VERIFIED",
            "original_local_copy_deleted": True,
            "raw_scientific_evidence_preserved": True,
            "relocation_changes_scientific_result": False,
            "GPU": False,
            "simulation": False,
        }
    )
    RELOCATION_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    RELOCATION_MANIFEST.write_text(json.dumps(relocation, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    report = f"""# Gate 24E-S4M: Verified raw-run relocation

- Starting HEAD: `{summary['starting_head']}`.
- Source: `{summary['source_path']}`.
- Archive: `{summary['archive_path']}`.
- Source files: `{summary['source_file_count']}`.
- Source bytes: `{summary['source_total_bytes']}`.
- Source tree SHA256: `{summary['source_raw_runs_tree_sha256']}`.
- Destination files: `{summary['destination_file_count']}`.
- Destination tree SHA256: `{summary['destination_raw_runs_tree_sha256']}`.
- Whole-tree hash match: `true`.
- Required scientific artifacts: `125/125`.
- Copy verification: `PASS`.
- Source deletion performed only after all checks passed: `true`.
- E free before/after: `{summary['e_free_before']}` / `{summary['e_free_after']}` bytes.
- D free before/after: `{summary['d_free_before']}` / `{summary['d_free_after']}` bytes.
- E bytes reclaimed: `{summary['e_bytes_reclaimed']}`.
- Gate24E result changed: `false`.
- GPU: `false`.
- Simulation: `false`.

The archive contains the complete raw run tree and its checksum file. The D:
archive is not committed to Git. The repository records only lightweight
provenance metadata; raw rollout files remain outside the repository.
"""
    RELOCATION_REPORT.parent.mkdir(parents=True, exist_ok=True)
    RELOCATION_REPORT.write_text(report, encoding="utf-8", newline="\n")


def write_failure_report(message: str, root: Path = ROOT) -> None:
    FAILURE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    FAILURE_REPORT.write_text(
        "# Gate 24E-S4M relocation failure\n\n"
        "No source deletion was performed. This is a technical failure only.\n\n"
        f"- Detail: `{message}`\n",
        encoding="utf-8",
        newline="\n",
    )


def relocate(root: Path = ROOT, *, execute: bool = False) -> dict[str, Any]:
    _require(execute, "explicit --execute is required before copy/deletion")
    validate_final_closure(root)
    validate_execution_manifests(root)
    _require(not ARCHIVE_EVIDENCE.exists(), f"archive evidence directory already exists: {ARCHIVE_EVIDENCE}")
    _require(SOURCE.is_dir(), f"raw runs source is missing: {SOURCE}")

    source_records = inventory_tree(SOURCE)
    source_directory_count = sum(1 for path in SOURCE.rglob("*") if path.is_dir())
    source_total_bytes = sum(item["size_bytes"] for item in source_records)
    e_free_before = shutil.disk_usage(SOURCE.anchor or "E:/").free
    d_free_before = shutil.disk_usage("D:/").free
    _require(d_free_before > source_total_bytes + TWO_GIB, "D: free space is below source bytes plus 2 GiB")
    inventory = _json(root / ARTIFACT_INVENTORY.relative_to(ROOT))
    required = required_artifacts(inventory, root)
    verify_required_artifacts(SOURCE, required, source_records)

    copy_tree(SOURCE, DESTINATION)
    destination_records = inventory_tree(DESTINATION)
    compare_inventories(source_records, destination_records)
    verify_required_artifacts(DESTINATION, required, destination_records)
    _require(tree_sha256(source_records) == tree_sha256(destination_records), "whole-tree SHA256 mismatch")
    write_archive_metadata(source_records, destination_records, source_total_bytes, e_free_before, d_free_before, DESTINATION, len(required))

    safe_delete_source(root)
    _require(not SOURCE.exists(), "source runs directory remains after deletion")
    _require(DESTINATION.is_dir(), "archive runs directory is missing after deletion")
    _require(ARCHIVE_MANIFEST.is_file() and ARCHIVE_CHECKSUMS.is_file(), "archive metadata is incomplete")
    e_free_after = shutil.disk_usage("E:/").free
    d_free_after = shutil.disk_usage("D:/").free
    _require(e_free_after > e_free_before, "E: free space did not increase")
    summary = {
        "starting_head": _current_head(root),
        "source_path": str(SOURCE),
        "archive_path": str(DESTINATION),
        "source_file_count": len(source_records),
        "source_directory_count": source_directory_count,
        "destination_file_count": len(destination_records),
        "source_total_bytes": source_total_bytes,
        "source_raw_runs_tree_sha256": tree_sha256(source_records),
        "destination_raw_runs_tree_sha256": tree_sha256(destination_records),
        "e_free_before": e_free_before,
        "e_free_after": e_free_after,
        "e_bytes_reclaimed": e_free_after - e_free_before,
        "d_free_before": d_free_before,
        "d_free_after": d_free_after,
        "required_scientific_artifacts_verified": len(required),
        "job_count": 25,
        "copy_verified": True,
        "gate24e_final_evidence_freeze_sha256": EXPECTED_FINAL_FREEZE,
        "virtual_prediction_freeze_sha256": EXPECTED_VIRTUAL_FREEZE,
        "scientific_result": "NEGATIVE_VALIDATION_RESULT",
    }
    write_relocation_artifacts(summary, root)
    return summary


def _current_head(root: Path) -> str:
    import subprocess

    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="copy, verify, then delete only the exact E: runs directory")
    args = parser.parse_args()
    try:
        result = relocate(ROOT, execute=args.execute)
    except ArchiveError as exc:
        write_failure_report(str(exc), ROOT)
        print(f"GATE24E_RAW_ARCHIVE_BLOCKED: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
