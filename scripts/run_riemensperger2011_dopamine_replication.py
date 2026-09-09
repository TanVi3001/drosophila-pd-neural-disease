"""Run the virtual dopamine-deficient arm after Gate 21D reviewer approval."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.riemensperger2011.metrics import rollout_seed_metrics, sample_summary
from drosophila_pd_neural.riemensperger2011.protocol import (
    build_manifest,
    project_path,
    read_yaml,
    require_status,
    sha256_file,
    write_csv_rows,
    write_json,
)
from scripts.run_riemensperger2011_healthy_replication import (
    _assert_gpu_idle,
    _gpu_telemetry,
    _resolve,
    _runtime_blockers,
)
from scripts.materialize_riemensperger2011_dopamine_checkpoint import materialize


DEFAULT_CONFIG = ROOT / "configs/replications/riemensperger_2011_dopamine_deficiency.yaml"
DEFAULT_MAPPING = ROOT / "experiments/gate_21d_riemensperger_dopamine_mapping/results/dopamine_mapping_summary.json"
DEFAULT_EVIDENCE = ROOT / "experiments/gate_21a_riemensperger_evidence_lock/results/evidence_lock_summary.json"
DEFAULT_OUTPUT = ROOT / "experiments/gate_21e_riemensperger_disease"
RUNNER = ROOT / "scripts/run_neural_experiment.py"
FIELDS = (
    "seed", "status", "message", "burden", "median_planar_speed_mm_s", "distance_traveled_mm",
    "displacement_mm", "duration_s", "frame_count", "contact_detected", "finite_qc",
    "timestamp_monotonic", "joint_trajectory_max_delta", "action_trajectory_max_delta", "rollout_path",
)


def _row(seed: int, *, status: str, message: str, burden: float, output: Path, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {field: "" for field in FIELDS}
    row.update({"seed": seed, "status": status, "message": message, "burden": burden, "rollout_path": project_path(output / "rollout.npz")})
    if metrics:
        row.update(metrics)
    return row


def _write_report(*, status: str, rows: list[dict[str, Any]], blockers: list[str]) -> None:
    lines = [
        "# Gate 21E - Virtual dopamine-deficiency replication",
        "",
        f"**Trạng thái:** `{status}`",
        "",
        "Transform: reviewed dopamine-class-level presynaptic connectome-weight hypothesis.",
        "Calibration, holdout tuning và biological validation: `OFF`.",
        "",
    ]
    if blockers:
        lines.extend(["## Blocker", "", *[f"- `{item}`" for item in blockers], ""])
    if rows:
        lines.extend([
            "| Seed | Status | Burden | Median speed (mm/s) | Distance (mm) |",
            "| ---: | --- | ---: | ---: | ---: |",
            *[f"| {row['seed']} | `{row['status']}` | {row['burden']} | {row.get('median_planar_speed_mm_s', '')} | {row.get('distance_traveled_mm', '')} |" for row in rows],
            "",
        ])
    lines.extend([
        "Các metric chỉ được ghi sau rollout FlyGym thật và QC đạt. Video (nếu có) là supplementary computational artifact.",
        "",
    ])
    report_path = ROOT / "docs/replications/riemensperger_2011/gate_21e_virtual_dopamine_deficiency.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def run(*, config_path: Path, mapping_path: Path, evidence_path: Path, output: Path, brain_root: Path, platform_root: Path, brain_python: Path, runner_python: Path, dry_run: bool) -> str:
    config = read_yaml(config_path)
    output.mkdir(parents=True, exist_ok=True)
    blockers: list[str] = []
    try:
        require_status(evidence_path, "RIEMENSPERGER_2011_EVIDENCE_LOCKED")
    except (OSError, RuntimeError, ValueError) as exc:
        blockers.append(f"evidence:{exc}")
    try:
        require_status(mapping_path, "READY_FOR_RIEMENSPERGER_DISEASE_REPLICATION")
    except (OSError, RuntimeError, ValueError) as exc:
        blockers.append(f"mapping:{exc}")
    runtime = _runtime_blockers(brain_root=brain_root, platform_root=platform_root, brain_python=brain_python)
    if runtime:
        blockers.extend(runtime)
    seeds = [int(seed) for seed in config["seed_policy"]["seeds"]]
    burden = float(config["parameter_policy"]["default_candidate"])
    reference_config = _resolve(config["reference_condition_config"])
    if not reference_config.is_file():
        blockers.append(f"reference_condition_config_missing:{reference_config}")

    if dry_run or blockers:
        status = "NOT_EXECUTED_DRY_RUN" if dry_run and not blockers else "WAITING_DOPAMINE_MAPPING_REVIEW" if any(item.startswith("mapping:") for item in blockers) else "DOPAMINE_DEFICIENCY_VIRTUAL_REPLICATION_BLOCKED"
        write_json(output / "results/disease_execution_plan.json", {"status": status, "dry_run": dry_run, "seeds": seeds, "burden": burden, "blockers": blockers, "simulation_run": False, "data_fabricated": False})
        write_json(output / "manifests/disease_manifest.json", build_manifest(status=status, config_paths=[config_path], input_paths=[mapping_path, evidence_path, reference_config], extra={"simulation_run": False, "seed_list": seeds, "burden": burden, "blockers": blockers}))
        _write_report(status=status, rows=[], blockers=blockers + (["dry_run_requested"] if dry_run else []))
        return status

    healthy_config = read_yaml(_resolve(config["healthy_config"]))
    steps = int(healthy_config["duration"]["steps"])
    checkpoint_output = output / "checkpoint_materialization"
    checkpoint_status = materialize(
        brain_root=brain_root,
        condition_config=reference_config,
        age_days=float(config["age_days"]),
        burden=burden,
        output=checkpoint_output,
    )
    if checkpoint_status.get("status") != "CHECKPOINT_READY":
        status = "DOPAMINE_DEFICIENCY_VIRTUAL_REPLICATION_BLOCKED"
        write_json(output / "results/disease_execution_plan.json", {"status": status, "checkpoint_status": checkpoint_status, "simulation_run": False, "data_fabricated": False})
        write_json(output / "manifests/disease_manifest.json", build_manifest(status=status, config_paths=[config_path, reference_config], input_paths=[mapping_path, evidence_path], extra={"simulation_run": False, "checkpoint_status": checkpoint_status, "blockers": ["dopamine_checkpoint_not_ready"]}))
        _write_report(status=status, rows=[], blockers=["dopamine_checkpoint_not_ready"])
        return status
    prepared_checkpoint = checkpoint_output / "plastic_weights.pt"
    rows: list[dict[str, Any]] = []
    telemetry: list[dict[str, Any]] = []
    telemetry_path = output / "results/gpu_telemetry.json"
    write_json(telemetry_path, {"schema_version": "gate26-gpu-telemetry-v1", "records": telemetry})
    for seed in seeds:
        seed_output = output / "results" / f"seed_{seed:03d}"
        if seed_output.exists() and any(seed_output.iterdir()):
            raise RuntimeError(f"Refusing to overwrite existing seed output; no retry is allowed: {seed_output}")
        _assert_gpu_idle()
        gpu_before = _gpu_telemetry()
        command = [
            str(runner_python), str(RUNNER), "--brain-root", str(brain_root), "--platform-root", str(platform_root),
            "--brain-python", str(brain_python), "--prepared-checkpoint", str(prepared_checkpoint),
            "--seed", str(seed), "--steps", str(steps), "--device", str(healthy_config["platform_runtime"]["device"]),
            "--output", str(seed_output), "--stimulus", str(healthy_config["controller"]["stimulus"]),
            "--cpg-frequency-hz", str(healthy_config["controller"]["cpg_frequency_hz"]),
            "--artifact-profile", "GATE24E_MEMORY_SAFE",
        ]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        gpu_after = _gpu_telemetry()
        telemetry.append({"seed": seed, "before": gpu_before, "after": gpu_after})
        write_json(telemetry_path, {"schema_version": "gate26-gpu-telemetry-v1", "records": telemetry})
        (output / "logs").mkdir(parents=True, exist_ok=True)
        (output / "logs" / f"seed_{seed:03d}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        rollout = seed_output / "rollout.npz"
        if result.returncode or not rollout.is_file():
            rows.append(_row(seed, status="FAILED", message=f"runner_return_code={result.returncode}", burden=burden, output=seed_output))
            break
        try:
            metrics = rollout_seed_metrics(rollout)
            if not metrics["contact_detected"]:
                raise RuntimeError("no ground contact detected")
            rows.append(_row(seed, status="PASS", message="real FlyGym disease rollout", burden=burden, output=seed_output, metrics=metrics))
        except (OSError, RuntimeError, ValueError) as exc:
            rows.append(_row(seed, status="FAILED", message=str(exc), burden=burden, output=seed_output))
            break

    write_csv_rows(output / "metrics/disease_per_seed_metrics.csv", FIELDS, rows)
    passed = [row for row in rows if row["status"] == "PASS"]
    status = "DOPAMINE_DEFICIENCY_VIRTUAL_REPLICATION_PASS" if len(passed) == len(seeds) else "DOPAMINE_DEFICIENCY_VIRTUAL_REPLICATION_BLOCKED"
    summary: dict[str, Any] = {"status": status, "n_seeds_planned": len(seeds), "n_seeds_passed": len(passed), "burden": burden, "data_fabricated": False}
    if passed:
        summary["median_planar_speed_mm_s"] = sample_summary([float(row["median_planar_speed_mm_s"]) for row in passed])
        summary["distance_traveled_mm"] = sample_summary([float(row["distance_traveled_mm"]) for row in passed])
    write_json(output / "results/disease_summary.json", summary)
    write_json(output / "manifests/disease_manifest.json", build_manifest(status=status, config_paths=[config_path, reference_config], input_paths=[mapping_path, evidence_path, output / "metrics/disease_per_seed_metrics.csv", output / "results/disease_summary.json", telemetry_path, checkpoint_output / "riemensperger_dopamine_checkpoint_manifest.json"], extra={"simulation_run": True, "seed_list": seeds, "burden": burden, "mapping_sha256": sha256_file(mapping_path), "checkpoint_sha256": sha256_file(prepared_checkpoint), "output_sha256": sha256_file(output / "metrics/disease_per_seed_metrics.csv")}))
    _write_report(status=status, rows=rows, blockers=[])
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--brain-root", type=Path, default=ROOT / "external/fly-brain")
    parser.add_argument("--platform-root", type=Path, default=ROOT.parent / "drosophila-pd-flygym")
    parser.add_argument("--brain-python", type=Path, default=ROOT.parent / "drosophila-pd-flygym/.venv/Scripts/python.exe")
    parser.add_argument("--runner-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    status = run(config_path=_resolve(args.config), mapping_path=_resolve(args.mapping), evidence_path=_resolve(args.evidence), output=_resolve(args.output), brain_root=_resolve(args.brain_root), platform_root=_resolve(args.platform_root), brain_python=_resolve(args.brain_python), runner_python=_resolve(args.runner_python), dry_run=args.dry_run)
    print(f"Status: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
