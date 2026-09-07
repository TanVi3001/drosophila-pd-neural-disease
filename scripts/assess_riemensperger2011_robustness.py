"""Gate 21G readiness and claim lock for preregistered robustness checks."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.riemensperger2011.dopamine_transform import apply_dopamine_class_presynaptic_transform
from drosophila_pd_neural.riemensperger2011.protocol import build_manifest, read_json, read_yaml, require_status, write_json


DEFAULT_MAPPING = ROOT / "experiments/gate_21d_riemensperger_dopamine_mapping/results/dopamine_mapping_summary.json"
DEFAULT_DISEASE = ROOT / "experiments/gate_21e_riemensperger_disease/results/disease_summary.json"
DEFAULT_HYPOTHESIS = ROOT / "research/replications/riemensperger_2011/mapping/dopamine_transform_hypothesis.yaml"
DEFAULT_OUTPUT = ROOT / "experiments/gate_21g_riemensperger_robustness"


def run(*, mapping_path: Path, disease_path: Path, hypothesis_path: Path, output: Path, dry_run: bool) -> str:
    output.mkdir(parents=True, exist_ok=True)
    hypothesis = read_yaml(hypothesis_path)
    burdens = hypothesis.get("parameter_range", [])
    no_op = apply_dopamine_class_presynaptic_transform([1.0, -2.0, 3.0], ["target", "other", "target"], ["target"], burden=0.0)
    no_op_pass = no_op.tolist() == [1.0, -2.0, 3.0]
    blockers: list[str] = []
    try:
        require_status(mapping_path, "READY_FOR_RIEMENSPERGER_DISEASE_REPLICATION")
        require_status(disease_path, "DOPAMINE_DEFICIENCY_VIRTUAL_REPLICATION_PASS")
    except (OSError, RuntimeError, ValueError) as exc:
        blockers.append(str(exc))
    status = "NOT_EXECUTED_DRY_RUN" if dry_run and not blockers else "WAITING_VIRTUAL_GROUP_RESULTS" if blockers else "ROBUSTNESS_EXECUTION_REQUIRED"
    result = {
        "status": status,
        "no_op_operator_test": "PASS" if no_op_pass else "FAIL",
        "burden_sensitivity_plan": burdens,
        "mapping_sensitivity": "NOT_AVAILABLE_WITH_CURRENT_CLASS_LEVEL_EVIDENCE",
        "seed_policy": "same independent seeds as healthy and disease; frames are not replicates",
        "blockers": blockers,
        "simulation_run": False,
        "data_fabricated": False,
    }
    write_json(output / "results/robustness_summary.json", result)
    write_json(output / "manifests/robustness_manifest.json", build_manifest(status=status, input_paths=[mapping_path, disease_path, hypothesis_path], extra={"simulation_run": False, "no_op_operator_test": result["no_op_operator_test"], "burden_sensitivity_plan": burdens, "blockers": blockers}))
    lines = [
        "# Gate 21G - Robustness and claim lock",
        "",
        f"**Trạng thái:** `{status}`",
        "",
        f"- No-op operator test: `{result['no_op_operator_test']}`.",
        f"- Burden sensitivity preregistered: `{burdens}`.",
        "- Mapping sensitivity: `NOT_AVAILABLE_WITH_CURRENT_CLASS_LEVEL_EVIDENCE`.",
        "- Không diễn giải burden như mức độ bệnh sinh học.",
        "",
    ]
    if blockers:
        lines.extend(["## Blocker", "", *[f"- `{blocker}`" for blocker in blockers], ""])
    report_path = ROOT / "docs/replications/riemensperger_2011/gate_21g_robustness_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return status


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--disease-summary", type=Path, default=DEFAULT_DISEASE)
    parser.add_argument("--hypothesis", type=Path, default=DEFAULT_HYPOTHESIS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    status = run(mapping_path=args.mapping.resolve(), disease_path=args.disease_summary.resolve(), hypothesis_path=args.hypothesis.resolve(), output=args.output.resolve(), dry_run=args.dry_run)
    print(f"Status: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
