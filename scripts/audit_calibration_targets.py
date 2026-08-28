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


def _value(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def _issue(code: str, message: str, severity: str) -> dict[str, str]:
    return {"code": code, "message": message, "severity": severity}


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
    if "median" in notes.lower() and _value(row, "metric").lower().startswith("mean_"):
        issues.append(
            _issue(
                "STATISTIC_MISMATCH",
                "Paper ghi median nhung metric dang dat ten mean_; can xac nhan phep quy doi.",
                severity,
            )
        )
    reviewer = _REVIEWER.search(notes)
    review_date = _REVIEW_DATE.search(notes)
    allocation = _ALLOCATION.search(notes)
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
            fieldnames=["row_number", "paper_id", "review_status", "metric", "value", "unit", "allocation", "eligible", "issues"],
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
            "Target approved phai co metadata, provenance, `reviewer=...`, `review_date=YYYY-MM-DD` va `allocation=calibration` hoac `allocation=holdout` trong notes.",
            "Khong dung cung mot target cho ca calibration va holdout.",
        ]
    )
    (output / "target_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
