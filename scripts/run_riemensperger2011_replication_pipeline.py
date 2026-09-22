"""Gate-aware orchestrator for the Riemensperger 2011 virtual replication."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.riemensperger2011.protocol import read_json, write_json
from scripts.analyze_riemensperger2011_four_group import run as run_four_group
from scripts.analyze_riemensperger2011_healthy_comparability import run as run_comparability
from scripts.assess_riemensperger2011_robustness import run as run_robustness
from scripts.lock_riemensperger2011_evidence import lock_evidence
from scripts.prepare_riemensperger2011_dopamine_mapping import validate_mapping
from scripts.run_riemensperger2011_dopamine_replication import run as run_disease
from scripts.run_riemensperger2011_healthy_replication import run as run_healthy


EVIDENCE_LOCK = ROOT / "research/replications/riemensperger_2011/evidence/paper_evidence_lock.csv"
ENDPOINT_CONTRACT = ROOT / "research/replications/riemensperger_2011/evidence/endpoint_contract.yaml"
CONTROL_POLICY = ROOT / "research/replications/riemensperger_2011/protocols/control_policy.md"
HEALTHY_CONFIG = ROOT / "configs/replications/riemensperger_2011_healthy.yaml"
DISEASE_CONFIG = ROOT / "configs/replications/riemensperger_2011_dopamine_deficiency.yaml"
ANALYSIS_CONFIG = ROOT / "configs/replications/riemensperger_2011_analysis.yaml"
MAPPING_SPEC = ROOT / "research/replications/riemensperger_2011/mapping/dopamine_mapping_spec.yaml"
TRANSFORM_HYPOTHESIS = ROOT / "research/replications/riemensperger_2011/mapping/dopamine_transform_hypothesis.yaml"
ROOT_AUDIT = ROOT / "datasets/literature_phenotypes/root_id_mapping_audit.csv"
EVIDENCE_OUTPUT = ROOT / "experiments/gate_21a_riemensperger_evidence_lock"
HEALTHY_OUTPUT = ROOT / "experiments/gate_21b_riemensperger_healthy"
COMPARABILITY_OUTPUT = ROOT / "experiments/gate_21c_riemensperger_healthy_comparability"
MAPPING_OUTPUT = ROOT / "experiments/gate_21d_riemensperger_dopamine_mapping"
DISEASE_OUTPUT = ROOT / "experiments/gate_21e_riemensperger_disease"
FOUR_GROUP_OUTPUT = ROOT / "experiments/gate_21f_four_group_analysis"
ROBUSTNESS_OUTPUT = ROOT / "experiments/gate_21g_riemensperger_robustness"


def _status(path: Path) -> str:
    if not path.is_file():
        return "NOT_RUN"
    try:
        return str(read_json(path).get("status", "UNKNOWN"))
    except (OSError, ValueError):
        return "INVALID_ARTIFACT"


def _write_final_report(
    statuses: dict[str, str],
    *,
    report_path: Path | None = None,
    status_path: Path | None = None,
) -> None:
    """Write the summary to explicit targets so tests can remain hermetic."""
    final_status = statuses.get("21F", "NOT_RUN")
    if final_status == "FOUR_GROUP_ANALYSIS_COMPLETE":
        summary_path = FOUR_GROUP_OUTPUT / "results/four_group_summary.json"
        summary = read_json(summary_path) if summary_path.is_file() else {}
        interpretation = summary.get("interpretation", "WAITING_EVIDENCE")
    else:
        interpretation = "WAITING_EVIDENCE"
    claim = (
        "Riemensperger 2011-guided dopamine-class computational perturbation reproduced the direction of locomotor impairment in the virtual fly, while substantial quantitative mismatch remained."
        if interpretation == "DIRECTIONALLY_CONCORDANT_QUANTITATIVE_MISMATCH"
        else "The Riemensperger 2011-guided computational replication remains a gated study; no biological validation claim is made."
    )
    lines = [
        "# Tái lập computational Riemensperger 2011",
        "",
        "## 1. Câu hỏi nghiên cứu",
        "",
        "Liệu một perturbation ở mức lớp neuron dopamine, được xây dựng từ evidence của Riemensperger 2011 và chạy qua neural core/FlyGym công khai, có tái hiện hướng thay đổi locomotion của ruồi thật hay không?",
        "",
        "## 2. Thiết kế bốn nhóm",
        "",
        "A. Real DTHg; ple control; B. virtual healthy; C. real DTHgFS±; ple; D. virtual dopamine-class perturbation.",
        "",
        "## 3. Trạng thái gate",
        "",
        *[f"- {gate}: `{value}`" for gate, value in statuses.items()],
        "",
        "## 4. Claim lock",
        "",
        f"> {claim}",
        "",
        "Không được gọi kết quả này là biological Parkinson validation, gene-specific validation, clinical validation, drug validation hoặc therapeutic validation.",
        "",
        "## 5. Evidence và giới hạn",
        "",
        "Paper báo median speed 10.8 mm/s cho DTHg; ple, 7.8 mm/s cho DTHgFS±; ple và 15 mm/s cho WT; median distance là endpoint riêng. Variance không báo cáo được giữ là NOT_REPORTED. Virtual duration khác 15 phút của assay thật nên raw-scale agreement không được khẳng định; ratio chỉ là endpoint exploratory có giới hạn.",
        "",
        "## 6. Tái lập",
        "",
        "Mọi gate phải lưu config, input/output SHA256, commit, Python/runtime, seed list, QC và trạng thái simulation. GPU chỉ được chạy sau khi evidence lock và mapping class-level có human signoff.",
        "",
    ]
    report = report_path or ROOT / "docs/replications/riemensperger_2011/final_replication_report.md"
    pipeline_status = status_path or ROOT / "experiments/riemensperger_2011_pipeline_status.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")
    write_json(pipeline_status, {"statuses": statuses, "interpretation": interpretation, "claim": claim, "simulation_executed": any("PASS" in value for value in statuses.values()), "data_fabricated": False})


def run_pipeline(*, stage: str, dry_run: bool, brain_root: Path, platform_root: Path, brain_python: Path, runner_python: Path) -> dict[str, str]:
    statuses: dict[str, str] = {}
    statuses["21A"] = lock_evidence(lock_path=EVIDENCE_LOCK, contract_path=ENDPOINT_CONTRACT, policy_path=CONTROL_POLICY, output=EVIDENCE_OUTPUT)
    if stage == "evidence":
        _write_final_report(statuses)
        return statuses
    if statuses["21A"] != "RIEMENSPERGER_2011_EVIDENCE_LOCKED":
        _write_final_report(statuses)
        return statuses

    if stage in {"healthy", "all"}:
        statuses["21B"], _ = run_healthy(config_path=HEALTHY_CONFIG, evidence_path=EVIDENCE_OUTPUT / "results/evidence_lock_summary.json", mapping_path=MAPPING_OUTPUT / "results/dopamine_mapping_summary.json", output=HEALTHY_OUTPUT, brain_root=brain_root, platform_root=platform_root, brain_python=brain_python, runner_python=runner_python, dry_run=dry_run)
    else:
        statuses["21B"] = _status(HEALTHY_OUTPUT / "manifests/healthy_manifest.json")
    if stage == "healthy":
        _write_final_report(statuses)
        return statuses

    if stage in {"comparability", "all"}:
        statuses["21C"] = run_comparability(evidence_path=EVIDENCE_OUTPUT / "results/evidence_lock_summary.json", healthy_path=HEALTHY_OUTPUT / "results/healthy_summary.json", lock_path=EVIDENCE_LOCK, contract_path=ENDPOINT_CONTRACT, output=COMPARABILITY_OUTPUT)
    else:
        statuses["21C"] = _status(COMPARABILITY_OUTPUT / "results/healthy_comparability_summary.json")
    if stage == "comparability":
        _write_final_report(statuses)
        return statuses

    if stage in {"mapping", "disease", "analysis", "robustness", "all"}:
        statuses["21D"] = validate_mapping(evidence_path=EVIDENCE_OUTPUT / "results/evidence_lock_summary.json", spec_path=MAPPING_SPEC, hypothesis_path=TRANSFORM_HYPOTHESIS, audit_path=ROOT_AUDIT, output=MAPPING_OUTPUT)
    else:
        statuses["21D"] = _status(MAPPING_OUTPUT / "results/dopamine_mapping_summary.json")
    if stage == "mapping":
        # Materialize downstream blocker artifacts without entering any runtime.
        # This keeps the gate chain auditable while the human mapping decision is pending.
        statuses["21E"] = run_disease(
            config_path=DISEASE_CONFIG,
            mapping_path=MAPPING_OUTPUT / "results/dopamine_mapping_summary.json",
            evidence_path=EVIDENCE_OUTPUT / "results/evidence_lock_summary.json",
            output=DISEASE_OUTPUT,
            brain_root=brain_root,
            platform_root=platform_root,
            brain_python=brain_python,
            runner_python=runner_python,
            dry_run=dry_run,
        )
        statuses["21F"] = run_four_group(
            evidence_lock=EVIDENCE_LOCK,
            contract_path=ENDPOINT_CONTRACT,
            analysis_config=ANALYSIS_CONFIG,
            healthy_path=HEALTHY_OUTPUT / "results/healthy_summary.json",
            disease_path=DISEASE_OUTPUT / "results/disease_summary.json",
            output=FOUR_GROUP_OUTPUT,
        )
        statuses["21G"] = run_robustness(
            mapping_path=MAPPING_OUTPUT / "results/dopamine_mapping_summary.json",
            disease_path=DISEASE_OUTPUT / "results/disease_summary.json",
            hypothesis_path=TRANSFORM_HYPOTHESIS,
            output=ROBUSTNESS_OUTPUT,
            dry_run=dry_run,
        )
        _write_final_report(statuses)
        return statuses
    if statuses["21D"] != "READY_FOR_RIEMENSPERGER_DISEASE_REPLICATION":
        statuses["21E"] = run_disease(
            config_path=DISEASE_CONFIG,
            mapping_path=MAPPING_OUTPUT / "results/dopamine_mapping_summary.json",
            evidence_path=EVIDENCE_OUTPUT / "results/evidence_lock_summary.json",
            output=DISEASE_OUTPUT,
            brain_root=brain_root,
            platform_root=platform_root,
            brain_python=brain_python,
            runner_python=runner_python,
            dry_run=dry_run,
        )
        statuses["21F"] = run_four_group(
            evidence_lock=EVIDENCE_LOCK,
            contract_path=ENDPOINT_CONTRACT,
            analysis_config=ANALYSIS_CONFIG,
            healthy_path=HEALTHY_OUTPUT / "results/healthy_summary.json",
            disease_path=DISEASE_OUTPUT / "results/disease_summary.json",
            output=FOUR_GROUP_OUTPUT,
        )
        statuses["21G"] = run_robustness(
            mapping_path=MAPPING_OUTPUT / "results/dopamine_mapping_summary.json",
            disease_path=DISEASE_OUTPUT / "results/disease_summary.json",
            hypothesis_path=TRANSFORM_HYPOTHESIS,
            output=ROBUSTNESS_OUTPUT,
            dry_run=dry_run,
        )
        _write_final_report(statuses)
        return statuses

    if stage in {"disease", "analysis", "robustness", "all"}:
        statuses["21E"] = run_disease(config_path=DISEASE_CONFIG, mapping_path=MAPPING_OUTPUT / "results/dopamine_mapping_summary.json", evidence_path=EVIDENCE_OUTPUT / "results/evidence_lock_summary.json", output=DISEASE_OUTPUT, brain_root=brain_root, platform_root=platform_root, brain_python=brain_python, runner_python=runner_python, dry_run=dry_run)
    else:
        statuses["21E"] = _status(DISEASE_OUTPUT / "results/disease_summary.json")
    if stage == "disease" or statuses["21E"] != "DOPAMINE_DEFICIENCY_VIRTUAL_REPLICATION_PASS":
        _write_final_report(statuses)
        return statuses

    if stage in {"analysis", "all"}:
        statuses["21F"] = run_four_group(evidence_lock=EVIDENCE_LOCK, contract_path=ENDPOINT_CONTRACT, analysis_config=ANALYSIS_CONFIG, healthy_path=HEALTHY_OUTPUT / "results/healthy_summary.json", disease_path=DISEASE_OUTPUT / "results/disease_summary.json", output=FOUR_GROUP_OUTPUT)
    else:
        statuses["21F"] = _status(FOUR_GROUP_OUTPUT / "results/four_group_summary.json")
    if stage == "analysis":
        _write_final_report(statuses)
        return statuses

    if stage in {"robustness", "all"}:
        statuses["21G"] = run_robustness(mapping_path=MAPPING_OUTPUT / "results/dopamine_mapping_summary.json", disease_path=DISEASE_OUTPUT / "results/disease_summary.json", hypothesis_path=TRANSFORM_HYPOTHESIS, output=ROBUSTNESS_OUTPUT, dry_run=dry_run)
    else:
        statuses["21G"] = _status(ROBUSTNESS_OUTPUT / "results/robustness_summary.json")
    _write_final_report(statuses)
    return statuses


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("evidence", "healthy", "comparability", "mapping", "disease", "analysis", "robustness", "all"), required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--brain-root", type=Path, default=ROOT / "external/fly-brain")
    parser.add_argument("--platform-root", type=Path, default=ROOT.parent / "drosophila-pd-flygym")
    parser.add_argument("--brain-python", type=Path, default=ROOT.parent / "drosophila-pd-flygym/.venv/Scripts/python.exe")
    parser.add_argument("--runner-python", type=Path, default=Path(sys.executable))
    args = parser.parse_args(argv)
    statuses = run_pipeline(stage=args.stage, dry_run=args.dry_run, brain_root=args.brain_root.resolve(), platform_root=args.platform_root.resolve(), brain_python=args.brain_python.resolve(), runner_python=args.runner_python.resolve())
    for gate, status in statuses.items():
        print(f"{gate}: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
