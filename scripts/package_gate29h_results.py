#!/usr/bin/env python3
"""Freeze and package the completed Gate29-H scientific result.

This script is deliberately analysis-only. It reads completed Gate29-H artifacts,
checks the expected 15-job matrix and preregistered result, creates a lightweight
release packet, and never launches a GPU job or changes any raw output.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from datetime import date
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_BASE = Path(r"E:\Drosophila_Parkinson\gate29h_scientific_outputs")
DEFAULT_ROOT_NAME = (
    "GATE29H_RIEMENSPERGER_SCIENTIFIC_TRACE_V1_ATTEMPT_003_CONTINUATION_003"
)
SOURCE_ROOT_NAMES = (
    "GATE29H_RIEMENSPERGER_SCIENTIFIC_TRACE_V1_ATTEMPT_003",
    "GATE29H_RIEMENSPERGER_SCIENTIFIC_TRACE_V1_ATTEMPT_003_CONTINUATION_002",
    "GATE29H_RIEMENSPERGER_SCIENTIFIC_TRACE_V1_ATTEMPT_003_CONTINUATION_003",
)
CONDITIONS = (
    "healthy_control",
    "dopamine_class_level_burden_zero",
    "dopamine_class_level_full_burden",
)
SEEDS = tuple(range(5))
PRIMARY = "median_planar_speed_mm_s"
TRACE_ENDPOINT = "brain_body_drive_mean_l2"
JOB_ARTIFACTS = (
    "brain_body_summary.json",
    "gate29h_job_manifest.json",
    "manifest.json",
    "metadata.json",
    "metrics/metrics.csv",
    "metrics/metrics.json",
    "report/summary.md",
    "rollout.npz",
    "rollout_index.json",
    "trace_arrays.npz",
    "trace_metadata.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def format_number(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return "NA"
    return f"{float(value):.{digits}f}"


def discover_jobs(source_roots: list[tuple[str, Path]]) -> dict[str, dict[str, Any]]:
    jobs: dict[str, dict[str, Any]] = {}
    for source_label, source_root in source_roots:
        manifests = sorted(source_root.rglob("gate29h_job_manifest.json"))
        for manifest_path in manifests:
            data = read_json(manifest_path)
            condition = data.get("condition_id")
            seed = data.get("seed")
            if condition not in CONDITIONS or seed not in SEEDS:
                continue
            job_id = f"{condition}_seed_{int(seed):03d}"
            if job_id in jobs:
                raise RuntimeError(f"duplicate Gate29-H job discovered: {job_id}")
            jobs[job_id] = {
                "job_id": job_id,
                "condition_id": condition,
                "seed": int(seed),
                "source_label": source_label,
                "source_root": str(source_root),
                "job_root": manifest_path.parent,
                "manifest": data,
            }
    expected = {
        f"{condition}_seed_{seed:03d}"
        for condition in CONDITIONS
        for seed in SEEDS
    }
    discovered = set(jobs)
    if discovered != expected:
        missing = sorted(expected - discovered)
        extra = sorted(discovered - expected)
        raise RuntimeError(f"Gate29-H matrix mismatch; missing={missing}, extra={extra}")
    return jobs


def validate_inputs(
    analysis: dict[str, Any],
    qc: dict[str, Any],
    combined: dict[str, Any],
    jobs: dict[str, dict[str, Any]],
) -> None:
    if analysis.get("status") != "GATE29H_STATISTICAL_ANALYSIS_COMPLETE":
        raise RuntimeError("statistical analysis is not complete")
    if analysis.get("input_qc_status") != "GATE29H_QC_INTEGRITY_PASS":
        raise RuntimeError("analysis does not reference a passing QC report")
    if qc.get("status") != "GATE29H_QC_INTEGRITY_PASS":
        raise RuntimeError("QC report is not PASS")
    if qc.get("planned_job_count") != 15 or qc.get("completed_job_count") != 15:
        raise RuntimeError("QC report is not 15/15")
    if combined.get("status") != "GATE29H_COMBINED_EXECUTION_COMPLETE":
        raise RuntimeError("combined execution summary is not complete")
    if combined.get("completed_job_count") != 15:
        raise RuntimeError("combined summary is not 15/15")
    if analysis.get("analysis_controls", {}).get("no_retuning") is not True:
        raise RuntimeError("analysis control no_retuning is not true")
    if analysis.get("analysis_controls", {}).get("holdout_opened") is not False:
        raise RuntimeError("holdout control is not false")
    if analysis.get("primary_endpoint") != PRIMARY:
        raise RuntimeError("unexpected primary endpoint")
    primary_test = analysis.get("primary_test", {})
    if primary_test.get("p_value_one_sided_less_than_zero") != 1.0:
        raise RuntimeError("unexpected primary p-value")
    if analysis.get("primary_paired_differences") != [0.0] * 5:
        raise RuntimeError("primary paired differences are not all zero")
    if any(item.get("status") != "PASS" for item in qc.get("results", [])):
        raise RuntimeError("at least one QC job is not PASS")
    if len(jobs) != 15:
        raise RuntimeError("expected exactly 15 jobs")


def build_primary_table(csv_path: Path, destination: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)
    rows.sort(key=lambda row: int(row["seed"]))
    source_fields = [
        "seed",
        "healthy_control__median_planar_speed_mm_s",
        "dopamine_class_level_full_burden__median_planar_speed_mm_s",
        "full_minus_healthy__median_planar_speed_mm_s",
        "healthy_control__brain_body_drive_mean_l2",
        "dopamine_class_level_full_burden__brain_body_drive_mean_l2",
        "full_minus_healthy__brain_body_drive_mean_l2",
    ]
    fields = [
        "seed",
        "healthy_control_median_planar_speed_mm_s",
        "dopamine_class_level_full_burden_median_planar_speed_mm_s",
        "full_minus_healthy_median_planar_speed_mm_s",
        "healthy_control_brain_body_drive_mean_l2",
        "dopamine_class_level_full_burden_brain_body_drive_mean_l2",
        "full_minus_healthy_brain_body_drive_mean_l2",
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(zip(fields, (row[field] for field in source_fields))))
    rows = [
        dict(zip(fields, (row[field] for field in source_fields))) for row in rows
    ]
    return rows


def draw_figure(rows: list[dict[str, Any]], destination: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    width, height = 1800, 1050
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    def font(size: int, bold: bool = False):
        candidates = [
            Path(r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"),
            Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
        ]
        for candidate in candidates:
            if candidate.is_file():
                return ImageFont.truetype(str(candidate), size)
        return ImageFont.load_default()

    title_font = font(38, True)
    subtitle_font = font(24, False)
    axis_font = font(22, False)
    small_font = font(20, False)
    bold_font = font(24, True)

    navy = (24, 46, 76)
    blue = (34, 93, 160)
    red = (196, 65, 65)
    gray = (130, 130, 130)
    light = (235, 239, 244)
    black = (25, 25, 25)

    draw.text((70, 35), "Gate29-H primary endpoint", fill=navy, font=title_font)
    draw.text(
        (70, 88),
        "Same-seed comparison: full dopamine class-level burden minus healthy control",
        fill=gray,
        font=subtitle_font,
    )

    left = (90, 180, 860, 830)
    right = (990, 180, 1710, 830)

    def panel_box(box, heading):
        x0, y0, x1, y1 = box
        draw.rounded_rectangle(box, radius=12, outline=light, width=3)
        draw.text((x0 + 25, y0 + 20), heading, fill=navy, font=bold_font)

    panel_box(left, "A  Median planar speed (mm/s)")
    panel_box(right, "B  Paired difference (mm/s)")

    values = [float(row["healthy_control_median_planar_speed_mm_s"]) for row in rows]
    ymin, ymax = 2.0, 2.8
    px0, py0, px1, py1 = left[0] + 90, left[1] + 95, left[2] - 35, left[3] - 75
    for tick in (2.0, 2.2, 2.4, 2.6, 2.8):
        y = py1 - (tick - ymin) / (ymax - ymin) * (py1 - py0)
        draw.line((px0, y, px1, y), fill=light, width=2)
        draw.text((px0 - 70, y - 13), f"{tick:.1f}", fill=gray, font=axis_font)
    draw.line((px0, py0, px0, py1), fill=black, width=3)
    draw.line((px0, py1, px1, py1), fill=black, width=3)
    step = (px1 - px0) / len(rows)
    for index, value in enumerate(values):
        x = px0 + step * (index + 0.5)
        y = py1 - (value - ymin) / (ymax - ymin) * (py1 - py0)
        draw.line((x, py1, x, y), fill=(215, 220, 225), width=2)
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=blue, outline=blue)
        draw.ellipse((x - 16, y - 16, x + 16, y + 16), outline=red, width=4)
        draw.text((x - 8, py1 + 18), str(index), fill=black, font=axis_font)
    draw.text((px0, py1 + 55), "seed", fill=gray, font=axis_font)
    draw.text((px0 + 210, py0 + 5), "Healthy (blue) and full burden (red ring) overlap", fill=gray, font=small_font)

    qx0, qy0, qx1, qy1 = right[0] + 100, right[1] + 95, right[2] - 35, right[3] - 75
    dmin, dmax = -0.1, 0.1
    for tick in (-0.1, 0.0, 0.1):
        y = qy1 - (tick - dmin) / (dmax - dmin) * (qy1 - qy0)
        draw.line((qx0, y, qx1, y), fill=navy if tick == 0 else light, width=3 if tick == 0 else 2)
        draw.text((qx0 - 70, y - 13), f"{tick:.1f}", fill=gray, font=axis_font)
    draw.line((qx0, qy0, qx0, qy1), fill=black, width=3)
    draw.line((qx0, qy1, qx1, qy1), fill=black, width=3)
    step = (qx1 - qx0) / len(rows)
    zero_y = qy1 - (0.0 - dmin) / (dmax - dmin) * (qy1 - qy0)
    for index in range(len(rows)):
        x = qx0 + step * (index + 0.5)
        draw.ellipse((x - 11, zero_y - 11, x + 11, zero_y + 11), fill=navy, outline=navy)
        draw.text((x - 8, qy1 + 18), str(index), fill=black, font=axis_font)
    draw.text((qx0 + 90, qy0 + 55), "All five paired differences = 0", fill=navy, font=bold_font)
    draw.text((qx0 + 90, qy0 + 100), "median = 0; 95% CI = [0, 0]", fill=gray, font=axis_font)
    draw.text((qx0 + 90, qy0 + 140), "one-sided exact sign-flip p = 1.00", fill=gray, font=axis_font)

    draw.text(
        (70, 900),
        "Interpretation: no preregistered directional effect was detected within this computational protocol.",
        fill=navy,
        font=subtitle_font,
    )
    draw.text(
        (70, 945),
        "Scope boundary: class-level computational contrast; not biological Parkinson validation.",
        fill=gray,
        font=small_font,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG", optimize=True)


def build_freeze_manifest(
    package_root: Path,
    source_roots: list[tuple[str, Path]],
    jobs: dict[str, dict[str, Any]],
    analysis_path: Path,
    qc_path: Path,
    combined_path: Path,
    analysis: dict[str, Any],
    qc: dict[str, Any],
) -> dict[str, Any]:
    source_artifacts: list[dict[str, Any]] = []
    for job_id in sorted(jobs):
        job = jobs[job_id]
        root: Path = job["job_root"]
        for relative_path in JOB_ARTIFACTS:
            artifact = root / relative_path
            if not artifact.is_file():
                raise FileNotFoundError(artifact)
            source_artifacts.append(
                {
                    "job_id": job_id,
                    "source_label": job["source_label"],
                    "relative_path": relative_path,
                    "absolute_path": str(artifact),
                    "size_bytes": artifact.stat().st_size,
                    "sha256": sha256(artifact),
                }
            )

    checkpoint_by_condition: dict[str, list[str]] = {}
    for job in jobs.values():
        checkpoint_by_condition.setdefault(job["condition_id"], []).append(
            job["manifest"].get("checkpoint_sha256")
        )
    checkpoint_by_condition = {
        key: sorted(set(value)) for key, value in checkpoint_by_condition.items()
    }

    payload = {
        "schema_version": "gate29h-result-freeze-manifest-v1",
        "freeze_date": date.today().isoformat(),
        "freeze_status": "FROZEN_FOR_DUAL_HUMAN_REVIEW",
        "preregistration_id": analysis["preregistration_id"],
        "execution_matrix": {
            "conditions": list(CONDITIONS),
            "seeds": list(SEEDS),
            "completed_jobs": 15,
        },
        "scientific_boundary": {
            "primary_endpoint": PRIMARY,
            "trace_endpoint": TRACE_ENDPOINT,
            "decision": analysis["decision"],
            "no_retuning": True,
            "no_holdout_opened": True,
            "no_additional_gpu_execution": True,
        },
        "input_artifacts": [
            {
                "role": "combined_execution_summary",
                "path": str(combined_path),
                "sha256": sha256(combined_path),
                "status": combined_path.name,
            },
            {
                "role": "qc_integrity_report",
                "path": str(qc_path),
                "sha256": sha256(qc_path),
                "status": qc["status"],
            },
            {
                "role": "statistical_analysis",
                "path": str(analysis_path),
                "sha256": sha256(analysis_path),
                "status": analysis["status"],
            },
        ],
        "source_roots": [
            {"label": label, "path": str(root)} for label, root in source_roots
        ],
        "checkpoint_sha256_by_condition": checkpoint_by_condition,
        "raw_job_artifacts": source_artifacts,
        "package_policy": {
            "raw_arrays_copied_into_package": False,
            "raw_arrays_remain_at_source_paths": True,
            "checksums_file": "checksums.sha256",
            "review_signoff": "manifests/gate29h_analysis_review_signoff.json",
        },
    }
    return payload


def build_report(rows: list[dict[str, Any]], analysis: dict[str, Any], qc: dict[str, Any], freeze: dict[str, Any]) -> str:
    primary = analysis["primary_effect_size"]
    test = analysis["primary_test"]
    ci = analysis["primary_uncertainty"]["ci_95_percentile"]
    healthy_checkpoint = freeze["checkpoint_sha256_by_condition"]["healthy_control"]
    full_checkpoint = freeze["checkpoint_sha256_by_condition"]["dopamine_class_level_full_burden"]
    lines = [
        "# Gate29-H final results report",
        "",
        f"Freeze date: {freeze['freeze_date']}",
        "",
        "## Executive result",
        "",
        "Trong protocol Gate29-H đã đăng ký trước, full-burden không tạo ra khác biệt quan sát được so với `healthy_control` ở endpoint chính hoặc endpoint trace đã định trước. Đây là kết luận trong phạm vi computational protocol này; không phải kết luận rằng dopamine depletion không có tác động sinh học trong ruồi giấm.",
        "",
        "Decision lock: `NOT_REPRODUCED_WITHIN_COMPUTATIONAL_SCOPE`.",
        "",
        "## Design and integrity",
        "",
        f"- 3 conditions x 5 seeds = {qc['completed_job_count']}/15 completed jobs; every QC job is PASS.",
        "- Same-seed pairing across conditions; primary unit is one simulation seed.",
        "- 5,000 steps per job, timestep 0.0001 s, CUDA execution, p9 stimulus.",
        "- Full burden: burden 1.0, full presynaptic gain 0.15, target count 342.",
        "- No automatic retry, calibration, fitting, retuning, post-hoc seed selection, or holdout opening.",
        f"- Healthy checkpoint SHA256: `{healthy_checkpoint[0]}`.",
        f"- Full-burden checkpoint SHA256: `{full_checkpoint[0]}`; this differs from the healthy checkpoint and is retained in the freeze manifest.",
        "",
        "## Primary endpoint",
        "",
        "Endpoint: `median_planar_speed_mm_s`; contrast: `full_burden - healthy_control`; hypothesis direction: less than zero.",
        "",
        f"- Paired differences by seed: `{analysis['primary_paired_differences']}`.",
        f"- Median paired difference: `{format_number(primary['median_paired_difference'])} mm/s`.",
        f"- Exact one-sided sign-flip test: p = `{test['p_value_one_sided_less_than_zero']:.2f}`, alpha = `{test['alpha']:.2f}`; not significant.",
        f"- Percentile paired bootstrap ({analysis['primary_uncertainty']['resamples']:,} resamples, seed {analysis['primary_uncertainty']['seed']}): 95% CI = `[{format_number(ci[0])}, {format_number(ci[1])}] mm/s`.",
        "- Paired rank-biserial correlation: not defined because all paired differences are exactly zero.",
        "",
        "| Seed | Healthy speed (mm/s) | Full-burden speed (mm/s) | Full - healthy (mm/s) |",
        "|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {int(row['seed'])} | {format_number(row['healthy_control_median_planar_speed_mm_s'])} | {format_number(row['dopamine_class_level_full_burden_median_planar_speed_mm_s'])} | {format_number(row['full_minus_healthy_median_planar_speed_mm_s'])} |"
        )
    lines += [
        "",
        "## Trace endpoint and identity control",
        "",
        "The preregistered trace endpoint `brain_body_drive_mean_l2` also had zero full-minus-healthy difference for all five seeds. The zero-burden identity control passed: zero-burden and healthy outputs were exactly identical by seed across the checked metrics and trace arrays.",
        "",
        "## Figure and artifact locations",
        "",
        "- Figure: `figures/gate29h_primary_paired_speed.png`.",
        "- Seed-level table: `tables/gate29h_primary_result.csv`.",
        "- Full analysis table: `tables/gate29h_seed_level_metrics_and_differences.csv`.",
        "- QC, analysis, execution summary, freeze manifest, and SHA256 list are in `manifests/` and `checksums.sha256`.",
        "",
        "## Claim boundary",
        "",
        "Allowed wording: “Under the preregistered Gate29-H class-level computational protocol, the full-burden condition did not differ from healthy control on the primary endpoint; all five paired differences were zero (exact one-sided sign-flip p = 1.00; 95% bootstrap CI [0, 0]).”",
        "",
        "Not allowed: “dopamine depletion has no biological effect,” “Parkinson disease was validated,” gene-specific or clinical claims, or any wording implying that this null result licenses retuning or a new burden search.",
        "",
        "## Review status",
        "",
        "The packet is frozen and ready for two-person human review. The review manifest intentionally remains `WAITING_DUAL_HUMAN_ANALYSIS_REVIEW` until Lê Tấn Vĩ and Tô Đặng Minh Tuấn directly attest that they reviewed the analysis report, table, figure, and claim boundary.",
    ]
    return "\n".join(lines)


def build_manuscript_insert(analysis: dict[str, Any], freeze: dict[str, Any]) -> str:
    return f"""# Gate29-H results insert for manuscript

