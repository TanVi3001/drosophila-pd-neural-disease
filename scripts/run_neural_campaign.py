"""Chay healthy va cac disease condition theo nhieu seed, khong tao du lieu gia."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_neural_experiment.py"


def _seeds(value: str) -> list[int]:
    result = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not result or any(seed < 0 for seed in result):
        raise ValueError("seeds phai la danh sach so nguyen >= 0")
    return result


def _read_scalars(path: Path) -> dict[str, float]:
    metrics_path = path / "metrics" / "metrics.json"
    if not metrics_path.is_file():
        return {}
    document = json.loads(metrics_path.read_text(encoding="utf-8"))
    source = document.get("scalar_metrics", document)
    if not isinstance(source, dict):
        return {}
    result: dict[str, float] = {}
    for key, value in source.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            result[str(key)] = float(value)
    return result


def _run(command: list[str]) -> int:
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def _baseline_comparisons(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    baselines = {
        row["seed"]: row
        for row in rows
        if row.get("condition") == "healthy" and row.get("status") == "PASS"
    }
    excluded = {"condition", "seed", "status", "output", "metric_count"}
    comparisons: list[dict[str, object]] = []
    for row in rows:
        baseline = baselines.get(row.get("seed"))
        if baseline is None or row.get("condition") == "healthy" or row.get("status") != "PASS":
            continue
        for metric in sorted(set(row) & set(baseline) - excluded):
            condition_value = row[metric]
            baseline_value = baseline[metric]
            if isinstance(condition_value, (int, float)) and isinstance(baseline_value, (int, float)):
                comparisons.append(
                    {
                        "condition": row["condition"],
                        "seed": row["seed"],
                        "metric": metric,
                        "baseline": baseline_value,
                        "condition_value": condition_value,
                        "delta": condition_value - baseline_value,
                    }
                )
    return comparisons


def run_campaign(args: argparse.Namespace) -> int:
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    args.brain_root = args.brain_root.resolve()
    args.platform_root = args.platform_root.resolve()
    if args.brain_python:
        args.brain_python = args.brain_python.resolve()
    seed_values = _seeds(args.seeds)
    configs = args.config or sorted((ROOT / "configs" / "conditions").glob("*.template.yaml"))
    configs = [path if path.is_absolute() else ROOT / path for path in configs]
    rows: list[dict[str, object]] = []

    def execute(label: str, config: Path | None, seed: int) -> None:
        output = output_root / label / f"seed_{seed:03d}"
        command = [
            sys.executable,
            str(RUNNER),
            "--brain-root", str(args.brain_root),
            "--platform-root", str(args.platform_root),
            "--seed", str(seed),
            "--steps", str(args.steps),
            "--device", args.device,
            "--output", str(output),
            "--age-days", str(args.age_days),
            "--stimulus", args.stimulus,
        ]
        if args.brain_python:
            command.extend(["--brain-python", str(args.brain_python)])
        if config is not None:
            command.extend(["--config", str(config)])
        if args.video:
            command.append("--video")
        return_code = _run(command)
        status_path = output / "status.json"
        status = "FAILED"
        if status_path.is_file():
            status = json.loads(status_path.read_text(encoding="utf-8")).get("status", "UNKNOWN")
        scalar_metrics = _read_scalars(output)
        row: dict[str, object] = {
            "condition": label,
            "seed": seed,
            "status": status if return_code == 0 else "FAILED",
            "output": str(output),
            "metric_count": len(scalar_metrics),
        }
        row.update(scalar_metrics)
        rows.append(row)

    for seed in seed_values:
        execute("healthy", None, seed)
    for config in configs:
        config_data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
        condition_id = str(config_data.get("condition_id", config.stem.replace(".template", "")))
        for seed in seed_values:
            execute(condition_id, config, seed)

    fields = sorted({key for row in rows for key in row})
    with (output_root / "campaign_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    comparisons = _baseline_comparisons(rows)
    with (output_root / "baseline_comparison.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["condition", "seed", "metric", "baseline", "condition_value", "delta"],
        )
        writer.writeheader()
        writer.writerows(comparisons)
    status_counts: dict[str, int] = {}
    for row in rows:
        key = str(row["status"])
        status_counts[key] = status_counts.get(key, 0) + 1
    payload = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status_counts": status_counts,
        "row_count": len(rows),
        "baseline_comparison_count": len(comparisons),
        "simulation_data_fabricated": False,
        "scientific_scope": "So sanh metric locomotion tinh toan; khong phai xac nhan Parkinson sinh hoc.",
        "rows": rows,
    }
    (output_root / "campaign_status.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = [
        "# Neural campaign summary",
        "",
        "Day la computational locomotion experiment; khong phai biological validation.",
        "",
        f"- So run: {len(rows)}",
        f"- Trang thai: {status_counts}",
        "- Du lieu gia: khong.",
        "",
    ]
    (output_root / "campaign_summary.md").write_text("\n".join(lines), encoding="utf-8")
    (output_root / "baseline_comparison.md").write_text(
        "# So sanh voi healthy baseline\n\n"
        "Chi bao cao delta metric giua cac run PASS cung seed; khong dien giai sinh hoc.\n\n"
        f"So dong so sanh: {len(comparisons)}.\n",
        encoding="utf-8",
    )
    return 0 if not any(row["status"] == "FAILED" for row in rows) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brain-root", type=Path, required=True)
    parser.add_argument("--platform-root", type=Path, default=ROOT.parent / "drosophila-pd-flygym")
    parser.add_argument("--brain-python", type=Path, default=None)
    parser.add_argument("--config", type=Path, action="append", default=None)
    parser.add_argument("--age-days", type=float, default=20.0)
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    parser.add_argument("--stimulus", default="p9")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--video", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.steps <= 0 or args.age_days < 0:
        parser.error("steps phai > 0 va age-days phai >= 0")
    try:
        return run_campaign(args)
    except (OSError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
