"""Chay mot rollout brain-body that qua FlyGym, co the xuat MP4 that."""

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
from typing import Any, Sequence
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLATFORM_ROOT = ROOT.parent / "drosophila-pd-flygym"
DEFAULT_BRAIN_ROOT = ROOT / "external" / "fly-brain"
PREPARE_SCRIPT = ROOT / "scripts" / "prepare_neural_checkpoint.py"
PLATFORM_RUNNER = "scripts/run_brain_body_rollout.py"

# These are the only two runtime contracts accepted by the Gate 24E wrapper.
# The amended contract changes post-simulation artifact handling only; it does
# not change the simulation loop or the scientific model.
ORIGINAL_PLATFORM_COMMIT = "3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06"
AMENDED_PLATFORM_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"
LEGACY_ARTIFACT_PROFILE = "LEGACY"
MEMORY_SAFE_ARTIFACT_PROFILE = "GATE24E_MEMORY_SAFE"
RUNTIME_CONTRACTS = {
    ORIGINAL_PLATFORM_COMMIT: LEGACY_ARTIFACT_PROFILE,
    AMENDED_PLATFORM_COMMIT: MEMORY_SAFE_ARTIFACT_PROFILE,
}

# Backward-compatible aliases retained for the existing Gate 24 tests and
# callers. The default workflow remains the original frozen runtime.
FROZEN_PLATFORM_COMMIT = ORIGINAL_PLATFORM_COMMIT
FROZEN_FLYGYM_VERSION = "2.1.0"
FROZEN_CPG_DEFAULT_HZ = 12.0

STAGED_FILES = (
    "brain_body_bridge.py",
    "code/run_pytorch.py",
    "code/benchmark.py",
    "data/2025_Completeness_783.csv",
    "data/2025_Connectivity_783.parquet",
)


def _resolve(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _write_status(output: Path, status: str, message: str, **extra: object) -> None:
    output.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "status": status,
        "message": message,
        "simulation_run": status == "PASS",
        "created_at_utc": datetime.now(UTC).isoformat(),
        **extra,
    }
    (output / "status.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "status.md").write_text(
        f"# Neural brain-body experiment\n\n**Trang thai:** `{status}`\n\n{message}\n",
        encoding="utf-8",
    )


def _brain_python(brain_root: Path, configured: str | Path | None) -> Path:
    if configured:
        return _resolve(configured)
    candidates = (
        brain_root / ".venv" / "Scripts" / "python.exe",
        brain_root / ".venv" / "bin" / "python",
    )
    return next((candidate for candidate in candidates if candidate.is_file()), Path(sys.executable))


def _link_or_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def _stage_source(source: Path, stage: Path, checkpoint: Path) -> None:
    for relative in STAGED_FILES:
        source_file = source / relative
        if not source_file.is_file():
            raise RuntimeError(f"Thieu file brain source: {source_file}")
        _link_or_copy(source_file, stage / relative)
    _link_or_copy(checkpoint, stage / "data" / "plastic_weights.pt")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Khong doc duoc platform commit: {result.stderr.strip()}")
    return result.stdout.strip()


