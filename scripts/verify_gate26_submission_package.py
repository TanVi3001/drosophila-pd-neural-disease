"""Independently verify the Gate 26 manuscript package without running GPU."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "experiments/gate_26_submission_package/manifests/submission_package_manifest.json"
DEFAULT_CHECKSUMS = ROOT / "experiments/gate_26_submission_package/manifests/checksums.sha256"


class IndependentVerificationError(ValueError):
    """Raised when a Gate 26 artifact cannot be reproduced from its checksum."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(manifest_path: Path = DEFAULT_MANIFEST, checksum_path: Path = DEFAULT_CHECKSUMS) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "SUBMISSION_PACKAGE_READY_FOR_INTERNAL_REVIEW":
        raise IndependentVerificationError("Gate 26 package is not ready for internal review")
    if any(manifest.get(key) is not True for key in ("no_gpu", "no_simulation", "no_calibration", "no_holdout_validation", "no_tuning")):
        raise IndependentVerificationError("Gate 26 execution boundary is incomplete")
    if manifest.get("boundaries", {}).get("biological_parkinson_validation") is not False:
        raise IndependentVerificationError("Biological-validation boundary is missing")
    if manifest.get("boundaries", {}).get("gene_specific_validation") is not False:
        raise IndependentVerificationError("Gene-specific boundary is missing")

    checked = 0
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        try:
            expected, relative = line.split("  ", maxsplit=1)
        except ValueError as exc:
            raise IndependentVerificationError("Malformed Gate 26 checksum file") from exc
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != expected:
            raise IndependentVerificationError(f"Checksum mismatch: {relative}")
        checked += 1
    if checked < 10:
        raise IndependentVerificationError("Submission package checksum coverage is too small")
    return {"status": "INDEPENDENT_REPRODUCIBILITY_CHECK_PASS", "checked_artifacts": checked}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--checksums", type=Path, default=DEFAULT_CHECKSUMS)
    args = parser.parse_args(argv)
    try:
        result = verify(args.manifest, args.checksums)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Status: INDEPENDENT_REPRODUCIBILITY_CHECK_FAILED\nReason: {exc}")
        return 1
    print(f"Status: {result['status']}\nChecked artifacts: {result['checked_artifacts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
