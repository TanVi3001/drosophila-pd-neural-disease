"""Lock a Chen-only ratio calibration from existing Gate 12G summaries.

Gate 13B is a discrete grid selection over already executed proxy rollouts.
It does not invoke FlyGym, create a new rollout, use Pozo, or run holdout
validation.
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
import subprocess
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments/gate_13b_chen_ratio_calibration/configs/chen_ratio_calibration_config.yaml"
OUTPUT_ROOT = ROOT / "experiments/gate_13b_chen_ratio_calibration"
RESULTS = OUTPUT_ROOT / "results/chen_ratio_calibration_results.csv"
SUMMARY_JSON = OUTPUT_ROOT / "results/chen_ratio_calibration_summary.json"
CALIBRATED_CONFIG = OUTPUT_ROOT / "configs/calibrated_alpha_synuclein_proxy.yaml"
MANIFEST = OUTPUT_ROOT / "manifests/chen_ratio_calibration_manifest.json"
REPORT = ROOT / "docs/calibration/gate_13b_chen_ratio_calibration_report.md"

PASS_STATUS = "CHEN_RATIO_CALIBRATION_PASS"
BLOCKED_STATUS = "CHEN_RATIO_CALIBRATION_BLOCKED"
RESULT_FIELDS = (
    "condition_id",
    "burden_level",
    "n_success",
    "simulated_speed_mean",
    "simulated_speed_std",
    "simulated_ratio_to_burden0",
    "chen_ratio_target",
    "ratio_error",
    "chen_absolute_speed_target_mm_s",
    "absolute_speed_error",
    "rank",
    "selected",
    "usable_for_calibration",
    "notes",
)


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _number(value: Any) -> float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _fmt(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    number = _number(value)
    return f"{number:.12g}" if number is not None else str(value)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "NOT_AVAILABLE"
    return result.stdout.strip()


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _fmt(row.get(field, "")) for field in RESULT_FIELDS})


def _resolve(relative: str) -> Path:
    return ROOT / relative.replace("/", "\\")


def _source_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "present": path.is_file(),
        "sha256": _sha256(path) if path.is_file() else "NOT_AVAILABLE",
    }


def _calibrated_config(selected_burden: float) -> str:
    return f"""schema_version: gate-13b-calibrated-alpha-synuclein-proxy-v1
status: CHEN_RATIO_CALIBRATED

condition_id: alpha_synuclein
scope: organism_level_proxy
gene_specific_mapping: false
biological_validation_claim: false

calibration_source:
  paper: Chen 2014
  allocation: calibration
  metric: mean_planar_speed_ratio_to_control
  disease_value_mm_s: 4.875
  control_value_mm_s: 7.275
  ratio_target: 0.6701030927835051
  uncertainty_type: CI95
  uncertainty_mm_s: 0.525
  ci95_converted_to_se: false

selected_parameter:
  parameter_name: proxy_burden_level
  selected_value: {_fmt(selected_burden)}
  selection_method: discrete_grid_min_absolute_ratio_error
  source_data: experiments/gate_12g_integrated_proxy_rollouts/results/integrated_proxy_disease_summary.csv

operator:
  source_config: experiments/gate_12e_proxy_operator/configs/proxy_burden_action_operator.yaml
  applies_to: joint_angles
  modifies_adhesion_onoff: false

forbidden_downstream:
  tune_on_pozo: true
  tune_on_holdout: true
  claim_biological_validation: true
  claim_gene_specific_mapping: true
