"""Launch a platform-owned healthy or bridge-scale computational run.

Neural checkpoint preparation is kept as a separate, explicit waiting path
until the platform exposes a compatible checkpoint-consuming runtime.
"""

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
PLATFORM_HEALTHY_RUNNER = "scripts/run_healthy_baseline.py"
PLATFORM_BRAIN_RUNNER = "scripts/run_brain_driven_experiment.py"

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
        f"# Neural extension run\n\n**Status:** `{status}`\n\n{message}\n",
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


def _platform_python(configured: str | Path | None) -> Path:
    """Return the interpreter that owns the FlyGym runtime.

    The brain and platform environments are allowed to differ.  Reusing the
    brain interpreter for the platform runner made the bridge path fail on
    machines where Brian2 was installed but FlyGym was not.
    """

    return _resolve(configured) if configured else Path(sys.executable)


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
    platform_root = _resolve(args.platform_root)
    output = _resolve(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if not platform_root.is_dir():
        _write_status(output, "WAITING_PLATFORM", f"Platform root was not found: {platform_root}")
        return 0

    if args.scales_json:
        scales_json = _resolve(args.scales_json)
        runner = platform_root / PLATFORM_BRAIN_RUNNER
        if not runner.is_file():
            _write_status(output, "WAITING_PLATFORM_CAPABILITY", f"Canonical brain-driven runner was not found: {runner}")
            return 0
        if not scales_json.is_file():
            _write_status(output, "WAITING_BRAIN_DATA", f"Bridge scales JSON was not found: {scales_json}")
            return 0
        platform_python = _platform_python(args.platform_python)
        if not platform_python.is_file():
            _write_status(output, "WAITING_PLATFORM_RUNTIME", f"Platform Python was not found: {platform_python}")
            return 0
        baseline_config = _resolve(args.baseline_config) if args.baseline_config else platform_root / "configs/experiments/healthy_baseline.yaml"
        command = [
            str(platform_python),
            str(runner),
            "--scales-json", str(scales_json),
            "--baseline-config", str(baseline_config),
            "--output", str(output / "platform_report.json"),
        ]
        if args.model_name:
            command.extend(["--model-name", args.model_name])
        if args.seed is not None:
            command.extend(["--seed", str(args.seed)])
        result = subprocess.run(command, cwd=platform_root, text=True, check=False)
        if result.returncode:
            _write_status(output, "FAILED_PLATFORM_RUN", "Canonical platform brain-driven runner failed.", command=command, return_code=result.returncode)
            return result.returncode
        _write_status(output, "PASS", "Canonical platform brain-driven runner completed.", command=command)
        return 0

    if args.config:
        brain_root = _resolve(args.brain_root)
        annotations = _resolve(args.annotations)
        config = _resolve(args.config)
        if not brain_root.is_dir():
            _write_status(output, "WAITING_BRAIN_DATA", f"Brain source was not found: {brain_root}")
            return 0
        if not annotations.is_file():
            _write_status(output, "WAITING_ANNOTATION_DATA", f"Neuron annotation was not found: {annotations}")
            return 0
        brain_python = _brain_python(brain_root, args.brain_python)
        if not brain_python.is_file():
            _write_status(output, "WAITING_BRAIN_RUNTIME", f"Brain Python was not found: {brain_python}")
            return 0
        try:
            _, preparation_status = _run_prepare(
                brain_python=brain_python,
                brain_root=brain_root,
                config=config,
                age_days=args.age_days,
                annotations=annotations,
                output=output / "prepared_checkpoint",
            )
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            _write_status(output, "FAILED_PREPARATION", str(exc), config=str(config))
            return 1
        _write_status(
            output,
            "WAITING_PLATFORM_NEURAL_RUNTIME",
            "The canonical platform exposes action-level Perturbation and bridge-scale runners, "
            "but no runner that consumes a neural edge checkpoint. The checkpoint was prepared "
            "only; no simulation was run.",
            preparation_status=preparation_status,
            platform_runner=PLATFORM_HEALTHY_RUNNER,
        )
        return 0

    if args.video:
        _write_status(
            output,
            "WAITING_PLATFORM_CAPABILITY",
            "Video is available through the platform video runner; this wrapper requires "
            "--scales-json for a brain-driven video run.",
        )
        return 0

    runner = platform_root / PLATFORM_HEALTHY_RUNNER
    if not runner.is_file():
        _write_status(output, "WAITING_PLATFORM_CAPABILITY", f"Canonical healthy runner was not found: {runner}")
        return 0
    command = [str(sys.executable), str(runner), "--output", str(output / "healthy_baseline.json")]
    result = subprocess.run(command, cwd=platform_root, text=True, check=False)
    status = "PASS" if result.returncode == 0 else "WAITING_RUNTIME"
    _write_status(output, status, "Canonical platform healthy-baseline runner completed." if result.returncode == 0 else "Canonical platform healthy-baseline runner is unavailable in this environment.", command=command, return_code=result.returncode)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brain-root", type=Path, default=DEFAULT_BRAIN_ROOT)
    parser.add_argument("--platform-root", type=Path, default=DEFAULT_PLATFORM_ROOT)
    parser.add_argument("--brain-python", type=Path, default=None)
    parser.add_argument(
        "--platform-python",
        type=Path,
        default=None,
        help="Python interpreter containing FlyGym/MuJoCo for --scales-json runs.",
    )
    parser.add_argument("--config", type=Path, default=None, help="YAML disease da review; bo trong de chay healthy.")
    parser.add_argument("--scales-json", type=Path, default=None, help="Platform bridge_scales.json for the canonical brain-driven runner.")
    parser.add_argument("--baseline-config", type=Path, default=None, help="Platform healthy-baseline YAML.")
    parser.add_argument("--model-name", type=str, default=None)
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
