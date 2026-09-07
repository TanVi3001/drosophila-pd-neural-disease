"""Verify the locked Pozo holdout result as the Gate 23 package.

Gate 23 is intentionally an analysis/provenance gate. The actual 12-run
runtime was executed by Gate 14B. This script verifies those immutable
artifacts, checks the Chen calibration lock and Gate 14C claim lock, and
reports PASS/MISMATCH/INCONCLUSIVE without starting FlyGym or changing any
raw result.
"""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "experiments/gate_23_pozo_holdout_validation/configs/pozo_holdout_validation.yaml"
DEFAULT_OUTPUT = ROOT / "experiments/gate_23_pozo_holdout_validation/manifests"
DEFAULT_REPORT = ROOT / "docs/holdout/gate_23_pozo_holdout_validation_report.md"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return value


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"CSV is empty: {path}")
    return rows


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _finite(value: Any, name: str) -> float:
    number = float(value)
    _require(math.isfinite(number), f"{name} must be finite")
    return number


def _verify_config(config: Mapping[str, Any]) -> None:
    _require(config.get("condition_id") == "pink1", "Gate 23 condition must be pink1")
    _require(config.get("proxy_scope") == "organism_level_proxy", "Gate 23 scope must be organism-level proxy")
    _require(config.get("gene_specific_mapping") is False, "Gate 23 cannot claim gene-specific mapping")
    locked = config.get("locked_calibration", {})
    _require(float(locked.get("selected_value")) == 0.5, "Gate 23 calibration burden must remain 0.5")
    _require(locked.get("no_parameter_reselection") is True, "Gate 23 must prohibit reselection")
    _require(locked.get("no_pozo_tuning") is True, "Gate 23 must prohibit Pozo tuning")
    holdout = config.get("holdout", {})
    _require(holdout.get("metric") == "distance_traveled_mm", "Pozo endpoint must remain distance_traveled_mm")
    _require(holdout.get("not_speed_target") is True, "Pozo target must not be treated as speed")
    _require(holdout.get("no_distance_to_speed_conversion") is True, "Distance-to-speed conversion must be forbidden")
    _require(holdout.get("allocation") == "holdout", "Pozo target must remain holdout")
    comparison = config.get("comparison", {})
    _require(comparison.get("no_post_hoc_tolerance") is True, "Post-hoc tolerance must be forbidden")
    execution = config.get("execution_policy", {})
    for field in ("run_new_simulation", "run_gpu", "run_calibration", "run_holdout_validation", "modify_gate14b_raw_results"):
        _require(execution.get(field) is False, f"Gate 23 execution policy must keep {field}=false")


def _verify_sources(config: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, str]], dict[str, str]]:
    source_paths = {key: ROOT / value for key, value in config["sources"].items()}
    for key, path in source_paths.items():
        _require(path.is_file(), f"Missing source {key}: {_relative(path)}")
    protocol = _yaml(source_paths["gate14a_protocol"])
    calibrated = _yaml(source_paths["gate13b_calibrated_config"])
    confirmation = _json(source_paths["gate13c_confirmation_manifest"])
    gate14b_manifest = _json(source_paths["gate14b_manifest"])
    gate14b_summary = _json(source_paths["gate14b_summary"])
    adjudication = _json(source_paths["gate14c_adjudication"])
    metrics = _csv(source_paths["gate14b_metrics"])

    _require(protocol.get("status") == "READY_FOR_GATE_14B_POZO_RATIO_HOLDOUT", "Gate 14A protocol is not locked")
    _require(protocol.get("locked_calibration", {}).get("selected_value") == 0.5, "Gate 14A lock is not 0.5")
    _require(protocol.get("locked_calibration", {}).get("no_pozo_tuning") is True, "Gate 14A permits Pozo tuning")
    _require(calibrated.get("status") == "CHEN_RATIO_CALIBRATED", "Gate 13B calibration lock is not active")
    _require(calibrated.get("selected_parameter", {}).get("selected_value") == 0.5, "Gate 13B selected burden is not 0.5")
    _require(confirmation.get("status") == "CHEN_CALIBRATED_CONFIRMATION_PASS", "Gate 13C confirmation is not PASS")
    _require(confirmation.get("no_pozo") is True and confirmation.get("no_pink1") is True, "Gate 13C used holdout data")

    _require(gate14b_manifest.get("execution_status") == "POZO_HOLDOUT_RUNTIME_PASS", "Gate 14B runtime is not PASS")
    _require(gate14b_manifest.get("planned_runs") == 12, "Gate 14B planned run count changed")
    _require(gate14b_manifest.get("successful_runs") == 12, "Gate 14B successful run count changed")
    _require(gate14b_manifest.get("locked_parameter", {}).get("proxy_burden_level") == 0.5, "Gate 14B parameter is not 0.5")
    for field in ("no_parameter_reselection", "no_pozo_tuning", "no_calibration_run", "no_distance_to_speed_conversion", "no_gene_specific_mapping", "no_biological_validation_claim"):
        _require(gate14b_manifest.get(field) is True, f"Gate 14B flag {field} is not true")

    hash_map = {
        "config_sha256": ROOT / "experiments/gate_14b_pozo_holdout_validation/configs/pozo_holdout_run_config.yaml",
        "metrics_csv_sha256": source_paths["gate14b_metrics"],
        "metrics_json_sha256": ROOT / "experiments/gate_14b_pozo_holdout_validation/results/pozo_holdout_metrics.json",
        "summary_csv_sha256": ROOT / "experiments/gate_14b_pozo_holdout_validation/results/pozo_holdout_summary.csv",
        "result_summary_sha256": source_paths["gate14b_summary"],
    }
    for field, path in hash_map.items():
        _require(path.is_file(), f"Missing hashed Gate 14B input: {_relative(path)}")
        _require(_sha256(path) == gate14b_manifest.get(field), f"Gate 14B checksum mismatch: {field}")

    _require(adjudication.get("final_adjudication_status") == "DIRECTIONAL_CONCORDANCE_WITH_QUANTITATIVE_MISMATCH", "Gate 14C claim lock does not report the locked mismatch")
    _require(adjudication.get("claim_lock", {}).get("quantitative_pozo_validation") is False, "Gate 14C permits quantitative Pozo claim")
    _require(adjudication.get("locked_parameter", {}).get("no_pozo_tuning") is True, "Gate 14C permits Pozo tuning")
    return gate14b_summary, gate14b_manifest, confirmation, metrics, {key: _relative(path) for key, path in source_paths.items()}


