"""Manifest va checksum cho run nghien cuu."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(path: str | Path, *, inputs: list[dict[str, Any]], config: dict[str, Any], status: str) -> None:
    document = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "inputs": inputs,
        "config": config,
        "scientific_scope": (
            "Mo phong perturbation neural tinh toan; khong phai mo hinh Parkinson sinh hoc, "
            "chan doan, du doan lam sang hay danh gia thuoc."
        ),
    }
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
