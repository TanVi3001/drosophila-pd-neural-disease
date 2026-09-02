"""Run the locked Gate 14B Pozo ratio holdout evaluation.

This is the first Gate 14B runner. It reuses the real Gate 12G action-hook
helper, executes only the two locked PINK1 organism-level proxy conditions,
and retains small per-run metric/QC artifacts. It never tunes on Pozo or
converts the Pozo distance endpoint to speed.
"""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import json
import math
import os
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

from scripts.run_disease_conditions_multiseed import (
    INTEGRATED_PROXY_CSV_FIELDS,
    _external_patch_verified,
    _integrated_proxy_blank_row,
    _read_finite_metrics,
    _resolve,
    _run_integrated_proxy_seed,
    _runtime_probe,
    _sample_mean_std,
    _sha256,
)


CONFIG = ROOT / "experiments/gate_14b_pozo_holdout_validation/configs/pozo_holdout_run_config.yaml"
OUTPUT_ROOT = ROOT / "experiments/gate_14b_pozo_holdout_validation"
RESULTS_ROOT = OUTPUT_ROOT / "results"
MANIFEST_ROOT = OUTPUT_ROOT / "manifests"
LOG_ROOT = OUTPUT_ROOT / "logs"
METRICS_CSV = RESULTS_ROOT / "pozo_holdout_metrics.csv"
METRICS_JSON = RESULTS_ROOT / "pozo_holdout_metrics.json"
SUMMARY_CSV = RESULTS_ROOT / "pozo_holdout_summary.csv"
RESULT_SUMMARY = RESULTS_ROOT / "pozo_holdout_result_summary.json"
MANIFEST = MANIFEST_ROOT / "pozo_holdout_manifest.json"
LOG_PATH = LOG_ROOT / "run.log"
REPORT = ROOT / "docs/holdout/gate_14b_pozo_holdout_validation_report.md"

METRICS_FIELDS = INTEGRATED_PROXY_CSV_FIELDS
SUMMARY_FIELDS = (
    "condition_id",
    "burden_level",
    "n_success",
    "n_failed",
    "distance_traveled_mm_mean",
    "distance_traveled_mm_std",
    "mean_planar_speed_mm_s_mean",
    "mean_planar_speed_mm_s_std",
    "displacement_mm_mean",
    "displacement_mm_std",
    "operator_applied_count",
    "qc_pass_count",
)

POZO_TARGET_RATIO = 0.19203837612811836
POZO_DISEASE_DISTANCE = 62.091
POZO_CONTROL_DISTANCE = 323.326
BURDENS = (0.0, 0.5)
SEEDS = (12, 13, 14, 15, 16, 17)
PLANNED_RUNS = len(BURDENS) * len(SEEDS)

RUNTIME_BLOCKED = "POZO_HOLDOUT_RUNTIME_BLOCKED"
RUNTIME_PARTIAL = "POZO_HOLDOUT_RUNTIME_PARTIAL"
RUNTIME_PASS = "POZO_HOLDOUT_RUNTIME_PASS"
SCIENTIFIC_REVIEW = "POZO_RATIO_HOLDOUT_REVIEW_REQUIRED"
SCIENTIFIC_NOT_CONCORDANT = "POZO_RATIO_HOLDOUT_NOT_CONCORDANT"
SCIENTIFIC_CONCORDANCE_REPORTED = "POZO_RATIO_HOLDOUT_CONCORDANCE_REPORTED"


def _load_yaml(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        raise ValueError(f"YAML must be a mapping: {path}")
    return document


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"JSON must be an object: {path}")
    return document


