"""Create the Gate 14A Pozo holdout protocol without running experiments.

The script reads reviewed repository metadata and writes a small, auditable
protocol package. It never calls the FlyGym runner, changes calibration
parameters, or treats the Pozo distance endpoint as speed.
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
import re
import subprocess
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
TARGETS = Path("calibration_targets/targets.csv")
CONTROL_SOURCE = Path("research/paper_review/full_target_survey_matrix.csv")
GATE13B_CONFIG = Path(
    "experiments/gate_13b_chen_ratio_calibration/configs/"
    "calibrated_alpha_synuclein_proxy.yaml"
)
GATE13C_MANIFEST = Path(
    "experiments/gate_13c_calibrated_confirmation/manifests/"
    "calibrated_confirmation_manifest.json"
)
PINK1_CONFIG = Path(
    "experiments/gate_12c_computational_proxy_configs/configs/"
    "pink1_proxy_condition.yaml"
)
POZO_SIGNOFF = Path("research/paper_review/pozo_distance_holdout_signoff.md")

OUTPUT_ROOT = Path("experiments/gate_14a_pozo_holdout_protocol")
CONFIG = OUTPUT_ROOT / "configs/pozo_holdout_protocol.yaml"
SUMMARY = OUTPUT_ROOT / "results/pozo_holdout_protocol_summary.csv"
MANIFEST = OUTPUT_ROOT / "manifests/pozo_holdout_protocol_manifest.json"
REPORT = Path("docs/holdout/gate_14a_pozo_holdout_protocol_report.md")

READY = "READY_FOR_GATE_14B_POZO_RATIO_HOLDOUT"
REVIEW_REQUIRED = "POZO_HOLDOUT_PROTOCOL_REVIEW_REQUIRED"
BLOCKED = "POZO_HOLDOUT_PROTOCOL_BLOCKED"

SUMMARY_FIELDS = (
    "source",
    "model",
    "simulation_condition",
    "metric",
    "disease_value_mm",
    "control_value_mm",
    "target_ratio",
    "spread_reported",
    "spread_policy",
    "n",
    "allocation",
    "primary_endpoint",
    "absolute_distance_role",
    "locked_parameter_name",
    "locked_parameter_value",
    "planned_gate_14b_runs",
    "status",
    "notes",
)

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


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
    if number is None:
        return str(value)
    return f"{number:.12g}"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _git_commit(root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "NOT_AVAILABLE"


def _parse_notes(value: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in value.split(";"):
        if "=" not in item:
            continue
        key, item_value = item.split("=", 1)
        parsed[key.strip()] = item_value.strip()
    return parsed


def _rooted(root: Path, relative: Path) -> Path:
    return root / relative


def _find_pozo_target(rows: list[dict[str, str]]) -> tuple[dict[str, str] | None, list[str]]:
    matches = [
        row
        for row in rows
        if row.get("paper_id") == "pozo_2022_pink1_serotonin"
        and row.get("metric") == "distance_traveled_mm"
    ]
    if len(matches) != 1:
        return None, ["Pozo holdout target khong duy nhat trong targets.csv."]

    row = matches[0]
    notes = _parse_notes(row.get("notes", ""))
    required = (
        row.get("gene_model") == "pink1",
        row.get("genotype") == "Pink1B9",
        row.get("unit") == "mm",
        _number(row.get("value")) == 62.091,
        row.get("variance_type") == "IQR_with_min_max_ranges_reported",
        _number(row.get("variance")) == 61.288,
        _number(row.get("sample_size")) == 21,
        row.get("review_status", "").strip().lower() == "approved",
        notes.get("allocation") == "holdout",
        notes.get("assay_transfer") == "allowed",
        notes.get("sample_unit") == "fly",
        notes.get("not_speed_target", "").lower() == "true",
        bool(notes.get("provenance")),
        bool(notes.get("reviewer")) and bool(_DATE.match(notes.get("review_date", ""))),
    )
    if not all(required):
        return None, [
            "Pozo target chua du metadata approved, provenance, assay transfer "
            "hoac quy tac distance holdout."
        ]
    return row, []


def _find_control(rows: list[dict[str, str]]) -> tuple[dict[str, str] | None, list[str]]:
    matches = [
        row
        for row in rows
        if row.get("paper_id") == "pozo_2022_pink1_serotonin"
        and row.get("metric") == "distance_traveled_mm"
        and _number(row.get("value")) == 323.326
        and row.get("figure_table") == "Figure 3B"
    ]
    if len(matches) != 1:
        return None, [
            "Khong xac minh duoc matched control Pozo 323.326 mm tu survey matrix."
        ]
    row = matches[0]
    provenance = row.get("provenance", "").strip()
    if not provenance or not row.get("doi_pmid") or _number(row.get("sample_size")) is None:
        return None, ["Matched control co nhung thieu provenance/metadata bat buoc."]
    return row, []


def _status_for_checks(
    *,
    pozo_target_valid: bool,
    locked_parameter_valid: bool,
    gate13c_valid: bool,
    pink1_config_valid: bool,
    control_provenance_valid: bool,
) -> str:
    if not all((pozo_target_valid, locked_parameter_valid, gate13c_valid, pink1_config_valid)):
        return BLOCKED
    return READY if control_provenance_valid else REVIEW_REQUIRED


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _fmt(row.get(field, "")) for field in SUMMARY_FIELDS})


def _write_config(
    path: Path,
    *,
    status: str,
    ratio: float | None,
    control_value: float | None,
) -> None:
    control_text = _fmt(control_value) if control_value is not None else "NOT_AVAILABLE"
    ratio_text = _fmt(ratio) if ratio is not None else "NOT_AVAILABLE"
    endpoint = "distance_ratio_to_control" if ratio is not None else "REVIEW_REQUIRED"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""schema_version: gate-14a-pozo-holdout-protocol-v1
status: {status}

holdout_scope:
  source: Pozo 2022
  model: Pink1B9
  simulation_condition: pink1
  proxy_scope: organism_level_proxy
  gene_specific_mapping: false
  biological_validation_claim: false

locked_calibration:
  source: experiments/gate_13b_chen_ratio_calibration/configs/calibrated_alpha_synuclein_proxy.yaml
  parameter_name: proxy_burden_level
  selected_value: 0.5
  no_parameter_reselection: true
  no_pozo_tuning: true

pozo_target:
  metric: distance_traveled_mm
  disease_value_mm: 62.091
  spread_reported: 61.288
  spread_policy: kept_as_reported_not_converted_to_sd_or_se
  n: 21
  allocation: holdout
  not_speed_target: true
  absolute_distance_role: reference_only
  matched_control_value_mm: {control_text}
  disease_control_ratio: {ratio_text}

holdout_endpoint_decision:
  preferred_endpoint: {endpoint}
  absolute_distance_role: reference_only
  reason: "A distance ratio is preferred when the matched Pozo control provenance is available; absolute distance remains reference-only because assay duration and runtime scale are not assumed identical."

gate_14b_design:
  condition_id: pink1
  control_burden_level: 0.0
  holdout_burden_level: 0.5
  seeds: [12, 13, 14, 15, 16, 17]
  planned_runs: 12
  no_tuning: true
  no_calibration: true
  no_holdout_parameter_search: true

forbidden:
  use_pozo_for_calibration: true
  parameter_reselection: true
  distance_to_speed_conversion: true
  spread_to_se_conversion: true
  alpha_synuclein_recalibration: true
  gene_specific_claim: true
  biological_validation_claim: true
"""
    path.write_text(text, encoding="utf-8")


