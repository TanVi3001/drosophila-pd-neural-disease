"""Create an auditable disease neural branch without changing the healthy core."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.annotations import load_neuron_annotations
from drosophila_pd_neural.models import profile_from_mapping
from drosophila_pd_neural.provenance import sha256_file


READY_MAPPING_STATUSES = {"MAPPED_EXPLORATORY", "CLASS_LEVEL_EXPLORATORY_ONLY", "APPROVED"}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _read_mapping_row(path: Path, condition_id: str) -> dict[str, str] | None:
    aliases = {condition_id}
    if condition_id.endswith("_template"):
        aliases.add(condition_id.removesuffix("_template"))
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        for row in rows:
            if (row.get("condition_id") or "").strip() in aliases:
                return {str(key): str(value or "").strip() for key, value in row.items()}
    return None


def _file_ref(path: Path) -> dict[str, Any]:
    return {"path": str(path.resolve()), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}


def _write_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(manifest), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _base_manifest(
    *,
    core_lock_path: Path,
    core_lock: Mapping[str, Any],
    config_path: Path,
    config: Mapping[str, Any],
    annotations_path: Path,
    mapping_audit_path: Path,
    mapping_row: Mapping[str, str] | None,
) -> dict[str, Any]:
    condition_id = str(config.get("condition_id", ""))
    healthy = core_lock.get("healthy_core") or {}
    parent_files = healthy.get("files") or {}
    parent_checkpoint = parent_files.get("data/plastic_weights.pt") or {}
    return {
        "schema_version": "disease-neural-branch-v1",
        "created_at_utc": _utc_now(),
        "status": "WAITING_DISEASE_MAPPING",
        "simulation_run": False,
        "calibration_run": False,
        "holdout_validation_run": False,
        "condition": {
            "condition_id": condition_id,
            "gene_model": str(config.get("gene_model", "")),
            "status_from_config": str(config.get("status", "")),
        },
        "parent_healthy_core": {
            "lock_manifest": _file_ref(core_lock_path),
            "lock_status": core_lock.get("status"),
            "root": healthy.get("root"),
            "source_commit": healthy.get("source_commit"),
            "immutable_reference": bool(healthy.get("immutable_reference")),
            "source_bytes_copied": bool(healthy.get("source_bytes_copied")),
            "checkpoint": parent_checkpoint,
        },
        "inputs": {
            "condition_config": _file_ref(config_path),
            "annotations": _file_ref(annotations_path) if annotations_path.is_file() else {"path": str(annotations_path.resolve()), "status": "MISSING"},
            "mapping_audit": _file_ref(mapping_audit_path),
        },
        "mapping": {
            "audit_row": dict(mapping_row or {}),
            "mapping_status": (mapping_row or {}).get("mapping_status", "MISSING"),
            "root_id_source": (mapping_row or {}).get("root_id_source")
            or (mapping_row or {}).get("neuron_provenance", ""),
            "gene_specific_mapping": False,
            "scope": "UNRESOLVED",
        },
        "branch": {
            "healthy_core_mutation_allowed": False,
            "separate_checkpoint_required": True,
            "target_neuron_count": len(config.get("target_neurons") or []),
            "target_edge_count": len(config.get("target_edges") or []),
            "target_neurons_are_root_ids": True,
            "target_edges_are_root_id_pairs": True,
        },
        "perturbation_rule": {
            "source_module": "src/drosophila_pd_neural/perturbations.py",
            "checkpoint_materializer": "scripts/prepare_neural_checkpoint.py",
            "transform_order": ["healthy_neural_state", "disease_neural_transform", "perturbed_neural_activity", "motor_output"],
            "parameters": dict(config.get("full_burden") or {}),
            "burden_curve": list(config.get("burden_curve") or []),
            "direct_action_mutation": False,
        },
        "checkpoint_manifest": {
            "parent_checkpoint": parent_checkpoint,
            "child_checkpoint": {"status": "NOT_CREATED"},
            "healthy_checkpoint_overwrite_allowed": False,
        },
        "provenance": list(config.get("provenance") or []),
        "blockers": [],
        "scientific_scope": (
            "Computational neural perturbation branch. A class-level mapping is exploratory and "
            "is not gene-specific mapping or biological Parkinson validation."
        ),
        "data_fabricated": False,
    }


def build_branch_manifest(
    *,
    core_lock_path: Path,
    config_path: Path,
    annotations_path: Path,
    mapping_audit_path: Path,
) -> dict[str, Any]:
    core_lock = json.loads(core_lock_path.read_text(encoding="utf-8"))
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(config, dict):
        raise ValueError("Disease config phai la YAML mapping.")
    condition_id = str(config.get("condition_id", "")).strip()
    manifest = _base_manifest(
        core_lock_path=core_lock_path,
        core_lock=core_lock,
        config_path=config_path,
        config=config,
        annotations_path=annotations_path,
        mapping_audit_path=mapping_audit_path,
        mapping_row=_read_mapping_row(mapping_audit_path, condition_id),
    )
    blockers: list[str] = []

    if core_lock.get("status") != "HEALTHY_NEURAL_CORE_LOCKED":
        blockers.append("parent healthy core lock is not HEALTHY_NEURAL_CORE_LOCKED")
        manifest["status"] = "WAITING_HEALTHY_CORE_LOCK"

    if not condition_id or not str(config.get("gene_model", "")).strip():
        blockers.append("condition_id and gene_model are required")
    if not (config.get("target_neurons") or config.get("target_edges")):
        blockers.append("target_neurons or target_edges is required")
    if not isinstance(config.get("full_burden"), dict) or not config.get("full_burden"):
        blockers.append("full_burden is required")
    if not isinstance(config.get("burden_curve"), list) or not config.get("burden_curve"):
        blockers.append("burden_curve is required")
    if not isinstance(config.get("provenance"), list) or not config.get("provenance"):
        blockers.append("condition provenance is required")

    try:
        profile_from_mapping(config)
    except (KeyError, TypeError, ValueError) as exc:
        blockers.append(f"invalid disease profile: {exc}")

    if config.get("target_neurons"):
        if not annotations_path.is_file():
            blockers.append("neuron annotation file is missing")
        else:
            annotations = load_neuron_annotations(annotations_path)
            missing = sorted(set(str(value) for value in config["target_neurons"]) - set(annotations))
            if missing:
                blockers.append(f"target neurons missing from annotation: {missing[:5]}")

    row = manifest["mapping"]["audit_row"]
    if not row:
        blockers.append("condition is missing from mapping audit")
    elif row.get("mapping_status") not in READY_MAPPING_STATUSES:
        blockers.append(f"mapping status is not ready: {row.get('mapping_status', 'MISSING')}")
        manifest["status"] = "WAITING_REVIEWED_MAPPING"
    elif not (row.get("root_id_source") or row.get("neuron_provenance")):
        blockers.append("mapping provenance is missing")
    else:
        mapping_status = row.get("mapping_status", "")
        manifest["mapping"]["scope"] = (
            "reviewed_mapping" if mapping_status == "APPROVED" else "class_level_exploratory"
        )
        manifest["mapping"]["gene_specific_mapping"] = mapping_status == "APPROVED"

    if not blockers and manifest["status"] == "WAITING_DISEASE_MAPPING":
        manifest["status"] = "DISEASE_NEURAL_BRANCH_READY"
    manifest["blockers"] = blockers
    return manifest


def run(*, core_lock_path: Path, config_path: Path, annotations_path: Path, mapping_audit_path: Path, output: Path) -> int:
    try:
        manifest = build_branch_manifest(
            core_lock_path=core_lock_path.resolve(),
            config_path=config_path.resolve(),
            annotations_path=annotations_path.resolve(),
            mapping_audit_path=mapping_audit_path.resolve(),
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError, csv.Error) as exc:
        manifest = {
            "schema_version": "disease-neural-branch-v1",
            "created_at_utc": _utc_now(),
            "status": "FAILED_BRANCH_AUDIT",
            "simulation_run": False,
            "calibration_run": False,
            "holdout_validation_run": False,
            "blockers": [str(exc)],
            "data_fabricated": False,
        }
    _write_manifest(output.resolve(), manifest)
    print(f"Status: {manifest['status']}")
    print(f"Manifest: {output.resolve()}")
    print(f"Blockers: {len(manifest.get('blockers', []))}")
    print("Simulation: NOT_RUN")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-lock", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--mapping-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(
        core_lock_path=args.core_lock,
        config_path=args.config,
        annotations_path=args.annotations,
        mapping_audit_path=args.mapping_audit,
        output=args.output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
