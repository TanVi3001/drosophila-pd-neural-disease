"""Materialize a separate neural disease checkpoint from a ready branch."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
PREPARE_SCRIPT = ROOT / "scripts" / "prepare_neural_checkpoint.py"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_status(output: Path, status: str, message: str, **extra: object) -> None:
    output.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "schema_version": "disease-neural-perturbation-status-v1",
        "created_at_utc": _now(),
        "status": status,
        "message": message,
        "simulation_run": False,
        "calibration_run": False,
        "holdout_validation_run": False,
        "data_fabricated": False,
        **extra,
    }
    (output / "status.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "status.md").write_text(
        f"# Neural perturbation runtime\n\n**Trang thai:** `{status}`\n\n{message}\n",
        encoding="utf-8",
    )


def _file_ref(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path.resolve()), "status": "MISSING"}
    return {"path": str(path.resolve()), "sha256": _sha256(path), "size_bytes": path.stat().st_size}


def _manifest(
    *,
    branch_manifest_path: Path,
    branch: Mapping[str, Any],
    brain_root: Path,
    child_checkpoint: Path,
    age_days: float,
    status: str,
    message: str,
    preparation_stdout: str = "",
) -> dict[str, Any]:
    parent = branch.get("parent_healthy_core") or {}
    parent_checkpoint = parent.get("checkpoint") or {}
    child_ref: dict[str, Any] = {"path": str(child_checkpoint.resolve()), "status": "NOT_CREATED"}
    if child_checkpoint.is_file():
        child_ref = _file_ref(child_checkpoint)
    return {
        "schema_version": "disease-neural-perturbation-v1",
        "created_at_utc": _now(),
        "status": status,
        "message": message,
        "simulation_run": False,
        "calibration_run": False,
        "holdout_validation_run": False,
        "data_fabricated": False,
        "condition": branch.get("condition", {}),
        "age_days": float(age_days),
        "branch_manifest": _file_ref(branch_manifest_path),
        "brain_root": str(brain_root.resolve()),
        "parent_healthy_checkpoint": parent_checkpoint,
        "child_disease_checkpoint": child_ref,
        "healthy_checkpoint_unchanged": False,
        "transform": {
            "stage": "healthy neural state -> disease neural transform -> perturbed neural activity",
            "materializer": "scripts/prepare_neural_checkpoint.py",
            "operator": "drosophila_pd_neural.perturbations.perturb_edges",
            "direct_action_mutation": False,
            "parameters": (branch.get("perturbation_rule") or {}).get("parameters", {}),
        },
        "preparation": {
            "stdout": preparation_stdout[-4000:],
            "checkpoint_manifest": (
                str((child_checkpoint.parent / "manifest.json").resolve())
                if (child_checkpoint.parent / "manifest.json").is_file()
                else None
            ),
        },
        "scientific_scope": (
            "Neural checkpoint perturbation for a computational class-level exploratory condition. "
            "This is not gene-specific mapping or biological Parkinson validation."
        ),
    }


def build_blocked_manifest(*, branch_manifest_path: Path, branch: Mapping[str, Any], brain_root: Path, age_days: float, status: str, message: str) -> dict[str, Any]:
    return _manifest(
        branch_manifest_path=branch_manifest_path,
        branch=branch,
        brain_root=brain_root,
        child_checkpoint=Path("disease_checkpoint_not_created.pt"),
        age_days=age_days,
        status=status,
        message=message,
    )


def _write_manifest(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(document), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(
    *,
    branch_manifest_path: Path,
    brain_root: Path,
    config_path: Path,
    annotations_path: Path,
    age_days: float,
    output: Path,
    brain_python: Path | None,
) -> int:
    output = output.resolve()
    branch_manifest_path = branch_manifest_path.resolve()
    brain_root = brain_root.resolve()
    config_path = config_path.resolve()
    annotations_path = annotations_path.resolve()
    branch = json.loads(branch_manifest_path.read_text(encoding="utf-8"))
    if branch.get("status") != "DISEASE_NEURAL_BRANCH_READY":
        document = build_blocked_manifest(
            branch_manifest_path=branch_manifest_path,
            branch=branch,
            brain_root=brain_root,
            age_days=age_days,
            status="WAITING_DISEASE_NEURAL_BRANCH",
            message="Step 2 chua READY; khong tao checkpoint va khong chay simulation.",
        )
        _write_manifest(output / "neural_perturbation_manifest.json", document)
        _write_status(output, document["status"], document["message"], blockers=branch.get("blockers", []))
        print(f"Status: {document['status']}")
        return 0

    parent_checkpoint = brain_root / "data" / "plastic_weights.pt"
    expected_parent = (
        (branch.get("parent_healthy_core") or {}).get("checkpoint") or {}
    ).get("sha256")
    if not parent_checkpoint.is_file():
        status = "WAITING_BRAIN_DATA"
        message = f"Khong tim thay healthy checkpoint: {parent_checkpoint}"
        document = build_blocked_manifest(branch_manifest_path=branch_manifest_path, branch=branch, brain_root=brain_root, age_days=age_days, status=status, message=message)
        _write_manifest(output / "neural_perturbation_manifest.json", document)
        _write_status(output, status, message)
        print(f"Status: {status}")
        return 0
    actual_parent = _sha256(parent_checkpoint)
    if expected_parent and actual_parent != expected_parent:
        status = "WAITING_HEALTHY_CORE_INTEGRITY"
        message = "Healthy checkpoint hash khong khop parent lock; dung truoc khi perturb."
        document = build_blocked_manifest(branch_manifest_path=branch_manifest_path, branch=branch, brain_root=brain_root, age_days=age_days, status=status, message=message)
        document["actual_parent_checkpoint_sha256"] = actual_parent
        document["expected_parent_checkpoint_sha256"] = expected_parent
        _write_manifest(output / "neural_perturbation_manifest.json", document)
        _write_status(output, status, message, expected=expected_parent, actual=actual_parent)
        print(f"Status: {status}")
        return 0
    if not config_path.is_file() or not annotations_path.is_file():
        status = "WAITING_INPUT_DATA"
        message = "Config hoac annotation cho neural transform bi thieu."
        document = build_blocked_manifest(branch_manifest_path=branch_manifest_path, branch=branch, brain_root=brain_root, age_days=age_days, status=status, message=message)
        _write_manifest(output / "neural_perturbation_manifest.json", document)
        _write_status(output, status, message)
        print(f"Status: {status}")
        return 0

    executable = brain_python.resolve() if brain_python else Path(sys.executable)
    if not executable.is_file():
        status = "WAITING_BRAIN_RUNTIME"
        message = f"Khong tim thay Python runtime: {executable}"
        document = build_blocked_manifest(branch_manifest_path=branch_manifest_path, branch=branch, brain_root=brain_root, age_days=age_days, status=status, message=message)
        _write_manifest(output / "neural_perturbation_manifest.json", document)
        _write_status(output, status, message)
        print(f"Status: {status}")
        return 0

    command = [
        str(executable), str(PREPARE_SCRIPT),
        "--brain-root", str(brain_root),
        "--config", str(config_path),
        "--age-days", str(age_days),
        "--annotations", str(annotations_path),
        "--output", str(output),
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    preparation_output = (result.stdout + "\n" + result.stderr).strip()
    status_path = output / "status.json"
    child_checkpoint = output / "plastic_weights.pt"
    prep_status = "UNKNOWN"
    if status_path.is_file():
        prep_status = json.loads(status_path.read_text(encoding="utf-8")).get("status", "UNKNOWN")
    if result.returncode != 0 or prep_status != "CHECKPOINT_READY" or not child_checkpoint.is_file():
        status = "WAITING_NEURAL_CHECKPOINT" if prep_status.startswith("WAITING") else "FAILED_NEURAL_PERTURBATION"
        message = f"Neural checkpoint preparation status: {prep_status}."
        document = _manifest(
            branch_manifest_path=branch_manifest_path,
            branch=branch,
            brain_root=brain_root,
            child_checkpoint=child_checkpoint,
            age_days=age_days,
            status=status,
            message=message,
            preparation_stdout=preparation_output,
        )
        document["parent_checkpoint_sha256_actual"] = actual_parent
        document["preparation_command"] = command
        _write_manifest(output / "neural_perturbation_manifest.json", document)
        _write_status(output, status, message, preparation_status=prep_status, command=command)
        print(f"Status: {status}")
        return 0

    child_hash = _sha256(child_checkpoint)
    if child_hash == actual_parent:
        status = "FAILED_NEURAL_PERTURBATION"
        message = "Checkpoint con trung hash voi healthy; khong chap nhan transform rong."
        document = _manifest(branch_manifest_path=branch_manifest_path, branch=branch, brain_root=brain_root, child_checkpoint=child_checkpoint, age_days=age_days, status=status, message=message, preparation_stdout=preparation_output)
        document["parent_checkpoint_sha256_actual"] = actual_parent
        document["healthy_checkpoint_unchanged"] = True
        _write_manifest(output / "neural_perturbation_manifest.json", document)
        _write_status(output, status, message)
        print(f"Status: {status}")
        return 0

    document = _manifest(
        branch_manifest_path=branch_manifest_path,
        branch=branch,
        brain_root=brain_root,
        child_checkpoint=child_checkpoint,
        age_days=age_days,
        status="DISEASE_NEURAL_PERTURBATION_READY",
        message="Da tao checkpoint disease rieng tu healthy checkpoint; chua chay simulation.",
        preparation_stdout=preparation_output,
    )
    document["parent_checkpoint_sha256_actual"] = actual_parent
    document["healthy_checkpoint_unchanged"] = _sha256(parent_checkpoint) == actual_parent
    document["preparation_command"] = command
    _write_manifest(output / "neural_perturbation_manifest.json", document)
    _write_status(output, document["status"], document["message"], child_checkpoint_sha256=child_hash, parent_checkpoint_sha256=actual_parent)
    print(f"Status: {document['status']}")
    print(f"Child checkpoint: {child_checkpoint}")
    print("Simulation: NOT_RUN")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch-manifest", type=Path, required=True)
    parser.add_argument("--brain-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--age-days", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--brain-python", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(
        branch_manifest_path=args.branch_manifest,
        brain_root=args.brain_root,
        config_path=args.config,
        annotations_path=args.annotations,
        age_days=args.age_days,
        output=args.output,
        brain_python=args.brain_python,
    )


if __name__ == "__main__":
    raise SystemExit(main())
