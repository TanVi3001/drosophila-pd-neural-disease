"""Compare Gate 21 Parkin proxy rollouts with the matched Healthy baseline.

This is a deterministic, analysis-only gate. It consumes compact committed
metric tables and manifests; it never starts a simulator, GPU process,
calibration, or holdout validation.
"""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "experiments/gate_22_parkin_healthy_comparison/configs/parkin_healthy_comparison.yaml"
DEFAULT_OUTPUT = ROOT / "experiments/gate_22_parkin_healthy_comparison/manifests"
DEFAULT_REPORT = ROOT / "docs/disease_rollouts/gate_22_parkin_healthy_comparison_report.md"
EXPECTED_METRIC_FIELDS = (
    "mean_planar_speed_mm_s",
    "distance_traveled_mm",
    "displacement_mm",
    "walking_speed_mm_s",
    "com_velocity_mean_mm_s",
    "heading_variance_rad2",
    "body_orientation_variance_rad2",
    "stride_frequency_hz",
    "step_frequency_hz",
    "trajectory_curvature_mean_rad_per_mm",
    "walking_speed_max_mm_s",
)
QC_FIELDS = (
    "status",
    "quality_status",
    "required_metric_status",
    "no_nan_inf",
    "locomotion_detected",
    "contact_detected",
    "joint_trajectory_changes",
    "action_trajectory_valid",
    "observation_state_valid",
    "quaternion_valid",
    "timestamp_monotonic",
    "timestep_consistent",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"CSV is empty: {path}")
    return rows


