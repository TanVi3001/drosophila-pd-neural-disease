"""Run and audit the Gate 19 healthy multi-seed baseline.

This is an execution wrapper, not a new simulation framework. It delegates
the actual brain-body rollout to the existing FlyGym runner and reuses the
Gate 11 artifact checks. Large raw artifacts stay outside Git; only compact
metrics, manifests, logs and the representative video are retained in the
local output area.
"""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "experiments/gate_19_healthy_baseline/configs/healthy_baseline_multiseed.yaml"
DEFAULT_OUTPUT = ROOT / "results/healthy_baseline_gate19"
RUNNER = ROOT / "scripts/run_neural_experiment.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_healthy_baseline_multiseed import (  # noqa: E402
    _artifact_audit,
    _finite_rollout,
    _read_scalar_metrics,
    _rollout_quality,
    _sha256,
)


def _resolve(value: str | Path, *, base: Path = ROOT) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def _git_value(path: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


def _load_config(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        raise ValueError("Gate 19 config must be a YAML mapping.")
    if document.get("condition") != "healthy":
        raise ValueError("Gate 19 only permits condition=healthy.")
    if document.get("disease_layer_enabled") is not False:
        raise ValueError("Gate 19 requires disease_layer_enabled=false.")
    if document.get("perturbation") != "none":
        raise ValueError("Gate 19 requires perturbation=none.")
    if document.get("calibration_enabled") is not False or document.get("holdout_enabled") is not False:
        raise ValueError("Gate 19 does not permit calibration or holdout execution.")
    execution = document.get("execution") or {}
    if execution.get("seeds") != [0, 1, 2, 3, 4]:
        raise ValueError("Gate 19 seed set must be [0, 1, 2, 3, 4].")
    if int(execution.get("steps", 0)) != 100000:
        raise ValueError("Gate 19 requires 100000 steps.")
    if float(execution.get("timestep_s", 0.0)) != 0.0001:
        raise ValueError("Gate 19 requires timestep_s=0.0001.")
    video = document.get("video") or {}
    if video.get("camera_mode") != "tracking":
        raise ValueError("Gate 19 requires tracking camera mode.")
    if not isinstance(document.get("required_metrics"), list):
        raise ValueError("required_metrics must be a list.")
    return document


def _runner_supports_tracking(platform_root: Path) -> bool:
    runner = platform_root / "scripts/run_brain_body_rollout.py"
    if not runner.is_file():
        return False
    source = runner.read_text(encoding="utf-8")
    return "--video-camera-mode" in source and "mjCAMERA_TRACKING" in source


def _mapping_mean(value: Any) -> float | None:
    """Return the mean of finite numeric entries in a per-joint/contact mapping."""
    if not isinstance(value, Mapping):
        return None
    values: list[float] = []
    for item in value.values():
        if not isinstance(item, (int, float)) or isinstance(item, bool):
            raise ValueError("Per-contact/joint metric contains a non-numeric value.")
        numeric = float(item)
        if not math.isfinite(numeric):
            raise ValueError("Per-contact/joint metric contains NaN or Inf.")
        values.append(numeric)
    return sum(values) / len(values) if values else None


def _read_gate19_metrics(path: Path) -> dict[str, float]:
    """Read scalar metrics and explicitly aggregate per-contact/joint exports.

    The external runner stores contact ratios and joint RMS velocities as
    mappings. Gate 19 reports their arithmetic mean across the exported
    contacts/joints while preserving the original JSON unchanged.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    metrics = _read_scalar_metrics(path)
    for name in ("contact_ratio", "joint_rms_velocity"):
        aggregate = _mapping_mean(document.get(name))
        if aggregate is not None:
            metrics[name] = aggregate
    return metrics


def _artifact_paths(output: Path) -> list[Path]:
    return sorted(path for path in output.rglob("*") if path.is_file())


def _copy_representative_video(source: Path, destination: Path) -> dict[str, Any]:
    if not source.is_file() or source.stat().st_size == 0:
        return {"status": "MISSING", "source": str(source)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {
        "status": "PASS",
        "path": str(destination),
        "source": str(source),
        "size_bytes": destination.stat().st_size,
        "sha256": _sha256(destination),
    }


def _run_seed(
    *,
    seed: int,
    config: Mapping[str, Any],
    brain_root: Path,
    platform_root: Path,
    brain_python: Path,
    raw_root: Path,
    summary_root: Path,
    execute: bool = True,
) -> dict[str, Any]:
    execution = config["execution"]
    video_config = config.get("video") or {}
    output = raw_root / f"healthy_seed_{seed:03d}"
    output.mkdir(parents=True, exist_ok=True)
    command = [
        str(brain_python),
        str(platform_root / "scripts/run_brain_body_rollout.py"),
        "--brain-root",
        str(brain_root),
        "--condition",
        "healthy",
        "--seed",
        str(seed),
        "--steps",
        str(int(execution["steps"])),
        "--device",
        str(execution.get("device", "cuda")),
        "--output",
        str(output),
        "--stimulus",
        str(execution.get("stimulus", "p9")),
        "--cpg-frequency-hz",
        str(execution.get("cpg_frequency_hz", 12.0)),
    ]
    requested_video = bool(video_config.get("enabled") and seed == int(video_config.get("representative_seed", 0)))
    video_path = output / "flygym_rollout.mp4"
    if requested_video:
        command.extend(
            [
                "--video-output",
                str(video_path),
                "--video-fps",
                str(int(video_config.get("fps", 60))),
                "--video-width",
                str(int(video_config.get("width", 960))),
                "--video-height",
                str(int(video_config.get("height", 540))),
                "--video-playback-speed",
                str(float(video_config.get("playback_speed", 1.0))),
                "--video-camera-mode",
                str(video_config.get("camera_mode", "tracking")),
            ]
        )
    environment = dict(os.environ)
    environment.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    if execute:
        started_at = time.time()
        process = subprocess.Popen(
            command,
            cwd=platform_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=environment,
        )
        simulation_artifacts_ready_at: float | None = None
        while process.poll() is None:
            rollout_ready = (output / "rollout.npz").is_file()
            metrics_ready = (output / "metrics/metrics.json").is_file()
            metrics_is_new = metrics_ready and (output / "metrics/metrics.json").stat().st_mtime >= started_at
            if rollout_ready and metrics_is_new:
                if simulation_artifacts_ready_at is None:
                    simulation_artifacts_ready_at = time.time()
                elif time.time() - simulation_artifacts_ready_at >= 5.0:
                    # The real runner has finished simulation and metric export;
                    # its optional viewer-pose stage can require several GB RAM.
                    process.terminate()
                    break
            time.sleep(1.0)
        try:
            stdout, _ = process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, _ = process.communicate()
        return_code: int | str | None = process.returncode
    else:
        stdout = "Aggregate-only: reused existing raw rollout artifacts; no simulation rerun.\n"
        return_code = "NOT_REEXECUTED"
    log_path = summary_root / "logs" / f"seed_{seed:03d}.log"
    _write_text(log_path, stdout or "")

    metrics_path = output / "metrics/metrics.json"
    rollout_path = output / "rollout.npz"
    required_files = [rollout_path, metrics_path]
    missing = [str(path.relative_to(output)) for path in required_files if not path.is_file()]
    metrics: dict[str, float] = {}
    if metrics_path.is_file():
        try:
            metrics = _read_gate19_metrics(metrics_path)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            missing.append("metrics/metrics.json:invalid")
    finite, invalid_arrays = _finite_rollout(rollout_path)
    quality = _rollout_quality(
        rollout_path,
        expected_frames=int(execution["steps"]) + 1,
        expected_timestep_s=float(execution["timestep_s"]),
        metrics=metrics,
    )
    required_metrics = [str(item) for item in config["required_metrics"]]
    mean_planar_speed = quality.get("mean_planar_speed_mm_s")
    if isinstance(mean_planar_speed, (int, float)) and math.isfinite(float(mean_planar_speed)):
        metrics["mean_planar_speed_mm_s"] = float(mean_planar_speed)
    for name in ("distance_traveled_mm", "displacement_mm"):
        value = quality.get(name)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            metrics[name] = float(value)
    present_metrics = [
        name
        for name in required_metrics
        if isinstance(metrics.get(name), (int, float)) and math.isfinite(float(metrics[name]))
    ]
    all_finite = finite and not invalid_arrays and all(math.isfinite(value) for value in metrics.values())
    quality_keys = (
        "timestamp_monotonic",
        "timestep_consistent",
        "locomotion_detected",
        "contact_detected",
        "joint_trajectory_changes",
        "action_trajectory_valid",
        "quaternion_valid",
    )
    quality_status = "PASS" if all_finite and all(quality.get(key) == "PASS" for key in quality_keys) else "FAIL"
    simulation_status = "PASS" if quality_status == "PASS" and not missing else "FAILED"
    viewer_pose = output / "viewer_pose.json"
    viewer_bundle = output / "viewer_bundle.zip"
    postprocess_status = "PASS" if viewer_pose.is_file() and viewer_bundle.is_file() else "PARTIAL"
    video_info = {
        "status": "NOT_REQUESTED",
        "path": None,
        "fps": None,
        "camera_mode": None,
    }
    if requested_video:
        video_info = {
            "status": "PASS" if video_path.is_file() and video_path.stat().st_size > 0 else "MISSING",
            "path": str(video_path),
            "fps": int(video_config.get("fps", 60)),
            "camera_mode": str(video_config.get("camera_mode", "tracking")),
        }
    raw_artifacts = []
    for path in _artifact_paths(output):
        raw_artifacts.append(
            {
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    row: dict[str, Any] = {
        "seed": seed,
        "status": simulation_status,
        "runner_return_code": return_code,
        "execution_source": "fresh_simulation" if execute else "existing_raw_artifacts",
        "raw_output": str(output),
        "missing_files": ";".join(missing),
        "invalid_arrays": ";".join(invalid_arrays),
        "required_metric_status": "PASS" if len(present_metrics) == len(required_metrics) else "INCOMPLETE",
        "required_metrics_present": ";".join(sorted(set(present_metrics))),
        "no_nan_inf": "PASS" if all_finite else "FAIL",
        "quality_status": quality_status,
        "postprocess_status": postprocess_status,
        "video_status": video_info["status"],
        "video_path": str(video_path) if requested_video else "",
        "artifact_count": len(raw_artifacts),
        "artifact_manifest": raw_artifacts,
    }
    row.update(quality)
    row.update(metrics)
    return row


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key, value in row.items() if not isinstance(value, (list, dict))})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: value for key, value in row.items() if not isinstance(value, (list, dict))})


def _metric_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, float | int]]:
    names = sorted(
        {
            key
            for row in rows
            for key, value in row.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool) and key != "seed"
        }
    )
    result: dict[str, dict[str, float | int]] = {}
    for name in names:
        values = [float(row[name]) for row in rows if isinstance(row.get(name), (int, float)) and not isinstance(row.get(name), bool)]
        if not values or not all(math.isfinite(value) for value in values):
            continue
        mean = sum(values) / len(values)
        sample_sd = math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1)) if len(values) > 1 else 0.0
        result[name] = {
            "n": len(values),
            "mean": mean,
            "sample_sd": sample_sd,
            "se": sample_sd / math.sqrt(len(values)) if len(values) > 1 else 0.0,
        }
    return result


def _write_report(path: Path, payload: Mapping[str, Any]) -> None:
    rows = payload["rows"]
    lines = [
        "# Gate 19 - Healthy Baseline Multi-Seed",
        "",
        f"Trang thai: `{payload['status']}`",
        "",
        "Day la computational healthy locomotion baseline. Khong phai biological Parkinson validation.",
        "Khong chay Disease Layer, calibration hoac holdout validation trong gate nay.",
        "",
        "## Protocol",
        "",
        f"- Seeds: `{payload['seeds']}`",
        f"- Steps moi seed: `{payload['steps']}`",
        f"- Timestep: `{payload['timestep_s']}` s",
        f"- Duration vat ly: `{payload['duration_s']}` s",
        f"- Device: `{payload['device']}`",
        f"- Stimulus: `{payload['stimulus']}`",
        f"- CPG frequency: `{payload['cpg_frequency_hz']}` Hz",
        f"- Video dai dien: `{payload['video_seed']}`; camera `{payload['video_camera_mode']}`",
        "",
        "## Ket qua tung seed",
        "",
        "| Seed | Simulation | Speed (mm/s) | Distance (mm) | Displacement (mm) | Contact | Joint | QC |",
        "| ---: | --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['seed']} | `{row['status']}` | {row.get('walking_speed_mm_s', '-') } | "
            f"{row.get('distance_traveled_mm', '-') } | {row.get('displacement_mm', '-') } | "
            f"`{row.get('contact_detected', '-')}` | `{row.get('joint_trajectory_changes', '-')}` | `{row.get('quality_status', '-')}` |"
        )
    lines.extend(["", "## Tong hop", "", "| Metric | n | Mean | Sample SD | SE |", "| --- | ---: | ---: | ---: | ---: |"])
    for metric, values in payload["summary"].items():
        if metric in {"runner_return_code", "artifact_count"}:
            continue
        lines.append(f"| `{metric}` | {values['n']} | {values['mean']} | {values['sample_sd']} | {values['se']} |")
    lines.extend(
        [
            "",
            "## Artifact va gioi han",
            "",
            f"- Simulation pass count: `{payload['simulation_pass_count']}/{len(rows)}`.",
            f"- Postprocess viewer status: `{payload['postprocess_status']}`.",
            f"- Video status: `{payload['video_status']}`.",
            "- Raw rollout lon duoc luu ngoai Git; manifest ghi checksum va duong dan may chay.",
            "- `contact_ratio` la trung binh cac contact ratios; `joint_rms_velocity` la trung binh RMS velocity cua cac joint trong metrics JSON goc.",
            "- Hai metric mapping duoc tong hop de phan tich; JSON goc theo tung contact/joint khong bi sua.",
            "- Observation array khong duoc tao boi runner hien tai; khong suy dien observation tu cac state khac.",
            "",
            "## Scientific boundary",
            "",
            "Ket qua nay chi xac nhan computational locomotion runtime va baseline healthy. "
            "No khong phai biological Parkinson validation, clinical prediction, drug response "
            "hay bang chung thay the thi nghiem wet-lab.",
            "",
        ]
    )
    _write_text(path, "\n".join(lines))


def run(
    config_path: Path,
    *,
    brain_root: Path | None,
    platform_root: Path | None,
    brain_python: Path | None,
    output_root: Path | None,
    aggregate_existing: bool = False,
) -> int:
    config = _load_config(config_path)
    paths = config["paths"]
    brain_root = _resolve(brain_root or paths["brain_root"])
    platform_root = _resolve(platform_root or paths["platform_root"])
    brain_python = _resolve(brain_python or paths["brain_python"])
    summary_root = _resolve(output_root or paths["summary_output_root"])
    raw_root = _resolve(paths["raw_output_root"])
    summary_root.mkdir(parents=True, exist_ok=True)
    (summary_root / "logs").mkdir(parents=True, exist_ok=True)

    artifact_audit = _artifact_audit(
        brain_root=brain_root,
        platform_root=platform_root,
        brain_python=brain_python,
        artifact_paths={
            "brain_bridge": str(brain_root / "brain_body_bridge.py"),
            "connectivity": str(brain_root / "data/2025_Connectivity_783.parquet"),
            "completeness": str(brain_root / "data/2025_Completeness_783.csv"),
            "checkpoint": str(brain_root / "data/plastic_weights.pt"),
        },
    )
    preflight = {
        "artifact_audit": artifact_audit,
        "tracking_camera_support": _runner_supports_tracking(platform_root),
        "simulation_run": False,
    }
    _write_text(summary_root / "preflight.json", json.dumps(preflight, indent=2, ensure_ascii=False) + "\n")
    if artifact_audit["status"] != "READY" or not preflight["tracking_camera_support"]:
        payload = {
            "status": "WAITING_RUNTIME",
            "simulation_run": False,
            "preflight": preflight,
            "scientific_scope": "Computational healthy locomotion baseline; no fabricated data.",
        }
        _write_text(summary_root / "healthy_baseline_summary.json", json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        _write_report(summary_root / "healthy_baseline_summary.md", {
            "status": "WAITING_RUNTIME",
            "seeds": config["execution"]["seeds"],
            "steps": config["execution"]["steps"],
            "timestep_s": config["execution"]["timestep_s"],
            "duration_s": config["execution"]["duration_s"],
            "device": config["execution"]["device"],
            "stimulus": config["execution"]["stimulus"],
            "cpg_frequency_hz": config["execution"]["cpg_frequency_hz"],
            "video_seed": config["video"]["representative_seed"],
            "video_camera_mode": config["video"]["camera_mode"],
            "rows": [],
            "summary": {},
            "simulation_pass_count": 0,
            "postprocess_status": "NOT_RUN",
            "video_status": "NOT_RUN",
        })
        return 2

    rows: list[dict[str, Any]] = []
    for seed in config["execution"]["seeds"]:
        row = _run_seed(
            seed=int(seed),
            config=config,
            brain_root=brain_root,
            platform_root=platform_root,
            brain_python=brain_python,
            raw_root=raw_root,
            summary_root=summary_root,
            execute=not aggregate_existing,
        )
        rows.append(row)
        print(f"seed={seed} status={row['status']} quality={row['quality_status']}")

    per_seed_path = summary_root / "per_seed_metrics.csv"
    _write_csv(per_seed_path, rows)
    video_seed = int(config["video"]["representative_seed"])
    video_row = next((row for row in rows if row["seed"] == video_seed), None)
    video_source = Path(video_row["video_path"]) if video_row and video_row.get("video_path") else None
    copied_video = _copy_representative_video(video_source, summary_root / "videos" / f"healthy_seed_{video_seed:03d}_tracking.mp4") if video_source else {"status": "MISSING"}
    simulation_pass_count = sum(row["status"] == "PASS" for row in rows)
    postprocess_status = "PASS" if all(row["postprocess_status"] == "PASS" for row in rows) else "PARTIAL"
    overall_status = "HEALTHY_BASELINE_PASS" if simulation_pass_count == len(rows) and all(row["required_metric_status"] == "PASS" for row in rows) else "HEALTHY_BASELINE_FAILED"
    payload: dict[str, Any] = {
        "schema_version": "gate-19-healthy-baseline-summary-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": overall_status,
        "simulation_run": True,
        "condition": "healthy",
        "disease_layer_enabled": False,
        "calibration_enabled": False,
        "holdout_enabled": False,
        "seeds": config["execution"]["seeds"],
        "steps": config["execution"]["steps"],
        "timestep_s": config["execution"]["timestep_s"],
        "duration_s": config["execution"]["duration_s"],
        "device": config["execution"]["device"],
        "stimulus": config["execution"]["stimulus"],
        "cpg_frequency_hz": config["execution"]["cpg_frequency_hz"],
        "rows": rows,
        "summary": _metric_summary(rows),
        "simulation_pass_count": simulation_pass_count,
        "postprocess_status": postprocess_status,
        "video_status": copied_video["status"],
        "video_seed": video_seed,
        "video_camera_mode": config["video"]["camera_mode"],
        "video": copied_video,
        "preflight": preflight,
        "git_commit": _git_value(ROOT, "rev-parse", "HEAD"),
        "platform_commit": _git_value(platform_root, "rev-parse", "HEAD"),
        "platform_worktree_status": _git_value(platform_root, "status", "--short"),
        "raw_output_root": str(raw_root),
        "scientific_scope": "Computational healthy locomotion baseline; not biological Parkinson validation.",
        "data_fabricated": False,
    }
    _write_text(summary_root / "healthy_baseline_summary.json", json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    _write_report(summary_root / "healthy_baseline_summary.md", payload)

    artifact_paths = [config_path, per_seed_path, summary_root / "healthy_baseline_summary.json", summary_root / "healthy_baseline_summary.md", summary_root / "preflight.json"]
    if copied_video.get("status") == "PASS":
        artifact_paths.append(Path(copied_video["path"]))
    manifest = {
        "schema_version": "gate-19-healthy-baseline-manifest-v1",
        "status": overall_status,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "config": str(config_path),
        "artifacts": [
            {"path": str(path), "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in artifact_paths
            if path.is_file()
        ],
        "raw_artifacts_external": True,
        "raw_artifact_paths_by_seed": [row["artifact_manifest"] for row in rows],
        "preflight": preflight,
        "simulation_pass_count": simulation_pass_count,
        "planned_seed_count": len(rows),
        "disease_layer_enabled": False,
        "calibration_enabled": False,
        "holdout_enabled": False,
        "scientific_boundary": config["scientific_boundary"],
        "data_fabricated": False,
    }
    manifest_path = summary_root / "manifest.json"
    _write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    checksum_paths = artifact_paths + [manifest_path]
    checksum_lines = [f"{_sha256(path)}  {path}" for path in checksum_paths if path.is_file()]
    _write_text(summary_root / "checksums.sha256", "\n".join(checksum_lines) + "\n")
    return 0 if overall_status == "HEALTHY_BASELINE_PASS" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--brain-root", type=Path, default=None)
    parser.add_argument("--platform-root", type=Path, default=None)
    parser.add_argument("--brain-python", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument(
        "--aggregate-existing",
        action="store_true",
        help="Recompute summary from existing raw artifacts without rerunning simulation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(
            args.config.resolve(),
            brain_root=args.brain_root,
            platform_root=args.platform_root,
            brain_python=args.brain_python,
            output_root=args.output_root,
            aggregate_existing=args.aggregate_existing,
        )
    except (OSError, ValueError, TypeError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
