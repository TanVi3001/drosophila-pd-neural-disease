"""Execute the frozen Riemensperger 2011 computational completion track."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = Path(r"E:\Drosophila_Parkinson\drosophila-pd-flygym-gate24-memorysafe-clean")
BRAIN_ROOT = Path(r"E:\Drosophila_Parkinson\external\fly-brain-audit")
BRAIN_PYTHON = Path(r"E:\Drosophila_Parkinson\drosophila-pd-flygym\.venv\Scripts\python.exe")
SEEDS = [0, 1, 2, 3, 4]
STEPS = 5000
TIMESTEP = 0.0001
STIMULUS = "p9"
CPG_HZ = 12.0
BURDEN = 1.0
RUNTIME_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"
HEALTHY_CHECKPOINT_SHA256 = "d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691"
MAPPING_TARGET_COUNT = 342
MAPPING_READY = "READY_FOR_RIEMENSPERGER_DISEASE_REPLICATION"
GATE24E_STATUS = "GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE"
GATE24E_RESULT = "NEGATIVE_VALIDATION_RESULT"
GATE24E_CROSS_ASSAY = "DIRECTIONAL_CROSS_ASSAY_DISCORDANCE"
GATE25_STATUS = "GATE25_R2_REPRODUCIBILITY_FREEZE_COMPLETE"
ARTIFACT_PROFILE = "GATE24E_MEMORY_SAFE"

EVIDENCE = ROOT / "experiments/gate_21a_riemensperger_evidence_lock/results/evidence_lock_summary.json"
MAPPING_SUMMARY = ROOT / "experiments/gate_21d_riemensperger_dopamine_mapping/results/dopamine_mapping_summary.json"
MAPPING_SPEC = ROOT / "research/replications/riemensperger_2011/mapping/dopamine_mapping_spec.yaml"
TRANSFORM = ROOT / "research/replications/riemensperger_2011/mapping/dopamine_transform_hypothesis.yaml"
HEALTHY_CONFIG = ROOT / "configs/replications/riemensperger_2011_healthy.yaml"
DISEASE_CONFIG = ROOT / "configs/replications/riemensperger_2011_dopamine_deficiency.yaml"
ANALYSIS_CONFIG = ROOT / "configs/replications/riemensperger_2011_analysis.yaml"
CONTRACT = ROOT / "research/replications/riemensperger_2011/evidence/endpoint_contract.yaml"
MAPPING_AUDIT = ROOT / "datasets/literature_phenotypes/root_id_mapping_audit.csv"
GATE26 = ROOT / "experiments/gate_26_riemensperger_full_completion"
FREEZE = GATE26 / "manifests/gate26_execution_freeze.json"
EXECUTION_LOCK = GATE26 / "manifests/execution_lock.json"
COMPLETION = GATE26 / "manifests/gate26_completion_manifest.json"
INVENTORY = GATE26 / "manifests/reproducibility_inventory.json"
CHECKSUMS = GATE26 / "manifests/checksums.sha256"
HEALTHY_OUTPUT = ROOT / "experiments/gate_21b_riemensperger_healthy"
DISEASE_OUTPUT = ROOT / "experiments/gate_21e_riemensperger_disease"
COMPARABILITY_OUTPUT = ROOT / "experiments/gate_21c_riemensperger_healthy_comparability"
FOUR_GROUP_OUTPUT = ROOT / "experiments/gate_21f_four_group_analysis"


class Gate26Error(RuntimeError):
    """Raised when the frozen completion contract cannot proceed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha(document: dict[str, Any]) -> str:
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Gate26Error(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode:
        raise Gate26Error(result.stderr.strip() or f"git command failed: {args}")
    return result.stdout.strip()


def runtime_telemetry() -> dict[str, Any]:
    command = ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.free", "--format=csv,noheader,nounits"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return {"available": False, "note": "nvidia-smi unavailable"}
    if result.returncode or not result.stdout.strip():
        return {"available": False, "note": "nvidia-smi unavailable"}
    fields = [item.strip() for item in result.stdout.splitlines()[0].split(",")]
    if len(fields) != 4:
        return {"available": False, "note": "nvidia-smi output could not be parsed"}
    try:
        telemetry = {
            "available": True,
            "temperature_c": float(fields[0]),
            "utilization_percent": float(fields[1]),
            "memory_used_mib": float(fields[2]),
            "memory_free_mib": float(fields[3]),
        }
    except ValueError as exc:
        raise Gate26Error(f"Could not parse GPU telemetry: {exc}") from exc
    if telemetry["temperature_c"] >= 82:
        raise Gate26Error(f"GPU temperature is too high: {telemetry['temperature_c']} C")
    return telemetry


def verify_runtime_and_brain() -> dict[str, Any]:
    if not RUNTIME_ROOT.is_dir() or not BRAIN_ROOT.is_dir() or not BRAIN_PYTHON.is_file():
        raise Gate26Error("Approved runtime, brain root, or Python executable is missing")
    runtime_head = git("rev-parse", "HEAD", cwd=RUNTIME_ROOT)
    if runtime_head != RUNTIME_COMMIT:
        raise Gate26Error(f"Runtime commit mismatch: {runtime_head}")
    if git("status", "--porcelain", cwd=RUNTIME_ROOT):
        raise Gate26Error("Approved runtime worktree is dirty")
    version = subprocess.run([str(BRAIN_PYTHON), "-c", "from importlib.metadata import version; print(version('flygym'))"], capture_output=True, text=True, check=False)
    if version.returncode or version.stdout.strip() != "2.1.0":
        raise Gate26Error(f"FlyGym version mismatch: {version.stdout.strip() or version.stderr.strip()}")
    runner = RUNTIME_ROOT / "scripts/run_brain_body_rollout.py"
    help_result = subprocess.run([str(BRAIN_PYTHON), str(runner), "--help"], capture_output=True, text=True, check=False)
    if help_result.returncode or "--artifact-profile" not in help_result.stdout:
        raise Gate26Error("Frozen runtime CLI does not expose --artifact-profile")
    forbidden = [flag for flag in ("--video-output", "--video-fps", "--video-width", "--video-height", "--video-playback-speed", "--video-camera-mode") if flag in help_result.stdout]
    if forbidden:
        raise Gate26Error(f"Frozen runtime unexpectedly exposes video flags: {forbidden}")
    required = ("brain_body_bridge.py", "code/run_pytorch.py", "code/benchmark.py", "data/2025_Completeness_783.csv", "data/2025_Connectivity_783.parquet", "data/plastic_weights.pt")
    missing = [item for item in required if not (BRAIN_ROOT / item).is_file()]
    if missing:
        raise Gate26Error(f"Brain source is incomplete: {missing}")
    checkpoint_sha = sha256_file(BRAIN_ROOT / "data/plastic_weights.pt")
    if checkpoint_sha != HEALTHY_CHECKPOINT_SHA256:
        raise Gate26Error(f"Healthy checkpoint SHA mismatch: {checkpoint_sha}")
    return {"runtime_commit": runtime_head, "flygym": version.stdout.strip(), "profile": ARTIFACT_PROFILE, "brain_root": str(BRAIN_ROOT), "healthy_checkpoint_sha256": checkpoint_sha, "cli_video_supported": False}


def verify_project_locks() -> dict[str, Any]:
    gate24e = read_json(ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_final_validation_decision.json")
    gate25 = read_json(ROOT / "experiments/gate_25_r2_parkin_reproducibility/manifests/gate25_r2_reproducibility_freeze.json")
    if gate24e.get("status") != GATE24E_STATUS or gate24e.get("scientific_result") != GATE24E_RESULT or gate24e.get("cross_assay_decision") != GATE24E_CROSS_ASSAY:
        raise Gate26Error("Gate24E scientific lock changed")
    if gate25.get("status") != GATE25_STATUS:
        raise Gate26Error("Gate25-R2 freeze is not complete")
    return {"gate24e_status": gate24e["status"], "gate24e_result": gate24e["scientific_result"], "gate24e_cross_assay": gate24e["cross_assay_decision"], "gate25_status": gate25["status"], "gate25_r2_freeze_sha256": gate25.get("gate25_r2_freeze_sha256", "")}


def verify_mapping() -> dict[str, Any]:
    mapping = read_json(MAPPING_SUMMARY)
    if mapping.get("status") != MAPPING_READY or mapping.get("mapping_level") != "DOPAMINE_CLASS_LEVEL_EXPLORATORY" or mapping.get("gene_specific_mapping") is not False or mapping.get("target_count") != MAPPING_TARGET_COUNT or mapping.get("blockers") != []:
        raise Gate26Error(f"Gate21D mapping is not ready: {mapping}")
    return {"status": mapping["status"], "mapping_level": mapping["mapping_level"], "target_count": mapping["target_count"], "mapping_summary_sha256": sha256_file(MAPPING_SUMMARY), "mapping_spec_sha256": sha256_file(MAPPING_SPEC)}


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def build_freeze(runtime: dict[str, Any], locks: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    healthy = yaml.safe_load(HEALTHY_CONFIG.read_text(encoding="utf-8"))
    disease = yaml.safe_load(DISEASE_CONFIG.read_text(encoding="utf-8"))
    analysis = yaml.safe_load(ANALYSIS_CONFIG.read_text(encoding="utf-8"))
    document: dict[str, Any] = {
        "schema_version": "gate26-riemensperger-execution-freeze-v1",
        "status": "GATE26_SCIENTIFIC_EXECUTION_FROZEN",
        "source_commit": git("rev-parse", "HEAD"),
        "canonical_origin_main": git("rev-parse", "origin/main"),
        "branch": git("branch", "--show-current"),
        "paper_evidence_sha256": sha256_file(EVIDENCE),
        "gate21d_mapping_sha256": mapping["mapping_summary_sha256"],
        "gate21d_mapping_spec_sha256": mapping["mapping_spec_sha256"],
        "mapping_target_count": MAPPING_TARGET_COUNT,
        "healthy_config_sha256": sha256_file(HEALTHY_CONFIG),
        "disease_config_sha256": sha256_file(DISEASE_CONFIG),
        "analysis_config_sha256": sha256_file(ANALYSIS_CONFIG),
        "transform_hypothesis_sha256": sha256_file(TRANSFORM),
        "runtime_commit": runtime["runtime_commit"],
        "runtime_profile": ARTIFACT_PROFILE,
        "healthy_checkpoint_sha256": runtime["healthy_checkpoint_sha256"],
        "seeds": SEEDS,
        "steps": STEPS,
        "virtual_duration_s": float(healthy["duration"]["virtual_duration_s"]),
        "timestep_s": TIMESTEP,
        "stimulus": STIMULUS,
        "cpg_frequency_hz": CPG_HZ,
        "world": healthy["world"],
        "controller": "same controller; disease differs only by reviewed neural transform",
        "disease_burden": BURDEN,
        "primary_metrics": ["median_planar_speed_mm_s", "distance_traveled_mm"],
        "qc_rules": ["finite_qc", "timestamp_monotonic", "contact_detected", "joint_trajectory_changes", "action_trajectory_changes"],
        "decision_rules": ["directionality first", "magnitude descriptive", "no posthoc threshold"],
        "no_retuning": True,
        "calibration": False,
        "holdout_validation": False,
        "simulation_count_authorized": 10,
        "scientific_contract_changed": False,
        "runtime_artifact_compatibility_amendment": True,
        "data_fabricated": False,
        "gate25_r2_sha256": locks["gate25_r2_freeze_sha256"],
        "disease_parameter_policy": disease["parameter_policy"],
        "analysis_policy": analysis,
    }
    document["gate26_execution_freeze_sha256"] = canonical_sha(document)
    return document


def write_initial_signoff(final_decision: str) -> None:
    signoff = {
        "schema_version": "riemensperger-final-review-signoff-v1",
        "status": "WAITING_RIEMENSPERGER_FINAL_HUMAN_REVIEW",
        "decision": "PENDING_HUMAN_REVIEW",
        "reviewer_1": "",
        "reviewer_2": "",
        "review_date": "",
        "evidence_paper_approved": False,
        "dopamine_mapping_approved": True,
        "healthy_rollout_qc_approved": False,
        "disease_rollout_qc_approved": False,
        "four_group_analysis_approved": False,
        "claim_lock_approved": False,
        "final_directional_decision": final_decision,
        "gate26_closed": False,
        "auto_sign": False,
    }
    write_json(ROOT / "research/validation/prospective/riemensperger_2011_final_reviewer_signoff.json", signoff)


def preflight() -> dict[str, Any]:
    runtime = verify_runtime_and_brain()
    locks = verify_project_locks()
    mapping = verify_mapping()
    if not EVIDENCE.is_file() or not HEALTHY_CONFIG.is_file() or not DISEASE_CONFIG.is_file() or not ANALYSIS_CONFIG.is_file():
        raise Gate26Error("Required Gate26 contract file is missing")
    freeze = build_freeze(runtime, locks, mapping)
    write_json(FREEZE, freeze)
    payload = {
        "status": "GATE26_SCIENTIFIC_PREFLIGHT_PASS",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "runtime": runtime,
        "locks": locks,
        "mapping": mapping,
        "freeze_sha256": freeze["gate26_execution_freeze_sha256"],
        "simulation_executed": False,
        "gpu_executed": False,
        "dry_run_contract_checked": True,
    }
    write_json(GATE26 / "manifests/gate26_preflight.json", payload)
    return payload


def _assert_freeze() -> dict[str, Any]:
    freeze = read_json(FREEZE)
    expected = freeze.pop("gate26_execution_freeze_sha256", None)
    if expected != canonical_sha(freeze):
        raise Gate26Error("Gate26 execution freeze hash mismatch")
    freeze["gate26_execution_freeze_sha256"] = expected
    if freeze.get("status") != "GATE26_SCIENTIFIC_EXECUTION_FROZEN" or freeze.get("disease_burden") != BURDEN or freeze.get("seeds") != SEEDS:
        raise Gate26Error("Gate26 execution freeze contract changed")
    return freeze


def _run_status(name: str, status: str) -> None:
    write_json(GATE26 / "manifests" / f"{name}_status.json", {"stage": name, "status": status, "recorded_at_utc": datetime.now(UTC).isoformat()})


def execute() -> dict[str, Any]:
    if EXECUTION_LOCK.exists():
        raise Gate26Error("Scientific execution lock already exists; no retry is allowed")
    freeze = _assert_freeze()
    runtime = verify_runtime_and_brain()
    write_json(EXECUTION_LOCK, {"status": "GATE26_EXECUTION_STARTED", "simulation_count_authorized": 10, "simulation_jobs_started": 0, "freeze_sha256": freeze["gate26_execution_freeze_sha256"], "started_at_utc": datetime.now(UTC).isoformat()})
    from scripts.run_riemensperger2011_healthy_replication import run as run_healthy
    from scripts.run_riemensperger2011_dopamine_replication import run as run_disease
    from scripts.analyze_riemensperger2011_healthy_comparability import run as run_comparability
    from scripts.analyze_riemensperger2011_four_group import run as run_four_group
    from scripts.assess_riemensperger2011_robustness import run as run_robustness

    healthy_status, _ = run_healthy(config_path=HEALTHY_CONFIG, evidence_path=EVIDENCE, mapping_path=MAPPING_SUMMARY, output=HEALTHY_OUTPUT, brain_root=BRAIN_ROOT, platform_root=RUNTIME_ROOT, brain_python=BRAIN_PYTHON, runner_python=Path(sys.executable), dry_run=False)
    _run_status("healthy", healthy_status)
    if healthy_status != "HEALTHY_VIRTUAL_REPLICATION_PASS":
        write_json(EXECUTION_LOCK, {"status": "GATE26_INCOMPLETE_TECHNICAL_EXECUTION", "failed_stage": "healthy", "healthy_status": healthy_status, "freeze_sha256": freeze["gate26_execution_freeze_sha256"], "simulation_count_started": 5})
        raise Gate26Error(f"Healthy batch failed: {healthy_status}; no disease jobs were run")

    comparability_status = run_comparability(evidence_path=EVIDENCE, healthy_path=HEALTHY_OUTPUT / "results/healthy_summary.json", lock_path=ROOT / "research/replications/riemensperger_2011/evidence/paper_evidence_lock.csv", contract_path=CONTRACT, output=COMPARABILITY_OUTPUT)
    _run_status("comparability", comparability_status)
    if comparability_status != "HEALTHY_COMPARABILITY_ACCEPTABLE_FOR_RATIO_ANALYSIS":
        raise Gate26Error(f"Healthy comparability failed: {comparability_status}")

    disease_status = run_disease(config_path=DISEASE_CONFIG, mapping_path=MAPPING_SUMMARY, evidence_path=EVIDENCE, output=DISEASE_OUTPUT, brain_root=BRAIN_ROOT, platform_root=RUNTIME_ROOT, brain_python=BRAIN_PYTHON, runner_python=Path(sys.executable), dry_run=False)
    _run_status("disease", disease_status)
    if disease_status != "DOPAMINE_DEFICIENCY_VIRTUAL_REPLICATION_PASS":
        write_json(EXECUTION_LOCK, {"status": "GATE26_INCOMPLETE_TECHNICAL_EXECUTION", "failed_stage": "disease", "healthy_status": healthy_status, "disease_status": disease_status, "freeze_sha256": freeze["gate26_execution_freeze_sha256"], "simulation_count_started": 10})
        raise Gate26Error(f"Disease batch failed: {disease_status}")

    analysis_status = run_four_group(evidence_lock=ROOT / "research/replications/riemensperger_2011/evidence/paper_evidence_lock.csv", contract_path=CONTRACT, analysis_config=ANALYSIS_CONFIG, healthy_path=HEALTHY_OUTPUT / "results/healthy_summary.json", disease_path=DISEASE_OUTPUT / "results/disease_summary.json", output=FOUR_GROUP_OUTPUT)
    _run_status("four_group_analysis", analysis_status)
    robustness_status = run_robustness(mapping_path=MAPPING_SUMMARY, disease_path=DISEASE_OUTPUT / "results/disease_summary.json", hypothesis_path=TRANSFORM, output=ROOT / "experiments/gate_21g_riemensperger_robustness", dry_run=False)
    _run_status("robustness", robustness_status)
    summary = read_json(FOUR_GROUP_OUTPUT / "results/four_group_summary.json")
    decision = summary.get("interpretation", "DIRECTIONAL_REPLICATION_INCONCLUSIVE")
    healthy_summary = read_json(HEALTHY_OUTPUT / "results/healthy_summary.json")
    disease_summary = read_json(DISEASE_OUTPUT / "results/disease_summary.json")
    final_status = {
        "21A": "RIEMENSPERGER_2011_EVIDENCE_LOCKED",
        "21B": healthy_status,
        "21C": comparability_status,
        "21D": MAPPING_READY,
        "21E": disease_status,
        "21F": analysis_status,
        "21G": robustness_status,
    }
    completion = {
        "schema_version": "gate26-riemensperger-completion-v1",
        "status": "GATE26_RIEMENSPERGER_FULL_COMPLETION",
        "source_commit": freeze["source_commit"],
        "execution_freeze_sha256": freeze["gate26_execution_freeze_sha256"],
        "gate_statuses": final_status,
        "healthy_seeds_planned": SEEDS,
        "healthy_seeds_passed": healthy_summary.get("n_seeds_passed", 0),
        "disease_seeds_planned": SEEDS,
        "disease_seeds_passed": disease_summary.get("n_seeds_passed", 0),
        "mapping_level": "DOPAMINE_CLASS_LEVEL_EXPLORATORY",
        "target_count": MAPPING_TARGET_COUNT,
        "disease_burden": BURDEN,
        "runtime_commit": RUNTIME_COMMIT,
        "healthy_checkpoint_sha256": HEALTHY_CHECKPOINT_SHA256,
        "disease_checkpoint_sha256": disease_summary.get("checkpoint_sha256", ""),
        "final_directional_decision": decision,
        "quantitative_validation_supported": False,
        "biological_validation_supported": False,
        "gene_specific_validation_supported": False,
        "clinical_validation_supported": False,
        "drug_validation_supported": False,
        "retuning_after_results": False,
        "posthoc_seed_selection": False,
        "posthoc_parameter_selection": False,
        "data_fabricated": False,
        "gate24e_unchanged": True,
        "gate25_unchanged": True,
    }
    write_json(COMPLETION, completion)
    _write_pipeline_status(final_status, decision, simulation_executed=True)
    _write_final_report_utf8(final_status, decision, healthy_summary, disease_summary, summary)
    _write_completion_update(final_status, decision, healthy_summary, disease_summary, summary)
    write_initial_signoff(decision)
    inventory = build_inventory(completion)
    write_json(INVENTORY, inventory)
    write_checksums(inventory)
    write_json(EXECUTION_LOCK, {"status": "GATE26_EXECUTION_COMPLETE", "simulation_jobs_started": 10, "freeze_sha256": freeze["gate26_execution_freeze_sha256"], "completed_at_utc": datetime.now(UTC).isoformat()})
    return completion


def _write_pipeline_status(statuses: dict[str, str], decision: str, *, simulation_executed: bool) -> None:
    write_json(ROOT / "experiments/riemensperger_2011_pipeline_status.json", {"statuses": statuses, "interpretation": decision, "claim": "Paper-guided computational replication only; no biological Parkinson validation claim.", "simulation_executed": simulation_executed, "data_fabricated": False})


def _write_final_report(statuses: dict[str, str], decision: str, healthy: dict[str, Any], disease: dict[str, Any], analysis: dict[str, Any]) -> None:
    report = ROOT / "docs/replications/riemensperger_2011/final_replication_report.md"
    text = f"""# Tái lập computational Riemensperger 2011

## 1. Câu hỏi nghiên cứu

Liệu perturbation cấp lớp neuron dopamine, được xây dựng từ bằng chứng Riemensperger 2011 và chạy qua neural core/FlyGym, có tái hiện được hướng thay đổi locomotion của ruồi thật hay không?

## 2. Evidence paper

- DTHg; ple: median speed 10.8 mm/s.
- DTHgFS±; ple: median speed 7.8 mm/s.
- WT: median speed 15 mm/s, secondary reference.
- Distance 15 phút: 425 cm control và 193 cm disease.
- Paper uncertainty: `NOT_REPORTED`; không tạo SD, SE, CI hoặc p-value.

## 3. Thiết kế bốn nhóm

A = real DTHg; ple control; B = virtual healthy; C = real DTHgFS±; ple; D = virtual dopamine-class perturbation.

## 4. Mapping và neural transform

Mapping là `DOPAMINE_CLASS_LEVEL_EXPLORATORY`, 342 target IDs, không gene-specific. Transform là presynaptic connectome-weight hypothesis với burden `1.0`; burden là tham số dimensionless, không phải phần trăm dopamine mất. Healthy checkpoint không bị ghi đè.

## 5. Runtime và protocol

Runtime `{RUNTIME_COMMIT}`, profile `{ARTIFACT_PROFILE}`, FlyGym 2.1.0, device CUDA. Cả hai nhánh dùng seed 0-4, 5000 steps, timestep 0.0001 s, stimulus p9, CPG 12 Hz và cùng world/controller. Scientific commands không dùng video CLI, compare-to hoặc visualization.

## 6. Kết quả execution

| Gate | Trạng thái |
| --- | --- |
{''.join(f'| {gate} | `{value}` |\\n' for gate, value in statuses.items())}

Healthy passed seeds: `{healthy.get('n_seeds_passed', 0)}/{healthy.get('n_seeds_planned', 5)}`.

Disease passed seeds: `{disease.get('n_seeds_passed', 0)}/{disease.get('n_seeds_planned', 5)}`.

## 7. Four-group analysis

- Real direction: 7.8 / 10.8 = 0.722222...
- Virtual direction: `{analysis.get('comparison', {}).get('virtual_effect_ratio', 'NOT_AVAILABLE')}`.
- Decision: `{decision}`.
- Interpretation is directional/descriptive only; no post-hoc threshold, calibration or holdout tuning.

## 8. Limitations và claim boundary

Virtual duration là 0.5 s, khác assay 15 phút; statistic/unit of analysis khác nhau; paper không báo uncertainty. Vì vậy không claim quantitative validation, parameter equivalence, gene-specific validation, biological Parkinson validation, clinical validation hoặc drug validation. Frames không phải replicate; seed là statistical unit.

Gate24E vẫn giữ `{GATE24E_RESULT}` và `{GATE24E_CROSS_ASSAY}`. Gate25-R2 vẫn giữ reproducibility freeze.

## 9. Reproducibility và human review

Per-seed metrics, manifests, checksums và execution freeze được lưu trong Gate26. Raw rollout lớn giữ local và không commit Git. Final signoff vẫn là `WAITING_RIEMENSPERGER_FINAL_HUMAN_REVIEW`; không auto-sign.
"""
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(text, encoding="utf-8")


def _write_final_report_utf8(statuses: dict[str, str], decision: str, healthy: dict[str, Any], disease: dict[str, Any], analysis: dict[str, Any]) -> None:
    """Write the final report with explicit UTF-8 Vietnamese text."""

    report = ROOT / "docs/replications/riemensperger_2011/final_replication_report.md"
    table = "".join(f"| {gate} | `{value}` |\n" for gate, value in statuses.items())
    text = f"""# Tái lập computational Riemensperger 2011

## 1. Câu hỏi nghiên cứu

Liệu perturbation cấp lớp neuron dopamine, được xây dựng từ bằng chứng Riemensperger 2011 và chạy qua neural core/FlyGym, có tái hiện được hướng thay đổi locomotion của ruồi thật hay không?

## 2. Bằng chứng từ paper

- DTHg; ple: median speed 10.8 mm/s.
- DTHgFS+/-; ple: median speed 7.8 mm/s.
- WT: median speed 15 mm/s, dùng như tham chiếu thứ cấp.
- Khoảng cách trong 15 phút: control 425 cm và disease 193 cm.
- Uncertainty của paper: `NOT_REPORTED`; không tạo SD, SE, CI hoặc p-value.

## 3. Thiết kế bốn nhóm

`A` = real DTHg; ple control; `B` = virtual healthy; `C` = real DTHgFS+/-; ple dopamine-deficient; `D` = virtual dopamine-class perturbation.

## 4. Mapping và neural transform

Mapping là `DOPAMINE_CLASS_LEVEL_EXPLORATORY` với 342 target IDs, không phải gene-specific. Transform là presynaptic connectome-weight hypothesis với burden `1.0`. Burden là tham số không đơn vị, không phải phần trăm dopamine mất. Healthy checkpoint không bị ghi đè.

## 5. Runtime và protocol

Runtime `{RUNTIME_COMMIT}`, profile `{ARTIFACT_PROFILE}`, FlyGym 2.1.0, thiết bị CUDA. Cả hai nhánh dùng seed 0-4, 5000 steps, timestep 0.0001 s, stimulus p9, CPG 12 Hz và cùng world/controller. Scientific command không dùng video CLI, compare-to hoặc visualization.

## 6. Trạng thái execution

| Gate | Trạng thái |
| --- | --- |
{table}

Healthy passed seeds: `{healthy.get('n_seeds_passed', 0)}/{healthy.get('n_seeds_planned', 5)}`.

Disease passed seeds: `{disease.get('n_seeds_passed', 0)}/{disease.get('n_seeds_planned', 5)}`.

## 7. Phân tích four-group

- Real direction ratio: 7.8 / 10.8 = 0.722222...
- Virtual direction ratio: `{analysis.get('comparison', {}).get('virtual_effect_ratio', 'NOT_AVAILABLE')}`.
- Decision: `{decision}`.
- Diễn giải chỉ mô tả directionality và magnitude; không tuning theo kết quả real disease, không hậu nghiệm đổi threshold.

## 8. Giới hạn và claim lock

Virtual duration là 0.5 s, khác assay 15 phút; statistic và unit of analysis cũng khác; paper không báo uncertainty. Vì vậy không claim quantitative validation, parameter equivalence, gene-specific validation, biological Parkinson validation, clinical validation hoặc drug validation. Frame không phải replicate; seed là đơn vị thống kê.

Gate24E vẫn giữ `{GATE24E_RESULT}` và `{GATE24E_CROSS_ASSAY}`. Gate25-R2 vẫn giữ reproducibility freeze đã khóa.

## 9. Reproducibility và human review

Per-seed metrics, manifest, telemetry GPU, checksum và execution freeze được lưu trong Gate26. Raw rollout lớn giữ ngoài Git và không commit. Final signoff vẫn là `WAITING_RIEMENSPERGER_FINAL_HUMAN_REVIEW`; không auto-sign.
"""
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(text, encoding="utf-8")


def _write_completion_update(statuses: dict[str, str], decision: str, healthy: dict[str, Any], disease: dict[str, Any], analysis: dict[str, Any]) -> None:
    update = ROOT / "docs/replications/riemensperger_2011/riemensperger_2011_pipeline_completion_update.md"
    table = "".join(f"| {gate} | `{value}` |\n" for gate, value in statuses.items())
    text = f"""# Cập nhật hoàn tất pipeline Riemensperger 2011

## Phạm vi

Đây là `PAPER_GUIDED_COMPUTATIONAL_REPLICATION`: kiểm tra perturbation cấp lớp dopamine có tái hiện hướng suy giảm locomotion của Riemensperger 2011 khi chạy qua neural core và FlyGym hay không. Đây không phải biological Parkinson validation, gene-specific validation, clinical validation hay drug validation.

## Trạng thái gate

| Gate | Trạng thái |
| --- | --- |
{table}

Gate24E và Gate25 được giữ nguyên kết luận đã khóa. Gate21D chỉ được reconciliate từ evidence đã review; không có mapping gene-specific mới.

## Hợp đồng rollout

Healthy và disease dùng cùng seed `0,1,2,3,4`, 5000 steps, duration 0.5 s, timestep 0.0001 s, stimulus `p9`, CPG 12 Hz, world và controller. QC yêu cầu finite values, timestamp tăng đều, contact, joint trajectory và action trajectory thay đổi. Telemetry GPU được lưu theo seed nếu `nvidia-smi` khả dụng.

## Kết quả hiện tại

- Healthy: `{healthy.get('status', 'NOT_AVAILABLE')}`; `{healthy.get('n_seeds_passed', 0)}/{healthy.get('n_seeds_planned', 5)} seeds passed.
- Disease: `{disease.get('status', 'NOT_AVAILABLE')}`; `{disease.get('n_seeds_passed', 0)}/{disease.get('n_seeds_planned', 5)} seeds passed.
- Four-group interpretation: `{analysis.get('interpretation', 'NOT_AVAILABLE')}`.
- Final decision: `{decision}`.

## Checklist phê duyệt cuối

File signoff ở `research/validation/prospective/riemensperger_2011_final_reviewer_signoff.json` vẫn để `WAITING_RIEMENSPERGER_FINAL_HUMAN_REVIEW`. Reviewer, ngày review và quyết định cuối phải do người có thẩm quyền điền; không auto-sign và không đóng Gate26 bằng mã.
"""
    update.parent.mkdir(parents=True, exist_ok=True)
    update.write_text(text, encoding="utf-8")


def build_inventory(completion: dict[str, Any]) -> dict[str, Any]:
    critical = [
        EVIDENCE, MAPPING_SUMMARY, MAPPING_SPEC, TRANSFORM, HEALTHY_CONFIG, DISEASE_CONFIG, ANALYSIS_CONFIG, CONTRACT,
        FREEZE, COMPLETION, ROOT / "experiments/riemensperger_2011_pipeline_status.json", ROOT / "docs/replications/riemensperger_2011/final_replication_report.md",
        ROOT / "experiments/gate_21b_riemensperger_healthy/metrics/healthy_per_seed_metrics.csv", ROOT / "experiments/gate_21b_riemensperger_healthy/results/healthy_summary.json",
        ROOT / "experiments/gate_21e_riemensperger_disease/metrics/disease_per_seed_metrics.csv", ROOT / "experiments/gate_21e_riemensperger_disease/results/disease_summary.json",
        ROOT / "experiments/gate_21f_four_group_analysis/metrics/four_group_table.csv", ROOT / "experiments/gate_21f_four_group_analysis/results/four_group_summary.json",
        ROOT / "experiments/gate_21b_riemensperger_healthy/results/gpu_telemetry.json", ROOT / "experiments/gate_21e_riemensperger_disease/results/gpu_telemetry.json",
        ROOT / "scripts/run_gate26_riemensperger_full_completion.py", ROOT / "docs/replications/riemensperger_2011/riemensperger_2011_pipeline_completion_update.md",
        ROOT / "research/validation/prospective/riemensperger_2011_final_reviewer_signoff.json",
    ]
    records = []
    for path in critical:
        if path.is_file():
            records.append({"path": _relative(path), "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    return {"schema_version": "gate26-reproducibility-inventory-v1", "status": "COMPLETE", "raw_rollouts_committed": False, "record_count": len(records), "records": records, "completion_manifest_sha256": canonical_sha(completion)}


def write_checksums(inventory: dict[str, Any]) -> None:
    CHECKSUMS.parent.mkdir(parents=True, exist_ok=True)
    CHECKSUMS.write_text("\n".join(f"{record['sha256']}  {record['path']}" for record in inventory["records"]) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = preflight() if args.preflight else execute()
    except (Gate26Error, OSError, ValueError, yaml.YAMLError) as exc:
        print(f"GATE26_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