def _write_report(
    path: Path,
    *,
    status: str,
    control: dict[str, str] | None,
    blockers: list[str],
) -> None:
    control_section = (
        "- Control distance: 323.326 mm.\n"
        "- Disease/control ratio: 0.19203837612811836.\n"
        "- Primary endpoint Gate 14B: `distance_ratio_to_control`.\n"
        "- Provenance: dòng control cùng Pozo Figure 3B trong `full_target_survey_matrix.csv`."
        if control is not None
        else "- Control matched chưa đủ provenance; ratio không được tạo hoặc sử dụng."
    )
    blocker_section = "\n".join(f"- {item}" for item in blockers) or "- Không có blocker dữ liệu cho việc khóa protocol."
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Gate 14A - Pozo Holdout Protocol

## Mục tiêu

Gate 14A khóa protocol cho Pozo 2022 holdout trước khi có thể xem xét chạy
Gate 14B. Gate này chỉ tạo protocol và artifact provenance; không chạy
simulation, holdout validation hoặc calibration.

## Trạng thái đầu vào

- Gate 13B: `CHEN_RATIO_CALIBRATION_PASS`.
- Gate 13C: `CHEN_CALIBRATED_CONFIRMATION_PASS`.
- Burden đã khóa: `proxy_burden_level = 0.5`.
- Audit target: `READY_FOR_CALIBRATION`.
- PINK1 hiện là `organism_level_proxy`, không có gene-specific neuron mapping.