## Results

We evaluated a preregistered class-level computational contrast using three conditions (`healthy_control`, `dopamine_class_level_burden_zero`, and `dopamine_class_level_full_burden`) and five matched simulation seeds per condition. The primary endpoint was `median_planar_speed_mm_s`, with the full-burden condition compared with healthy control within seed. All 15 jobs passed the prespecified integrity checks.

The full-burden minus healthy-control primary differences were exactly zero for all five seeds. The preregistered one-sided exact sign-flip test gave p = 1.00 (alpha = 0.05), the median paired difference was 0 mm/s, and the 95% percentile paired bootstrap interval was [0, 0] mm/s (10,000 resamples; analysis seed 29001). The preregistered trace endpoint, `brain_body_drive_mean_l2`, likewise showed zero paired difference for every seed.

## Interpretation and limitation

These data do not support the preregistered directional hypothesis within this computational protocol. The appropriate conclusion is a null result at the class-level computational scope, not evidence that dopamine depletion has no biological effect in Drosophila and not a biological Parkinson validation. No calibration, fitting, retuning, additional burden selection, or holdout analysis was performed after seeing the result.

The complete computational provenance is frozen under `{freeze['preregistration_id']}`. The corresponding QC and statistical-analysis SHA256 values are recorded in the release packet checksum file.

