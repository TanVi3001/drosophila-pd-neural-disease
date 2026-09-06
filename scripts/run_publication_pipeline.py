"""Run the gated Steps 5-12 publication workflow without unsafe promotion."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "publication_pipeline.yaml"
DEFAULT_OUTPUT = ROOT / "results" / "publication_pipeline"
BRANCH_SCRIPT = ROOT / "scripts" / "prepare_disease_neural_branch.py"
PERTURBATION_SCRIPT = ROOT / "scripts" / "prepare_disease_neural_perturbation.py"
INTEGRATION_SCRIPT = ROOT / "scripts" / "run_brain_body_neural_first.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prepare_disease_neural_branch import build_branch_manifest


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Config phai la mapping: {path}")
    return value


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else None


def assess_healthy_baseline(path: Path, *, expected_seeds: Sequence[int], expected_steps: int, expected_timestep_s: float) -> dict[str, Any]:
    """Require an existing complete baseline; do not rerun it implicitly."""
    summary = _read_json(path)
    if summary is None:
        return {
            "status": "WAITING_HEALTHY_BASELINE",
            "path": str(path.resolve()),
            "blockers": ["healthy baseline summary is missing"],
            "simulation_run": False,
        }
    blockers: list[str] = []
    if summary.get("status") != "HEALTHY_BASELINE_PASS":
        blockers.append(f"summary status={summary.get('status', 'MISSING')}")
    if summary.get("simulation_run") is not True:
        blockers.append("simulation_run is not true")
    if summary.get("disease_layer_enabled") is not False:
        blockers.append("disease layer was not explicitly disabled")
    if list(summary.get("seeds", [])) != list(expected_seeds):
        blockers.append(f"seed protocol mismatch: expected {list(expected_seeds)}")
    if int(summary.get("steps", 0)) != int(expected_steps):
        blockers.append(f"steps mismatch: expected {expected_steps}")
    if float(summary.get("timestep_s", 0.0)) != float(expected_timestep_s):
        blockers.append(f"timestep mismatch: expected {expected_timestep_s}")
    rows = summary.get("rows", [])
    if isinstance(rows, list) and rows:
        for row in rows:
            if row.get("status") != "PASS":
                blockers.append(f"seed {row.get('seed', 'MISSING')} status is not PASS")
            if row.get("required_metric_status") not in ("PASS", None):
                blockers.append(f"seed {row.get('seed', 'MISSING')} required metrics incomplete")
            if row.get("quality_status") not in ("PASS", None):
                blockers.append(f"seed {row.get('seed', 'MISSING')} physical QC failed")
    else:
        blockers.append("per-seed rows are missing")
    return {
        "status": "HEALTHY_BASELINE_QC_PASS" if not blockers else "HEALTHY_BASELINE_QC_BLOCKED",
        "path": str(path.resolve()),
        "blockers": blockers,
        "simulation_run": True,
        "summary_status": summary.get("status"),
        "seed_count": len(summary.get("seeds", [])),
        "postprocess_status": summary.get("postprocess_status"),
    }


def _condition_config(condition_id: str) -> Path | None:
    candidates = sorted((ROOT / "configs" / "conditions").glob("*.yaml"))
    for path in candidates:
        try:
            document = _load_yaml(path)
        except (OSError, ValueError, yaml.YAMLError):
            continue
        declared = str(document.get("condition_id", ""))
        if declared in {condition_id, f"{condition_id}_template"}:
            return path
    return None


def _branch_output(root: Path, condition_id: str) -> Path:
    return root / condition_id / "branch_manifest.json"


def _prepare_branches(*, output_root: Path, core_lock: Path, annotations: Path, mapping_audit: Path, conditions: Sequence[str]) -> list[dict[str, Any]]:
    branch_root = output_root / "step_06_disease" / "branches"
    rows: list[dict[str, Any]] = []
    for condition_id in conditions:
        config = _condition_config(condition_id)
        target = _branch_output(branch_root, condition_id)
        if config is None:
            document = {"status": "WAITING_CONDITION_CONFIG", "condition_id": condition_id, "blockers": ["condition config is missing"], "simulation_run": False, "data_fabricated": False}
        else:
            document = build_branch_manifest(
                core_lock_path=core_lock,
                config_path=config,
                annotations_path=annotations,
                mapping_audit_path=mapping_audit,
            )
        _write_json(target, document)
        rows.append({
            "condition_id": condition_id,
            "config": str(config) if config else None,
            "branch_manifest": str(target),
            "status": document.get("status", "UNKNOWN"),
            "blockers": document.get("blockers", []),
            "scope": (document.get("mapping") or {}).get("scope"),
            "gene_specific_mapping": (document.get("mapping") or {}).get("gene_specific_mapping", False),
        })
    return rows


def _find_existing(path_candidates: Sequence[Path]) -> Path | None:
    return next((path for path in path_candidates if path.is_file()), None)


def _existing_perturbation(condition_id: str, search_root: Path | None = None) -> Path | None:
    candidates = [
        ROOT / "results" / "neural_perturbations" / condition_id / "day_005" / "neural_perturbation_manifest.json",
        ROOT / "results" / "neural_perturbations" / "dopamine_deficiency_exploratory" / "day_005" / "neural_perturbation_manifest.json" if condition_id == "dopamine_deficiency" else ROOT / "__missing__",
    ]
    if search_root is not None:
        candidates.insert(0, search_root / "step_06_disease" / "perturbations" / condition_id / "day_005" / "neural_perturbation_manifest.json")
    return _find_existing(candidates)


def _existing_integration(condition_id: str, seed: int, search_root: Path | None = None) -> Path | None:
    candidates = [
        ROOT / "results" / "neural_first_integration" / f"{condition_id}_seed_{seed:03d}" / "brain_body_integration_manifest.json",
        ROOT / "results" / "neural_first_integration" / "dopamine_deficiency_exploratory_seed_000" / "brain_body_integration_manifest.json" if condition_id == "dopamine_deficiency_exploratory" and seed == 0 else ROOT / "__missing__",
    ]
    if search_root is not None:
        candidates.insert(0, search_root / "step_06_disease" / "rollouts" / condition_id / f"seed_{seed:03d}" / "brain_body_integration_manifest.json")
    return _find_existing(candidates)


def _integration_passed(condition_id: str, seed: int, search_root: Path | None = None) -> bool:
    path = _existing_integration(condition_id, seed, search_root)
    if path is None:
        return False
    document = _read_json(path)
    return bool(document and document.get("status") == "BRAIN_TO_BODY_INTEGRATION_PASS")


def _disease_readiness(branches: Sequence[Mapping[str, Any]], *, seeds: Sequence[int], search_root: Path | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for branch in branches:
        condition_id = str(branch["condition_id"])
        branch_status = str(branch["status"])
        perturbation = _existing_perturbation(condition_id, search_root)
        perturbation_status = "MISSING"
        if perturbation:
            loaded = _read_json(perturbation)
            perturbation_status = str((loaded or {}).get("status", "UNKNOWN"))
        if branch_status != "DISEASE_NEURAL_BRANCH_READY":
            status = "WAITING_REVIEWED_MAPPING"
        elif perturbation_status != "DISEASE_NEURAL_PERTURBATION_READY":
            status = "WAITING_NEURAL_PERTURBATION"
        else:
            completed = sum(1 for seed in seeds if _integration_passed(condition_id, int(seed), search_root))
            status = "DISEASE_MULTI_SEED_PASS" if completed == len(seeds) else "DISEASE_MULTI_SEED_PENDING"
        completed = sum(1 for seed in seeds if _integration_passed(condition_id, int(seed), search_root))
        rows.append({
            "condition_id": condition_id,
            "branch_status": branch_status,
            "perturbation_status": perturbation_status,
            "completed_seeds": completed,
            "planned_seeds": list(seeds),
            "status": status,
            "gene_specific_mapping": bool(branch.get("gene_specific_mapping", False)),
            "blockers": branch.get("blockers", []),
        })
    return rows


def _runtime_executable(configured: Path | None) -> Path:
    if configured is not None:
        return configured.resolve()
    candidates = (
        ROOT.parent / "drosophila-pd-flygym" / ".venv" / "Scripts" / "python.exe",
        ROOT.parent / "drosophila-pd-flygym" / ".venv" / "bin" / "python",
        Path(sys.executable),
    )
    return next((path for path in candidates if path.is_file()), Path(sys.executable))


def _run_neural_prep_for_branch(
    *,
    branch: Mapping[str, Any],
    output_root: Path,
    brain_root: Path,
    annotations: Path,
    runtime: Path,
) -> dict[str, Any]:
    condition_id = str(branch["condition_id"])
    branch_manifest = Path(str(branch["branch_manifest"])).resolve()
    config = Path(str(branch.get("config") or "")).resolve()
    perturbation_output = output_root / "step_06_disease" / "perturbations" / condition_id / "day_005"
    perturbation_manifest = perturbation_output / "neural_perturbation_manifest.json"
    if branch.get("status") != "DISEASE_NEURAL_BRANCH_READY":
        return {"condition_id": condition_id, "status": "SKIPPED", "reason": "branch_not_ready"}
    command = [
        str(runtime), str(PERTURBATION_SCRIPT),
        "--branch-manifest", str(branch_manifest),
        "--brain-root", str(brain_root),
        "--config", str(config),
        "--annotations", str(annotations),
        "--age-days", "5",
        "--output", str(perturbation_output),
        "--brain-python", str(runtime),
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    status = "FAILED" if result.returncode else "UNKNOWN"
    document = _read_json(perturbation_manifest)
    if document:
        status = str(document.get("status", status))
    return {
        "condition_id": condition_id,
        "status": status,
        "manifest": str(perturbation_manifest),
        "return_code": result.returncode,
        "stdout_tail": (result.stdout + "\n" + result.stderr)[-2000:],
        "command": command,
    }


def _execute_neural_disease_rollouts(
    *,
    branches: Sequence[Mapping[str, Any]],
    output_root: Path,
    brain_root: Path,
    platform_root: Path,
    annotations: Path,
    runtime: Path,
    seeds: Sequence[int],
    steps: int,
    device: str,
    prepare_first: bool,
) -> list[dict[str, Any]]:
    executions: list[dict[str, Any]] = []
    for branch in branches:
        condition_id = str(branch["condition_id"])
        if branch.get("status") != "DISEASE_NEURAL_BRANCH_READY":
            executions.append({"condition_id": condition_id, "status": "WAITING_REVIEWED_MAPPING", "executed_seeds": []})
            continue
        prep = _run_neural_prep_for_branch(
            branch=branch,
            output_root=output_root,
            brain_root=brain_root,
            annotations=annotations,
            runtime=runtime,
        ) if prepare_first else None
        perturbation_manifest = output_root / "step_06_disease" / "perturbations" / condition_id / "day_005" / "neural_perturbation_manifest.json"
        perturbation = _read_json(perturbation_manifest)
        if not perturbation or perturbation.get("status") != "DISEASE_NEURAL_PERTURBATION_READY":
            executions.append({"condition_id": condition_id, "status": "WAITING_NEURAL_PERTURBATION", "preparation": prep, "executed_seeds": []})
            continue
        executed: list[dict[str, Any]] = []
        for seed in seeds:
            output = output_root / "step_06_disease" / "rollouts" / condition_id / f"seed_{int(seed):03d}"
            existing = _read_json(output / "brain_body_integration_manifest.json")
            if existing and existing.get("status") == "BRAIN_TO_BODY_INTEGRATION_PASS":
                executed.append({"seed": int(seed), "status": "SKIPPED_EXISTING_PASS", "output": str(output)})
                continue
            command = [
                str(runtime), str(INTEGRATION_SCRIPT),
                "--branch-manifest", str(Path(str(branch["branch_manifest"])).resolve()),
                "--perturbation-manifest", str(perturbation_manifest.resolve()),
                "--brain-root", str(brain_root),
                "--platform-root", str(platform_root),
                "--brain-python", str(runtime),
                "--output", str(output),
                "--seed", str(int(seed)),
                "--steps", str(int(steps)),
                "--device", device,
            ]
            output.mkdir(parents=True, exist_ok=True)
            with (output / "orchestrator.log").open("w", encoding="utf-8") as log:
                result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
            integration = _read_json(output / "brain_body_integration_manifest.json")
            executed.append({
                "seed": int(seed),
                "status": (integration or {}).get("status", "FAILED" if result.returncode else "UNKNOWN"),
                "return_code": result.returncode,
                "output": str(output),
            })
        executions.append({"condition_id": condition_id, "status": "EXECUTED", "preparation": prep, "executed_seeds": executed})
    return executions


def _calibration_holdout_status(*, healthy_status: str, disease_rows: Sequence[Mapping[str, Any]], audit_path: Path) -> dict[str, Any]:
    audit = _read_json(audit_path) or {}
    blockers: list[str] = []
    if healthy_status != "HEALTHY_BASELINE_QC_PASS":
        blockers.append("healthy baseline QC is not PASS")
    if audit.get("status") != "READY_FOR_CALIBRATION":
        blockers.append(f"target audit status={audit.get('status', 'MISSING')}")
    neural_ready = any(row.get("status") == "DISEASE_MULTI_SEED_PASS" for row in disease_rows)
    if not neural_ready:
        blockers.append("neural-first disease multi-seed evidence is not complete")
    old_calibration = _read_json(ROOT / "experiments/gate_13b_chen_ratio_calibration/results/chen_ratio_calibration_summary.json")
    old_holdout = _read_json(ROOT / "experiments/gate_14b_pozo_holdout_validation/results/pozo_holdout_result_summary.json")
    return {
        "step_07_calibration": "READY_TO_RUN_NEURAL_FIRST_CHEN_CALIBRATION" if not blockers else "NEURAL_FIRST_CALIBRATION_PENDING",
        "step_08_confirmation": "PENDING_NEURAL_FIRST_CALIBRATION",
        "step_09_holdout": "PENDING_NEURAL_FIRST_RERUN",
        "blockers": blockers,
        "chen_target_audit": audit.get("status", "MISSING"),
        "historical_calibration_reference": old_calibration.get("status") if old_calibration else "MISSING",
        "historical_holdout_reference": old_holdout.get("execution_status") if old_holdout else "MISSING",
        "historical_results_are_neural_first": False,
        "pozo_used_for_calibration": False,
        "parameter_reselection_after_holdout": False,
    }


def _artifact_inventory(output_root: Path, *, extra_paths: Sequence[Path]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    roots = [output_root]
    for path in extra_paths:
        if path.is_file():
            records.append({"path": str(path.resolve()), "size_bytes": path.stat().st_size, "sha256": _sha256(path)})
    for root in roots:
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name not in {"checksums.sha256"}:
                records.append({"path": str(path.resolve()), "size_bytes": path.stat().st_size, "sha256": _sha256(path)})
    return {
        "schema_version": "publication-artifact-inventory-v1",
        "created_at_utc": _now(),
        "status": "ARTIFACT_PACKAGE_READY",
        "large_raw_rollouts_included": False,
        "records": records,
        "data_fabricated": False,
    }


def _write_report(path: Path, payload: Mapping[str, Any]) -> None:
    baseline = payload["step_05_healthy_baseline"]
    disease = payload["step_06_disease_multi_seed"]
    cal = payload["step_07_to_09_calibration_holdout"]
    lines = [
        "# Báo cáo pipeline Steps 5–12",
        "",
        f"- Thời điểm tạo: `{payload['created_at_utc']}`",
        f"- Trạng thái package: `{payload['status']}`",
        "- Phạm vi: neural-first computational locomotion pipeline; không phải biological Parkinson validation.",
        "",
        "## Step 5: Healthy baseline",
        f"- Trạng thái: `{baseline['status']}`.",
        f"- Seed: `{baseline.get('seed_count', 0)}`; QC blocker: `{len(baseline.get('blockers', []))}`.",
        "- Disease layer phải tắt hoàn toàn và không được dùng dữ liệu disease để tạo baseline.",
        "",
        "## Step 6: Disease multi-seed",
        "| Condition | Branch | Perturbation | Seed hoàn tất | Trạng thái |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in disease:
        lines.append(f"| `{row['condition_id']}` | `{row['branch_status']}` | `{row['perturbation_status']}` | {row['completed_seeds']}/{len(row['planned_seeds'])} | `{row['status']}` |")
    lines.extend([
        "",
        "Condition thiếu mapping vẫn giữ `WAITING_REVIEWED_MAPPING`; không tạo metric giả.",
        "",
        "## Steps 7–9: Calibration, confirmation, holdout",
        f"- Chen calibration neural-first: `{cal['step_07_calibration']}`.",
        f"- Confirmation: `{cal['step_08_confirmation']}`.",
        f"- Pozo holdout: `{cal['step_09_holdout']}`.",
        f"- Audit target: `{cal['chen_target_audit']}`.",
        "- Chen là calibration; Pozo chỉ là holdout và không được đổi distance thành speed.",
        "- Artifact Gate 13–14 cũ được ghi là historical action-level reference, không được tái nhãn thành neural-first result.",
        "",
        "## Steps 10–12: Robustness, artifact, public package",
        "- Robustness cần chạy nhiều seed, burden 0/dương, sensitivity, negative control và QC action/contact/joint.",
        "- Artifact package giữ manifest/checksum/config/report nhẹ; raw rollout lớn không đưa vào Git.",
        "- Public package chỉ đạt đầy đủ sau khi disease multi-seed, neural-first calibration, confirmation và holdout rerun pass.",
        "",
        "## Giới hạn claim",
        "Kết quả runtime PASS chỉ xác nhận pipeline thực thi và trajectory tính toán hợp lệ. Nó không chứng minh cơ chế bệnh Parkinson, không phải chẩn đoán, không dự đoán thuốc và không thay thế thí nghiệm ruồi thật.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pipeline(
    *,
    config_path: Path,
    output_root: Path,
    prepare_branches: bool,
    execute_neural_prep: bool = False,
    execute_disease_rollouts: bool = False,
    brain_root: Path | None = None,
    platform_root: Path | None = None,
    brain_python: Path | None = None,
    steps_override: int | None = None,
    device_override: str | None = None,
) -> dict[str, Any]:
    config = _load_yaml(config_path)
    protocol = config.get("protocol") or {}
    healthy_seeds = [int(value) for value in protocol.get("healthy_seeds", [0, 1, 2, 3, 4])]
    disease_seeds = [int(value) for value in protocol.get("disease_seeds", [0, 1, 2, 3, 4])]
    healthy_status = assess_healthy_baseline(
        ROOT / str((config.get("paths") or {}).get("healthy_summary", "results/healthy_baseline_gate19/healthy_baseline_summary.json")),
        expected_seeds=healthy_seeds,
        expected_steps=int(protocol.get("steps", 100000)),
        expected_timestep_s=float(protocol.get("timestep_s", 0.0001)),
    )
    core_lock = ROOT / "results/neural_core_lock/healthy_neural_core_lock.json"
    annotations = ROOT / "annotations/neuron_annotations.csv"
    mapping_audit = ROOT / "datasets/literature_phenotypes/root_id_mapping_audit.csv"
    conditions = [str(value) for value in config.get("conditions", [])]
    if prepare_branches or execute_neural_prep or execute_disease_rollouts:
        branch_rows = _prepare_branches(output_root=output_root, core_lock=core_lock, annotations=annotations, mapping_audit=mapping_audit, conditions=conditions)
    else:
        branch_rows = []
        for condition_id in conditions:
            path = _branch_output(output_root / "step_06_disease" / "branches", condition_id)
            document = _read_json(path) or {"status": "WAITING_BRANCH_AUDIT"}
            branch_rows.append({"condition_id": condition_id, "status": document.get("status"), "blockers": document.get("blockers", []), "gene_specific_mapping": (document.get("mapping") or {}).get("gene_specific_mapping", False)})
    execution: list[dict[str, Any]] = []
    if execute_neural_prep or execute_disease_rollouts:
        execution = _execute_neural_disease_rollouts(
            branches=branch_rows,
            output_root=output_root,
            brain_root=(brain_root or ROOT / "external" / "fly-brain").resolve(),
            platform_root=(platform_root or ROOT.parent / "drosophila-pd-flygym").resolve(),
            annotations=annotations,
            runtime=_runtime_executable(brain_python),
            seeds=disease_seeds if execute_disease_rollouts else [],
            steps=int(steps_override or protocol.get("steps", 100000)),
            device=device_override or str(protocol.get("device", "cuda")),
            prepare_first=True,
        )
    disease_rows = _disease_readiness(branch_rows, seeds=disease_seeds, search_root=output_root)
    cal_holdout = _calibration_holdout_status(
        healthy_status=healthy_status["status"],
        disease_rows=disease_rows,
        audit_path=ROOT / str((config.get("paths") or {}).get("calibration_audit", "results/calibration_readiness/target_audit.json")),
    )
    robustness = {
        "status": "ROBUSTNESS_PLAN_READY",
        "required_checks": ["multi_seed", "burden_zero_identity", "positive_burden_sensitivity", "negative_control", "contact_joint_action_qc", "checksum_reproducibility"],
        "executed": False,
    }
    payload: dict[str, Any] = {
        "schema_version": "publication-pipeline-v1",
        "created_at_utc": _now(),
        "status": "PUBLICATION_PACKAGE_PARTIAL",
        "step_05_healthy_baseline": healthy_status,
        "step_06_disease_multi_seed": disease_rows,
        "step_06_execution": execution,
        "step_07_to_09_calibration_holdout": cal_holdout,
        "step_10_robustness": robustness,
        "step_11_artifact_package": {"status": "PENDING_INVENTORY"},
        "step_12_public_package": {"status": "PUBLICATION_PACKAGE_PARTIAL", "ready_for_submission": False},
        "protocol": protocol,
        "scientific_boundary": config.get("scientific_boundary", {}),
        "data_fabricated": False,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    _write_json(output_root / "publication_pipeline_status.json", payload)
    _write_report(output_root / "publication_pipeline_report_vi.md", payload)
    inventory = _artifact_inventory(output_root, extra_paths=[config_path])
    _write_json(output_root / "artifact_package" / "artifact_manifest.json", inventory)
    checksum_lines = [f"{record['sha256']}  {record['path']}" for record in inventory["records"]]
    (output_root / "artifact_package" / "checksums.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    payload["step_11_artifact_package"] = {
        "status": "ARTIFACT_PACKAGE_READY",
        "manifest": str((output_root / "artifact_package/artifact_manifest.json").resolve()),
        "checksums": str((output_root / "artifact_package/checksums.sha256").resolve()),
        "large_raw_rollouts_included": False,
    }
    _write_json(output_root / "publication_pipeline_status.json", payload)
    _write_report(output_root / "publication_pipeline_report_vi.md", payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--prepare-branches", action="store_true", help="Audit and write Step 2 branch manifests; no simulation.")
    parser.add_argument("--execute-neural-prep", action="store_true", help="Materialize ready disease checkpoints; no simulation.")
    parser.add_argument("--execute-disease-rollouts", action="store_true", help="Run ready neural-first disease conditions for the configured seeds.")
    parser.add_argument("--brain-root", type=Path, default=None)
    parser.add_argument("--platform-root", type=Path, default=None)
    parser.add_argument("--brain-python", type=Path, default=None)
    parser.add_argument("--steps", type=int, default=None, help="Optional explicit rollout step override when executing disease.")
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = run_pipeline(
            config_path=args.config.resolve(),
            output_root=args.output_root.resolve(),
            prepare_branches=args.prepare_branches,
            execute_neural_prep=args.execute_neural_prep,
            execute_disease_rollouts=args.execute_disease_rollouts,
            brain_root=args.brain_root,
            platform_root=args.platform_root,
            brain_python=args.brain_python,
            steps_override=args.steps,
            device_override=args.device,
        )
    except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Status: {payload['status']}")
    print(f"Report: {args.output_root.resolve() / 'publication_pipeline_report_vi.md'}")
    print("Simulation: NOT_RUN_BY_ORCHESTRATOR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
