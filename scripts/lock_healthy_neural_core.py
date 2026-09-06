"""Lock a verified healthy neural source reference without running simulation."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_neural_inputs import inspect_brain_root


def _git_commit(root: Path) -> str | None:
    if not root.is_dir():
        return None
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    commit = result.stdout.strip()
    return commit or None


def build_lock_manifest(
    *,
    brain_root: Path,
    inspection: Mapping[str, Any],
    project_commit: str | None,
) -> dict[str, Any]:
    """Build an auditable reference lock; no source bytes are copied."""
    integrity = inspection.get("integrity") or {}
    source_files = integrity.get("files") or {}
    ready = inspection.get("status") == "READY"
    license_ready = inspection.get("license_status") == "VERIFIED_MIT"
    if ready and license_ready:
        status = "HEALTHY_NEURAL_CORE_LOCKED"
    elif not ready:
        status = "WAITING_BRAIN_DATA"
    else:
        status = "WAITING_LICENSE_REVIEW"
    return {
        "schema_version": "healthy-neural-core-lock-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "simulation_run": False,
        "disease_layer_enabled": False,
        "calibration_run": False,
        "holdout_validation_run": False,
        "healthy_core": {
            "root": str(brain_root.resolve()),
            "immutable_reference": True,
            "source_bytes_copied": False,
            "source_commit": _git_commit(brain_root),
            "project_commit": project_commit,
            "required_files": inspection.get("required_files", {}),
            "files": source_files,
            "integrity_status": integrity.get("status", "NOT_CHECKED"),
            "license_status": inspection.get("license_status", "UNVERIFIED"),
            "data_license_status": inspection.get("data_license_status", "UNVERIFIED"),
        },
        "disease_branch_policy": {
            "healthy_core_mutation_allowed": False,
            "disease_branch_must_be_separate": True,
            "required_parent_lock": "HEALTHY_NEURAL_CORE_LOCKED",
            "neural_perturbation_must_have_provenance": True,
        },
        "scientific_scope": (
            "Healthy neural source reference only; no biological Parkinson validation "
            "and no disease simulation."
        ),
        "data_fabricated": False,
    }


def run(*, brain_root: Path, output: Path) -> int:
    inspection = inspect_brain_root(brain_root.resolve())
    manifest = build_lock_manifest(
        brain_root=brain_root,
        inspection=inspection,
        project_commit=_git_commit(ROOT),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Status: {manifest['status']}")
    print(f"Manifest: {output.resolve()}")
    print("Simulation: NOT_RUN")
    return 0 if manifest["status"] == "HEALTHY_NEURAL_CORE_LOCKED" else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lock healthy neural source provenance without running simulation."
    )
    parser.add_argument("--brain-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(brain_root=args.brain_root, output=args.output)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Healthy core lock stopped: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
