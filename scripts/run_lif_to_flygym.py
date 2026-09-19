#!/usr/bin/env python
"""Execute the complete Brian2 spike-output -> FlyGym bridge pipeline."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from drosophila_pd_neural.bridge import build_bridge_scales, write_bridge_scales  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Brian2 readout conversion and the native FlyGym bridge consumer."
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
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Explicit seed forwarded to the platform brain-driven runner.",
    )
    parser.add_argument("--allow-missing-turn", action="store_true")
    parser.add_argument(
        "--platform-root",
        type=Path,
        default=REPO_ROOT.parent / "drosophila-pd-flygym",
    )
    parser.add_argument("--platform-python", type=Path, default=Path(sys.executable))
    parser.add_argument(
        "--baseline-config",
        type=Path,
        default=REPO_ROOT.parent / "drosophila-pd-flygym" / "configs" / "experiments" / "healthy_baseline.yaml",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def _manifest_path(path: Path) -> str:
    return str(path.resolve())


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_root = args.output.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    bridge_path = output_root / "bridge_scales.json"
    platform_report_path = output_root / "platform_report.json"
    log_path = output_root / "platform_runner.log"

    try:
        bridge = build_bridge_scales(
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
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        failure = {
            "schema_version": "lif-to-flygym-e2e-manifest-1",
            "created_at": datetime.now(UTC).isoformat(),
            "status": "FAIL",
            "bridge_status": "FAILED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "scientific_scope": (
                "End-to-end computational integration was blocked before bridge output; "
                "no biological conclusion is available."
            ),
        }
        (output_root / "pipeline_manifest.json").write_text(
            json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(failure, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    write_bridge_scales(bridge, bridge_path)

    command = [
        str(args.platform_python.resolve()),
        str((args.platform_root / "scripts" / "run_brain_driven_experiment.py").resolve()),
        "--scales-json",
        str(bridge_path),
        "--baseline-config",
        str(args.baseline_config.resolve()),
        "--model-name",
        args.model,
        "--output",
        str(platform_report_path),
    ]
    if args.seed is not None:
        command.extend(("--seed", str(args.seed)))
    process = subprocess.run(
        command,
        cwd=args.platform_root,
        capture_output=True,
        text=True,
        check=False,
    )
    log_path.write_text(
        (process.stdout or "") + "\n--- STDERR ---\n" + (process.stderr or ""),
        encoding="utf-8",
    )

    platform_report: dict[str, Any] | None = None
    if platform_report_path.is_file():
        try:
            value = json.loads(platform_report_path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                platform_report = value
        except json.JSONDecodeError:
            platform_report = None

    platform_pass = bool(platform_report and platform_report.get("overall_pass") is True)
    manifest = {
        "schema_version": "lif-to-flygym-e2e-manifest-1",
        "created_at": datetime.now(UTC).isoformat(),
        "status": "PASS" if process.returncode == 0 and platform_pass else "FAIL",
        "bridge_status": bridge["status"],
        "platform_return_code": process.returncode,
        "platform_overall_pass": platform_report.get("overall_pass") if platform_report else None,
        "source_artifacts": {
            "reference_spikes": {
                "path": _manifest_path(args.reference_spikes),
                "sha256": _sha256(args.reference_spikes),
            },
            "condition_spikes": {
                "path": _manifest_path(args.condition_spikes),
                "sha256": _sha256(args.condition_spikes),
            },
            "reference_run_manifest": {
                "path": _manifest_path(args.reference_manifest),
                "sha256": _sha256(args.reference_manifest),
            },
            "condition_run_manifest": {
                "path": _manifest_path(args.condition_manifest),
                "sha256": _sha256(args.condition_manifest),
            },
            "annotations": {
                "path": _manifest_path(args.annotations),
                "sha256": _sha256(args.annotations),
            },
        },
        "artifacts": {
            "bridge_scales": _manifest_path(bridge_path),
            "platform_report": _manifest_path(platform_report_path),
            "platform_log": _manifest_path(log_path),
        },
        "command": command,
        "scientific_scope": (
            "End-to-end computational integration only. The Brian2 readout is mapped "
            "to FlyGym proxy scales; this is not biological disease validation."
        ),
    }
    manifest_path = output_root / "pipeline_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote pipeline manifest: {manifest_path}")
    print(f"Bridge status: {bridge['status']}")
    print(f"FlyGym overall_pass: {platform_report.get('overall_pass') if platform_report else None}")
    if process.returncode != 0:
        print(f"FlyGym runner returned {process.returncode}; see {log_path}")
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
