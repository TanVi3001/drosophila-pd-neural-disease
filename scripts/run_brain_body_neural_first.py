"""Run a ready neural disease checkpoint through the real FlyGym action hook."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLATFORM_ROOT = ROOT.parent / "drosophila-pd-flygym"
PLATFORM_RUNNER = "scripts/run_brain_body_rollout.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_neural_experiment import _stage_source


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_status(output: Path, status: str, message: str, *, simulation_run: bool = False, **extra: object) -> None:
    output.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "schema_version": "brain-body-neural-first-status-v1",
        "created_at_utc": _now(),
        "status": status,
        "message": message,
        "simulation_run": simulation_run,
        "calibration_run": False,
        "holdout_validation_run": False,
        "data_fabricated": False,
        **extra,
    }
    (output / "status.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "status.md").write_text(
        f"# Brain-to-body neural-first integration\n\n**Trang thai:** `{status}`\n\n{message}\n",
        encoding="utf-8",
    )


def _blocked_manifest(*, branch_path: Path, perturbation_path: Path, status: str, message: str, output: Path) -> dict[str, Any]:
    return {
        "schema_version": "brain-body-neural-first-v1",
        "created_at_utc": _now(),
        "status": status,
        "message": message,
        "simulation_run": False,
        "calibration_run": False,
        "holdout_validation_run": False,
        "data_fabricated": False,
        "branch_manifest": str(branch_path.resolve()),
        "perturbation_manifest": str(perturbation_path.resolve()),
        "output": str(output.resolve()),
        "action_contract": {
            "status": "NOT_EXECUTED",
            "flow": ["Brain output", "controller.step()", "LocomotionAction", "apply_locomotion_action()", "simulation.step()"],
        },
        "scientific_scope": "No brain-to-body rollout was executed.",
    }


def _load_npz_evidence(output: Path) -> dict[str, Any]:
    rollout = output / "rollout.npz"
    if not rollout.is_file():
        raise RuntimeError("rollout.npz khong ton tai sau simulation.")
    with np.load(rollout, allow_pickle=False) as data:
        required = ("timestamp_s", "thorax", "joint_positions", "actuator_position", "contact_found")
        missing = [key for key in required if key not in data.files]
        if missing:
            raise RuntimeError(f"rollout.npz thieu truong: {missing}")
        timestamps = np.asarray(data["timestamp_s"], dtype=float)
        thorax = np.asarray(data["thorax"], dtype=float)
        joints = np.asarray(data["joint_positions"], dtype=float)
        actuators = np.asarray(data["actuator_position"], dtype=float)
        contact = np.asarray(data["contact_found"], dtype=float)
    if timestamps.ndim != 1 or timestamps.size < 2 or not np.isfinite(timestamps).all():
        raise RuntimeError("timestamp khong hop le.")
    if np.any(np.diff(timestamps) < 0):
        raise RuntimeError("timestamp khong tang dan.")
    for name, value in (("thorax", thorax), ("joint_positions", joints), ("actuator_position", actuators), ("contact_found", contact)):
        if not np.isfinite(value).all():
            raise RuntimeError(f"{name} co NaN/Inf.")
    if thorax.ndim != 2 or thorax.shape[0] != timestamps.size or thorax.shape[1] < 3:
        raise RuntimeError("thorax trajectory sai shape.")
    if joints.ndim != 2 or joints.shape[0] != timestamps.size:
        raise RuntimeError("joint trajectory sai shape.")
    if actuators.ndim != 2 or actuators.shape[0] != timestamps.size or actuators.shape[1] != 42:
        raise RuntimeError("actuator trajectory khong co shape (frames, 42).")
    joint_delta = float(np.max(np.abs(np.diff(joints, axis=0)))) if joints.shape[0] > 1 else 0.0
    actuator_delta = float(np.max(np.abs(np.diff(actuators, axis=0)))) if actuators.shape[0] > 1 else 0.0
    thorax_displacement = float(np.linalg.norm(thorax[-1, :2] - thorax[0, :2]))
    if actuator_delta <= 0.0 and joint_delta <= 0.0:
        raise RuntimeError("joint/action trajectory khong thay doi.")
    return {
        "frame_count": int(timestamps.size),
        "duration_s": float(timestamps[-1] - timestamps[0]),
        "timestamp_monotonic": True,
        "thorax_displacement_xy": thorax_displacement,
        "joint_positions_shape": list(joints.shape),
        "actuator_position_shape": list(actuators.shape),
        "joint_trajectory_max_delta": joint_delta,
        "actuator_trajectory_max_delta": actuator_delta,
        "contact_shape": list(contact.shape),
        "finite_values": True,
    }


def _write_manifest(output: Path, document: Mapping[str, Any]) -> None:
    (output / "brain_body_integration_manifest.json").write_text(
        json.dumps(dict(document), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def run(
    *,
    branch_manifest_path: Path,
    perturbation_manifest_path: Path,
    brain_root: Path,
    platform_root: Path,
    output: Path,
    brain_python: Path | None,
    seed: int,
    steps: int,
    device: str,
    stimulus: str,
    cpg_frequency_hz: float,
    video: bool,
    video_output: Path | None,
    video_fps: int,
    video_width: int,
    video_height: int,
    video_playback_speed: float,
    video_camera_mode: str,
) -> int:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    branch_manifest_path = branch_manifest_path.resolve()
    perturbation_manifest_path = perturbation_manifest_path.resolve()
    brain_root = brain_root.resolve()
    platform_root = platform_root.resolve()
    branch = json.loads(branch_manifest_path.read_text(encoding="utf-8"))
    perturbation = json.loads(perturbation_manifest_path.read_text(encoding="utf-8"))
    if branch.get("status") != "DISEASE_NEURAL_BRANCH_READY":
        status = "WAITING_DISEASE_NEURAL_BRANCH"
        message = "Step 2 chua READY; Step 4 khong duoc chay."
        _write_manifest(output, _blocked_manifest(branch_path=branch_manifest_path, perturbation_path=perturbation_manifest_path, status=status, message=message, output=output))
        _write_status(output, status, message, blockers=branch.get("blockers", []))
        return 0
    if perturbation.get("status") != "DISEASE_NEURAL_PERTURBATION_READY":
        status = "WAITING_NEURAL_PERTURBATION"
        message = "Step 3 chua READY; Step 4 khong duoc chay."
        _write_manifest(output, _blocked_manifest(branch_path=branch_manifest_path, perturbation_path=perturbation_manifest_path, status=status, message=message, output=output))
        _write_status(output, status, message)
        return 0

    child_info = perturbation.get("child_disease_checkpoint") or {}
    child_checkpoint = Path(str(child_info.get("path", ""))).resolve()
    if not child_checkpoint.is_file():
        status = "WAITING_NEURAL_CHECKPOINT"
        message = f"Khong tim thay child checkpoint: {child_checkpoint}"
        _write_manifest(output, _blocked_manifest(branch_path=branch_manifest_path, perturbation_path=perturbation_manifest_path, status=status, message=message, output=output))
        _write_status(output, status, message)
        return 0
    expected_child = child_info.get("sha256")
    actual_child = _sha256(child_checkpoint)
    if expected_child and actual_child != expected_child:
        status = "WAITING_NEURAL_CHECKPOINT_INTEGRITY"
        message = "Child checkpoint hash khong khop perturbation manifest."
        document = _blocked_manifest(branch_path=branch_manifest_path, perturbation_path=perturbation_manifest_path, status=status, message=message, output=output)
        document["expected_child_checkpoint_sha256"] = expected_child
        document["actual_child_checkpoint_sha256"] = actual_child
        _write_manifest(output, document)
        _write_status(output, status, message)
        return 0
    parent_info = perturbation.get("parent_healthy_checkpoint") or {}
    parent_path = brain_root / "data" / "plastic_weights.pt"
    expected_parent = parent_info.get("sha256")
    if not parent_path.is_file() or (expected_parent and _sha256(parent_path) != expected_parent):
        status = "WAITING_HEALTHY_CORE_INTEGRITY"
        message = "Healthy parent checkpoint khong con khop manifest; dung truoc integration."
        _write_manifest(output, _blocked_manifest(branch_path=branch_manifest_path, perturbation_path=perturbation_manifest_path, status=status, message=message, output=output))
        _write_status(output, status, message)
        return 0
    if not (platform_root / PLATFORM_RUNNER).is_file():
        status = "WAITING_PLATFORM_RUNTIME"
        message = f"Khong tim thay FlyGym runner: {platform_root / PLATFORM_RUNNER}"
        _write_manifest(output, _blocked_manifest(branch_path=branch_manifest_path, perturbation_path=perturbation_manifest_path, status=status, message=message, output=output))
        _write_status(output, status, message)
        return 0
    executable = brain_python.resolve() if brain_python else Path(sys.executable)
    if not executable.is_file():
        status = "WAITING_BRAIN_RUNTIME"
        message = f"Khong tim thay Python runtime: {executable}"
        _write_manifest(output, _blocked_manifest(branch_path=branch_manifest_path, perturbation_path=perturbation_manifest_path, status=status, message=message, output=output))
        _write_status(output, status, message)
        return 0

    command = [
        str(executable), str(platform_root / PLATFORM_RUNNER),
        "--brain-root", "__STAGED_BRAIN_ROOT__",
        "--condition", "healthy",
        "--seed", str(seed),
        "--steps", str(steps),
        "--device", device,
        "--output", str(output),
        "--stimulus", stimulus,
        "--cpg-frequency-hz", str(cpg_frequency_hz),
    ]
    wants_video = video or video_output is not None
    if wants_video:
        target_video = (video_output or (output / "flygym_rollout.mp4")).resolve()
        command.extend([
            "--video-output", "__VIDEO_OUTPUT__",
            "--video-fps", str(video_fps),
            "--video-width", str(video_width),
            "--video-height", str(video_height),
            "--video-playback-speed", str(video_playback_speed),
            "--video-camera-mode", video_camera_mode,
        ])
    log_path = output / "run.log"
    result_code = 1
    evidence: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="dpd-neural-first-", dir=output.parent) as temporary:
        stage = Path(temporary) / "brain"
        _stage_source(brain_root, stage, child_checkpoint)
        actual_command = [
            str(stage) if value == "__STAGED_BRAIN_ROOT__" else value
            for value in command
        ]
        if wants_video:
            actual_video = (video_output or (output / "flygym_rollout.mp4")).resolve()
            actual_command = [str(actual_video) if value == "__VIDEO_OUTPUT__" else value for value in actual_command]
        environment = os.environ.copy()
        environment.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
        with log_path.open("w", encoding="utf-8") as log:
            result = subprocess.run(actual_command, cwd=platform_root, stdout=log, stderr=subprocess.STDOUT, check=False, env=environment)
            result_code = result.returncode
        if result_code == 0:
            try:
                evidence = _load_npz_evidence(output)
            except (OSError, ValueError, RuntimeError) as exc:
                result_code = 1
                evidence = {"validation_error": str(exc)}
    parent_unchanged = parent_path.is_file() and _sha256(parent_path) == expected_parent
    if result_code != 0:
        status = "FAILED_BRAIN_BODY_INTEGRATION"
        message = "FlyGym brain-body integration khong dat; xem run.log va validation evidence."
        document = _blocked_manifest(branch_path=branch_manifest_path, perturbation_path=perturbation_manifest_path, status=status, message=message, output=output)
        document.update({"command": command, "log": str(log_path), "rollout_evidence": evidence, "healthy_checkpoint_unchanged": parent_unchanged})
        _write_manifest(output, document)
        _write_status(output, status, message, command=command, rollout_evidence=evidence)
        return result_code or 1

    document = {
        "schema_version": "brain-body-neural-first-v1",
        "created_at_utc": _now(),
        "status": "BRAIN_TO_BODY_INTEGRATION_PASS",
        "message": "Neural checkpoint disease rieng da chay qua FlyGym brain-to-body hook.",
        "simulation_run": True,
        "calibration_run": False,
        "holdout_validation_run": False,
        "data_fabricated": False,
        "branch_manifest": str(branch_manifest_path),
        "perturbation_manifest": str(perturbation_manifest_path),
        "brain_root": str(brain_root),
        "child_checkpoint": {"path": str(child_checkpoint), "sha256": actual_child},
        "healthy_parent_checkpoint": {"path": str(parent_path), "sha256": expected_parent, "unchanged_after_run": parent_unchanged},
        "seed": seed,
        "steps": steps,
        "device": device,
        "command": command,
        "run_log": str(log_path),
        "action_contract": {
            "status": "EXECUTED",
            "flow": ["Brain output", "controller.step()", "LocomotionAction", "apply_locomotion_action()", "simulation.step()"],
            "action_type": "LocomotionAction",
            "joint_angles_shape": [42],
            "adhesion_onoff_shape": [6],
            "action_write": "apply_locomotion_action()",
            "physics_step": "simulation.step()",
            "evidence_basis": "platform runner contract plus non-constant actuator trajectory in rollout.npz",
        },
        "rollout_evidence": evidence,
        "scientific_scope": (
            "Real computational neural-first brain-body locomotion rollout for an exploratory class-level "
            "dopamine condition; not gene-specific mapping, biological Parkinson validation, or clinical evidence."
        ),
    }
    _write_manifest(output, document)
    _write_status(output, document["status"], document["message"], simulation_run=True, rollout_evidence=evidence)
    print(f"Status: {document['status']}")
    print(f"Output: {output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch-manifest", type=Path, required=True)
    parser.add_argument("--perturbation-manifest", type=Path, required=True)
    parser.add_argument("--brain-root", type=Path, required=True)
    parser.add_argument("--platform-root", type=Path, default=DEFAULT_PLATFORM_ROOT)
    parser.add_argument("--brain-python", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    parser.add_argument("--stimulus", default="p9")
    parser.add_argument("--cpg-frequency-hz", type=float, default=12.0)
    parser.add_argument("--video", action="store_true")
    parser.add_argument("--video-output", type=Path, default=None)
    parser.add_argument("--video-fps", type=int, default=60)
    parser.add_argument("--video-width", type=int, default=640)
    parser.add_argument("--video-height", type=int, default=360)
    parser.add_argument("--video-playback-speed", type=float, default=0.2)
    parser.add_argument("--video-camera-mode", choices=("tracking", "fixed"), default="tracking")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.seed < 0 or args.steps <= 0 or args.cpg_frequency_hz <= 0:
        build_parser().error("seed >= 0, steps > 0 va cpg-frequency-hz > 0")
    return run(
        branch_manifest_path=args.branch_manifest,
        perturbation_manifest_path=args.perturbation_manifest,
        brain_root=args.brain_root,
        platform_root=args.platform_root,
        output=args.output,
        brain_python=args.brain_python,
        seed=args.seed,
        steps=args.steps,
        device=args.device,
        stimulus=args.stimulus,
        cpg_frequency_hz=args.cpg_frequency_hz,
        video=args.video,
        video_output=args.video_output,
        video_fps=args.video_fps,
        video_width=args.video_width,
        video_height=args.video_height,
        video_playback_speed=args.video_playback_speed,
        video_camera_mode=args.video_camera_mode,
    )


if __name__ == "__main__":
    raise SystemExit(main())
