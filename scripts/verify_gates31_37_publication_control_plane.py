"""Verify local Gate 31--37 artifacts without performing external actions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "experiments/gate_37_acceptance_archive/manifests/publication_control_plane_manifest.json"
CHECKSUMS = ROOT / "experiments/gate_37_acceptance_archive/manifests/checksums.sha256"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("status") != "PUBLICATION_CONTROL_PLANE_READY":
        raise ValueError("Unexpected global publication-control status")
    for field in (
        "no_gpu", "no_simulation", "no_calibration", "no_holdout_validation",
        "no_tuning", "no_external_release", "no_external_submission",
    ):
        if manifest.get(field) is not True:
            raise ValueError(f"Boundary missing: {field}")
    checked = 0
    for line in CHECKSUMS.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", maxsplit=1)
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != digest:
            raise ValueError(f"Checksum mismatch: {relative}")
        checked += 1
    if checked < 30:
        raise ValueError("Insufficient Gate 31--37 checksum coverage")
    return {"status": "PUBLICATION_CONTROL_PLANE_LOCAL_VERIFICATION_PASS", "checked_artifacts": checked}


def main() -> int:
    try:
        result = verify()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Status: PUBLICATION_CONTROL_PLANE_LOCAL_VERIFICATION_FAILED\nReason: {exc}")
        return 1
    print(f"Status: {result['status']}\nChecked artifacts: {result['checked_artifacts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
