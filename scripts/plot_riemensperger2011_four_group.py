"""Render paper-guided figures only after a real four-group analysis exists."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.riemensperger2011.protocol import read_json, write_json


DEFAULT_SUMMARY = ROOT / "experiments/gate_21f_four_group_analysis/results/four_group_summary.json"
DEFAULT_METRICS = ROOT / "experiments/gate_21f_four_group_analysis/results/four_group_metrics.csv"
DEFAULT_EFFECTS = ROOT / "experiments/gate_21f_four_group_analysis/results/four_group_effect_comparison.csv"
DEFAULT_OUTPUT = ROOT / "figures/riemensperger_2011"


def plot(*, summary_path: Path, metrics_path: Path, effects_path: Path, output: Path) -> str:
    if not summary_path.is_file() or not metrics_path.is_file() or not effects_path.is_file():
        output.mkdir(parents=True, exist_ok=True)
        write_json(output / "figure_status.json", {"status": "WAITING_FOUR_GROUP_RESULTS", "message": "No figures were created because the four-group numeric artifacts are unavailable.", "data_fabricated": False})
        return "WAITING_FOUR_GROUP_RESULTS"
    summary = read_json(summary_path)
    if summary.get("status") != "FOUR_GROUP_ANALYSIS_COMPLETE":
        output.mkdir(parents=True, exist_ok=True)
        write_json(output / "figure_status.json", {"status": "WAITING_FOUR_GROUP_RESULTS", "message": f"No figures were created for status {summary.get('status')}.", "data_fabricated": False})
        return "WAITING_FOUR_GROUP_RESULTS"

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Install the analysis extra to render figures: pip install -e .[analysis]") from exc

    with metrics_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    with effects_path.open("r", encoding="utf-8-sig", newline="") as handle:
        effect = next(csv.DictReader(handle))
    output.mkdir(parents=True, exist_ok=True)
    labels = [f"{row['group']}\n{row['condition_role']}" for row in rows]
    values = [float(row["value"]) for row in rows]
    figure, axis = plt.subplots(figsize=(10, 5))
    colors = ["#4C78A8", "#72B7B2", "#E45756", "#F58518"]
    axis.bar(labels, values, color=colors[:len(values)])
    axis.set_ylabel("Median planar speed (mm/s)")
    axis.set_title("Riemensperger 2011: real and virtual four-group comparison")
    axis.tick_params(axis="x", labelrotation=15)
    figure.tight_layout()
    figure.savefig(output / "four_group_overview.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(6, 4))
    ratio_labels = ["Real disease/control", "Virtual disease/control"]
    ratio_values = [float(effect["real_effect_ratio"]), float(effect["virtual_effect_ratio"])]
    axis.bar(ratio_labels, ratio_values, color=["#E45756", "#F58518"])
    axis.axhline(1.0, color="#444444", linewidth=1, linestyle="--")
    axis.set_ylabel("Median speed ratio")
    axis.set_title("Effect-ratio comparison")
    figure.tight_layout()
    figure.savefig(output / "effect_ratio_comparison.png", dpi=180)
    plt.close(figure)

    write_json(output / "figure_status.json", {"status": "FIGURES_RENDERED_FROM_FOUR_GROUP_ARTIFACTS", "interpretation": summary.get("interpretation"), "source_summary": str(summary_path), "data_fabricated": False})
    return "FIGURES_RENDERED_FROM_FOUR_GROUP_ARTIFACTS"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--effects", type=Path, default=DEFAULT_EFFECTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    status = plot(summary_path=args.summary.resolve(), metrics_path=args.metrics.resolve(), effects_path=args.effects.resolve(), output=args.output.resolve())
    print(f"Status: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
