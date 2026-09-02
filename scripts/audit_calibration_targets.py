"""Audit literature targets without approving or changing scientific data."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COLUMNS = (
    "paper_id",
    "gene_model",
    "genotype",
    "age_days",
    "sex",
    "assay",
    "metric",
    "value",
    "unit",
    "variance_type",
    "variance",
    "sample_size",
    "figure_table",
    "doi_pmid",
    "review_status",
    "notes",
)
ALLOWED_STATUSES = {"pending", "approved", "rejected"}
ALLOWED_TARGET_STATISTICS = {
    "mean",
    "median",
    "se",
    "sem",
    "sd",
    "iqr",
    "range",
    "ci95",
}
UNCERTAINTY_STATISTICS = {"se", "sem", "sd", "iqr", "range", "ci95"}
CALIBRATION_ENDPOINTS = {
    "mean_planar_speed_mm_s": "mm/s",
    "median_planar_speed_mm_s": "mm/s",
    "distance_traveled_mm": "mm",
}
VALIDATION_ONLY_ENDPOINTS = {
    "activity_time_s": "s",
    "climbing_score": None,
    "dam_activity": None,
}
ALLOWED_SAMPLE_UNITS = {
    "animal",
    "fly",
    "independent_experiment",
    "independent_vial",
    "recording",
    "vial",
}
APPROVED_METADATA = (
    "paper_id",
    "gene_model",
    "genotype",
    "age_days",
    "sex",
    "assay",
    "metric",
    "value",
    "unit",
    "variance_type",
    "variance",
    "sample_size",
    "figure_table",
    "doi_pmid",
    "notes",
)
_REVIEWER = re.compile(r"(?:^|;)\s*reviewer=([^;]+)", re.IGNORECASE)
_REVIEW_DATE = re.compile(r"(?:^|;)\s*review_date=(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
_ALLOCATION = re.compile(r"(?:^|;)\s*allocation=(calibration|holdout)", re.IGNORECASE)
_ASSAY_TRANSFER = re.compile(
    r"(?:^|;)\s*assay_transfer=(allowed|validation_only|not_comparable)",
    re.IGNORECASE,
)
_SAMPLE_UNIT = re.compile(r"(?:^|;)\s*sample_unit=([a-z_]+)", re.IGNORECASE)
_CENTER_STATISTIC = re.compile(
    r"(?:^|;)\s*statistic=(mean|median|paper_reported_center)",
    re.IGNORECASE,
)


def _value(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def _issue(code: str, message: str, severity: str) -> dict[str, str]:
    return {"code": code, "message": message, "severity": severity}


def _statistic_tokens(value: str) -> set[str]:
    """Return recognized statistic tokens without inferring missing metadata."""

    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    aliases = {
        "standard_deviation": "sd",
        "standard_error": "se",
        "interquartile_range": "iqr",
    }
    for source, target in aliases.items():
        normalized = normalized.replace(source, target)
    return set(normalized.split("_")) & ALLOWED_TARGET_STATISTICS


def _audit_endpoint_policy(
    row: dict[str, str],
    *,
    status: str,
    severity: str,
    notes: str,
) -> list[dict[str, str]]:
    """Enforce endpoint, statistic, unit, and transfer compatibility."""

    issues: list[dict[str, str]] = []
    metric = _value(row, "metric").lower()
    unit = _value(row, "unit").lower()
    variance_type = _value(row, "variance_type")
    statistics = _statistic_tokens(variance_type)
    note_statistics = _statistic_tokens(notes)
    center_match = _CENTER_STATISTIC.search(notes)
    center = center_match.group(1).lower() if center_match else ""
    allocation_match = _ALLOCATION.search(notes)
    allocation = allocation_match.group(1).lower() if allocation_match else ""

    if variance_type and not statistics:
        issues.append(
            _issue(
                "INVALID_VARIANCE_TYPE",
                "variance_type phai ghi ro mean, median, SE, SEM, SD, IQR, range hoac CI95.",
                severity,
            )
        )
    if variance_type and not (statistics & UNCERTAINTY_STATISTICS):
        issues.append(
            _issue(
                "MISSING_UNCERTAINTY_STATISTIC",
                "variance_type phai ghi mot uncertainty type: SE, SEM, SD, IQR, range hoac CI95.",
                severity,
            )
        )

    if metric in VALIDATION_ONLY_ENDPOINTS:
        issues.append(
            _issue(
                "VALIDATION_ONLY_ENDPOINT",
                f"{metric} chi duoc dung cho validation cho den khi assay tuong ung duoc implement.",
                severity,
            )
        )
    elif metric not in CALIBRATION_ENDPOINTS:
        issues.append(
            _issue(
                "UNSUPPORTED_ENDPOINT",
                f"Endpoint {metric or '<blank>'} chua nam trong target policy.",
                severity,
            )
        )
    else:
        expected_unit = CALIBRATION_ENDPOINTS[metric]
        if unit and unit != expected_unit:
            issues.append(
                _issue(
                    "ENDPOINT_UNIT_MISMATCH",
                    f"{metric} phai dung don vi {expected_unit}.",
                    severity,
                )
            )

    if metric.startswith("mean_"):
        if "median" in statistics or "median" in note_statistics or center == "median":
            issues.append(
                _issue(
                    "STATISTIC_MISMATCH",
                    "Mean endpoint khong duoc dung gia tri trung tam la median.",
                    severity,
                )
            )
    elif metric.startswith("median_"):
        if not ({"iqr", "range"} & statistics):
            issues.append(
                _issue(
                    "MEDIAN_SPREAD_REQUIRED",
                    "Median endpoint phai co numeric IQR hoac range duoc paper bao cao.",
                    severity,
                )
            )
    elif metric == "distance_traveled_mm":
        if not center:
            issues.append(
                _issue(
                    "MISSING_CENTER_STATISTIC",
                    "Distance target phai ghi statistic=mean, statistic=median hoac statistic=paper_reported_center trong notes.",
                    severity,
                )
            )
        elif center in {"median", "paper_reported_center"} and not ({"iqr", "range"} & statistics):
            issues.append(
                _issue(
                    "MEDIAN_SPREAD_REQUIRED",
                    "Median/paper-reported distance target phai co numeric IQR hoac range.",
                    severity,
                )
            )
        elif center == "paper_reported_center" and allocation != "holdout":
            issues.append(
                _issue(
                    "PAPER_CENTER_HOLDOUT_ONLY",
                    "paper_reported_center chi duoc dung cho distance holdout.",
                    severity,
                )
            )

    # A paper-reported center is a provenance-preserving holdout value. It is
    # never a substitute for a calibration statistic, even when the endpoint
    # itself is otherwise listed in the policy.
    if center == "paper_reported_center" and allocation == "calibration":
        issues.append(
            _issue(
                "PAPER_CENTER_HOLDOUT_ONLY",
                "paper_reported_center chi duoc dung cho holdout, khong duoc dung cho calibration.",
                "error" if status == "approved" else severity,
            )
        )

    if metric == "distance_traveled_mm" and allocation == "calibration":
        issues.append(
            _issue(
                "DISTANCE_HOLDOUT_ONLY",
                "distance_traveled_mm chi duoc dung lam holdout endpoint, khong duoc dung de calibration speed.",
                "error" if status == "approved" else severity,
            )
        )

    assay_transfer = _ASSAY_TRANSFER.search(notes)
    sample_unit = _SAMPLE_UNIT.search(notes)
    if status == "approved":
        if assay_transfer is None:
            issues.append(
                _issue(
                    "MISSING_ASSAY_TRANSFER",
                    "Approved target phai ghi assay_transfer=allowed trong notes.",
                    "error",
                )
            )
        elif assay_transfer.group(1).lower() != "allowed":
            issues.append(
                _issue(
                    "ASSAY_TRANSFER_NOT_ALLOWED",
                    "Approved calibration/holdout target phai co assay_transfer=allowed.",
                    "error",
                )
            )
        if sample_unit is None:
            issues.append(
                _issue(
                    "MISSING_SAMPLE_UNIT",
                    "Approved target phai ghi sample_unit trong notes.",
                    "error",
                )
            )
        elif sample_unit.group(1).lower() not in ALLOWED_SAMPLE_UNITS:
            issues.append(
                _issue(
                    "INVALID_SAMPLE_UNIT",
                    "sample_unit khong nam trong target policy.",
                    "error",
                )
            )
    return issues


def _audit_numeric_field(
    row: dict[str, str],
    field: str,
    *,
    severity: str,
    integer: bool = False,
    positive: bool = False,
    nonnegative: bool = False,
) -> list[dict[str, str]]:
    """Validate numeric metadata instead of accepting placeholders as data."""

    raw = _value(row, field)
    if not raw:
        return []
    try:
        value = float(raw)
    except ValueError:
        return [_issue(f"INVALID_{field.upper()}", f"{field} phai la so.", severity)]
    if not math.isfinite(value):
        return [_issue(f"NONFINITE_{field.upper()}", f"{field} phai huu han.", severity)]
    if positive and value <= 0:
        return [_issue(f"INVALID_{field.upper()}", f"{field} phai lon hon 0.", severity)]
    if nonnegative and value < 0:
        return [_issue(f"INVALID_{field.upper()}", f"{field} khong duoc am.", severity)]
    if integer and value != int(value):
        return [_issue(f"INVALID_{field.upper()}", f"{field} phai la so nguyen.", severity)]
    return []


def _audit_row(row_number: int, row: dict[str, str]) -> dict[str, Any]:
    status = _value(row, "review_status").lower()
    severity = "error" if status == "approved" else "warning"
    issues: list[dict[str, str]] = []

    if status not in ALLOWED_STATUSES:
        issues.append(_issue("INVALID_REVIEW_STATUS", "review_status khong hop le.", "error"))
        status = "invalid"

    for field in APPROVED_METADATA:
        if not _value(row, field):
            issues.append(_issue(f"MISSING_{field.upper()}", f"Thieu truong {field}.", severity))

    raw_value = _value(row, "value")
    numeric_value: float | None = None
    if raw_value:
        try:
            numeric_value = float(raw_value)
        except ValueError:
            issues.append(_issue("INVALID_VALUE", "value phai la so.", "error"))
        else:
            if not math.isfinite(numeric_value):
                issues.append(_issue("NONFINITE_VALUE", "value phai huu han.", "error"))

    notes = _value(row, "notes")
    issues.extend(_audit_numeric_field(row, "sample_size", severity=severity, integer=True, positive=True))
    issues.extend(_audit_numeric_field(row, "variance", severity=severity, nonnegative=True))
    issues.extend(_audit_endpoint_policy(row, status=status, severity=severity, notes=notes))
    reviewer = _REVIEWER.search(notes)
    review_date = _REVIEW_DATE.search(notes)
    allocation = _ALLOCATION.search(notes)
    assay_transfer = _ASSAY_TRANSFER.search(notes)
    sample_unit = _SAMPLE_UNIT.search(notes)
    if status == "approved":
        if reviewer is None:
            issues.append(_issue("MISSING_REVIEWER", "Approved target phai ghi reviewer trong notes.", "error"))
        if review_date is None:
            issues.append(_issue("MISSING_REVIEW_DATE", "Approved target phai ghi review_date trong notes.", "error"))
        elif _invalid_date(review_date.group(1)):
            issues.append(_issue("INVALID_REVIEW_DATE", "review_date phai co dang YYYY-MM-DD hop le.", "error"))
        if allocation is None:
            issues.append(_issue("MISSING_ALLOCATION", "Approved target phai ghi allocation=calibration|holdout.", "error"))

    hard_errors = [item for item in issues if item["severity"] == "error"]
    eligible = status == "approved" and not hard_errors and numeric_value is not None
    return {
        "row_number": row_number,
        "paper_id": _value(row, "paper_id"),
        "review_status": status,
        "metric": _value(row, "metric"),
        "value": numeric_value,
        "unit": _value(row, "unit"),
        "allocation": allocation.group(1).lower() if allocation else "",
        "assay_transfer": assay_transfer.group(1).lower() if assay_transfer else "",
        "sample_unit": sample_unit.group(1).lower() if sample_unit else "",
        "eligible": eligible,
        "issues": issues,
    }


def _invalid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return True
    return False


def audit_targets(path: Path) -> dict[str, Any]:
    """Return a readiness audit; this function never mutates the target file."""

    if not path.is_file():
        return {
            "status": "WAITING_TARGET_DATA",
            "source": str(path),
            "counts": {},
            "blockers": [f"Khong tim thay target file: {path}"],
            "rows": [],
        }

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in columns]
        if missing_columns:
            return {
                "status": "INVALID_TARGET_SCHEMA",
                "source": str(path),
                "counts": {},
                "blockers": [f"Thieu cot: {', '.join(missing_columns)}"],
                "rows": [],
            }
        source_rows = list(reader)

    audited_rows = [_audit_row(index, row) for index, row in enumerate(source_rows, start=2)]
    duplicate_groups: dict[tuple[str, str, str, str], list[int]] = {}
    for row_number, row in enumerate(source_rows, start=2):
        key = (_value(row, "paper_id"), _value(row, "metric"), _value(row, "unit"), _value(row, "value"))
        if all(key):
            duplicate_groups.setdefault(key, []).append(row_number)
    blockers: list[str] = []
    for key, row_numbers in duplicate_groups.items():
        if len(row_numbers) > 1:
            message = f"Target trung lap {key[0]}/{key[1]} tai dong {row_numbers}."
            blockers.append(message)
            for audited in audited_rows:
                if audited["row_number"] in row_numbers:
                    audited["issues"].append(_issue("DUPLICATE_TARGET", message, "error"))
                    audited["eligible"] = False

    status_counts = {status: 0 for status in (*sorted(ALLOWED_STATUSES), "invalid")}
    for row in audited_rows:
        status_counts[row["review_status"]] = status_counts.get(row["review_status"], 0) + 1
        for item in row["issues"]:
            if item["severity"] == "error":
                blockers.append(f"Dong {row['row_number']}: {item['message']}")
    eligible = [row for row in audited_rows if row["eligible"]]
    allocation_counts = {"calibration": 0, "holdout": 0}
    for row in eligible:
        allocation_counts[row["allocation"]] += 1
    if not eligible:
        blockers.append("Chua co target approved du metadata va provenance de calibration.")
        status = "WAITING_TARGET_DATA"
    elif not all(allocation_counts.values()):
        blockers.append("Can co it nhat mot target calibration va mot target holdout.")
        status = "WAITING_TARGET_DATA"
    else:
        status = "READY_FOR_CALIBRATION"
    return {
        "status": status,
        "source": str(path),
        "counts": {
            "rows": len(audited_rows),
            "review_status": status_counts,
            "eligible_approved": len(eligible),
            "allocation": allocation_counts,
        },
        "blockers": sorted(set(blockers)),
        "rows": audited_rows,
        "target_policy": {
            "calibration_endpoints": sorted(CALIBRATION_ENDPOINTS),
            "validation_only_endpoints": sorted(VALIDATION_ONLY_ENDPOINTS),
            "allowed_statistics": sorted(ALLOWED_TARGET_STATISTICS),
        },
        "scientific_scope": "Audit provenance va readiness; khong tu phe duyet target, khong chay simulation.",
    }


def _write_outputs(audit: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": "calibration-target-audit-1", "created_at_utc": datetime.now(UTC).isoformat(), **audit}
    (output / "target_audit.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    eligible = [row for row in audit["rows"] if row["eligible"]]
    manifest = {
        "schema_version": "calibration-target-manifest-1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": audit["status"],
        "ready_for_calibration": audit["status"] == "READY_FOR_CALIBRATION",
        "source": audit["source"],
        "calibration": [row for row in eligible if row["allocation"] == "calibration"],
        "holdout": [row for row in eligible if row["allocation"] == "holdout"],
        "scientific_scope": "Manifest readiness; khong phe duyet target va khong chay simulation.",
    }
    (output / "calibration_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with (output / "target_audit.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "row_number",
                "paper_id",
                "review_status",
                "metric",
                "value",
                "unit",
                "allocation",
                "assay_transfer",
                "sample_unit",
                "eligible",
                "issues",
            ],
        )
        writer.writeheader()
        for row in audit["rows"]:
            writer.writerow({**row, "issues": "; ".join(item["code"] for item in row["issues"])})
    counts = audit.get("counts", {})
    lines = [
        "# Calibration target audit",
        "",
        f"**Trang thai:** `{audit['status']}`",
        "",
        "Audit nay chi kiem tra provenance va readiness; khong phe duyet target va khong tao du lieu khoa hoc.",
        "",
        f"- Nguon: `{audit['source']}`",
        f"- So dong: `{counts.get('rows', 0)}`",
        f"- Approved du dieu kien: `{counts.get('eligible_approved', 0)}`",
        f"- Phan bo: `{counts.get('allocation', {})}`",
        "",
        "## Blockers",
        "",
    ]
    blockers = audit.get("blockers", [])
    lines.extend(f"- {item}" for item in blockers or ["Khong co."])
    lines.extend(
        [
            "",
            "## Quy tac de sang calibration",
            "",
            "Target approved phai co metadata, provenance, `reviewer=...`, `review_date=YYYY-MM-DD`, `allocation=calibration|holdout`, `assay_transfer=allowed` va `sample_unit=...` trong notes.",
            "Khong dung cung mot target cho ca calibration va holdout.",
        ]
    )
    (output / "target_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    policy_lines = [
        "# Báo cáo nâng cấp target policy và calibration readiness",
        "",
        f"**Trạng thái:** `{audit['status']}`",
        "",
        "Repository chưa đạt `READY_FOR_CALIBRATION` vì chưa có target approved đủ metadata, uncertainty số học, sample size số học, reviewer, review date, allocation và assay transfer được phép.",
        "",
        "## Dữ liệu còn thiếu chính xác",
        "",
        "- Riemensperger: cần metric median riêng, numeric IQR/range và quyết định assay transfer; không đổi median thành mean.",
        "- Pokrzywa: cần numeric SE, mốc tuổi endpoint chính xác, numeric sample size theo đúng unit of analysis và `assay_transfer=allowed`.",
        "- Pozo: cần xác nhận spread, metric `distance_traveled_mm` trong output simulation và assay transfer riêng cho distance.",
        "- Hwang/Godena: climbing chỉ validation-only cho đến khi climbing assay được implement.",
        "- Dumitrescu: DAM activity không được chuyển thành walking speed.",
        "",
        "## Ứng viên gần nhất",
        "",
        "- Calibration: Pokrzywa alpha-synuclein Day 21 speed, nếu exact SE và unit of analysis được xác nhận.",
        "- Holdout: Pozo Pink1B9 Day 28 distance, nếu spread policy và simulation distance endpoint được xác nhận độc lập.",
        "",
        "Hai nhận định trên chỉ là xếp hạng readiness; không phê duyệt target và không phải biological validation.",
        "",
        "## Blocker từ audit",
        "",
    ]
    policy_lines.extend(f"- {item}" for item in blockers or ["Khong co."])
    (output / "target_policy_upgrade_report.md").write_text(
        "\n".join(policy_lines) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", type=Path, default=ROOT / "calibration_targets" / "targets.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "calibration_readiness")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        audit = audit_targets(args.targets.resolve())
        _write_outputs(audit, args.output.resolve())
    except (OSError, csv.Error, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Status: {audit['status']}")
    print(f"Audit: {args.output.resolve() / 'target_audit.json'}")
    return 0 if audit["status"] in {"WAITING_TARGET_DATA", "READY_FOR_CALIBRATION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
