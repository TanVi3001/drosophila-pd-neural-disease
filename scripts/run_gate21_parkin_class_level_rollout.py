"""Run the evidence-gated Parkin class-level exploratory rollout campaign."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_CONFIG = ROOT / "experiments/gate_21_parkin_class_level_rollout/configs/parkin_class_level_exploratory.yaml"
DEFAULT_OUTPUT = ROOT / "experiments/gate_21_parkin_class_level_rollout/results"
DEFAULT_MAPPING = ROOT / "research/disease_mapping/manual_imports/parkin/codex_export.csv"
DEFAULT_SIGNOFF = ROOT / "research/disease_mapping/manual_imports/parkin/reviewer_signoff.json"
DEFAULT_HEALTHY = ROOT / "experiments/gate_11_healthy_baseline/manifests/healthy_baseline_manifest.json"
NEURAL_RUNNER = ROOT / "scripts/run_neural_experiment.py"
CANONICAL_METRICS = ("mean_planar_speed_mm_s", "distance_traveled_mm", "displacement_mm")
RAW_ARTIFACTS = (
    "rollout.json", "rollout.csv", "rollout.npz", "viewer_pose.json", "viewer_bundle.zip",
    "viewer_bundle", "biomarkers",
)
FAKE_IDS = {"todo_root_id", "fake_root_id", "synthetic_root", "tbd_root", "mock_root", "000000"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Config phai la YAML mapping: {path}")
    return value


def _load_mapping(path: Path) -> tuple[list[str], str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids: list[str] = []
    for row in rows:
        root_id = str(row.get("root_id", "")).strip()
        if not root_id or not root_id.isdigit() or root_id.lower() in FAKE_IDS:
            raise ValueError(f"Mapping Parkin co root_id khong hop le: {root_id!r}")
        ids.append(root_id)
    if len(ids) != 330 or len(set(ids)) != len(ids):
        raise ValueError(f"Mapping Parkin phai co 330 root ID duy nhat, nhan {len(ids)}")
    return ids, _sha256(path)


def _preflight(
    *, config: Mapping[str, Any], mapping_path: Path, signoff_path: Path, healthy_path: Path
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        mapping_ids, mapping_sha = _load_mapping(mapping_path)
    except (OSError, csv.Error, ValueError) as exc:
        mapping_ids, mapping_sha = [], ""
        blockers.append(f"mapping_invalid:{exc}")
    try:
        signoff = json.loads(signoff_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        signoff = {}
        blockers.append(f"signoff_invalid:{exc}")
    try:
        healthy = json.loads(healthy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        healthy = {}
        blockers.append(f"healthy_manifest_invalid:{exc}")

    if str(config.get("condition_id")) != "parkin":
        blockers.append("condition_must_be_parkin")
    if config.get("mapping_scope") != "class_level_exploratory":
        blockers.append("mapping_scope_must_be_class_level_exploratory")
    if config.get("gene_specific_mapping") is not False:
        blockers.append("gene_specific_mapping_must_be_false")
    if config.get("allowed_rollout_scope") != "CLASS_LEVEL_EXPLORATORY_ONLY":
        blockers.append("allowed_rollout_scope_must_be_class_level_exploratory")
    levels = config.get("burden_levels")
    if not isinstance(levels, list) or not levels:
        blockers.append("burden_levels_missing")
    else:
        values = [float(item.get("value")) for item in levels if isinstance(item, dict) and "value" in item]
        if values != sorted(set(values)) or values[0] < 0 or values[-1] > 1:
            blockers.append("burden_levels_must_be_sorted_and_in_[0,1]")
    runtime = config.get("runtime") if isinstance(config.get("runtime"), dict) else {}
    seeds = runtime.get("seeds")
    if not isinstance(seeds, list) or not seeds or any(int(seed) < 0 for seed in seeds):
        blockers.append("runtime_seeds_missing_or_invalid")
    if int(runtime.get("step_count", 0)) <= 0 or float(runtime.get("timestep_s", 0)) <= 0:
        blockers.append("runtime_step_count_or_timestep_invalid")
    parameters = config.get("exploratory_full_burden_parameters")
    if not isinstance(parameters, dict) or not parameters:
        blockers.append("exploratory_full_burden_parameters_missing")
    if signoff.get("decision") != "APPROVED_FOR_CLASS_LEVEL_EXPLORATORY":
        blockers.append("parkin_signoff_not_class_level_approved")
    if signoff.get("gene_specific_mapping") is not False:
        blockers.append("signoff_gene_specific_mapping_must_be_false")
    if signoff.get("allowed_rollout_scope") != "CLASS_LEVEL_EXPLORATORY_ONLY":
        blockers.append("signoff_scope_not_class_level_exploratory")
    if healthy.get("status") != "PASS":
        blockers.append("healthy_baseline_manifest_not_PASS")
    if healthy.get("disease_layer_enabled") is not False:
        blockers.append("healthy_baseline_disease_layer_not_OFF")
    if healthy.get("calibration_run") or healthy.get("holdout_validation_run"):
        blockers.append("healthy_baseline_has_calibration_or_holdout_flag")
    if healthy.get("metric_contract", {}).get("status") != "PASS":
        blockers.append("healthy_baseline_metric_contract_not_PASS")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "blockers": blockers,
        "mapping_count": len(mapping_ids),
        "mapping_sha256": mapping_sha,
        "signoff": signoff,
        "healthy_manifest_status": healthy.get("status", "MISSING"),
    }


def _runtime_config(
    *, config: Mapping[str, Any], root_ids: Sequence[str], burden: float, seed: int, mapping_path: Path, signoff_path: Path
) -> dict[str, Any]:
    runtime = config["runtime"]
    parameters = dict(config["exploratory_full_burden_parameters"])
    return {
        "condition_id": "parkin_class_level_exploratory",
        "gene_model": str(config["gene_model"]),
        "seed": int(seed),
        "target_neurons": list(root_ids),
        "target_edges": [],
        "full_burden": parameters,
        "burden_curve": [{"age_days": float(runtime["age_days"]), "burden": float(burden)}],
        "provenance": [
            _relative(mapping_path),
            _relative(signoff_path),
            _relative(DEFAULT_CONFIG),
            _relative(DEFAULT_HEALTHY),
        ],
        "notes": (
            "Class-level exploratory computational proxy. Parameters are declared sensitivity values, "
            "not gene-specific or literature-calibrated biological constants."
        ),
    }


def _read_metrics(path: Path) -> tuple[dict[str, float], dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    metrics: dict[str, float] = {}
    source: dict[str, Any] = {}
    scalar_metrics = document.get("scalar_metrics")
    if isinstance(scalar_metrics, dict):
        source.update(scalar_metrics)
    source.update(document)
    for key, value in source.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
            metrics[key] = float(value)
    return metrics, document


def _quality(npz_path: Path, *, expected_frames: int, timestep_s: float, metrics: Mapping[str, float]) -> dict[str, Any]:
    from scripts.run_healthy_baseline_multiseed import _rollout_quality

    return _rollout_quality(
        npz_path,
        expected_frames=expected_frames,
        expected_timestep_s=timestep_s,
        metrics=metrics,
    )


def _hash_and_discard_raw(output: Path, *, retain_raw: bool) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for name in RAW_ARTIFACTS:
        path = output / name
        paths = list(path.rglob("*") if path.is_dir() else ([path] if path.is_file() else []))
        for item in paths:
            if item.is_file():
                files.append({"path": item.relative_to(output).as_posix(), "size": item.stat().st_size, "sha256": _sha256(item)})
        if path.is_file() and not retain_raw:
            path.unlink()
        elif path.is_dir() and not retain_raw:
            import shutil

            shutil.rmtree(path)
    manifest = {"retained": retain_raw, "files": files}
    (output / "raw_artifact_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _run_one(
    *, config: Mapping[str, Any], root_ids: Sequence[str], mapping_path: Path, signoff_path: Path,
    output: Path, burden: float, burden_label: str, seed: int, brain_root: Path, platform_root: Path,
    brain_python: Path | None, annotations: Path, video: bool, retain_raw: bool,
) -> dict[str, Any]:
    runtime = config["runtime"]
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gate21-config-", dir=str(output.parent)) as temporary:
        condition_config = Path(temporary) / "condition.yaml"
        condition_config.write_text(yaml.safe_dump(_runtime_config(config=config, root_ids=root_ids, burden=burden, seed=seed, mapping_path=mapping_path, signoff_path=signoff_path), sort_keys=False), encoding="utf-8")
        command = [
            sys.executable, str(NEURAL_RUNNER),
            "--brain-root", str(brain_root), "--platform-root", str(platform_root),
            "--config", str(condition_config), "--annotations", str(annotations),
            "--age-days", str(runtime["age_days"]), "--seed", str(seed),
            "--steps", str(runtime["step_count"]), "--device", str(runtime["device"]),
            "--output", str(output), "--stimulus", str(runtime["stimulus"]),
            "--cpg-frequency-hz", str(runtime["cpg_frequency_hz"]),
        ]
        if brain_python is not None:
            command.extend(["--brain-python", str(brain_python)])
        if video:
            command.extend([
                "--video", "--video-output", str(output / "flygym_rollout.mp4"),
                "--video-fps", str(runtime["video_fps"]),
                "--video-width", str(runtime["video_width"]),
                "--video-height", str(runtime["video_height"]),
                "--video-playback-speed", str(runtime["video_playback_speed"]),
                "--video-camera-mode", str(runtime["video_camera_mode"]),
            ])
        log_path = output / "run.log"
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    status_path = output / "status.json"
    status_doc = json.loads(status_path.read_text(encoding="utf-8")) if status_path.is_file() else {}
    metrics_path = output / "metrics" / "metrics.json"
    metrics: dict[str, float] = {}
    runtime_doc: dict[str, Any] = {}
    missing: list[str] = []
    if metrics_path.is_file():
        try:
            metrics, runtime_doc = _read_metrics(metrics_path)
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            missing.append("metrics/metrics.json:invalid")
    else:
        missing.append("metrics/metrics.json")
    expected_frames = int(runtime["step_count"]) + 1
    finite = False
    try:
        with np.load(output / "rollout.npz", allow_pickle=False) as archive:
            finite = all(np.isfinite(np.asarray(archive[name])).all() for name in archive.files if np.issubdtype(np.asarray(archive[name]).dtype, np.number))
    except (OSError, ValueError, KeyError):
        missing.append("rollout.npz")
    quality = _quality(output / "rollout.npz", expected_frames=expected_frames, timestep_s=float(runtime["timestep_s"]), metrics=metrics)
    for name in CANONICAL_METRICS:
        value = quality.get(name)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            metrics[name] = float(value)
    required_present = all(name in metrics for name in CANONICAL_METRICS)
    quality_keys = ("timestamp_monotonic", "timestep_consistent", "locomotion_detected", "contact_detected", "joint_trajectory_changes", "action_trajectory_valid", "observation_state_valid", "quaternion_valid")
    quality_pass = finite and not missing and required_present and all(quality.get(key) == "PASS" for key in quality_keys)
    status = "PASS" if completed.returncode == 0 and status_doc.get("status") == "PASS" and quality_pass else str(status_doc.get("status", "FAILED_SIMULATION"))
    if completed.returncode != 0:
        status = "FAILED_SIMULATION"
    elif completed.returncode == 0 and not quality_pass and status == "PASS":
        status = "FAILED_PHYSICAL_QC"
    raw_manifest = _hash_and_discard_raw(output, retain_raw=retain_raw) if metrics_path.is_file() else {"retained": retain_raw, "files": []}
    row: dict[str, Any] = {
        "condition_id": "parkin",
        "mapping_scope": "class_level_exploratory",
        "gene_specific_mapping": False,
        "burden_level": burden,
        "burden_label": burden_label,
        "seed": seed,
        "status": status,
        "return_code": completed.returncode,
        "output": _relative(output),
        "metrics_path": _relative(metrics_path),
        "required_metric_status": "PASS" if required_present else "INCOMPLETE",
        "no_nan_inf": "PASS" if finite and not missing else "FAIL",
        "quality_status": "PASS" if quality_pass else "FAIL",
        "video_requested": video,
        "video_present": (output / "flygym_rollout.mp4").is_file(),
        "raw_artifacts_retained": retain_raw,
        "raw_artifact_manifest": _relative(output / "raw_artifact_manifest.json"),
        "missing_files": ";".join(missing),
        "frame_count": runtime_doc.get("frame_count", ""),
        "duration_s": runtime_doc.get("duration_s", ""),
        "timestep_s": runtime_doc.get("timestep_s", runtime["timestep_s"]),
    }
    row.update(quality)
    row.update(metrics)
    return row


def _summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for burden in sorted({float(row["burden_level"]) for row in rows}):
        selected = [row for row in rows if float(row["burden_level"]) == burden and row.get("status") == "PASS"]
        values: dict[str, Any] = {}
        for metric in CANONICAL_METRICS:
            data = np.asarray([float(row[metric]) for row in selected if isinstance(row.get(metric), (int, float))], dtype=float)
            if data.size:
                values[metric] = {"n": int(data.size), "mean": float(data.mean()), "sample_sd": float(data.std(ddof=1)) if data.size > 1 else 0.0, "se": float(data.std(ddof=1) / math.sqrt(data.size)) if data.size > 1 else 0.0}
        result[f"{burden:.2f}"] = values
    return result


def _write_report(path: Path, manifest: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> None:
    lines = [
        "# Gate 21: Parkin class-level exploratory rollout",
        "",
        f"Trang thai: `{manifest['status']}`",
        "",
        f"- Planned rollouts: `{manifest['planned_rollouts']}`.",
        f"- Executed rollouts: `{manifest['executed_rollouts']}`.",
        f"- Passed QC: `{manifest['passed_rollouts']}`.",
        f"- Mapping: `DAN/dopaminergic class-level`, gene-specific: `{manifest['gene_specific_mapping']}`.",
        f"- Calibration: `{manifest['calibration_run']}`; holdout: `{manifest['holdout_validation_run']}`.",
        "",
        "## Dien giai",
        "",
        "Gate nay chi kiem tra computational neural perturbation pipeline tren mot mapping class-level da review. "
        "Cac he so burden la proxy sensitivity values duoc khai bao trong config; chung khong phai so do Parkin, dopamine hay ket qua calibration.",
        "",
        "## QC per rollout",
        "",
        "| Burden | Seed | Status | Speed | Distance | Displacement | Contact | Joint | Video |",
        "| ---: | ---: | --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in rows:
        lines.append("| {burden} | {seed} | `{status}` | {speed} | {distance} | {displacement} | `{contact}` | `{joint}` | `{video}` |".format(
            burden=row.get("burden_level", ""), seed=row.get("seed", ""), status=row.get("status", ""),
            speed=row.get("mean_planar_speed_mm_s", "-"), distance=row.get("distance_traveled_mm", "-"),
            displacement=row.get("displacement_mm", "-"), contact=row.get("contact_detected", "-"),
            joint=row.get("joint_trajectory_changes", "-"), video="PASS" if row.get("video_present") else "-"))
    lines.extend([
        "",
        "## Ranh gioi khoa hoc",
        "",
        "Khong co gene-specific validation, biological Parkinson validation, calibration, holdout validation, clinical prediction hay drug validation trong Gate 21.",
        "",
        "Metrics chi la output cua computational rollout va chi duoc tong hop khi rollout dat QC. Khong co metric nao duoc tao khi simulation bi block.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_checksums(root: Path) -> None:
    entries: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "checksums.sha256":
            entries.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}")
    (root / "checksums.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def run_campaign(args: argparse.Namespace) -> int:
    config_path = args.config.resolve()
    config = _load_yaml(config_path)
    mapping_path = args.mapping.resolve()
    signoff_path = args.signoff.resolve()
    healthy_path = args.healthy_manifest.resolve()
    preflight = _preflight(config=config, mapping_path=mapping_path, signoff_path=signoff_path, healthy_path=healthy_path)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "preflight.json").write_text(json.dumps(preflight, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.preflight_only or preflight["status"] != "PASS":
        manifest = {
            "schema_version": "gate-21-parkin-class-level-exploratory-result-v1",
            "created_at_utc": datetime.now(UTC).isoformat(), "status": "PARKIN_CLASS_LEVEL_EXPLORATORY_ROLLOUTS_BLOCKED" if preflight["status"] != "PASS" else "PREFLIGHT_PASS",
            "planned_rollouts": 0, "executed_rollouts": 0, "passed_rollouts": 0,
            "mapping_scope": "class_level_exploratory", "gene_specific_mapping": False,
            "calibration_run": False, "holdout_validation_run": False, "tuning_run": False,
            "simulation_data_fabricated": False, "blockers": preflight["blockers"],
        }
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _write_report(output / "report.md", manifest, [])
        _write_checksums(output)
        print(f"Status: {manifest['status']}")
        for blocker in preflight["blockers"]:
            print(f"Blocker: {blocker}")
        return 0
    root_ids, _ = _load_mapping(mapping_path)
    runtime = config["runtime"]
    levels = [(float(item["value"]), str(item.get("label", f"burden_{item['value']}"))) for item in config["burden_levels"]]
    seeds = [int(value) for value in runtime["seeds"]]
    all_runs = [(burden, label, seed) for burden, label in levels for seed in seeds]
    planned = len(all_runs)
    selected_runs = all_runs[: args.limit] if args.limit is not None else all_runs
    rows: list[dict[str, Any]] = []
    with (output / "campaign.log").open("w", encoding="utf-8") as log:
        log.write(f"Gate 21 planned={planned} mapping_count={len(root_ids)}\n")
    for burden, label, seed in selected_runs:
            run_output = output / f"burden_{burden:0.2f}" / f"seed_{seed:03d}"
            wants_video = seed in [int(value) for value in config.get("video", {}).get("seeds", [])] and burden in [float(value) for value in config.get("video", {}).get("burdens", [])]
            print(f"[{len(rows) + 1}/{planned}] burden={burden:.2f} seed={seed}{' video' if wants_video else ''}")
            row = _run_one(
                config=config, root_ids=root_ids, mapping_path=mapping_path, signoff_path=signoff_path,
                output=run_output, burden=burden, burden_label=label, seed=seed,
                brain_root=args.brain_root.resolve(), platform_root=args.platform_root.resolve(),
                brain_python=args.brain_python.resolve() if args.brain_python else None,
                annotations=args.annotations.resolve(), video=wants_video,
                retain_raw=bool(config.get("video", {}).get("retain_raw", False)),
            )
            rows.append(row)
            with (output / "campaign.log").open("a", encoding="utf-8") as log:
                log.write(json.dumps(row, ensure_ascii=False) + "\n")
    fields = sorted({key for row in rows for key in row})
    with (output / "metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    passed = sum(row.get("status") == "PASS" for row in rows)
    failed = sum(row.get("status", "").startswith("FAILED") for row in rows)
    status = "PARKIN_CLASS_LEVEL_EXPLORATORY_ROLLOUTS_PASS" if passed == planned else ("PARKIN_CLASS_LEVEL_EXPLORATORY_ROLLOUTS_PARTIAL" if passed or failed else "PARKIN_CLASS_LEVEL_EXPLORATORY_ROLLOUTS_BLOCKED")
    manifest = {
        "schema_version": "gate-21-parkin-class-level-exploratory-result-v1",
        "created_at_utc": datetime.now(UTC).isoformat(), "status": status,
        "config": _relative(config_path), "config_sha256": _sha256(config_path),
        "mapping": _relative(mapping_path), "mapping_sha256": _sha256(mapping_path),
        "signoff": _relative(signoff_path), "signoff_sha256": _sha256(signoff_path),
        "healthy_baseline_manifest": _relative(healthy_path), "healthy_baseline_manifest_sha256": _sha256(healthy_path),
        "mapping_scope": "class_level_exploratory", "gene_specific_mapping": False,
        "planned_seeds": seeds, "planned_burden_levels": [value for value, _ in levels], "planned_rollouts": planned,
        "executed_rollouts": len(rows), "passed_rollouts": passed, "failed_rollouts": failed,
        "execution_limit": args.limit,
        "simulation_data_fabricated": False, "calibration_run": False, "holdout_validation_run": False, "tuning_run": False,
        "metrics": _summary(rows), "rows": rows,
        "scientific_boundary": "Class-level exploratory Parkin proxy only; not gene-specific or biological Parkinson validation.",
    }
    (output / "metrics.json").write_text(json.dumps({"schema_version": "gate-21-metrics-v1", **manifest}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_report(output / "report.md", manifest, rows)
    _write_checksums(output)
    print(f"Status: {status}; passed={passed}/{planned}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--signoff", type=Path, default=DEFAULT_SIGNOFF)
    parser.add_argument("--healthy-manifest", type=Path, default=DEFAULT_HEALTHY)
    parser.add_argument("--brain-root", type=Path, default=ROOT / "external/fly-brain")
    parser.add_argument("--platform-root", type=Path, default=ROOT.parent / "drosophila-pd-flygym")
    parser.add_argument("--brain-python", type=Path, default=None)
    parser.add_argument("--annotations", type=Path, default=ROOT / "annotations/neuron_annotations.csv")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="Chi chay N rollout dau tien cho pilot; khong dung trong campaign day du.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit phai lon hon 0")
    try:
        return run_campaign(args)
    except (OSError, ValueError, KeyError, TypeError, csv.Error, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
