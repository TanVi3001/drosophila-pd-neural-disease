"""Chay disease rollouts Gate 12 neu co artifact hop le, khong fake ket qua."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_healthy_baseline_multiseed import (
    _finite_rollout,
    _read_scalar_metrics,
    _rollout_quality,
)


PLAN_DEFAULT = ROOT / "experiments/gate_12_disease_rollouts/configs/disease_rollout_plan.yaml"
HEALTHY_MANIFEST_DEFAULT = ROOT / "experiments/gate_11_healthy_baseline/manifests/healthy_baseline_manifest.json"
MAPPING_DEFAULT = ROOT / "research/disease_mapping/disease_condition_readiness.csv"
RUNNER = ROOT / "scripts/run_neural_experiment.py"
CANONICAL_METRICS = (
    "mean_planar_speed_mm_s",
    "distance_traveled_mm",
    "displacement_mm",
)


def _is_proxy_plan(plan: Mapping[str, Any]) -> bool:
    """Return whether a plan uses the Gate 12C proxy contract."""

    return str(plan.get("schema_version", "")).startswith(
        "gate-12c-proxy-ready-rollout-plan-"
    )
CSV_FIELDS = (
    "condition_id",
    "seed",
    "run_status",
    "skip_reason",
    "step_count",
    "timestep_s",
    "duration_s",
    *CANONICAL_METRICS,
    "walking_speed_mm_s_raw",
    "total_distance_mm_raw",
    "thorax_displacement_mm_raw",
    "no_nan",
    "no_inf",
    "locomotion_detected",
    "contact_detected",
    "timestamp_valid",
    "quaternion_valid",
    "joint_action_trajectory_valid",
    "metric_contract_status",
)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def _resolve(value: str | Path, *, base: Path = ROOT) -> Path:
    path = Path(value).expanduser()
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def _load_yaml(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        raise ValueError(f"YAML phai la mapping: {path}")
    return document


def _read_mapping(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {
            str(row.get("condition_id", "")).strip(): {
                str(key): str(value or "").strip() for key, value in row.items()
            }
            for row in csv.DictReader(handle)
            if str(row.get("condition_id", "")).strip()
        }


def _mapping_details(condition_id: str, mapping: Mapping[str, Mapping[str, str]]) -> tuple[str, list[str], str]:
    row = mapping.get(condition_id, {})
    status = row.get("mapping_status", "NOT_AVAILABLE")
    provenance = [
        value
        for value in (row.get("paper_provenance", ""), row.get("neuron_provenance", ""))
        if value
    ]
    if status in {"MAPPED_GENE_SPECIFIC", "GENE_SPECIFIC"}:
        scope = "gene_specific"
    elif status in {"MAPPED_EXPLORATORY", "CLASS_LEVEL_EXPLORATORY_ONLY"}:
        scope = "class_level"
    elif status in {"ORGANISM_LEVEL", "MODEL_SCOPE_NOT_CELL_SPECIFIC"}:
        scope = "organism_level"
    else:
        scope = "not_available"
    reason = f"mapping_status={status}"
    if row.get("blocker"):
        reason += f"; blocker={row['blocker']}"
    return scope, provenance, reason


def _runtime_probe(
    *, brain_root: Path, platform_root: Path, brain_python: Path, device: str
) -> tuple[bool, list[str], bool]:
    missing: list[str] = []
    if not brain_root.is_dir():
        missing.append(f"brain_root_missing:{brain_root}")
    if not (platform_root / "scripts/run_brain_body_rollout.py").is_file():
        missing.append(f"platform_runner_missing:{platform_root / 'scripts/run_brain_body_rollout.py'}")
    for relative in (
        "brain_body_bridge.py",
        "code/run_pytorch.py",
        "data/2025_Completeness_783.csv",
        "data/2025_Connectivity_783.parquet",
        "data/plastic_weights.pt",
    ):
        if not (brain_root / relative).is_file():
            missing.append(f"brain_artifact_missing:{relative}")
    if not brain_python.is_file():
        missing.append(f"brain_python_missing:{brain_python}")
        return False, missing, False
    cuda_available = False
    probe = subprocess.run(
        [str(brain_python), "-c", "import torch; print('1' if torch.cuda.is_available() else '0')"],
        capture_output=True,
        text=True,
        check=False,
    )
    cuda_available = probe.returncode == 0 and probe.stdout.strip().splitlines()[-1:] == ["1"]
    if device == "cuda" and not cuda_available:
        missing.append("cuda_unavailable_for_requested_device=cuda")
    return not missing, missing, cuda_available


def _config_blockers(
    *, condition_id: str, config_path: Path, mapping_scope: str, proxy_mode: bool = False
) -> tuple[list[str], dict[str, Any]]:
    if not config_path.is_file():
        return [f"missing_condition_template:{_relative(config_path)}"], {}
    try:
        document = _load_yaml(config_path)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        return [f"invalid_condition_yaml:{exc}"], {}
    blockers: list[str] = []
    declared_id = str(document.get("condition_id", "")).strip()
    if declared_id not in {condition_id, f"{condition_id}_template"}:
        blockers.append(f"condition_id_mismatch={declared_id or 'MISSING'}")

    is_proxy_config = proxy_mode or str(document.get("schema_version", "")).startswith(
        "gate-12c-proxy-condition-"
    )
    if is_proxy_config:
        return _proxy_config_blockers(
            condition_id=condition_id,
            document=document,
            initial_blockers=blockers,
        ), document

    status = str(document.get("status", "")).strip()
    if not status or status.startswith("WAITING") or "TEMPLATE" in status.upper():
        blockers.append(f"condition_status={status or 'MISSING'}")
    if not (document.get("target_neurons") or document.get("target_edges")):
        blockers.append("target_neurons_or_edges_missing")
    if not document.get("burden_curve"):
        blockers.append("burden_curve_missing")
    if not document.get("full_burden"):
        blockers.append("full_burden_missing")
    provenance = document.get("provenance")
    if not isinstance(provenance, list) or not [item for item in provenance if str(item).strip()]:
        blockers.append("condition_provenance_missing")
    declared_scope = str(document.get("mapping_scope", "")).strip()
    if mapping_scope == "not_available":
        blockers.append("reviewed_mapping_or_checkpoint_provenance_missing")
    elif mapping_scope == "class_level" and declared_scope != "class_level":
        blockers.append("class_level_scope_not_declared_in_condition")
    elif mapping_scope == "organism_level":
        blockers.append("organism_level_scope_not_allowed_for_neural_rollout")
    return blockers, document


def _proxy_config_blockers(
    *, condition_id: str, document: Mapping[str, Any], initial_blockers: Sequence[str]
) -> list[str]:
    """Validate Gate 12C proxy readiness without requiring fake neural targets."""

    blockers = list(initial_blockers)
    status = str(document.get("run_status", "")).strip()
    if status != "RUN_READY_FOR_GATE_12D":
        blockers.append(f"condition_status={status or 'MISSING'}")

    scope = str(document.get("scope", "")).strip()
    target_definition = document.get("target_definition")
    target_definition = target_definition if isinstance(target_definition, Mapping) else {}
    burden = document.get("burden")
    burden = burden if isinstance(burden, Mapping) else {}
    runtime = document.get("runtime")
    runtime = runtime if isinstance(runtime, Mapping) else {}
    provenance = document.get("provenance")
    provenance = provenance if isinstance(provenance, Mapping) else {}

    if scope in {"organism_level_proxy", "class_level_proxy"}:
        if not str(target_definition.get("proxy_target", "")).strip():
            blockers.append("proxy_target_missing")
        operator = document.get("proxy_operator")
        if not isinstance(operator, Mapping) or str(operator.get("type", "")).strip() != "disease_layer_burden_proxy":
            blockers.append("proxy_operator_invalid")
        if operator.get("biological_mapping_claim") is not False:
            blockers.append("biological_mapping_claim_not_false")
        if target_definition.get("gene_specific_mapping") is not False:
            blockers.append("gene_specific_mapping_not_false")
        if target_definition.get("target_neurons") not in ([], None):
            blockers.append("proxy_target_neurons_must_be_empty")
        if target_definition.get("target_edges") not in ([], None):
            blockers.append("proxy_target_edges_must_be_empty")
    elif scope == "gene_specific":
        if not (target_definition.get("target_neurons") or target_definition.get("target_edges")):
            blockers.append("target_neurons_or_edges_missing")
        if not str(target_definition.get("root_id_mapping_source", "")).strip() or str(
            target_definition.get("root_id_mapping_source", "")
        ).strip() == "NOT_AVAILABLE":
            blockers.append("root_id_mapping_source_missing")
        if not str(provenance.get("checkpoint_mapping_provenance", "")).strip():
            blockers.append("checkpoint_mapping_provenance_missing")
    else:
        blockers.append(f"proxy_scope_invalid={scope or 'MISSING'}")

    curve = burden.get("burden_curve")
    if not isinstance(curve, list) or not curve:
        blockers.append("burden_curve_missing")
    full_burden = burden.get("full_burden")
    if full_burden in (None, "", "NOT_AVAILABLE"):
        blockers.append("full_burden_missing")
    else:
        try:
            if not math.isfinite(float(full_burden)):
                blockers.append("full_burden_not_finite")
        except (TypeError, ValueError):
            blockers.append("full_burden_not_numeric")

    if runtime.get("compatible_with_gate11_runtime") is not True:
        blockers.append("gate11_runtime_incompatible")
    if not str(provenance.get("mapping_source", "")).strip():
        blockers.append("proxy_provenance_missing")
    if not str(provenance.get("reviewer", "")).strip() or str(provenance.get("reviewer", "")).strip() == "CHUA_DIEN":
        blockers.append("proxy_reviewer_missing")
    if not str(provenance.get("review_date", "")).strip() or str(provenance.get("review_date", "")).strip() == "CHUA_DIEN":
        blockers.append("proxy_review_date_missing")
    boundary = document.get("scientific_boundary")
    if not isinstance(boundary, Mapping) or not str(boundary.get("statement", "")).strip():
        blockers.append("scientific_boundary_missing")
    return blockers


def _blank_row(condition_id: str, seed: int, *, steps: int, timestep_s: float, status: str, reason: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        field: "" for field in CSV_FIELDS
    }
    row.update(
        {
            "condition_id": condition_id,
            "seed": seed,
            "run_status": status,
            "skip_reason": reason,
            "step_count": steps,
            "timestep_s": timestep_s,
            "duration_s": steps * timestep_s,
        }
    )
    return row


def _read_finite_metrics(path: Path) -> tuple[dict[str, float], bool]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        source = document.get("scalar_metrics", document)
        if not isinstance(source, dict):
            return {}, False
        values: dict[str, float] = {}
        finite = True
        for key, value in source.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if not math.isfinite(float(value)):
                    finite = False
                else:
                    values[str(key)] = float(value)
        return values, finite
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}, False


def _run_seed(
    *,
    condition_id: str,
    config_path: Path,
    seed: int,
    plan: Mapping[str, Any],
    brain_root: Path,
    platform_root: Path,
    brain_python: Path,
    annotations: Path,
    output_root: Path,
) -> dict[str, Any]:
    runtime = plan["base_runtime"]
    steps = int(runtime["step_count"])
    timestep_s = float(runtime["timestep_s"])
    output = output_root / "results" / condition_id / f"seed_{seed:03d}"
    output.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(RUNNER),
        "--brain-root", str(brain_root),
        "--platform-root", str(platform_root),
        "--brain-python", str(brain_python),
        "--config", str(config_path),
        "--age-days", str(float(runtime.get("age_days", 20.0))),
        "--seed", str(seed),
        "--steps", str(steps),
        "--device", str(runtime.get("device", "cuda")),
        "--output", str(output),
        "--annotations", str(annotations),
        "--stimulus", str(runtime.get("stimulus", "p9")),
        "--cpg-frequency-hz", str(float(runtime.get("cpg_frequency_hz", 12.0))),
    ]
    environment = os.environ.copy()
    environment.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False, env=environment)
    log = f"=== condition={condition_id} seed={seed} return_code={completed.returncode} ===\n"
    log += completed.stdout + completed.stderr
    with (output_root / "logs" / "run.log").open("a", encoding="utf-8") as handle:
        handle.write(log)

    metrics_path = output / "metrics" / "metrics.json"
    row = _blank_row(condition_id, seed, steps=steps, timestep_s=timestep_s, status="FAILED", reason="")
    if completed.returncode != 0:
        row["skip_reason"] = f"runner_return_code={completed.returncode}"
        return row
    required = [output / "rollout.json", output / "rollout.npz", metrics_path]
    missing = [str(path.relative_to(output)) for path in required if not path.is_file()]
    metrics, metrics_finite = _read_finite_metrics(metrics_path)
    finite, invalid_arrays = _finite_rollout(output / "rollout.npz")
    quality = _rollout_quality(
        output / "rollout.npz",
        expected_frames=steps + 1,
        expected_timestep_s=timestep_s,
        metrics=metrics,
    )
    required_present = all(metric in quality and quality[metric] is not None for metric in CANONICAL_METRICS)
    no_nan_inf = not missing and finite and metrics_finite
    action_qc = all(
        quality.get(key) == "PASS"
        for key in ("joint_trajectory_changes", "action_trajectory_valid", "observation_state_valid")
    )
    qc_pass = all(
        quality.get(key) == "PASS"
        for key in (
            "timestamp_monotonic",
            "timestep_consistent",
            "locomotion_detected",
            "contact_detected",
            "quaternion_valid",
        )
    ) and action_qc
    if completed.returncode == 0 and no_nan_inf and required_present and qc_pass:
        row.update(
            {
                "run_status": "PASS",
                "no_nan": "PASS",
                "no_inf": "PASS",
                "locomotion_detected": quality["locomotion_detected"],
                "contact_detected": quality["contact_detected"],
                "timestamp_valid": quality["timestamp_monotonic"],
                "quaternion_valid": quality["quaternion_valid"],
                "joint_action_trajectory_valid": "PASS",
                "metric_contract_status": "PASS",
                "mean_planar_speed_mm_s": quality["mean_planar_speed_mm_s"],
                "distance_traveled_mm": quality["distance_traveled_mm"],
                "displacement_mm": quality["displacement_mm"],
                "walking_speed_mm_s_raw": metrics.get("walking_speed_mm_s", ""),
                "total_distance_mm_raw": metrics.get("total_distance_mm", ""),
                "thorax_displacement_mm_raw": quality["thorax_displacement_xy_mm"],
            }
        )
        return row
    reasons = []
    if missing:
        reasons.append("missing=" + ";".join(missing))
    if invalid_arrays:
        reasons.append("invalid_arrays=" + ";".join(invalid_arrays))
    if not no_nan_inf:
        reasons.append("numeric_qc_failed")
    if not required_present:
        reasons.append("canonical_metrics_missing")
    if not qc_pass:
        reasons.append("physical_qc_failed")
    row["skip_reason"] = ";".join(reasons) or "rollout_failed_quality_gate"
    return row


def _condition_status(rows: Sequence[Mapping[str, Any]]) -> str:
    statuses = {str(row["run_status"]) for row in rows}
    if statuses == {"SKIPPED"}:
        return "SKIPPED"
    if statuses == {"PASS"}:
        return "PASS"
    return "FAILED"


def _condition_summary(
    condition: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    *,
    mapping_scope: str,
    provenance: Sequence[str],
    config_path: Path,
    skip_reason: str = "",
) -> dict[str, Any]:
    pass_rows = [row for row in rows if row.get("run_status") == "PASS"]
    summary: dict[str, Any] = {
        "condition_id": str(condition["condition_id"]),
        "config_path": _relative(config_path),
        "run_status": _condition_status(rows),
        "planned_seed_count": len(rows),
        "seed_count": len(pass_rows),
        "mapping_scope": mapping_scope,
        "provenance": list(provenance),
        "skip_reason": skip_reason,
        "runs": list(rows),
    }
    for metric in CANONICAL_METRICS:
        values = [float(row[metric]) for row in pass_rows if isinstance(row.get(metric), (int, float))]
        if values:
            mean = sum(values) / len(values)
            variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1) if len(values) > 1 else 0.0
            summary[f"{metric}_mean"] = mean
            summary[f"{metric}_std"] = math.sqrt(variance)
    return summary


def _write_report(
    path: Path,
    *,
    status: str,
    healthy_manifest: Mapping[str, Any],
    summaries: Sequence[Mapping[str, Any]],
    runtime_reasons: Sequence[str],
) -> None:
    lines = [
        "# Gate 12 — Disease Condition Multi-Seed Rollouts",
        "",
        f"**Trạng thái:** `{status}`",
        "",
        "## Input status",
        "",
        "- Gate 09B: `READY_FOR_CALIBRATION` theo audit target hiện có.",
        "- Gate 11: `HEALTHY_BASELINE_RUNTIME_PASS`.",
        f"- Metric contract: `{healthy_manifest.get('metric_contract', {}).get('status', 'NOT_REPORTED')}`.",
        f"- Healthy baseline duration: `{healthy_manifest.get('runs', [{}])[0].get('duration_s', 'NOT_REPORTED')} s`.",
        "- Healthy baseline seeds: `0–5`.",
        "",
        "## Scope",
        "",
        "Gate 12 chỉ chạy computational disease perturbation rollouts. Không calibration, "
        "không holdout validation, không tune parameter và không dùng Chen/Pozo để khớp tham số.",
        "Kết quả không phải biological Parkinson validation.",
        "",
        "## Runtime gate",
        "",
    ]
    if runtime_reasons:
        lines.append("- Runtime blocker: `" + "; ".join(runtime_reasons) + "`")
    else:
        lines.append("- Runtime artifact: `AVAILABLE`")
    lines.extend(["", "## Conditions", "", "| Condition | Status | Seeds PASS / planned | Mapping scope | Reason |", "| --- | --- | ---: | --- | --- |"])
    for summary in summaries:
        lines.append(
            f"| `{summary['condition_id']}` | `{summary['run_status']}` | "
            f"{summary['seed_count']} / {summary['planned_seed_count']} | "
            f"`{summary['mapping_scope']}` | {summary.get('skip_reason') or ''} |"
        )
    lines.extend(["", "## Metrics", ""])
    measured = [summary for summary in summaries if summary.get("seed_count", 0) > 0]
    if not measured:
        lines.append("Chưa có disease metric nào được ghi nhận: mọi condition đều bị skip hoặc chưa qua QC. Không tạo metric giả.")
    else:
        lines.extend([
            "Các giá trị dưới đây là mean ± sample SD giữa các seed PASS; không phải dữ liệu ruồi thật.",
            "",
            "| Condition | Mean planar speed (mm/s) | Distance (mm) | Displacement (mm) |",
            "| --- | ---: | ---: | ---: |",
        ])
        for summary in measured:
            def fmt(metric: str) -> str:
                mean = summary.get(f"{metric}_mean")
                std = summary.get(f"{metric}_std")
                return f"{mean:.6g} ± {std:.6g}" if isinstance(mean, float) and isinstance(std, float) else "NOT_REPORTED"
            lines.append(
                f"| `{summary['condition_id']}` | {fmt('mean_planar_speed_mm_s')} | "
                f"{fmt('distance_traveled_mm')} | {fmt('displacement_mm')} |"
            )
    lines.extend(["", "## Healthy comparison", ""])
    if measured:
        lines.append("So sánh disease với Healthy chỉ được tính cho seed và metric có rollout PASS; không dùng target literature để tune trong Gate 12.")
    else:
        lines.append("Chưa thực hiện so sánh vì chưa có disease rollout PASS. Healthy baseline vẫn được giữ nguyên làm reference.")
    lines.extend([
        "",
        "## Limitations",
        "",
        "- Duration hiện tại khoảng 0,5 giây, ngắn hơn nhiều behavioral assay trong literature.",
        "- Condition gene chỉ được gọi là gene-specific khi mapping có provenance gene-specific; class-level/organism-level không được gọi như vậy.",
        "- Đây là computational perturbation, chưa phải calibration và chưa phải holdout validation.",
        "- Không suy ra cơ chế Parkinson sinh học, chẩn đoán, clinical prediction hay đáp ứng thuốc.",
        "",
        "## Final status",
        "",
        f"`{status}`. Không calibration và không holdout validation đã được chạy trong Gate 12.",
    ])
    _write_text(path, "\n".join(lines) + "\n")


def run_campaign(args: argparse.Namespace) -> int:
    plan_path = _resolve(args.config)
    plan = _load_yaml(plan_path)
    proxy_plan = _is_proxy_plan(plan)
    healthy_manifest_path = _resolve(args.healthy_manifest)
    healthy_manifest = json.loads(healthy_manifest_path.read_text(encoding="utf-8"))
    if healthy_manifest.get("status") != "PASS":
        raise RuntimeError("Healthy baseline manifest khong PASS.")
    if healthy_manifest.get("seed_count") != 6 or healthy_manifest.get("metric_contract", {}).get("status") != "PASS":
        raise RuntimeError("Healthy baseline khong dat seed_count=6 va metric contract PASS.")
    if healthy_manifest.get("calibration_run") or healthy_manifest.get("holdout_validation_run"):
        raise RuntimeError("Healthy baseline manifest co calibration/holdout flag bat thuong.")

    output_root = _resolve(args.output)
    results_dir = output_root / "results"
    manifests_dir = output_root / "manifests"
    logs_dir = output_root / "logs"
    results_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    _write_text(logs_dir / "run.log", "# Gate 12 disease rollout log\n")

    runtime = plan["base_runtime"]
    brain_root = _resolve(args.brain_root)
    platform_root = _resolve(args.platform_root)
    brain_python = _resolve(args.brain_python) if args.brain_python else platform_root / ".venv/Scripts/python.exe"
    annotations = _resolve(args.annotations)
    runtime_ok, runtime_reasons, cuda_available = _runtime_probe(
        brain_root=brain_root,
        platform_root=platform_root,
        brain_python=brain_python,
        device=str(runtime.get("device", "cuda")),
    )
    mapping = _read_mapping(_resolve(args.mapping))
    rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for condition in plan.get("conditions", []):
        condition_id = str(condition["condition_id"])
        if condition.get("calibration", False) or condition.get("holdout_validation", False):
            raise RuntimeError(f"Gate 12 condition {condition_id} bat calibration/holdout flag.")
        config_value = condition.get(
            "config",
            condition.get("config_path", f"configs/conditions/{condition_id}.yaml"),
        )
        config_path = _resolve(config_value)
        mapping_scope, mapping_provenance, mapping_reason = _mapping_details(condition_id, mapping)
        if proxy_plan:
            # Gate 12C proxy scope is explicitly reviewed in the proxy config;
            # the old gene-mapping CSV must not block an organism-level proxy.
            mapping_scope = str(condition.get("scope", "not_available")).strip() or "not_available"
            mapping_provenance = []
            mapping_reason = ""
        blockers, condition_document = _config_blockers(
            condition_id=condition_id,
            config_path=config_path,
            mapping_scope=mapping_scope,
            proxy_mode=proxy_plan,
        )
        if proxy_plan and str(condition.get("run_status", "")).strip() != "RUN_READY_FOR_GATE_12D":
            blockers.append("condition_declared_not_run_ready")
        provenance = list(mapping_provenance) + [
            str(item)
            for item in (
                condition_document.get("provenance", [])
                if isinstance(condition_document.get("provenance", []), list)
                else []
            )
            if str(item).strip()
        ]
        if proxy_plan and isinstance(condition_document.get("provenance"), Mapping):
            provenance = [
                str(value)
                for value in condition_document["provenance"].values()
                if str(value).strip()
            ]
        reason_parts = []
        if not runtime_ok:
            reason_parts.append("MISSING_RUNTIME_ARTIFACT: " + "; ".join(runtime_reasons))
        if blockers:
            reason_parts.append("MISSING_DISEASE_ARTIFACT: " + "; ".join(blockers))
        if mapping_reason:
            reason_parts.append(mapping_reason)
        reason = "; ".join(reason_parts)
        condition_rows: list[dict[str, Any]] = []
        if reason:
            for seed in plan["seeds"]["values"]:
                condition_rows.append(
                    _blank_row(
                        condition_id,
                        int(seed),
                        steps=int(runtime["step_count"]),
                        timestep_s=float(runtime["timestep_s"]),
                        status="SKIPPED",
                        reason=reason,
                    )
                )
        else:
            for seed in plan["seeds"]["values"]:
                condition_rows.append(
                    _run_seed(
                        condition_id=condition_id,
                        config_path=config_path,
                        seed=int(seed),
                        plan=plan,
                        brain_root=brain_root,
                        platform_root=platform_root,
                        brain_python=brain_python,
                        annotations=annotations,
                        output_root=output_root,
                    )
                )
        rows.extend(condition_rows)
        summaries.append(
            _condition_summary(
                condition,
                condition_rows,
                mapping_scope=mapping_scope,
                provenance=provenance,
                config_path=config_path,
                skip_reason=reason,
            )
        )

    metrics_csv = results_dir / "disease_metrics.csv"
    with metrics_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    pass_count = sum(row["run_status"] == "PASS" for row in rows)
    failed_count = sum(row["run_status"] == "FAILED" for row in rows)
    if pass_count == 0 and failed_count == 0:
        status = "DISEASE_ROLLOUTS_BLOCKED"
    elif failed_count or pass_count < len(rows):
        status = "DISEASE_ROLLOUTS_PARTIAL"
    else:
        status = "DISEASE_ROLLOUTS_PASS"
    payload = {
        "schema_version": "gate-12-disease-metrics-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "simulation_data_fabricated": False,
        "no_gene_specific_mapping": proxy_plan,
        "no_calibration": True,
        "no_holdout_validation": True,
        "forbidden_uses": plan.get("forbidden_uses", []),
        "metric_contract": list(CANONICAL_METRICS),
        "rows": rows,
        "conditions": summaries,
    }
    metrics_json = results_dir / "disease_metrics.json"
    _write_text(metrics_json, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    external_audit = ROOT / "experiments/gate_11_healthy_baseline/manifests/external_input_audit.json"
    external_summary: dict[str, Any] = {"status": "NOT_AVAILABLE"}
    if external_audit.is_file():
        external_summary = {
            "path": _relative(external_audit),
            "sha256": _sha256(external_audit),
            "status": json.loads(external_audit.read_text(encoding="utf-8")).get("status", "UNKNOWN"),
        }
    manifest = {
        "schema_version": "gate-12-disease-rollout-manifest-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "git_commit": _git_commit(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cuda_available": cuda_available,
        "seeds": [int(seed) for seed in plan["seeds"]["values"]],
        "source_healthy_baseline_manifest": _relative(healthy_manifest_path),
        "source_healthy_baseline_manifest_sha256": _sha256(healthy_manifest_path),
        "config_sha256": _sha256(plan_path),
        "metrics_csv_sha256": _sha256(metrics_csv),
        "metrics_json_sha256": _sha256(metrics_json),
        "metric_contract": list(CANONICAL_METRICS),
        "no_gene_specific_mapping": proxy_plan,
        "forbidden_uses": plan.get("forbidden_uses", []),
        "conditions": summaries,
        "external_artifact_audit": external_summary,
        "no_calibration": True,
        "no_holdout_validation": True,
        "scientific_boundary": (
            "Computational locomotion disease perturbation only; not biological Parkinson validation, "
            "clinical prediction, diagnosis, drug response, or replacement for wet-lab experiments."
        ),
    }
    manifest_path = manifests_dir / "disease_rollout_manifest.json"
    _write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    _write_report(
        ROOT / "docs/disease_rollouts/gate_12_disease_rollout_report.md",
        status=("DISEASE_ROLLOUTS_PASS\nREADY_FOR_CHEN_CALIBRATION" if status == "DISEASE_ROLLOUTS_PASS" else status),
        healthy_manifest=healthy_manifest,
        summaries=summaries,
        runtime_reasons=runtime_reasons,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=PLAN_DEFAULT)
    parser.add_argument("--healthy-manifest", type=Path, default=HEALTHY_MANIFEST_DEFAULT)
    parser.add_argument("--mapping", type=Path, default=MAPPING_DEFAULT)
    parser.add_argument("--brain-root", type=Path, default=ROOT / "external/fly-brain")
    parser.add_argument("--platform-root", type=Path, default=ROOT.parent / "drosophila-pd-flygym")
    parser.add_argument("--brain-python", type=Path, default=None)
    parser.add_argument("--annotations", type=Path, default=ROOT / "annotations/neuron_annotations.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/gate_12_disease_rollouts")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run_campaign(args)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
