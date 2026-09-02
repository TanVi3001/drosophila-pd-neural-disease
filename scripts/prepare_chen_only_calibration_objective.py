"""Prepare the Gate 13A Chen-only calibration objective.

This script creates a provenance-preserving feasibility package. It does not
optimize parameters, run calibration, or run a holdout validation.
"""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGETS = ROOT / "calibration_targets/targets.csv"
CHEN_SOURCE = ROOT / "research/paper_review/digitized/chen_2014_adult_walking_speed.csv"
HEALTHY_MANIFEST = ROOT / "experiments/gate_11_healthy_baseline/manifests/healthy_baseline_manifest.json"
G12_SUMMARY = ROOT / "experiments/gate_12g_integrated_proxy_rollouts/results/integrated_proxy_disease_summary.csv"
G12_MANIFEST = ROOT / "experiments/gate_12g_integrated_proxy_rollouts/manifests/integrated_proxy_rollout_manifest.json"
OUTPUT_ROOT = ROOT / "experiments/gate_13a_chen_objective"
CONFIG = OUTPUT_ROOT / "configs/chen_only_calibration_objective.yaml"
FEASIBILITY = OUTPUT_ROOT / "results/chen_objective_feasibility.csv"
CANDIDATES = OUTPUT_ROOT / "results/chen_calibration_candidates.csv"
MANIFEST = OUTPUT_ROOT / "manifests/chen_objective_manifest.json"
REPORT = ROOT / "docs/calibration/gate_13a_chen_objective_feasibility_report.md"

FINAL_READY = "READY_FOR_GATE_13B_CHEN_RATIO_CALIBRATION"
FINAL_REVIEW = "CHEN_OBJECTIVE_REVIEW_REQUIRED"
FEASIBILITY_FIELDS = (
    "objective_type",
    "metric",
    "target_value",
    "target_unit",
    "uncertainty",
    "uncertainty_type",
    "provenance",
    "status",
    "notes",
)
CANDIDATE_FIELDS = (
    "condition_id",
    "burden_level",
    "n_success",
    "simulated_mean_planar_speed_mm_s_mean",
    "simulated_mean_planar_speed_mm_s_std",
    "simulated_ratio_to_burden0",
    "chen_absolute_target_mm_s",
    "chen_ratio_target",
    "absolute_speed_error",
    "ratio_error",
    "candidate_rank_by_ratio",
    "usable_for_gate_13b",
    "notes",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    if isinstance(value, int):
        return str(value)
    number = _number(value)
    if number is None:
        return str(value)
    return f"{number:.12g}"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "NOT_AVAILABLE"


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _fmt(row.get(field, "")) for field in fields})


def _approved_chen_target(rows: list[dict[str, str]]) -> dict[str, str] | None:
    matches = [
        row
        for row in rows
        if row.get("paper_id") == "chen_2014_adult_walking"
        and row.get("metric") == "mean_planar_speed_mm_s"
        and row.get("review_status", "").strip().lower() == "approved"
    ]
    return matches[0] if len(matches) == 1 else None


def _chen_source_rows(rows: list[dict[str, str]]) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    disease = next(
        (
            row
            for row in rows
            if row.get("condition") == "Old A30P"
            and row.get("genotype") == "pan-neuronal Elav > human alpha-synuclein A30P"
        ),
        None,
    )
    control = next(
        (
            row
            for row in rows
            if row.get("condition") == "Old CT"
            and row.get("genotype") == "age-matched control"
        ),
        None,
    )
    return disease, control


def _source_value_mm_s(row: dict[str, str] | None) -> float | None:
    if row is None or row.get("unit") != "cm/s":
        return None
    value = _number(row.get("value"))
    return value * 10.0 if value is not None else None