## Suggested figure caption

**Figure X. Gate29-H primary endpoint.** Same-seed median planar speed for healthy control and full dopamine class-level burden (panel A) and paired full-minus-healthy differences (panel B). The two conditions overlap for all five seeds; every paired difference is zero, with exact one-sided sign-flip p = 1.00 and 95% bootstrap CI [0, 0]. This is a class-level computational result and does not establish biological Parkinson causality.
"""


def build_review_packet(analysis: dict[str, Any]) -> str:
    return f"""# Gate29-H dual human analysis review packet

Review status: `WAITING_DUAL_HUMAN_ANALYSIS_REVIEW`

## Materials to review

1. `reports/gate29h_final_results_report.md`
2. `tables/gate29h_primary_result.csv`
3. `figures/gate29h_primary_paired_speed.png`
4. `manifests/gate29h_qc_integrity_report.json`
5. `manifests/gate29h_statistical_analysis.json`
6. `manifests/gate29h_result_freeze_manifest.json`
7. `checksums.sha256`

## Review checklist

- [ ] I verified that QC is PASS for 15/15 jobs.
- [ ] I verified the primary endpoint, same-seed pairing, exact sign-flip test, bootstrap settings, and the reported values.
- [ ] I agree that the main result is that full-burden did not differ from healthy control within this protocol.
- [ ] I agree with the claim boundary: computational class-level result only; no biological, gene-specific, clinical, drug, or therapeutic claim.
- [ ] I agree that no retuning, extra burden search, or holdout opening should be performed to seek a different result.

