"""Kiểm tra đầu vào neural ngoài repository, không chạy simulation."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "brain_body_bridge.py",
    "code/run_pytorch.py",
    "data/2025_Completeness_783.csv",
    "data/2025_Connectivity_783.parquet",
    "data/flywire_annotations.tsv",
    "data/plastic_weights.pt",
)


def _digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _manifest_integrity(root: Path, checks: dict[str, bool]) -> dict[str, object]:
    manifest_path = root / "source_manifest.json"
    if not manifest_path.is_file():
        return {
            "status": "UNVERIFIED_NO_MANIFEST",
            "manifest": str(manifest_path),
            "files": {},
            "message": "Khong co source_manifest.json; chi kiem tra su ton tai cua file.",
        }
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        records = manifest["files"]
        declared = {
            str(record["path"]): {
                "size": int(record["size"]),
                "sha256": str(record["sha256"]).lower(),
            }
            for record in records
        }
        catalog = json.loads(
            (REPOSITORY_ROOT / "data/source_catalog.json").read_text(encoding="utf-8")
        )["verified_external_source"]
        pinned = {
            str(record["path"]): {
                "size": int(record["size"]),
                "sha256": str(record["sha256"]).lower(),
            }
            for record in catalog["files"]
        }
        if manifest.get("source_repository") != catalog["repository"]:
            raise ValueError("source_repository khong khop catalog")
        if manifest.get("source_commit") != catalog["commit"]:
            raise ValueError("source_commit khong khop catalog")
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return {
            "status": "FAILED",
            "manifest": str(manifest_path),
            "files": {},
            "message": f"Manifest khong hop le: {exc}",
        }

    file_results: dict[str, dict[str, object]] = {}
    failed: list[str] = []
    for relative, present in checks.items():
        if not present:
            continue
        path = root / relative
        contract = declared.get(relative)
        pinned_contract = pinned.get(relative)
        if contract is None or pinned_contract is None:
            file_results[relative] = {"status": "MISSING_FROM_MANIFEST"}
            failed.append(relative)
            continue
        if contract != pinned_contract:
            file_results[relative] = {"status": "MANIFEST_DIFFERS_FROM_CATALOG"}
            failed.append(relative)
            continue
        actual_size = path.stat().st_size
        actual_hash = _digest(path)
        valid = actual_size == contract["size"] and actual_hash == contract["sha256"]
        file_results[relative] = {
            "status": "PASS" if valid else "MISMATCH",
            "size": actual_size,
            "sha256": actual_hash,
        }
        if not valid:
            failed.append(relative)
    return {
        "status": "VERIFIED_SHA256" if not failed else "FAILED",
        "manifest": str(manifest_path),
        "files": file_results,
        "message": (
            "Tat ca file bat buoc khop size va SHA256 trong manifest."
            if not failed
            else f"File khong khop manifest: {', '.join(failed)}"
        ),
    }


def _license_status(root: Path) -> str:
    license_path = root / "LICENSE"
    if not license_path.is_file():
        return "UNVERIFIED"
    try:
        text = license_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return "UNVERIFIED"
    return "VERIFIED_MIT" if "MIT License" in text else "UNVERIFIED"


def inspect_brain_root(root: Path) -> dict[str, object]:
    checks = {relative: (root / relative).is_file() for relative in REQUIRED_FILES}
    missing = [relative for relative, present in checks.items() if not present]
    integrity = _manifest_integrity(root, checks)
    if missing:
        status = "WAITING_BRAIN_DATA"
    elif integrity["status"] == "FAILED":
        status = "INVALID_BRAIN_DATA"
    else:
        status = "READY"
    return {
        "status": status,
        "brain_root": str(root),
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "required_files": checks,
        "integrity": integrity,
        "license_status": _license_status(root),
        "data_license_status": "REVIEW_CC_BY_NC_4_0",
        "simulation_run": False,
        "message": (
            f"Thieu dau vao neural: {', '.join(missing)}"
            if missing
            else integrity["message"]
        ),
    }


def main(argv: list[str] | None = None) -> int:
    # Keep CLI help ASCII so it remains usable on Windows consoles using CP1252.
    parser = argparse.ArgumentParser(description="Check external neural inputs without running simulation.")
    parser.add_argument("--brain-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = inspect_brain_root(args.brain_root)
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    print(text, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    return 0 if report["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
