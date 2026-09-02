"""Run the Gate 13C locked alpha-synuclein confirmation rerun.

This script executes only real external FlyGym rollouts through the already
integrated action hook.  Large per-rollout artifacts are temporary; only the
small measured tables, manifest, log, and report are retained.
"""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import sys
import tempfile
from typing import Any, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_disease_conditions_multiseed import (  # noqa: E402
    _external_patch_verified,
    _proxy_operator_config_blockers,
    _relative,
    _resolve,
    _run_integrated_proxy_seed,
    _runtime_probe,
    _sample_mean_std,
)


DEFAULT_CONFIG = ROOT / "experiments/gate_13c_calibrated_confirmation/configs/calibrated_confirmation_run_config.yaml"
DEFAULT_OUTPUT = ROOT / "experiments/gate_13c_calibrated_confirmation"
METRICS_FIELDS = (
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
SUMMARY_FIELDS = (
    "condition_id",
    "burden_level",
    "n_success",
    "n_failed",
    "mean_planar_speed_mm_s_mean",
    "mean_planar_speed_mm_s_std",
    "distance_traveled_mm_mean",
    "distance_traveled_mm_std",
    "displacement_mm_mean",
    "displacement_mm_std",
    "operator_applied_count",
    "qc_pass_count",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        raise ValueError(f"YAML must contain a mapping: {path}")
    return document


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"JSON must contain an object: {path}")
    return document


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def _float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _require(mapping: Mapping[str, Any], path: str) -> Any:
    value: Any = mapping
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            raise ValueError(f"Missing required config field: {path}")
        value = value[part]
    return value


def _validate_locked_inputs(plan: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path, Path, Path, Path, Path, Path]:
    source = _require(plan, "source")
    condition = _require(plan, "condition")
    locked = _require(plan, "locked_parameter")
    if not isinstance(source, Mapping) or not isinstance(condition, Mapping) or not isinstance(locked, Mapping):
        raise ValueError("source, condition, and locked_parameter must be mappings")
    if str(plan.get("status", "")) != "RUN_CALIBRATED_CONFIRMATION_RERUN":
        raise ValueError("invalid Gate 13C run status")
    if str(condition.get("condition_id")) != "alpha_synuclein":
        raise ValueError("Gate 13C allows alpha_synuclein only")
    if str(condition.get("scope")) != "organism_level_proxy":
        raise ValueError("Gate 13C requires organism_level_proxy scope")
    if condition.get("gene_specific_mapping") is not False:
        raise ValueError("Gate 13C forbids gene-specific mapping")
    if str(locked.get("parameter_name")) != "proxy_burden_level" or locked.get("locked") is not True:
        raise ValueError("proxy_burden_level must be explicitly locked")
    selected = _float(locked.get("selected_value"))
    if selected is None or not math.isclose(selected, 0.5, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("Gate 13C requires the Gate 13B selected burden 0.5")

    paths = tuple(_resolve(str(source[key])) for key in (
        "calibrated_config",
        "gate_13b_summary",
        "gate_12g_summary",
        "operator_config",
        "action_hook_integration_manifest",
        "gate_13b_manifest",
    ))
    if len(paths) != 6:  # pragma: no cover - defensive type narrowing
        raise AssertionError("source path count changed")
    return dict(source), dict(condition), dict(locked), *paths


def _validate_source_files(
    plan: Mapping[str, Any],
) -> tuple[list[str], dict[str, Any], dict[str, Any], dict[str, Any], Path, Path, Path, Path, Path, Path]:
    source, condition, locked, calibrated_config_path, summary_path, gate12g_path, operator_path, hook_path, manifest_path = _validate_locked_inputs(plan)
    blockers: list[str] = []
    paths = {
        "gate_13b_calibrated_config": calibrated_config_path,
        "gate_13b_summary": summary_path,
        "gate_12g_summary": gate12g_path,
        "operator_config": operator_path,
        "action_hook_integration_manifest": hook_path,
        "gate_13b_manifest": manifest_path,
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    blockers.extend(f"source_file_missing:{name}" for name in missing)
    if blockers:
        return blockers, {}, {}, {}, calibrated_config_path, summary_path, gate12g_path, operator_path, hook_path, manifest_path

    calibrated = _load_yaml(calibrated_config_path)
    summary = _load_json(summary_path)
    manifest = _load_json(manifest_path)
    hook = _load_json(hook_path)
    if summary.get("status") != "CHEN_RATIO_CALIBRATION_PASS":
        blockers.append("gate_13b_summary_not_pass")
    if not math.isclose(float(summary.get("selected_burden_level", -1)), 0.5, rel_tol=0.0, abs_tol=1e-12):
        blockers.append("gate_13b_selected_burden_is_not_0.5")
    if calibrated.get("condition_id") != "alpha_synuclein":
        blockers.append("gate_13b_condition_not_alpha_synuclein")
    if calibrated.get("scope") != "organism_level_proxy":
        blockers.append("gate_13b_scope_not_organism_level_proxy")
    if calibrated.get("gene_specific_mapping") is not False:
        blockers.append("gate_13b_gene_specific_mapping_not_false")
    if hook.get("status") != "CONNECTED_TO_EXTERNAL_RUNTIME" or hook.get("patch_applied_to_external_runtime") is not True:
        blockers.append("action_hook_integration_not_connected")
    if hook.get("operator_applies_to") != "joint_angles":
        blockers.append("action_hook_operator_target_not_joint_angles")
    if hook.get("modifies_adhesion_onoff") is not False:
        blockers.append("action_hook_must_preserve_adhesion_onoff")
    operator_blockers, _ = _proxy_operator_config_blockers(operator_path)
    blockers.extend(operator_blockers)
    return blockers, calibrated, summary, manifest, calibrated_config_path, summary_path, manifest_path, hook_path, gate12g_path, operator_path


def _blank_row(*, burden: float, seed: int, steps: int, timestep: float, reason: str, config_hash: str) -> dict[str, Any]:
    row = {field: "" for field in METRICS_FIELDS}
    row.update({
        "condition_id": "alpha_synuclein",
        "scope": "organism_level_proxy",
        "gene_specific_mapping": False,
        "burden_level": burden,
        "burden_label": f"burden_{burden:.2f}",
        "seed": seed,
        "run_status": "BLOCKED",
        "skip_reason": reason,
        "step_count": steps,
        "timestep_s": timestep,
        "duration_s": steps * timestep,
        "operator_config_sha256": config_hash,
    })
    return row


def _read_gate12g_summary(path: Path) -> None:
    """Require the locked source summary to be readable without reusing it as data."""

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("Gate 12G summary is empty")


def _ratio(rows: Sequence[Mapping[str, Any]], burden: float) -> float | None:
    values = [
        _float(row.get("mean_planar_speed_mm_s"))
        for row in rows
        if row.get("run_status") == "PASS" and math.isclose(float(row.get("burden_level", -1)), burden, abs_tol=1e-12)
    ]
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def _write_csv(path: Path, fields: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def _read_existing_rows(path: Path) -> list[dict[str, Any]]:
    boolean_fields = {
        "gene_specific_mapping",
        "operator_applied",
        "action_changed_for_positive_burden",
    }
    numeric_fields = {
        "burden_level",
        "seed",
        "step_count",
        "timestep_s",
        "duration_s",
        "mean_planar_speed_mm_s",
        "distance_traveled_mm",
        "displacement_mm",
    }
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("existing Gate 13C metrics CSV is empty")
    for row in rows:
        for field in boolean_fields:
            if row.get(field) == "True":
                row[field] = True
            elif row.get(field) == "False":
                row[field] = False
        for field in numeric_fields:
            if row.get(field, "") != "":
                value = _float(row[field])
                if value is None:
                    raise ValueError(f"existing metrics field is not finite: {field}")
                row[field] = int(value) if field in {"seed", "step_count"} else value
    return rows


def _report(
    path: Path,
    *,
    status: str,
    rows: Sequence[Mapping[str, Any]],
    summary_rows: Sequence[Mapping[str, Any]],
    blockers: Sequence[str],
    ratio: float | None,
    target: float,
    gate13b_ratio: float | None,
) -> None:
    passed = sum(row.get("run_status") == "PASS" for row in rows)
    lines = [
        "# Gate 13C — Calibrated confirmation rerun",
        "",
        f"**Trạng thái:** `{status}`",
        "",
        "## Phạm vi",
        "",
        "Đây là confirmation rerun tính toán locomotion cho proxy alpha-synuclein ở scope organism-level. Gate này giữ khóa `proxy_burden_level=0.5` từ Gate 13B và dùng control burden `0.0` để kiểm tra lại bằng seed độc lập `6–11`.",
        "",
        "Không chọn lại tham số, không tối ưu liên tục, không dùng Pozo/PINK1/holdout và không thực hiện gene-specific mapping. Đây không phải biological Parkinson validation, chẩn đoán, dự đoán lâm sàng, drug validation hay thay thế thí nghiệm wet-lab.",
        "",
        "## Thiết kế thực thi",
        "",
        "- Condition duy nhất: `alpha_synuclein`.",
        "- Burden: `0.0` và khóa `0.5`.",
        "- Seed: `6, 7, 8, 9, 10, 11` cho mỗi mức, tổng `12` rollout.",
        "- Runtime: `5000` bước, timestep `0.0001 s`, thời lượng `0.5 s`, giữ nguyên physics/timestep/duration của Gate 11/12G.",
        f"- Rollout PASS: `{passed}/{len(rows)}`.",
        "",
        "## Kết quả đo",
        "",
        "| Burden | Số run PASS | Mean planar speed (mm/s) | Ratio so với control | Sai số so với Chen | Độ trôi so với Gate 13B |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in summary_rows:
        def fmt(key: str) -> str:
            value = item.get(key)
            return f"{value:.8g}" if isinstance(value, (int, float)) else "NOT_REPORTED"
        is_calibrated = math.isclose(float(item["burden_level"]), 0.5, abs_tol=1e-12)
        ratio_value = ratio if is_calibrated else 1.0 if ratio is not None else None
        error_value = abs(ratio - target) if is_calibrated and ratio is not None else None
        drift_value = abs(ratio - gate13b_ratio) if is_calibrated and ratio is not None and gate13b_ratio is not None else None
        lines.append(
            f"| {item['burden_level']} | {item['n_success']} | {fmt('mean_planar_speed_mm_s_mean')} ± {fmt('mean_planar_speed_mm_s_std')} | {ratio_value:.8g} | {error_value:.8g} | {drift_value:.8g} |"
            if ratio_value is not None and error_value is not None and drift_value is not None
            else f"| {item['burden_level']} | {item['n_success']} | {fmt('mean_planar_speed_mm_s_mean')} ± {fmt('mean_planar_speed_mm_s_std')} | NOT_REPORTED | NOT_REPORTED | NOT_REPORTED |"
        )
    lines.extend([
        "",
        "## Ratio đối chiếu",
        "",
        f"- Chen reference ratio: `{target:.15g}`.",
        f"- Confirmation ratio (burden 0.5 / burden 0.0): `{ratio:.15g}`." if ratio is not None else "- Confirmation ratio: `NOT_REPORTED` vì thiếu nhóm PASS.",
        f"- Gate 13B selected ratio: `{gate13b_ratio:.15g}`." if gate13b_ratio is not None else "- Gate 13B selected ratio: `NOT_REPORTED`.",
        "- CI95 của Chen được giữ nguyên là CI95; không chuyển thành SE.",
        "",
        "## Blocker hoặc lỗi",
        "",
    ])
    lines.extend(f"- `{item}`" for item in blockers) if blockers else lines.append("- Không có blocker được ghi nhận.")
    lines.extend([
        "",
        "## Artifact",
        "",
        "Chỉ giữ metrics CSV/JSON, summary CSV, manifest, log và report. Rollout NPZ, video, viewer bundle và checkpoint không được commit; nếu được tạo trong quá trình chạy, chúng nằm trong thư mục tạm và bị xóa sau khi đo.",
        "",
        "## Kết luận phạm vi",
        "",
        f"Gate 13C chỉ có thể được gọi là `{status}` theo QC rollout và operator. Nó không xác nhận cơ chế bệnh học, không phải biological Parkinson validation và không được dùng để suy ra hiệu quả thuốc.",
    ])
    lines.extend([
        "",
        "## Trạng thái chuyển tiếp",
        "",
        "`READY_FOR_GATE_14A_POZO_HOLDOUT_PROTOCOL` chỉ là trạng thái sẵn sàng lập protocol holdout sau confirmation; Gate 13C chưa chạy holdout và không sử dụng Pozo.",
    ])
    _write_text(path, "\n".join(lines) + "\n")


def run_campaign(config_path: Path, output_root: Path, *, brain_root_override: Path | None = None, platform_root_override: Path | None = None, brain_python_override: Path | None = None, device_override: str | None = None, reuse_existing: bool = False) -> int:
    plan = _load_yaml(config_path)
    output_root.mkdir(parents=True, exist_ok=True)
    results_dir = output_root / "results"
    manifests_dir = output_root / "manifests"
    logs_dir = output_root / "logs"
    for directory in (results_dir, manifests_dir, logs_dir):
        directory.mkdir(parents=True, exist_ok=True)
    metrics_csv = results_dir / "calibrated_confirmation_metrics.csv"
    metrics_json = results_dir / "calibrated_confirmation_metrics.json"
    summary_csv = results_dir / "calibrated_confirmation_summary.csv"
    manifest_path = manifests_dir / "calibrated_confirmation_manifest.json"
    log_path = logs_dir / "run.log"
    _write_text(log_path, "# Gate 13C calibrated confirmation rerun\n")

    blockers: list[str] = []
    try:
        source, condition, locked, calibrated_path, gate13b_summary_path, gate12g_path, operator_path, hook_path, gate13b_manifest_path = _validate_locked_inputs(plan)
        source_blockers, calibrated, gate13b_summary, gate13b_manifest, *_ = _validate_source_files(plan)
        blockers.extend(source_blockers)
        _read_gate12g_summary(gate12g_path)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        blockers.append(f"input_validation_error:{exc}")
        source = plan.get("source", {}) if isinstance(plan.get("source"), Mapping) else {}
        condition = plan.get("condition", {}) if isinstance(plan.get("condition"), Mapping) else {}
        locked = plan.get("locked_parameter", {}) if isinstance(plan.get("locked_parameter"), Mapping) else {}
        calibrated_path = gate13b_summary_path = gate13b_manifest_path = hook_path = gate12g_path = operator_path = ROOT / "missing"
        calibrated = gate13b_summary = gate13b_manifest = {}

    external = plan.get("external_runtime", {}) if isinstance(plan.get("external_runtime"), Mapping) else {}
    runtime = plan.get("runtime", {}) if isinstance(plan.get("runtime"), Mapping) else {}
    default_platform = (ROOT.parent / "drosophila-pd-flygym").resolve()
    default_brain = (ROOT.parent / "external/fly-brain-audit").resolve()
    platform_root = platform_root_override.resolve() if platform_root_override else _resolve(str(external.get("path", default_platform)))
    brain_root = brain_root_override.resolve() if brain_root_override else _resolve(str(external.get("brain_root", default_brain)))
    brain_python = brain_python_override.resolve() if brain_python_override else _resolve(str(external.get("brain_python", platform_root / ".venv/Scripts/python.exe")))
    runner = (platform_root / str(external.get("runner_file", "scripts/run_brain_body_rollout.py"))).resolve()
    device = device_override or str(runtime.get("device", "cuda"))
    operator_hash = _sha256(operator_path) if operator_path.is_file() else ""
    if not runner.is_file():
        blockers.append(f"external_runner_missing:{runner}")
    if not _external_patch_verified(runner):
        blockers.append("external_action_hook_patch_not_verified")
    runtime_ok, runtime_reasons, cuda_available = _runtime_probe(
        brain_root=brain_root, platform_root=platform_root, brain_python=brain_python, device=device
    )
    if not runtime_ok:
        blockers.extend(runtime_reasons)
    steps = int(runtime.get("step_count", 0))
    timestep = float(runtime.get("timestep_s", 0.0))
    confirmation_design = plan.get("confirmation_design", {}) if isinstance(plan.get("confirmation_design"), Mapping) else {}
    seed_values = [int(value) for value in confirmation_design.get("seeds", [])]
    burdens = [float(confirmation_design.get("control_burden_level", 0.0)), float(locked.get("selected_value", 0.5))]
    if seed_values != [6, 7, 8, 9, 10, 11]:
        blockers.append("confirmation_seeds_do_not_match_locked_design")
    if burdens != [0.0, 0.5]:
        blockers.append("confirmation_burdens_do_not_match_locked_design")
    if int(confirmation_design.get("planned_runs", 0)) != 12:
        blockers.append("planned_run_count_is_not_12")

    rows: list[dict[str, Any]] = []
    if reuse_existing and not blockers:
        rows = _read_existing_rows(metrics_csv)
    else:
        temporary_parent = ROOT / "temporary"
        temporary_parent.mkdir(parents=True, exist_ok=True)
        temporary_root = Path(tempfile.mkdtemp(prefix="gate13c-", dir=str(temporary_parent)))
        try:
            if blockers:
                for burden in burdens:
                    for seed in seed_values:
                        rows.append(_blank_row(burden=burden, seed=seed, steps=steps, timestep=timestep, reason="; ".join(blockers), config_hash=operator_hash))
            else:
                for burden in burdens:
                    for seed in seed_values:
                        row = _run_integrated_proxy_seed(
                            condition_id="alpha_synuclein",
                            burden_level=burden,
                            burden_label=f"burden_{burden:.2f}",
                            seed=seed,
                            steps=steps,
                            timestep_s=timestep,
                            device=device,
                            brain_root=brain_root,
                            platform_root=platform_root,
                            brain_python=brain_python,
                            runner=runner,
                            operator_config=operator_path,
                            adapter_source=ROOT,
                            temporary_root=temporary_root,
                            log_path=log_path,
                            operator_config_sha256=operator_hash,
                        )
                        row["scope"] = "organism_level_proxy"
                        row["gene_specific_mapping"] = False
                        rows.append(row)
        finally:
            shutil.rmtree(temporary_root, ignore_errors=True)

    successful = sum(row.get("run_status") == "PASS" for row in rows)
    failed = sum(row.get("run_status") == "FAILED" for row in rows)
    blocked = sum(row.get("run_status") == "BLOCKED" for row in rows)
    status = "CHEN_CALIBRATED_CONFIRMATION_PASS" if successful == 12 else "CHEN_CALIBRATED_CONFIRMATION_PARTIAL" if successful else "CHEN_CALIBRATED_CONFIRMATION_BLOCKED"
    target = float(_require(plan, "chen_reference.ratio_target"))
    gate13b_ratio = _float(gate13b_summary.get("selected_simulated_ratio"))
    control_mean = _ratio(rows, 0.0)
    confirmation_mean = _ratio(rows, 0.5)
    confirmation_ratio = confirmation_mean / control_mean if confirmation_mean is not None and control_mean not in (None, 0.0) else None

    summary_rows: list[dict[str, Any]] = []
    for burden in burdens:
        matching = [row for row in rows if math.isclose(float(row.get("burden_level", -1)), burden, abs_tol=1e-12)]
        pass_rows = [row for row in matching if row.get("run_status") == "PASS"]
        mean, std = _sample_mean_std(pass_rows, "mean_planar_speed_mm_s")
        distance_mean, distance_std = _sample_mean_std(pass_rows, "distance_traveled_mm")
        displacement_mean, displacement_std = _sample_mean_std(pass_rows, "displacement_mm")
        summary_rows.append({
            "condition_id": "alpha_synuclein",
            "burden_level": burden,
            "n_success": len(pass_rows),
            "n_failed": len(matching) - len(pass_rows),
            "mean_planar_speed_mm_s_mean": mean if mean is not None else "",
            "mean_planar_speed_mm_s_std": std if std is not None else "",
            "distance_traveled_mm_mean": distance_mean if distance_mean is not None else "",
            "distance_traveled_mm_std": distance_std if distance_std is not None else "",
            "displacement_mm_mean": displacement_mean if displacement_mean is not None else "",
            "displacement_mm_std": displacement_std if displacement_std is not None else "",
            "operator_applied_count": sum(row.get("operator_applied") is True for row in pass_rows),
            "qc_pass_count": sum(row.get("metric_contract_status") == "PASS" for row in pass_rows),
        })

    _write_csv(metrics_csv, METRICS_FIELDS, rows)
    _write_csv(summary_csv, SUMMARY_FIELDS, summary_rows)
    metrics_payload = {
        "schema_version": "gate-13c-calibrated-confirmation-metrics-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "simulation_data_fabricated": False,
        "condition_id": "alpha_synuclein",
        "scope": "organism_level_proxy",
        "gene_specific_mapping": False,
        "locked_parameter": {"parameter_name": "proxy_burden_level", "selected_value": 0.5, "selection_source": "Gate 13B"},
        "burdens": burdens,
        "seeds": seed_values,
        "planned_runs": 12,
        "successful_runs": successful,
        "failed_runs": failed,
        "blocked_runs": blocked,
        "rows": rows,
        "summary": summary_rows,
        "confirmation_ratio": confirmation_ratio,
        "chen_ratio_target": target,
        "absolute_ratio_error_vs_chen": abs(confirmation_ratio - target) if confirmation_ratio is not None else None,
        "gate_13b_selected_ratio": gate13b_ratio,
        "absolute_ratio_drift_vs_gate_13b": abs(confirmation_ratio - gate13b_ratio) if confirmation_ratio is not None and gate13b_ratio is not None else None,
        "operator_config_sha256": operator_hash,
        "action_hook_connected": not any(item == "external_action_hook_patch_not_verified" for item in blockers),
        "no_reselection": True,
        "no_parameter_reselection": True,
        "no_continuous_optimization": True,
        "no_pozo": True,
        "no_pink1": True,
        "no_pozo_used": True,
        "no_pink1_used": True,
        "no_holdout_validation": True,
        "no_holdout_validation_run": True,
        "no_ci95_to_se": True,
        "ci95_to_se_conversion": False,
        "distance_to_speed_conversion": False,
        "no_gene_specific_mapping": True,
        "no_biological_validation_claim": True,
        "biological_validation_claim": False,
    }
    _write_text(metrics_json, json.dumps(metrics_payload, indent=2, ensure_ascii=False) + "\n")
    manifest = {
        "schema_version": "gate-13c-calibrated-confirmation-manifest-v1",
        "status": status,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cuda_available": cuda_available,
        "config_sha256": _sha256(config_path),
        "metrics_csv_sha256": _sha256(metrics_csv),
        "metrics_json_sha256": _sha256(metrics_json),
        "summary_csv_sha256": _sha256(summary_csv),
        "operator_config_sha256": operator_hash,
        "external_runtime_path": str(platform_root),
        "external_runner_sha256": _sha256(runner) if runner.is_file() else "",
        "external_patch_verified": _external_patch_verified(runner),
        "external_action_hook_patch_verified": _external_patch_verified(runner),
        "action_hook_integration_manifest_sha256": _sha256(hook_path) if hook_path.is_file() else "",
        "gate_13b_summary_sha256": _sha256(gate13b_summary_path) if gate13b_summary_path.is_file() else "",
        "gate_13b_manifest_sha256": _sha256(gate13b_manifest_path) if gate13b_manifest_path.is_file() else "",
        "planned_runs": 12,
        "successful_runs": successful,
        "failed_runs": failed,
        "blocked_runs": blocked,
        "condition_id": "alpha_synuclein",
        "control_burden_level": 0.0,
        "calibrated_burden_level": 0.5,
        "confirmation_seeds": seed_values,
        "conditions": ["alpha_synuclein"],
        "burdens": burdens,
        "seeds": seed_values,
        "confirmation_ratio": confirmation_ratio,
        "chen_ratio_target": target,
        "gate13b_selected_ratio": gate13b_ratio,
        "gate_13b_selected_ratio": gate13b_ratio,
        "confirmation_ratio_error": abs(confirmation_ratio - target) if confirmation_ratio is not None else None,
        "drift_from_gate13b": abs(confirmation_ratio - gate13b_ratio) if confirmation_ratio is not None and gate13b_ratio is not None else None,
        "no_reselection": True,
        "no_parameter_reselection": True,
        "no_continuous_optimization": True,
        "no_pozo": True,
        "no_pink1": True,
        "no_pozo_used": True,
        "no_pink1_used": True,
        "no_holdout_validation": True,
        "no_holdout_validation_run": True,
        "no_ci95_to_se": True,
        "no_distance_to_speed": True,
        "no_gene_specific_mapping": True,
        "no_biological_validation_claim": True,
        "biological_validation_claim": False,
        "large_artifacts_committed": False,
        "scientific_boundary": "Computational locomotion confirmation only; not biological Parkinson validation.",
        "source_calibrated_config": _relative(calibrated_path),
        "source_gate_13b_summary": _relative(gate13b_summary_path),
        "source_gate_12g_summary": _relative(gate12g_path),
        "source": {key: _relative(path) for key, path in {
            "config": config_path,
            "source_calibrated_config": calibrated_path,
            "source_gate_13b_summary": gate13b_summary_path,
            "source_gate_12g_summary": gate12g_path,
            "operator_config": operator_path,
            "action_hook_integration_manifest": hook_path,
        }.items()},
    }
    _write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    _report(
        ROOT / "docs/calibration/gate_13c_calibrated_confirmation_rerun_report.md",
        status=status,
        rows=rows,
        summary_rows=summary_rows,
        blockers=blockers,
        ratio=confirmation_ratio,
        target=target,
        gate13b_ratio=gate13b_ratio,
    )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"status": status, "planned_runs": 12, "successful_runs": successful, "failed_runs": failed, "blocked_runs": blocked, "simulation_data_fabricated": False}, ensure_ascii=False) + "\n")
    return 0 if status == "CHEN_CALIBRATED_CONFIRMATION_PASS" else 1


def _git_commit() -> str:
    import subprocess

    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--brain-root", type=Path, default=None)
    parser.add_argument("--platform-root", type=Path, default=None)
    parser.add_argument("--brain-python", type=Path, default=None)
    parser.add_argument("--device", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run_campaign(
            _resolve(args.config),
            _resolve(args.output),
            brain_root_override=args.brain_root,
            platform_root_override=args.platform_root,
            brain_python_override=args.brain_python,
            device_override=args.device,
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