def _finite(value: str, *, field: str, row_key: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Non-numeric {field} at {row_key}: {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"Non-finite {field} at {row_key}: {value!r}")
    return number


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _sample_sd(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    center = _mean(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / (len(values) - 1))


def _qc_pass(row: Mapping[str, str]) -> bool:
    return all(row.get(field, "") == "PASS" for field in QC_FIELDS)


def _validate_config(config: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if config.get("condition_id") != "parkin_class_level_exploratory":
        blockers.append("condition_id_must_be_parkin_class_level_exploratory")
    if config.get("mapping_scope") != "class_level_exploratory":
        blockers.append("mapping_scope_must_be_class_level_exploratory")
    if config.get("gene_specific_mapping") is not False:
        blockers.append("gene_specific_mapping_must_be_false")
    if config.get("unit_of_analysis") != "matched_rollout_seed":
        blockers.append("unit_of_analysis_must_be_matched_rollout_seed")
    if config.get("healthy_seeds_used") != [0, 1, 2, 3, 4]:
        blockers.append("healthy_seeds_used_must_be_0_to_4")
    if config.get("healthy_seed_5_policy") != "excluded_from_paired_comparison":
        blockers.append("healthy_seed_5_policy_must_be_explicit")
    if config.get("burden_levels") != [0.0, 0.25, 0.5, 0.75, 1.0]:
        blockers.append("burden_levels_must_match_gate21")
    analysis = config.get("analysis")
    if not isinstance(analysis, dict):
        blockers.append("analysis_policy_missing")
    else:
        if analysis.get("calibration") is not False:
            blockers.append("calibration_must_be_false")
        if analysis.get("holdout_validation") is not False:
            blockers.append("holdout_validation_must_be_false")
    return blockers


def _index_healthy(rows: Iterable[Mapping[str, str]], seeds: Sequence[int]) -> dict[int, dict[str, str]]:
    indexed: dict[int, dict[str, str]] = {}
    for row in rows:
        seed = int(row.get("seed", "-1"))
        if seed in seeds:
            if seed in indexed:
                raise ValueError(f"Duplicate Healthy seed: {seed}")
            indexed[seed] = dict(row)
    return indexed


def _index_parkin(rows: Iterable[Mapping[str, str]], burden_levels: Sequence[float], seeds: Sequence[int]) -> dict[tuple[float, int], dict[str, str]]:
    indexed: dict[tuple[float, int], dict[str, str]] = {}
    allowed = {round(float(value), 8) for value in burden_levels}
    for row in rows:
        burden = round(float(row.get("burden_level", "nan")), 8)
        seed = int(row.get("seed", "-1"))
        if burden in allowed and seed in seeds:
            key = (burden, seed)
            if key in indexed:
                raise ValueError(f"Duplicate Parkin burden/seed: {key}")
            indexed[key] = dict(row)
    return indexed


def _compare(
    *, healthy_rows: Sequence[Mapping[str, str]], parkin_rows: Sequence[Mapping[str, str]], config: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    seeds = [int(value) for value in config["healthy_seeds_used"]]
    burdens = [float(value) for value in config["burden_levels"]]
    healthy = _index_healthy(healthy_rows, seeds)
    parkin = _index_parkin(parkin_rows, burdens, seeds)
    expected = len(seeds) * len(burdens)
    blockers: list[str] = []
    missing_healthy = [seed for seed in seeds if seed not in healthy]
    if missing_healthy:
        blockers.append(f"missing_healthy_seeds:{','.join(map(str, missing_healthy))}")
    expected_keys = {(round(burden, 8), seed) for burden in burdens for seed in seeds}
    missing_parkin = sorted(expected_keys - set(parkin))
    if missing_parkin:
        blockers.append(f"missing_parkin_pairs:{missing_parkin}")

    metrics = list(config["primary_metrics"]) + list(config["secondary_metrics"])
    rows: list[dict[str, Any]] = []
    for burden in burdens:
        for metric in metrics:
            healthy_values: list[float] = []
            parkin_values: list[float] = []
            deltas: list[float] = []
            relative_deltas: list[float] = []
            paired_qc = True
            pair_count = 0
            for seed in seeds:
                healthy_row = healthy.get(seed)
                parkin_row = parkin.get((round(burden, 8), seed))
                if healthy_row is None or parkin_row is None:
                    paired_qc = False
                    continue
                pair_count += 1
                paired_qc = paired_qc and _qc_pass(healthy_row) and _qc_pass(parkin_row)
                healthy_value = _finite(healthy_row.get(metric, ""), field=metric, row_key=f"healthy/{seed}")
                parkin_value = _finite(parkin_row.get(metric, ""), field=metric, row_key=f"parkin/{burden}/{seed}")
                delta = parkin_value - healthy_value
                healthy_values.append(healthy_value)
                parkin_values.append(parkin_value)
                deltas.append(delta)
                if healthy_value != 0:
                    relative_deltas.append(delta / healthy_value)
            if len(deltas) != len(seeds):
                paired_qc = False
            delta_sd = _sample_sd(deltas) if deltas else None
            mean_delta = _mean(deltas) if deltas else None
            standardised = None
            if mean_delta is not None and delta_sd is not None:
                standardised = mean_delta / delta_sd if delta_sd > 0 else (0.0 if mean_delta == 0 else None)
            row = {
                "condition": "parkin_class_level_exploratory",
                "burden_level": burden,
                "metric": metric,
                "unit_of_analysis": "matched_rollout_seed",
                "n_pairs": len(deltas),
                "expected_pairs": len(seeds),
                "healthy_mean": _mean(healthy_values) if healthy_values else None,
                "healthy_sample_sd": _sample_sd(healthy_values) if healthy_values else None,
                "proxy_mean": _mean(parkin_values) if parkin_values else None,
                "proxy_sample_sd": _sample_sd(parkin_values) if parkin_values else None,
                "mean_delta_proxy_minus_healthy": mean_delta,
                "delta_sample_sd": delta_sd,
                "delta_se": (delta_sd / math.sqrt(len(deltas))) if delta_sd is not None and deltas else None,
                "mean_relative_change": _mean(relative_deltas) if relative_deltas else None,
                "paired_standardized_delta": standardised,
                "paired_qc_status": "PASS" if paired_qc else "FAIL",
                "comparison_status": "PASS" if paired_qc and len(deltas) == len(seeds) else "BLOCKED",
            }
            rows.append(row)
    passed = sum(row["comparison_status"] == "PASS" for row in rows)
    summary = {
        "status": "PARKIN_HEALTHY_COMPARISON_PASS" if passed == len(rows) and not blockers else "PARKIN_HEALTHY_COMPARISON_PARTIAL",
        "planned_pair_count": expected,
        "observed_pair_count": sum(1 for burden in burdens for seed in seeds if (round(burden, 8), seed) in parkin and seed in healthy),
        "comparison_row_count": len(rows),
        "passed_comparison_rows": passed,
        "failed_comparison_rows": len(rows) - passed,
        "seeds_used": seeds,
        "healthy_seed_5_excluded": True,
        "burden_levels": burdens,
        "primary_metrics": list(config["primary_metrics"]),
        "secondary_metrics": list(config["secondary_metrics"]),
        "blockers": blockers,
        "gene_specific_mapping": False,
        "mapping_scope": "class_level_exploratory",
        "calibration_run": False,
        "holdout_validation_run": False,
        "simulation_run": False,
        "gpu_run": False,
        "data_fabricated": False,
    }
    return rows, summary


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.8g}"
    return str(value)


def _write_report(path: Path, *, summary: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], sources: Mapping[str, str]) -> None:
    primary = set(summary["primary_metrics"])
    lines = [
        "# Gate 22: So sánh Parkin proxy class-level với Healthy baseline",
        "",
        f"**Trạng thái:** `{summary['status']}`",
        "",
        "Gate 22 là phân tích hậu nghiệm trên các bảng metric nhỏ đã được lưu từ Gate 11 và Gate 21. Gate này không chạy GPU, không chạy simulation, không calibration và không holdout validation.",
        "",
        "## Thiết kế",
        "",
        "- Đơn vị phân tích: một cặp rollout ghép cùng `seed`.",
        f"- Seed sử dụng: `{', '.join(map(str, summary['seeds_used']))}`; Healthy seed `5` được giữ trong baseline nhưng loại khỏi paired comparison vì Gate 21 chỉ chạy seed `0–4`.",
        "- So sánh: `delta = Parkin_proxy - Healthy`; standardized delta = trung bình delta chia cho sample SD của các delta ghép cặp.",
        "- Các con số là thống kê mô tả trên 5 seed, không phải uncertainty sinh học và không phải kiểm định xác nhận bệnh.",
        "- Mapping vẫn là `class_level_exploratory`; không diễn giải là Parkin gene-specific.",
        "",
        "## Kết quả metric chính",
        "",
        "| Burden | Metric | n | Healthy mean | Proxy mean | Delta | Paired standardized delta | QC |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        if row["metric"] not in primary:
            continue
        lines.append(
            f"| {_fmt(row['burden_level'])} | `{row['metric']}` | {row['n_pairs']} | {_fmt(row['healthy_mean'])} | {_fmt(row['proxy_mean'])} | {_fmt(row['mean_delta_proxy_minus_healthy'])} | {_fmt(row['paired_standardized_delta'])} | `{row['comparison_status']}` |"
        )
    lines.extend([
        "",
        "## Đọc kết quả",
        "",
        "Gate 21 đã đạt QC rollout, nên phép ghép và tính toán của Gate 22 hoàn tất. Tuy nhiên, các burden trong Gate 21 không tạo ra xu hướng đơn điệu rõ ràng trên metric chính; kết quả này chỉ xác nhận pipeline so sánh hoạt động và ghi nhận response quan sát được của proxy. Nó không chứng minh Parkin gây ra phenotype sinh học, không chứng minh mapping gene-specific và không thay thế dữ liệu ruồi thật.",
        "",
        "## Provenance",
        "",
        f"- Healthy metrics: `{sources['healthy_metrics']}`",
        f"- Healthy manifest: `{sources['healthy_manifest']}`",
        f"- Gate 21 metrics: `{sources['parkin_metrics']}`",
        f"- Gate 21 manifest: `{sources['parkin_manifest']}`",
        "",
        "## Ranh giới",
        "",
        "Không dùng Chen hoặc Pozo ở Gate 22. Không có calibration, tuning, holdout validation, biological Parkinson validation, clinical prediction hay drug validation.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(*, config_path: Path = DEFAULT_CONFIG, output_dir: Path = DEFAULT_OUTPUT, report_path: Path = DEFAULT_REPORT) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(config, dict):
        raise ValueError("Gate 22 config must be a YAML mapping")
    blockers = _validate_config(config)
    source_paths = {key: ROOT / value for key, value in config["sources"].items()}
    for key, path in source_paths.items():
        if not path.is_file():
            blockers.append(f"missing_source:{key}:{_relative(path)}")
    if blockers:
        raise ValueError("Gate 22 blocked: " + "; ".join(blockers))
    healthy_manifest = _read_json(source_paths["healthy_manifest"])
    parkin_manifest = _read_json(source_paths["parkin_manifest"])
    metric_contract = healthy_manifest.get("metric_contract")
    contract_status = (
        healthy_manifest.get("metric_contract_status")
        if healthy_manifest.get("metric_contract_status") is not None
        else metric_contract.get("status") if isinstance(metric_contract, dict) else None
    )
    if healthy_manifest.get("status") != "PASS" or contract_status != "PASS":
        raise ValueError("Healthy baseline manifest is not PASS with metric contract PASS")
    if parkin_manifest.get("status") != "PARKIN_CLASS_LEVEL_EXPLORATORY_ROLLOUTS_PASS":
        raise ValueError("Gate 21 manifest is not a completed exploratory rollout")
    if parkin_manifest.get("gene_specific_mapping") is not False:
        raise ValueError("Gate 21 mapping must remain non-gene-specific")
    if parkin_manifest.get("calibration_run") or parkin_manifest.get("holdout_validation_run"):
        raise ValueError("Gate 22 cannot consume calibrated or holdout output")
    healthy_rows = _read_csv(source_paths["healthy_metrics"])
    parkin_rows = _read_csv(source_paths["parkin_metrics"])
    rows, summary = _compare(healthy_rows=healthy_rows, parkin_rows=parkin_rows, config=config)
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = output_dir / "gate22_comparison.csv"
    summary_path = output_dir / "gate22_comparison_summary.json"
    manifest_path = output_dir / "gate22_comparison_manifest.json"
    _write_csv(comparison_path, rows)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "gate-22-parkin-healthy-comparison-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        **summary,
        "config": _relative(config_path),
        "config_sha256": _sha256(config_path),
        "sources": {key: {"path": _relative(path), "sha256": _sha256(path)} for key, path in source_paths.items()},
        "artifacts": {
            "comparison_csv": _relative(comparison_path),
            "summary_json": _relative(summary_path),
            "report": _relative(report_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_report(report_path, summary=summary, rows=rows, sources={key: _relative(path) for key, path in source_paths.items()})
    checksum_paths = [comparison_path, summary_path, manifest_path, report_path]
    checksum_path = output_dir / "gate22_checksums.sha256"
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
    print(json.dumps({key: result[key] for key in ("status", "planned_pair_count", "observed_pair_count", "comparison_row_count", "passed_comparison_rows", "failed_comparison_rows")}, indent=2))
    print(f"Manifest: {args.output / 'gate22_comparison_manifest.json'}")
    print(f"Report: {args.report}")
    return 0 if result["status"] == "PARKIN_HEALTHY_COMPARISON_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
