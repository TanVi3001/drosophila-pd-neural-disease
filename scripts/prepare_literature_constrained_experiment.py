"""Validate and package one literature-constrained virtual experiment.

This command is a preflight/package step.  It never starts FlyGym and never
creates rollout metrics or video files.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from drosophila_pd_neural.literature_experiment import (  # noqa: E402
    input_manifest,
    validate_experiment_plan,
)


def _write_json(path: Path, document: dict[str, Any]) -> None:
    import json

    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_report(path: Path, manifest: dict[str, Any]) -> None:
    validation = manifest["validation"]
    lines = [
        "# Literature-constrained experiment preflight",
        "",
        f"- Experiment: `{manifest.get('experiment_id', '')}`",
        f"- Status: `{validation.get('status', 'UNKNOWN')}`",
        f"- Simulation executed: `{manifest.get('simulation_executed', False)}`",
        f"- Virtual metric: `{validation.get('virtual_metric', '')}`",
        "",
        "## Issues",
        "",
    ]
    issues = validation.get("issues", [])
    if issues:
        lines.extend(f"- `{item['severity']}` `{item['code']}`: {item['message']}" for item in issues)
    else:
        lines.append("- Không có lỗi preflight.")
    lines.extend(
        [
            "",
            "## Scientific boundary",
            "",
            "Đây là protocol computational có provenance. Bước này không chạy",
            "simulation, không tạo metrics/video và không phải biological Parkinson",
            "validation.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare(config: Path, output: Path) -> dict[str, Any]:
    document = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    validation = validate_experiment_plan(document, root=ROOT)
    output.mkdir(parents=True, exist_ok=True)
    manifest = input_manifest(document, config, validation)
    _write_json(output / "experiment_manifest.json", manifest)
    _write_report(output / "preflight_report.md", manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = args.config if args.config.is_absolute() else ROOT / args.config
    output = args.output if args.output.is_absolute() else ROOT / args.output
    try:
        manifest = prepare(config.resolve(), output.resolve())
    except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Status: {manifest['status']}")
    print(f"Manifest: {output.resolve() / 'experiment_manifest.json'}")
    return 0 if manifest["status"] != "INVALID_PROTOCOL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
