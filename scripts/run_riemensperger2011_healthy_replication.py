"""Run the healthy arm of the paper-guided Riemensperger 2011 replication."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.riemensperger2011.metrics import rollout_seed_metrics, sample_summary
from drosophila_pd_neural.riemensperger2011.protocol import (
    build_manifest,
    project_path,
    read_json,
    read_yaml,
    require_status,
    sha256_file,
    utc_now,
    write_csv_rows,
    write_json,
)


DEFAULT_CONFIG = ROOT / "configs/replications/riemensperger_2011_healthy.yaml"
DEFAULT_EVIDENCE = ROOT / "experiments/gate_21a_riemensperger_evidence_lock/results/evidence_lock_summary.json"
DEFAULT_MAPPING = ROOT / "experiments/gate_21d_riemensperger_dopamine_mapping/results/dopamine_mapping_summary.json"
DEFAULT_OUTPUT = ROOT / "experiments/gate_21b_riemensperger_healthy"
RUNNER = ROOT / "scripts/run_neural_experiment.py"
FIELDS = (
    "seed",
    "status",
    "message",
    "median_planar_speed_mm_s",
    "distance_traveled_mm",
    "displacement_mm",
    "duration_s",
    "frame_count",
    "contact_detected",
    "finite_qc",
    "timestamp_monotonic",
    "joint_trajectory_max_delta",
    "action_trajectory_max_delta",
    "mean_framewise_planar_speed_mm_s",
    "rollout_path",
)


def _resolve(value: str | Path, *, base: Path = ROOT) -> Path:
    candidate = Path(value).expanduser()
    return (base / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()


def _runtime_blockers(*, brain_root: Path, platform_root: Path, brain_python: Path) -> list[str]:
    blockers: list[str] = []
    for relative in (
        "brain_body_bridge.py",
        "code/run_pytorch.py",
        "data/2025_Completeness_783.csv",
        "data/2025_Connectivity_783.parquet",
        "data/plastic_weights.pt",
    ):
        if not (brain_root / relative).is_file():
            blockers.append(f"brain_artifact_missing:{relative}")
    if not (platform_root / "scripts/run_brain_body_rollout.py").is_file():
        blockers.append("platform_runner_missing:scripts/run_brain_body_rollout.py")
    if not brain_python.is_file():
        blockers.append(f"brain_python_missing:{brain_python}")
    return blockers


def _runtime_label(path: Path, external_label: str) -> str:
    """Keep committed execution plans portable when runtime roots live outside this repo."""

    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except (OSError, ValueError):
        return external_label


def _row(seed: int, *, status: str, message: str, output: Path, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {field: "" for field in FIELDS}
    row.update({"seed": seed, "status": status, "message": message, "rollout_path": project_path(output / "rollout.npz")})
    if metrics:
        row.update(metrics)
    return row


def _gpu_telemetry() -> dict[str, Any]:
    """Read the lightweight GPU safety telemetry required by Gate 26."""

    command = [
        "nvidia-smi",
        "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.free",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return {"available": False, "note": "nvidia-smi unavailable"}
    if result.returncode or not result.stdout.strip():
        return {"available": False, "note": "nvidia-smi unavailable"}
    values = [item.strip() for item in result.stdout.splitlines()[0].split(",")]
    if len(values) != 4:
        return {"available": False, "note": "nvidia-smi output could not be parsed"}
    try:
        telemetry = {
            "available": True,
            "temperature_c": float(values[0]),
            "utilization_percent": float(values[1]),
            "memory_used_mib": float(values[2]),
            "memory_free_mib": float(values[3]),
        }
    except ValueError as exc:
        return {"available": False, "note": f"nvidia-smi parse error: {exc}"}
    if telemetry["temperature_c"] >= 82:
        raise RuntimeError(f"GPU temperature reached the safety limit: {telemetry['temperature_c']} C")
    return telemetry


def _assert_gpu_idle() -> None:
    """Stop before launching a seed if another CUDA process is already active."""

    command = [
        "nvidia-smi",
        "--query-compute-apps=pid,used_memory",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return
    if result.returncode != 0 or not result.stdout.strip():
        return
    active = []
    for line in result.stdout.splitlines():
        fields = [item.strip() for item in line.split(",")]
        if len(fields) != 2 or fields[1].upper() in {"[N/A]", "N/A"}:
            continue
        try:
            if float(fields[1]) > 0:
                active.append(line.strip())
        except ValueError:
            continue
    if active:
        raise RuntimeError(f"GPU has pre-existing compute processes: {', '.join(active)}")


def _write_gpu_telemetry(output: Path, records: list[dict[str, Any]]) -> Path:
    path = output / "results/gpu_telemetry.json"
    write_json(path, {"schema_version": "gate26-gpu-telemetry-v1", "records": records})
    return path


def _write_report(output: Path, *, status: str, rows: list[dict[str, Any]], blockers: list[str]) -> None:
    lines = [
        "# Gate 21B - Virtual healthy replication",
        "",
        f"**Trạng thái:** `{status}`",
        "",
        "Disease layer: `OFF`. Calibration và tuning: `OFF`.",
        "",
    ]
    if blockers:
        lines.extend(["## Blocker", "", *[f"- `{item}`" for item in blockers], ""])
    if rows:
        lines.extend([
            "## Seed-level results",
            "",
            "| Seed | Status | Median speed (mm/s) | Distance (mm) | QC |",
            "| ---: | --- | ---: | ---: | --- |",
        ])
        for row in rows:
            qc = "PASS" if row.get("finite_qc") and row.get("timestamp_monotonic") and row.get("contact_detected") else "INCOMPLETE"
            lines.append(f"| {row['seed']} | `{row['status']}` | {row.get('median_planar_speed_mm_s', '')} | {row.get('distance_traveled_mm', '')} | `{qc}` |")
    lines.extend([
        "",
        "Mỗi hàng là một seed độc lập. Frame trong rollout không được dùng như replicate thống kê.",
        "Video (nếu có) chỉ là minh họa cho rollout computational, không là bằng chứng định lượng.",
        "",
    ])
    report_path = ROOT / "docs/replications/riemensperger_2011/gate_21b_healthy_virtual_replication.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def run(
    *,
    config_path: Path,
    evidence_path: Path,
    mapping_path: Path,
    output: Path,
    brain_root: Path,
    platform_root: Path,
    brain_python: Path,
    runner_python: Path,
    dry_run: bool,
    reuse_completed: bool = False,
) -> tuple[str, list[dict[str, Any]]]:
    config = read_yaml(config_path)
    output.mkdir(parents=True, exist_ok=True)
    try:
        require_status(evidence_path, "RIEMENSPERGER_2011_EVIDENCE_LOCKED")
    except (OSError, RuntimeError, ValueError) as exc:
        status = "WAITING_RIEMENSPERGER_2011_PAPER_EVIDENCE"
        manifest = build_manifest(status=status, config_paths=[config_path], input_paths=[evidence_path], extra={"message": str(exc), "simulation_run": False})
        write_json(output / "manifests/healthy_manifest.json", manifest)
        _write_report(output, status=status, rows=[], blockers=[str(exc)])
        return status, []

    seeds = [int(seed) for seed in config["seed_policy"]["seeds"]]
    steps = int(config["duration"]["steps"])
    mapping_blocker: list[str] = []
    if not dry_run:
        try:
            require_status(mapping_path, "READY_FOR_RIEMENSPERGER_DISEASE_REPLICATION")
        except (OSError, RuntimeError, ValueError) as exc:
            mapping_blocker.append(f"mapping:{exc}")
    runtime_blockers = _runtime_blockers(brain_root=brain_root, platform_root=platform_root, brain_python=brain_python)
    plan = {
        "schema_version": "riemensperger-2011-healthy-execution-plan-v1",
        "created_at_utc": utc_now(),
        "dry_run": dry_run,
        "seeds": seeds,
        "steps": steps,
        "brain_root": _runtime_label(brain_root, "<external-brain-root>"),
        "platform_root": _runtime_label(platform_root, "<external-flygym-root>"),
        "brain_python": _runtime_label(brain_python, "<external-brain-python>"),
        "runtime_blockers": runtime_blockers,
        "disease_layer": False,
        "calibration": False,
        "tuning": False,
    }
    write_json(output / "results/healthy_execution_plan.json", plan)
    if dry_run or runtime_blockers or mapping_blocker:
        status = "NOT_EXECUTED_DRY_RUN" if dry_run else "WAITING_DOPAMINE_MAPPING_REVIEW" if mapping_blocker else "WAITING_HEALTHY_REPLICATION_RUNTIME"
        manifest = build_manifest(
            status=status,
            config_paths=[config_path],
            input_paths=[evidence_path, mapping_path],
            extra={"simulation_run": False, "runtime_blockers": runtime_blockers + mapping_blocker, "seed_list": seeds, "duration_s": config["duration"]["virtual_duration_s"], "timestep": config["timestep_s"]},
        )
        write_json(output / "manifests/healthy_manifest.json", manifest)
        _write_report(output, status=status, rows=[], blockers=runtime_blockers + mapping_blocker + (["dry_run_requested"] if dry_run else []))
        return status, []

    rows: list[dict[str, Any]] = []
    telemetry: list[dict[str, Any]] = []
    _write_gpu_telemetry(output, telemetry)
    for seed in seeds:
        seed_output = output / "results" / f"seed_{seed:03d}"
        if seed_output.exists() and any(seed_output.iterdir()):
            if not reuse_completed:
                raise RuntimeError(f"Refusing to overwrite existing seed output; no retry is allowed: {seed_output}")
            rollout = seed_output / "rollout.npz"
            if not rollout.is_file():
                raise RuntimeError(f"Existing seed output is incomplete; no retry is allowed: {seed_output}")
            metrics = rollout_seed_metrics(rollout)
            if not metrics["contact_detected"]:
                raise RuntimeError(f"Existing seed output failed contact QC: {seed_output}")
            rows.append(_row(seed, status="PASS", message="reused completed rollout for post-processing only", output=seed_output, metrics=metrics))
            continue
        _assert_gpu_idle()
        gpu_before = _gpu_telemetry()
        command = [
            str(runner_python), str(RUNNER),
            "--brain-root", str(brain_root),
            "--platform-root", str(platform_root),
            "--brain-python", str(brain_python),
            "--seed", str(seed),
            "--steps", str(steps),
            "--device", str(config["platform_runtime"]["device"]),
            "--output", str(seed_output),
            "--stimulus", str(config["controller"]["stimulus"]),
            "--cpg-frequency-hz", str(config["controller"]["cpg_frequency_hz"]),
            "--artifact-profile", "GATE24E_MEMORY_SAFE",
        ]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        gpu_after = _gpu_telemetry()
        telemetry.append({"seed": seed, "before": gpu_before, "after": gpu_after})
        _write_gpu_telemetry(output, telemetry)
        (output / "logs").mkdir(parents=True, exist_ok=True)
        (output / "logs" / f"seed_{seed:03d}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        rollout = seed_output / "rollout.npz"
        if result.returncode != 0 or not rollout.is_file():
            rows.append(_row(seed, status="FAILED", message=f"runner_return_code={result.returncode}", output=seed_output))
            break
        try:
            metrics = rollout_seed_metrics(rollout)
            if not metrics["contact_detected"]:
                raise RuntimeError("no ground contact detected")
            rows.append(_row(seed, status="PASS", message="real FlyGym rollout", output=seed_output, metrics=metrics))
        except (OSError, RuntimeError, ValueError) as exc:
            rows.append(_row(seed, status="FAILED", message=str(exc), output=seed_output))
            break

    telemetry_path = _write_gpu_telemetry(output, telemetry)
    write_csv_rows(output / "metrics/healthy_per_seed_metrics.csv", FIELDS, rows)
    passed = [row for row in rows if row["status"] == "PASS"]
    status = "HEALTHY_VIRTUAL_REPLICATION_PASS" if len(passed) == len(seeds) else "HEALTHY_VIRTUAL_REPLICATION_BLOCKED"
    summary: dict[str, Any] = {"status": status, "n_seeds_planned": len(seeds), "n_seeds_passed": len(passed), "data_fabricated": False}
    if passed:
        summary["median_planar_speed_mm_s"] = sample_summary([float(row["median_planar_speed_mm_s"]) for row in passed])
        summary["distance_traveled_mm"] = sample_summary([float(row["distance_traveled_mm"]) for row in passed])
    write_json(output / "results/healthy_summary.json", summary)
    manifest = build_manifest(
        status=status,
        config_paths=[config_path],
        input_paths=[evidence_path, output / "metrics/healthy_per_seed_metrics.csv", output / "results/healthy_summary.json", telemetry_path],
        extra={"simulation_run": True, "seed_list": seeds, "duration_s": config["duration"]["virtual_duration_s"], "timestep": config["timestep_s"], "output_sha256": sha256_file(output / "metrics/healthy_per_seed_metrics.csv")},
    )
    write_json(output / "manifests/healthy_manifest.json", manifest)
    _write_report(output, status=status, rows=rows, blockers=[])
    return status, rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--brain-root", type=Path, default=ROOT / "external/fly-brain")
    parser.add_argument("--platform-root", type=Path, default=ROOT.parent / "drosophila-pd-flygym")
    parser.add_argument("--brain-python", type=Path, default=ROOT.parent / "drosophila-pd-flygym/.venv/Scripts/python.exe")
    parser.add_argument("--runner-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    status, _ = run(
        config_path=_resolve(args.config), evidence_path=_resolve(args.evidence), mapping_path=_resolve(args.mapping), output=_resolve(args.output),
        brain_root=_resolve(args.brain_root), platform_root=_resolve(args.platform_root),
        brain_python=_resolve(args.brain_python), runner_python=_resolve(args.runner_python), dry_run=args.dry_run,
    )
    print(f"Status: {status}")
    return 0 if status in {"HEALTHY_VIRTUAL_REPLICATION_PASS", "NOT_EXECUTED_DRY_RUN", "WAITING_HEALTHY_REPLICATION_RUNTIME", "WAITING_DOPAMINE_MAPPING_REVIEW", "WAITING_RIEMENSPERGER_2011_PAPER_EVIDENCE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
