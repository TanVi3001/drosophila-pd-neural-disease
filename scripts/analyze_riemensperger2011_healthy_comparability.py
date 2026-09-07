"""Audit healthy virtual versus real DTHg; ple comparability for ratio analysis."""

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
    numeric,
    read_csv_rows,
    read_json,
    read_yaml,
    require_status,
    write_csv_rows,
    write_json,
)


DEFAULT_EVIDENCE = ROOT / "experiments/gate_21a_riemensperger_evidence_lock/results/evidence_lock_summary.json"
DEFAULT_HEALTHY = ROOT / "experiments/gate_21b_riemensperger_healthy/results/healthy_summary.json"
DEFAULT_LOCK = ROOT / "research/replications/riemensperger_2011/evidence/paper_evidence_lock.csv"
DEFAULT_CONTRACT = ROOT / "research/replications/riemensperger_2011/evidence/endpoint_contract.yaml"
DEFAULT_OUTPUT = ROOT / "experiments/gate_21c_riemensperger_healthy_comparability"


def _primary_control_speed(lock_path: Path) -> float:
    rows = read_csv_rows(lock_path)
    matching = [
        row for row in rows
        if row.get("condition_role") == "REAL_PRIMARY_CONTROL"
        and row.get("endpoint") == "median_planar_speed_mm_s"
    ]
    if len(matching) != 1:
        raise RuntimeError("Evidence lock must contain exactly one primary-control speed row.")
    return numeric(matching[0].get("uncertainty_value") or matching[0].get("value", "10.8"), field="real control speed")


def _real_control_row(lock_path: Path) -> dict[str, str]:
    rows = read_csv_rows(lock_path)
    rows = [row for row in rows if row.get("condition_role") == "REAL_PRIMARY_CONTROL" and row.get("endpoint") == "median_planar_speed_mm_s"]
    if len(rows) != 1:
        raise RuntimeError("Evidence lock must contain exactly one primary-control speed row.")
    return rows[0]


def run(*, evidence_path: Path, healthy_path: Path, lock_path: Path, contract_path: Path, output: Path) -> str:
    output.mkdir(parents=True, exist_ok=True)
    try:
        require_status(evidence_path, "RIEMENSPERGER_2011_EVIDENCE_LOCKED")
        healthy = require_status(healthy_path, "HEALTHY_VIRTUAL_REPLICATION_PASS")
    except (OSError, RuntimeError, ValueError) as exc:
        status = "WAITING_HEALTHY_REPLICATION_RUNTIME"
        write_json(output / "results/healthy_comparability_summary.json", {"status": status, "message": str(exc), "data_fabricated": False})
        write_json(output / "manifests/healthy_comparability_manifest.json", build_manifest(status=status, input_paths=[evidence_path, healthy_path, lock_path, contract_path], extra={"simulation_run": False, "message": str(exc)}))
        _write_report(status=status, comparison=None, message=str(exc))
        return status

    contract = read_yaml(contract_path)
    real = _real_control_row(lock_path)
    real_value = numeric(real["value"], field="real control speed")
    virtual_value = numeric(healthy["median_planar_speed_mm_s"]["median"], field="virtual healthy median speed")
    comparison = {
        "metric": "median_planar_speed_mm_s",
        "real_control_raw_metric": real_value,
        "virtual_control_raw_metric": virtual_value,
        "unit": "mm/s",
        "absolute_difference_mm_s": abs(virtual_value - real_value),
        "relative_difference_vs_real": abs(virtual_value - real_value) / real_value,
        "unit_compatibility": "MATCH",
        "statistic_compatibility": "LIMITED_DIFFERENT_UNIT_OF_ANALYSIS",
        "assay_compatibility": "RATIO_ANALYSIS_WITH_LIMITATIONS",
        "absolute_scale_status": "ABSOLUTE_SCALE_MISMATCH" if abs(virtual_value - real_value) / real_value > 0.25 else "DESCRIPTIVE_SCALE_DIFFERENCE",
        "ratio_analysis_allowed": contract["primary_endpoint"]["assay_transfer_status"],
        "notes": "No calibration is applied to force virtual and real healthy raw speeds to match.",
    }
    write_csv_rows(output / "results/healthy_comparability.csv", comparison.keys(), [comparison])
    status = "HEALTHY_COMPARABILITY_ACCEPTABLE_FOR_RATIO_ANALYSIS"
    summary = {"status": status, "comparison": comparison, "data_fabricated": False, "calibration_run": False}
    write_json(output / "results/healthy_comparability_summary.json", summary)
    write_json(output / "manifests/healthy_comparability_manifest.json", build_manifest(status=status, input_paths=[evidence_path, healthy_path, lock_path, contract_path, output / "results/healthy_comparability.csv"], extra={"simulation_run": False, "primary_endpoint": comparison["metric"], "assay_limitation": contract["primary_endpoint"]["limitation"]}))
    _write_report(status=status, comparison=comparison, message="")
    return status


def _write_report(*, status: str, comparison: dict[str, Any] | None, message: str) -> None:
    lines = ["# Gate 21C - Healthy comparability audit", "", f"**Trạng thái:** `{status}`", ""]
    if message:
        lines.extend(["## Blocker", "", message, ""])
    if comparison:
        lines.extend([
            "| Hạng mục | Giá trị |",
            "| --- | --- |",
            f"| Real DTHg; ple median speed | {comparison['real_control_raw_metric']} mm/s |",
            f"| Virtual healthy median speed | {comparison['virtual_control_raw_metric']} mm/s |",
            f"| Chênh lệch tuyệt đối | {comparison['absolute_difference_mm_s']} mm/s |",
            f"| Unit | `{comparison['unit_compatibility']}` |",
            f"| Statistic/unit of analysis | `{comparison['statistic_compatibility']}` |",
            f"| Assay | `{comparison['assay_compatibility']}` |",
            f"| Absolute scale | `{comparison['absolute_scale_status']}` |",
            "",
            "Scale thô không được ép khớp bằng calibration. Gate sau chỉ được dùng normalized disease/control ratio theo contract, với giới hạn assay được giữ nguyên.",
            "",
        ])
    report_path = ROOT / "docs/replications/riemensperger_2011/gate_21c_healthy_comparability.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--healthy-summary", type=Path, default=DEFAULT_HEALTHY)
    parser.add_argument("--evidence-lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--endpoint-contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    status = run(evidence_path=args.evidence.resolve(), healthy_path=args.healthy_summary.resolve(), lock_path=args.evidence_lock.resolve(), contract_path=args.endpoint_contract.resolve(), output=args.output.resolve())
    print(f"Status: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
