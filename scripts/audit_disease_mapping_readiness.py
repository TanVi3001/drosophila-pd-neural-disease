"""Audit disease mapping before opening the neural multi-seed gate."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "experiments/gate_20a_disease_mapping/configs/disease_mapping_review_plan.yaml"
DEFAULT_ROOT_AUDIT = ROOT / "datasets/literature_phenotypes/root_id_mapping_audit.csv"
DEFAULT_MAPPING_STATUS = ROOT / "research/disease_mapping/mapping_status.csv"
DEFAULT_MAPPING_REVIEW = ROOT / "research/disease_mapping/gene_specific_mapping_review.csv"
DEFAULT_OUTPUT = ROOT / "experiments/gate_20a_disease_mapping"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{str(key): str(value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _mapping_for(rows: Sequence[Mapping[str, str]], condition_id: str) -> dict[str, str] | None:
    aliases = {condition_id, f"{condition_id}_template"}
    return next((dict(row) for row in rows if row.get("condition_id") in aliases), None)


def _config_path(condition_id: str) -> Path:
    if condition_id == "dopamine_deficiency_exploratory":
        return ROOT / "configs" / "conditions" / "dopamine_deficiency.exploratory.yaml"
    return ROOT / "configs" / "conditions" / f"{condition_id}.template.yaml"


def _config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def _has_mapping_identifier(mapping: Mapping[str, str]) -> bool:
    """Accept an explicit root-ID mapping or an explicit edge-ID mapping."""
    for key in ("root_id", "edge_id", "edge_ids", "target_edges"):
        value = str(mapping.get(key, "")).strip()
        if value and value not in {"[]", "{}", "None"}:
            return True
    return False


def _valid_review_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _audit_condition(
    *,
    condition_id: str,
    mapping: Mapping[str, str] | None,
    mapping_review: Mapping[str, str] | None,
    config: Mapping[str, Any],
    requested: bool,
) -> dict[str, Any]:
    blockers: list[str] = []
    mapping_status = str((mapping or {}).get("mapping_status", "MISSING"))
    mapping_source = str(
        (mapping or {}).get("root_id_source")
        or (mapping or {}).get("neuron_provenance")
        or ""
    ).strip()
    has_mapping_identifier = _has_mapping_identifier(mapping or {})
    reviewer = str((mapping or {}).get("reviewer_2", ""))
    review_date = str((mapping or {}).get("review_date", ""))
    cell_type_or_scope = str(
        (mapping or {}).get("cell_type")
        or (mapping or {}).get("cell_type_or_scope")
        or ""
    ).strip()
    driver_scope = str((mapping or {}).get("driver_scope", "")).strip()
    connectome_version = str((mapping or {}).get("connectome_version", "")).strip()
    mapping_review_status = str((mapping_review or {}).get("mapping_status", "MISSING")).strip()
    mapping_review_decision = str((mapping_review or {}).get("decision", "MISSING")).strip()
    class_level = mapping_status in {"MAPPED_EXPLORATORY", "CLASS_LEVEL_EXPLORATORY_ONLY"}
    approved = mapping_status == "APPROVED"

    if mapping is None:
        blockers.append("mapping audit row is missing")
    if not has_mapping_identifier and not class_level:
        blockers.append("reviewed root-ID or edge-ID mapping is missing")
    if not mapping_source:
        blockers.append("root_id_source/neuron provenance is missing")
    if not cell_type_or_scope:
        blockers.append("cell_type or scope is missing")
    if not driver_scope:
        blockers.append("driver_scope is missing")
    if not connectome_version:
        blockers.append("connectome_version is missing")
    if not reviewer:
        blockers.append("reviewer_2 is missing")
    if not _valid_review_date(review_date):
        blockers.append("review_date is missing or not YYYY-MM-DD")
    if not (config.get("target_neurons") or config.get("target_edges")):
        blockers.append("condition target_neurons/target_edges is missing")
    if not config.get("burden_curve"):
        blockers.append("condition burden_curve is missing")
    has_perturbation_rule = bool(config.get("perturbation_rule") or config.get("full_burden"))
    if not has_perturbation_rule:
        blockers.append("condition perturbation_rule/full_burden is missing")
    if not config.get("provenance"):
        blockers.append("condition provenance is missing")
    if requested and mapping_review is None:
        blockers.append("gene-specific mapping review row is missing")
    if requested and mapping_review is not None:
        if mapping_review_status != mapping_status:
            blockers.append("gene-specific mapping review status does not match root-ID audit")
        if mapping_review_status == "APPROVED" and mapping_review_decision != "APPROVED":
            blockers.append("gene-specific mapping review decision is not APPROVED")
        try:
            review_identifier_count = int(mapping_review.get("mapping_identifier_count", "0"))
        except ValueError:
            blockers.append("gene-specific mapping identifier count is not numeric")
        else:
            if mapping_review_status == "APPROVED" and review_identifier_count <= 0:
                blockers.append("approved gene-specific mapping has zero identifiers")

    if not requested:
        status = "READY_EXPLORATORY_CLASS_LEVEL" if class_level and not blockers else "REFERENCE_ONLY"
    elif mapping_status in {"NOT_MAPPABLE_FROM_PAPER", "NOT_MAPPABLE_TO_CURRENT_CONNECTOME", "MODEL_SCOPE_NOT_CELL_SPECIFIC"}:
        status = "WAITING_MODEL_SCOPE_REVIEW"
    elif blockers:
        status = "WAITING_REVIEWED_MAPPING"
    elif class_level:
        status = "READY_EXPLORATORY_CLASS_LEVEL"
    elif approved:
        status = "READY_FOR_DISEASE_BRANCH"
    else:
        status = "WAITING_REVIEWED_MAPPING"
    if class_level and requested and status.startswith("READY"):
        status = "READY_EXPLORATORY_CLASS_LEVEL"
    return {
        "condition_id": condition_id,
        "requested_for_step_06": requested,
        "mapping_status": mapping_status,
        "mapping_scope": "class_level_exploratory" if class_level else ("reviewed_mapping" if approved else "unresolved"),
        "gene_specific_mapping": approved,
        "mapping_identifier_present": has_mapping_identifier,
        "root_id_source_present": bool(mapping_source),
        "cell_type_or_scope_present": bool(cell_type_or_scope),
        "driver_scope_present": bool(driver_scope),
        "connectome_version_present": bool(connectome_version),
        "mapping_review_status": mapping_review_status,
        "mapping_review_decision": mapping_review_decision,
        "reviewer_2_present": bool(reviewer),
        "review_date_valid": _valid_review_date(review_date),
        "config_path": str(_config_path(condition_id)),
        "status": status,
        "blockers": blockers,
        "simulation_run": False,
        "data_fabricated": False,
    }


def build_audit(
    *,
    plan_path: Path,
    root_audit_path: Path,
    mapping_status_path: Path,
    mapping_review_path: Path = DEFAULT_MAPPING_REVIEW,
) -> dict[str, Any]:
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    if not isinstance(plan, dict):
        raise ValueError("Gate 20A plan phai la YAML mapping.")
    root_rows = _rows(root_audit_path)
    status_rows = _rows(mapping_status_path)
    mapping_review_rows = _rows(mapping_review_path)
    conditions = [str(value) for value in plan.get("conditions", [])]
    exploratory = [str(value) for value in plan.get("exploratory_reference", [])]
    output_rows: list[dict[str, Any]] = []
    for condition_id in conditions + exploratory:
        mapping = _mapping_for(root_rows, condition_id) or _mapping_for(status_rows, condition_id)
        mapping_review = _mapping_for(mapping_review_rows, condition_id)
        config = _config(_config_path(condition_id))
        output_rows.append(
            _audit_condition(
                condition_id=condition_id,
                mapping=mapping,
                mapping_review=mapping_review,
                config=config,
                requested=condition_id in conditions,
            )
        )
    requested_rows = [row for row in output_rows if row["requested_for_step_06"]]
    ready_requested = [
        row
        for row in requested_rows
        if row["status"] in {"READY_FOR_DISEASE_BRANCH", "READY_EXPLORATORY_CLASS_LEVEL"}
    ]
    exploratory_ready = [row for row in output_rows if row["status"] == "READY_EXPLORATORY_CLASS_LEVEL"]
    status = "READY_FOR_STEP_06" if ready_requested else "DISEASE_MAPPING_BLOCKED"
    return {
        "schema_version": "gate-20a-disease-mapping-readiness-v1",
        "created_at_utc": _now(),
        "status": status,
        "requested_condition_count": len(requested_rows),
        "requested_ready_count": len(ready_requested),
        "exploratory_reference_ready_count": len(exploratory_ready),
        "conditions": output_rows,
        "inputs": {
            "plan": {"path": str(plan_path.resolve()), "sha256": _sha256(plan_path)},
            "root_id_mapping_audit": {"path": str(root_audit_path.resolve()), "sha256": _sha256(root_audit_path)},
            "mapping_status": {"path": str(mapping_status_path.resolve()), "sha256": _sha256(mapping_status_path)},
            "gene_specific_mapping_review": {"path": str(mapping_review_path.resolve()), "sha256": _sha256(mapping_review_path)},
        },
        "no_root_id_inference": True,
        "no_simulation_run": True,
        "no_calibration_run": True,
        "no_holdout_validation_run": True,
        "data_fabricated": False,
        "scientific_scope": "Disease mapping readiness audit; no gene-specific or biological Parkinson validation.",
        "policy": plan.get("policy", {}),
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["condition_id", "requested_for_step_06", "mapping_status", "mapping_scope", "gene_specific_mapping", "mapping_identifier_present", "root_id_source_present", "cell_type_or_scope_present", "driver_scope_present", "connectome_version_present", "mapping_review_status", "mapping_review_decision", "reviewer_2_present", "review_date_valid", "status", "blockers", "simulation_run", "data_fabricated"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            value = dict(row)
            value["blockers"] = "; ".join(str(item) for item in row.get("blockers", []))
            writer.writerow({field: value.get(field, "") for field in fields})


def _write_report(path: Path, audit: Mapping[str, Any]) -> None:
    lines = [
        "# Gate 20A: Disease mapping readiness",
        "",
        f"**Trạng thái:** `{audit['status']}`",
        "",
        f"- Condition mục tiêu: `{audit['requested_condition_count']}`.",
        f"- Condition mục tiêu đủ điều kiện branch: `{audit['requested_ready_count']}`.",
        f"- Reference exploratory đủ cấu trúc: `{audit['exploratory_reference_ready_count']}`.",
        "- Không suy ra root ID từ tên gene.",
        "- Không chạy simulation, calibration hoặc holdout.",
        "",
        "| Condition | Mapping | Scope | Gene-specific | Trạng thái | Blocker |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in audit["conditions"]:
        blockers = "; ".join(row["blockers"]) or "-"
        lines.append(f"| `{row['condition_id']}` | `{row['mapping_status']}` | `{row['mapping_scope']}` | `{row['gene_specific_mapping']}` | `{row['status']}` | {blockers} |")
    lines.extend([
        "",
        "## Điều kiện mở Step 6",
        "",
        "Cần một mapping được review với root-ID/edge provenance, connectome version, driver scope, reviewer và ngày review; đồng thời condition config phải có target, perturbation rule, burden curve và provenance. Nếu chỉ có cell-class evidence thì chỉ được ghi exploratory class-level, không gọi gene-specific.",
        "",
        "## Ranh giới khoa học",
        "",
        "Gate này chỉ xác nhận độ đầy đủ của metadata mapping. Nó không xác nhận cơ chế Parkinson sinh học, không phải biological validation và không tạo metric disease.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(*, plan_path: Path, root_audit_path: Path, mapping_status_path: Path, output_root: Path) -> int:
    audit = build_audit(plan_path=plan_path.resolve(), root_audit_path=root_audit_path.resolve(), mapping_status_path=mapping_status_path.resolve())
    output_root.mkdir(parents=True, exist_ok=True)
    _write_csv(output_root / "results/disease_mapping_readiness.csv", audit["conditions"])
    _write_report(output_root / "results/disease_mapping_readiness.md", audit)
    manifest = dict(audit)
    manifest["report"] = str((output_root / "results/disease_mapping_readiness.md").resolve())
    manifest["table"] = str((output_root / "results/disease_mapping_readiness.csv").resolve())
    (output_root / "manifests").mkdir(parents=True, exist_ok=True)
    (output_root / "manifests/disease_mapping_readiness_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Status: {audit['status']}")
    print(f"Ready requested conditions: {audit['requested_ready_count']}/{audit['requested_condition_count']}")
    print(f"Report: {output_root.resolve() / 'results/disease_mapping_readiness.md'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--root-audit", type=Path, default=DEFAULT_ROOT_AUDIT)
    parser.add_argument("--mapping-status", type=Path, default=DEFAULT_MAPPING_STATUS)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(plan_path=args.plan, root_audit_path=args.root_audit, mapping_status_path=args.mapping_status, output_root=args.output_root)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError, csv.Error, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
