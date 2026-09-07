"""Validate the reviewed scope and hypothesis before a dopamine disease run."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.riemensperger2011.protocol import (
    build_manifest,
    read_csv_rows,
    read_yaml,
    project_path,
    require_status,
    sha256_file,
    write_json,
)


DEFAULT_EVIDENCE = ROOT / "experiments/gate_21a_riemensperger_evidence_lock/results/evidence_lock_summary.json"
DEFAULT_SPEC = ROOT / "research/replications/riemensperger_2011/mapping/dopamine_mapping_spec.yaml"
DEFAULT_HYPOTHESIS = ROOT / "research/replications/riemensperger_2011/mapping/dopamine_transform_hypothesis.yaml"
DEFAULT_AUDIT = ROOT / "datasets/literature_phenotypes/root_id_mapping_audit.csv"
DEFAULT_OUTPUT = ROOT / "experiments/gate_21d_riemensperger_dopamine_mapping"
APPROVAL = "APPROVED_FOR_DOPAMINE_CLASS_LEVEL_EXPLORATORY"


def _root_ids(spec: dict[str, Any]) -> tuple[Path, list[str], int]:
    target = spec.get("target_neurons")
    if not isinstance(target, dict):
        raise ValueError("mapping spec target_neurons must reference an approved source config.")
    source_value = str(target.get("source_config", "")).strip()
    if not source_value:
        raise ValueError("mapping spec target_neurons.source_config is missing.")
    source = (ROOT / source_value).resolve()
    document = read_yaml(source)
    ids = [str(value) for value in document.get("target_neurons", [])]
    expected = int(target.get("expected_count", -1))
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("referenced target set is missing or contains duplicated root IDs.")
    if len(ids) != expected:
        raise ValueError(f"target count mismatch: expected {expected}, received {len(ids)}.")
    if str(target.get("source_sha256", "")).lower() != sha256_file(source):
        raise ValueError("referenced target source checksum does not match the mapping spec.")
    return source, ids, expected


def validate_mapping(*, evidence_path: Path, spec_path: Path, hypothesis_path: Path, audit_path: Path, output: Path) -> str:
    output.mkdir(parents=True, exist_ok=True)
    blockers: list[str] = []
    try:
        require_status(evidence_path, "RIEMENSPERGER_2011_EVIDENCE_LOCKED")
    except (OSError, RuntimeError, ValueError) as exc:
        blockers.append(f"evidence_lock:{exc}")
    try:
        spec = read_yaml(spec_path)
        hypothesis = read_yaml(hypothesis_path)
        source_config, root_ids, expected_count = _root_ids(spec)
    except (OSError, RuntimeError, ValueError) as exc:
        spec, hypothesis, source_config, root_ids, expected_count = {}, {}, ROOT / "__missing__", [], 0
        blockers.append(f"mapping_spec:{exc}")

    if spec:
        if spec.get("mapping_level") != "DOPAMINE_CLASS_LEVEL_EXPLORATORY":
            blockers.append("mapping_level_not_class_level_exploratory")
        if spec.get("gene_specific_mapping") is not False:
            blockers.append("gene_specific_mapping_must_be_false")
        audit_rows = read_csv_rows(audit_path)
        audit_row = next((row for row in audit_rows if row.get("condition_id") == "dopamine_deficiency_exploratory"), None)
        if not audit_row or audit_row.get("root_id_status") != "CLASS_LEVEL_EXPLORATORY_ONLY":
            blockers.append("root_id_audit_does_not_confirm_class_level_only")
        if not str(spec.get("reviewer_1", "")).strip():
            blockers.append("reviewer_1_missing")
        reviewer_2 = str(spec.get("reviewer_2", "")).strip()
        if not reviewer_2 or reviewer_2.startswith("NOT_"):
            blockers.append("reviewer_2_human_signoff_missing")
        if str(spec.get("decision", "")).strip() != APPROVAL:
            blockers.append("class_level_mapping_decision_not_approved")
        if not str(spec.get("review_date", "")).strip():
            blockers.append("review_date_missing")
        if hypothesis.get("transform_type") != "presynaptic_connectome_weight_gain":
            blockers.append("transform_type_invalid")
        if hypothesis.get("identity_condition") != "burden=0.0 returns an exact copy of every input weight":
            blockers.append("identity_condition_not_locked")
        if hypothesis.get("parameter_range") != [0.0, 0.25, 0.5, 0.75, 1.0]:
            blockers.append("preregistered_parameter_range_invalid")

    status = "READY_FOR_RIEMENSPERGER_DISEASE_REPLICATION" if not blockers else "WAITING_DOPAMINE_MAPPING_REVIEW"
    payload = {
        "schema_version": "riemensperger-2011-dopamine-mapping-review-v1",
        "status": status,
        "mapping_level": spec.get("mapping_level", "NOT_AVAILABLE"),
        "gene_specific_mapping": spec.get("gene_specific_mapping", False),
        "target_count": expected_count,
        "target_source": project_path(source_config),
        "target_source_sha256": sha256_file(source_config) if source_config.is_file() else "NOT_AVAILABLE",
        "target_ids_loaded": len(root_ids),
        "blockers": blockers,
        "data_fabricated": False,
        "simulation_run": False,
        "scientific_scope": "Dopamine-class-level computational mapping only; never a gene-specific or biological validation claim.",
    }
    write_json(output / "results/dopamine_mapping_summary.json", payload)
    write_json(output / "manifests/dopamine_mapping_manifest.json", build_manifest(status=status, input_paths=[evidence_path, spec_path, hypothesis_path, audit_path, source_config], extra={"simulation_run": False, "mapping_sha256": sha256_file(spec_path) if spec_path.is_file() else "NOT_AVAILABLE", "target_count": expected_count, "blockers": blockers}))
    _write_report(status=status, payload=payload)
    return status


def _write_report(*, status: str, payload: dict[str, Any]) -> None:
    lines = [
        "# Gate 21D - Dopamine biology-to-model mapping",
        "",
        f"**Trạng thái:** `{status}`",
        "",
        f"- Mapping level: `{payload['mapping_level']}`.",
        f"- Gene-specific mapping: `{payload['gene_specific_mapping']}`.",
        f"- Target IDs loaded from checked source: `{payload['target_ids_loaded']}`.",
        "- Transform: presynaptic connectome-weight gain before public brain-to-body action generation.",
        "- `burden=0` là identity; burden không phải phần trăm dopamine mất.",
        "",
    ]
    if payload["blockers"]:
        lines.extend(["## Blocker", "", *[f"- `{value}`" for value in payload["blockers"]], ""])
    lines.extend([
        "Không có root ID hay edge ID nào được suy từ tên gene. Gate này chỉ có thể mở disease rollout sau signoff con người cho đúng phạm vi dopamine class-level exploratory.",
        "",
    ])
    report_path = ROOT / "docs/replications/riemensperger_2011/gate_21d_dopamine_mapping.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--mapping-spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--hypothesis", type=Path, default=DEFAULT_HYPOTHESIS)
    parser.add_argument("--root-id-audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    status = validate_mapping(evidence_path=args.evidence.resolve(), spec_path=args.mapping_spec.resolve(), hypothesis_path=args.hypothesis.resolve(), audit_path=args.root_id_audit.resolve(), output=args.output.resolve())
    print(f"Status: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
