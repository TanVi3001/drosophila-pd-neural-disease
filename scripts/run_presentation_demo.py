"""Run exactly two short, presentation-only Gate24E visualizations.

This wrapper is intentionally narrower than the scientific runners.  It never
opens the holdout, changes a checkpoint, computes validation metrics, or runs
the frozen scientific batch.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "eb6aecaf034fadfd16ae39a1b9d1a5e521cae676"
EXPECTED_CANONICAL_MAIN = "07329fff0cc158abf91f40d867c29a01fbd80d7d"
CURRENT_R2_SHA256 = "147bc90ea017b0a88a580e95d07f9d85548f157f45479283f67ac1b54444e36b"
PREVIOUS_R2_SHA256 = "5aa0d5bf05dac950761b8636fdea001072f27c8226139ec1dac9066be6146d05"
GATE24E_RESULT = "NEGATIVE_VALIDATION_RESULT"
GATE24E_CROSS_ASSAY = "DIRECTIONAL_CROSS_ASSAY_DISCORDANCE"
FINAL_EVIDENCE_SHA256 = "2f056bf5b73ecc4b4de27f714bda681134050c5d82eb2f0f3170b67a5286e967"
VIRTUAL_FREEZE_SHA256 = "f44e9ad10b9fc4795ae2173d3e8b27fc9ea0d8202925bfc08cdcc72d06b00863"
SCIENTIFIC_PLAN_SHA256 = "4515e1916631b019711154dccb5fb887110d5572e3eb82b7ea5118c643db5aac"
RAW_TREE_SHA256 = "f6e3de6e96cbe3be0f447ea8eeca463087a9381d1c2d2965807d04df1655faff"
RUNTIME_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"
MODEL_COMMIT = "be4b10a80755d9f7bad931f56b8a739bd64e3619"
HEALTHY_CHECKPOINT_SHA256 = "d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691"
PARKIN_P100_CHECKPOINT_SHA256 = "0ecf37ce96b6d4ea09b00204c3f01c6f41b6a2820b5f21170c6856760850e2b1"

RUNTIME_ROOT = Path(r"E:\Drosophila_Parkinson\drosophila-pd-flygym-gate24-memorysafe-clean")
BRAIN_ROOT = Path(r"E:\Drosophila_Parkinson\external\fly-brain-audit")
BRAIN_PYTHON = Path(r"E:\Drosophila_Parkinson\drosophila-pd-flygym\.venv\Scripts\python.exe")
DEMO_ROOT = Path(r"E:\Drosophila_Parkinson\demo_outputs\gate24e_presentation")
PRESENTATION_ROOT = DEMO_ROOT / "presentation"
PARKIN_CANDIDATES = (
    ROOT / "results/gate24_neural_transform/parkin_grid/parameter_1_00/plastic_weights.pt",
    ROOT.parent / "main-public-docs/results/gate24_neural_transform/parkin_grid/parameter_1_00/plastic_weights.pt",
    ROOT.parent / "results/gate24_neural_transform/parkin_grid/parameter_1_00/plastic_weights.pt",
)
STEPS = 12_000
SEED = 0
STIMULUS = "p9"
VIDEO_FPS = 30
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 360
PLAYBACK_SPEED = 0.15
CPG_FREQUENCY_HZ = 12.0
PAUSE_SECONDS = 60
MIN_FREE_BYTES = 5 * 1024**3
SAFE_MAX_STEPS = 12_000


class DemoError(RuntimeError):
    """Raised when the presentation-only safety contract is not satisfied."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str, cwd: Path = ROOT) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _json_from_git(commit: str, relative: str) -> dict[str, Any]:
    code, stdout, stderr = _git("show", f"{commit}:{relative}")
    if code:
        raise DemoError(f"Cannot read {relative} from {commit}: {stderr}")
    value = json.loads(stdout)
    if not isinstance(value, dict):
        raise DemoError(f"Expected JSON object in {relative}")
    return value


