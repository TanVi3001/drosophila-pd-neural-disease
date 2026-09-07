"""Build a claim-safe Gate 24 concordance evidence package.

The script reads compact, checksum-tracked artifacts from prior gates. It
does not start FlyGym, CUDA, calibration, holdout validation, or tuning.
"""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "experiments/gate_24_concordance/configs/concordance_analysis.yaml"
DEFAULT_OUTPUT = ROOT / "experiments/gate_24_concordance/results"
DEFAULT_REPORT = ROOT / "docs/concordance/gate_24_concordance_report.md"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return value


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"CSV is empty: {path}")
    return rows


def _finite(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is not numeric: {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} is not finite")
    return number


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _sample_sd(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    center = _mean(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / (len(values) - 1))


def _load_sources(config: Mapping[str, Any]) -> tuple[dict[str, Path], dict[str, Any]]:
    paths = {key: ROOT / value for key, value in config["sources"].items()}
    for key, path in paths.items():
        if not path.is_file():
            raise ValueError(f"Missing source {key}: {_relative(path)}")
    documents = {
        "gate13b": _json(paths["gate13b_summary"]),
        "gate13b_manifest": _json(paths["gate13b_manifest"]),
        "gate13b_config": _yaml(paths["gate13b_config"]),
        "gate13c": _json(paths["gate13c_manifest"]),
        "healthy": _json(paths["healthy_manifest"]),
        "gate21": _json(paths["gate21_manifest"]),
        "gate22": _json(paths["gate22_summary"]),
        "gate22_manifest": _json(paths["gate22_manifest"]),
        "gate23": _json(paths["gate23_summary"]),
        "gate23_manifest": _json(paths["gate23_manifest"]),
        "gate13b_rows": _csv(paths["gate13b_results"]),
        "gate13c_rows": _csv(paths["gate13c_metrics"]),
        "gate13c_summary_rows": _csv(paths["gate13c_summary"]),
        "gate22_rows": _csv(paths["gate22_metrics"]),
        "gate21_rows": _csv(paths["gate21_metrics"]),
        "healthy_rows": _csv(paths["healthy_metrics"]),
    }
    return paths, documents


def _validate_sources(config: Mapping[str, Any], documents: Mapping[str, Any]) -> None:
    for field in ("analysis_only", "run_gpu", "run_simulation", "run_calibration", "run_holdout_validation", "run_tuning"):
        expected = False if field.startswith("run_") else True
        if documents.get(field) is not None and documents[field] is not expected:
            raise ValueError(f"Gate 24 policy violation: {field}")
    if config.get("analysis_only") is not True:
        raise ValueError("Gate 24 must be analysis_only")
    for field in ("run_gpu", "run_simulation", "run_calibration", "run_holdout_validation", "run_tuning"):
        if config.get(field) is not False:
            raise ValueError(f"Gate 24 must keep {field}=false")

    gate13b = documents["gate13b"]
    if gate13b.get("status") != "CHEN_RATIO_CALIBRATION_PASS" or gate13b.get("selected_burden_level") != 0.5:
        raise ValueError("Gate 13B calibration lock is not valid")
    if gate13b.get("pozo_used") is not False or gate13b.get("no_holdout_validation_run") is not True:
        raise ValueError("Gate 13B was not isolated from Pozo holdout")
    gate13c = documents["gate13c"]
    if gate13c.get("status") != "CHEN_CALIBRATED_CONFIRMATION_PASS" or gate13c.get("calibrated_burden_level") != 0.5:
        raise ValueError("Gate 13C confirmation lock is not valid")
    if gate13c.get("no_pozo") is not True or gate13c.get("no_pink1") is not True:
        raise ValueError("Gate 13C unexpectedly used holdout data")
    if documents["healthy"].get("status") != "PASS":
        raise ValueError("Healthy baseline is not PASS")
    gate21 = documents["gate21"]
    if gate21.get("status") != "PARKIN_CLASS_LEVEL_EXPLORATORY_ROLLOUTS_PASS":
        raise ValueError("Gate 21 rollout is not PASS")
    if gate21.get("executed_rollouts") != 25 or gate21.get("passed_rollouts") != 25 or gate21.get("gene_specific_mapping") is not False:
        raise ValueError("Gate 21 execution or scope is invalid")
    gate22 = documents["gate22"]
    if gate22.get("status") != "PARKIN_HEALTHY_COMPARISON_PASS" or gate22.get("passed_comparison_rows") != 55:
        raise ValueError("Gate 22 comparison is not complete")
    if gate22.get("gene_specific_mapping") is not False or gate22.get("simulation_run") is not False:
        raise ValueError("Gate 22 scope is invalid")
    gate23 = documents["gate23"]
    if gate23.get("status") != "POZO_HOLDOUT_MISMATCH" or gate23.get("runtime_status") != "PASS":
        raise ValueError("Gate 23 result is not the locked runtime mismatch")
    if gate23.get("directionality_pass") is not True or gate23.get("quantitative_ratio_match") is not False:
        raise ValueError("Gate 23 claim lock changed")
    if gate23.get("no_pozo_tuning") is not True or gate23.get("no_parameter_reselection") is not True:
        raise ValueError("Gate 23 tuning boundary changed")


def _concordance_rows(documents: Mapping[str, Any]) -> list[dict[str, Any]]:
    gate13b = documents["gate13b"]
    gate13c = documents["gate13c"]
    gate21 = documents["gate21"]
    gate22 = documents["gate22"]
    gate23 = documents["gate23"]
    return [
        {
            "evidence_id": "chen_calibration",
            "stage": "calibration",
            "status": "PASS",
            "metric": "mean_planar_speed_ratio",
            "observed": gate13b["selected_simulated_ratio"],
            "target": gate13b["chen_ratio_target"],
            "error": gate13b["selected_ratio_error"],
            "scope": "organism_level_proxy",
            "claim_status": "allowed_computational_calibration",
            "interpretation": "Discrete burden 0.5 selected without using Pozo.",
        },
        {
            "evidence_id": "chen_confirmation",
            "stage": "confirmation",
            "status": "PASS",
            "metric": "mean_planar_speed_ratio",
            "observed": gate13c["confirmation_ratio"],
            "target": gate13c["chen_ratio_target"],
            "error": gate13c["confirmation_ratio_error"],
            "scope": "organism_level_proxy",
            "claim_status": "allowed_computational_confirmation",
            "interpretation": "Locked burden behavior confirmed on independent seeds.",
        },
        {
            "evidence_id": "gate21_rollout",
            "stage": "exploratory_rollout",
            "status": "PASS",
            "metric": "passed_rollouts",
            "observed": gate21["passed_rollouts"],
            "target": gate21["planned_rollouts"],
            "error": 0.0,
            "scope": "class_level_exploratory",
            "claim_status": "allowed_runtime_evidence",
            "interpretation": "25/25 rollout QC passed; not gene-specific validation.",
        },
        {
            "evidence_id": "gate22_comparison",
            "stage": "healthy_comparison",
            "status": "PASS",
            "metric": "comparison_rows",
            "observed": gate22["passed_comparison_rows"],
            "target": gate22["comparison_row_count"],
            "error": 0.0,
            "scope": "class_level_exploratory",
            "claim_status": "allowed_runtime_evidence",
            "interpretation": "Matched-seed comparison passed; burden response is not monotonic.",
        },
        {
            "evidence_id": "pozo_directionality",
            "stage": "holdout",
            "status": "PASS",
            "metric": "distance_directionality",
            "observed": gate23["simulated_distance_ratio"],
            "target": "< 1.0",
            "error": gate23["ratio_error"],
            "scope": "organism_level_proxy",
            "claim_status": "allowed_directional_concordance",
            "interpretation": "Distance decreased under locked burden 0.5.",
        },
        {
            "evidence_id": "pozo_quantitative_ratio",
            "stage": "holdout",
            "status": "MISMATCH",
            "metric": "distance_ratio_to_control",
            "observed": gate23["simulated_distance_ratio"],
            "target": gate23["pozo_target_ratio"],
            "error": gate23["ratio_error"],
            "scope": "organism_level_proxy",
            "claim_status": "mismatch_reported",
            "interpretation": "Simulated ratio is far from the Pozo target ratio.",
        },
        {
            "evidence_id": "gene_specific_validation",
            "stage": "scope",
            "status": "NOT_AVAILABLE",
            "metric": "gene_specific_mapping",
            "observed": "false",
            "target": "required",
            "error": "NA",
            "scope": "class_level_exploratory",
            "claim_status": "forbidden_positive_claim",
            "interpretation": "No gene-specific neuron/edge mapping is validated.",
        },
        {
            "evidence_id": "biological_parkinson_validation",
            "stage": "scope",
            "status": "NOT_AVAILABLE",
            "metric": "biological_validation",
            "observed": "false",
            "target": "required",
            "error": "NA",
            "scope": "computational_only",
            "claim_status": "forbidden_positive_claim",
            "interpretation": "Wet-lab biological validation is outside the evidence package.",
        },
    ]


def _descriptive_rows(documents: Mapping[str, Any], metrics: Sequence[str]) -> list[dict[str, Any]]:
    rows = [row for row in documents["gate22_rows"] if row.get("metric") in metrics]
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append({
            "burden_level": _finite(row["burden_level"], "burden_level"),
            "metric": row["metric"],
            "n_pairs": int(row["n_pairs"]),
            "healthy_mean": _finite(row["healthy_mean"], "healthy_mean"),
            "healthy_sample_sd": _finite(row["healthy_sample_sd"], "healthy_sample_sd"),
            "proxy_mean": _finite(row["proxy_mean"], "proxy_mean"),
            "proxy_sample_sd": _finite(row["proxy_sample_sd"], "proxy_sample_sd"),
            "delta": _finite(row["mean_delta_proxy_minus_healthy"], "delta"),
            "delta_sample_sd": _finite(row["delta_sample_sd"], "delta_sample_sd"),
            "delta_se": _finite(row["delta_se"], "delta_se"),
            "relative_change": _finite(row["mean_relative_change"], "relative_change"),
            "paired_standardized_delta": _finite(row["paired_standardized_delta"], "paired_standardized_delta"),
            "qc_status": row["comparison_status"],
        })
    if len(result) != len(metrics) * 5:
        raise ValueError(f"Expected {len(metrics) * 5} Gate 22 primary rows, found {len(result)}")
    return result


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def _plot_chen(path: Path, documents: Mapping[str, Any]) -> None:
    gate13b = documents["gate13b"]
    gate13c = documents["gate13c"]
    labels = ["Chen target", "Gate 13B selected", "Gate 13C confirmation"]
    values = [gate13b["chen_ratio_target"], gate13b["selected_simulated_ratio"], gate13c["confirmation_ratio"]]
    colors = ["#c98b2e", "#2364aa", "#3a9d5d"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylabel("Ratio")
    ax.set_title("Chen calibration and confirmation ratios")
    ax.set_ylim(0, max(values) * 1.25)
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.3f}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _plot_gate22(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    labels = {
        "mean_planar_speed_mm_s": "Planar speed (mm/s)",
        "distance_traveled_mm": "Distance (mm)",
        "displacement_mm": "Displacement (mm)",
    }
    for ax, metric in zip(axes, labels):
        selected = [row for row in rows if row["metric"] == metric]
        burdens = [row["burden_level"] for row in selected]
        healthy = [row["healthy_mean"] for row in selected]
        proxy = [row["proxy_mean"] for row in selected]
        ax.plot(burdens, healthy, "o--", label="Healthy", color="#555555")
        ax.plot(burdens, proxy, "o-", label="Parkin proxy", color="#c34a36")
        ax.set_xlabel("Burden")
        ax.set_ylabel(labels[metric])
        ax.grid(alpha=0.25)
        ax.set_xticks(burdens)
    axes[0].legend(frameon=False)
    fig.suptitle("Gate 22 matched-seed Healthy comparison")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _plot_pozo(path: Path, documents: Mapping[str, Any]) -> None:
    gate23 = documents["gate23"]
    labels = ["Simulated ratio", "Pozo target ratio"]
    values = [gate23["simulated_distance_ratio"], gate23["pozo_target_ratio"]]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(labels, values, color=["#c34a36", "#2364aa"])
    ax.set_ylabel("Distance ratio to control")
    ax.set_title("Pozo holdout ratio: mismatch remains")
    ax.set_ylim(0, 1.1)
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.3f}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _plot_directionality(path: Path, documents: Mapping[str, Any]) -> None:
    gate23 = documents["gate23"]
    labels = ["Control", "Burden 0.5"]
    values = [gate23["mean_distance_control_mm"], gate23["mean_distance_holdout_mm"]]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(labels, values, color=["#777777", "#c98b2e"])
    ax.set_ylabel("Distance traveled (mm)")
    ax.set_title("Pozo directionality: distance decreases")
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.3f}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _plot_qc(path: Path, concordance: Sequence[Mapping[str, Any]]) -> None:
    statuses = {"PASS": "#3a9d5d", "MISMATCH": "#c34a36", "NOT_AVAILABLE": "#777777"}
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.axis("off")
    table_data = [[row["evidence_id"], row["status"], row["scope"], row["claim_status"]] for row in concordance]
    table = ax.table(cellText=table_data, colLabels=["Evidence", "Status", "Scope", "Claim status"], loc="center", cellLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.55)
    for row_index, row in enumerate(concordance, start=1):
        table[(row_index, 1)].set_facecolor(statuses.get(row["status"], "#ffffff"))
        table[(row_index, 1)].get_text().set_color("white" if row["status"] != "NOT_AVAILABLE" else "white")
    ax.set_title("Gate 24 QC and claim-scope matrix", pad=12)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _write_report(path: Path, summary: Mapping[str, Any], concordance: Sequence[Mapping[str, Any]]) -> None:
    lines = [
        "# Gate 24: Concordance analysis va bang chung cho bai bao",
        "",
        f"**Trang thai:** `{summary['status']}`",
        "",
        "Gate 24 la phan tich hau nghiem tren artifact da khoa tu Gate 13B, 13C, 21, 22 va 23. Gate nay khong chay GPU, simulation, calibration, holdout validation hoac tuning moi.",
        "",
        "## Cau hoi phan tich",
        "",
        "- Parameter Chen da khoa co duoc xac nhan lai khong? Co, o muc computational confirmation.",
        "- Proxy co tao ra thay doi van dong co QC khong? Co, nhung pham vi la organism/class-level exploratory.",
        "- Co phu hop voi Pozo ve huong thay doi khong? Co, distance giam duoi burden 0.5.",
        "- Co phu hop dinh luong voi Pozo khong? Khong; quantitative ratio mismatch van lon.",
        "",
        "## Concordance matrix",
        "",
        "| Evidence | Stage | Status | Metric | Observed | Target | Error | Scope | Claim status |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in concordance:
        lines.append(f"| {row['evidence_id']} | {row['stage']} | `{row['status']}` | `{row['metric']}` | {row['observed']} | {row['target']} | {row['error']} | `{row['scope']}` | `{row['claim_status']}` |")
    lines.extend([
        "",
        "## Thong ke",
        "",
        "Gate 22 cung cap mean, sample SD, SE, delta, relative change va paired standardized delta cho 5 seed ghep cap. Khong tinh p-value va khong xem seed la mau sinh hoc doc lap. Pozo ratio mismatch duoc bao cao theo artifact da khoa; khong dat tolerance hau nghiem.",
        "",
        "## Claim duoc phep dung",
        "",
        "> Chen-calibrated organism-level computational locomotion proxy with directional Pozo holdout concordance and substantial quantitative ratio mismatch.",
        "",
        "## Claim bi cam",
        "",
        "- Biological Parkinson validation.",
        "- Gene-specific PINK1 validation.",
        "- Quantitative Pozo validation.",
        "- Clinical validation.",
        "- Drug efficacy validation.",
        "",
        "## Hinh va artifact",
        "",
        "- `results/figures/chen_ratio_concordance.png`: Chen target, calibration va confirmation.",
        "- `results/figures/gate22_burden_response.png`: Healthy va Parkin proxy theo burden.",
        "- `results/figures/pozo_ratio_concordance.png`: simulated ratio va Pozo ratio.",
        "- `results/figures/pozo_directionality.png`: control va burden 0.5.",
        "- `results/figures/qc_claim_matrix.png`: QC/provenance/claim matrix.",
        "",
        "## Gioi han",
        "",
        "Ket qua hien tai phu hop voi mot bai computational locomotion proxy co calibration va holdout directionality, khong phai bang chung thay the thi nghiem ruoi that. Quantitative mismatch voi Pozo la ket qua can duoc giu nguyen trong manuscript, khong duoc lam mem hoac bo qua.",
    ])
    _write_text(path, "\n".join(lines) + "\n")


def run(*, config_path: Path = DEFAULT_CONFIG, output_dir: Path = DEFAULT_OUTPUT, report_path: Path = DEFAULT_REPORT) -> dict[str, Any]:
    config = _yaml(config_path)
    paths, documents = _load_sources(config)
    _validate_sources(config, documents)
    metrics = list(config["primary_metrics"])
    concordance = _concordance_rows(documents)
    descriptive = _descriptive_rows(documents, metrics)
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    concordance_path = output_dir / "concordance_matrix.csv"
    descriptive_path = output_dir / "descriptive_metrics.csv"
    summary_path = output_dir / "concordance_summary.json"
    _write_csv(concordance_path, concordance)
    _write_csv(descriptive_path, descriptive)
    _plot_chen(figures_dir / "chen_ratio_concordance.png", documents)
    _plot_gate22(figures_dir / "gate22_burden_response.png", descriptive)
    _plot_pozo(figures_dir / "pozo_ratio_concordance.png", documents)
    _plot_directionality(figures_dir / "pozo_directionality.png", documents)
    _plot_qc(figures_dir / "qc_claim_matrix.png", concordance)
    summary = {
        "schema_version": "gate-24-concordance-summary-v1",
        "status": "CONCORDANCE_REPORT_COMPLETE",
        "analysis_only": True,
        "run_gpu": False,
        "run_simulation": False,
        "run_calibration": False,
        "run_holdout_validation": False,
        "run_tuning": False,
        "source_count": len(paths),
        "concordance_row_count": len(concordance),
        "descriptive_row_count": len(descriptive),
        "gate13b_status": documents["gate13b"]["status"],
        "gate13b_selected_burden": documents["gate13b"]["selected_burden_level"],
        "gate13b_selected_ratio": documents["gate13b"]["selected_simulated_ratio"],
        "gate13b_target_ratio": documents["gate13b"]["chen_ratio_target"],
        "gate13c_status": documents["gate13c"]["status"],
        "gate13c_confirmation_ratio": documents["gate13c"]["confirmation_ratio"],
        "gate21_status": documents["gate21"]["status"],
        "gate21_rollouts": documents["gate21"]["passed_rollouts"],
        "gate22_status": documents["gate22"]["status"],
        "gate22_comparison_rows": documents["gate22"]["passed_comparison_rows"],
        "gate23_status": documents["gate23"]["status"],
        "pozo_directionality": documents["gate23"]["directionality_pass"],
        "pozo_simulated_ratio": documents["gate23"]["simulated_distance_ratio"],
        "pozo_target_ratio": documents["gate23"]["pozo_target_ratio"],
        "pozo_quantitative_match": documents["gate23"]["quantitative_ratio_match"],
        "gene_specific_validation": False,
        "biological_parkinson_validation": False,
        "permitted_claim": config["claim_lock"]["permitted"],
        "forbidden_claims": config["claim_lock"]["forbidden"],
        "source_artifacts": {key: {"path": _relative(path), "sha256": _sha256(path)} for key, path in paths.items()},
        "artifacts": {
            "concordance_matrix": _relative(concordance_path),
            "descriptive_metrics": _relative(descriptive_path),
            "report": _relative(report_path),
            "figures": [_relative(path) for path in sorted(figures_dir.glob("*.png"))],
        },
    }
    _write_report(report_path, summary, concordance)
    _write_text(summary_path, json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    manifest_path = output_dir.parent / "manifests" / "gate24_concordance_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "gate-24-concordance-manifest-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": summary["status"],
        "summary": _relative(summary_path),
        "summary_sha256": _sha256(summary_path),
        "config": _relative(config_path),
        "config_sha256": _sha256(config_path),
        "no_new_simulation": True,
        "no_calibration": True,
        "no_holdout_validation": True,
        "no_tuning": True,
        "gene_specific_validation": False,
        "biological_parkinson_validation": False,
        "pozo_quantitative_match": False,
        "source_artifacts": summary["source_artifacts"],
        "artifacts": summary["artifacts"],
    }
    _write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    checksum_targets = [concordance_path, descriptive_path, summary_path, manifest_path, report_path, *sorted(figures_dir.glob("*.png"))]
    checksum_path = manifest_path.parent / "gate24_checksums.sha256"
    _write_text(checksum_path, "".join(f"{_sha256(path)}  {_relative(path)}\n" for path in checksum_targets))
    return {**summary, "manifest": _relative(manifest_path), "checksum_file": _relative(checksum_path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(config_path=args.config, output_dir=args.output, report_path=args.report)
    print(json.dumps({key: result[key] for key in ("status", "concordance_row_count", "descriptive_row_count", "gate23_status", "pozo_quantitative_match")}, indent=2))
    print(f"Manifest: {result['manifest']}")
    print(f"Report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
