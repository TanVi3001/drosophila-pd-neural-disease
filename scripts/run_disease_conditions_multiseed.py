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
import shutil
import subprocess
import sys
import tempfile
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


def _is_proxy_run_config(plan: Mapping[str, Any]) -> bool:
    """Return whether a config requests the Gate 12D proxy matrix."""

    return str(plan.get("schema_version", "")).startswith(
        "gate-12d-proxy-rollout-run-config-"
    )


def _is_integrated_proxy_run_config(plan: Mapping[str, Any]) -> bool:
    """Return whether a plan requests Gate 12G's real action-hook runs."""

    return str(plan.get("schema_version", "")).startswith(
        "gate-12g-integrated-proxy-rollout-config-"
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

PROXY_CSV_FIELDS = (
    "condition_id",
    "scope",
    "gene_specific_mapping",
    "burden_level",
    "burden_label",
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
    "operator_applied",
    "operator_config_sha256",
)

PROXY_SUMMARY_FIELDS = (
    "condition_id",
    "scope",
    "burden_level",
    "burden_label",
    "planned_seed_count",
    "n_success",
    "mean_planar_speed_mm_s_mean",
    "mean_planar_speed_mm_s_std",
    "distance_traveled_mm_mean",
    "distance_traveled_mm_std",
    "displacement_mm_mean",
    "displacement_mm_std",
    "qc_pass_count",
    "failed_count",
    "status",
)

INTEGRATED_PROXY_CSV_FIELDS = (
    "condition_id",
    "scope",
    "gene_specific_mapping",
    "burden_level",
    "burden_label",
    "seed",
    "run_status",
    "skip_reason",
    "step_count",
    "timestep_s",
    "duration_s",
    "operator_applied",
    "operator_config_sha256",
    "action_changed_for_positive_burden",
    "burden_zero_identity_pass",
    "adhesion_onoff_unchanged",
    "mean_planar_speed_mm_s",
    "distance_traveled_mm",
    "displacement_mm",
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

INTEGRATED_PROXY_SUMMARY_FIELDS = (
    "condition_id",
    "burden_level",
    "burden_label",
    "n_success",
    "mean_planar_speed_mm_s_mean",
    "mean_planar_speed_mm_s_std",
    "distance_traveled_mm_mean",
    "distance_traveled_mm_std",
    "displacement_mm_mean",
    "displacement_mm_std",
    "operator_applied_count",
    "qc_pass_count",
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


def _proxy_operator_config_blockers(path: Path) -> tuple[list[str], dict[str, Any]]:
    """Validate an optional Gate 12E operator config without running it."""

    if not path.is_file():
        return [f"operator_config_missing:{_relative(path)}"], {}
    try:
        document = _load_yaml(path)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        return [f"invalid_operator_config:{exc}"], {}
    blockers: list[str] = []
    if document.get("status") != "OPERATOR_IMPLEMENTED":
        blockers.append(f"operator_status={document.get('status', 'MISSING')}")
    operator = document.get("operator")
    if not isinstance(operator, Mapping) or operator.get("type") != "amplitude_attenuation":
        blockers.append("operator_type_invalid")
    else:
        for field in ("attenuation_strength", "noise_strength"):
            try:
                if not math.isfinite(float(operator.get(field))):
                    blockers.append(f"operator_{field}_not_finite")
            except (TypeError, ValueError):
                blockers.append(f"operator_{field}_not_numeric")
    allowed = document.get("allowed_conditions")
    if not isinstance(allowed, list) or not {"alpha_synuclein", "pink1"}.issubset(set(allowed)):
        blockers.append("operator_allowed_conditions_incomplete")
    scope = document.get("scope")
    if not isinstance(scope, Mapping) or scope.get("organism_level_proxy") is not True:
        blockers.append("operator_scope_not_organism_proxy")
    if not isinstance(scope, Mapping) or scope.get("gene_specific_mapping") is not False:
        blockers.append("operator_gene_specific_claim_not_disabled")
    forbidden = document.get("forbidden")
    if not isinstance(forbidden, Mapping) or forbidden.get("calibration") is not True or forbidden.get("holdout_validation") is not True:
        blockers.append("operator_downstream_fitting_not_forbidden")
    return blockers, document


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


def _proxy_burden_label(document: Mapping[str, Any], level: float) -> str:
    burden = document.get("burden")
    curve = burden.get("burden_curve") if isinstance(burden, Mapping) else None
    if isinstance(curve, list):
        for point in curve:
            if isinstance(point, Mapping):
                try:
                    if math.isclose(float(point.get("level")), float(level), rel_tol=0.0, abs_tol=1e-12):
                        return str(point.get("label", "")).strip() or f"level_{level:g}"
                except (TypeError, ValueError):
                    continue
    return f"level_{level:g}"


def _proxy_blank_row(
    *,
    condition_id: str,
    scope: str,
    burden_level: float,
    burden_label: str,
    seed: int,
    steps: int,
    timestep_s: float,
    status: str,
    reason: str,
    operator_applied: bool = False,
    operator_config_sha256: str = "",
) -> dict[str, Any]:
    row = {field: "" for field in PROXY_CSV_FIELDS}
    row.update(
        {
            "condition_id": condition_id,
            "scope": scope,
            "gene_specific_mapping": False,
            "burden_level": burden_level,
            "burden_label": burden_label,
            "seed": seed,
            "run_status": status,
            "skip_reason": reason,
            "step_count": steps,
            "timestep_s": timestep_s,
            "duration_s": steps * timestep_s,
            "operator_applied": operator_applied,
            "operator_config_sha256": operator_config_sha256,
        }
    )
    return row


def _sample_mean_std(rows: Sequence[Mapping[str, Any]], metric: str) -> tuple[float | None, float | None]:
    values = [
        float(row[metric])
        for row in rows
        if row.get("run_status") == "PASS" and isinstance(row.get(metric), (int, float))
    ]
    if not values:
        return None, None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1) if len(values) > 1 else 0.0
    return mean, math.sqrt(variance)


def _write_proxy_report(
    path: Path,
    *,
    status: str,
    runtime_reasons: Sequence[str],
    operator_reason: str,
    summaries: Sequence[Mapping[str, Any]],
) -> None:
    lines = [
        "# Gate 12D — Actual Proxy Disease Multi-Seed Rollouts",
        "",
        f"**Trạng thái:** `{status}`",
        "",
        "## Input status",
        "",
        "- Gate 12C đã mở khóa `alpha_synuclein` và `pink1` ở scope `organism_level_proxy`.",
        "- Gate 11 healthy baseline pass.",
        "- Metric contract pass.",
        "- Audit `READY_FOR_CALIBRATION`.",
        "",
        "## Scope",
        "",
        "Gate 12D chỉ dành cho computational proxy rollout. Không calibration, không holdout validation, không dùng Chen/Pozo để tune, không gene-specific mapping và không biological validation.",
        "",
        "## Runtime",
        "",
        "- Seeds: `0–5`.",
        "- Step count: `5000`.",
        "- Timestep: `0.0001 s`.",
        "- Duration: khoảng `0.5 s`.",
        "- Physics được khai báo giữ nguyên theo Gate 11.",
    ]
    if runtime_reasons:
        lines.extend(["", "## Runtime blocker", "", "- `" + "; ".join(runtime_reasons) + "`"])
    if operator_reason:
        lines.extend(["", "## Proxy execution blocker", "", f"- `{operator_reason}`"])
    lines.extend(
        [
            "",
            "## Conditions",
            "",
            "| Condition | Scope | Planned runs | Successful | Failed | Blocked | Status |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for condition_id in ("alpha_synuclein", "pink1"):
        matching = [item for item in summaries if item.get("condition_id") == condition_id]
        planned = sum(int(item.get("planned_seed_count", 0)) for item in matching)
        successful = sum(int(item.get("n_success", 0)) for item in matching)
        failed = sum(int(item.get("failed_count", 0)) for item in matching)
        blocked = planned - successful - failed
        condition_status = "PASS" if successful == planned else "BLOCKED" if successful == 0 else "PARTIAL"
        lines.append(
            f"| `{condition_id}` | `organism_level_proxy` | {planned} | {successful} | {failed} | {blocked} | `{condition_status}` |"
        )
    lines.extend(["", "## Metric summary", ""])
    if not any(int(item.get("n_success", 0)) > 0 for item in summaries):
        lines.append("Chưa có metric disease thật: tất cả proxy run bị chặn trước simulation. Không tạo metric giả.")
    else:
        lines.extend(
            [
                "| Condition | Burden | Mean planar speed (mm/s) | Distance (mm) | Displacement (mm) | QC pass |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for item in summaries:
            def fmt(metric: str) -> str:
                mean = item.get(f"{metric}_mean")
                std = item.get(f"{metric}_std")
                return f"{mean:.6g} ± {std:.6g}" if isinstance(mean, float) and isinstance(std, float) else "NOT_REPORTED"
            lines.append(
                f"| `{item['condition_id']}` | {item['burden_level']} | {fmt('mean_planar_speed_mm_s')} | {fmt('distance_traveled_mm')} | {fmt('displacement_mm')} | {item.get('qc_pass_count', 0)} |"
            )
    lines.extend(
        [
            "",
            "## Healthy comparison",
            "",
            "Chưa thực hiện so sánh disease với Healthy vì chưa có proxy rollout PASS.",
            "",
            "## Skipped conditions",
            "",
            "- `parkin`: `BLOCKED_IN_GATE_12C`.",
            "- `dj1`: `BLOCKED_IN_GATE_12C`.",
            "- `lrrk2`: `BLOCKED_IN_GATE_12C`.",
            "",
            "## Limitations",
            "",
            "- Alpha-synuclein và PINK1 chỉ là organism-level computational proxy, không phải gene-specific mapping.",
            "- Burden level dimensionless chưa phải calibration value và chưa được dùng để tune theo Chen/Pozo.",
            "- Runtime hiện chưa chứng minh action-level operator kết nối burden proxy vào brain-body runner.",
            "- Đây không phải biological Parkinson validation, clinical prediction, chẩn đoán hoặc drug validation.",
            "",
            "## Final status",
            "",
            f"`{status}`.",
        ]
    )
    _write_text(path, "\n".join(lines) + "\n")


def _integrated_proxy_blank_row(
    *,
    condition_id: str,
    burden_level: float,
    burden_label: str,
    seed: int,
    steps: int,
    timestep_s: float,
    status: str,
    reason: str,
    operator_config_sha256: str,
) -> dict[str, Any]:
    row = {field: "" for field in INTEGRATED_PROXY_CSV_FIELDS}
    row.update(
        {
            "condition_id": condition_id,
            "scope": "organism_level_proxy",
            "gene_specific_mapping": False,
            "burden_level": burden_level,
            "burden_label": burden_label,
            "seed": seed,
            "run_status": status,
            "skip_reason": reason,
            "step_count": steps,
            "timestep_s": timestep_s,
            "duration_s": steps * timestep_s,
            "operator_config_sha256": operator_config_sha256,
        }
    )
    return row


def _external_patch_verified(runner: Path) -> bool:
    """Check the committed integration markers in the external runner."""

    try:
        source = runner.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    required = (
        "--enable-proxy-burden-operator",
        "proxy_operator=proxy_operator",
        "proxy_operator_config=proxy_operator_config",
        "apply_locomotion_action(simulation, fly.name, action)",
    )
    return all(marker in source for marker in required)


def _git_ref(ref: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", ref], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def _run_integrated_proxy_seed(
    *,
    condition_id: str,
    burden_level: float,
    burden_label: str,
    seed: int,
    steps: int,
    timestep_s: float,
    device: str,
    brain_root: Path,
    platform_root: Path,
    brain_python: Path,
    runner: Path,
    operator_config: Path,
    adapter_source: Path,
    temporary_root: Path,
    log_path: Path,
    operator_config_sha256: str,
) -> dict[str, Any]:
    """Run one real FlyGym rollout and retain only its measured row."""

    run_output = (
        temporary_root
        / condition_id
        / f"burden_{burden_level:.2f}"
        / f"seed_{seed:03d}"
    )
    row = _integrated_proxy_blank_row(
        condition_id=condition_id,
        burden_level=burden_level,
        burden_label=burden_label,
        seed=seed,
        steps=steps,
        timestep_s=timestep_s,
        status="FAILED",
        reason="",
        operator_config_sha256=operator_config_sha256,
    )
    command = [
        str(brain_python if brain_python.is_file() else sys.executable),
        str(runner),
        "--brain-root",
        str(brain_root),
        "--condition",
        "healthy",
        "--seed",
        str(seed),
        "--steps",
        str(steps),
        "--device",
        device,
        "--output",
        str(run_output),
        "--enable-proxy-burden-operator",
        "--proxy-operator-config",
        str(operator_config),
        "--proxy-operator-source",
        str(adapter_source),
        "--proxy-burden",
        str(burden_level),
    ]
    environment = os.environ.copy()
    environment.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    try:
        completed = subprocess.run(
            command,
            cwd=platform_root,
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )
        log = (
            f"=== condition={condition_id} burden={burden_level} seed={seed} "
            f"return_code={completed.returncode} ===\n"
            + completed.stdout
            + completed.stderr
        )
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(log)
            if log and not log.endswith("\n"):
                handle.write("\n")
        if completed.returncode != 0:
            row["skip_reason"] = f"external_runner_return_code={completed.returncode}"
            return row

        metrics_path = run_output / "metrics" / "metrics.json"
        rollout_path = run_output / "rollout.npz"
        summary_path = run_output / "brain_body_summary.json"
        required_files = (metrics_path, rollout_path, summary_path)
        missing = [str(path.relative_to(run_output)) for path in required_files if not path.is_file()]
        if missing:
            row["skip_reason"] = "missing_artifact=" + ";".join(missing)
            return row

        metrics, metrics_finite = _read_finite_metrics(metrics_path)
        finite, invalid_arrays = _finite_rollout(rollout_path)
        quality = _rollout_quality(
            rollout_path,
            expected_frames=steps + 1,
            expected_timestep_s=timestep_s,
            metrics=metrics,
        )
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            summary = {}

        operator_enabled = summary.get("proxy_burden_operator_enabled") is True
        operator_applied = summary.get("operator_applied") is True
        before_hash = summary.get("joint_angles_first_before_sha256") or summary.get("joint_angles_before_sha256")
        after_hash = summary.get("joint_angles_first_after_sha256") or summary.get("joint_angles_after_sha256")
        hashes_present = isinstance(before_hash, str) and isinstance(after_hash, str) and bool(before_hash) and bool(after_hash)
        action_changed = bool(hashes_present and before_hash != after_hash)
        adhesion_before_hash = summary.get("adhesion_onoff_first_before_sha256")
        adhesion_after_hash = summary.get("adhesion_onoff_first_after_sha256")
        adhesion_hashes_present = (
            isinstance(adhesion_before_hash, str)
            and isinstance(adhesion_after_hash, str)
            and bool(adhesion_before_hash)
            and bool(adhesion_after_hash)
        )
        adhesion_unchanged = adhesion_hashes_present and adhesion_before_hash == adhesion_after_hash
        if burden_level == 0.0:
            identity_check: Any = "PASS" if hashes_present and before_hash == after_hash else "FAIL"
            positive_action_check: Any = False
        else:
            identity_check = "NOT_APPLICABLE"
            positive_action_check = action_changed

        numeric_qc = finite and metrics_finite
        required_present = all(quality.get(metric) is not None for metric in CANONICAL_METRICS)
        physical_qc = all(
            quality.get(key) == "PASS"
            for key in (
                "timestamp_monotonic",
                "timestep_consistent",
                "locomotion_detected",
                "contact_detected",
                "quaternion_valid",
                "joint_trajectory_changes",
                "action_trajectory_valid",
                "observation_state_valid",
            )
        )
        operator_qc = (
            operator_enabled
            and operator_applied
            and adhesion_unchanged
            and (identity_check == "PASS" if burden_level == 0.0 else positive_action_check)
        )
        if numeric_qc and required_present and physical_qc and operator_qc:
            row.update(
                {
                    "run_status": "PASS",
                    "operator_applied": True,
                    "action_changed_for_positive_burden": positive_action_check,
                    "burden_zero_identity_pass": identity_check,
                    "adhesion_onoff_unchanged": "PASS" if adhesion_unchanged else "FAIL",
                    "mean_planar_speed_mm_s": quality["mean_planar_speed_mm_s"],
                    "distance_traveled_mm": quality["distance_traveled_mm"],
                    "displacement_mm": quality["displacement_mm"],
                    "walking_speed_mm_s_raw": metrics.get("walking_speed_mm_s", ""),
                    "total_distance_mm_raw": metrics.get("total_distance_mm", ""),
                    "thorax_displacement_mm_raw": quality["thorax_displacement_xy_mm"],
                    "no_nan": "PASS",
                    "no_inf": "PASS",
                    "locomotion_detected": quality["locomotion_detected"],
                    "contact_detected": quality["contact_detected"],
                    "timestamp_valid": quality["timestamp_monotonic"],
                    "quaternion_valid": quality["quaternion_valid"],
                    "joint_action_trajectory_valid": quality["action_trajectory_valid"],
                    "metric_contract_status": "PASS",
                }
            )
            return row

        reasons: list[str] = []
        if invalid_arrays:
            reasons.append("invalid_arrays=" + ";".join(invalid_arrays))
        if not numeric_qc:
            reasons.append("numeric_qc_failed")
        if not required_present:
            reasons.append("canonical_metrics_missing")
        if not physical_qc:
            reasons.append("physical_qc_failed")
        if not operator_enabled:
            reasons.append("operator_enabled_flag_missing")
        if not operator_applied:
            reasons.append("operator_applied_flag_missing")
        if not adhesion_unchanged:
            reasons.append("adhesion_onoff_changed_or_hash_missing")
        if burden_level == 0.0 and identity_check != "PASS":
            reasons.append("burden_zero_identity_failed")
        if burden_level > 0.0 and not positive_action_check:
            reasons.append("positive_burden_action_unchanged")
        row["skip_reason"] = ";".join(reasons) or "integrated_rollout_quality_gate_failed"
        return row
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        row["skip_reason"] = f"runner_or_artifact_error={exc}"
        return row
    finally:
        # The large rollout, viewer, and checkpoint artifacts are measured
        # locally and deliberately not retained in the small Gate 12G result.
        shutil.rmtree(run_output, ignore_errors=True)


def _write_integrated_proxy_report(
    path: Path,
    *,
    status: str,
    plan: Mapping[str, Any],
    manifest: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    summary_rows: Sequence[Mapping[str, Any]],
    blockers: Sequence[str],
) -> None:
    healthy_manifest: dict[str, Any] = {}
    source = plan.get("source")
    if isinstance(source, Mapping):
        healthy_path = _resolve(str(source.get("healthy_baseline_manifest", "")))
        if healthy_path.is_file():
            try:
                healthy_manifest = json.loads(healthy_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                healthy_manifest = {}

    def mean_for(metric: str) -> str:
        values = [
            float(item[metric])
            for item in healthy_manifest.get("runs", [])
            if isinstance(item.get(metric), (int, float)) and math.isfinite(float(item[metric]))
        ]
        return f"{sum(values) / len(values):.9g}" if values else "NOT_REPORTED"

    lines = [
        "# Gate 12G - Integrated Proxy Disease Rollout Report",
        "",
        f"**Trạng thái:** `{status}`",
        "",
        "Báo cáo này ghi nhận rollout computational của proxy organism-level qua action hook FlyGym thật.",
        "Không phải biological Parkinson validation, không phải chẩn đoán, dự đoán lâm sàng hoặc đánh giá thuốc.",
        "",
        "## Phạm vi và đầu vào",
        "",
        "- Condition chạy: `alpha_synuclein`, `pink1`.",
        "- Scope: `organism_level_proxy`; không có gene-specific mapping.",
        "- Condition nền của runner: `healthy`; proxy được áp ở action-level hook.",
        "- Calibration, holdout validation, Chen tuning và Pozo tuning: `OFF`.",
        f"- Planned runs: `{manifest.get('planned_runs', {}).get('total', 0)}`.",
        "",
        "## Runtime và operator",
        "",
        f"- CUDA available: `{manifest.get('cuda_available')}`.",
        f"- External patch verified: `{manifest.get('external_patch_verified')}`.",
        f"- Operator config SHA256: `{manifest.get('operator_config_sha256')}`.",
        "- Operator chỉ thay đổi `joint_angles`; `adhesion_onoff` không bị thay đổi.",
        "- burden=0 kiểm tra identity; burden>0 yêu cầu action hash thay đổi.",
        "",
        "## Kết quả theo burden",
        "",
        "| Condition | Burden | PASS | Speed mean (mm/s) | Distance mean (mm) | Displacement mean (mm) | QC |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in summary_rows:
        def fmt(key: str) -> str:
            value = item.get(key, "")
            return f"{float(value):.9g}" if isinstance(value, (int, float)) else (str(value) or "NOT_REPORTED")

        lines.append(
            f"| `{item['condition_id']}` | {item['burden_level']} | {item['n_success']} | "
            f"{fmt('mean_planar_speed_mm_s_mean')} | {fmt('distance_traveled_mm_mean')} | "
            f"{fmt('displacement_mm_mean')} | {item['qc_pass_count']} |"
        )
    lines.extend(
        [
            "",
            "## Healthy baseline tham chiếu",
            "",
            f"- Healthy mean_planar_speed_mm_s: `{mean_for('mean_planar_speed_mm_s')}`.",
            f"- Healthy distance_traveled_mm: `{mean_for('distance_traveled_mm')}`.",
            f"- Healthy displacement_mm: `{mean_for('displacement_mm')}`.",
            "- Các giá trị trên chỉ là tham chiếu computational; không được diễn giải như biological effect.",
            "",
            "## Blockers hoặc lỗi",
            "",
        ]
    )
    if blockers:
        lines.extend(f"- `{reason}`." for reason in blockers)
    else:
        failed = [str(row.get("skip_reason", "")) for row in rows if row.get("run_status") != "PASS" and row.get("skip_reason")]
        lines.extend(f"- `{reason}`." for reason in failed[:20])
        if not failed:
            lines.append("- Không có blocker runtime nào được ghi nhận.")
    lines.extend(
        [
            "",
            "## Giới hạn khoa học",
            "",
            "- Đây là organism-level computational proxy rollout, không phải mapping gene-specific.",
            "- Proxy burden là dimensionless và chưa được dùng để fit Chen hoặc đánh giá Pozo.",
            "- Thời lượng mô phỏng theo Gate 11 khoảng 0.5 giây; không phải diễn tiến bệnh theo thời gian sinh học.",
            "- Không có calibration, holdout validation hoặc biological Parkinson validation trong Gate 12G.",
            "",
            "## Final status",
            "",
            f"`{status}`.",
        ]
    )
    _write_text(path, "\n".join(lines) + "\n")


def _run_integrated_proxy_campaign(args: argparse.Namespace, plan: Mapping[str, Any]) -> int:
    """Run Gate 12G through the real external FlyGym action hook."""

    configured_default = ROOT / "experiments/gate_12_disease_rollouts"
    output_root = _resolve(args.output)
    if output_root == configured_default.resolve():
        output_root = ROOT / "experiments/gate_12g_integrated_proxy_rollouts"
    results_dir = output_root / "results"
    manifests_dir = output_root / "manifests"
    logs_dir = output_root / "logs"
    for directory in (results_dir, manifests_dir, logs_dir):
        directory.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "run.log"
    _write_text(log_path, "# Gate 12G integrated proxy disease rollout log\n")

    source = plan.get("source") if isinstance(plan.get("source"), Mapping) else {}
    external = plan.get("external_runtime") if isinstance(plan.get("external_runtime"), Mapping) else {}
    runtime = plan.get("runtime") if isinstance(plan.get("runtime"), Mapping) else {}
    operator = plan.get("operator") if isinstance(plan.get("operator"), Mapping) else {}
    seeds_block = plan.get("seeds") if isinstance(plan.get("seeds"), Mapping) else {}
    seed_values = [int(value) for value in seeds_block.get("values", [])]
    steps = int(runtime.get("step_count", 0))
    timestep_s = float(runtime.get("timestep_s", 0.0))
    device = str(runtime.get("device", plan.get("device", "cuda")))
    conditions = plan.get("conditions_to_run") if isinstance(plan.get("conditions_to_run"), list) else []
    skipped_conditions = plan.get("conditions_to_skip") if isinstance(plan.get("conditions_to_skip"), list) else []

    default_brain = (ROOT / "external/fly-brain").resolve()
    default_platform = (ROOT.parent / "drosophila-pd-flygym").resolve()
    configured_brain = str(external.get("brain_root", "")).strip()
    configured_platform = str(external.get("path", "")).strip()
    brain_root = _resolve(configured_brain) if configured_brain and _resolve(args.brain_root) == default_brain else _resolve(args.brain_root)
    platform_root = _resolve(configured_platform) if configured_platform and _resolve(args.platform_root) == default_platform else _resolve(args.platform_root)
    configured_python = str(external.get("brain_python", "")).strip()
    if args.brain_python:
        brain_python = _resolve(args.brain_python)
    elif configured_python:
        brain_python = _resolve(configured_python)
    else:
        brain_python = platform_root / ".venv/Scripts/python.exe"

    runner_value = str(external.get("runner_file", "scripts/run_brain_body_rollout.py")).strip()
    runner = (platform_root / runner_value).resolve()
    operator_value = str(source.get("operator_config", "")).strip()
    operator_config = _resolve(operator_value) if operator_value else ROOT / "missing-operator-config.yaml"
    operator_config_sha256 = _sha256(operator_config) if operator_config.is_file() else ""
    adapter_source = ROOT

    blockers: list[str] = []
    if not runner.is_file():
        blockers.append(f"external_runner_missing:{runner}")
    if not _external_patch_verified(runner):
        blockers.append("external_action_hook_patch_not_verified")
    if not operator_config.is_file():
        blockers.append(f"operator_config_missing:{_relative(operator_config)}")
    else:
        operator_blockers, _ = _proxy_operator_config_blockers(operator_config)
        blockers.extend(operator_blockers)
    proxy_plan_value = str(source.get("proxy_ready_plan", "")).strip()
    proxy_plan_path = _resolve(proxy_plan_value) if proxy_plan_value else ROOT / "missing-proxy-plan.yaml"
    if not proxy_plan_path.is_file():
        blockers.append(f"proxy_ready_plan_missing:{_relative(proxy_plan_path)}")
    healthy_manifest_value = str(source.get("healthy_baseline_manifest", "")).strip()
    healthy_manifest_path = _resolve(healthy_manifest_value) if healthy_manifest_value else ROOT / "missing-healthy-manifest.json"
    healthy_manifest: dict[str, Any] = {}
    if not healthy_manifest_path.is_file():
        blockers.append(f"healthy_baseline_manifest_missing:{_relative(healthy_manifest_path)}")
    else:
        try:
            healthy_manifest = json.loads(healthy_manifest_path.read_text(encoding="utf-8"))
            if healthy_manifest.get("status") != "PASS":
                blockers.append("healthy_baseline_manifest_not_pass")
        except (OSError, json.JSONDecodeError):
            blockers.append("healthy_baseline_manifest_invalid")
    runtime_ok, runtime_reasons, cuda_available = _runtime_probe(
        brain_root=brain_root,
        platform_root=platform_root,
        brain_python=brain_python,
        device=device,
    )
    if not runtime_ok:
        blockers.extend(runtime_reasons)
    elif runtime_reasons:
        blockers.extend(runtime_reasons)

    expected_conditions = {"alpha_synuclein", "pink1"}
    configured_conditions = {str(item.get("condition_id", "")).strip() for item in conditions if isinstance(item, Mapping)}
    missing_conditions = sorted(expected_conditions - configured_conditions)
    if missing_conditions:
        blockers.append("configured_conditions_missing=" + ";".join(missing_conditions))
    if not seed_values:
        blockers.append("seed_values_missing")
    if steps <= 0 or timestep_s <= 0:
        blockers.append("invalid_runtime_steps_or_timestep")
    if not isinstance(operator.get("apply_to"), str) or operator.get("apply_to") != "joint_angles":
        blockers.append("operator_apply_to_must_be_joint_angles")
    if operator.get("modifies_adhesion_onoff") is not False:
        blockers.append("operator_must_preserve_adhesion_onoff")

    rows: list[dict[str, Any]] = []
    temporary_parent = ROOT / "temporary"
    temporary_parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix="gate12g-", dir=temporary_parent))
    try:
        for condition in conditions:
            if not isinstance(condition, Mapping):
                continue
            condition_id = str(condition.get("condition_id", "")).strip()
            scope = str(condition.get("scope", "")).strip()
            levels = condition.get("burden_levels") if isinstance(condition.get("burden_levels"), list) else []
            for raw_level in levels:
                level = float(raw_level)
                label = "burden_" + f"{level:.2f}"
                for seed in seed_values:
                    if blockers:
                        row = _integrated_proxy_blank_row(
                            condition_id=condition_id,
                            burden_level=level,
                            burden_label=label,
                            seed=seed,
                            steps=steps,
                            timestep_s=timestep_s,
                            status="BLOCKED",
                            reason="; ".join(blockers),
                            operator_config_sha256=operator_config_sha256,
                        )
                        row["scope"] = scope
                    else:
                        row = _run_integrated_proxy_seed(
                            condition_id=condition_id,
                            burden_level=level,
                            burden_label=label,
                            seed=seed,
                            steps=steps,
                            timestep_s=timestep_s,
                            device=device,
                            brain_root=brain_root,
                            platform_root=platform_root,
                            brain_python=brain_python,
                            runner=runner,
                            operator_config=operator_config,
                            adapter_source=adapter_source,
                            temporary_root=temporary_root,
                            log_path=log_path,
                            operator_config_sha256=operator_config_sha256,
                        )
                        row["scope"] = scope
                    rows.append(row)
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)

    summary_rows: list[dict[str, Any]] = []
    for condition in conditions:
        if not isinstance(condition, Mapping):
            continue
        condition_id = str(condition.get("condition_id", "")).strip()
        scope = str(condition.get("scope", "")).strip()
        levels = condition.get("burden_levels") if isinstance(condition.get("burden_levels"), list) else []
        for raw_level in levels:
            level = float(raw_level)
            matching = [
                row for row in rows
                if row.get("condition_id") == condition_id and math.isclose(float(row.get("burden_level", -1)), level)
            ]
            pass_rows = [row for row in matching if row.get("run_status") == "PASS"]
            summary: dict[str, Any] = {
                "condition_id": condition_id,
                "burden_level": level,
                "burden_label": "burden_" + f"{level:.2f}",
                "n_success": len(pass_rows),
                "operator_applied_count": sum(row.get("operator_applied") is True for row in pass_rows),
                "qc_pass_count": sum(row.get("metric_contract_status") == "PASS" for row in pass_rows),
            }
            for metric in CANONICAL_METRICS:
                mean, std = _sample_mean_std(pass_rows, metric)
                summary[f"{metric}_mean"] = mean if mean is not None else ""
                summary[f"{metric}_std"] = std if std is not None else ""
            summary_rows.append(summary)

    total_planned = len(rows)
    successful = sum(row.get("run_status") == "PASS" for row in rows)
    failed = sum(row.get("run_status") == "FAILED" for row in rows)
    blocked = sum(row.get("run_status") == "BLOCKED" for row in rows)
    if successful == total_planned and total_planned == 60:
        status = "INTEGRATED_PROXY_ROLLOUTS_PASS"
    elif successful:
        status = "INTEGRATED_PROXY_ROLLOUTS_PARTIAL"
    else:
        status = "INTEGRATED_PROXY_ROLLOUTS_BLOCKED"

    metrics_csv = results_dir / "integrated_proxy_disease_metrics.csv"
    with metrics_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INTEGRATED_PROXY_CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary_csv = results_dir / "integrated_proxy_disease_summary.csv"
    with summary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INTEGRATED_PROXY_SUMMARY_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary_rows)
    metrics_payload = {
        "schema_version": "gate-12g-integrated-proxy-disease-metrics-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "simulation_data_fabricated": False,
        "rows": rows,
        "planned_runs": total_planned,
        "successful_runs": successful,
        "failed_runs": failed,
        "blocked_runs": blocked,
        "no_calibration_run": True,
        "no_holdout_validation_run": True,
        "no_gene_specific_mapping": True,
        "metric_contract": list(CANONICAL_METRICS),
        "operator_config_sha256": operator_config_sha256,
        "operator_applied": successful > 0,
        "action_hook_connected": _external_patch_verified(runner),
    }
    metrics_json = results_dir / "integrated_proxy_disease_metrics.json"
    _write_text(metrics_json, json.dumps(metrics_payload, indent=2, ensure_ascii=False) + "\n")

    planned_by_condition = {
        condition_id: sum(
            len(item.get("burden_levels", [])) for item in conditions
            if isinstance(item, Mapping) and item.get("condition_id") == condition_id
        ) * len(seed_values)
        for condition_id in ("alpha_synuclein", "pink1")
    }
    manifest = {
        "schema_version": "gate-12g-integrated-proxy-rollout-manifest-v1",
        "status": status,
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "python_version": platform.python_version(),
        "cuda_available": cuda_available,
        "current_repo_main_commit": _git_ref("main"),
        "external_runtime_path": str(platform_root),
        "external_runtime_runner_sha256": _sha256(runner) if runner.is_file() else "",
        "external_patch_verified": _external_patch_verified(runner),
        "operator_config_sha256": operator_config_sha256,
        "config_sha256": _sha256(_resolve(args.config)),
        "metrics_csv_sha256": _sha256(metrics_csv),
        "metrics_json_sha256": _sha256(metrics_json),
        "summary_csv_sha256": _sha256(summary_csv),
        "planned_runs": {"total": total_planned, **planned_by_condition},
        "successful_runs": successful,
        "blocked_runs": blocked,
        "failed_runs": failed,
        "conditions_run": [str(item.get("condition_id", "")) for item in conditions if isinstance(item, Mapping)],
        "conditions_skipped": [str(item.get("condition_id", "")) for item in skipped_conditions if isinstance(item, Mapping)],
        "no_calibration_run": True,
        "no_holdout_validation_run": True,
        "no_gene_specific_mapping": True,
        "no_biological_validation_claim": True,
        "large_artifacts_committed": False,
        "scientific_boundary": "computational organism-level proxy rollout only; not biological validation",
        "source": {
            "healthy_baseline_manifest": _relative(healthy_manifest_path),
            "proxy_ready_plan": _relative(proxy_plan_path),
            "operator_config": _relative(operator_config),
        },
    }
    manifest_path = manifests_dir / "integrated_proxy_rollout_manifest.json"
    _write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    _write_text(
        log_path,
        log_path.read_text(encoding="utf-8")
        + "\n".join(
            [
                f"status={status}",
                f"planned_runs={total_planned}",
                f"successful_runs={successful}",
                f"failed_runs={failed}",
                f"blocked_runs={blocked}",
                f"blockers={' ; '.join(blockers)}",
                "simulation_data_fabricated=False",
                "no_calibration_run=True",
                "no_holdout_validation_run=True",
                "",
            ]
        ),
    )
    _write_integrated_proxy_report(
        ROOT / "docs/disease_rollouts/gate_12g_integrated_proxy_rollout_report.md",
        status=status,
        plan=plan,
        manifest=manifest,
        rows=rows,
        summary_rows=summary_rows,
        blockers=blockers,
    )
    return 0


def _run_proxy_campaign(args: argparse.Namespace, plan: Mapping[str, Any]) -> int:
    """Run or conservatively block the Gate 12D proxy matrix."""

    configured_default = ROOT / "experiments/gate_12_disease_rollouts"
    output_root = _resolve(args.output)
    if output_root == configured_default.resolve():
        output_root = ROOT / "experiments/gate_12d_proxy_rollouts"
    results_dir = output_root / "results"
    manifests_dir = output_root / "manifests"
    logs_dir = output_root / "logs"
    for directory in (results_dir, manifests_dir, logs_dir):
        directory.mkdir(parents=True, exist_ok=True)
    _write_text(logs_dir / "run.log", "# Gate 12D proxy disease rollout log\n")

    runtime = plan.get("runtime")
    runtime = runtime if isinstance(runtime, Mapping) else {}
    steps = int(runtime.get("step_count", 0))
    timestep_s = float(runtime.get("timestep_s", 0.0))
    seeds = plan.get("seeds")
    seeds = seeds if isinstance(seeds, Mapping) else {}
    seed_values = [int(seed) for seed in seeds.get("values", [])]
    conditions = plan.get("conditions_to_run")
    conditions = conditions if isinstance(conditions, list) else []
    skipped_conditions = plan.get("conditions_to_skip")
    skipped_conditions = skipped_conditions if isinstance(skipped_conditions, list) else []

    healthy_source = plan.get("source_configs", {})
    healthy_source = healthy_source if isinstance(healthy_source, Mapping) else {}
    healthy_manifest_path = _resolve(str(healthy_source.get("healthy_baseline_manifest", "")))
    healthy_manifest: dict[str, Any] = {}
    validation_reasons: list[str] = []
    if not healthy_manifest_path.is_file():
        validation_reasons.append(f"healthy_manifest_missing:{_relative(healthy_manifest_path)}")
    else:
        try:
            healthy_manifest = json.loads(healthy_manifest_path.read_text(encoding="utf-8"))
            if healthy_manifest.get("status") != "PASS":
                validation_reasons.append("healthy_manifest_not_pass")
        except (OSError, json.JSONDecodeError):
            validation_reasons.append("healthy_manifest_invalid")

    brain_root = _resolve(args.brain_root)
    platform_root = _resolve(args.platform_root)
    brain_python = _resolve(args.brain_python) if args.brain_python else platform_root / ".venv/Scripts/python.exe"
    device = str(plan.get("device", "cuda"))
    runtime_ok, runtime_reasons, cuda_available = _runtime_probe(
        brain_root=brain_root,
        platform_root=platform_root,
        brain_python=brain_python,
        device=device,
    )
    runtime_reasons = list(validation_reasons) + list(runtime_reasons)

    operator_config_value = plan.get("operator_config")
    if operator_config_value is None and isinstance(plan.get("operator"), Mapping):
        operator_config_value = plan["operator"].get("config")
    operator_config_path = (
        _resolve(str(operator_config_value)) if operator_config_value else None
    )
    operator_config_sha256 = ""
    operator_config_blockers: list[str] = []
    if operator_config_path is not None:
        operator_config_blockers, _ = _proxy_operator_config_blockers(operator_config_path)
        if operator_config_path.is_file():
            operator_config_sha256 = _sha256(operator_config_path)

    rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    operator_reason = (
        "; ".join(operator_config_blockers)
        if operator_config_blockers
        else "proxy_burden_to_action_operator_not_connected_to_current_brain_body_runner"
    )
    for condition in conditions:
        condition_id = str(condition.get("condition_id", "")).strip()
        scope = str(condition.get("scope", "")).strip()
        condition_path = _resolve(str(condition.get("config", "")))
        blockers, document = _config_blockers(
            condition_id=condition_id,
            config_path=condition_path,
            mapping_scope=scope,
            proxy_mode=True,
        )
        levels = condition.get("burden_levels")
        levels = levels if isinstance(levels, list) else []
        condition_reasons = list(runtime_reasons) + list(blockers)
        if operator_reason:
            condition_reasons.append(operator_reason)
        if not levels:
            condition_reasons.append("burden_levels_missing")
        for raw_level in levels:
            level = float(raw_level)
            label = _proxy_burden_label(document, level)
            run_rows: list[dict[str, Any]] = []
            for seed in seed_values:
                row = _proxy_blank_row(
                    condition_id=condition_id,
                    scope=scope,
                    burden_level=level,
                    burden_label=label,
                    seed=seed,
                    steps=steps,
                    timestep_s=timestep_s,
                    status="BLOCKED" if condition_reasons else "FAILED",
                    reason="; ".join(condition_reasons) or "proxy_execution_not_available",
                    operator_applied=False,
                    operator_config_sha256=operator_config_sha256,
                )
                run_rows.append(row)
            rows.extend(run_rows)
            summary: dict[str, Any] = {
                "condition_id": condition_id,
                "scope": scope,
                "burden_level": level,
                "burden_label": label,
                "planned_seed_count": len(seed_values),
                "n_success": 0,
                "qc_pass_count": 0,
                "failed_count": sum(row["run_status"] == "FAILED" for row in run_rows),
                "status": "BLOCKED" if condition_reasons else "FAILED",
            }
            for metric in CANONICAL_METRICS:
                mean, std = _sample_mean_std(run_rows, metric)
                summary[f"{metric}_mean"] = mean if mean is not None else ""
                summary[f"{metric}_std"] = std if std is not None else ""
            summary_rows.append(summary)

    total_planned = len(rows)
    successful = sum(row["run_status"] == "PASS" for row in rows)
    failed = sum(row["run_status"] == "FAILED" for row in rows)
    blocked = sum(row["run_status"] == "BLOCKED" for row in rows)
    status = "PROXY_ROLLOUTS_PASS" if successful == total_planned and total_planned else (
        "PROXY_ROLLOUTS_PARTIAL" if successful else "PROXY_ROLLOUTS_BLOCKED"
    )

    metrics_csv = results_dir / "proxy_disease_metrics.csv"
    with metrics_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PROXY_CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    summary_csv = results_dir / "proxy_disease_summary.csv"
    with summary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PROXY_SUMMARY_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary_rows)

    metrics_payload = {
        "schema_version": "gate-12d-proxy-disease-metrics-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "simulation_data_fabricated": False,
        "rows": rows,
        "planned_runs": total_planned,
        "successful_runs": successful,
        "failed_runs": failed,
        "blocked_runs": blocked,
        "no_calibration_run": True,
        "no_holdout_validation_run": True,
        "no_gene_specific_mapping": True,
        "metric_contract": list(CANONICAL_METRICS),
        "operator_config_sha256": operator_config_sha256 or None,
        "operator_applied": False,
        "action_hook_connected": False,
    }
    metrics_json = results_dir / "proxy_disease_metrics.json"
    _write_text(metrics_json, json.dumps(metrics_payload, indent=2, ensure_ascii=False) + "\n")

    proxy_plan_path = _resolve(str(healthy_source.get("proxy_ready_plan", "")))
    manifest = {
        "schema_version": "gate-12d-proxy-disease-rollout-manifest-v1",
        "status": status,
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "python_version": platform.python_version(),
        "cuda_available": cuda_available,
        "config_sha256": _sha256(_resolve(args.config)),
        "metrics_csv_sha256": _sha256(metrics_csv),
        "metrics_json_sha256": _sha256(metrics_json),
        "summary_csv_sha256": _sha256(summary_csv),
        "source_healthy_baseline_manifest": _relative(healthy_manifest_path),
        "source_proxy_ready_plan": _relative(proxy_plan_path),
        "conditions_run": [str(item.get("condition_id", "")) for item in conditions],
        "conditions_skipped": [str(item.get("condition_id", "")) for item in skipped_conditions],
        "planned_runs": {
            "total": total_planned,
            "alpha_synuclein": sum(len(condition.get("burden_levels", [])) for condition in conditions if condition.get("condition_id") == "alpha_synuclein") * len(seed_values),
            "pink1": sum(len(condition.get("burden_levels", [])) for condition in conditions if condition.get("condition_id") == "pink1") * len(seed_values),
        },
        "successful_runs": {"total": successful},
        "failed_runs": {"total": failed},
        "blocked_runs": {"total": blocked},
        "no_calibration_run": True,
        "no_holdout_validation_run": True,
        "no_gene_specific_mapping": True,
        "large_artifacts_committed": False,
        "simulation_run": successful > 0,
        "scientific_boundary": "computational proxy rollout only; not biological validation",
        "operator_config_sha256": operator_config_sha256 or None,
        "operator_applied": False,
        "action_hook_connected": False,
        "operator_status": (
            "OPERATOR_IMPLEMENTED_BUT_NOT_CONNECTED"
            if not operator_config_blockers
            else "OPERATOR_CONFIG_INVALID"
        ),
    }
    manifest_path = manifests_dir / "proxy_disease_rollout_manifest.json"
    _write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    _write_text(
        logs_dir / "run.log",
        "\n".join(
            [
                "# Gate 12D proxy disease rollout log",
                f"status={status}",
                f"planned_runs={total_planned}",
                f"successful_runs={successful}",
                f"failed_runs={failed}",
                f"blocked_runs={blocked}",
                f"runtime_reasons={' ; '.join(runtime_reasons)}",
                f"operator_reason={operator_reason}",
                "simulation_data_fabricated=False",
                "no_calibration_run=True",
                "no_holdout_validation_run=True",
                "",
            ]
        ),
    )
    _write_proxy_report(
        ROOT / "docs/disease_rollouts/gate_12d_proxy_disease_rollout_report.md",
        status=status.replace("PROXY_ROLLOUTS", "PROXY_DISEASE_ROLLOUTS"),
        runtime_reasons=runtime_reasons,
        operator_reason=operator_reason,
        summaries=summary_rows,
    )
    return 0


def run_campaign(args: argparse.Namespace) -> int:
    plan_path = _resolve(args.config)
    plan = _load_yaml(plan_path)
    if _is_integrated_proxy_run_config(plan):
        return _run_integrated_proxy_campaign(args, plan)
    if _is_proxy_run_config(plan):
        return _run_proxy_campaign(args, plan)
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
