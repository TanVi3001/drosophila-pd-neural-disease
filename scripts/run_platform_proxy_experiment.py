"""Run one proxy-burden condition through the canonical FlyGym API.

This is a thin integration boundary. The platform owns FlyGym/MuJoCo,
controller construction, simulation stepping, metrics, and pass criteria. The
neural repository supplies only a ``Perturbation``-protocol object.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from drosophila_pd_neural.platform_contract import default_platform_root, inspect_platform  # noqa: E402
from drosophila_pd_neural.platform_perturbation import ProxyBurdenPerturbation  # noqa: E402


def _load_platform_api(platform_root: Path):
    source_root = platform_root / "src"
    if not source_root.is_dir():
        raise RuntimeError(f"Platform source directory was not found: {source_root}")
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))
    from drosophila_pd.experiments.healthy_baseline import (  # noqa: PLC0415
        HealthyBaselineConfig,
    )
    from drosophila_pd.experiments.perturbation_experiment import (  # noqa: PLC0415
        build_perturbation_unavailable_report,
        run_paired_perturbation_experiment,
    )

    return (
        HealthyBaselineConfig,
        build_perturbation_unavailable_report,
        run_paired_perturbation_experiment,
    )


def _load_mapping(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        raise ValueError(f"Configuration must be a mapping: {path}")
    return document


def _build_config(
    path: Path,
    *,
    seed: int,
    steps: int | None,
    timestep_s: float | None,
    healthy_config_type: Any,
):
    values = deepcopy(_load_mapping(path))
    values["random_seed"] = int(seed)
    if steps is not None:
        if int(steps) <= 0:
            raise ValueError("steps must be positive when provided.")
        simulation = values.setdefault("simulation", {})
        if not isinstance(simulation, dict):
            raise ValueError("simulation must be a mapping.")
        effective_timestep = float(timestep_s if timestep_s is not None else simulation.get("timestep_s", 0.0001))
        if effective_timestep <= 0:
            raise ValueError("timestep_s must be positive.")
        simulation["timestep_s"] = effective_timestep
        simulation["duration_s"] = int(steps) * effective_timestep
    elif timestep_s is not None:
        simulation = values.setdefault("simulation", {})
        if not isinstance(simulation, dict):
            raise ValueError("simulation must be a mapping.")
        simulation["timestep_s"] = float(timestep_s)
    return healthy_config_type.from_mapping(values)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    platform_root = args.platform_root.expanduser().resolve()
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    contract = inspect_platform(platform_root)
    if not contract.ready:
        _write_json(output / "status.json", {
            "status": contract.status,
            "simulation_run": False,
            "message": "Platform source contract is incomplete.",
            "platform_contract": contract.as_dict(),
            "created_at_utc": datetime.now(UTC).isoformat(),
        })
        return 0

    try:
        (
            healthy_config_type,
            build_unavailable,
            run_paired,
        ) = _load_platform_api(platform_root)
    except Exception as exc:  # Import-time dependency failures are explicit waits.
        _write_json(output / "platform_contract.json", contract.as_dict())
        _write_json(output / "status.json", {
            "status": "WAITING_RUNTIME",
            "simulation_run": False,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "message": f"Platform API could not be imported: {type(exc).__name__}: {exc}",
            "platform_contract": contract.as_dict(),
            "scientific_scope": "No simulation was run; no biological claim is made.",
        })
        print(json.dumps({"status": "WAITING_RUNTIME", "output": str(output)}, ensure_ascii=False))
        return 0
    baseline_config = _build_config(
        args.baseline_config.expanduser().resolve(),
        seed=args.seed,
        steps=args.steps,
        timestep_s=args.timestep_s,
        healthy_config_type=healthy_config_type,
    )
    operator_config = _load_mapping(args.operator_config.expanduser().resolve())
    perturbation = ProxyBurdenPerturbation(
        burden_level=args.burden,
        operator_config=operator_config,
        name=args.name,
        config_id=args.config_id,
        random_seed=args.seed,
    )

    try:
        report = run_paired(
            baseline_config=baseline_config,
            perturbation=perturbation,
            repo_root=platform_root,
        )
        status = "PASS" if report.get("overall_pass") else "FAILED_QC"
    except Exception as exc:  # Platform runtime errors become explicit artifacts.
        report = build_unavailable(
            exc,
            baseline_config=baseline_config,
            perturbation=perturbation,
            repo_root=platform_root,
        )
        status = "WAITING_RUNTIME"

    _write_json(output / "platform_contract.json", contract.as_dict())
    _write_json(output / "proxy_report.json", report)
    _write_json(output / "status.json", {
        "status": status,
        "simulation_run": status in {"PASS", "FAILED_QC"},
        "created_at_utc": datetime.now(UTC).isoformat(),
        "platform_contract": contract.as_dict(),
        "perturbation": perturbation.metadata(),
        "report": "proxy_report.json",
        "scientific_scope": perturbation.metadata()["scientific_scope"],
    })

    perturbed = report.get("perturbed", {}) if isinstance(report, dict) else {}
    metrics = perturbed.get("derived_locomotion_metrics", {}) if isinstance(perturbed, dict) else {}
    if isinstance(metrics, dict):
        metrics = dict(metrics)
        # Keep the target's compact metric contract as aliases over the
        # platform's canonical names. The platform remains the metric owner.
        if "planar_path_length_mm" in metrics:
            metrics.setdefault("distance_traveled_mm", metrics["planar_path_length_mm"])
        if "planar_displacement_mm" in metrics:
            metrics.setdefault("displacement_mm", metrics["planar_displacement_mm"])
        _write_json(output / "metrics" / "metrics.json", {
            "schema_version": "platform-derived-locomotion-metrics-1",
            "condition_id": args.name,
            "scalar_metrics": metrics,
            "source": "drosophila_pd.experiments.healthy_baseline.run_locomotion",
            "scientific_scope": perturbation.metadata()["scientific_scope"],
        })
    print(json.dumps({"status": status, "output": str(output), "platform_commit": contract.git_commit}, ensure_ascii=False))
    return 0 if status in {"PASS", "WAITING_RUNTIME"} else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform-root", type=Path, default=default_platform_root())
    parser.add_argument(
        "--baseline-config",
        type=Path,
        default=None,
        help="Platform healthy-baseline YAML; defaults to the canonical platform config.",
    )
    parser.add_argument(
        "--operator-config",
        type=Path,
        default=ROOT / "experiments/gate_12e_proxy_operator/configs/proxy_burden_action_operator.yaml",
    )
    parser.add_argument("--burden", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--timestep-s", type=float, default=None)
    parser.add_argument("--name", default="proxy_burden")
    parser.add_argument("--config-id", default=None)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.seed < 0 or not 0.0 <= args.burden <= 1.0:
        raise SystemExit("seed must be non-negative and burden must be within [0, 1].")
    if args.baseline_config is None:
        args.baseline_config = args.platform_root / "configs/experiments/healthy_baseline.yaml"
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