def _number(value: Any) -> float | None:
    try:
        result = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _fmt(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    number = _number(value)
    return f"{number:.12g}" if number is not None else str(value)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def _write_csv(path: Path, fields: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _fmt(row.get(field, "")) for field in fields})


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _git_commit() -> str:
    from subprocess import run

    result = run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def _nested_mapping(document: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = document.get(key)
    return value if isinstance(value, Mapping) else {}


def _verify_protocol(
    plan: Mapping[str, Any],
    *,
    root: Path,
    platform_root: Path,
    brain_root: Path,
    brain_python: Path,
) -> tuple[list[str], dict[str, Any]]:
    blockers: list[str] = []
    source = _nested_mapping(plan, "source")
    scope = _nested_mapping(plan, "holdout_scope")
    lock = _nested_mapping(plan, "locked_parameter")
    design = _nested_mapping(plan, "holdout_design")
    target = _nested_mapping(plan, "pozo_target")
    forbidden = _nested_mapping(plan, "forbidden")

    def source_path(key: str) -> Path:
        value = str(source.get(key, "")).strip()
        return _resolve(value) if value else root / "missing-input"

    gate14a_config = source_path("gate_14a_protocol")
    gate14a_manifest = source_path("gate_14a_manifest")
    gate13b_config = source_path("calibrated_config")
    gate13c_manifest = source_path("gate_13c_manifest")
    pink1_config = source_path("pink1_proxy_config")
    operator_config = source_path("operator_config")
    hook_manifest = source_path("action_hook_integration_manifest")
    inputs = {
        "gate14a_config": gate14a_config,
        "gate14a_manifest": gate14a_manifest,
        "gate13b_config": gate13b_config,
        "gate13c_manifest": gate13c_manifest,
        "pink1_config": pink1_config,
        "operator_config": operator_config,
        "hook_manifest": hook_manifest,
    }
    for label, path in inputs.items():
        if not path.is_file():
            blockers.append(f"{label}_missing:{_relative(path)}")

    gate14a: dict[str, Any] = {}
    gate14a_manifest_doc: dict[str, Any] = {}
    gate13b: dict[str, Any] = {}
    gate13c: dict[str, Any] = {}
    pink1: dict[str, Any] = {}
    operator: dict[str, Any] = {}
    hook: dict[str, Any] = {}
    try:
        if gate14a_config.is_file():
            gate14a = _load_yaml(gate14a_config)
        if gate14a_manifest.is_file():
            gate14a_manifest_doc = _load_json(gate14a_manifest)
        if gate13b_config.is_file():
            gate13b = _load_yaml(gate13b_config)
        if gate13c_manifest.is_file():
            gate13c = _load_json(gate13c_manifest)
        if pink1_config.is_file():
            pink1 = _load_yaml(pink1_config)
        if operator_config.is_file():
            operator = _load_yaml(operator_config)
        if hook_manifest.is_file():
            hook = _load_json(hook_manifest)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        blockers.append(f"input_parse_error:{exc}")

    if gate14a.get("status") != "READY_FOR_GATE_14B_POZO_RATIO_HOLDOUT":
        blockers.append("gate14a_protocol_status_mismatch")
    if gate14a_manifest_doc.get("status") != "READY_FOR_GATE_14B_POZO_RATIO_HOLDOUT":
        blockers.append("gate14a_manifest_status_mismatch")
    if gate14a.get("pozo_target", {}).get("metric") != "distance_traveled_mm":
        blockers.append("pozo_metric_must_be_distance_traveled_mm")
    if gate14a.get("pozo_target", {}).get("not_speed_target") is not True:
        blockers.append("pozo_not_speed_target_lock_missing")
    gate14a_ratio = _number(gate14a.get("pozo_target", {}).get("disease_control_ratio"))
    if gate14a_ratio is None or not math.isclose(gate14a_ratio, POZO_TARGET_RATIO, rel_tol=0.0, abs_tol=1e-12):
        blockers.append("pozo_target_ratio_mismatch")
    if lock.get("parameter_name") != "proxy_burden_level" or _number(lock.get("selected_value")) != 0.5:
        blockers.append("locked_burden_must_be_0.5")
    if lock.get("no_parameter_reselection") is not True or lock.get("no_pozo_tuning") is not True:
        blockers.append("parameter_lock_policy_missing")
    if _number(gate13b.get("selected_parameter", {}).get("selected_value")) != 0.5:
        blockers.append("gate13b_selected_burden_mismatch")
    if gate13c.get("status") != "CHEN_CALIBRATED_CONFIRMATION_PASS":
        blockers.append("gate13c_confirmation_status_mismatch")
    if _number(gate13c.get("calibrated_burden_level")) != 0.5:
        blockers.append("gate13c_calibrated_burden_mismatch")

    pink_target_definition = _nested_mapping(pink1, "target_definition")
    if pink1.get("condition_id") != "pink1":
        blockers.append("pink1_condition_id_mismatch")
    if pink1.get("scope") != "organism_level_proxy":
        blockers.append("pink1_scope_mismatch")
    if pink_target_definition.get("gene_specific_mapping") is not False:
        blockers.append("pink1_gene_specific_mapping_must_be_false")
    if scope.get("condition_id") != "pink1" or scope.get("proxy_scope") != "organism_level_proxy":
        blockers.append("holdout_scope_mismatch")
    if scope.get("gene_specific_mapping") is not False or scope.get("biological_validation_claim") is not False:
        blockers.append("scientific_boundary_lock_missing")

    if operator.get("status") != "OPERATOR_IMPLEMENTED":
        blockers.append("operator_status_mismatch")
    operator_body = _nested_mapping(operator, "operator")
    if operator_body.get("type") != "amplitude_attenuation":
        blockers.append("operator_type_mismatch")
    if operator.get("scope", {}).get("gene_specific_mapping") is not False:
        blockers.append("operator_gene_specific_claim_not_disabled")
    if hook.get("status") != "CONNECTED_TO_EXTERNAL_RUNTIME":
        blockers.append("action_hook_integration_not_connected")
    if hook.get("operator_applies_to") != "joint_angles":
        blockers.append("operator_must_apply_to_joint_angles")
    if hook.get("modifies_adhesion_onoff") is not False:
        blockers.append("adhesion_onoff_must_be_unchanged")
    if hook.get("no_full_rollout_run") is not True or hook.get("no_calibration_run") is not True:
        blockers.append("hook_manifest_boundary_mismatch")

    if design.get("control_burden_level") != 0.0 or design.get("holdout_burden_level") != 0.5:
        blockers.append("holdout_burden_design_mismatch")
    if tuple(int(value) for value in design.get("seeds", [])) != SEEDS:
        blockers.append("holdout_seed_policy_mismatch")
    if int(design.get("planned_runs", 0)) != PLANNED_RUNS:
        blockers.append("planned_run_count_mismatch")
    if _number(target.get("primary_metric")) is not None:
        blockers.append("pozo_primary_metric_invalid")
    if target.get("primary_metric") != "distance_traveled_mm":
        blockers.append("pozo_primary_metric_mismatch")
    configured_ratio = _number(target.get("target_ratio"))
    if configured_ratio is None or not math.isclose(configured_ratio, POZO_TARGET_RATIO, rel_tol=0.0, abs_tol=1e-12):
        blockers.append("pozo_config_ratio_mismatch")
    for forbidden_key in (
        "parameter_reselection",
        "pozo_tuning",
        "calibration_run",
        "use_pozo_for_calibration",
        "use_pink1_for_calibration",
        "distance_to_speed_conversion",
        "spread_to_se_conversion",
        "biological_validation_claim",
    ):
        if forbidden.get(forbidden_key) is not True:
            blockers.append(f"forbidden_policy_missing:{forbidden_key}")

    runner_value = str(_nested_mapping(plan, "external_runtime").get("runner_file", "scripts/run_brain_body_rollout.py"))
    runner = (platform_root / runner_value).resolve()
    if not runner.is_file():
        blockers.append(f"external_runner_missing:{runner}")
    elif not _external_patch_verified(runner):
        blockers.append("external_action_hook_patch_not_verified")
    compile_status = _compile_external_runner(runner, brain_python)
    if compile_status != "PASS":
        blockers.append(f"external_runner_compile={compile_status}")

    runtime_ok, runtime_reasons, cuda_available = _runtime_probe(
        brain_root=brain_root,
        platform_root=platform_root,
        brain_python=brain_python,
        device="cuda",
    )
    if not runtime_ok:
        blockers.extend(runtime_reasons)
    return blockers, {
        "inputs": inputs,
        "runner": runner,
        "runtime_ok": runtime_ok,
        "runtime_reasons": runtime_reasons,
        "cuda_available": cuda_available,
        "operator_config": operator_config,
        "operator_config_sha256": _sha256(operator_config) if operator_config.is_file() else "",
    }


def _compile_external_runner(runner: Path, brain_python: Path) -> str:
    if not runner.is_file() or not brain_python.is_file():
        return "NOT_AVAILABLE"
    import subprocess

    result = subprocess.run(
        [str(brain_python), "-m", "py_compile", str(runner)],
        capture_output=True,
        text=True,
        check=False,
    )
    return "PASS" if result.returncode == 0 else f"FAIL:{result.returncode}"


def _blank_rows(reason: str, *, steps: int, timestep_s: float, operator_hash: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for burden in BURDENS:
        for seed in SEEDS:
            rows.append(
                _integrated_proxy_blank_row(
                    condition_id="pink1",
                    burden_level=burden,
                    burden_label=f"burden_{burden:.2f}",
                    seed=seed,
                    steps=steps,
                    timestep_s=timestep_s,
                    status="BLOCKED",
                    reason=reason,
                    operator_config_sha256=operator_hash,
                )
            )
    return rows


def _summary_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for burden in BURDENS:
        selected = [
            row
            for row in rows
            if row.get("condition_id") == "pink1"
            and math.isclose(float(row.get("burden_level", -1)), burden, abs_tol=1e-12)
        ]
        passed = [row for row in selected if row.get("run_status") == "PASS"]
        item: dict[str, Any] = {
            "condition_id": "pink1",
            "burden_level": burden,
            "n_success": len(passed),
            "n_failed": len(selected) - len(passed),
            "operator_applied_count": sum(row.get("operator_applied") is True for row in passed),
            "qc_pass_count": sum(row.get("metric_contract_status") == "PASS" for row in passed),
        }
        for metric in ("distance_traveled_mm", "mean_planar_speed_mm_s", "displacement_mm"):
            mean, std = _sample_mean_std(passed, metric)
            item[f"{metric}_mean"] = mean if mean is not None else ""
            item[f"{metric}_std"] = std if std is not None else ""
        summaries.append(item)
    return summaries


def _mean(summary: Mapping[str, Any], field: str) -> float | None:
    return _number(summary.get(field))


def _scientific_status(execution_status: str, summaries: Sequence[Mapping[str, Any]]) -> tuple[str, float | None, bool | None]:
    if execution_status != RUNTIME_PASS:
        return SCIENTIFIC_REVIEW, None, None
    control = next(item for item in summaries if item["burden_level"] == 0.0)
    holdout = next(item for item in summaries if item["burden_level"] == 0.5)
    control_mean = _mean(control, "distance_traveled_mm_mean")
    holdout_mean = _mean(holdout, "distance_traveled_mm_mean")
    if control_mean is None or holdout_mean is None or control_mean == 0.0:
        return SCIENTIFIC_REVIEW, None, None
    ratio = holdout_mean / control_mean
    directionality = holdout_mean < control_mean
    return (SCIENTIFIC_CONCORDANCE_REPORTED if directionality else SCIENTIFIC_NOT_CONCORDANT), ratio, directionality


def _write_report(
    path: Path,
    *,
    execution_status: str,
    scientific_status: str,
    result: Mapping[str, Any],
    blockers: Sequence[str],
) -> None:
    def display(value: Any) -> str:
        if value is None:
            return "NOT_REPORTED"
        if isinstance(value, float):
            return f"{value:.12g}"
        return str(value)

    blocker_lines = "\n".join(f"- `{item}`" for item in blockers) if blockers else "- Không có runtime blocker."
    qc_lines = "- Chưa có QC PASS vì rollout chưa hoàn tất." if result.get("successful_runs", 0) == 0 else (
        f"- Successful runs: `{result.get('successful_runs')}`; QC pass count được ghi trong summary CSV."
    )
    text = f"""# Gate 14B - Pozo Ratio Holdout Validation Run

## Mục tiêu

Gate 14B chạy holdout evaluation cho Pozo 2022 bằng PINK1 organism-level
computational proxy, với parameter đã khóa từ Chen calibration. Đây là
computational proxy holdout check, không phải biological Parkinson validation.

## Input và lock

- Gate 13B: `CHEN_RATIO_CALIBRATION_PASS`.
- Gate 13C: `CHEN_CALIBRATED_CONFIRMATION_PASS`.
- Gate 14A: `READY_FOR_GATE_14B_POZO_RATIO_HOLDOUT`.
- Locked burden: `proxy_burden_level = 0.5`.
- Không chọn lại parameter và không dùng Pozo để tune.

## Pozo holdout target

- Model: `Pink1B9`.
- Metric: `distance_traveled_mm`.
- Disease value: `62.091 mm`.
- Control value: `323.326 mm`.
- Target ratio: `0.19203837612811836`.
- Spread: `61.288`, giữ nguyên paper-reported, không đổi thành SD/SE.
- Sample size: `n=21`.
- Allocation: holdout only.
- Đây không phải speed target; không chuyển distance thành speed.

## Run design

- Condition duy nhất: `pink1`.
- Scope: `organism_level_proxy`.
- Control burden: `0.0`.
- Holdout burden: `0.5`.
- Seeds: `12, 13, 14, 15, 16, 17`.
- Planned runs: `12`.
- Runtime cố định: `5000` steps, timestep `0.0001 s`, duration `0.5 s`.

## Results

- Execution status: `{execution_status}`.
- Scientific status: `{scientific_status}`.
- Successful runs: `{display(result.get('successful_runs'))}`.
- Failed runs: `{display(result.get('failed_runs'))}`.
- Blocked runs: `{display(result.get('blocked_runs'))}`.
- Mean distance control: `{display(result.get('mean_distance_control'))}` mm.
- Mean distance holdout: `{display(result.get('mean_distance_holdout'))}` mm.
- Simulated distance ratio: `{display(result.get('simulated_distance_ratio'))}`.
- Ratio error: `{display(result.get('ratio_error'))}`.
- Directionality (`burden_0.5 < burden_0.0`): `{display(result.get('directionality_pass'))}`.
- Absolute distance error: `{display(result.get('absolute_distance_error_reference_only'))}` mm, reference-only.

## Runtime và QC

{qc_lines}
{blocker_lines}

Mỗi run PASS phải có metrics finite, timestamp/quaternion/action/observation QC,
locomotion và contact hợp lệ, cùng operator checks theo burden. Artifact lớn
như NPZ, video và viewer bundle không được lưu trong Gate 14B repository output.

## Diễn giải giới hạn

`POZO_HOLDOUT_RUNTIME_PASS` chỉ cho biết 12 rollout computational đã chạy và
qua QC. Ratio được báo cáo theo protocol; không có numerical tolerance được
đăng ký trước nên không tự đặt ngưỡng hậu nghiệm. Scientific status không phải
là biological validation. Kết quả không chứng minh gene-specific PINK1 mapping,
cơ chế Parkinson, chẩn đoán lâm sàng, drug efficacy hoặc thay thế thí nghiệm
wet-lab. Absolute distance chỉ là reference-only vì scale/thời lượng assay và
runtime không được giả định tương đương trực tiếp.

## Cấm trong Gate 14B

- Không calibration.
- Không parameter search hoặc Pozo tuning.
- Không chạy alpha-synuclein, Parkin, DJ-1 hoặc LRRK2.
- Không đổi distance thành speed hoặc spread thành SD/SE.

## Final status

- Execution: `{execution_status}`.
- Scientific: `{scientific_status}`.
"""
    _write_text(path, text)


def run_validation(
    *,
    config_path: Path = CONFIG,
    output_root: Path = OUTPUT_ROOT,
    brain_root: Path | None = None,
    platform_root: Path | None = None,
    brain_python: Path | None = None,
) -> dict[str, Any]:
    plan = _load_yaml(config_path)
    external = _nested_mapping(plan, "external_runtime")
    runtime = _nested_mapping(plan, "runtime")
    root = config_path.resolve().parents[2]
    if root != ROOT:
        root = ROOT
    selected_platform = platform_root.resolve() if platform_root else _resolve(str(external.get("path", "../drosophila-pd-flygym")))
    selected_brain = brain_root.resolve() if brain_root else _resolve(str(external.get("brain_root", "external/fly-brain")))
    selected_python = brain_python.resolve() if brain_python else _resolve(str(external.get("brain_python", "")))
    steps = int(runtime.get("step_count", 5000))
    timestep_s = float(runtime.get("timestep_s", 0.0001))
    output_root = output_root.resolve()
    results_root = output_root / "results"
    manifests_root = output_root / "manifests"
    logs_root = output_root / "logs"
    for directory in (results_root, manifests_root, logs_root):
        directory.mkdir(parents=True, exist_ok=True)
    metrics_csv = results_root / "pozo_holdout_metrics.csv"
    metrics_json = results_root / "pozo_holdout_metrics.json"
    summary_csv = results_root / "pozo_holdout_summary.csv"
    result_summary_path = results_root / "pozo_holdout_result_summary.json"
    manifest_path = manifests_root / "pozo_holdout_manifest.json"
    log_path = logs_root / "run.log"
    _write_text(log_path, "# Gate 14B Pozo ratio holdout validation log\n")

    blockers, runtime_context = _verify_protocol(
        plan,
        root=ROOT,
        platform_root=selected_platform,
        brain_root=selected_brain,
        brain_python=selected_python,
    )
    operator_hash = str(runtime_context.get("operator_config_sha256", ""))
    rows: list[dict[str, Any]] = []
    if blockers:
        rows = _blank_rows("; ".join(blockers), steps=steps, timestep_s=timestep_s, operator_hash=operator_hash)
    else:
        temporary_parent = ROOT / "temporary"
        temporary_parent.mkdir(parents=True, exist_ok=True)
        temporary_root = Path(tempfile.mkdtemp(prefix="gate14b-", dir=temporary_parent))
        try:
            runner = runtime_context["runner"]
            operator_config = runtime_context["operator_config"]
            for burden in BURDENS:
                for seed in SEEDS:
                    try:
                        row = _run_integrated_proxy_seed(
                            condition_id="pink1",
                            burden_level=burden,
                            burden_label=f"burden_{burden:.2f}",
                            seed=seed,
                            steps=steps,
                            timestep_s=timestep_s,
                            device="cuda",
                            brain_root=selected_brain,
                            platform_root=selected_platform,
                            brain_python=selected_python,
                            runner=runner,
                            operator_config=operator_config,
                            adapter_source=ROOT,
                            temporary_root=temporary_root,
                            log_path=log_path,
                            operator_config_sha256=operator_hash,
                        )
                    except Exception as exc:  # preserve failed-run evidence without fabricating metrics
                        row = _integrated_proxy_blank_row(
                            condition_id="pink1",
                            burden_level=burden,
                            burden_label=f"burden_{burden:.2f}",
                            seed=seed,
                            steps=steps,
                            timestep_s=timestep_s,
                            status="FAILED",
                            reason=f"runner_exception={type(exc).__name__}:{exc}",
                            operator_config_sha256=operator_hash,
                        )
                    rows.append(row)
        finally:
            shutil.rmtree(temporary_root, ignore_errors=True)

    summaries = _summary_rows(rows)
    successful = sum(row.get("run_status") == "PASS" for row in rows)
    failed = sum(row.get("run_status") == "FAILED" for row in rows)
    blocked = sum(row.get("run_status") == "BLOCKED" for row in rows)
    if blockers or blocked == PLANNED_RUNS:
        execution_status = RUNTIME_BLOCKED
    elif successful == PLANNED_RUNS:
        execution_status = RUNTIME_PASS
    else:
        execution_status = RUNTIME_PARTIAL
    scientific_status, simulated_ratio, directionality_pass = _scientific_status(execution_status, summaries)
    control_summary = next(item for item in summaries if item["burden_level"] == 0.0)
    holdout_summary = next(item for item in summaries if item["burden_level"] == 0.5)
    mean_control = _mean(control_summary, "distance_traveled_mm_mean")
    mean_holdout = _mean(holdout_summary, "distance_traveled_mm_mean")
    ratio_error = abs(simulated_ratio - POZO_TARGET_RATIO) if simulated_ratio is not None else None
    absolute_error = abs(mean_holdout - POZO_DISEASE_DISTANCE) if mean_holdout is not None else None
    result = {
        "schema_version": "gate-14b-pozo-holdout-result-summary-v1",
        "execution_status": execution_status,
        "scientific_status": scientific_status,
        "condition_id": "pink1",
        "proxy_scope": "organism_level_proxy",
        "gene_specific_mapping": False,
        "biological_validation_claim": False,
        "locked_parameter": {"proxy_burden_level": 0.5},
        "planned_runs": PLANNED_RUNS,
        "successful_runs": successful,
        "failed_runs": failed,
        "blocked_runs": blocked,
        "control_burden_level": 0.0,
        "holdout_burden_level": 0.5,
        "mean_distance_control": mean_control,
        "mean_distance_holdout": mean_holdout,
        "simulated_distance_ratio": simulated_ratio,
        "pozo_target_ratio": POZO_TARGET_RATIO,
        "ratio_error": ratio_error,
        "directionality_pass": directionality_pass,
        "absolute_distance_reference_only": {
            "pozo_disease_value_mm": POZO_DISEASE_DISTANCE,
            "simulated_holdout_distance_mm": mean_holdout,
            "absolute_distance_error_reference_only": absolute_error,
        },
        "no_parameter_reselection": True,
        "no_pozo_tuning": True,
        "no_calibration_run": True,
        "no_distance_to_speed_conversion": True,
        "no_spread_to_se_conversion": True,
        "no_biological_validation_claim": True,
        "simulation_data_fabricated": False,
        "notes": [
            "Pozo is used only as holdout.",
            "Absolute distance is reference-only because simulation runtime and assay scale are not directly identical.",
            "Scientific interpretation must use the locked protocol and cannot add a post-hoc ratio tolerance.",
        ],
    }
    _write_csv(metrics_csv, METRICS_FIELDS, rows)
    _write_csv(summary_csv, SUMMARY_FIELDS, summaries)
    _write_text(metrics_json, json.dumps({
        "schema_version": "gate-14b-pozo-holdout-metrics-v1",
        "execution_status": execution_status,
        "scientific_status": scientific_status,
        "simulation_data_fabricated": False,
        "rows": rows,
        "summary": summaries,
    }, indent=2, ensure_ascii=False) + "\n")
    _write_text(result_summary_path, json.dumps(result, indent=2, ensure_ascii=False) + "\n")

    source_paths = [
        plan.get("source", {}).get(key, "")
        for key in (
            "gate_14a_protocol",
            "gate_14a_manifest",
            "calibrated_config",
            "gate_13c_manifest",
            "pink1_proxy_config",
        )
    ]
    source_records = []
    for source_value in source_paths:
        source_path = _resolve(str(source_value))
        source_records.append({
            "path": _relative(source_path),
            "present": source_path.is_file(),
            "sha256": _sha256(source_path) if source_path.is_file() else "",
        })
    manifest = {
        "schema_version": "gate-14b-pozo-holdout-manifest-v1",
        "execution_status": execution_status,
        "scientific_status": scientific_status,
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "python_version": platform.python_version(),
        "cuda_available": runtime_context.get("cuda_available", False),
        "external_runtime_path": _relative(selected_platform),
        "external_runtime_runner_sha256": _sha256(runtime_context["runner"]) if runtime_context["runner"].is_file() else "",
        "external_patch_verified": _external_patch_verified(runtime_context["runner"]),
        "source_files": [record["path"] for record in source_records],
        "source_file_records": source_records,
        "config_sha256": _sha256(config_path),
        "metrics_csv_sha256": _sha256(metrics_csv),
        "metrics_json_sha256": _sha256(metrics_json),
        "summary_csv_sha256": _sha256(summary_csv),
        "result_summary_sha256": _sha256(result_summary_path),
        "planned_runs": PLANNED_RUNS,
        "successful_runs": successful,
        "failed_runs": failed,
        "blocked_runs": blocked,
        "condition_id": "pink1",
        "control_burden_level": 0.0,
        "holdout_burden_level": 0.5,
        "holdout_seeds": list(SEEDS),
        "pozo_target": {
            "metric": "distance_traveled_mm",
            "disease_value_mm": POZO_DISEASE_DISTANCE,
            "control_value_mm": POZO_CONTROL_DISTANCE,
            "target_ratio": POZO_TARGET_RATIO,
            "spread_reported": 61.288,
            "spread_policy": "kept_as_reported_not_converted_to_sd_or_se",
            "n": 21,
            "allocation": "holdout",
            "not_speed_target": True,
        },
        "holdout_result": {
            "mean_distance_control": mean_control,
            "mean_distance_holdout": mean_holdout,
            "simulated_distance_ratio": simulated_ratio,
            "ratio_error": ratio_error,
            "directionality_pass": directionality_pass,
        },
        "locked_parameter": {"proxy_burden_level": 0.5},
        "no_parameter_reselection": True,
        "no_pozo_tuning": True,
        "no_calibration_run": True,
        "no_distance_to_speed_conversion": True,
        "no_spread_to_se_conversion": True,
        "no_gene_specific_mapping": True,
        "no_biological_validation_claim": True,
        "large_artifacts_committed": False,
        "runtime_blockers": blockers,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    _write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    _write_report(
        REPORT,
        execution_status=execution_status,
        scientific_status=scientific_status,
        result=result,
        blockers=blockers,
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--brain-root", type=Path, default=None)
    parser.add_argument("--platform-root", type=Path, default=None)
    parser.add_argument("--brain-python", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = run_validation(
            config_path=args.config.resolve(),
            output_root=args.output.resolve(),
            brain_root=args.brain_root,
            platform_root=args.platform_root,
            brain_python=args.brain_python,
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Execution status: {manifest['execution_status']}")
    print(f"Scientific status: {manifest['scientific_status']}")
    print(f"Successful runs: {manifest['successful_runs']}/{manifest['planned_runs']}")
    print(f"Manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