## Pozo target

- Model: `Pink1B9`.
- Metric: `distance_traveled_mm`.
- Giá trị bệnh: `62.091 mm`.
- Spread: `61.288`, giữ nguyên dạng paper-reported IQR/min-max; không đổi thành SD/SE.
- Sample size: `n=21 fly`.
- Allocation: holdout only.
- Đây không phải speed target và không được chuyển distance thành speed.

## Endpoint holdout

{control_section}

Absolute distance của paper chỉ là reference-only vì thời lượng assay và scale
runtime không được giả định là tương đương trực tiếp. Pozo không được dùng để
tune hoặc chọn lại `proxy_burden_level`.

## Thiết kế Gate 14B dự kiến

- Condition: `pink1` organism-level proxy.
- Control burden: `0.0`.
- Holdout burden đã khóa: `0.5`.
- Seeds: `12, 13, 14, 15, 16, 17`.
- Planned runs: `12`.
- Không tuning, không calibration, không parameter search trên holdout.

## Kiểm tra blocker

{blocker_section}

## Ranh giới khoa học

Đây là protocol cho computational locomotion holdout. Nó không phải biological
Parkinson validation, không phải gene-specific PINK1 validation, không phải
chẩn đoán lâm sàng, không phải drug efficacy validation và không thay thế thí
nghiệm wet-lab. Gate 14A không chạy simulation và không tạo disease metrics.

## Final status

