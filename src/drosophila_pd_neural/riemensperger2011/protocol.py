"""Small, deterministic helpers shared by the Riemensperger 2011 gates."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Iterable, Mapping

import yaml


ROOT = Path(__file__).resolve().parents[3]


def utc_now() -> str:
    """Return an explicit UTC timestamp for an artifact manifest."""

    return datetime.now(UTC).isoformat()


def sha256_file(path: Path) -> str:
    """Return a streaming SHA256 checksum for an existing file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(path: Path) -> str:
    """Prefer a portable repository-relative path in committed artifacts."""

    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def git_commit() -> str:
    """Read the checked-out commit without failing an artifact write."""

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def read_yaml(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        raise ValueError(f"YAML must be a mapping: {path}")
    return document


def write_yaml(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(dict(document), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {str(key): str(value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def write_csv_rows(path: Path, fieldnames: Iterable[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))


def write_json(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(document), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"JSON must be a mapping: {path}")
    return document


def numeric(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric.") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite.")
    return result


def build_manifest(
    *,
    status: str,
    config_paths: Iterable[Path] = (),
    input_paths: Iterable[Path] = (),
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact, provenance-first manifest without fabricating inputs."""

    def reference(path: Path) -> dict[str, Any]:
        resolved = path.resolve()
        record: dict[str, Any] = {"path": project_path(resolved)}
        if resolved.is_file():
            record["sha256"] = sha256_file(resolved)
            record["size_bytes"] = resolved.stat().st_size
        else:
            record["status"] = "MISSING"
        return record

    payload: dict[str, Any] = {
        "schema_version": "riemensperger-2011-replication-manifest-v1",
        "created_at_utc": utc_now(),
        "status": status,
        "git_commit": git_commit(),
        "python_version": platform.python_version(),
        "extension_commit": git_commit(),
        "config_inputs": [reference(path) for path in config_paths],
        "data_inputs": [reference(path) for path in input_paths],
        "simulation_run": False,
        "data_fabricated": False,
    }
    if extra:
        payload.update(dict(extra))
    return payload


def require_status(path: Path, expected: str) -> dict[str, Any]:
    document = read_json(path)
    received = str(document.get("status", ""))
    if received != expected:
        raise RuntimeError(
            f"Required status {expected}, received {received or 'MISSING'} "
            f"from {project_path(path)}."
        )
    return document
