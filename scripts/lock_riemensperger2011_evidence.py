"""Lock directly reported Riemensperger 2011 evidence before any simulation."""

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
    read_yaml,
    sha256_file,
    write_json,
)


LOCK = ROOT / "research/replications/riemensperger_2011/evidence/paper_evidence_lock.csv"
CONTRACT = ROOT / "research/replications/riemensperger_2011/evidence/endpoint_contract.yaml"
POLICY = ROOT / "research/replications/riemensperger_2011/protocols/control_policy.md"
OUTPUT = ROOT / "experiments/gate_21a_riemensperger_evidence_lock"
REQUIRED = {
    ("REAL_PRIMARY_CONTROL", "median_planar_speed_mm_s"): 10.8,
    ("REAL_DISEASE", "median_planar_speed_mm_s"): 7.8,
    ("REAL_SECONDARY_REFERENCE", "median_planar_speed_mm_s"): 15.0,
    ("REAL_PRIMARY_CONTROL", "median_distance_covered_cm_15min"): 425.0,
    ("REAL_DISEASE", "median_distance_covered_cm_15min"): 193.0,
}


def lock_evidence(*, lock_path: Path, contract_path: Path, policy_path: Path, output: Path) -> str:
    output.mkdir(parents=True, exist_ok=True)
    blockers: list[str] = []
    rows: list[dict[str, str]] = []
    try:
        rows = read_csv_rows(lock_path)
        for (role, endpoint), expected in REQUIRED.items():
            selected = [row for row in rows if row.get("condition_role") == role and row.get("endpoint") == endpoint]
            if len(selected) != 1:
                blockers.append(f"evidence_row_count:{role}:{endpoint}={len(selected)}")
                continue
            row = selected[0]
            if row.get("statistic") != "median":
                blockers.append(f"statistic_not_median:{role}:{endpoint}")
            if numeric(row.get("value"), field=f"{role}:{endpoint}") != expected:
                blockers.append(f"unexpected_value:{role}:{endpoint}")
            if row.get("evidence_status") != "VERIFIED_PRIMARY_SOURCE_TEXT":
                blockers.append(f"unverified_source:{role}:{endpoint}")
            if not row.get("source_url", "").startswith("https://pmc.ncbi.nlm.nih.gov/articles/PMC3021077/"):
                blockers.append(f"unexpected_source_url:{role}:{endpoint}")
        primary = next(row for row in rows if row.get("condition_role") == "REAL_PRIMARY_CONTROL" and row.get("endpoint") == "median_planar_speed_mm_s")
        disease = next(row for row in rows if row.get("condition_role") == "REAL_DISEASE" and row.get("endpoint") == "median_planar_speed_mm_s")
        if primary.get("genotype") != "DTHg; ple":
            blockers.append("primary_control_not_DTHg_ple")
        if disease.get("genotype") != "DTHgFS±; ple":
            blockers.append("disease_not_DTHgFS_ple")
        if not any(row.get("condition_role") == "REAL_SECONDARY_REFERENCE" and row.get("genotype") == "WT" for row in rows):
            blockers.append("secondary_WT_reference_missing")
        contract = read_yaml(contract_path)
        if contract.get("primary_endpoint", {}).get("statistic") != "median":
            blockers.append("endpoint_contract_does_not_preserve_median")
        if not policy_path.is_file():
            blockers.append("control_policy_missing")
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        blockers.append(f"evidence_io_or_schema:{exc}")

    status = "RIEMENSPERGER_2011_EVIDENCE_LOCKED" if not blockers else "WAITING_RIEMENSPERGER_2011_PAPER_EVIDENCE"
    speed_ratio = None
    distance_ratio = None
    if not blockers:
        speed_ratio = 7.8 / 10.8
        distance_ratio = 193.0 / 425.0
    summary: dict[str, Any] = {
        "schema_version": "riemensperger-2011-evidence-lock-v1",
        "status": status,
        "paper_id": "riemensperger_2011_dopamine_deficiency",
        "paper_doi": "10.1073/pnas.1010930108",
        "pmid": "21187381",
        "primary_real_control": "DTHg; ple",
        "real_disease": "DTHgFS±; ple",
        "secondary_real_reference": "WT",
        "primary_endpoint": "median_planar_speed_mm_s",
        "real_speed_ratio": speed_ratio,
        "real_distance_ratio": distance_ratio,
        "uncertainty_policy": "NOT_REPORTED is retained; no SE, SD, IQR, range, or CI is fabricated.",
        "review_status": "PRIMARY_TEXT_LOCKED_HUMAN_SIGNOFF_NOT_SUBSTITUTED",
        "blockers": blockers,
        "simulation_run": False,
        "data_fabricated": False,
    }
    write_json(output / "results/evidence_lock_summary.json", summary)
    write_json(output / "manifests/evidence_lock_manifest.json", build_manifest(status=status, input_paths=[lock_path, contract_path, policy_path], extra={"simulation_run": False, "paper_evidence_sha256": sha256_file(lock_path) if lock_path.is_file() else "NOT_AVAILABLE", "real_speed_ratio": speed_ratio, "real_distance_ratio": distance_ratio, "blockers": blockers}))
    _write_report(summary)
    return status


def _write_report(summary: dict[str, Any]) -> None:
    lines = [
        "# Gate 21A - Paper evidence lock",
        "",
        f"**Trạng thái:** `{summary['status']}`",
        "",
        "| Nhóm thật | Genotype | Endpoint chính | Giá trị |",
        "| --- | --- | --- | ---: |",
        "| Primary control | DTHg; ple | Median speed | 10.8 mm/s |",
        "| Disease | DTHgFS±; ple | Median speed | 7.8 mm/s |",
        "| Secondary reference | WT | Median speed | 15 mm/s |",
        "",
        "- Figure 2A cũng báo median distance 425 cm (control) và 193 cm (disease) trong 15 phút.",
        "- Statistic được khóa là `median`; variance không báo cáo được giữ là `NOT_REPORTED`.",
        "- Bản PDF không được commit. Provenance chính là DOI/PMID và URL PMC công khai trong CSV evidence lock.",
        "",
        f"- Real matched speed ratio: `{summary['real_speed_ratio']}`.",
        f"- Real matched distance ratio: `{summary['real_distance_ratio']}`.",
        "",
    ]
    if summary["blockers"]:
        lines.extend(["## Blocker", "", *[f"- `{value}`" for value in summary["blockers"]], ""])
    report_path = ROOT / "docs/replications/riemensperger_2011/gate_21a_paper_evidence_lock.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-lock", type=Path, default=LOCK)
    parser.add_argument("--endpoint-contract", type=Path, default=CONTRACT)
    parser.add_argument("--control-policy", type=Path, default=POLICY)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    status = lock_evidence(lock_path=args.evidence_lock.resolve(), contract_path=args.endpoint_contract.resolve(), policy_path=args.control_policy.resolve(), output=args.output.resolve())
    print(f"Status: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
