"""Run Gate 20 as a real organism-level action proxy experiment.

The external FlyGym runner performs the simulation. This wrapper only locks
the predeclared matrix, captures compact QC/metric artifacts, and removes
large temporary rollout files after their hashes have been recorded.
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
import tempfile
import time
from typing import Any, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "experiments/gate_20_disease_exploratory_proxy/configs/disease_exploratory_proxy_multiseed.yaml"
DEFAULT_OUTPUT = ROOT / "results/disease_exploratory_gate20"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_healthy_baseline_gate19 import (  # noqa: E402
    _artifact_audit,
    _read_gate19_metrics,
    _rollout_quality,
    _runner_supports_tracking,
    _sha256,
)
from scripts.run_healthy_baseline_multiseed import _finite_rollout  # noqa: E402


REQUIRED_QUALITY_KEYS = (
    "timestamp_monotonic",
    "timestep_consistent",
    "locomotion_detected",
    "contact_detected",
    "joint_trajectory_changes",
    "action_trajectory_valid",
    "observation_state_valid",
    "quaternion_valid",
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
        raise ValueError("Gate 20 config must be a YAML mapping.")
    if document.get("schema_version") != "gate-20-disease-exploratory-proxy-multiseed-v1":
        raise ValueError("Unexpected Gate 20 schema version.")
    runtime = document.get("runtime") or {}
    if runtime.get("seeds") != [0, 1, 2, 3, 4]:
        raise ValueError("Gate 20 seed set must be [0, 1, 2, 3, 4].")
    if int(runtime.get("steps", 0)) != 100000 or float(runtime.get("timestep_s", 0.0)) != 0.0001:
        raise ValueError("Gate 20 must match the Gate 19 100000-step, 0.0001-s protocol.")
    conditions = document.get("conditions")
    if not isinstance(conditions, list) or [item.get("condition_id") for item in conditions] != ["alpha_synuclein", "pink1"]:
        raise ValueError("Gate 20 conditions must be alpha_synuclein and pink1.")
    for condition in conditions:
        if condition.get("scope") != "organism_level_proxy" or condition.get("gene_specific_mapping") is not False:
            raise ValueError("Gate 20 permits organism-level proxies only.")
        if condition.get("burden_levels") != [0.0, 0.25, 0.5, 0.75, 1.0]:
            raise ValueError("Gate 20 burden grid must be [0, .25, .5, .75, 1].")
    if document.get("scientific_boundary", {}).get("calibration_run") is not False:
        raise ValueError("Gate 20 cannot run calibration.")
    if document.get("scientific_boundary", {}).get("holdout_validation") is not False:
        raise ValueError("Gate 20 cannot run holdout validation.")
    return document


def _operator_config_is_valid(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, f"operator_config_missing:{path}"
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        return False, "operator_config_not_mapping"
    if document.get("status") != "OPERATOR_IMPLEMENTED":
        return False, f"operator_status={document.get('status', 'MISSING')}"
    operator = document.get("operator")
    if not isinstance(operator, Mapping) or operator.get("type") != "amplitude_attenuation":
        return False, "operator_type_invalid"
    if document.get("scope", {}).get("organism_level_proxy") is not True:
        return False, "operator_scope_not_organism_proxy"
    if document.get("scope", {}).get("gene_specific_mapping") is not False:
        return False, "operator_gene_specific_claim_not_disabled"
    if document.get("forbidden", {}).get("calibration") is not True:
        return False, "operator_calibration_forbidden_flag_missing"
    if document.get("forbidden", {}).get("holdout_validation") is not True:
        return False, "operator_holdout_forbidden_flag_missing"
    return True, ""


def _mapping_equal(left: Any, right: Any) -> bool:
    return isinstance(left, str) and isinstance(right, str) and left == right


def _numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _artifact_inventory(output: Path) -> list[dict[str, Any]]:
    return [
        {"name": str(path.relative_to(output)).replace("\\", "/"), "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in sorted(path for path in output.rglob("*") if path.is_file())
    ]


def _runner_summary(stdout: str) -> dict[str, Any]:
    """Extract the final summary object from the runner's mixed text output."""

    decoder = json.JSONDecoder()
    for index in (position for position, character in enumerate(stdout) if character == "{"):
        try:
            value, _ = decoder.raw_decode(stdout[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "operator_applied" in value:
            return value
    return {}


def _load_checkpoint(output: Path) -> list[dict[str, Any]]:
    """Load only previously verified PASS rows for resumable long batches."""

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, float, int]] = set()
    for path in sorted((output / "logs").glob("*.qc.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict) or value.get("status") != "PASS":
            continue
        try:
            key = (str(value["condition_id"]), float(value["burden_level"]), int(value["seed"]))
        except (KeyError, TypeError, ValueError):
            continue
        if key in seen:
            continue
        seen.add(key)
        rows.append(value)
    return rows


def _build_command(
    *,
    brain_python: Path,
    platform_root: Path,
    brain_root: Path,
    operator_config: Path,
    seed: int,
    burden: float,
    output: Path,
    steps: int,
    device: str,
    stimulus: str,
    cpg_frequency_hz: float,
    video: bool,
) -> list[str]:
    command = [
        str(brain_python),
        str(platform_root / "scripts/run_brain_body_rollout.py"),
        "--brain-root", str(brain_root),
        "--condition", "healthy",
        "--seed", str(seed),
        "--steps", str(steps),
        "--device", device,
        "--output", str(output),
        "--stimulus", stimulus,
        "--cpg-frequency-hz", str(cpg_frequency_hz),
        "--enable-proxy-burden-operator",
        "--proxy-operator-config", str(operator_config),
        "--proxy-operator-source", str(ROOT),
        "--proxy-burden", str(burden),
    ]
    if video:
        command.extend(
            [
                "--video-output", str(output / "flygym_rollout.mp4"),
                "--video-fps", "60",
                "--video-width", "960",
                "--video-height", "540",
                "--video-playback-speed", "1.0",
                "--video-camera-mode", "tracking",
            ]
        )
    return command


def _run_one(
    *,
    condition_id: str,
    burden: float,
    seed: int,
    config: Mapping[str, Any],
    brain_root: Path,
    platform_root: Path,
    brain_python: Path,
    operator_config: Path,
    temporary_root: Path,
    output_root: Path,
    video: bool,
) -> dict[str, Any]:
    runtime = config["runtime"]
    run_output = temporary_root / f"{condition_id}_burden_{burden:.2f}_seed_{seed:03d}"
    run_output.mkdir(parents=True, exist_ok=True)
    command = _build_command(
        brain_python=brain_python,
        platform_root=platform_root,
        brain_root=brain_root,
        operator_config=operator_config,
        seed=seed,
        burden=burden,
        output=run_output,
        steps=int(runtime["steps"]),
        device=str(runtime["device"]),
        stimulus=str(runtime["stimulus"]),
        cpg_frequency_hz=float(runtime["cpg_frequency_hz"]),
        video=video,
    )
    environment = dict(os.environ)
    environment.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    process = subprocess.Popen(
        command,
        cwd=platform_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=environment,
    )
    started_at = time.time()
    exported_at: float | None = None
    termination_requested = False
    while process.poll() is None:
        rollout_ready = (run_output / "rollout.npz").is_file()
        metrics_path = run_output / "metrics/metrics.json"
        metadata_path = run_output / "metadata.json"
        operator_audit_path = run_output / "proxy_operator_audit.json"
        artifacts_ready = all(
            path.is_file()
            for path in (run_output / "rollout.npz", metrics_path, metadata_path, operator_audit_path)
        )
        metrics_is_new = metrics_path.is_file() and metrics_path.stat().st_mtime >= started_at
        if artifacts_ready and metrics_is_new:
            if exported_at is None:
                exported_at = time.time()
            elif time.time() - exported_at >= 5.0:
                process.terminate()
                termination_requested = True
                break
        time.sleep(1.0)
    try:
        stdout, _ = process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, _ = process.communicate()
    return_code = process.returncode

    metrics_path = run_output / "metrics/metrics.json"
    metadata_path = run_output / "metadata.json"
    rollout_path = run_output / "rollout.npz"
    operator_audit_path = run_output / "proxy_operator_audit.json"
    required_files = [rollout_path, metrics_path, metadata_path, operator_audit_path]
    missing_files = [str(path.relative_to(run_output)).replace("\\", "/") for path in required_files if not path.is_file()]
    metrics: dict[str, float] = {}
    metadata: dict[str, Any] = {}
    reasons: list[str] = []
    if metrics_path.is_file():
        try:
            metrics = _read_gate19_metrics(metrics_path)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            reasons.append(f"metrics_invalid:{exc}")
    if metadata_path.is_file():
        try:
            loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                nested = loaded.get("simulation")
                metadata = nested if isinstance(nested, dict) else loaded
            else:
                reasons.append("metadata_not_mapping")
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            reasons.append(f"metadata_invalid:{exc}")
    if operator_audit_path.is_file():
        try:
            audit = json.loads(operator_audit_path.read_text(encoding="utf-8"))
            if isinstance(audit, dict):
                metadata.update(audit)
            else:
                reasons.append("operator_audit_not_mapping")
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            reasons.append(f"operator_audit_invalid:{exc}")
    # The external recorder snapshots metadata before the final operator hash
    # fields are updated. The runner's final JSON summary is the authoritative
    # post-run record for those fields; merge it without discarding file data.
    metadata.update(_runner_summary(stdout or ""))
    finite, invalid_arrays = _finite_rollout(rollout_path)
    quality = _rollout_quality(
        rollout_path,
        expected_frames=int(runtime["steps"]) + 1,
        expected_timestep_s=float(runtime["timestep_s"]),
        metrics=metrics,
    )
    for name, value in quality.items():
        if _numeric(value):
            metrics.setdefault(name, float(value))
    all_finite = finite and not invalid_arrays and all(_numeric(value) for value in metrics.values())
    required_metrics = [str(item) for item in config["metrics"]["required"]]
    for metric in required_metrics:
        if not _numeric(metrics.get(metric)):
            reasons.append(f"missing_metric:{metric}")
    if not all_finite:
        reasons.append("numeric_qc_failed")
    if return_code not in (0, None) and not termination_requested:
        reasons.append(f"runner_exit_code={return_code}")
    if invalid_arrays:
        reasons.append("invalid_arrays=" + ";".join(invalid_arrays))
    for key in REQUIRED_QUALITY_KEYS:
        if quality.get(key) != "PASS":
            reasons.append(f"quality_{key}={quality.get(key, 'MISSING')}")

    operator_enabled = metadata.get("proxy_burden_operator_enabled") is True
    operator_applied = metadata.get("operator_applied") is True
    before_hash = metadata.get("joint_angles_first_before_sha256")
    after_hash = metadata.get("joint_angles_first_after_sha256")
    adhesion_before_hash = metadata.get("adhesion_onoff_first_before_sha256")
    adhesion_after_hash = metadata.get("adhesion_onoff_first_after_sha256")
    action_changed = bool(before_hash and after_hash and before_hash != after_hash)
    adhesion_unchanged = _mapping_equal(adhesion_before_hash, adhesion_after_hash)
    if not operator_enabled or not operator_applied:
        reasons.append("operator_metadata_missing_or_not_applied")
    if burden == 0.0 and (not before_hash or not after_hash or before_hash != after_hash):
        reasons.append("zero_burden_identity_failed")
    if burden > 0.0 and not action_changed:
        reasons.append("positive_burden_action_unchanged")
    if not adhesion_unchanged:
        reasons.append("adhesion_onoff_changed_or_unrecorded")

    row: dict[str, Any] = {
        "condition_id": condition_id,
        "proxy_scope": "organism_level_proxy",
        "gene_specific_mapping": False,
        "burden_level": burden,
        "seed": seed,
        "status": "PASS" if not missing_files and not reasons else "FAILED_QC",
        "runner_return_code": return_code,
        "runner_terminated_after_export": termination_requested,
        "missing_files": ";".join(missing_files),
        "invalid_arrays": ";".join(invalid_arrays),
        "no_nan_inf": "PASS" if all_finite else "FAIL",
        "operator_enabled": operator_enabled,
        "operator_applied": operator_applied,
        "action_changed": action_changed,
        "adhesion_onoff_unchanged": adhesion_unchanged,
        "quality_status": "PASS" if not reasons else "FAIL",
        "video_status": "PASS" if video and (run_output / "flygym_rollout.mp4").is_file() else ("NOT_REQUESTED" if not video else "MISSING"),
        "reasons": ";".join(reasons),
        "artifact_inventory": _artifact_inventory(run_output) if not missing_files else [],
    }
    row.update(metrics)
    if video and (run_output / "flygym_rollout.mp4").is_file():
        destination = output_root / "videos" / f"{condition_id}_burden_{burden:.2f}_seed_{seed:03d}_tracking.mp4"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(run_output / "flygym_rollout.mp4", destination)
        row["video_path"] = str(destination)
    else:
        row["video_path"] = ""
    _write_text(output_root / "logs" / f"{condition_id}_burden_{burden:.2f}_seed_{seed:03d}.log", stdout or "")
    _write_text(
        output_root / "logs" / f"{condition_id}_burden_{burden:.2f}_seed_{seed:03d}.qc.json",
        json.dumps(row, indent=2, ensure_ascii=False, default=str) + "\n",
    )
    shutil.rmtree(run_output, ignore_errors=True)
    return row


def _metric_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, float | int]]:
    names = sorted(
        {
            key
            for row in rows
            for key, value in row.items()
            if _numeric(value) and key not in {"seed", "burden_level", "runner_return_code"}
        }
    )
    summary: dict[str, dict[str, float | int]] = {}
    for name in names:
        values = [float(row[name]) for row in rows if _numeric(row.get(name))]
        if not values:
            continue
        mean = sum(values) / len(values)
        sample_sd = math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1)) if len(values) > 1 else 0.0
        summary[name] = {"n": len(values), "mean": mean, "sample_sd": sample_sd}
    return summary


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key, value in row.items() if not isinstance(value, (list, dict))})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: value for key, value in row.items() if not isinstance(value, (list, dict))})


