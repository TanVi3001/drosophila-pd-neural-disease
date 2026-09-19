#!/usr/bin/env python
"""Build a reproducible bridge_scales.json from Brian2 spike outputs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from drosophila_pd_neural.bridge import (  # noqa: E402
    build_bridge_scales,
    write_bridge_scales,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert comparable Brian2 spike tables into FlyGym bridge scales."
    )
    parser.add_argument("--reference-spikes", type=Path, required=True)
    parser.add_argument("--condition-spikes", type=Path, required=True)
    parser.add_argument(
        "--reference-manifest",
        type=Path,
        required=True,
        help="Run manifest for the reference spike output; must declare trial_count.",
    )
    parser.add_argument(
        "--condition-manifest",
        type=Path,
        required=True,
        help="Run manifest for the condition spike output; must declare trial_count.",
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        default=REPO_ROOT / "annotations" / "neuron_annotations.csv",
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--condition-label", default="condition")
    parser.add_argument("--duration-s", type=float, default=1.0)
    parser.add_argument("--allow-missing-turn", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data = build_bridge_scales(
        reference_spikes=args.reference_spikes,
        condition_spikes=args.condition_spikes,
        annotations=args.annotations,
        model=args.model,
        reference_manifest=args.reference_manifest,
        condition_manifest=args.condition_manifest,
        duration_s=args.duration_s,
        allow_missing_turn=args.allow_missing_turn,
        condition_label=args.condition_label,
    )
    output = write_bridge_scales(data, args.output)
    print(f"Wrote bridge scales: {output}")
    print(f"Status: {data['status']}")
    print(f"motor_scale: {data['motor_scale']}")
    print(f"coupling_scale: {data['coupling_scale']}")
    for warning in data["readout_summary"]["warnings"]:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