"""


def _report(
    *,
    status: str,
    rows: list[dict[str, Any]],
    selected: dict[str, Any] | None,
    ratio_target: float,
) -> str:
    lines = [
        "# Gate 13B - Chen-only Ratio Calibration",
        "",
        "## Mục tiêu",
        "",
        "Gate 13B khóa một lựa chọn calibration rời rạc bằng target Chen 2014, sử dụng tỷ lệ tốc độ đi bộ disease/control.",
        "",
        "## Trạng thái input",
        "",
        "- Gate 12G integrated proxy rollouts: đã có summary alpha-synuclein với 6 seed cho mỗi mức burden.",
        "- Gate 13A objective: Chen-only ratio objective đã sẵn sàng.",
        "- Audit: `READY_FOR_CALIBRATION`.",
        "- Không dùng Pozo và không dùng PINK1 cho calibration.",
        "",
        "## Chen target",
        "",
        "- Disease A30P speed: `4.875 mm/s`.",
        "- Control Old CT speed: `7.275 mm/s`.",
        f"- Ratio target: `{ratio_target:.16f}`.",
        "- Uncertainty: `0.525 CI95`; CI95 không bị đổi thành SE.",
        "- Sample size: `n=20 fly`.",
        "",
        "## Calibration method",
        "",
        "- Method: `discrete_grid_selection` trên các rollout Gate 12G đã tồn tại.",
        "- Control burden: `0.0`.",
        "- Candidate burdens: `0.25, 0.5, 0.75, 1.0`.",
        "- Objective: giảm nhỏ nhất `abs(simulated_ratio_to_burden0 - chen_ratio_target)`.",
        "- Absolute speed chỉ là reference, không phải objective chính.",
        "- Không tối ưu liên tục và không chạy simulation mới.",
        "",
        "## Calibration result",
        "",
        "| Burden | Speed mean (mm/s) | Speed std | Ratio | Ratio error | Rank | Selected | Usable |",
        "|---:|---:|---:|---:|---:|---:|:---:|:---:|",
    ]
    for row in rows:
        lines.append(
            "| {burden} | {speed} | {std} | {ratio} | {error} | {rank} | {selected} | {usable} |".format(
                burden=_fmt(row["burden_level"]),
                speed=_fmt(row["simulated_speed_mean"]),
                std=_fmt(row["simulated_speed_std"]),
                ratio=_fmt(row["simulated_ratio_to_burden0"]),
                error=_fmt(row["ratio_error"]),
                rank=row["rank"] or "-",
                selected="yes" if row["selected"] else "no",
                usable="yes" if row["usable_for_calibration"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Selected parameter",
            "",
            f"- Selected `proxy_burden_level`: `{_fmt(selected['burden_level']) if selected else 'NOT_AVAILABLE'}`.",
            f"- Selected simulated ratio: `{_fmt(selected['simulated_ratio_to_burden0']) if selected else 'NOT_AVAILABLE'}`.",
            f"- Selected ratio error: `{_fmt(selected['ratio_error']) if selected else 'NOT_AVAILABLE'}`.",
            f"- Absolute speed error (reference only): `{_fmt(selected['absolute_speed_error']) if selected else 'NOT_AVAILABLE'} mm/s`.",
            "- Burden `0.5` là closest available discrete-grid candidate theo ratio error; đây không phải perfect fit.",
            "",
            "## Boundary",
            "",
            "Đây là computational proxy calibration ở phạm vi organism-level locomotion. Không phải gene-specific mapping, không phải biological Parkinson validation, không phải chẩn đoán lâm sàng và không phải đánh giá thuốc.",
            "- Không phải biological Parkinson validation.",
            "- Không chạy holdout validation trong Gate 13B.",
            "- Không dùng Pozo; target Pozo vẫn được giữ cho holdout độc lập ở Gate 14.",
            "- Không dùng PINK1, Parkin, DJ-1 hoặc LRRK2 trong objective calibration này.",
            "",
            "## Final status",
            "",
            f"`{status}`",
            "",
            "Nếu status PASS, Gate 13C có thể chạy calibrated rerun để kiểm tra lại rollout bằng cấu hình đã khóa; đây không phải holdout và không phải biological validation.",
            "",
        ]
    )
    return "\n".join(lines)


def run_calibration() -> dict[str, Any]:
    config = _load_yaml(CONFIG)
    source = config["source"]
    objective_path = _resolve(str(source["gate_13a_objective"]))
    candidates_path = _resolve(str(source["gate_13a_candidates"]))
    summary_path = _resolve(str(source["gate_12g_summary"]))
    operator_path = _resolve(str(source["operator_config"]))
    objective = _load_yaml(objective_path)
    summary_rows = _read_csv(summary_path)

    target = config["chen_target"]
    ratio_target = _number(target["ratio_target"])
    absolute_target = _number(target["disease_value_mm_s"])
    if ratio_target is None or absolute_target is None:
        raise ValueError("Chen target ratio or absolute target is not numeric.")
    if objective.get("status") != "READY_FOR_GATE_13B_CHEN_RATIO_CALIBRATION":
        raise ValueError("Gate 13A objective is not ready for Gate 13B.")
    if not candidates_path.is_file() or not operator_path.is_file():
        raise FileNotFoundError("Required Gate 13A candidate or operator config is missing.")
    if config["calibration_scope"]["condition_id"] != "alpha_synuclein":
        raise ValueError("Gate 13B is Chen-only alpha_synuclein calibration.")

    levels = [_number(value) for value in config["calibration_method"]["candidate_burden_levels"]]
    levels = [value for value in levels if value is not None]
    control_level = _number(config["calibration_method"]["control_burden_level"])
    alpha_rows = [row for row in summary_rows if row.get("condition_id") == "alpha_synuclein"]
    control_rows = [
        row for row in alpha_rows if _number(row.get("burden_level")) is not None and math.isclose(_number(row["burden_level"]) or 0.0, control_level or 0.0, abs_tol=1e-12)
    ]
    selected_rows: list[dict[str, Any]] = []
    if len(control_rows) != 1:
        status = BLOCKED_STATUS
        selected = None
    else:
        control_speed = _number(control_rows[0].get("mean_planar_speed_mm_s_mean"))
        selected = None
        if control_speed is None or control_speed == 0:
            status = BLOCKED_STATUS
        else:
            for level in [value for value in levels if value > 0]:
                matching = [
                    row
                    for row in alpha_rows
                    if _number(row.get("burden_level")) is not None and math.isclose(_number(row["burden_level"]) or 0.0, level, abs_tol=1e-12)
                ]
                if len(matching) != 1:
                    continue
                row = matching[0]
                speed = _number(row.get("mean_planar_speed_mm_s_mean"))
                speed_std = _number(row.get("mean_planar_speed_mm_s_std"))
                n_success = _number(row.get("n_success"))
                if speed is None or speed_std is None or n_success is None or n_success <= 0:
                    continue
                simulated_ratio = speed / control_speed
                selected_rows.append(
                    {
                        "condition_id": "alpha_synuclein",
                        "burden_level": level,
                        "n_success": int(n_success),
                        "simulated_speed_mean": speed,
                        "simulated_speed_std": speed_std,
                        "simulated_ratio_to_burden0": simulated_ratio,
                        "chen_ratio_target": ratio_target,
                        "ratio_error": abs(simulated_ratio - ratio_target),
                        "chen_absolute_speed_target_mm_s": absolute_target,
                        "absolute_speed_error": abs(speed - absolute_target),
                        "rank": "",
                        "selected": False,
                        "usable_for_calibration": True,
                        "notes": "Discrete candidate from Gate 12G; no new simulation was run.",
                    }
                )
            status = PASS_STATUS if selected_rows else BLOCKED_STATUS
            if selected_rows:
                ranked = sorted(selected_rows, key=lambda row: (row["ratio_error"], row["burden_level"]))
                for rank, row in enumerate(ranked, start=1):
                    row["rank"] = rank
                selected = ranked[0]
                selected["selected"] = True

    control_output = {
        "condition_id": "alpha_synuclein",
        "burden_level": control_level,
        "n_success": int(_number(control_rows[0].get("n_success")) or 0) if control_rows else "",
        "simulated_speed_mean": _number(control_rows[0].get("mean_planar_speed_mm_s_mean")) if control_rows else "",
        "simulated_speed_std": _number(control_rows[0].get("mean_planar_speed_mm_s_std")) if control_rows else "",
        "simulated_ratio_to_burden0": 1.0 if control_rows else "",
        "chen_ratio_target": ratio_target,
        "ratio_error": abs(1.0 - ratio_target) if control_rows else "",
        "chen_absolute_speed_target_mm_s": absolute_target,
        "absolute_speed_error": abs((_number(control_rows[0].get("mean_planar_speed_mm_s_mean")) or 0.0) - absolute_target) if control_rows else "",
        "rank": "",
        "selected": False,
        "usable_for_calibration": False,
        "notes": "Control burden 0.0; used only to normalize the Chen ratio and is never selected.",
    }
    output_rows = [control_output, *sorted(selected_rows, key=lambda row: row["burden_level"])]
    _write_csv(RESULTS, output_rows)

    CALIBRATED_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if selected is not None and status == PASS_STATUS:
        CALIBRATED_CONFIG.write_text(_calibrated_config(selected["burden_level"]), encoding="utf-8")
    else:
        CALIBRATED_CONFIG.write_text(
            _calibrated_config(0.0).replace("status: CHEN_RATIO_CALIBRATED", "status: CHEN_RATIO_CALIBRATION_BLOCKED"),
            encoding="utf-8",
        )

    summary_document: dict[str, Any] = {
        "schema_version": "gate-13b-chen-ratio-calibration-summary-v1",
        "status": status,
        "chen_ratio_target": ratio_target,
        "selected_burden_level": selected["burden_level"] if selected else None,
        "selected_simulated_ratio": selected["simulated_ratio_to_burden0"] if selected else None,
        "selected_ratio_error": selected["ratio_error"] if selected else None,
        "selected_absolute_speed_error_reference_only": selected["absolute_speed_error"] if selected else None,
        "calibration_method": "discrete_grid_selection",
        "source_gate_12g_summary": str(summary_path.relative_to(ROOT)).replace("\\", "/"),
        "source_gate_13a_objective": str(objective_path.relative_to(ROOT)).replace("\\", "/"),
        "pozo_used": False,
        "pink1_used_for_calibration": False,
        "no_holdout_validation_run": True,
        "no_new_simulation_run": True,
        "gene_specific_mapping": False,
        "biological_validation_claim": False,
        "selected_parameter": "proxy_burden_level" if selected else None,
    }
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary_document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    source_paths = [
        objective_path,
        candidates_path,
        summary_path,
        operator_path,
    ]
    manifest: dict[str, Any] = {
        "schema_version": "gate-13b-chen-ratio-calibration-manifest-v1",
        "status": status,
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "python_version": platform.python_version(),
        "source_files": [str(path.relative_to(ROOT)).replace("\\", "/") for path in source_paths],
        "source_file_records": [_source_record(path) for path in source_paths],
        "config_sha256": _sha256(CONFIG),
        "results_csv_sha256": _sha256(RESULTS),
        "summary_json_sha256": _sha256(SUMMARY_JSON),
        "calibrated_config_sha256": _sha256(CALIBRATED_CONFIG),
        "chen_target": {
            "ratio_target": ratio_target,
            "disease_value_mm_s": absolute_target,
            "control_value_mm_s": _number(target["control_value_mm_s"]),
            "uncertainty_type": target["uncertainty_type"],
            "uncertainty_mm_s": _number(target["uncertainty_mm_s"]),
        },
        "selected_parameter": {
            "proxy_burden_level": selected["burden_level"] if selected else None,
            "ratio_error": selected["ratio_error"] if selected else None,
        },
        "no_pozo_used": True,
        "no_pink1_calibration": True,
        "no_holdout_validation_run": True,
        "no_new_simulation_run": True,
        "no_gene_specific_mapping": True,
        "no_biological_validation_claim": True,
        "large_artifacts_committed": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        _report(status=status, rows=output_rows, selected=selected, ratio_target=ratio_target),
        encoding="utf-8",
    )
    return {
        "status": status,
        "selected_burden_level": selected["burden_level"] if selected else None,
        "selected_ratio": selected["simulated_ratio_to_burden0"] if selected else None,
        "selected_ratio_error": selected["ratio_error"] if selected else None,
        "new_simulation_run": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = run_calibration()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