def _write_report(path: Path, payload: Mapping[str, Any]) -> None:
    lines = [
        "# Gate 20 - Disease Exploratory Proxy Multi-Seed",
        "",
        f"Trang thai: `{payload['status']}`",
        "",
        "Day la rollout computational organism-level proxy qua action hook FlyGym that.",
        "Khong phai mapping gene-specific va khong phai biological Parkinson validation.",
        "",
        "## Protocol",
        "",
        f"- Conditions proxy: `{payload['conditions']}`.",
        f"- Burden grid da khai bao truoc: `{payload['burden_levels']}`.",
        f"- Seeds: `{payload['seeds']}`; tong so rollout: `{payload['planned_rollouts']}`.",
        f"- Steps/seed: `{payload['steps']}`; duration vat ly: `{payload['duration_s']}` s; timestep: `{payload['timestep_s']}` s.",
        f"- Device: `{payload['device']}`; stimulus: `{payload['stimulus']}`; CPG: `{payload['cpg_frequency_hz']}` Hz.",
        "- Physics, timestep, duration va seed policy duoc giu nhu Gate 19.",
        "- Khong calibration, khong holdout, khong toi uu burden va khong gene-specific claim.",
        f"- Da hoan tat: `{payload.get('completed_rollouts', 0)}`; PASS: `{payload.get('pass_count', 0)}`; FAILED_QC: `{payload.get('failed_count', 0)}`; PENDING: `{payload.get('pending_count', 0)}`.",
        "",
        "## Ket qua",
        "",
        "| Condition | Burden | Seed pass | Recorded | Speed mean (mm/s) | Displacement mean (mm) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for condition in payload["conditions"]:
        for burden in payload["burden_levels"]:
            matching = [row for row in payload["rows"] if row["condition_id"] == condition and math.isclose(float(row["burden_level"]), float(burden))]
            passing = [row for row in matching if row["status"] == "PASS"]
            speed_values = [float(row["mean_planar_speed_mm_s"]) for row in passing if _numeric(row.get("mean_planar_speed_mm_s"))]
            displacement_values = [float(row["displacement_mm"]) for row in passing if _numeric(row.get("displacement_mm"))]
            speed = sum(speed_values) / len(speed_values) if speed_values else "NOT_REPORTED"
            displacement = sum(displacement_values) / len(displacement_values) if displacement_values else "NOT_REPORTED"
            lines.append(f"| `{condition}` | {burden} | {len(passing)} | {len(matching)} | {speed} | {displacement} |")
    lines.extend(
        [
            "",
            "## Artifact policy",
            "",
            "- Raw rollout lon duoc xu ly tam thoi ngoai Git; sau khi QC va hash, file lon duoc xoa de khong nhan ban du lieu.",
            "- Metrics compact, logs, manifest, report va video dai dien duoc giu lai.",
            "- `data_fabricated=false`; khong co calibration hay holdout trong Gate 20.",
            "",
            "## Scientific boundary",
            "",
            "Ket qua chi cho thay pipeline co the ap dung mot operator computational vao action joint_angles cua FlyGym.",
            "Khong duoc dien giai la tac dong cua gene, co che Parkinson, chan doan, clinical prediction hay drug response.",
            "",
        ]
    )
    _write_text(path, "\n".join(lines))


def _finalize_gate20(
    *,
    config_path: Path,
    config: Mapping[str, Any],
    output: Path,
    healthy_summary_path: Path,
    preflight: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> int:
    runtime = config["runtime"]
    planned = len(config["conditions"]) * len(runtime["seeds"]) * 5
    pass_count = sum(row.get("status") == "PASS" for row in rows)
    status = (
        "DISEASE_EXPLORATORY_PROXY_PASS"
        if pass_count == planned
        else ("DISEASE_EXPLORATORY_PROXY_PARTIAL" if pass_count else "DISEASE_EXPLORATORY_PROXY_FAILED")
    )
    per_run_path = output / "per_run_metrics.csv"
    _write_csv(per_run_path, rows)
    payload: dict[str, Any] = {
        "schema_version": "gate-20-disease-exploratory-proxy-summary-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "simulation_run": bool(rows),
        "conditions": [str(item["condition_id"]) for item in config["conditions"]],
        "burden_levels": [float(level) for level in config["conditions"][0]["burden_levels"]],
        "seeds": [int(seed) for seed in runtime["seeds"]],
        "planned_rollouts": planned,
        "completed_rollouts": len(rows),
        "pass_count": pass_count,
        "failed_count": sum(row.get("status") != "PASS" for row in rows),
        "pending_count": planned - len(rows),
        "steps": int(runtime["steps"]),
        "timestep_s": float(runtime["timestep_s"]),
        "duration_s": float(runtime["duration_s"]),
        "device": str(runtime["device"]),
        "stimulus": str(runtime["stimulus"]),
        "cpg_frequency_hz": float(runtime["cpg_frequency_hz"]),
        "rows": list(rows),
        "summary": _metric_summary([row for row in rows if row.get("status") == "PASS"]),
        "preflight": {**preflight, "simulation_run": bool(rows)},
        "operator_config_sha256": _sha256(_resolve(config["paths"]["operator_config"])),
        "calibration_run": False,
        "holdout_validation": False,
        "gene_specific_mapping": False,
        "data_fabricated": False,
        "scientific_scope": "Organism-level computational exploratory proxy; not biological Parkinson validation.",
    }
    summary_json = output / "disease_exploratory_summary.json"
    summary_md = output / "disease_exploratory_summary.md"
    _write_text(summary_json, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    _write_report(summary_md, payload)
    platform_root = _resolve(config["paths"]["platform_root"])
    brain_root = _resolve(config["paths"]["brain_root"])
    operator_config = _resolve(config["paths"]["operator_config"])
    manifest = {
        "schema_version": "gate-20-disease-exploratory-proxy-manifest-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "config": str(config_path),
        "config_sha256": _sha256(config_path),
        "compact_artifacts": [],
        "raw_artifacts_retained": False,
        "raw_artifacts_compacted_after_qc": True,
        "simulation_pass_count": pass_count,
        "planned_rollouts": planned,
        "calibration_run": False,
        "holdout_validation": False,
        "gene_specific_mapping": False,
        "data_fabricated": False,
        "healthy_baseline_source": str(healthy_summary_path),
        "healthy_baseline_source_sha256": _sha256(healthy_summary_path),
        "platform_commit": _git_value(platform_root, "rev-parse", "HEAD"),
        "platform_worktree_status": _git_value(platform_root, "status", "--short"),
        "brain_root": str(brain_root),
        "brain_commit": _git_value(brain_root, "rev-parse", "HEAD"),
        "external_runner": str(platform_root / "scripts/run_brain_body_rollout.py"),
        "external_runner_sha256": _sha256(platform_root / "scripts/run_brain_body_rollout.py"),
        "operator_config_sha256": _sha256(operator_config),
        "scientific_boundary": "Organism-level computational exploratory proxy; not biological Parkinson validation.",
    }
    manifest_path = output / "manifest.json"
    artifact_paths = [config_path, output / "preflight.json", per_run_path, output / "per_run_metrics.partial.csv", summary_json, summary_md]
    artifact_paths.extend(sorted((output / "logs").glob("*.log")))
    artifact_paths.extend(sorted((output / "logs").glob("*.qc.json")))
    if (output / "videos").is_dir():
        artifact_paths.extend(path for path in sorted((output / "videos").glob("*.mp4")) if path.is_file())
    manifest["compact_artifacts"] = [
        {"path": str(path), "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in artifact_paths
        if path.is_file()
    ]
    _write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    checksum_paths = artifact_paths + [manifest_path]
    _write_text(output / "checksums.sha256", "\n".join(f"{_sha256(path)}  {path}" for path in checksum_paths if path.is_file()) + "\n")
    return 0 if status == "DISEASE_EXPLORATORY_PROXY_PASS" else 1


def finalize_checkpoint(config_path: Path, *, output_root: Path | None = None) -> int:
    config = _load_config(config_path)
    output = _resolve(output_root or config["paths"]["output_root"])
    preflight_path = output / "preflight.json"
    if not preflight_path.is_file():
        raise ValueError(f"Cannot finalize checkpoint without {preflight_path}")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if not isinstance(preflight, dict) or preflight.get("status") != "READY":
        raise ValueError("Cannot finalize a checkpoint with blocked preflight.")
    healthy_summary_path = _resolve(config["paths"]["healthy_baseline_summary"])
    rows = _load_checkpoint(output)
    if not rows:
        raise ValueError("No verified PASS rows are available for checkpoint finalization.")
    return _finalize_gate20(
        config_path=config_path,
        config=config,
        output=output,
        healthy_summary_path=healthy_summary_path,
        preflight=preflight,
        rows=rows,
    )


def run(config_path: Path, *, output_root: Path | None = None) -> int:
    config = _load_config(config_path)
    paths = config["paths"]
    output = _resolve(output_root or paths["output_root"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "logs").mkdir(parents=True, exist_ok=True)
    runtime = config["runtime"]
    brain_root = _resolve(paths["brain_root"])
    platform_root = _resolve(paths["platform_root"])
    brain_python = _resolve(paths["brain_python"])
    operator_config = _resolve(paths["operator_config"])
    healthy_summary_path = _resolve(paths["healthy_baseline_summary"])

    healthy_summary: dict[str, Any] = {}
    preflight_reasons: list[str] = []
    if not healthy_summary_path.is_file():
        preflight_reasons.append(f"healthy_baseline_summary_missing:{healthy_summary_path}")
    else:
        healthy_summary = json.loads(healthy_summary_path.read_text(encoding="utf-8"))
        if healthy_summary.get("status") != "HEALTHY_BASELINE_PASS":
            preflight_reasons.append(f"healthy_baseline_not_pass:{healthy_summary.get('status', 'MISSING')}")
        if healthy_summary.get("steps") != runtime["steps"] or healthy_summary.get("timestep_s") != runtime["timestep_s"]:
            preflight_reasons.append("healthy_baseline_protocol_mismatch")
    operator_ok, operator_reason = _operator_config_is_valid(operator_config)
    if not operator_ok:
        preflight_reasons.append(operator_reason)
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
    if artifact_audit.get("status") != "READY":
        preflight_reasons.append(f"runtime_artifact_audit={artifact_audit.get('status', 'MISSING')}")
    tracking_support = _runner_supports_tracking(platform_root)
    if not tracking_support:
        preflight_reasons.append("tracking_camera_support_missing")
    preflight = {
        "status": "READY" if not preflight_reasons else "BLOCKED",
        "reasons": preflight_reasons,
        "healthy_baseline": {"path": str(healthy_summary_path), "status": healthy_summary.get("status")},
        "artifact_audit": artifact_audit,
        "tracking_camera_support": tracking_support,
        "operator_config": {"path": str(operator_config), "sha256": _sha256(operator_config) if operator_config.is_file() else None},
        "simulation_run": False,
    }
    _write_text(output / "preflight.json", json.dumps(preflight, indent=2, ensure_ascii=False) + "\n")
    if preflight_reasons:
        payload = {
            "schema_version": "gate-20-disease-exploratory-proxy-summary-v1",
            "status": "DISEASE_EXPLORATORY_PROXY_BLOCKED",
            "simulation_run": False,
            "planned_rollouts": len(config["conditions"]) * len(runtime["seeds"]) * 5,
            "conditions": [item["condition_id"] for item in config["conditions"]],
            "burden_levels": [0.0, 0.25, 0.5, 0.75, 1.0],
            "preflight": preflight,
            "data_fabricated": False,
        }
        _write_text(output / "disease_exploratory_summary.json", json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        _write_report(output / "disease_exploratory_summary.md", {**payload, "seeds": runtime["seeds"], "steps": runtime["steps"], "duration_s": runtime["duration_s"], "timestep_s": runtime["timestep_s"], "device": runtime["device"], "stimulus": runtime["stimulus"], "cpg_frequency_hz": runtime["cpg_frequency_hz"], "rows": []})
        return 2

    rows = _load_checkpoint(output)
    completed = {
        (str(row["condition_id"]), float(row["burden_level"]), int(row["seed"]))
        for row in rows
    }
    if rows:
        print(f"Resuming {len(rows)} previously verified Gate 20 rollouts.", flush=True)
    temporary_root = Path(tempfile.mkdtemp(prefix="gate20-", dir=str(_resolve("D:/Bookdata"))))
    try:
        for condition in config["conditions"]:
            for burden in condition["burden_levels"]:
                for seed in runtime["seeds"]:
                    key = (str(condition["condition_id"]), float(burden), int(seed))
                    if key in completed:
                        print(f"condition={key[0]} burden={key[1]} seed={key[2]} status=CHECKPOINT_PASS", flush=True)
                        continue
                    row = _run_one(
                        condition_id=str(condition["condition_id"]),
                        burden=float(burden),
                        seed=int(seed),
                        config=config,
                        brain_root=brain_root,
                        platform_root=platform_root,
                        brain_python=brain_python,
                        operator_config=operator_config,
                        temporary_root=temporary_root,
                        output_root=output,
                        video=(int(seed) == 0 and float(burden) == 0.5 and str(condition["condition_id"]) == "alpha_synuclein"),
                    )
                    rows.append(row)
                    if row["status"] == "PASS":
                        completed.add(key)
                    _write_csv(output / "per_run_metrics.partial.csv", rows)
                    print(f"condition={condition['condition_id']} burden={burden} seed={seed} status={row['status']}", flush=True)
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)

    return _finalize_gate20(
        config_path=config_path,
        config=config,
        output=output,
        healthy_summary_path=healthy_summary_path,
        preflight={**preflight, "simulation_run": True},
        rows=rows,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument(
        "--finalize-checkpoint",
        action="store_true",
        help="Write a partial summary from verified PASS checkpoint rows without simulation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.finalize_checkpoint:
            return finalize_checkpoint(args.config, output_root=args.output_root)
        return run(args.config, output_root=args.output_root)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