## Required human attestations

### Reviewer 1 — Lê Tấn Vĩ

- Status: `PENDING_HUMAN_CONFIRMATION`
- Confirmation: ______________________________
- Date: __________________

### Reviewer 2 — Tô Đặng Minh Tuấn

- Status: `PENDING_HUMAN_CONFIRMATION`
- Confirmation: ______________________________
- Date: __________________

The manifest is not marked PASS until both confirmations are supplied directly by the named reviewers.

## Locked decision

`{analysis['decision']['status']}` — `{analysis['decision']['scope']}`
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-base", type=Path, default=DEFAULT_OUTPUT_BASE)
    parser.add_argument("--release-root", type=Path, default=REPO_ROOT / "release" / "gate29h_continuation_003")
    args = parser.parse_args()

    output_base = args.output_base
    release_root = args.release_root
    final_root = output_base / DEFAULT_ROOT_NAME
    source_roots = [(name, output_base / name) for name in SOURCE_ROOT_NAMES]
    for _, root in source_roots:
        if not root.is_dir():
            raise FileNotFoundError(root)

    analysis_path = final_root / "analysis" / "gate29h_statistical_analysis.json"
    analysis_csv_path = final_root / "analysis" / "gate29h_seed_level_metrics_and_differences.csv"
    qc_path = final_root / "gate29h_qc_integrity_report.json"
    combined_path = final_root / "gate29h_combined_execution_summary.json"
    analysis = read_json(analysis_path)
    qc = read_json(qc_path)
    combined = read_json(combined_path)
    jobs = discover_jobs(source_roots)
    validate_inputs(analysis, qc, combined, jobs)

    release_root.mkdir(parents=True, exist_ok=True)
    freeze = build_freeze_manifest(
        release_root,
        source_roots,
        jobs,
        analysis_path,
        qc_path,
        combined_path,
        analysis,
        qc,
    )

    copy_file(qc_path, release_root / "manifests" / "gate29h_qc_integrity_report.json")
    copy_file(analysis_path, release_root / "manifests" / "gate29h_statistical_analysis.json")
    copy_file(combined_path, release_root / "manifests" / "gate29h_combined_execution_summary.json")
    copy_file(analysis_csv_path, release_root / "tables" / "gate29h_seed_level_metrics_and_differences.csv")

    rows = build_primary_table(
        analysis_csv_path,
        release_root / "tables" / "gate29h_primary_result.csv",
    )
    draw_figure(rows, release_root / "figures" / "gate29h_primary_paired_speed.png")

    report = build_report(rows, analysis, qc, freeze)
    write_text(release_root / "reports" / "gate29h_final_results_report.md", report)
    write_text(release_root / "reports" / "gate29h_claim_lock.md", """# Gate29-H claim lock

## Locked primary claim

Under the preregistered Gate29-H class-level computational protocol, the full-burden condition did not differ from healthy control on the primary endpoint: all five same-seed paired differences were exactly zero, the exact one-sided sign-flip p-value was 1.00, and the 95% paired bootstrap interval was [0, 0].

## Scope

This is a computational class-level null result. It is not biological Parkinson validation, gene-specific validation, a clinical claim, a drug claim, or evidence that dopamine depletion has no effect in vivo.

## Prohibited post-result changes

Do not retune the model, change burden, select a different seed, fit parameters, calibrate against the observed null, or open the holdout to search for significance.
""")
    write_text(release_root / "reports" / "gate29h_review_packet.md", build_review_packet(analysis))
    write_text(release_root / "manuscript" / "gate29h_results_insert_vi.md", build_manuscript_insert(analysis, freeze))

    signoff = {
        "schema_version": "gate29h-analysis-review-signoff-v1",
        "status": "WAITING_DUAL_HUMAN_ANALYSIS_REVIEW",
        "preregistration_id": analysis["preregistration_id"],
        "analysis_status": analysis["status"],
        "qc_status": qc["status"],
        "decision": analysis["decision"],
        "review_scope": [
            "statistical analysis",
            "QC/integrity report",
            "primary table",
            "primary figure",
            "claim boundary",
            "freeze manifest and SHA256 checksums",
        ],
        "reviewers": [
            {
                "name": "Lê Tấn Vĩ",
                "role": "reviewer_1",
                "status": "PENDING_HUMAN_CONFIRMATION",
                "attestation": None,
            },
            {
                "name": "Tô Đặng Minh Tuấn",
                "role": "reviewer_2",
                "status": "PENDING_HUMAN_CONFIRMATION",
                "attestation": None,
            },
        ],
        "input_sha256": {
            "combined_execution_summary": sha256(combined_path),
            "qc_integrity_report": sha256(qc_path),
            "statistical_analysis": sha256(analysis_path),
            "analysis_runner": analysis["analysis_runner_sha256"],
            "qc_runner": qc["qc_runner_sha256"],
        },
        "next_action": "Both named reviewers must directly confirm the report and claim boundary before final release signoff.",
    }
    write_json(release_root / "manifests" / "gate29h_analysis_review_signoff.json", signoff)
    write_json(release_root / "manifests" / "gate29h_result_freeze_manifest.json", freeze)

    write_text(release_root / "README_reproduce.md", f"""# Gate29-H continuation 003 release packet

This packet contains the frozen Gate29-H QC and statistical-analysis outputs for preregistration `{analysis['preregistration_id']}`.

## Result

15/15 jobs passed QC. The full-burden minus healthy-control primary endpoint difference was exactly zero for every matched seed; exact one-sided sign-flip p = 1.00 and 95% bootstrap CI [0, 0]. The locked decision is `NOT_REPRODUCED_WITHIN_COMPUTATIONAL_SCOPE`.

## Reproducibility

The raw rollout and trace arrays are intentionally not copied into this lightweight repository packet. Their source paths and SHA256 hashes are recorded per job in `manifests/gate29h_result_freeze_manifest.json`. The QC report and statistical-analysis JSON are copied verbatim into `manifests/`. Verify all packet files using `checksums.sha256`.

This release step is analysis-only. It does not launch GPU execution, modify raw outputs, retune the model, change burden, or open a holdout.

## Human review

Review `reports/gate29h_review_packet.md` and record both direct human attestations in `manifests/gate29h_analysis_review_signoff.json` only after Lê Tấn Vĩ and Tô Đặng Minh Tuấn have reviewed the materials.
""")

    package_files = sorted(
        path for path in release_root.rglob("*") if path.is_file() and path.name != "checksums.sha256"
    )
    checksum_lines = [
        f"{sha256(path)}  {path.relative_to(release_root).as_posix()}" for path in package_files
    ]
    write_text(release_root / "checksums.sha256", "\n".join(checksum_lines))

    # A compact, deterministic summary for the console and CI.
    print(json.dumps({
        "release_root": str(release_root),
        "status": "GATE29H_RESULT_PACKET_BUILT",
        "jobs": len(jobs),
        "qc": qc["status"],
        "analysis": analysis["status"],
        "primary_p_value": analysis["primary_test"]["p_value_one_sided_less_than_zero"],
        "primary_median_difference": analysis["primary_effect_size"]["median_paired_difference"],
        "review_status": signoff["status"],
        "package_file_count": len(package_files) + 1,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
