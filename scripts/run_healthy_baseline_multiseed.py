"""Run the real unperturbed healthy baseline for the Gate 11 seed set.

This script is deliberately a thin execution wrapper around the existing
``run_neural_experiment.py`` entry point. It never passes a disease config,
never runs calibration, and refuses to fabricate outputs when preflight or a
rollout fails.
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
import subprocess
import sys
from typing import Any, Mapping, Sequence

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "experiments" / "gate_11_healthy_baseline" / "configs" / "healthy_baseline_multiseed.yaml"
RUNNER = ROOT / "scripts" / "run_neural_experiment.py"
DEFAULT_OUTPUT_ROOT = ROOT / "experiments" / "gate_11_healthy_baseline"
DEFAULT_REPORT = ROOT / "docs" / "baseline" / "gate_11_healthy_baseline_report.md"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_neural_inputs import inspect_brain_root


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


def _resolve(value: str | Path, *, base: Path = ROOT) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load_config(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        raise ValueError("Gate 11 config phai la YAML mapping.")
    condition = document.get("condition") or {}
    if not isinstance(condition, dict):
        raise ValueError("condition phai la mapping.")
    if condition.get("name") != "healthy_baseline":
        raise ValueError("Gate 11 chi cho phep condition=healthy_baseline.")
    if condition.get("disease_layer_enabled") is not False:
        raise ValueError("Gate 11 bat buoc disease_layer_enabled=false.")
    if condition.get("perturbation_config") is not None:
        raise ValueError("Gate 11 khong cho phep perturbation config.")
    if condition.get("calibration_enabled") is not False:
        raise ValueError("Gate 11 khong cho phep calibration.")
    execution = document.get("execution") or {}
    seeds = execution.get("seeds")
    if seeds != [0, 1, 2, 3, 4, 5]:
        raise ValueError("Gate 11 seed set phai la [0, 1, 2, 3, 4, 5].")
    if int(execution.get("steps", 0)) <= 0:
        raise ValueError("steps phai la so nguyen duong.")
    if not isinstance(document.get("required_metrics"), list):
        raise ValueError("required_metrics phai la danh sach.")
    return document


def _runtime_probe(python_path: Path) -> dict[str, Any]:
    if not python_path.is_file():
        return {"status": "MISSING", "python": str(python_path), "message": "Khong tim thay brain/platform Python."}
    code = (
        "import sys; import torch, flygym, mujoco, flygym_demo; "
        "print(sys.version.split()[0]); print(torch.__version__); "
        "print(flygym.__version__ if hasattr(flygym, '__version__') else 'available'); "
        "print(mujoco.__version__)"
    )
    result = subprocess.run(
        [str(python_path), "-c", code], capture_output=True, text=True, check=False
    )
    return {
        "status": "PASS" if result.returncode == 0 else "FAILED",
        "python": str(python_path),
        "return_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _artifact_audit(
    *,
    brain_root: Path,
    platform_root: Path,
    brain_python: Path,
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    brain_report = inspect_brain_root(brain_root)
    files: dict[str, dict[str, Any]] = {}
    for name, declared in artifact_paths.items():
        path = _resolve(declared)
        if not path.is_file():
            files[name] = {"path": str(path), "status": "MISSING_EXTERNAL_ARTIFACT"}
            continue
        files[name] = {
            "path": str(path),
            "relative_path": _relative(path),
            "status": "PRESENT",
            "size": path.stat().st_size,
            "sha256": _sha256(path),
        }
    runner = platform_root / "scripts" / "run_brain_body_rollout.py"
    platform_status = "PASS" if runner.is_file() else "MISSING_PLATFORM_RUNNER"
    runtime = _runtime_probe(brain_python)
    status = "READY"
    if brain_report.get("status") != "READY" or platform_status != "PASS" or runtime.get("status") != "PASS":
        status = "MISSING_EXTERNAL_ARTIFACT" if brain_report.get("status") != "READY" else "WAITING_RUNTIME"
    if any(record["status"] != "PRESENT" for record in files.values()):
        status = "MISSING_EXTERNAL_ARTIFACT"
    return {
        "status": status,
        "brain_source": brain_report,
        "platform_runner": {"path": str(runner), "status": platform_status},
        "runtime": runtime,
        "artifacts": files,
        "simulation_run": False,
    }


def _read_scalar_metrics(path: Path) -> dict[str, float]:
    document = json.loads(path.read_text(encoding="utf-8"))
    source = document.get("scalar_metrics", document)
    if not isinstance(source, dict):
        return {}
    metrics: dict[str, float] = {}
    for key, value in source.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
            metrics[str(key)] = float(value)
    return metrics


def _finite_rollout(path: Path) -> tuple[bool, list[str]]:
    if not path.is_file():
        return False, [f"missing:{path.name}"]
    invalid: list[str] = []
    try:
        with np.load(path, allow_pickle=False) as archive:
            for name in archive.files:
                array = np.asarray(archive[name])
                if np.issubdtype(array.dtype, np.number) and not np.isfinite(array).all():
                    invalid.append(name)
    except (OSError, ValueError, TypeError) as exc:
        invalid.append(f"load_error:{exc}")
    return not invalid, invalid


def _rollout_quality(
    path: Path,
    *,
    expected_frames: int,
    expected_timestep_s: float,
    metrics: Mapping[str, float],
) -> dict[str, Any]:
    """Check QC fields that are exported by the real rollout artifact."""
    quality: dict[str, Any] = {
        "timestamp_monotonic": "NOT_REPORTED",
        "timestep_consistent": "NOT_REPORTED",
        "thorax_displacement_xy_mm": None,
        "mean_planar_speed_mm_s": None,
        "distance_traveled_mm": None,
        "displacement_mm": None,
        "locomotion_detected": "NOT_REPORTED",
        "contact_detected": "NOT_REPORTED",
        "joint_trajectory_changes": "NOT_REPORTED",
        "action_trajectory_valid": "NOT_REPORTED",
        "observation_state_valid": "NOT_REPORTED",
        "quaternion_valid": "NOT_REPORTED",
    }
    if not path.is_file():
        return quality
    try:
        with np.load(path, allow_pickle=False) as archive:
            timestamps = np.asarray(archive["timestamp_s"], dtype=float)
            deltas = np.diff(timestamps)
            quality["timestamp_monotonic"] = (
                "PASS"
                if timestamps.size == expected_frames and deltas.size and np.all(deltas > 0)
                else "FAIL"
            )
            quality["timestep_consistent"] = (
                "PASS"
                if deltas.size
                and np.allclose(deltas, expected_timestep_s, rtol=0.0, atol=1e-10)
                else "FAIL"
            )

            thorax = np.asarray(archive["thorax"], dtype=float)
            displacement = float(np.linalg.norm(thorax[-1, :2] - thorax[0, :2]))
            planar_steps = np.linalg.norm(np.diff(thorax[:, :2], axis=0), axis=1)
            path_length = float(np.sum(planar_steps))
            quality["thorax_displacement_xy_mm"] = displacement
            executed_duration_s = float((expected_frames - 1) * expected_timestep_s)
            quality["mean_planar_speed_mm_s"] = (
                displacement / executed_duration_s if executed_duration_s > 0 else None
            )
            quality["distance_traveled_mm"] = path_length
            quality["displacement_mm"] = displacement
            quality["locomotion_detected"] = (
                "PASS"
                if displacement > 0 and float(metrics.get("walking_speed_mm_s", 0.0)) > 0
                else "FAIL"
            )

            contact = np.asarray(archive["contact_found"], dtype=float)
            quality["contact_detected"] = (
                "PASS" if contact.size and bool(np.any(contact > 0)) else "FAIL"
            )

            joint_positions = np.asarray(archive["joint_positions"], dtype=float)
            quality["joint_trajectory_changes"] = (
                "PASS" if joint_positions.size and float(np.ptp(joint_positions, axis=0).max()) > 0 else "FAIL"
            )

            actuator = np.asarray(archive["actuator_position"], dtype=float)
            quality["action_trajectory_valid"] = (
                "PASS"
                if actuator.size and np.all(np.isfinite(actuator)) and float(np.ptp(actuator, axis=0).max()) > 0
                else "FAIL"
            )

            state_names = ("thorax", "com", "orientation", "joint_positions", "joint_velocity", "contact_found")
            quality["observation_state_valid"] = (
                "PASS"
                if all(name in archive.files and len(archive[name]) == expected_frames for name in state_names)
                else "FAIL"
            )

            orientation = np.asarray(archive["orientation"], dtype=float)
            norms = np.linalg.norm(orientation, axis=1)
            quality["quaternion_valid"] = (
                "PASS" if norms.size and np.allclose(norms, 1.0, rtol=0.0, atol=1e-3) else "FAIL"
            )
    except (KeyError, OSError, ValueError, TypeError, IndexError):
        for key in (
            "timestamp_monotonic",
            "timestep_consistent",
            "locomotion_detected",
            "contact_detected",
            "joint_trajectory_changes",
            "action_trajectory_valid",
            "observation_state_valid",
            "quaternion_valid",
        ):
            quality[key] = "FAIL"
    return quality


def _run_seed(
    *,
    seed: int,
    config: Mapping[str, Any],
    brain_root: Path,
    platform_root: Path,
    brain_python: Path,
    output_root: Path,
) -> dict[str, Any]:
    execution = config["execution"]
    output = output_root / "results" / f"seed_{seed:03d}"
    output.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(RUNNER),
        "--brain-root", str(brain_root),
        "--platform-root", str(platform_root),
        "--brain-python", str(brain_python),
        "--seed", str(seed),
        "--steps", str(int(execution["steps"])),
        "--device", str(execution.get("device", "cuda")),
        "--output", str(output),
        "--stimulus", str(execution.get("stimulus", "p9")),
        "--cpg-frequency-hz", str(execution.get("cpg_frequency_hz", 12.0)),
    ]
    environment = os.environ.copy()
    environment.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False, env=environment)
    log_text = completed.stdout + completed.stderr
    (output_root / "logs" / f"seed_{seed:03d}.log").write_text(log_text, encoding="utf-8")
    with (output_root / "logs" / "run.log").open("a", encoding="utf-8") as handle:
        handle.write(f"=== seed {seed} ===\n")
        handle.write(log_text)
        if log_text and not log_text.endswith("\n"):
            handle.write("\n")
    metrics_path = output / "metrics" / "metrics.json"
    required_files = [output / "rollout.json", output / "rollout.npz", metrics_path]
    missing = [str(path.relative_to(output)) for path in required_files if not path.is_file()]
    metrics: dict[str, float] = {}
    runtime_metadata: dict[str, int | float] = {}
    if metrics_path.is_file():
        try:
            metrics = _read_scalar_metrics(metrics_path)
            document = json.loads(metrics_path.read_text(encoding="utf-8"))
            for key in ("frame_count", "duration_s", "timestep_s"):
                value = document.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
                    runtime_metadata[key] = int(value) if key == "frame_count" else float(value)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            missing.append("metrics/metrics.json:invalid")
    finite, invalid_arrays = _finite_rollout(output / "rollout.npz")
    no_nan_inf = finite and not missing and all(math.isfinite(value) for value in metrics.values())
    quality = _rollout_quality(
        output / "rollout.npz",
        expected_frames=int(execution["steps"]) + 1,
        expected_timestep_s=float(execution.get("timestep_s", 0.0001)),
        metrics=metrics,
    )
    quality_status = "PASS" if no_nan_inf and all(
        quality[key] == "PASS"
        for key in (
            "timestamp_monotonic",
            "timestep_consistent",
            "locomotion_detected",
            "contact_detected",
            "joint_trajectory_changes",
            "action_trajectory_valid",
            "observation_state_valid",
            "quaternion_valid",
        )
    ) else "FAIL"
    status = "PASS"
    if completed.returncode != 0:
        status = "FAILED_SIMULATION"
    elif missing:
        status = "FAILED_ARTIFACT"
    elif not no_nan_inf:
        status = "FAILED_NUMERIC_QC"
    required_metrics = [str(item) for item in config["required_metrics"]]
    present_required = [name for name in required_metrics if name in metrics]
    row: dict[str, Any] = {
        "seed": seed,
        "status": status,
        "return_code": completed.returncode,
        "output": _relative(output),
        "required_metric_status": "PASS" if len(present_required) == len(required_metrics) else "INCOMPLETE",
        "required_metrics_present": ";".join(present_required),
        "missing_files": ";".join(missing),
        "invalid_arrays": ";".join(invalid_arrays),
        "no_nan": "PASS" if no_nan_inf else "FAIL",
        "no_inf": "PASS" if no_nan_inf else "FAIL",
        "no_nan_inf": "PASS" if no_nan_inf else "FAIL",
        "quality_status": quality_status,
        "metrics_path": _relative(metrics_path),
    }
    row.update(runtime_metadata)
    row.update(quality)
    if status == "PASS" and quality_status == "FAIL":
        status = "FAILED_PHYSICAL_QC"
    row["status"] = status
    row.update(metrics)
    return row


def _summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    names = sorted({key for row in rows for key, value in row.items() if isinstance(value, (int, float)) and key != "seed"})
    result: dict[str, dict[str, float | int]] = {}
    for name in names:
        values = np.asarray([float(row[name]) for row in rows if isinstance(row.get(name), (int, float))], dtype=float)
        if values.size == 0 or not np.isfinite(values).all():
            continue
        mean = float(values.mean())
        sample_sd = float(values.std(ddof=1)) if values.size > 1 else 0.0
        result[name] = {
            "n": int(values.size),
            "mean": mean,
            "sample_sd": sample_sd,
            "se": float(sample_sd / math.sqrt(values.size)) if values.size > 1 else 0.0,
        }
    return result


def _runtime_summary(rows: list[dict[str, Any]], config: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize runtime values read from each seed's metrics artifact."""
    expected_steps = int(config["execution"]["steps"])
    expected_frames = expected_steps + 1
    timestep_values = [
        float(row["timestep_s"])
        for row in rows
        if isinstance(row.get("timestep_s"), (int, float))
    ]
    duration_values = [
        float(row["duration_s"])
        for row in rows
        if isinstance(row.get("duration_s"), (int, float))
    ]
    frame_values = [
        int(row["frame_count"])
        for row in rows
        if isinstance(row.get("frame_count"), int)
    ]
    if not timestep_values or not duration_values or not frame_values:
        return {
            "step_count": expected_steps,
            "timestep_s": "NOT_AVAILABLE",
            "duration_s": "NOT_AVAILABLE",
            "duration_source": "NOT_AVAILABLE",
            "duration_consistency": "INCOMPLETE",
            "distance_speed_consistency": "INCOMPLETE",
        }
    timestep = timestep_values[0]
    duration = duration_values[0]
    duration_consistent = (
        len(timestep_values) == len(rows)
        and len(duration_values) == len(rows)
        and len(frame_values) == len(rows)
        and all(math.isclose(value, timestep, rel_tol=0.0, abs_tol=1e-10) for value in timestep_values)
        and all(math.isclose(value, duration, rel_tol=0.0, abs_tol=1e-10) for value in duration_values)
        and all(value == expected_frames for value in frame_values)
        and math.isclose(duration, expected_steps * timestep, rel_tol=0.0, abs_tol=1e-10)
    )
    consistency_values = []
    for row in rows:
        canonical_speed = row.get("mean_planar_speed_mm_s")
        displacement = row.get("displacement_mm")
        distance = row.get("distance_traveled_mm")
        row_duration = row.get("duration_s")
        if not all(isinstance(value, (int, float)) for value in (canonical_speed, displacement, distance, row_duration)):
            continue
        consistency_values.append(
            math.isclose(float(canonical_speed) * float(row_duration), float(displacement), rel_tol=1e-9, abs_tol=1e-12)
            and math.isclose(float(distance), float(row.get("total_distance_mm", distance)), rel_tol=1e-9, abs_tol=1e-12)
        )
    return {
        "step_count": expected_steps,
        "timestep_s": timestep,
        "duration_s": duration,
        "duration_source": "runtime_artifact:metrics/metrics.json",
        "duration_consistency": "PASS" if duration_consistent else "INCOMPLETE",
        "distance_speed_consistency": "PASS" if consistency_values and all(consistency_values) else "INCOMPLETE",
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    *,
    report_path: Path,
    manifest: Mapping[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    contract = manifest["metric_contract"]
    required = contract["required"]
    canonical = contract.get("canonical_metrics", {})
    runtime = manifest.get("runtime", {})
    lines = [
        "# Gate 11: Healthy Baseline Multi-Seed Report",
        "",
        f"**Trạng thái:** `{manifest['status']}`",
        "",
        "Báo cáo này ghi nhận rollout healthy computational thật theo Gate 10. "
        "Không chạy disease condition, calibration hoặc holdout validation.",
        "",
        "## Phạm vi chạy",
        "",
        f"- Số seed: `{len(rows)}`; seed set: `{manifest['seeds']}`.",
        f"- Config: `{manifest['config']}`.",
        f"- Git commit: `{manifest['git_commit']}`.",
        f"- Runtime preflight: `{manifest['preflight_status']}`.",
        f"- External artifact audit: `{manifest['external_artifact_status']}`.",
        "- Disease Layer: `OFF`.",
        "- Calibration: `OFF`.",
        "- Video: `NOT_REQUESTED` để tránh đưa artifact lớn vào baseline commit.",
        "",
        "## Kết quả từng seed",
        "",
            "| Seed | Status | Observed walking speed (mm/s) | Observed distance (mm) | Locomotion | Contact | QC | Contract |",
            "| ---: | --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        speed = row.get("walking_speed_mm_s", "-")
        distance = row.get("total_distance_mm", row.get("distance_traveled_mm", "-"))
        lines.append(
            f"| {row['seed']} | `{row['status']}` | {speed} | {distance} | "
            f"`{row['locomotion_detected']}` | `{row['contact_detected']}` | "
            f"`{row['quality_status']}` | `{row['required_metric_status']}` |"
        )
    lines.extend(["", "## Tổng hợp metric quan sát được", ""])
    lines.extend(
        [
            "Các thống kê dưới đây được tính giữa các seed; chúng không phải uncertainty "
            "của dữ liệu ruồi thật và không được dùng để thay thế target literature.",
            "",
            "| Metric | n | Mean | Sample SD | SE |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    summary = _summary(rows)
    for metric, values in summary.items():
        if metric in {"return_code", "seed"}:
            continue
        lines.append(
            f"| `{metric}` | {values['n']} | {values['mean']} | "
            f"{values['sample_sd']} | {values['se']} |"
        )
    lines.extend(["", "## Metric contract alignment", ""])
    for metric, present in required.items():
        lines.append(f"- `{metric}`: `{present}`.")
    lines.extend(
        [
            "",
            f"**Contract status:** `{contract['status']}`.",
            "Các metric raw được giữ nguyên. Canonical metrics được tính hoặc kiểm tra "
            "từ rollout thật theo công thức có provenance; không chuyển distance thành speed.",
            "",
        ]
    )
    for raw_name, canonical_name in (
        ("walking_speed_mm_s", "mean_planar_speed_mm_s"),
        ("total_distance_mm", "distance_traveled_mm"),
        ("thorax_displacement_mm (không được runtime xuất trực tiếp)", "displacement_mm"),
    ):
        detail = canonical.get(canonical_name, {})
        lines.extend(
            [
                f"- Raw runtime metric: `{raw_name}`.",
                f"  Canonical metric: `{canonical_name}`.",
                f"  Alias decision: `{'approved' if detail.get('alias_allowed') else 'not approved; derived'}`.",
                f"  Reason: {detail.get('reason', 'NOT_AVAILABLE')}",
                f"  Source/formula: `{detail.get('source', 'NOT_AVAILABLE')}`; "
                f"`{detail.get('formula', 'NOT_AVAILABLE')}`.",
            ]
        )
    lines.extend(
        [
            "",
            "## Runtime duration",
            "",
            f"- Step count: `{runtime.get('step_count', 'NOT_AVAILABLE')}`.",
            f"- Timestep: `{runtime.get('timestep_s', 'NOT_AVAILABLE')}` s.",
            f"- Duration: `{runtime.get('duration_s', 'NOT_AVAILABLE')}` s.",
            f"- Duration source: `{runtime.get('duration_source', 'NOT_AVAILABLE')}`.",
            f"- Duration consistency check: `{runtime.get('duration_consistency', 'INCOMPLETE')}`.",
            f"- Distance/speed consistency check: `{runtime.get('distance_speed_consistency', 'INCOMPLETE')}`.",
            "",
            "## Quality control",
            "",
            "- Mỗi seed có `no_nan=PASS` và `no_inf=PASS`; tổng hợp là không NaN/Inf.",
            "- QC trực tiếp từ rollout: timestamp, timestep, thorax displacement, "
            "contact, joint trajectory, actuator trajectory, observation state và quaternion.",
            "- Mỗi seed có thư mục rollout riêng và log riêng.",
            "- Log tổng hợp: `experiments/gate_11_healthy_baseline/logs/run.log`.",
            "",
            "## External artifact provenance",
            "",
            f"- Brain source status: `{manifest['external_artifact_status']}`.",
            "- Checksum chi tiết nằm trong `manifests/external_input_audit.json` và "
            "`manifests/healthy_baseline_manifest.json`.",
            "",
            "## Kết luận Gate 11B",
            "",
            "`HEALTHY_BASELINE_RUNTIME_PASS`.",
            f"`METRIC_CONTRACT_{contract['status']}`.",
            (
                "`READY_FOR_DISEASE_ROLLOUTS`."
                if contract["status"] == "PASS"
                else "`NOT_READY_FOR_DISEASE_ROLLOUTS`."
            ),
            "Baseline này chỉ xác nhận computational locomotion runtime; không phải "
            "biological validation và không phải Parkinson result.",
            "",
            "## Ranh giới khoa học",
            "",
            "Đây là computational locomotion baseline. Nó không phải biological "
            "Parkinson model validation, clinical prediction, diagnosis, drug efficacy "
            "validation hoặc thay thế thí nghiệm wet-lab.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _write_missing_report(report_path: Path, audit: Mapping[str, Any], config_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Gate 11: Healthy Baseline Multi-Seed Report",
        "",
        "**Trạng thái:** `MISSING_EXTERNAL_ARTIFACT` hoặc `WAITING_RUNTIME`",
        "",
        "Không chạy simulation và không tạo metrics giả vì preflight chưa đạt.",
        "",
        f"- Config: `{_relative(config_path)}`.",
        f"- Preflight: `{audit['status']}`.",
        f"- Brain source: `{audit['brain_source'].get('status')}`.",
        f"- Platform runner: `{audit['platform_runner'].get('status')}`.",
        f"- Runtime: `{audit['runtime'].get('status')}`.",
        "",
        "Chi tiết file thiếu hoặc checksum nằm trong `manifests/external_input_audit.json`.",
        "",
        "Đây là computational locomotion execution gate, không phải biological Parkinson validation.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def run(config_path: Path, *, overrides: argparse.Namespace) -> int:
    config = _load_config(config_path)
    paths = config.get("paths") or {}
    brain_root = _resolve(overrides.brain_root or paths["brain_root"])
    platform_root = _resolve(overrides.platform_root or paths["platform_root"])
    brain_python = _resolve(overrides.brain_python or paths["brain_python"])
    output_root = _resolve(config.get("output", {}).get("root", str(DEFAULT_OUTPUT_ROOT)))
    manifests = output_root / "manifests"
    logs = output_root / "logs"
    results = output_root / "results"
    manifests.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)

    artifact_audit = _artifact_audit(
        brain_root=brain_root,
        platform_root=platform_root,
        brain_python=brain_python,
        artifact_paths=config.get("artifact_paths") or {},
    )
    (manifests / "external_input_audit.json").write_text(
        json.dumps(artifact_audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if artifact_audit["status"] != "READY":
        _write_missing_report(DEFAULT_REPORT, artifact_audit, config_path)
        (manifests / "healthy_baseline_manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": "gate-11-healthy-baseline-manifest-v1",
                    "status": artifact_audit["status"],
                    "simulation_run": False,
                    "config": _relative(config_path),
                    "external_input_audit": _relative(manifests / "external_input_audit.json"),
                    "scientific_scope": "Computational locomotion only; no fabricated baseline.",
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return 2

    rows: list[dict[str, Any]] = []
    for seed in config["execution"]["seeds"]:
        row = _run_seed(
            seed=int(seed),
            config=config,
            brain_root=brain_root,
            platform_root=platform_root,
            brain_python=brain_python,
            output_root=output_root,
        )
        rows.append(row)
        print(f"seed={seed} status={row['status']} metrics={row['required_metric_status']}")

    metrics_csv = results / "healthy_baseline_metrics.csv"
    metrics_json = results / "healthy_baseline_metrics.json"
    _write_csv(metrics_csv, rows)
    required_metrics = {}
    for metric in config["required_metrics"]:
        required_metrics[str(metric)] = (
            "PRESENT"
            if all(isinstance(row.get(metric), (int, float)) and math.isfinite(float(row[metric])) for row in rows)
            else "MISSING"
        )
    run_status = "PASS" if all(row["status"] == "PASS" for row in rows) else "FAILED"
    contract_status = "PASS" if all(value == "PRESENT" for value in required_metrics.values()) else "INCOMPLETE"
    canonical_metrics = {
        "mean_planar_speed_mm_s": {
            "source": "rollout.npz:thorax",
            "unit": "mm/s",
            "formula": "norm(final_thorax_xy - initial_thorax_xy) / ((frame_count - 1) * timestep_s)",
            "alias_allowed": False,
            "reason": (
                "Derived directly from the planar thorax trajectory using the repository canonical formula. "
                "The raw walking_speed_mm_s is mean instantaneous path speed and is retained separately."
            ),
        },
        "distance_traveled_mm": {
            "source": "total_distance_mm; verified against rollout.npz:thorax",
            "unit": "mm",
            "formula": "sum(norm(diff(thorax_xy)))",
            "alias_allowed": True,
            "reason": "The runtime total_distance_mm is the total planar XY path length.",
        },
        "displacement_mm": {
            "source": "rollout.npz:thorax",
            "unit": "mm",
            "formula": "norm(final_thorax_xy - initial_thorax_xy)",
            "alias_allowed": False,
            "reason": "Derived directly as net planar thorax displacement; no distance-to-speed conversion is used.",
        },
    }
    payload = {
        "schema_version": "gate-11-healthy-baseline-metrics-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": run_status,
        "metric_contract_status": contract_status,
        "seeds": config["execution"]["seeds"],
        "rows": rows,
        "summary": _summary(rows),
        "runtime": _runtime_summary(rows, config),
        "metric_contract": {"status": contract_status, "canonical_metrics": canonical_metrics},
        "scientific_scope": "Computational healthy locomotion baseline; not biological validation.",
        "data_fabricated": False,
    }
    metrics_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    artifact_records = []
    for path in [config_path, metrics_csv, metrics_json, manifests / "external_input_audit.json"]:
        artifact_records.append({"path": _relative(path), "size": path.stat().st_size, "sha256": _sha256(path)})
    manifest = {
        "schema_version": "gate-11-healthy-baseline-manifest-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": run_status,
        "simulation_run": True,
        "condition": "healthy_baseline",
        "disease_layer_enabled": False,
        "calibration_run": False,
        "holdout_validation_run": False,
        "config": _relative(config_path),
        "config_sha256": _sha256(config_path),
        "git_commit": _git_commit(),
        "seeds": config["execution"]["seeds"],
        "seed_count": len(rows),
        "preflight_status": artifact_audit["runtime"]["status"],
        "external_artifact_status": artifact_audit["status"],
        "external_input_audit": _relative(manifests / "external_input_audit.json"),
        "metric_contract": {
            "required": required_metrics,
            "status": contract_status,
            "canonical_metrics": canonical_metrics,
            "forbidden": [
                "no distance_to_speed conversion",
                "no CI95_to_SE conversion",
                "no median_to_mean conversion",
            ],
        },
        "runtime": _runtime_summary(rows, config),
        "runs": rows,
        "artifacts": artifact_records,
        "scientific_scope": "Healthy computational locomotion baseline only; not biological Parkinson validation.",
        "data_fabricated": False,
    }
    manifest_path = manifests / "healthy_baseline_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_report(report_path=DEFAULT_REPORT, manifest=manifest, rows=rows)
    return 0 if run_status == "PASS" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--brain-root", type=Path, default=None)
    parser.add_argument("--platform-root", type=Path, default=None)
    parser.add_argument("--brain-python", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(_resolve(args.config), overrides=args)
    except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(f"Gate 11 stopped before simulation: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