`{status}`
"""
    path.write_text(text, encoding="utf-8")


def build_protocol(root: Path = ROOT) -> dict[str, Any]:
    targets_path = _rooted(root, TARGETS)
    control_path = _rooted(root, CONTROL_SOURCE)
    gate13b_path = _rooted(root, GATE13B_CONFIG)
    gate13c_path = _rooted(root, GATE13C_MANIFEST)
    pink1_path = _rooted(root, PINK1_CONFIG)
    pozo_signoff_path = _rooted(root, POZO_SIGNOFF)

    blockers: list[str] = []
    target_rows = _read_csv(targets_path) if targets_path.is_file() else []
    target, target_blockers = _find_pozo_target(target_rows)
    blockers.extend(target_blockers)

    survey_rows = _read_csv(control_path) if control_path.is_file() else []
    control, control_blockers = _find_control(survey_rows)
    if not control_path.is_file():
        control_blockers = ["Khong tim thay full_target_survey_matrix.csv de xac minh control."]
    blockers.extend(control_blockers)

    gate13b = _read_yaml(gate13b_path) if gate13b_path.is_file() else {}
    selected = gate13b.get("selected_parameter", {})
    locked_parameter_valid = (
        selected.get("parameter_name") == "proxy_burden_level"
        and _number(selected.get("selected_value")) == 0.5
    )
    if not locked_parameter_valid:
        blockers.append("Gate 13B khong xac minh duoc locked proxy_burden_level=0.5.")

    gate13c = _read_json(gate13c_path) if gate13c_path.is_file() else {}
    gate13c_valid = gate13c.get("status") == "CHEN_CALIBRATED_CONFIRMATION_PASS" and (
        _number(gate13c.get("calibrated_burden_level")) == 0.5
    )
    if not gate13c_valid:
        blockers.append("Gate 13C khong o trang thai confirmation pass voi burden 0.5.")

    pink1 = _read_yaml(pink1_path) if pink1_path.is_file() else {}
    pink1_target_definition = pink1.get("target_definition", {})
    if not isinstance(pink1_target_definition, dict):
        pink1_target_definition = {}
    pink1_valid = (
        pink1.get("condition_id") == "pink1"
        and pink1.get("scope") == "organism_level_proxy"
        and pink1_target_definition.get("gene_specific_mapping") is False
    )
    if not pink1_valid:
        blockers.append("PINK1 config khong xac minh organism_level_proxy va gene_specific_mapping=false.")

    status = _status_for_checks(
        pozo_target_valid=target is not None,
        locked_parameter_valid=locked_parameter_valid,
        gate13c_valid=gate13c_valid,
        pink1_config_valid=pink1_valid,
        control_provenance_valid=control is not None,
    )
    if status == READY:
        blockers = []

    disease_value = _number(target.get("value")) if target else 62.091
    control_value = _number(control.get("value")) if control else None
    ratio = disease_value / control_value if disease_value is not None and control_value else None

    output_root = _rooted(root, OUTPUT_ROOT)
    config_path = _rooted(root, CONFIG)
    summary_path = _rooted(root, SUMMARY)
    manifest_path = _rooted(root, MANIFEST)
    report_path = _rooted(root, REPORT)
    _write_config(config_path, status=status, ratio=ratio, control_value=control_value)
    summary_row = {
        "source": "Pozo 2022",
        "model": "Pink1B9",
        "simulation_condition": "pink1",
        "metric": "distance_traveled_mm",
        "disease_value_mm": disease_value,
        "control_value_mm": control_value if control_value is not None else "NOT_AVAILABLE",
        "target_ratio": ratio if ratio is not None else "NOT_AVAILABLE",
        "spread_reported": 61.288,
        "spread_policy": "kept_as_reported_IQR_minmax_not_SD_SE",
        "n": 21,
        "allocation": "holdout",
        "primary_endpoint": "distance_ratio_to_control" if ratio is not None else "REVIEW_REQUIRED",
        "absolute_distance_role": "reference_only",
        "locked_parameter_name": "proxy_burden_level",
        "locked_parameter_value": 0.5,
        "planned_gate_14b_runs": 12,
        "status": status,
        "notes": "No Pozo tuning; no distance-to-speed conversion; no simulation in Gate 14A.",
    }
    _write_csv(summary_path, [summary_row])
    _write_report(report_path, status=status, control=control, blockers=blockers)

    source_paths = [TARGETS, GATE13B_CONFIG, GATE13C_MANIFEST, PINK1_CONFIG, CONTROL_SOURCE, POZO_SIGNOFF]
    source_records = [
        {"path": str(path).replace("\\", "/"), "present": _rooted(root, path).is_file(), "sha256": _sha256(_rooted(root, path))}
        for path in source_paths
    ]
    manifest = {
        "schema_version": "gate-14a-pozo-holdout-protocol-manifest-v1",
        "status": status,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(root),
        "python_version": platform.python_version(),
        "source_files": [str(path).replace("\\", "/") for path in source_paths],
        "source_file_records": source_records,
        "pozo_target": {
            "paper_id": "pozo_2022_pink1_serotonin",
            "metric": "distance_traveled_mm",
            "disease_value_mm": disease_value,
            "spread_reported": 61.288,
            "spread_policy": "kept_as_reported_not_converted_to_sd_or_se",
            "n": 21,
            "allocation": "holdout",
            "not_speed_target": True,
            "provenance": _parse_notes(target.get("notes", "")).get("provenance", "") if target else "NOT_AVAILABLE",
        },
        "matched_control": {
            "available": control is not None,
            "metric": control.get("metric") if control else "distance_traveled_mm",
            "value_mm": control_value if control_value is not None else "NOT_AVAILABLE",
            "sample_size": _number(control.get("sample_size")) if control else "NOT_AVAILABLE",
            "figure_table": control.get("figure_table") if control else "NOT_AVAILABLE",
            "provenance": control.get("provenance") if control else "NOT_AVAILABLE",
            "source_file": str(CONTROL_SOURCE).replace("\\", "/"),
            "target_ratio": ratio if ratio is not None else "NOT_AVAILABLE",
        },
        "locked_parameter": {
            "parameter_name": "proxy_burden_level",
            "selected_value": 0.5,
            "source": str(GATE13B_CONFIG).replace("\\", "/"),
        },
        "planned_gate_14b": {
            "condition_id": "pink1",
            "seeds": [12, 13, 14, 15, 16, 17],
            "planned_runs": 12,
            "control_burden_level": 0.0,
            "holdout_burden_level": 0.5,
        },
        "no_simulation_run": True,
        "no_calibration_run": True,
        "no_holdout_validation_run": True,
        "no_pozo_tuning": True,
        "no_parameter_reselection": True,
        "no_distance_to_speed_conversion": True,
        "no_spread_to_se_conversion": True,
        "no_gene_specific_mapping": True,
        "no_biological_validation_claim": True,
        "large_artifacts_committed": False,
        "output_sha256": {
            "config": _sha256(config_path),
            "summary": _sha256(summary_path),
            "report": _sha256(report_path),
        },
        "scientific_boundary": "Computational locomotion holdout protocol only; not biological Parkinson validation.",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root")
    args = parser.parse_args(argv)
    manifest = build_protocol(args.root.resolve())
    print(f"Status: {manifest['status']}")
    print(f"Protocol: {args.root.resolve() / MANIFEST}")
    print("No simulation, calibration, or holdout validation was run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
