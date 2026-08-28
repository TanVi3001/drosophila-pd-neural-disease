"""Evaluate an approved calibration/holdout split without fitting or fabricating data."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from drosophila_pd_neural.calibration import compute_loss
from scripts.audit_calibration_targets import audit_targets


def _read_metrics(path: Path) -> dict[str, float]:
    source = path / "metrics.json" if path.is_dir() else path
    document = json.loads(source.read_text(encoding="utf-8"))
    values = document.get("scalar_metrics", document)
    if not isinstance(values, dict):
        return {}
    result: dict[str, float] = {}
    for key, value in values.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            result[str(key)] = float(value)
    return result


def _validate_observed_metrics(observed: dict[str, float], targets: dict[str, float]) -> str | None:
    invalid = sorted(key for key, value in observed.items() if not math.isfinite(value))
    if invalid:
        return f"Observed metrics chua gia tri huu han: {', '.join(invalid)}."
    missing = sorted(set(targets) - set(observed))
    if missing:
        return f"Observed metrics thieu target metrics: {', '.join(missing)}."
    return None


def _target_values(rows: list[dict[str, Any]], allocation: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for row in rows:
        if row["allocation"] != allocation or not row["eligible"]:
            continue
        metric = str(row["metric"])
        value = row["value"]
        if metric in values:
            raise ValueError(f"Trung metric trong split {allocation}: {metric}")
        if not isinstance(value, (int, float)):
            raise ValueError(f"Target {metric} trong split {allocation} khong phai so.")
        values[metric] = float(value)
    return values


def _write_csv(path: Path, observed: dict[str, float], targets: dict[str, float]) -> list[dict[str, object]]:
    rows = [
        {
            "metric": metric,
            "observed": observed[metric],
            "target": targets[metric],
            "delta": observed[metric] - targets[metric],
        }
        for metric in sorted(set(observed) & set(targets))
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "observed", "target", "delta"])
        writer.writeheader()
        writer.writerows(rows)
    return rows


def _write_result(output: Path, status: str, message: str, **extra: object) -> None:
    payload = {
        "schema_version": "calibration-holdout-evaluation-1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "message": message,
        "scientific_scope": "Danh gia metric computational; khong phai biological Parkinson validation.",
        **extra,
    }
    (output / "evaluation.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Calibration va holdout evaluation",
        "",
        f"**Trang thai:** `{status}`",
        "",
        message,
        "",
        "Day la danh gia tren target da duoc review; script khong toi uu tham so va khong tao du lieu.",
    ]
    (output / "evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate(metrics: Path, targets: Path, output: Path) -> str:
    output.mkdir(parents=True, exist_ok=True)
    audit = audit_targets(targets)
    if audit["status"] != "READY_FOR_CALIBRATION":
        _write_result(
            output,
            "WAITING_TARGET_DATA",
            "Chua co calibration target va holdout target approved du metadata/provenance; khong tinh loss.",
            target_audit=audit,
        )
        for name in ("calibration_metrics.csv", "holdout_metrics.csv"):
            _write_csv(output / name, {}, {})
        return "WAITING_TARGET_DATA"

    observed = _read_metrics(metrics)
    results: dict[str, Any] = {}
    for allocation in ("calibration", "holdout"):
        target_values = _target_values(audit["rows"], allocation)
        if not target_values:
            _write_result(output, "WAITING_TARGET_DATA", f"Split {allocation} rong.", target_audit=audit)
            return "WAITING_TARGET_DATA"
        validation_error = _validate_observed_metrics(observed, target_values)
        if validation_error:
            _write_result(
                output,
                "INSUFFICIENT_METRICS",
                validation_error,
                target_audit=audit,
                observed_metrics=observed,
                allocation=allocation,
            )
            return "INSUFFICIENT_METRICS"
        try:
            loss = compute_loss(observed, target_values)
        except (ValueError, KeyError) as exc:
            status = "INSUFFICIENT_METRICS"
            _write_result(output, status, str(exc), target_audit=audit, observed_metrics=observed)
            return status
        rows = _write_csv(output / f"{allocation}_metrics.csv", observed, target_values)
        results[allocation] = {"loss": loss, "row_count": len(rows), "target_metrics": target_values}

    _write_result(output, "PASS", "Calibration split va holdout split da duoc danh gia tach biet.", results=results)
    return "PASS"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        status = evaluate(args.metrics.resolve(), args.targets.resolve(), args.output.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Status: {status}")
    return 0 if status in {"PASS", "WAITING_TARGET_DATA", "INSUFFICIENT_METRICS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
