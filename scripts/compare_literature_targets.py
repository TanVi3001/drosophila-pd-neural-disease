"""Doi chieu metrics that voi literature target da duoc review, khong tu dien target."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Sequence

from drosophila_pd_neural.calibration import compute_loss, require_targets


def _metrics(path: Path) -> dict[str, float]:
    source = path / "metrics.json" if path.is_dir() else path
    document = json.loads(source.read_text(encoding="utf-8"))
    values = document.get("scalar_metrics", document)
    if not isinstance(values, dict):
        return {}
    return {
        str(key): float(value)
        for key, value in values.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }


def _approved_targets(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if (row.get("review_status") or "").strip().lower() == "approved"
        ]


def compare(metrics_path: Path, target_path: Path, output: Path) -> str:
    output.mkdir(parents=True, exist_ok=True)
    targets = _approved_targets(target_path)
    if not targets:
        status = "WAITING_TARGET_DATA"
        rows: list[dict[str, object]] = []
        message = "Chua co dong literature target co review_status=approved; khong tinh loss."
    else:
        observed = _metrics(metrics_path)
        target: dict[str, float] = {}
        for row in targets:
            metric = (row.get("metric") or "").strip()
            value = (row.get("value") or "").strip()
            if metric and value:
                try:
                    target[metric] = float(value)
                except ValueError:
                    continue
        try:
            require_targets(target)
            loss = compute_loss(observed, target)
        except (RuntimeError, ValueError) as exc:
            status = "WAITING_TARGET_DATA" if "WAITING_TARGET_DATA" in str(exc) else "INSUFFICIENT_METRICS"
            rows = []
            message = str(exc)
        else:
            status = "PASS"
            rows = [{"metric": key, "observed": observed[key], "target": target[key], "delta": observed[key] - target[key]} for key in sorted(set(observed) & set(target))]
            message = json.dumps(loss, ensure_ascii=False)
    with (output / "comparison.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "observed", "target", "delta"])
        writer.writeheader()
        writer.writerows(rows)
    payload = {
        "status": status,
        "message": message,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "rows": rows,
        "scientific_scope": "Doi chieu metric tinh toan voi target literature; khong phai ket luan sinh hoc.",
    }
    (output / "comparison.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "comparison.md").write_text(
        f"# So sanh metric voi literature\n\n**Trang thai:** `{status}`\n\n{message}\n",
        encoding="utf-8",
    )
    return status


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        status = compare(args.metrics.resolve(), args.targets.resolve(), args.output.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Status: {status}")
    return 0 if status in {"PASS", "WAITING_TARGET_DATA", "INSUFFICIENT_METRICS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