def resolve_parkin_checkpoint() -> Path:
    for candidate in PARKIN_CANDIDATES:
        if candidate.is_file() and sha256_file(candidate) == PARKIN_P100_CHECKPOINT_SHA256:
            return candidate.resolve()
    raise DemoError("DEMO_BLOCKED_FROZEN_CHECKPOINT_NOT_AVAILABLE")


def validate_checkpoint(path: Path, expected_sha256: str, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise DemoError(f"{label} checkpoint is missing: {path}")
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise DemoError(f"{label} checkpoint SHA256 mismatch: {actual}")
    return {"path": str(path), "sha256": actual, "verified": True}


def validate_runtime_commit(actual: str, expected: str = RUNTIME_COMMIT) -> None:
    if actual != expected:
        raise DemoError(f"Runtime commit mismatch: {actual}")


def validate_demo_parameters(*, seed: int = SEED, steps: int = STEPS) -> None:
    if seed != SEED:
        raise DemoError("Only seed 0 is allowed for the presentation preset")
    if steps <= 0 or steps > SAFE_MAX_STEPS or steps != STEPS:
        raise DemoError(f"Presentation preset requires exactly {STEPS} steps")


def output_isolation_check(output: Path = DEMO_ROOT) -> dict[str, Any]:
    resolved = output.resolve()
    protected = (
        ROOT / "experiments/gate_24e_blinded_parkin_prediction",
        ROOT / "experiments/gate_25_r2_parkin_reproducibility",
        ROOT / "research/validation",
        ROOT / "docs/validation",
        Path(r"D:\EHouse\Drosophila_Archive\Gate24E_Final_Raw_Evidence"),
    )
    inside_repo = resolved == ROOT.resolve() or ROOT.resolve() in resolved.parents
    inside_protected = any(item.resolve() == resolved or item.resolve() in resolved.parents for item in protected)
    if inside_repo or inside_protected:
        raise DemoError(f"Demo output is inside a protected repository/evidence path: {resolved}")
    return {"path": str(resolved), "isolated": True}


def _runtime_telemetry() -> dict[str, Any]:
    command = [
        "nvidia-smi",
        "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.free",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return {"available": False, "note": "nvidia-smi unavailable; telemetry not collected"}
    if result.returncode or not result.stdout.strip():
        return {"available": False, "note": "nvidia-smi unavailable; telemetry not collected"}
    fields = [item.strip() for item in result.stdout.splitlines()[0].split(",")]
    if len(fields) != 4:
        return {"available": False, "note": "nvidia-smi output could not be parsed"}
    try:
        telemetry = {
            "available": True,
            "temperature_c": float(fields[0]),
            "utilization_percent": float(fields[1]),
            "memory_used_mib": float(fields[2]),
            "memory_free_mib": float(fields[3]),
        }
    except ValueError:
        return {"available": False, "note": "nvidia-smi values could not be parsed"}
    if telemetry["temperature_c"] >= 82:
        raise DemoError(f"GPU temperature is too high: {telemetry['temperature_c']} C")
    return telemetry


def _runtime_checks() -> dict[str, Any]:
    if not RUNTIME_ROOT.is_dir():
        raise DemoError(f"Approved platform runtime is missing: {RUNTIME_ROOT}")
    code, head, stderr = _git("rev-parse", "HEAD", cwd=RUNTIME_ROOT)
    if code:
        raise DemoError(f"Runtime commit could not be read: {stderr}")
    validate_runtime_commit(head)
    _, status, _ = _git("status", "--porcelain", cwd=RUNTIME_ROOT)
    if status:
        raise DemoError("Approved runtime worktree is dirty")
    if not BRAIN_PYTHON.is_file():
        raise DemoError(f"Approved Python runtime is missing: {BRAIN_PYTHON}")
    version = subprocess.run(
        [str(BRAIN_PYTHON), "-c", "from importlib.metadata import version; print(version('flygym'))"],
        capture_output=True,
        text=True,
        check=False,
    )
    flygym_version = version.stdout.strip()
    if version.returncode or flygym_version != "2.1.0":
        raise DemoError(f"FlyGym version mismatch: {flygym_version or version.stderr.strip()}")
    return {"path": str(RUNTIME_ROOT), "commit": head, "clean": True, "flygym": flygym_version}


def _brain_checks() -> dict[str, Any]:
    required = (
        "brain_body_bridge.py",
        "code/run_pytorch.py",
        "code/benchmark.py",
        "data/2025_Completeness_783.csv",
        "data/2025_Connectivity_783.parquet",
        "data/plastic_weights.pt",
    )
    missing = [relative for relative in required if not (BRAIN_ROOT / relative).is_file()]
    if missing:
        raise DemoError(f"Brain source is incomplete: {missing}")
    healthy = validate_checkpoint(BRAIN_ROOT / "data/plastic_weights.pt", HEALTHY_CHECKPOINT_SHA256, "Healthy")
    parkin = validate_checkpoint(resolve_parkin_checkpoint(), PARKIN_P100_CHECKPOINT_SHA256, "Parkin p=1.00")
    return {"root": str(BRAIN_ROOT), "required_files": list(required), "healthy_checkpoint": healthy, "parkin_checkpoint": parkin}


def _main_provenance() -> dict[str, Any]:
    code, source_head, stderr = _git("rev-parse", "HEAD")
    if code:
        raise DemoError(f"Demo branch commit could not be read: {stderr}")
    code, _, _ = _git("merge-base", "--is-ancestor", SOURCE_COMMIT, source_head)
    if code:
        raise DemoError(f"Demo source snapshot {SOURCE_COMMIT} is not an ancestor of {source_head}")
    code, remote_head, stderr = _git("rev-parse", "refs/remotes/origin/main")
    if code:
        raise DemoError(f"origin/main is unavailable: {stderr}")
    code, _, _ = _git("merge-base", "--is-ancestor", SOURCE_COMMIT, remote_head)
    if code:
        raise DemoError("Demo source is not an ancestor of canonical remote main")
    freeze = _json_from_git(remote_head, "experiments/gate_25_r2_parkin_reproducibility/manifests/gate25_r2_reproducibility_freeze.json")
    locked = freeze.get("locked_identifiers", {})
    expected_locked = {
        "final_evidence_freeze_sha256": FINAL_EVIDENCE_SHA256,
        "virtual_prediction_freeze_sha256": VIRTUAL_FREEZE_SHA256,
        "scientific_plan_sha256": SCIENTIFIC_PLAN_SHA256,
        "raw_runs_tree_sha256": RAW_TREE_SHA256,
        "runtime_commit": RUNTIME_COMMIT,
        "model_commit": MODEL_COMMIT,
    }
    for key, expected in expected_locked.items():
        if locked.get(key) != expected:
            raise DemoError(f"Locked Gate24E identifier changed: {key}")
    if freeze.get("gate25_r2_freeze_sha256") != CURRENT_R2_SHA256:
        raise DemoError("Current Gate25-R2 SHA does not match the approved amendment")
    if freeze.get("previous_gate25_r2_freeze_sha256") != PREVIOUS_R2_SHA256:
        raise DemoError("Previous Gate25-R2 SHA is not preserved")
    for key in ("gate24e_evidence_changed", "scientific_result_changed", "raw_archive_changed"):
        if freeze.get(key) is not False:
            raise DemoError(f"Gate25-R2 changed flag is not false: {key}")
    if freeze.get("refresh_reason") != "CROSS_PLATFORM_FROZEN_ARTIFACT_TRANSPORT_FIX":
        raise DemoError("Gate25-R2 refresh reason changed")
    if freeze.get("scientific_result") != GATE24E_RESULT or freeze.get("cross_assay_decision") != GATE24E_CROSS_ASSAY:
        raise DemoError("Locked Gate24E scientific interpretation changed")
    return {
        "canonical_remote_main_commit": remote_head,
        "demo_source_commit": SOURCE_COMMIT,
        "demo_branch_commit_before_execution": source_head,
        "demo_source_is_ancestor_of_canonical_main": True,
        "gate25_r2_freeze_sha256": freeze["gate25_r2_freeze_sha256"],
        "previous_gate25_r2_freeze_sha256": freeze["previous_gate25_r2_freeze_sha256"],
        "gate24e_scientific_result": freeze["scientific_result"],
        "gate24e_cross_assay_decision": freeze["cross_assay_decision"],
    }


def preflight() -> dict[str, Any]:
    blockers: list[str] = []
    checks: dict[str, Any] = {}
    try:
        checks["main_provenance"] = _main_provenance()
        checks["runtime"] = _runtime_checks()
        checks["brain"] = _brain_checks()
        checks["output_isolation"] = output_isolation_check()
        disk_path = DEMO_ROOT
        while not disk_path.exists() and disk_path != disk_path.parent:
            disk_path = disk_path.parent
        disk = shutil.disk_usage(disk_path)
        checks["disk"] = {"free_bytes": disk.free, "required_free_bytes": MIN_FREE_BYTES, "pass": disk.free >= MIN_FREE_BYTES}
        if not checks["disk"]["pass"]:
            blockers.append("OUTPUT_VOLUME_FREE_SPACE_BELOW_5_GIB")
        checks["gpu_telemetry"] = _runtime_telemetry()
    except (DemoError, OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError) as exc:
        blockers.append(str(exc))
    return {
        "status": "DEMO_PREFLIGHT_PASS" if not blockers else "DEMO_PREFLIGHT_BLOCKED",
        "blockers": blockers,
        "checks": checks,
        "scientific_batch_rerun": False,
        "validation_analysis": False,
        "holdout_used": False,
        "retuning": False,
        "parameter_selection_for_science": False,
        "gpu_executed": False,
        "simulation_executed": False,
    }


def build_command(condition: str, output: Path, parkin_checkpoint: Path | None = None) -> list[str]:
    if condition not in {"healthy", "parkin_p100"}:
        raise DemoError(f"Unsupported demo condition: {condition}")
    validate_demo_parameters()
    command = [
        str(sys.executable),
        str(ROOT / "scripts/run_neural_experiment.py"),
        "--brain-root", str(BRAIN_ROOT),
        "--platform-root", str(RUNTIME_ROOT),
        "--brain-python", str(BRAIN_PYTHON),
        "--seed", str(SEED),
        "--steps", str(STEPS),
        "--stimulus", STIMULUS,
        "--device", "cuda",
        "--artifact-profile", "GATE24E_MEMORY_SAFE",
        "--video", "--video-fps", str(VIDEO_FPS),
        "--video-width", str(VIDEO_WIDTH), "--video-height", str(VIDEO_HEIGHT),
        "--video-playback-speed", str(PLAYBACK_SPEED),
        "--video-camera-mode", "tracking",
        "--output", str(output),
    ]
    if condition == "parkin_p100":
        if parkin_checkpoint is None:
            raise DemoError("Parkin p=1.00 checkpoint is required")
        command.extend(["--prepared-checkpoint", str(parkin_checkpoint)])
    if "--compare-to" in command:
        raise DemoError("Presentation demo cannot use --compare-to")
    return command


def _require_pass(output: Path) -> dict[str, Any]:
    status_path = output / "status.json"
    video = output / "flygym_rollout.mp4"
    if not status_path.is_file():
        raise DemoError(f"Missing status.json: {status_path}")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status.get("status") != "PASS":
        raise DemoError(f"Demo rollout did not pass: {status.get('status')}")
    if not video.is_file() or video.stat().st_size <= 0:
        raise DemoError(f"Missing demo video: {video}")
    return {"status": status.get("status"), "video": {"path": str(video), "bytes": video.stat().st_size, "sha256": sha256_file(video)}}


def _write_presentation(manifest: dict[str, Any]) -> None:
    PRESENTATION_ROOT.mkdir(parents=True, exist_ok=True)
    html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gate24E presentation demo</title><style>
body{font-family:system-ui,sans-serif;margin:2rem;background:#101827;color:#eef2ff}h1{margin-bottom:.4rem}
.banner{padding:1rem;background:#8b2635;border:1px solid #ff9aa8;font-weight:700}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin-top:1rem}
article{background:#1d293b;padding:1rem;border-radius:8px}video{width:100%;background:#000}
button{margin:.75rem .5rem 0 0;padding:.55rem .8rem;border:0;border-radius:5px;cursor:pointer}
code{color:#b9e6ff}@media(max-width:800px){.grid{grid-template-columns:1fr}}
</style></head><body>
<h1>Gate24E brain-body visualization</h1>
<p class="banner">DEMO ONLY - NOT SCIENTIFIC VALIDATION EVIDENCE</p>
<div class="grid"><article><h2>Healthy checkpoint - DEMO</h2><video id="healthy" controls muted loop playsinline src="healthy_demo.mp4"></video></article>
<article><h2>Frozen Parkin perturbation p=1.00 - DEMO</h2><video id="parkin" controls muted loop playsinline src="parkin_p100_demo.mp4"></video></article></div>
<p><button onclick="both('play')">Play both</button><button onclick="both('pause')">Pause both</button><button onclick="both('restart')">Restart both</button></p>
<p>Gate24E scientific result: <code>NEGATIVE_VALIDATION_RESULT</code><br>Cross-assay decision: <code>DIRECTIONAL_CROSS_ASSAY_DISCORDANCE</code></p>
<p>The videos demonstrate execution of the frozen brain-body computational pipeline. Visual appearance is not used as validation evidence.</p>
<script>function both(action){for(const id of ['healthy','parkin']){const v=document.getElementById(id);if(action==='play')v.play();if(action==='pause')v.pause();if(action==='restart'){v.currentTime=0;v.play();}}}</script>
</body></html>
"""
    (PRESENTATION_ROOT / "index.html").write_text(html, encoding="utf-8")
    (PRESENTATION_ROOT / "README_DEMO.md").write_text(
        "# Gate24E presentation demo\n\n"
        "This offline package contains two short demo videos only. It is not validation evidence.\n\n"
        f"Scientific result: `{manifest['gate24e_scientific_result']}`\n\n"
        f"Cross-assay decision: `{manifest['gate24e_cross_assay_decision']}`\n",
        encoding="utf-8",
    )


def _write_report(manifest: dict[str, Any]) -> None:
    ROOT.joinpath("docs/demo").mkdir(parents=True, exist_ok=True)
    lines = [
        "# Gate24E presentation demo report",
        "",
        "This report documents two short local visualization rollouts. They are demo artifacts, not scientific evidence.",
        "",
        f"- Canonical remote main: `{manifest['canonical_remote_main_commit']}`.",
        f"- Demo source commit: `{manifest['demo_source_commit']}`.",
        f"- Runtime commit: `{manifest['runtime_commit']}`.",
        f"- Gate25-R2 SHA: `{manifest['gate25_r2_freeze_sha256']}`; previous SHA preserved as `{manifest['previous_gate25_r2_freeze_sha256']}`.",
        f"- Healthy checkpoint SHA: `{manifest['healthy_checkpoint_sha256']}`.",
        f"- Parkin p=1.00 checkpoint SHA: `{manifest['parkin_p100_checkpoint_sha256']}`.",
        f"- Seed/steps/video: `{manifest['seed']}` / `{manifest['steps']}` / `{manifest['video_resolution']}` at `{manifest['video_fps']} FPS`, playback `{manifest['playback_speed']}`.",
        "",
        "## Results",
        "",
        f"- Healthy status: `{manifest['healthy']['status']}`; video SHA256 `{manifest['healthy']['video']['sha256']}`.",
        f"- Parkin status: `{manifest['parkin_p100']['status']}`; video SHA256 `{manifest['parkin_p100']['video']['sha256']}`.",
        f"- Scientific result unchanged: `{manifest['gate24e_scientific_result']}`.",
        f"- Cross-assay decision unchanged: `{manifest['gate24e_cross_assay_decision']}`.",
        "- Scientific evidence: `false`; validation analysis: `false`; holdout used: `false`; retuning: `false`.",
        "",
        "The demo does not support a claim that the Parkin video is slower, that a biological Parkinson phenotype was reproduced, or that p=1.00 is a biological severity percentage.",
    ]
    (ROOT / "docs/demo/gate24e_presentation_demo_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_manifest(
    provenance: dict[str, Any],
    healthy: dict[str, Any],
    parkin: dict[str, Any],
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "presentation-demo-v1",
        "status": "DEMO_SAFE_PACKAGE_READY",
        "scientific_evidence": False,
        "demo_only": True,
        **provenance,
        "runtime_commit": RUNTIME_COMMIT,
        "model_commit": MODEL_COMMIT,
        "healthy_checkpoint_sha256": HEALTHY_CHECKPOINT_SHA256,
        "parkin_p100_checkpoint_sha256": PARKIN_P100_CHECKPOINT_SHA256,
        "seed": SEED,
        "steps": STEPS,
        "video_fps": VIDEO_FPS,
        "video_resolution": f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}",
        "playback_speed": PLAYBACK_SPEED,
        "scientific_batch_rerun": False,
        "validation_analysis": False,
        "holdout_used": False,
        "retuning": False,
        "parameter_selection_for_science": False,
        "healthy": healthy,
        "parkin_p100": parkin,
        "gpu_telemetry": telemetry,
        "gate24e_scientific_result": GATE24E_RESULT,
        "gate24e_cross_assay_decision": GATE24E_CROSS_ASSAY,
        "gate25_r2_freeze_sha256": CURRENT_R2_SHA256,
        "previous_gate25_r2_freeze_sha256": PREVIOUS_R2_SHA256,
    }


def _execute_one(condition: str, output: Path, checkpoint: Path | None) -> dict[str, Any]:
    telemetry = _runtime_telemetry()
    command = build_command(condition, output, checkpoint)
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode:
        raise DemoError(f"{condition} demo runner failed with exit code {result.returncode}; no retry is allowed")
    result = _require_pass(output)
    result["gpu_telemetry"] = telemetry
    return result


def execute() -> dict[str, Any]:
    result = preflight()
    if result["status"] != "DEMO_PREFLIGHT_PASS":
        raise DemoError(json.dumps(result, ensure_ascii=False))
    validate_demo_parameters()
    checkpoint = Path(result["checks"]["brain"]["parkin_checkpoint"]["path"])
    healthy_output = DEMO_ROOT / "healthy"
    parkin_output = DEMO_ROOT / "parkin_p100"
    if healthy_output.exists() or parkin_output.exists():
        raise DemoError("Demo outputs already exist; refusing automatic retry")
    healthy = _execute_one("healthy", healthy_output, None)
    time.sleep(PAUSE_SECONDS)
    parkin = _execute_one("parkin_p100", parkin_output, checkpoint)
    shutil.copy2(healthy_output / "flygym_rollout.mp4", PRESENTATION_ROOT / "healthy_demo.mp4")
    shutil.copy2(parkin_output / "flygym_rollout.mp4", PRESENTATION_ROOT / "parkin_p100_demo.mp4")
    provenance = result["checks"]["main_provenance"]
    manifest = build_manifest(
        provenance,
        healthy,
        parkin,
        {
            "preflight": result["checks"].get("gpu_telemetry", {}),
            "healthy": healthy.get("gpu_telemetry", {}),
            "parkin_p100": parkin.get("gpu_telemetry", {}),
        },
    )
    DEMO_ROOT.mkdir(parents=True, exist_ok=True)
    (DEMO_ROOT / "demo_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    _write_presentation(manifest)
    _write_report(manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.execute:
        try:
            manifest = execute()
        except DemoError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(json.dumps(manifest, indent=2))
        return 0
    result = preflight()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "DEMO_PREFLIGHT_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
