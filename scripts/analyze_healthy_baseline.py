"""Audit and summarize real multi-seed healthy brain-body rollouts."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import subprocess
from typing import Any, Iterable, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS = ROOT / "results" / "healthy_baseline_reproducible" / "runs"
DEFAULT_OUTPUT = ROOT / "results" / "healthy_baseline_reproducible" / "summary"
DEFAULT_PROTOCOL = ROOT / "configs" / "healthy_baseline_reproducible.yaml"

METRIC_LABELS = {
    "thorax_planar_displacement_mm": "Thorax displacement (Dịch chuyển ngực, mm)",
    "walking_speed_mm_s": "Walking speed (Vận tốc đi bộ, mm/s)",
    "planar_path_length_mm": "Planar path length (Độ dài quỹ đạo, mm)",
    "trajectory_efficiency": "Trajectory efficiency (Hiệu suất quỹ đạo)",
    "heading_variance_rad2": "Heading variance (Phương sai hướng, rad²)",
    "joint_velocity_rms_rad_s": "Joint velocity RMS (RMS vận tốc khớp, rad/s)",
    "body_orientation_variance_rad2": "Orientation variance (Phương sai tư thế, rad²)",
    "foot_contact_frame_fraction": "Ground-contact fraction (Tỷ lệ frame chạm đất)",
}

SUMMARY_METRICS = tuple(METRIC_LABELS)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_entries(manifest: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    files = manifest.get("files", {})
    if isinstance(files, dict):
        for name, record in files.items():
            yield str(name), dict(record)
    elif isinstance(files, list):
        for index, record in enumerate(files):
            yield str(record.get("name", index)), dict(record)
    else:
        raise ValueError("manifest.files must be an object or array")


def _check(
    checks: list[dict[str, Any]], seed: int, name: str, status: str, detail: str
) -> None:
    checks.append({"seed": seed, "check": name, "status": status, "detail": detail})


def _scalar_metrics(path: Path) -> dict[str, Any]:
    document = _read_json(path)
    result = dict(document.get("scalar_metrics", {}))
    for key in (
        "walking_speed_mm_s",
        "heading_variance_rad2",
        "body_orientation_variance_rad2",
    ):
        if key not in result and key in document:
            result[key] = document[key]
    return result


def audit_run(
    run_dir: Path,
    *,
    seed: int,
    expected_steps: int,
    expected_timestep_s: float,
    video_expected: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    required = (
        "status.json",
        "manifest.json",
        "metadata.json",
        "rollout.npz",
        "metrics/metrics.json",
    )
    missing = [relative for relative in required if not (run_dir / relative).is_file()]
    _check(
        checks,
        seed,
        "required_artifacts",
        "FAIL" if missing else "PASS",
        "Missing: " + ", ".join(missing) if missing else "All required artifacts exist.",
    )
    if missing:
        return {"seed": seed, "status": "FAIL", "run_dir": str(run_dir)}, checks

    status = _read_json(run_dir / "status.json")
    _check(
        checks,
        seed,
        "simulation_status",
        "PASS" if status.get("status") == "PASS" and status.get("simulation_run") is True else "FAIL",
        f"status={status.get('status')}; simulation_run={status.get('simulation_run')}",
    )

    command = [str(item) for item in status.get("command", [])]
    command_text = " ".join(command)
    disease_off = "--config" not in command and "--condition healthy" in command_text
    _check(
        checks,
        seed,
        "healthy_without_disease_layer",
        "PASS" if disease_off else "FAIL",
        "No perturbation config; condition is healthy." if disease_off else command_text,
    )
    seed_matches = "--seed" in command and command[command.index("--seed") + 1] == str(seed)
    _check(checks, seed, "seed_matches", "PASS" if seed_matches else "FAIL", f"expected={seed}")
    expected_command_values = {
        "--steps": str(expected_steps),
        "--stimulus": "p9",
        "--cpg-frequency-hz": "12.0",
        "--device": "cuda",
    }
    mismatches = []
    for option, expected in expected_command_values.items():
        actual = command[command.index(option) + 1] if option in command else None
        if actual != expected:
            mismatches.append(f"{option}: expected={expected}, actual={actual}")
    _check(
        checks,
        seed,
        "execution_protocol",
        "FAIL" if mismatches else "PASS",
        "; ".join(mismatches) if mismatches else "steps, stimulus, CPG, and device match the locked protocol.",
    )

    manifest = _read_json(run_dir / "manifest.json")
    manifest_errors: list[str] = []
    verified_count = 0
    for name, record in _manifest_entries(manifest):
        relative = record.get("path")
        if not relative:
            manifest_errors.append(f"{name}: missing path")
            continue
        artifact = run_dir / str(relative)
        if not artifact.is_file():
            manifest_errors.append(f"{relative}: missing")
            continue
        expected_size = record.get("byte_size", record.get("size_bytes"))
        if expected_size is not None and artifact.stat().st_size != int(expected_size):
            manifest_errors.append(f"{relative}: size mismatch")
            continue
        expected_hash = record.get("sha256")
        if expected_hash and _sha256(artifact) != expected_hash:
            manifest_errors.append(f"{relative}: SHA256 mismatch")
            continue
        verified_count += 1
    _check(
        checks,
        seed,
        "manifest_integrity",
        "FAIL" if manifest_errors else "PASS",
        "; ".join(manifest_errors) if manifest_errors else f"Verified {verified_count} artifacts.",
    )

    with np.load(run_dir / "rollout.npz", allow_pickle=False) as rollout:
        arrays = {name: rollout[name] for name in rollout.files}

    expected_frames = expected_steps + 1
    timestamp = np.asarray(arrays["timestamp_s"], dtype=float)
    timestep = np.diff(timestamp)
    frame_ok = len(timestamp) == expected_frames
    _check(
        checks,
        seed,
        "frame_count",
        "PASS" if frame_ok else "FAIL",
        f"expected={expected_frames}; actual={len(timestamp)}",
    )
    monotonic = bool(timestep.size and np.all(timestep > 0))
    consistent = bool(
        timestep.size
        and np.allclose(timestep, expected_timestep_s, rtol=0.0, atol=1e-10)
    )
    _check(
        checks,
        seed,
        "timestamp_monotonic_and_consistent",
        "PASS" if monotonic and consistent else "FAIL",
        f"strict={monotonic}; timestep_min={timestep.min():.12g}; timestep_max={timestep.max():.12g}",
    )

    nonfinite = [name for name, array in arrays.items() if np.issubdtype(array.dtype, np.number) and not np.all(np.isfinite(array))]
    _check(
        checks,
        seed,
        "numeric_arrays_finite",
        "FAIL" if nonfinite else "PASS",
        "Non-finite arrays: " + ", ".join(nonfinite) if nonfinite else f"Checked {len(arrays)} exported arrays.",
    )

    thorax = np.asarray(arrays["thorax"], dtype=float)
    com = np.asarray(arrays["com"], dtype=float)
    planar_steps = np.linalg.norm(np.diff(thorax[:, :2], axis=0), axis=1)
    displacement = float(np.linalg.norm(thorax[-1, :2] - thorax[0, :2]))
    path_length = float(planar_steps.sum())
    efficiency = displacement / path_length if path_length > 0 else math.nan
    _check(
        checks,
        seed,
        "positive_locomotion",
        "PASS" if displacement > 0 and path_length > 0 else "FAIL",
        f"displacement_mm={displacement:.9g}; planar_path_length_mm={path_length:.9g}",
    )

    contact = np.asarray(arrays.get("contact_found", np.empty((0, 0))), dtype=bool)
    contact_fraction = float(np.mean(np.any(contact, axis=1))) if contact.size else math.nan
    grounded = bool(np.isfinite(contact_fraction) and contact_fraction >= 0.5)
    _check(
        checks,
        seed,
        "ground_contact",
        "PASS" if grounded else "FAIL",
        f"any-foot contact frame fraction={contact_fraction:.6f}",
    )

    joint_position = np.asarray(arrays["joint_positions"], dtype=float)
    joint_velocity = np.asarray(arrays["joint_velocity"], dtype=float)
    joint_range = float(np.ptp(joint_position, axis=0).max())
    joint_velocity_rms = float(np.sqrt(np.mean(np.square(joint_velocity))))
    joint_ok = joint_range > 0 and joint_velocity_rms > 0
    _check(
        checks,
        seed,
        "joint_trajectory_changes",
        "PASS" if joint_ok else "FAIL",
        f"max_joint_range_rad={joint_range:.9g}; velocity_rms_rad_s={joint_velocity_rms:.9g}",
    )

    orientation = np.asarray(arrays["orientation"], dtype=float)
    quaternion_norm = np.linalg.norm(orientation, axis=1)
    quaternion_ok = bool(np.allclose(quaternion_norm, 1.0, rtol=0.0, atol=1e-3))
    _check(
        checks,
        seed,
        "quaternion_valid",
        "PASS" if quaternion_ok else "FAIL",
        f"norm_min={quaternion_norm.min():.9g}; norm_max={quaternion_norm.max():.9g}",
    )

    observation_arrays = (
        "thorax",
        "com",
        "orientation",
        "joint_positions",
        "joint_velocity",
        "contact_found",
    )
    observation_ok = all(name in arrays and len(arrays[name]) == expected_frames for name in observation_arrays)
    _check(
        checks,
        seed,
        "exported_observation_state",
        "PASS" if observation_ok else "FAIL",
        ", ".join(observation_arrays),
    )

    actuator = np.asarray(arrays.get("actuator_position", np.empty((0, 0))), dtype=float)
    actuator_ok = bool(actuator.size and np.all(np.isfinite(actuator)) and np.ptp(actuator, axis=0).max() > 0)
    _check(
        checks,
        seed,
        "exported_actuator_state",
        "PASS" if actuator_ok else "FAIL",
        "Finite actuator state varies over time." if actuator_ok else "Actuator state missing, invalid, or constant.",
    )
    _check(
        checks,
        seed,
        "raw_action_command",
        "WARN",
        "The platform runner does not export the raw action command array; actuator state was checked instead.",
    )

    video = run_dir / "flygym_rollout.mp4"
    video_ok = video.is_file() and video.stat().st_size > 0
    _check(
        checks,
        seed,
        "representative_video",
        "PASS" if video_ok else ("FAIL" if video_expected else "NOT_APPLICABLE"),
        f"expected={video_expected}; exists={video_ok}",
    )

    scalars = _scalar_metrics(run_dir / "metrics" / "metrics.json")
    speed = float(scalars.get("walking_speed_mm_s", math.nan))
    _check(
        checks,
        seed,
        "positive_walking_speed",
        "PASS" if np.isfinite(speed) and speed > 0 else "FAIL",
        f"walking_speed_mm_s={speed:.9g}",
    )
    failures = [row for row in checks if row["status"] == "FAIL"]
    return {
        "seed": seed,
        "status": "FAIL" if failures else "PASS_WITH_LIMITATIONS",
        "run_dir": str(run_dir),
        "frame_count": len(timestamp),
        "duration_s": float(timestamp[-1] - timestamp[0]),
        "timestep_s": float(np.median(timestep)),
        "thorax_planar_displacement_mm": displacement,
        "com_planar_displacement_mm": float(np.linalg.norm(com[-1, :2] - com[0, :2])),
        "walking_speed_mm_s": speed,
        "planar_path_length_mm": path_length,
        "trajectory_efficiency": efficiency,
        "heading_variance_rad2": float(scalars.get("heading_variance_rad2", math.nan)),
        "joint_velocity_rms_rad_s": joint_velocity_rms,
        "body_orientation_variance_rad2": float(scalars.get("body_orientation_variance_rad2", math.nan)),
        "foot_contact_frame_fraction": contact_fraction,
        "mean_leg_contact_fraction": float(contact.mean()) if contact.size else math.nan,
        "thorax_height_min_mm": float(thorax[:, 2].min()),
        "thorax_height_max_mm": float(thorax[:, 2].max()),
        "quaternion_norm_min": float(quaternion_norm.min()),
        "quaternion_norm_max": float(quaternion_norm.max()),
        "max_joint_position_range_rad": joint_range,
        "max_actuator_position_range": float(np.ptp(actuator, axis=0).max()),
        "rollout_npz_sha256": _sha256(run_dir / "rollout.npz"),
        "video_path": str(video) if video_ok else "",
    }, checks


def bootstrap_ci(values: Sequence[float], *, samples: int, seed: int = 0) -> tuple[float, float]:
    data = np.asarray(values, dtype=float)
    if not data.size or not np.all(np.isfinite(data)):
        return math.nan, math.nan
    generator = np.random.default_rng(seed)
    indices = generator.integers(0, len(data), size=(samples, len(data)))
    means = data[indices].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)


def summarize(rows: Sequence[dict[str, Any]], *, bootstrap_samples: int) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for metric in SUMMARY_METRICS:
        values = np.asarray([float(row[metric]) for row in rows], dtype=float)
        finite = values[np.isfinite(values)]
        sd = float(np.std(finite, ddof=1)) if len(finite) > 1 else math.nan
        low, high = bootstrap_ci(finite, samples=bootstrap_samples)
        summary.append(
            {
                "metric": metric,
                "n": len(finite),
                "mean": float(np.mean(finite)) if len(finite) else math.nan,
                "sample_sd": sd,
                "se": sd / math.sqrt(len(finite)) if len(finite) > 1 else math.nan,
                "ci_method": "bootstrap_percentile_95",
                "ci95_low": low,
                "ci95_high": high,
            }
        )
    return summary


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(rows)


def _plot(rows: Sequence[dict[str, Any]], output: Path) -> list[str]:
    import matplotlib.pyplot as plt

    seeds = [int(row["seed"]) for row in rows]
    created: list[str] = []
    panels = (
        "walking_speed_mm_s",
        "thorax_planar_displacement_mm",
        "planar_path_length_mm",
        "trajectory_efficiency",
    )
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for axis, metric in zip(axes.flat, panels, strict=True):
        values = [float(row[metric]) for row in rows]
        axis.plot(seeds, values, marker="o", color="#007C91", linewidth=2)
        axis.axhline(np.mean(values), color="#D1495B", linestyle="--", linewidth=1.5, label="Mean (Trung bình)")
        axis.set_title(METRIC_LABELS[metric])
        axis.set_xlabel("Seed (Hạt giống ngẫu nhiên)")
        axis.grid(alpha=0.25)
        axis.legend()
    path = output / "key_metrics_by_seed.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    created.append(path.name)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)
    quality = (
        ("foot_contact_frame_fraction", "Ground contact (Tiếp xúc mặt đất)"),
        ("joint_velocity_rms_rad_s", "Joint velocity RMS (Vận tốc khớp RMS)"),
        ("thorax_height_min_mm", "Minimum thorax height (Độ cao ngực tối thiểu)"),
    )
    colors = ["#2A9D8F", "#F4A261", "#457B9D"]
    for axis, (metric, title), color in zip(axes, quality, colors, strict=True):
        axis.bar(seeds, [float(row[metric]) for row in rows], color=color)
        axis.set_title(title)
        axis.set_xlabel("Seed (Hạt giống ngẫu nhiên)")
        axis.grid(axis="y", alpha=0.25)
    path = output / "quality_control_by_seed.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    created.append(path.name)

    fig, axis = plt.subplots(figsize=(8, 7), constrained_layout=True)
    for row in rows:
        with np.load(Path(row["run_dir"]) / "rollout.npz", allow_pickle=False) as rollout:
            thorax = np.asarray(rollout["thorax"], dtype=float)
        axis.plot(thorax[:, 0], thorax[:, 1], linewidth=1.5, label=f"Seed {row['seed']}")
        axis.scatter(thorax[0, 0], thorax[0, 1], s=24, marker="o")
        axis.scatter(thorax[-1, 0], thorax[-1, 1], s=30, marker="x")
    axis.set_title("Healthy planar trajectories (Quỹ đạo phẳng Healthy)")
    axis.set_xlabel("X position (Vị trí X, mm)")
    axis.set_ylabel("Y position (Vị trí Y, mm)")
    axis.set_aspect("equal", adjustable="datalim")
    axis.grid(alpha=0.25)
    axis.legend()
    path = output / "trajectories_by_seed.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    created.append(path.name)
    return created


def _git_state(path: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(path), *args], capture_output=True, text=True, check=False
        )
        return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"

    return {
        "path": str(path),
        "commit": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "dirty": bool(run("status", "--porcelain")),
    }


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "NOT_INSTALLED"


def _torch_runtime() -> dict[str, Any]:
    try:
        import torch

        return {
            "cuda_available": bool(torch.cuda.is_available()),
            "cuda_runtime": str(torch.version.cuda),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "gpu_memory_bytes": (
                int(torch.cuda.get_device_properties(0).total_memory)
                if torch.cuda.is_available()
                else None
            ),
        }
    except (ImportError, RuntimeError) as exc:
        return {"cuda_available": False, "error": str(exc)}


def _runtime_preflight(platform_root: Path) -> dict[str, Any]:
    script = platform_root / "scripts" / "check_runtime.py"
    if not script.is_file():
        return {"status": "UNAVAILABLE", "message": f"Missing: {script}"}
    result = subprocess.run(
        [__import__("sys").executable, str(script), "--root", str(platform_root), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "status": "ERROR",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    document["returncode"] = result.returncode
    return document


def _write_output_manifest(output: Path) -> None:
    files = []
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != "manifest.json":
            files.append(
                {
                    "path": path.name,
                    "byte_size": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
    manifest = {
        "schema_version": "healthy-baseline-summary-manifest-1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "files": files,
        "scientific_scope": "Computational locomotion baseline; not biological Parkinson validation.",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _artifact_record(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return {
        "path": str(path),
        "byte_size": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _run_artifact_lock(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    relative_paths = {
        "platform_manifest": Path("manifest.json"),
        "status": Path("status.json"),
        "rollout_npz": Path("rollout.npz"),
        "metrics": Path("metrics") / "metrics.json",
        "biomarkers": Path("biomarkers") / "biomarkers.json",
        "viewer_pose": Path("viewer_pose.json"),
        "viewer_bundle": Path("viewer_bundle.zip"),
        "video": Path("flygym_rollout.mp4"),
    }
    result: dict[str, Any] = {}
    for row in rows:
        run_dir = Path(row["run_dir"])
        result[str(row["seed"])] = {
            name: record
            for name, relative in relative_paths.items()
            if (record := _artifact_record(run_dir / relative)) is not None
        }
    return result


def _fmt(value: Any) -> str:
    if isinstance(value, (int, np.integer)):
        return str(value)
    if isinstance(value, (float, np.floating)):
        return "NA" if not np.isfinite(value) else f"{float(value):.6g}"
    return str(value)


def _report(
    *,
    rows: Sequence[dict[str, Any]],
    stats: Sequence[dict[str, Any]],
    checks: Sequence[dict[str, Any]],
    output: Path,
    status: str,
    plots: Sequence[str],
) -> None:
    failures = [row for row in checks if row["status"] == "FAIL"]
    warnings = [row for row in checks if row["status"] == "WARN"]
    lines = [
        "# Healthy baseline đa seed",
        "",
        f"**Trạng thái:** `{status}`",
        "",
        "Đây là baseline vận động tính toán của FlyGym kết hợp neural source đã khóa. "
        "Kết quả không phải xác nhận Parkinson sinh học, chẩn đoán, dự đoán lâm sàng hoặc đánh giá thuốc.",
        "",
        "## Protocol",
        "",
        "- Condition: `healthy`; Disease Layer tắt; không calibration.",
        "- Seeds: `0, 1, 2, 3, 4`.",
        "- Mỗi rollout: 5.000 bước, 5.001 frame, timestep 0,0001 s, thời gian mô phỏng 0,5 s.",
        "- Stimulus: `p9`; CPG: 12 Hz; neural execution: CUDA.",
        "- Seed 0 có video đại diện. MP4 khoảng 12 giây là phát chậm 0,5 giây mô phỏng.",
        "",
        "## Chất lượng rollout",
        "",
        f"- Số seed đạt: {sum(row['status'].startswith('PASS') for row in rows)}/{len(rows)}.",
        f"- Kiểm tra lỗi: {len(failures)} FAIL; {len(warnings)} WARN.",
        "- Timestamp, NaN/Inf, contact, quaternion, chuyển động khớp, actuator state và checksum được kiểm tra trên từng seed.",
        "- Raw action command chưa được runner export; actuator state hữu hạn và thay đổi đã được kiểm tra thay thế. Đây là hạn chế dữ liệu, không phải PASS cho action command.",
        "",
        "## Metric theo seed",
        "",
        "| Seed | Speed (mm/s) | Displacement (mm) | Path (mm) | Efficiency | Contact fraction |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['seed']} | {_fmt(row['walking_speed_mm_s'])} | "
            f"{_fmt(row['thorax_planar_displacement_mm'])} | {_fmt(row['planar_path_length_mm'])} | "
            f"{_fmt(row['trajectory_efficiency'])} | {_fmt(row['foot_contact_frame_fraction'])} |"
        )
    lines.extend(
        [
            "",
            "## Thống kê mô tả",
            "",
            "CI 95% dùng bootstrap percentile 10.000 lần, seed phân tích 0. Với n=5, CI chỉ mô tả độ biến thiên tính toán hiện tại.",
            "",
            "| Metric | n | Mean | SD | SE | CI95 low | CI95 high |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in stats:
        lines.append(
            f"| `{row['metric']}` | {row['n']} | {_fmt(row['mean'])} | {_fmt(row['sample_sd'])} | "
            f"{_fmt(row['se'])} | {_fmt(row['ci95_low'])} | {_fmt(row['ci95_high'])} |"
        )
    lines.extend(["", "## Visualization", ""])
    lines.extend(f"- `{name}`" for name in plots)
    lines.extend(
        [
            "",
            "## Diễn giải được phép",
            "",
            "Năm rollout Healthy hoàn thành và tạo locomotion khác 0 trong cùng protocol. "
            "Chúng đủ làm chuẩn kỹ thuật ban đầu cho disease sweep sau khi condition và target khoa học được phê duyệt.",
            "",
            "Không được dùng baseline này một mình để kết luận biological Parkinson validation. "
            "Chưa sinh disease comparison trong bước này.",
            "",
        ]
    )
    (output / "healthy_baseline_summary.md").write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--seeds", default="0,1,2,3,4")
    parser.add_argument("--video-seeds", default="0")
    parser.add_argument("--expected-steps", type=int, default=5000)
    parser.add_argument("--expected-timestep-s", type=float, default=0.0001)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--platform-root", type=Path, default=ROOT.parent / "drosophila-pd-flygym")
    return parser


def _parse_seeds(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runs_root = args.runs_root.resolve()
    output = args.output.resolve()
    protocol = args.protocol.resolve()
    output.mkdir(parents=True, exist_ok=True)
    seeds = _parse_seeds(args.seeds)
    video_seeds = set(_parse_seeds(args.video_seeds))

    rows: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    for seed in seeds:
        row, run_checks = audit_run(
            runs_root / f"seed_{seed:03d}",
            seed=seed,
            expected_steps=args.expected_steps,
            expected_timestep_s=args.expected_timestep_s,
            video_expected=seed in video_seeds,
        )
        rows.append(row)
        checks.extend(run_checks)

    hashes = [row.get("rollout_npz_sha256", "") for row in rows]
    duplicates = len([value for value in hashes if value]) != len(set(value for value in hashes if value))
    for seed in seeds:
        _check(
            checks,
            seed,
            "duplicate_rollout",
            "FAIL" if duplicates else "PASS",
            "Duplicate rollout.npz SHA256 detected." if duplicates else "All rollout.npz hashes are unique.",
        )

    stats = summarize(rows, bootstrap_samples=args.bootstrap_samples) if all("walking_speed_mm_s" in row for row in rows) else []
    failures = [row for row in checks if row["status"] == "FAIL"]
    warnings = [row for row in checks if row["status"] == "WARN"]
    status = "HEALTHY_BASELINE_FAILED" if failures else (
        "HEALTHY_BASELINE_PASS_WITH_LIMITATIONS" if warnings else "HEALTHY_BASELINE_PASS"
    )
    _write_csv(output / "per_seed_metrics.csv", rows)
    _write_csv(output / "summary_statistics.csv", stats)
    _write_csv(output / "quality_checks.csv", checks)
    plots = _plot(rows, output) if not failures else []

    source_manifest = ROOT / "external" / "fly-brain" / "source_manifest.json"
    source_lock = _read_json(source_manifest)
    platform_root = args.platform_root.resolve()
    provenance = {
        "schema_version": "healthy-baseline-provenance-1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "protocol": str(protocol),
        "protocol_sha256": _sha256(protocol),
        "repositories": {
            "neural_disease": _git_state(ROOT),
            "flygym_platform": _git_state(platform_root),
        },
        "brain_source_manifest": str(source_manifest),
        "brain_source_manifest_sha256": _sha256(source_manifest),
        "brain_source_lock": {
            "repository": source_lock.get("source_repository"),
            "commit": source_lock.get("source_commit"),
            "license": source_lock.get("license"),
        },
        "runtime": {
            "python": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}.{__import__('sys').version_info.micro}",
            "numpy": np.__version__,
            "flygym": _package_version("flygym"),
            "mujoco": _package_version("mujoco"),
            "torch": _package_version("torch"),
            "accelerator": _torch_runtime(),
            "preflight": _runtime_preflight(platform_root),
        },
        "seeds": seeds,
        "run_rollout_sha256": {str(row.get("seed")): row.get("rollout_npz_sha256") for row in rows},
        "representative_video": next((row.get("video_path") for row in rows if row.get("video_path")), None),
        "run_artifacts": _run_artifact_lock(rows),
        "scientific_scope": "Computational locomotion baseline; not biological Parkinson validation.",
    }
    (output / "provenance_lock.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    result = {
        "schema_version": "healthy-baseline-summary-1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "seed_count": len(rows),
        "passed_seed_count": sum(str(row.get("status", "")).startswith("PASS") for row in rows),
        "failed_check_count": len(failures),
        "warning_count": len(warnings),
        "per_seed": rows,
        "summary_statistics": stats,
        "plots": plots,
        "scientific_scope": "Computational locomotion baseline; not biological Parkinson validation.",
    }
    (output / "baseline_summary.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _report(rows=rows, stats=stats, checks=checks, output=output, status=status, plots=plots)
    _write_output_manifest(output)
    print(f"Status: {status}")
    print(f"Report: {output / 'healthy_baseline_summary.md'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