def _summarize(gate14b_summary: Mapping[str, Any], metrics: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    result = (
        gate14b_summary.get("holdout_result")
        or gate14b_summary.get("pozo_holdout_result")
        or gate14b_summary
    )
    _require(isinstance(result, Mapping), "Gate 14B summary has no holdout result")
    qc_fields = ("run_status", "no_nan", "no_inf", "locomotion_detected", "contact_detected", "timestamp_valid", "quaternion_valid", "joint_action_trajectory_valid", "metric_contract_status")
    qc_pass = sum(all(row.get(field) == "PASS" for field in qc_fields) for row in metrics)
    control = _finite(result["mean_distance_control"], "mean_distance_control")
    holdout = _finite(result["mean_distance_holdout"], "mean_distance_holdout")
    simulated_ratio = _finite(result["simulated_distance_ratio"], "simulated_distance_ratio")
    target_ratio = _finite(result["pozo_target_ratio"], "pozo_target_ratio")
    directionality = holdout < control
    quantitative = bool(result.get("quantitative_ratio_match", False))
    runtime_status = "PASS" if len(metrics) == 12 and qc_pass == 12 else "INCONCLUSIVE"
    if runtime_status != "PASS":
        interpretation = "INCONCLUSIVE"
    elif not quantitative:
        interpretation = "MISMATCH"
    else:
        interpretation = "PASS"
    return {
        "gate": "Gate 23",
        "status": f"POZO_HOLDOUT_{interpretation}",
        "runtime_status": runtime_status,
        "holdout_interpretation": interpretation,
        "condition_id": "pink1",
        "proxy_scope": "organism_level_proxy",
        "gene_specific_mapping": False,
        "locked_burden_level": 0.5,
        "planned_runs": 12,
        "successful_runs": 12 if runtime_status == "PASS" else None,
        "qc_pass_runs": qc_pass,
        "metric": "distance_traveled_mm",
        "mean_distance_control_mm": control,
        "mean_distance_holdout_mm": holdout,
        "simulated_distance_ratio": simulated_ratio,
        "pozo_target_ratio": target_ratio,
        "ratio_error": _finite(result["ratio_error"], "ratio_error"),
        "directionality_pass": directionality,
        "quantitative_ratio_match": quantitative,
        "spread_reported": 61.288,
        "spread_policy": "kept_as_reported_not_converted_to_sd_or_se",
        "sample_size": 21,
        "absolute_distance_role": "reference_only",
        "no_distance_to_speed_conversion": True,
        "no_pozo_tuning": True,
        "no_parameter_reselection": True,
        "no_calibration_run": True,
        "no_new_simulation_run": True,
        "gpu_run": False,
        "data_fabricated": False,
        "biological_validation_claim": False,
        "claim_boundary": "Directional computational proxy comparison only; quantitative Pozo ratio mismatch remains.",
    }


def _write_csv(path: Path, summary: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["metric", "control_mean_mm", "holdout_mean_mm", "simulated_ratio", "pozo_target_ratio", "ratio_error", "directionality", "quantitative_interpretation"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerow({
            "metric": summary["metric"],
            "control_mean_mm": summary["mean_distance_control_mm"],
            "holdout_mean_mm": summary["mean_distance_holdout_mm"],
            "simulated_ratio": summary["simulated_distance_ratio"],
            "pozo_target_ratio": summary["pozo_target_ratio"],
            "ratio_error": summary["ratio_error"],
            "directionality": "PASS" if summary["directionality_pass"] else "FAIL",
            "quantitative_interpretation": summary["holdout_interpretation"],
        })


def _write_report(path: Path, summary: Mapping[str, Any], sources: Mapping[str, str]) -> None:
    lines = [
        "# Gate 23: Pozo holdout validation",
        "",
        f"**Trạng thái runtime:** `{summary['runtime_status']}`  ",
        f"**Diễn giải holdout:** `{summary['holdout_interpretation']}`",
        "",
        "Gate 23 xác minh lại holdout Pozo trên artifact Gate 14B đã được khóa. Gate này không chạy GPU, không chạy simulation mới, không calibration, không tuning và không sửa raw metrics.",
        "",
        "## Thiết kế khóa",
        "",
        "- Condition: `pink1`, phạm vi `organism_level_proxy`.",
        "- Tham số calibration từ Chen đã khóa: `proxy_burden_level = 0.5`.",
        "- Endpoint duy nhất: `distance_traveled_mm`.",
        "- Không chuyển distance thành speed.",
        "- Pozo chỉ là holdout, không dùng để chọn lại tham số.",
        "- Đơn vị tính toán: rollout seed; runtime Gate 14B có 12/12 run thành công.",
        "",
        "## Kết quả",
        "",
        f"- Khoảng cách control trung bình: `{summary['mean_distance_control_mm']:.8f} mm`.",
        f"- Khoảng cách holdout trung bình: `{summary['mean_distance_holdout_mm']:.8f} mm`.",
        f"- Tỷ lệ mô phỏng: `{summary['simulated_distance_ratio']:.12f}`.",
        f"- Tỷ lệ Pozo: `{summary['pozo_target_ratio']:.12f}`.",
        f"- Sai số tỷ lệ: `{summary['ratio_error']:.12f}`.",
        f"- Directionality: `{'PASS' if summary['directionality_pass'] else 'FAIL'}`.",
        f"- Quantitative interpretation: `{summary['holdout_interpretation']}`.",
        "",
        "Kết quả đúng là **directionality concordance nhưng quantitative mismatch**. Khoảng cách giảm khi burden 0.5 được áp dụng, nhưng tỷ lệ `0.9470` khác xa tỷ lệ Pozo `0.1920`; không được gọi là quantitative holdout validation.",
        "",
        "## Giới hạn claim",
        "",
        "Kết quả chỉ hỗ trợ so sánh computational locomotion proxy ở mức organism-level. Không phải biological Parkinson validation, không phải gene-specific PINK1 validation, không phải clinical validation và không phải drug validation.",
        "",
        "## Provenance",
        "",
    ]
    lines.extend(f"- `{key}`: `{value}`" for key, value in sources.items())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(*, config_path: Path = DEFAULT_CONFIG, output_dir: Path = DEFAULT_OUTPUT, report_path: Path = DEFAULT_REPORT) -> dict[str, Any]:
    config = _yaml(config_path)
    _verify_config(config)
    summary_source, manifest_source, confirmation, metrics, source_paths = _verify_sources(config)
    summary = _summarize(summary_source, metrics)
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "gate23_pozo_holdout_result.csv"
    summary_path = output_dir / "gate23_pozo_holdout_summary.json"
    manifest_path = output_dir / "gate23_pozo_holdout_manifest.json"
    _write_csv(result_path, summary)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "gate-23-pozo-holdout-validation-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        **summary,
        "config": _relative(config_path),
        "config_sha256": _sha256(config_path),
        "source_artifacts": {key: {"path": value, "sha256": _sha256(ROOT / value)} for key, value in source_paths.items()},
        "gate14b_execution_status": manifest_source.get("execution_status"),
        "gate13c_confirmation_status": confirmation.get("status"),
        "artifacts": {
            "result_csv": _relative(result_path),
            "summary_json": _relative(summary_path),
            "report": _relative(report_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_report(report_path, summary, source_paths)
    checksum_paths = [result_path, summary_path, manifest_path, report_path]
    checksum_path = output_dir / "gate23_checksums.sha256"
    checksum_path.write_text("".join(f"{_sha256(path)}  {_relative(path)}\n" for path in checksum_paths), encoding="utf-8")
    return {**manifest, "checksum_file": _relative(checksum_path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(config_path=args.config, output_dir=args.output, report_path=args.report)
    print(json.dumps({key: result[key] for key in ("status", "runtime_status", "holdout_interpretation", "planned_runs", "successful_runs", "directionality_pass", "quantitative_ratio_match")}, indent=2))
    print(f"Manifest: {args.output / 'gate23_pozo_holdout_manifest.json'}")
    print(f"Report: {args.report}")
    return 0 if result["runtime_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