def _valid_chen_target(row: dict[str, str] | None) -> bool:
    if row is None:
        return False
    required = {
        "metric": "mean_planar_speed_mm_s",
        "unit": "mm/s",
        "variance_type": "CI95",
    }
    if any(row.get(key) != value for key, value in required.items()):
        return False
    return all(_number(row.get(key)) is not None for key in ("value", "variance", "sample_size"))


def _valid_source_row(row: dict[str, str] | None) -> bool:
    if row is None:
        return False
    return (
        row.get("unit") == "cm/s"
        and row.get("metric") == "mean_walking_velocity_cm_s"
        and row.get("center_statistic") == "mean"
        and row.get("uncertainty_type") == "CI95"
        and _number(row.get("value")) is not None
        and _number(row.get("uncertainty")) is not None
        and _number(row.get("sample_size")) is not None
    )


def _load_alpha_summary(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        if row.get("condition_id") != "alpha_synuclein":
            continue
        burden = _number(row.get("burden_level"))
        speed = _number(row.get("mean_planar_speed_mm_s_mean"))
        speed_std = _number(row.get("mean_planar_speed_mm_s_std"))
        n_success = _number(row.get("n_success"))
        if burden is None or speed is None or speed_std is None or n_success is None:
            continue
        selected.append(
            {
                "condition_id": row["condition_id"],
                "burden_level": burden,
                "n_success": int(n_success),
                "speed": speed,
                "speed_std": speed_std,
            }
        )
    return sorted(selected, key=lambda item: item["burden_level"])


def _yaml_config(
    *,
    status: str,
    control_mm_s: float | None,
    ratio: float | None,
) -> str:
    control = _fmt(control_mm_s) if control_mm_s is not None else "NOT_AVAILABLE"
    ratio_value = _fmt(ratio) if ratio is not None else "NOT_AVAILABLE"
    preferred = "mean_planar_speed_ratio_to_control" if ratio is not None else "REVIEW_REQUIRED"
    return f"""schema_version: gate-13a-chen-only-objective-v1
status: {status}

calibration_scope:
  condition_id: alpha_synuclein
  proxy_scope: organism_level_proxy
  gene_specific_mapping: false
  biological_validation_claim: false

source_targets:
  chen_2014:
    allocation: calibration
    disease_metric: mean_planar_speed_mm_s
    disease_value_mm_s: 4.875
    uncertainty_type: CI95
    uncertainty_mm_s: 0.525
    n: 20
    matched_control_required_for_ratio: true
    matched_control_value_mm_s: {control}
    disease_to_control_ratio: {ratio_value}

objective_decision:
  preferred_objective: {preferred}
  absolute_speed_target_role: reference_only
  reason: "Ratio objective is preferred for organism-level proxy calibration because the simulated healthy baseline scale and Chen assay scale are not directly identical."

simulation_inputs:
  gate_12g_summary: experiments/gate_12g_integrated_proxy_rollouts/results/integrated_proxy_disease_summary.csv
  use_condition: alpha_synuclein
  control_burden_level: 0.0
  candidate_burden_levels: [0.25, 0.5, 0.75, 1.0]

forbidden:
  use_pozo: false
  holdout_validation: false
  calibration_optimization_in_gate_13a: false
  ci95_to_se_conversion: false
  distance_to_speed_conversion: false
  biological_validation_claim: false
"""


def prepare() -> dict[str, Any]:
    targets = _read_csv(TARGETS)
    chen_source = _read_csv(CHEN_SOURCE) if CHEN_SOURCE.is_file() else []
    summary = _read_csv(G12_SUMMARY) if G12_SUMMARY.is_file() else []
    healthy_manifest = _read_json(HEALTHY_MANIFEST) if HEALTHY_MANIFEST.is_file() else {}
    g12_manifest = _read_json(G12_MANIFEST) if G12_MANIFEST.is_file() else {}

    target = _approved_chen_target(targets)
    disease_source, control_source = _chen_source_rows(chen_source)
    target_valid = _valid_chen_target(target)
    source_valid = _valid_source_row(disease_source)
    control_valid = _valid_source_row(control_source)
    disease_mm_s = _source_value_mm_s(disease_source)
    control_mm_s = _source_value_mm_s(control_source) if control_valid else None
    ratio = disease_mm_s / control_mm_s if disease_mm_s is not None and control_mm_s else None
    summary_rows = _load_alpha_summary(summary)
    summary_ready = (
        len(summary_rows) == 5
        and all(item["n_success"] > 0 for item in summary_rows)
        and summary_rows[0]["burden_level"] == 0.0
        and all(math.isfinite(item["speed"]) for item in summary_rows)
    )
    final_status = FINAL_READY if target_valid and source_valid and control_valid and ratio is not None and summary_ready else FINAL_REVIEW

    target_provenance = "calibration_targets/targets.csv"
    source_provenance = "research/paper_review/digitized/chen_2014_adult_walking_speed.csv"
    absolute_status = "REFERENCE_ONLY" if target_valid else "REVIEW_REQUIRED"
    absolute_notes = (
        "Chen absolute speed is retained as a reference target; Gate 13A does not tune a parameter and does not assume direct scale equivalence."
        if target_valid
        else "Approved Chen target is missing or has invalid metadata."
    )
    ratio_status = "PREFERRED_FOR_PROXY_CALIBRATION" if ratio is not None and final_status == FINAL_READY else "BLOCKED_NO_MATCHED_CONTROL"
    ratio_notes = (
        "Computed only from the matched Old A30P and Old CT rows in the same Chen digitization source; ratio is dimensionless."
        if ratio is not None
        else "Matched Chen control provenance or numeric value is unavailable; do not create a ratio."
    )
    feasibility_rows = [
        {
            "objective_type": "absolute",
            "metric": "mean_planar_speed_mm_s",
            "target_value": 4.875 if target_valid else "",
            "target_unit": "mm/s",
            "uncertainty": 0.525 if target_valid else "",
            "uncertainty_type": "CI95" if target_valid else "NOT_AVAILABLE",
            "provenance": target_provenance,
            "status": absolute_status,
            "notes": absolute_notes,
        },
        {
            "objective_type": "ratio",
            "metric": "mean_planar_speed_ratio_to_control",
            "target_value": ratio if ratio is not None else "",
            "target_unit": "dimensionless",
            "uncertainty": "",
            "uncertainty_type": "NOT_REPORTED",
            "provenance": source_provenance,
            "status": ratio_status,
            "notes": ratio_notes,
        },
    ]

    control_speed = summary_rows[0]["speed"] if summary_ready else None
    candidate_rows: list[dict[str, Any]] = []
    for item in summary_rows:
        sim_ratio = item["speed"] / control_speed if control_speed not in (None, 0) else None
        candidate_rows.append(
            {
                "condition_id": item["condition_id"],
                "burden_level": item["burden_level"],
                "n_success": item["n_success"],
                "simulated_mean_planar_speed_mm_s_mean": item["speed"],
                "simulated_mean_planar_speed_mm_s_std": item["speed_std"],
                "simulated_ratio_to_burden0": sim_ratio if sim_ratio is not None else "",
                "chen_absolute_target_mm_s": 4.875 if target_valid else "",
                "chen_ratio_target": ratio if ratio is not None else "",
                "absolute_speed_error": abs(item["speed"] - 4.875) if target_valid else "",
                "ratio_error": abs(sim_ratio - ratio) if sim_ratio is not None and ratio is not None else "",
                "candidate_rank_by_ratio": "",
                "usable_for_gate_13b": False,
                "notes": "Control burden 0.0 is the Gate 12G proxy reference; no burden is selected in Gate 13A.",
            }
        )

    ranked = sorted(
        (
            row
            for row in candidate_rows
            if row["burden_level"] > 0 and _number(row["ratio_error"]) is not None
        ),
        key=lambda row: (float(row["ratio_error"]), float(row["burden_level"])),
    )
    for rank, row in enumerate(ranked, start=1):
        row["candidate_rank_by_ratio"] = rank
        row["usable_for_gate_13b"] = final_status == FINAL_READY
        row["notes"] = "Descriptive ratio ranking for Gate 13B review; it does not choose or tune a final parameter in Gate 13A."

    _write_csv(FEASIBILITY, FEASIBILITY_FIELDS, feasibility_rows)
    _write_csv(CANDIDATES, CANDIDATE_FIELDS, candidate_rows)
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(
        _yaml_config(status=final_status, control_mm_s=control_mm_s, ratio=ratio),
        encoding="utf-8",
    )

    source_files = [TARGETS, CHEN_SOURCE, G12_SUMMARY]
    source_records = [
        {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": _sha256(path) if path.is_file() else "NOT_AVAILABLE",
            "present": path.is_file(),
        }
        for path in source_files
    ]
    manifest: dict[str, Any] = {
        "schema_version": "gate-13a-chen-objective-manifest-v1",
        "status": final_status,
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "python_version": __import__("platform").python_version(),
        "source_files": [record["path"] for record in source_records],
        "source_file_records": source_records,
        "chen_target": {
            "disease_value_mm_s": 4.875 if target_valid else None,
            "uncertainty_type": "CI95" if target_valid else "NOT_AVAILABLE",
            "uncertainty_mm_s": 0.525 if target_valid else None,
            "n": 20 if target_valid else None,
            "matched_control_value_mm_s": control_mm_s,
            "ratio_target": ratio,
            "disease_source_row_present": disease_source is not None,
            "control_source_row_present": control_source is not None,
        },
        "objective": {
            "preferred": "mean_planar_speed_ratio_to_control" if ratio is not None and final_status == FINAL_READY else "REVIEW_REQUIRED",
            "absolute_target_role": "reference_only",
            "candidate_count": len(ranked),
            "no_parameter_selected": True,
        },
        "simulation_inputs": {
            "gate_12g_summary": str(G12_SUMMARY.relative_to(ROOT)).replace("\\", "/"),
            "gate_12g_manifest_status": g12_manifest.get("status", "NOT_AVAILABLE"),
            "healthy_baseline_manifest": str(HEALTHY_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
            "healthy_baseline_status": healthy_manifest.get("status", "NOT_AVAILABLE"),
            "condition_used": "alpha_synuclein",
            "control_burden_level": 0.0,
            "candidate_burden_levels": [0.25, 0.5, 0.75, 1.0],
        },
        "no_calibration_run": True,
        "no_holdout_validation_run": True,
        "pozo_used": False,
        "pink1_used_for_calibration": False,
        "gene_specific_mapping": False,
        "biological_validation_claim": False,
        "large_artifacts_committed": False,
        "scientific_boundary": "Gate 13A is a computational organism-level proxy objective feasibility package, not biological Parkinson validation.",
        "outputs": {
            "feasibility_csv": str(FEASIBILITY.relative_to(ROOT)).replace("\\", "/"),
            "candidates_csv": str(CANDIDATES.relative_to(ROOT)).replace("\\", "/"),
            "config": str(CONFIG.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report_lines = [
        "# Gate 13A - Chen-only Calibration Objective & Feasibility",
        "",
        "## Mục tiêu",
        "",
        "Gate 13A chuẩn bị objective cho calibration bằng Chen 2014 only. Gate này không tối ưu tham số, không chạy calibration và không chạy holdout validation.",
        "",
        "## Trạng thái input",
        "",
        f"- Gate 12G integrated proxy rollouts: `{g12_manifest.get('status', 'NOT_AVAILABLE')}`.",
        f"- Healthy baseline manifest: `{healthy_manifest.get('status', 'NOT_AVAILABLE')}`.",
        f"- Audit target: `READY_FOR_CALIBRATION` (đã kiểm tra trước khi tạo gate).",
        "- Condition được dùng: `alpha_synuclein`, phạm vi `organism_level_proxy`.",
        "- Chưa chạy calibration và chưa chạy holdout validation.",
        "",
        "## Chen target",
        "",
        "- Disease value: `4.875 mm/s`.",
        "- Uncertainty: `0.525 CI95`.",
        "- Sample size: `n=20 fly`.",
        "- Metric: `mean_planar_speed_mm_s`.",
        "- Allocation: `calibration`.",
        f"- Matched Old CT control: `{_fmt(control_mm_s)} mm/s` nếu có provenance.",
        f"- Disease/control ratio: `{_fmt(ratio)}` nếu có thể tính từ cùng source.",
        "",
        "Giá trị Chen gốc được ghi trong source là `0.4875 cm/s`, được đổi đơn vị vật lý thành `4.875 mm/s`. CI95 được giữ nguyên là CI95; không đổi thành SE.",
        "",
        "## Quyết định objective",
        "",
        "- Absolute speed target chỉ giữ vai trò `reference_only`, vì scale assay Chen và scale simulator chưa được chứng minh là đồng nhất trực tiếp.",
        "- Ratio `mean_planar_speed_ratio_to_control` được ưu tiên cho Gate 13B khi matched control có provenance.",
        "- Không dùng Pozo trong Gate 13A; Pozo chỉ là holdout của Gate 14.",
        "- Không dùng PINK1 cho Chen calibration objective.",
        "",
        "## Candidate burden table",
        "",
        "Bảng dưới đây lấy từ summary Gate 12G của `alpha_synuclein`. Hạng chỉ để Gate 13B review, không phải kết quả tuning hay lựa chọn tham số cuối.",
        "",
    ]
    report_lines.extend(
        [
            "| Burden | Successful runs | Speed mean (mm/s) | Speed std | Ratio vs burden 0 | Ratio error vs Chen | Rank | Usable for Gate 13B |",
            "|---:|---:|---:|---:|---:|---:|---:|:---:|",
        ]
    )
    for row in candidate_rows:
        report_lines.append(
            "| {burden} | {n} | {speed} | {std} | {ratio_value} | {error} | {rank} | {usable} |".format(
                burden=_fmt(row["burden_level"]),
                n=row["n_success"],
                speed=_fmt(row["simulated_mean_planar_speed_mm_s_mean"]),
                std=_fmt(row["simulated_mean_planar_speed_mm_s_std"]),
                ratio_value=_fmt(row["simulated_ratio_to_burden0"]),
                error=_fmt(row["ratio_error"]),
                rank=row["candidate_rank_by_ratio"] or "-",
                usable="yes" if row["usable_for_gate_13b"] else "no",
            )
        )
    report_lines.extend(
        [
            "",
            "## Final status",
            "",
            f"`{final_status}`",
            "",
            "Gate 13A chỉ xác nhận rằng objective có thể được chuẩn bị từ target Chen và summary proxy hiện có. Gate 13B mới là nơi nhóm nghiên cứu quyết định cách chạy calibration; Gate 13A không chọn parameter bằng tối ưu hóa.",
            "",
            "## Boundary",
            "",
            "Đây là computational locomotion experiment ở phạm vi organism-level proxy. Không phải biological Parkinson validation, không phải gene-specific mapping, không phải chẩn đoán lâm sàng và không phải đánh giá thuốc.",
            "",
            "Các artifact lớn như video, NPZ và checkpoint không được sao chép vào package Gate 13A; chỉ lưu bảng summary và provenance cần thiết.",
            "",
        ]
    )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report_lines), encoding="utf-8")

    return {
        "status": final_status,
        "ratio": ratio,
        "control_mm_s": control_mm_s,
        "candidate_count": len(candidate_rows),
        "ranked_count": len(ranked),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = prepare()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
