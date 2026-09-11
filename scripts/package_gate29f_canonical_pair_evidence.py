"""Package lightweight evidence for the completed Gate29 canonical pair.

This command is analysis-only. It reads the immutable external rollout artifacts,
validates the frozen pair, and writes only small reviewable evidence files to Git.
It never launches FlyGym, MuJoCo, CUDA, calibration, or disease execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from drosophila_pd_neural.causal_trace import (  # noqa: E402
    compare_trace_arrays,
    summarize_trace_arrays,
)
from drosophila_pd_neural.causal_trace.schema import (  # noqa: E402
    NONPERTURBATION_COMPARISONS,
)

from scripts import run_gate29_neural_causal_trace as trace_runner  # noqa: E402


DEFAULT_RAW_ROOT = ROOT.parent / "gate29_technical_outputs/canonical_pair_v1"
GATE_ROOT = ROOT / "experiments/gate_29f_canonical_pair_evidence"
MANIFEST_PATH = GATE_ROOT / "manifests/canonical_pair_evidence_manifest.json"
CHECKSUM_PATH = GATE_ROOT / "manifests/raw_artifact_checksums.sha256"
PACKAGE_CHECKSUM_PATH = GATE_ROOT / "manifests/package_artifact_checksums.sha256"
COMPARISON_PATH = GATE_ROOT / "results/canonical_pair_comparison.json"
METRICS_PATH = GATE_ROOT / "results/canonical_pair_metrics.json"
TRACE_SUMMARY_PATH = GATE_ROOT / "results/canonical_pair_trace_summary.json"
REPORT_PATH = ROOT / "docs/research_design/gate29f_canonical_pair_evidence_report.md"

AUTHORIZATION_PATH = (
    ROOT
    / "experiments/gate_29_neural_causal_trace/manifests/"
    "canonical_pair_execution_authorization.json"
)
FREEZE_PATH = (
    ROOT
    / "experiments/gate_29_neural_causal_trace/manifests/"
    "canonical_pair_execution_freeze.json"
)

RAW_ARTIFACTS = (
    "baseline/rollout.npz",
    "trace/rollout.npz",
    "trace/trace_arrays.npz",
    "baseline/metadata.json",
    "trace/metadata.json",
    "baseline/metrics/metrics.json",
    "trace/metrics/metrics.json",
    "logs/baseline.log",
    "logs/trace.log",
    "execution_state/status.json",
)

SCALAR_METRICS = (
    "median_planar_speed_mm_s",
    "distance_traveled_mm",
    "thorax_displacement_xy_mm",
)


class Gate29FError(RuntimeError):
    """Fail-closed Gate29-F evidence packaging error."""


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Gate29FError(f"required file is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise Gate29FError(message)


def _authorization_commit() -> str:
    relative = AUTHORIZATION_PATH.relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "-C", str(ROOT), "log", "-1", "--format=%H", "--", relative],
        capture_output=True,
        text=True,
        check=False,
    )
    commit = result.stdout.strip()
    if result.returncode != 0 or len(commit) != 40:
        raise Gate29FError("cannot resolve authorization commit")
    return commit


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        return {key: np.array(data[key], copy=True) for key in data.files}


def _artifact_records(raw_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relative in RAW_ARTIFACTS:
        path = raw_root / relative
        _require(path.is_file(), f"required raw artifact is missing: {relative}")
        records.append(
            {
                "logical_path": f"gate29_technical_outputs/canonical_pair_v1/{relative}",
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return records


def _comparison(raw_root: Path) -> dict[str, Any]:
    baseline = _load_npz(raw_root / "baseline/rollout.npz")
    traced = _load_npz(raw_root / "trace/trace_arrays.npz")
    required_baseline = {
        "timestamp_s",
        "thorax_positions",
        "joint_positions",
        "actuator_position",
        "contact_found",
    }
    _require(required_baseline.issubset(baseline), "baseline rollout schema is incomplete")
    baseline_aligned = {
        "timestamp_s": baseline["timestamp_s"][1:],
        "thorax": baseline["thorax_positions"][1:],
        "joint_positions": baseline["joint_positions"][1:],
        "actuator_position": baseline["actuator_position"][1:],
        "contact_found": baseline["contact_found"][1:],
    }
    result = compare_trace_arrays(
        baseline_aligned,
        traced,
        NONPERTURBATION_COMPARISONS,
    )
    _require(
        result["status"] == "TRACE_OBSERVATION_NONPERTURBING_PASS",
        "canonical trace changes the frozen healthy rollout",
    )
    return result


def _metrics(raw_root: Path) -> dict[str, Any]:
    baseline = _json(raw_root / "baseline/metrics/metrics.json")
    trace = _json(raw_root / "trace/metrics/metrics.json")
    rows: list[dict[str, Any]] = []
    for metric in SCALAR_METRICS:
        baseline_value = baseline.get(metric)
        trace_value = trace.get(metric)
        _require(
            isinstance(baseline_value, (int, float))
            and isinstance(trace_value, (int, float)),
            f"metric is missing or nonnumeric: {metric}",
        )
        delta = float(trace_value) - float(baseline_value)
        _require(delta == 0.0, f"baseline/trace metric mismatch: {metric}")
        rows.append(
            {
                "metric": metric,
                "baseline": float(baseline_value),
                "trace": float(trace_value),
                "delta": delta,
            }
        )
    return {
        "status": "GATE29F_CANONICAL_METRICS_EXACT_MATCH",
        "rows": rows,
        "unit_context": {
            "median_planar_speed_mm_s": "mm/s",
            "distance_traveled_mm": "mm",
            "thorax_displacement_xy_mm": "mm",
        },
    }


def build_package(raw_root: Path) -> dict[str, Any]:
    raw_root = raw_root.resolve()
    authorization = _json(AUTHORIZATION_PATH)
    freeze = _json(FREEZE_PATH)
    state = _json(raw_root / "execution_state/status.json")
    identity = trace_runner._paired_execution_identity({"output_root": raw_root})

    _require(authorization.get("authorized") is True, "canonical pair is not authorized")
    _require(
        authorization.get("status") == "GATE29_CANONICAL_PAIR_HUMAN_AUTHORIZED",
        "authorization status is invalid",
    )
    _require(state.get("state") == "PAIR_COMPLETE", "canonical pair is not complete")
    _require(state.get("pair_id") == freeze.get("pair_id"), "pair identity mismatch")
    _require(identity["seed"] == freeze.get("seed") == 9202, "canonical seed mismatch")
    _require(identity["condition"] == freeze.get("condition") == "healthy", "condition mismatch")
    _require(identity["runtime_commit"] == freeze.get("runtime_commit"), "runtime mismatch")
    _require(
        identity["checkpoint_sha256"] == freeze.get("checkpoint_sha256"),
        "checkpoint mismatch",
    )
    _require(identity["brain_device"] == "cuda", "canonical run was not recorded on CUDA")
    _require(state.get("baseline", {}).get("returncode") == 0, "baseline job failed")
    _require(state.get("trace", {}).get("returncode") == 0, "trace job failed")
    _require(state.get("retry") is False, "retry policy was violated")
    _require(state.get("scientific_jobs") == 0, "scientific job firewall was violated")
    _require(state.get("disease_jobs") == 0, "disease job firewall was violated")

    comparison = _comparison(raw_root)
    metrics = _metrics(raw_root)
    trace_arrays = _load_npz(raw_root / "trace/trace_arrays.npz")
    signal_summary = summarize_trace_arrays(trace_arrays)
    artifacts = _artifact_records(raw_root)
    authorization_commit = _authorization_commit()

    trace_summary = {
        "status": "GATE29F_CANONICAL_TRACE_CAPTURED",
        "pair_id": freeze["pair_id"],
        "seed": identity["seed"],
        "step_count": int(trace_arrays["step_index"].shape[0]),
        "signal_count": len(trace_arrays),
        "signal_summary": signal_summary,
        "runtime_verified_edges": 0,
        "biological_causality_established": False,
    }
    manifest = {
        "schema_version": "gate29f-canonical-pair-evidence-v1",
        "status": "GATE29F_CANONICAL_PAIR_EVIDENCE_LOCKED",
        "pair_id": freeze["pair_id"],
        "seed": identity["seed"],
        "condition": identity["condition"],
        "jobs_executed": 2,
        "baseline_returncode": state["baseline"]["returncode"],
        "trace_returncode": state["trace"]["returncode"],
        "execution_state": state["state"],
        "execution_code_head": authorization["authorized_execution_code_head"],
        "freeze_commit": authorization["authorized_freeze_commit"],
        "authorization_commit": authorization_commit,
        "analyzer_source_sha256": _sha256(Path(trace_runner.__file__)),
        "packager_source_sha256": _sha256(Path(__file__)),
        "runtime_commit": identity["runtime_commit"],
        "brain_source_tree_sha256": authorization[
            "authorized_brain_source_tree_sha256"
        ],
        "checkpoint_sha256": identity["checkpoint_sha256"],
        "reviewer": authorization["reviewer"],
        "review_date": authorization["review_date"],
        "gpu": {
            "preflight": state["gpu_preflight"],
            "baseline_peak_memory_mb": state["baseline"][
                "device_peak_memory_used_mb"
            ],
            "baseline_max_temperature_c": state["baseline"][
                "max_observed_gpu_temperature_c"
            ],
            "trace_peak_memory_mb": state["trace"]["device_peak_memory_used_mb"],
            "trace_max_temperature_c": state["trace"][
                "max_observed_gpu_temperature_c"
            ],
            "temperature_abort_threshold_c": state["trace"][
                "gpu_temperature_abort_threshold_c"
            ],
            "memory_scope": state["trace"]["device_memory_scope"],
        },
        "comparison_status": comparison["status"],
        "comparison_rtol": comparison["rtol"],
        "comparison_atol": comparison["atol"],
        "discrete_comparison": comparison["discrete_comparison"],
        "metrics_status": metrics["status"],
        "raw_artifact_root_logical": "gate29_technical_outputs/canonical_pair_v1",
        "raw_artifacts_outside_git": True,
        "raw_artifact_count": len(artifacts),
        "raw_artifact_total_bytes": sum(item["size_bytes"] for item in artifacts),
        "raw_artifacts": artifacts,
        "scientific_jobs": 0,
        "disease_jobs": 0,
        "calibration_run": False,
        "fitting_run": False,
        "retuning": False,
        "dopamine_implemented": False,
        "biological_validation": False,
        "claim_scope": "ENGINEERING_NONPERTURBATION_EVIDENCE_ONLY",
    }
    return {
        "manifest": manifest,
        "comparison": comparison,
        "metrics": metrics,
        "trace_summary": trace_summary,
    }


def _report(package: Mapping[str, Any]) -> str:
    manifest = package["manifest"]
    rows = package["metrics"]["rows"]
    comparisons = package["comparison"]["comparisons"]
    lines = [
        "# Gate 29-F - Khóa bằng chứng canonical pair",
        "",
        f"Trạng thái: `{manifest['status']}`.",
        "",
        "## Mục tiêu",
        "",
        "Gate này đóng gói bằng chứng của cặp healthy engineering đã được chạy đúng một lần. "
        "Nó kiểm tra rằng instrumentation đọc neural/body signals không làm thay đổi rollout.",
        "",
        "## Danh tính execution",
        "",
        f"- Pair: `{manifest['pair_id']}`",
        f"- Seed: `{manifest['seed']}`",
        f"- Jobs: `{manifest['jobs_executed']}`",
        f"- Execution state: `{manifest['execution_state']}`",
        f"- Execution code: `{manifest['execution_code_head']}`",
        f"- Freeze commit: `{manifest['freeze_commit']}`",
        f"- Authorization commit: `{manifest['authorization_commit']}`",
        f"- Runtime commit: `{manifest['runtime_commit']}`",
        f"- Checkpoint SHA256: `{manifest['checkpoint_sha256']}`",
        "",
        "## GPU safety",
        "",
        f"- Baseline: peak `{manifest['gpu']['baseline_peak_memory_mb']} MiB`, max `{manifest['gpu']['baseline_max_temperature_c']} C`.",
        f"- Trace: peak `{manifest['gpu']['trace_peak_memory_mb']} MiB`, max `{manifest['gpu']['trace_max_temperature_c']} C`.",
        f"- Ngưỡng abort: `{manifest['gpu']['temperature_abort_threshold_c']} C`.",
        "- Cả hai job kết thúc với return code 0; không retry.",
        "",
        "## Metrics",
        "",
        "| Metric | Baseline | Trace | Delta |",
        "|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['metric']}` | {row['baseline']:.12g} | {row['trace']:.12g} | {row['delta']:.12g} |"
        )
    lines.extend(
        [
            "",
            "## Non-perturbation comparison",
            "",
            "| Signal | Shape | Max absolute difference | Kết quả |",
            "|---|---|---:|---|",
        ]
    )
    for name, result in comparisons.items():
        shape = "x".join(str(value) for value in result["shape_baseline"])
        lines.append(
            f"| `{name}` | `{shape}` | {result['max_abs_diff']:.12g} | `{'PASS' if result['passed'] else 'FAIL'}` |"
        )
    lines.extend(
        [
            "",
            f"Kết luận kỹ thuật: `{package['comparison']['status']}` với "
            f"`rtol={package['comparison']['rtol']}` và `atol={package['comparison']['atol']}`.",
            "",
            "## Provenance và lưu trữ",
            "",
            f"Gói khóa `{manifest['raw_artifact_count']}` raw artifacts, tổng "
            f"`{manifest['raw_artifact_total_bytes']}` bytes bằng SHA256. Raw `.npz` nằm ngoài Git; "
            "repository chỉ giữ manifest, checksum, kết quả tổng hợp và báo cáo nhẹ.",
            "",
            "## Giới hạn claim",
            "",
            "Gate 29-F chỉ chứng minh instrumentation không làm thay đổi cặp healthy engineering "
            "trong các signal đã khóa. Gate này không phải disease execution, không calibration, "
            "không xác nhận dopamine, không chứng minh neural causality sinh học và không phải "
            "biological Parkinson validation.",
            "",
        ]
    )
    return "\n".join(lines)


def write_package(raw_root: Path) -> dict[str, Any]:
    package = build_package(raw_root)
    _write_json(COMPARISON_PATH, package["comparison"])
    _write_json(METRICS_PATH, package["metrics"])
    _write_json(TRACE_SUMMARY_PATH, package["trace_summary"])
    _write_json(MANIFEST_PATH, package["manifest"])
    CHECKSUM_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKSUM_PATH.write_text(
        "".join(
            f"{item['sha256']}  {item['logical_path']}\n"
            for item in package["manifest"]["raw_artifacts"]
        ),
        encoding="utf-8",
        newline="\n",
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(_report(package), encoding="utf-8", newline="\n")
    package_paths = (
        MANIFEST_PATH,
        COMPARISON_PATH,
        METRICS_PATH,
        TRACE_SUMMARY_PATH,
        REPORT_PATH,
    )
    PACKAGE_CHECKSUM_PATH.write_text(
        "".join(
            f"{_sha256(path)}  {path.relative_to(ROOT).as_posix()}\n"
            for path in package_paths
        ),
        encoding="utf-8",
        newline="\n",
    )
    return package


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    package = build_package(args.raw_root)
    if not args.verify_only:
        package = write_package(args.raw_root)
    print(
        json.dumps(
            {
                "status": package["manifest"]["status"],
                "pair_id": package["manifest"]["pair_id"],
                "seed": package["manifest"]["seed"],
                "comparison_status": package["comparison"]["status"],
                "raw_artifact_count": package["manifest"]["raw_artifact_count"],
                "gpu_execution_in_packaging": False,
                "simulation_execution_in_packaging": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