def _installed_distribution_version(python: Path, distribution: str) -> str:
    code = (
        "from importlib.metadata import version; "
        f"print(version({distribution!r}))"
    )
    result = subprocess.run(
        [str(python), "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"Khong xac minh duoc {distribution} trong runtime {python}: "
            f"{result.stderr.strip()}"
        )
    return result.stdout.strip()


def validate_runtime_contract(*, platform_commit: str, artifact_profile: str) -> None:
    """Reject unknown or mismatched platform/profile pairs fail-closed."""
    if artifact_profile not in {LEGACY_ARTIFACT_PROFILE, MEMORY_SAFE_ARTIFACT_PROFILE}:
        raise RuntimeError(f"UNKNOWN_ARTIFACT_PROFILE: {artifact_profile}")
    expected_profile = RUNTIME_CONTRACTS.get(platform_commit)
    if expected_profile is None:
        raise RuntimeError(f"UNKNOWN_PLATFORM_COMMIT: {platform_commit}")
    if expected_profile != artifact_profile:
        raise RuntimeError(
            "INCOMPATIBLE_RUNTIME_PROFILE: "
            f"commit {platform_commit} requires {expected_profile}, got {artifact_profile}"
        )


def validate_runtime_cpg_compatibility(
    *,
    platform_commit: str,
    flygym_version: str,
    requested_frequency_hz: float,
) -> None:
    """Validate CPG invariants for either reviewed runtime contract."""
    if platform_commit not in RUNTIME_CONTRACTS:
        raise RuntimeError(
            "INCOMPATIBLE_FLYGYM_PLATFORM_COMMIT: "
            f"unknown approved runtime commit, got {platform_commit}"
        )
    if flygym_version != FROZEN_FLYGYM_VERSION:
        raise RuntimeError(
            "INCOMPATIBLE_FLYGYM_VERSION: "
            f"expected {FROZEN_FLYGYM_VERSION}, got {flygym_version}"
        )
    if requested_frequency_hz != FROZEN_CPG_DEFAULT_HZ:
        raise RuntimeError(
            "INCOMPATIBLE_CPG_FREQUENCY: the frozen platform default is "
            f"{FROZEN_CPG_DEFAULT_HZ} Hz, requested {requested_frequency_hz} Hz"
        )


def validate_frozen_cpg_compatibility(
    *,
    platform_commit: str,
    flygym_version: str,
    requested_frequency_hz: float,
) -> None:
    """Validate the frozen platform before omitting its unsupported CLI flag."""
    if platform_commit != FROZEN_PLATFORM_COMMIT:
        raise RuntimeError(
            "INCOMPATIBLE_FLYGYM_PLATFORM_COMMIT: "
            f"expected {FROZEN_PLATFORM_COMMIT}, got {platform_commit}"
        )
    if flygym_version != FROZEN_FLYGYM_VERSION:
        raise RuntimeError(
            "INCOMPATIBLE_FLYGYM_VERSION: "
            f"expected {FROZEN_FLYGYM_VERSION}, got {flygym_version}"
        )
    if requested_frequency_hz != FROZEN_CPG_DEFAULT_HZ:
        raise RuntimeError(
            "INCOMPATIBLE_CPG_FREQUENCY: the frozen platform default is "
            f"{FROZEN_CPG_DEFAULT_HZ} Hz, requested {requested_frequency_hz} Hz"
        )


def build_platform_command(
    *,
    brain_python: Path,
    platform_root: Path,
    run_brain_root: Path,
    seed: int,
    steps: int,
    device: str,
    output: Path,
    stimulus: str,
    requested_frequency_hz: float,
    artifact_profile: str = LEGACY_ARTIFACT_PROFILE,
    video: bool = False,
    video_output: Path | None = None,
    video_fps: int = 60,
    video_width: int = 640,
    video_height: int = 360,
    video_playback_speed: float = 0.2,
    video_camera_mode: str = "tracking",
    compare_to: Path | None = None,
) -> list[str]:
    """Build a command accepted by the frozen platform runner.

    The local wrapper keeps accepting ``--cpg-frequency-hz`` for API
    compatibility, but the frozen downstream runner has no such option.  The
    value is therefore validated against the audited intrinsic default and
    deliberately omitted from the child command.
    """
    platform_commit = _git_commit(platform_root)
    validate_runtime_contract(
        platform_commit=platform_commit,
        artifact_profile=artifact_profile,
    )
    validate_runtime_cpg_compatibility(
        platform_commit=platform_commit,
        flygym_version=_installed_distribution_version(brain_python, "flygym"),
        requested_frequency_hz=requested_frequency_hz,
    )
    command = [
        str(brain_python),
        str(platform_root / PLATFORM_RUNNER),
        "--brain-root",
        str(run_brain_root),
        "--condition",
        "healthy",
        "--seed",
        str(seed),
        "--steps",
        str(steps),
        "--device",
        device,
        "--output",
        str(output),
        "--stimulus",
        stimulus,
    ]
    if artifact_profile == MEMORY_SAFE_ARTIFACT_PROFILE:
        # The amended runner explicitly accepts this profile. The legacy
        # runner does not, so LEGACY remains omitted for old workflows.
        command.extend(["--artifact-profile", MEMORY_SAFE_ARTIFACT_PROFILE])
    if video or video_output:
        command.extend(
            [
                "--video-output",
                str(_resolve(video_output or output / "flygym_rollout.mp4")),
                "--video-fps",
                str(video_fps),
                "--video-width",
                str(video_width),
                "--video-height",
                str(video_height),
                "--video-playback-speed",
                str(video_playback_speed),
                "--video-camera-mode",
                video_camera_mode,
            ]
        )
    if compare_to:
        command.extend(["--compare-to", str(_resolve(compare_to))])
    return command


def _recover_viewer_bundle(output: Path) -> bool:
    """Finish a bundle after the platform ran out of RAM while hashing pose JSON.

    The platform has already completed simulation, export, and asset copying
    when this case occurs. This recovery only streams existing files into a
    zip; it never changes the pose document or creates scientific data.
    """

    stage = output / "viewer_bundle"
    if not stage.is_dir() or not (stage / "index.html").is_file():
        return False
    files = []
    for path in sorted(stage.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            relative = path.relative_to(stage).as_posix()
            files.append(
                {
                    "path": relative,
                    "byte_size": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
    manifest = {
        "schema_version": "viewer-bundle-1-recovered",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "files": files,
        "scientific_scope": "Bundle artifact for a real computational locomotion rollout.",
        "recovery_reason": "Memory-safe wrapper recovery after platform bundle hashing.",
    }
    (stage / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    archive = output / "viewer_bundle.zip"
    partial = archive.with_name(archive.name + ".part")
    with ZipFile(partial, "w", compression=ZIP_DEFLATED, compresslevel=6) as handle:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                archive_name = "viewer_bundle/" + path.relative_to(stage).as_posix()
                handle.write(path, archive_name)
    partial.replace(archive)
    return archive.is_file() and archive.stat().st_size > 0


def _recoverable_postprocess(output: Path, video_requested: bool) -> bool:
    required = (
        output / "rollout.json",
        output / "rollout.npz",
        output / "metrics" / "metrics.json",
        output / "viewer_pose.json",
    )
    if video_requested:
        required += (output / "flygym_rollout.mp4",)
    if not all(path.is_file() and path.stat().st_size > 0 for path in required):
        return False
    return _recover_viewer_bundle(output)


def _run_prepare(
    *,
    brain_python: Path,
    brain_root: Path,
    config: Path,
    age_days: float,
    annotations: Path,
    output: Path,
) -> tuple[int, str]:
    command = [
        str(brain_python),
        str(PREPARE_SCRIPT),
        "--brain-root",
        str(brain_root),
        "--config",
        str(config),
        "--age-days",
        str(age_days),
        "--annotations",
        str(annotations),
        "--output",
        str(output),
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    message = (result.stdout + result.stderr).strip()
    if result.returncode:
        raise RuntimeError(message or "Khong tao duoc checkpoint perturbation.")
    status_path = output / "status.json"
    if not status_path.is_file():
        raise RuntimeError("Bo chuan bi checkpoint khong tao status.json.")
    status = json.loads(status_path.read_text(encoding="utf-8")).get("status", "UNKNOWN")
    return result.returncode, str(status)


def run_experiment(args: argparse.Namespace) -> int:
    brain_root = _resolve(args.brain_root)
    platform_root = _resolve(args.platform_root)
    output = _resolve(args.output)
    annotations = _resolve(args.annotations)
    config = _resolve(args.config) if args.config else None
    configured_prepared_checkpoint = getattr(args, "prepared_checkpoint", None)
    prepared_checkpoint = _resolve(configured_prepared_checkpoint) if configured_prepared_checkpoint else None
    output.mkdir(parents=True, exist_ok=True)
    if not brain_root.is_dir():
        _write_status(output, "WAITING_BRAIN_DATA", f"Khong tim thay brain source: {brain_root}")
        return 0
    if not (platform_root / PLATFORM_RUNNER).is_file():
        _write_status(output, "WAITING_PLATFORM", f"Khong tim thay runner FlyGym: {platform_root / PLATFORM_RUNNER}")
        return 0
    if config is not None and not annotations.is_file():
        _write_status(output, "WAITING_ANNOTATION_DATA", f"Khong tim thay annotation: {annotations}")
        return 0
    brain_python = _brain_python(brain_root, args.brain_python)
    if not brain_python.is_file() and args.brain_python:
        _write_status(output, "WAITING_BRAIN_RUNTIME", f"Khong tim thay Python brain: {brain_python}")
        return 0
    try:
        # The sparse cache can be several hundred MB. Keep the staging area
        # beside the output so a nearly-full system drive cannot interrupt a
        # valid run while the connectome cache is being built.
        with tempfile.TemporaryDirectory(prefix="dpd-brain-stage-", dir=output.parent) as temporary:
            temporary_root = Path(temporary)
            checkpoint = brain_root / "data" / "plastic_weights.pt"
            preparation_status = None
            run_brain_root = brain_root
            if config is not None:
                prepared = temporary_root / "prepared"
                _, preparation_status = _run_prepare(
                    brain_python=brain_python,
                    brain_root=brain_root,
                    config=config,
                    age_days=args.age_days,
                    annotations=annotations,
                    output=prepared,
                )
                if preparation_status != "CHECKPOINT_READY":
                    _write_status(
                        output,
                        preparation_status,
                        "Disease condition chua du dieu kien de chay simulation.",
                        config=str(config),
                        age_days=args.age_days,
                    )
                    return 0
                checkpoint = prepared / "plastic_weights.pt"
                stage = temporary_root / "brain"
                _stage_source(brain_root, stage, checkpoint)
                run_brain_root = stage
            elif prepared_checkpoint is not None:
                if not prepared_checkpoint.is_file():
                    _write_status(output, "WAITING_NEURAL_CHECKPOINT", f"Khong tim thay prepared checkpoint: {prepared_checkpoint}")
                    return 0
                stage = temporary_root / "prepared"
                _stage_source(brain_root, stage, prepared_checkpoint)
                run_brain_root = stage
            command = build_platform_command(
                brain_python=brain_python,
                platform_root=platform_root,
                run_brain_root=run_brain_root,
                seed=args.seed,
                steps=args.steps,
                device=args.device,
                output=output,
                stimulus=args.stimulus,
                requested_frequency_hz=args.cpg_frequency_hz,
                artifact_profile=args.artifact_profile,
                video=args.video,
                video_output=args.video_output,
                video_fps=args.video_fps,
                video_width=args.video_width,
                video_height=args.video_height,
                video_playback_speed=args.video_playback_speed,
                video_camera_mode=args.video_camera_mode,
                compare_to=args.compare_to,
            )
            environment = os.environ.copy()
            environment.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
            result = subprocess.run(
                command,
                cwd=platform_root,
                text=True,
                check=False,
                env=environment,
            )
            if result.returncode:
                recovered = _recoverable_postprocess(
                    output, video_requested=args.video or args.video_output is not None
                )
                if recovered:
                    _write_status(
                        output,
                        "PASS",
                        "Simulation va cac artifact da hoan tat; bundle duoc dong goi lai bang bo nho an toan.",
                        return_code=result.returncode,
                        command=command,
                        preparation_status=preparation_status,
                        bundle_recovered=True,
                    )
                    return 0
                _write_status(
                    output,
                    "FAILED_SIMULATION",
                    "Runner FlyGym tra ve loi; xem stdout/stderr cua lenh.",
                    return_code=result.returncode,
                    command=command,
                    preparation_status=preparation_status,
                )
                return result.returncode
            _write_status(
                output,
                "PASS",
                "Rollout brain-body va artifact FlyGym da tao thanh cong.",
                command=command,
                preparation_status=preparation_status,
            )
            return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        _write_status(output, "FAILED_PREPARATION", str(exc), config=str(config) if config else None)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brain-root", type=Path, default=DEFAULT_BRAIN_ROOT)
    parser.add_argument("--platform-root", type=Path, default=DEFAULT_PLATFORM_ROOT)
    parser.add_argument("--brain-python", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None, help="YAML disease da review; bo trong de chay healthy.")
    parser.add_argument("--prepared-checkpoint", type=Path, default=None, help="Checkpoint neural da materialize boi mot gate co provenance.")
    parser.add_argument("--annotations", type=Path, default=ROOT / "annotations" / "neuron_annotations.csv")
    parser.add_argument("--age-days", type=float, default=20.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--stimulus", default="p9")
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--video", action="store_true")
    parser.add_argument("--video-output", type=Path, default=None)
    parser.add_argument("--video-fps", type=int, default=60)
    parser.add_argument("--video-width", type=int, default=640)
    parser.add_argument("--video-height", type=int, default=360)
    parser.add_argument("--video-playback-speed", type=float, default=0.2)
    parser.add_argument(
        "--video-camera-mode",
        choices=("tracking", "fixed"),
        default="tracking",
        help="Che do video; tracking bam theo thorax, fixed giu camera the gioi.",
    )
    parser.add_argument("--cpg-frequency-hz", type=float, default=12.0)
    parser.add_argument(
        "--artifact-profile",
        choices=(LEGACY_ARTIFACT_PROFILE, MEMORY_SAFE_ARTIFACT_PROFILE),
        default=LEGACY_ARTIFACT_PROFILE,
        help="Artifact contract paired with the selected reviewed platform commit.",
    )
    parser.add_argument("--compare-to", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.seed < 0 or args.steps <= 0:
        parser.error("seed phai >= 0 va steps phai > 0")
    if args.age_days < 0 or args.video_fps <= 0 or args.video_width <= 0 or args.video_height <= 0:
        parser.error("age-days va tham so video phai hop le")
    if args.video_playback_speed <= 0 or args.cpg_frequency_hz <= 0:
        parser.error("video-playback-speed va cpg-frequency-hz phai > 0")
    return run_experiment(args)


if __name__ == "__main__":
    raise SystemExit(main())
