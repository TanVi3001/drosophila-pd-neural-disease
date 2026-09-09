"""Compute the matched four-group result without fitting to paper targets."""

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


DEFAULT_EVIDENCE_LOCK = ROOT / "research/replications/riemensperger_2011/evidence/paper_evidence_lock.csv"
DEFAULT_CONTRACT = ROOT / "research/replications/riemensperger_2011/evidence/endpoint_contract.yaml"
DEFAULT_ANALYSIS_CONFIG = ROOT / "configs/replications/riemensperger_2011_analysis.yaml"
DEFAULT_HEALTHY = ROOT / "experiments/gate_21b_riemensperger_healthy/results/healthy_summary.json"
DEFAULT_DISEASE = ROOT / "experiments/gate_21e_riemensperger_disease/results/disease_summary.json"
DEFAULT_OUTPUT = ROOT / "experiments/gate_21f_four_group_analysis"


def _evidence_value(rows: list[dict[str, str]], role: str, endpoint: str) -> dict[str, str]:
    found = [row for row in rows if row.get("condition_role") == role and row.get("endpoint") == endpoint]
    if len(found) != 1:
        raise RuntimeError(f"Expected exactly one evidence row for {role}/{endpoint}.")
    return found[0]


def _write_report(*, status: str, interpretation: str, message: str = "") -> None:
    lines = [
        "# Gate 21F - Matched four-group analysis",
        "",
        f"**Trạng thái:** `{status}`",
        f"**Diễn giải:** `{interpretation}`",
        "",
    ]
    if message:
        lines.extend(["## Chờ dữ liệu", "", message, ""])
    lines.extend([
        "| Nhóm | Nguồn | Vai trò |",
        "| --- | --- | --- |",
        "| A | Real | DTHg; ple primary control |",
        "| B | Virtual | healthy neural core, disease layer OFF |",
        "| C | Real | DTHgFS±; ple dopamine-deficient condition |",
        "| D | Virtual | dopamine-class-level computational transform |",
        "",
        "Không đổi median thành mean, không đổi distance thành speed, không tuning theo kết quả real disease và không xem frame là replicate.",
        "",
    ])
    report_path = ROOT / "docs/replications/riemensperger_2011/gate_21f_four_group_analysis.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def run(*, evidence_lock: Path, contract_path: Path, analysis_config: Path, healthy_path: Path, disease_path: Path, output: Path) -> str:
    output.mkdir(parents=True, exist_ok=True)
    try:
        healthy = require_status(healthy_path, "HEALTHY_VIRTUAL_REPLICATION_PASS")
        disease = require_status(disease_path, "DOPAMINE_DEFICIENCY_VIRTUAL_REPLICATION_PASS")
    except (OSError, RuntimeError, ValueError) as exc:
        status = "WAITING_VIRTUAL_GROUP_RESULTS"
        summary = {"status": status, "interpretation": "WAITING_EVIDENCE", "message": str(exc), "simulation_run": False, "data_fabricated": False}
        write_json(output / "results/four_group_summary.json", summary)
        write_json(output / "manifests/four_group_manifest.json", build_manifest(status=status, input_paths=[evidence_lock, contract_path, analysis_config, healthy_path, disease_path], extra={"simulation_run": False, "message": str(exc)}))
        _write_report(status=status, interpretation="WAITING_EVIDENCE", message=str(exc))
        return status

    contract = read_yaml(contract_path)
    policy = read_yaml(analysis_config)
    if policy.get("calibration") != "forbidden" or policy.get("holdout") != "forbidden":
        raise RuntimeError("Four-group protocol must forbid calibration and holdout fitting.")
    evidence = read_csv_rows(evidence_lock)
    real_control = _evidence_value(evidence, "REAL_PRIMARY_CONTROL", "median_planar_speed_mm_s")
    real_disease = _evidence_value(evidence, "REAL_DISEASE", "median_planar_speed_mm_s")
    real_control_value = numeric(real_control["value"], field="real control speed")
    real_disease_value = numeric(real_disease["value"], field="real disease speed")
    virtual_control_value = numeric(healthy["median_planar_speed_mm_s"]["median"], field="virtual healthy speed")
    virtual_disease_value = numeric(disease["median_planar_speed_mm_s"]["median"], field="virtual disease speed")
    real_ratio = real_disease_value / real_control_value
    virtual_ratio = virtual_disease_value / virtual_control_value
    ratio_error = abs(virtual_ratio - real_ratio)
    direction = real_disease_value < real_control_value and virtual_disease_value < virtual_control_value
    interpretation = "DIRECTIONALLY_CONCORDANT_QUANTITATIVE_MISMATCH" if direction else "NOT_REPRODUCED"
    comparison = {
        "metric": "median_planar_speed_mm_s",
        "real_control": real_control_value,
        "real_disease": real_disease_value,
        "real_effect_ratio": real_ratio,
        "virtual_control": virtual_control_value,
        "virtual_disease": virtual_disease_value,
        "virtual_effect_ratio": virtual_ratio,
        "ratio_error": ratio_error,
        "direction_concordant": direction,
        "quantitative_match": "NOT_ASSESSED_NO_PREREGISTERED_THRESHOLD",
        "assay_comparability": contract["primary_endpoint"]["comparability"],
        "notes": "No calibration or post-hoc threshold was applied. Absolute raw-scale agreement is not claimed.",
    }
    four_groups = [
        {"group": "A", "source_type": "real", "condition_role": "REAL_PRIMARY_CONTROL", "metric": "median_planar_speed_mm_s", "statistic": "median", "value": real_control_value, "unit": "mm/s", "uncertainty": "NOT_REPORTED", "n": real_control.get("sample_size"), "source": real_control["source_url"], "config": "paper_evidence_lock", "notes": "DTHg; ple"},
        {"group": "B", "source_type": "virtual", "condition_role": "VIRTUAL_HEALTHY_CONTROL", "metric": "median_planar_speed_mm_s", "statistic": "median_across_seed_medians", "value": virtual_control_value, "unit": "mm/s", "uncertainty": healthy["median_planar_speed_mm_s"].get("sample_sd"), "n": healthy["median_planar_speed_mm_s"].get("n_seeds"), "source": str(healthy_path), "config": "riemensperger_2011_healthy.yaml", "notes": "Disease layer OFF"},
        {"group": "C", "source_type": "real", "condition_role": "REAL_DISEASE", "metric": "median_planar_speed_mm_s", "statistic": "median", "value": real_disease_value, "unit": "mm/s", "uncertainty": "NOT_REPORTED", "n": real_disease.get("sample_size"), "source": real_disease["source_url"], "config": "paper_evidence_lock", "notes": "DTHgFS±; ple"},
        {"group": "D", "source_type": "virtual", "condition_role": "VIRTUAL_DOPAMINE_DEFICIENT", "metric": "median_planar_speed_mm_s", "statistic": "median_across_seed_medians", "value": virtual_disease_value, "unit": "mm/s", "uncertainty": disease["median_planar_speed_mm_s"].get("sample_sd"), "n": disease["median_planar_speed_mm_s"].get("n_seeds"), "source": str(disease_path), "config": "riemensperger_2011_dopamine_deficiency.yaml", "notes": "Class-level exploratory mapping; not gene-specific"},
    ]
    four_fields = ("group", "source_type", "condition_role", "metric", "statistic", "value", "unit", "uncertainty", "n", "source", "config", "notes")
    write_csv_rows(output / "results/four_group_metrics.csv", four_fields, four_groups)
    write_csv_rows(output / "metrics/four_group_table.csv", four_fields, four_groups)
    write_csv_rows(output / "results/four_group_effect_comparison.csv", comparison.keys(), [comparison])
    summary = {"status": "FOUR_GROUP_ANALYSIS_COMPLETE", "interpretation": interpretation, "comparison": comparison, "distance_endpoint_status": "DISTANCE_ENDPOINT_NOT_COMPARABLE", "data_fabricated": False, "calibration_run": False, "holdout_validation_run": False}
    write_json(output / "results/four_group_summary.json", summary)
    write_json(output / "manifests/four_group_manifest.json", build_manifest(status="FOUR_GROUP_ANALYSIS_COMPLETE", config_paths=[contract_path, analysis_config], input_paths=[evidence_lock, healthy_path, disease_path, output / "results/four_group_metrics.csv", output / "results/four_group_effect_comparison.csv"], extra={"simulation_run": False, "primary_endpoint": "median_planar_speed_mm_s", "real_effect_ratio": real_ratio, "virtual_effect_ratio": virtual_ratio, "ratio_error": ratio_error, "interpretation": interpretation}))
    _write_report(status="FOUR_GROUP_ANALYSIS_COMPLETE", interpretation=interpretation)
    return "FOUR_GROUP_ANALYSIS_COMPLETE"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-lock", type=Path, default=DEFAULT_EVIDENCE_LOCK)
    parser.add_argument("--endpoint-contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--analysis-config", type=Path, default=DEFAULT_ANALYSIS_CONFIG)
    parser.add_argument("--healthy-summary", type=Path, default=DEFAULT_HEALTHY)
    parser.add_argument("--disease-summary", type=Path, default=DEFAULT_DISEASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    status = run(evidence_lock=args.evidence_lock.resolve(), contract_path=args.endpoint_contract.resolve(), analysis_config=args.analysis_config.resolve(), healthy_path=args.healthy_summary.resolve(), disease_path=args.disease_summary.resolve(), output=args.output.resolve())
    print(f"Status: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
