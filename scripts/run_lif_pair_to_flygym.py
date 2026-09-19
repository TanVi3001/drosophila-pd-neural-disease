#!/usr/bin/env python
"""Run two newly generated LIF conditions through the explicit FlyGym bridge.

The configuration must provide both conditions, public model files, a reviewed
annotation table, and a platform Python that owns FlyGym/MuJoCo.  This command
never substitutes an old spike artifact when a new condition cannot be run.
Missing or incompatible ID mappings produce a failed pipeline manifest.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLATFORM_ROOT = ROOT.parent / "drosophila-pd-flygym"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_component(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip())
    return normalized.strip("._") or "condition"


def _load_document(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("PyYAML is required for YAML pipeline configuration.") from exc
        value = yaml.safe_load(text)
    else:
        value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("pipeline configuration must contain an object")
    return value


def _path(value: object, base: Path, *, required: bool = True) -> Path | None:
    if value is None or not str(value).strip():
        if required:
            raise ValueError("required path is missing from pipeline configuration")
        return None
    candidate = Path(str(value)).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


def _condition(document: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = document.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} condition must be an object")
    input_ids = value.get("input_ids", ())
    silence_ids = value.get("silence_ids", ())
    if not isinstance(input_ids, list) or not all(not isinstance(item, bool) for item in input_ids):
        raise ValueError(f"{key}.input_ids must be a list of neuron IDs")
    if not isinstance(silence_ids, list) or not all(not isinstance(item, bool) for item in silence_ids):
        raise ValueError(f"{key}.silence_ids must be a list of neuron IDs")
    return {
        "label": str(value.get("label", key)),
        "input_ids": [int(item) for item in input_ids],
        "silence_ids": [int(item) for item in silence_ids],
    }


def _lif_command(
    *,
    condition: Mapping[str, Any],
    args: argparse.Namespace,
    output: Path,
) -> list[str]:
    command = [
        str(args.neural_python.resolve()),
        str((ROOT / "scripts" / "run_lif_condition.py").resolve()),
        "--model-root", str(args.model_root),
        "--completeness", str(args.completeness),
        "--connectivity", str(args.connectivity),
        "--condition-label", str(condition["label"]),
        "--output", str(output),
        "--seed", str(args.seed),
        "--trials", str(args.trials),
        "--duration-s", str(args.duration_s),
        "--stimulus-rate-hz", str(args.stimulus_rate_hz),
        "--id-namespace", str(args.id_namespace),
        "--dataset-id", str(args.dataset_id),
        "--overwrite",
    ]
    for value in condition["input_ids"]:
        command.extend(("--input-id", str(value)))
    for value in condition["silence_ids"]:
        command.extend(("--silence-id", str(value)))
    return command


def run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    base = args.config.resolve().parent
    document = _load_document(args.config)
    args.model_root = _path(document.get("model_root"), base)
    args.completeness = _path(document.get("completeness"), base)
    args.connectivity = _path(document.get("connectivity"), base)
    args.annotations = _path(document.get("annotations"), base)
    args.platform_root = _path(document.get("platform_root", DEFAULT_PLATFORM_ROOT), base)
    args.platform_python = _path(document.get("platform_python"), base)
    args.neural_python = _path(document.get("neural_python", sys.executable), base)
    args.baseline_config = _path(document.get("baseline_config"), base)
    args.model = str(document.get("model", "lif_pair"))
    args.condition_label = str(document.get("condition_label", "condition"))
    args.seed = int(document.get("seed", 0))
    args.trials = int(document.get("trials", 1))
    args.duration_s = float(document.get("duration_s", 1.0))
    args.stimulus_rate_hz = float(document.get("stimulus_rate_hz", 150.0))
    args.id_namespace = str(document.get("id_namespace", "flywire_root_id"))
    args.dataset_id = str(document.get("dataset_id", "flywire-630-2023-03-23"))
    reference = _condition(document, "reference")
    condition = _condition(document, "condition")
    for path in (args.model_root, args.completeness, args.connectivity, args.annotations, args.platform_root, args.neural_python, args.platform_python):
        if path is None or not path.exists():
            raise FileNotFoundError(path or "missing configured path")
    if args.baseline_config is None:
        args.baseline_config = args.platform_root / "configs" / "experiments" / "healthy_baseline.yaml"
    if not args.baseline_config.is_file():
        raise FileNotFoundError(args.baseline_config)

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    reference_output = output / "lif" / "reference"
    condition_output = output / "lif" / "condition"
    commands = {
        "reference": _lif_command(condition=reference, args=args, output=reference_output),
        "condition": _lif_command(condition=condition, args=args, output=condition_output),
    }
    process_log: dict[str, Any] = {}
    for label, command in commands.items():
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        (output / f"{label}_lif.log").write_text(
            (process.stdout or "") + "\n--- STDERR ---\n" + (process.stderr or ""),
            encoding="utf-8",
        )
        process_log[label] = {"return_code": process.returncode, "command": command}
        if process.returncode != 0:
            raise RuntimeError(f"new {label} LIF condition failed; see {output / f'{label}_lif.log'}")

    bridge_output = output / "lif_to_flygym"
    bridge_command = [
        str(args.neural_python.resolve()),
        str((ROOT / "scripts" / "run_lif_to_flygym.py").resolve()),
        "--reference-spikes", str(reference_output / f"{_safe_component(reference['label'])}.parquet"),
        "--condition-spikes", str(condition_output / f"{_safe_component(condition['label'])}.parquet"),
        "--reference-manifest", str(reference_output / "run_manifest.json"),
        "--condition-manifest", str(condition_output / "run_manifest.json"),
        "--annotations", str(args.annotations),
        "--model", args.model,
        "--condition-label", args.condition_label,
        "--duration-s", str(args.duration_s),
        "--platform-root", str(args.platform_root),
        "--platform-python", str(args.platform_python),
        "--baseline-config", str(args.baseline_config),
        "--output", str(bridge_output),
        "--seed", str(args.seed),
    ]
    bridge = subprocess.run(bridge_command, cwd=ROOT, capture_output=True, text=True, check=False)
    (output / "bridge.log").write_text(
        (bridge.stdout or "") + "\n--- STDERR ---\n" + (bridge.stderr or ""),
        encoding="utf-8",
    )
    pipeline_manifest = {
        "schema_version": "lif-generated-to-flygym-manifest-1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "PASS" if bridge.returncode == 0 else "FAIL",
        "seed": args.seed,
        "trial_count": args.trials,
        "duration_s": args.duration_s,
        "source_config": {"path": str(args.config.resolve()), "sha256": _sha256(args.config)},
        "condition_runs": {
            "reference": {"path": str(reference_output / "run_manifest.json"), "condition": reference},
            "condition": {"path": str(condition_output / "run_manifest.json"), "condition": condition},
        },
        "lif_processes": process_log,
        "bridge_process": {"return_code": bridge.returncode, "command": bridge_command},
        "artifacts": {
            "bridge_pipeline": str(bridge_output / "pipeline_manifest.json"),
            "bridge_scales": str(bridge_output / "bridge_scales.json"),
            "platform_report": str(bridge_output / "platform_report.json"),
        },
        "scientific_scope": (
            "Generated LIF-to-FlyGym computational integration only. The bridge mapping is a proxy; "
            "no biological validation or firing-to-behavior calibration is implied."
        ),
    }
    manifest_path = output / "pipeline_manifest.json"
    manifest_path.write_text(json.dumps(pipeline_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(pipeline_manifest, indent=2, sort_keys=True))
    return pipeline_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = run_pipeline(args)
    except (FileNotFoundError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        args.output.mkdir(parents=True, exist_ok=True)
        failure = {
            "schema_version": "lif-generated-to-flygym-manifest-1",
            "created_at_utc": datetime.now(UTC).isoformat(),
            "status": "FAIL",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "scientific_scope": "No valid generated LIF-to-FlyGym integration result was produced.",
        }
        (args.output / "pipeline_manifest.json").write_text(
            json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(failure, indent=2, sort_keys=True), file=sys.stderr)
        return 2
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
