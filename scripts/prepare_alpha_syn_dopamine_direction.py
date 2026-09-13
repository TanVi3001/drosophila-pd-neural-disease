#!/usr/bin/env python3
"""Prepare Gate A/B artifacts for the alpha-synuclein/dopamine paper.

This is a preparation-only workflow. It converts the repository's existing
paper-review rows into an explicit endpoint registry, records a study-level
allocation plan, and writes an alignment report. It does not fit parameters,
modify model code, authorize a run, or launch GPU execution.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "research" / "paper_review" / "paper_analysis_vi.csv"
SOURCES = ROOT / "research" / "paper_review" / "selected_sources.csv"
DEFAULT_OUTPUT = ROOT / "research" / "alpha_syn_dopamine_preparation"


FIELDNAMES = [
    "endpoint_id",
    "source_id",
    "paper_id",
    "source_url",
    "source_role",
    "genotype",
    "driver",
    "sex",
    "age_days",
    "assay_id",
    "assay_description",
    "duration_s",
    "frame_rate_hz",
    "metadata_source",
    "metric_source",
    "metric_canonical",
    "unit",
    "center_value",
    "center_statistic",
    "spread_type",
    "spread_value",
    "sample_size_text",
    "sample_size_numeric",
    "sample_unit",
    "experimental_unit",
    "figure_table",
    "data_origin",
    "digitization_status",
    "assay_transfer",
    "assay_transfer_basis",
    "allocation",
    "source_risk",
    "reviewer_1",
    "reviewer_2_recorded",
    "review_date",
    "approval_status",
    "notes",
]


ROLE_BY_PAPER = {
    "riemensperger_2011_dopamine_deficiency": ("unit_test", "unit_test"),
    "pokrzywa_2017_alpha_syn_flytracker": ("calibration_candidate", "calibration_candidate"),
    "riemensperger_2013_alpha_synuclein_progression": ("generalization_candidate", "holdout_candidate"),
    "haywood_2004_parkin_alpha_synuclein_climbing": ("intervention_specificity", "holdout_candidate"),
    "aggarwal_2019_pd_locomotor_assay": ("assay_validation", "validation_only"),
    "dumitrescu_2023_parkin_rnai": ("regional_dopamine_constraint", "context_only"),
    "liessem_2026_walking_direction_dopamine": ("direction_prior", "prior_only"),
    "pugliese_2025_fly_cpg_preprint": ("motor_body_implementation", "implementation_only"),
    "neuromechfly_v2_2024": ("motor_body_implementation", "implementation_only"),
    "pozo_2022_pink1_serotonin": ("cross_disease_context", "context_only"),
    "hwang_2013_dj1_dlp": ("cross_disease_context", "context_only"),
    "godena_2014_lrrk2_microtubule": ("cross_disease_context", "context_only"),
}


# These values are metadata leads explicitly recorded in the supplied synthesis.
# They are not treated as approved targets until checked against the primary paper.
ASSAY_METADATA_LEADS = {
    "riemensperger_2011_dopamine_deficiency": ("900", "NOT_REPORTED"),
    "pokrzywa_2017_alpha_syn_flytracker": ("10", "30"),
    "pozo_2022_pink1_serotonin": ("180", "NOT_REPORTED"),
    "hwang_2013_dj1_dlp": ("4", "NOT_REPORTED"),
    "aggarwal_2019_pd_locomotor_assay": ("300", "NOT_REPORTED"),
}


# Source-audit overrides. Values are copied only when supported by a primary
# source, an already reviewed project artifact, or an explicitly recorded
# figure digitization. Missing numeric fields stay missing; no estimate is
# created from a bar height or from a sample-size range.
METADATA_OVERRIDES: dict[str, dict[str, str]] = {
    "riemensperger_speed_day5": {
        "source_id": "riemensperger_2011_dopamine_deficiency",
        "age_days": "2-5",
        "sex": "NOT_REPORTED",
        "duration_s": "900",
        "center_value": "7.8",
        "center_statistic": "median",
        "spread_type": "Q25_Q75_Q10_Q90_extremes_reported_non_numeric",
        "spread_value": "NOT_REPORTED",
        "sample_size_text": "13 individual flies",
        "sample_size_numeric": "13",
        "sample_unit": "fly",
        "experimental_unit": "fly",
        "metadata_source": "primary_source_PMC3021077_fulltext",
        "digitization_status": "SOURCE_TEXT_VERIFIED_CENTER_ONLY",
        "assay_transfer": "pending",
        "assay_transfer_basis": "same behavioral concept but median/open-arena transfer requires explicit adjudication",
        "notes": "Primary source reports median walking speed 7.8 mm/s for 5-day adult flies, 15-min open-arena recording, n=13 individual flies; plot reports quartiles/quantiles/extremes without numeric spread. Keep median separate from mean.",
    },
    "pokrzywa_alpha_speed_day1": {
        "center_value": "5.6",
        "center_statistic": "mean",
        "spread_type": "SE_not_numerically_reported",
        "spread_value": "NOT_REPORTED",
        "sample_unit": "independent_vial",
        "experimental_unit": "independent_vial",
        "metadata_source": "primary_source_PMC5581160_fulltext",
        "digitization_status": "SOURCE_TEXT_VERIFIED_CENTER_ONLY",
        "assay_transfer": "pending",
        "assay_transfer_basis": "same velocity unit but vial-level design and transfer to FlyGym remain unadjudicated",
        "notes": "Primary source states mean velocity falls from 5.6 mm/s at the early time point; 10-s recording at 30 fps, 10 female flies per vial, two sequences averaged, 3-10 independent vials. Exact n and numeric SE for this row are not reported.",
    },
    "pokrzywa_alpha_speed_day21": {
        "center_value": "2.5",
        "center_statistic": "mean",
        "spread_type": "SE_figure_digitized_approx",
        "spread_value": "0.12",
        "sample_unit": "independent_vial",
        "experimental_unit": "independent_vial",
        "metadata_source": "primary_source_PMC5581160_fulltext_plus_project_digitization",
        "digitization_status": "APPROXIMATE_FIGURE_DIGITIZATION_PENDING_SECOND_REVIEW",
        "assay_transfer": "pending",
        "assay_transfer_basis": "same velocity unit but approximate figure SE, non-unique vial count, and cross-assay transfer require review",
        "notes": "Mean 2.5 mm/s is reported in Results. Project digitization records an approximate SE of 0.12 mm/s from Figure 2A; it is not an exact table value. Paper reports 3-10 independent vials, so numeric n remains unavailable.",
    },
    "pokrzywa_control_speed_day1": {
        "center_value": "6.0",
        "center_statistic": "mean",
        "spread_type": "SE_not_numerically_reported",
        "spread_value": "NOT_REPORTED",
        "sample_unit": "independent_vial",
        "experimental_unit": "independent_vial",
        "metadata_source": "primary_source_PMC5581160_fulltext",
        "digitization_status": "SOURCE_TEXT_VERIFIED_CENTER_ONLY",
        "assay_transfer": "pending",
        "assay_transfer_basis": "control for same FlyTracker study; not a FlyGym baseline equivalence claim",
        "notes": "Primary source reports the control mean velocity at the early time point as 6 mm/s. Exact numeric SE and unique independent-vial count are not reported.",
    },
    "pokrzywa_control_speed_day21": {
        "center_value": "5.0",
        "center_statistic": "mean",
        "spread_type": "SE_figure_digitized_approx",
        "spread_value": "0.14",
        "sample_unit": "independent_vial",
        "experimental_unit": "independent_vial",
        "metadata_source": "primary_source_PMC5581160_fulltext_plus_project_digitization",
        "digitization_status": "APPROXIMATE_FIGURE_DIGITIZATION_PENDING_SECOND_REVIEW",
        "assay_transfer": "pending",
        "assay_transfer_basis": "control for same FlyTracker study; no direct FlyGym baseline equivalence",
        "notes": "Primary source reports the control mean velocity at day 21 as 5 mm/s. Project digitization records an approximate SE of 0.14 mm/s from Figure 2A; unique vial count remains unavailable.",
    },
    "dumitrescu_parkin_activity_day1": {
        "sex": "male",
        "duration_s": "604800",
        "center_value": "NOT_REPORTED",
        "center_statistic": "relative_reduction_percent",
        "spread_type": "SEM_not_numerically_reported",
        "spread_value": "NOT_REPORTED",
        "sample_size_numeric": "29",
        "sample_unit": "fly",
        "experimental_unit": "fly",
        "metadata_source": "primary_source_PMC9897283_Figure1_caption",
        "digitization_status": "SOURCE_TEXT_VERIFIED_DESIGN_ONLY",
        "assay_transfer": "not_comparable",
        "assay_transfer_basis": "7-day DAM average daily beam-break counts are not planar walking speed",
        "notes": "Primary caption reports average daily DAM counts per individual male fly during a 7-day monitoring period, n=29 for parkin-RNAi at 1 dpe; numeric center of the relative reduction is not text-reported. Do not convert DAM counts to speed.",
    },
    "dumitrescu_parkin_activity_day45": {
        "sex": "male",
        "duration_s": "604800",
        "center_value": "NOT_REPORTED",
        "center_statistic": "relative_reduction_percent",
        "spread_type": "SEM_not_numerically_reported",
        "spread_value": "NOT_REPORTED",
        "sample_size_numeric": "52",
        "sample_unit": "fly",
        "experimental_unit": "fly",
        "metadata_source": "primary_source_PMC9897283_Figure1_caption",
        "digitization_status": "SOURCE_TEXT_VERIFIED_DESIGN_ONLY",
        "assay_transfer": "not_comparable",
        "assay_transfer_basis": "7-day DAM average daily beam-break counts are not planar walking speed",
        "notes": "Primary caption reports average daily DAM counts per individual male fly during a 7-day monitoring period, n=52 for parkin-RNAi at 45 dpe; numeric center of the relative reduction is not text-reported. Do not convert DAM counts to speed.",
    },
    "pozo_pink1_distance_day28": {
        "sex": "male",
        "duration_s": "180",
        "center_value": "62.091",
        "center_statistic": "paper_reported_center",
        "spread_type": "IQR_with_min_max_ranges_reported",
        "spread_value": "61.288",
        "sample_unit": "fly",
        "experimental_unit": "fly",
        "metadata_source": "primary_source_PMC9105628_fulltext_Figure3B",
        "digitization_status": "SOURCE_TEXT_VERIFIED_CENTER_AND_SPREAD",
        "assay_transfer": "pending",
        "assay_transfer_basis": "open-field distance is a candidate distance holdout; transfer to FlyGym distance still needs explicit adjudication",
        "notes": "Primary source reports 28-day-old male Pink1B9 open-field distance 62.091 +/- 61.288 mm, with IQR and maximum/minimum ranges; n=21. Keep as distance/path-length only and do not convert to speed.",
    },
    "pozo_control_distance_day28": {
        "sex": "male",
        "duration_s": "180",
        "center_value": "323.326",
        "center_statistic": "paper_reported_center",
        "spread_type": "IQR_with_min_max_ranges_reported",
        "spread_value": "236.209",
        "sample_unit": "fly",
        "experimental_unit": "fly",
        "metadata_source": "primary_source_PMC9105628_fulltext_Figure3B",
        "digitization_status": "SOURCE_TEXT_VERIFIED_CENTER_AND_SPREAD",
        "assay_transfer": "pending",
        "assay_transfer_basis": "matched open-field control; no cross-assay equivalence inferred",
        "notes": "Primary source reports 28-day-old male w1118 control open-field distance 323.326 +/- 236.209 mm, with IQR and maximum/minimum ranges; n=20. Kept as context for a distance endpoint only.",
    },
    "pozo_pink1_activity_time_day28": {
        "sex": "male",
        "duration_s": "180",
        "center_value": "11.865",
        "center_statistic": "paper_reported_center",
        "spread_type": "IQR_with_min_max_ranges_reported",
        "spread_value": "12.914",
        "sample_unit": "fly",
        "experimental_unit": "fly",
        "metadata_source": "primary_source_PMC9105628_fulltext_Figure3C",
        "digitization_status": "SOURCE_TEXT_VERIFIED_CENTER_AND_SPREAD",
        "assay_transfer": "not_comparable",
        "assay_transfer_basis": "activity time is not walking speed and no approved pause-fraction adapter exists",
        "notes": "Primary source reports 28-day-old male Pink1B9 activity time 11.865 +/- 12.914 s, with IQR and maximum/minimum ranges; n=21. Keep separate from distance and speed.",
    },
    "pozo_control_activity_time_day28": {
        "sex": "male",
        "duration_s": "180",
        "center_value": "51.894",
        "center_statistic": "paper_reported_center",
        "spread_type": "IQR_with_min_max_ranges_reported",
        "spread_value": "32.409",
        "sample_unit": "fly",
        "experimental_unit": "fly",
        "metadata_source": "primary_source_PMC9105628_fulltext_Figure3C",
        "digitization_status": "SOURCE_TEXT_VERIFIED_CENTER_AND_SPREAD",
        "assay_transfer": "not_comparable",
        "assay_transfer_basis": "activity time is not walking speed and no approved pause-fraction adapter exists",
        "notes": "Primary source reports 28-day-old male w1118 control activity time 51.894 +/- 32.409 s, with IQR and maximum/minimum ranges; n=20. Kept separate from distance and speed.",
    },
    "hwang_dj1_climbing_day5": {
        "duration_s": "4",
        "center_value": "NOT_REPORTED",
        "center_statistic": "mean_climbing_score",
        "spread_type": "SE_not_numerically_reported",
        "spread_value": "NOT_REPORTED",
        "sample_unit": "test_group",
        "experimental_unit": "test_group",
        "metadata_source": "primary_source_PMC3616925_methods_Figure5E",
        "digitization_status": "SOURCE_TEXT_VERIFIED_DESIGN_ONLY",
        "assay_transfer": "validation_only",
        "assay_transfer_basis": "4-second negative-geotaxis score is not implemented as the primary planar-speed endpoint",
        "notes": "Primary methods report 10 male flies per test, ten trials per group, and at least ten independent transgenic-line repetitions; Figure 5E reports 5-day climbing mean +/- SE with n>=12. Exact plotted center and spread are not text-numeric. Validation-only.",
    },
    "godena_lrrk2_r1441c_climbing": {
        "center_value": "NOT_REPORTED",
        "center_statistic": "mean_climbing_score",
        "spread_type": "SEM_not_numerically_reported",
        "spread_value": "NOT_REPORTED",
        "sample_size_numeric": "43",
        "sample_unit": "fly",
        "experimental_unit": "fly",
        "metadata_source": "primary_source_PMC4208097_methods_Figure6C",
        "digitization_status": "SOURCE_TEXT_VERIFIED_DESIGN_ONLY",
        "assay_transfer": "validation_only",
        "assay_transfer_basis": "climbing assay is validation-only; observation window is not stated in the available source text",
        "notes": "Primary Figure 6C caption reports n=43 animals for R1441C vehicle/control arm; climbing assay was performed after a 5-day TSA exposure, but the scoring window is not stated in the available source text. Center/SEM remain non-numeric and validation-only.",
    },
    "godena_lrrk2_y1699c_climbing": {
        "center_value": "NOT_REPORTED",
        "center_statistic": "mean_climbing_score",
        "spread_type": "SEM_not_numerically_reported",
        "spread_value": "NOT_REPORTED",
        "sample_size_numeric": "59",
        "sample_unit": "fly",
        "experimental_unit": "fly",
        "metadata_source": "primary_source_PMC4208097_methods_Figure6C",
        "digitization_status": "SOURCE_TEXT_VERIFIED_DESIGN_ONLY",
        "assay_transfer": "validation_only",
        "assay_transfer_basis": "climbing assay is validation-only; observation window is not stated in the available source text",
        "notes": "Primary Figure 6C caption reports n=59 animals for Y1699C vehicle/control arm; climbing assay was performed after a 5-day TSA exposure, but the scoring window is not stated in the available source text. Center/SEM remain non-numeric and validation-only.",
    },
}


PLANNED_STUDY_ALLOCATIONS = [
    ("riemensperger_2011_dopamine_deficiency", "unit_test", "unit_test", "PRESENT_IN_REVIEW_TABLE"),
    ("pokrzywa_2017_alpha_syn_flytracker", "calibration_candidate", "calibration_candidate", "PRESENT_IN_REVIEW_TABLE"),
    ("riemensperger_2013_alpha_synuclein_progression", "generalization_candidate", "holdout_candidate", "PENDING_REGISTRY_ROWS"),
    ("haywood_2004_parkin_alpha_synuclein_climbing", "intervention_specificity", "holdout_candidate", "PENDING_REGISTRY_ROWS"),
    ("aggarwal_2019_pd_locomotor_assay", "assay_validation", "validation_only", "PENDING_REGISTRY_ROWS"),
    ("dumitrescu_2023_parkin_rnai", "regional_dopamine_constraint", "context_only", "PRESENT_IN_REVIEW_TABLE"),
    ("liessem_2026_walking_direction_dopamine", "direction_prior", "prior_only", "PENDING_REGISTRY_ROWS"),
    ("pugliese_2025_fly_cpg_preprint", "motor_body_implementation", "implementation_only", "PENDING_REGISTRY_ROWS"),
    ("neuromechfly_v2_2024", "motor_body_implementation", "implementation_only", "PENDING_REGISTRY_ROWS"),
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metric_canonical(metric: str) -> str:
    return {
        "walking_speed": "walking_speed_mm_s",
        "distance_traveled": "distance_traveled_mm",
        "activity_time": "activity_time_s",
        "climbing_ability": "climbing_score",
        "locomotor_activity_reduction": "DAM_activity_relative",
    }.get(metric, "NOT_MAPPED")


def source_role(paper_id: str) -> tuple[str, str]:
    return ROLE_BY_PAPER.get(paper_id, ("unclassified", "pending"))


def infer_sample_unit(sample_text: str) -> str:
    text = sample_text.lower().strip()
    if re.fullmatch(r"\d+ flies", text):
        return "fly"
    if "vial" in text:
        return "vial_or_grouped_flies"
    if "animal" in text:
        return "animal_or_unclear"
    return "NOT_REPORTED"


def infer_sample_size(sample_text: str) -> str:
    text = sample_text.lower().strip()
    match = re.fullmatch(r"(\d+) flies", text)
    return match.group(1) if match else "NOT_NUMERIC_UNAMBIGUOUS"


def transfer_status(raw: str) -> str:
    if raw.startswith("PENDING"):
        return "pending"
    if raw.startswith("VALIDATION_ONLY"):
        return "validation_only"
    if raw == "NOT_COMPARABLE" or raw.startswith("NOT_COMPARABLE"):
        return "not_comparable"
    if raw == "ALLOWED":
        return "allowed"
    return "not_yet_adjudicated"


def build_registry(
    analysis_rows: list[dict[str, str]],
    source_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    source_map = {row["source_id"]: row for row in source_rows}
    registry: list[dict[str, str]] = []
    for row in analysis_rows:
        paper_id = row["paper_id"]
        role, allocation = source_role(paper_id)
        source = source_map.get(paper_id, {})
        duration_s, frame_rate_hz = ASSAY_METADATA_LEADS.get(
            paper_id, ("NOT_REPORTED", "NOT_REPORTED")
        )
        sample_text = row.get("sample_size", "")
        uncertainty_type = row.get("uncertainty_type", "") or "NOT_REPORTED"
        uncertainty_value = row.get("uncertainty", "") or "NOT_REPORTED"
        if uncertainty_type in {"NOT_REPORTED_FOR_RELATIVE_DIFFERENCE", "reported plus/minus statistic unresolved"}:
            spread_type = "UNRESOLVED"
        else:
            spread_type = uncertainty_type
        status = "PENDING_HUMAN_REVIEW"
        if row.get("decision") in {"NOT_COMPARABLE", "VALIDATION_ONLY"}:
            status = "CONTEXT_OR_VALIDATION_ONLY"
        registry.append(
            {
                "endpoint_id": row["record_id"],
                "source_id": paper_id,
                "paper_id": paper_id,
                "source_url": source.get("source_url", "NOT_RECORDED"),
                "source_role": role,
                "genotype": row.get("genotype", "NOT_REPORTED"),
                "driver": "NOT_REPORTED",
                "sex": row.get("sex", "NOT_REPORTED"),
                "age_days": row.get("age_days", "NOT_REPORTED"),
                "assay_id": re.sub(r"[^a-z0-9]+", "_", row.get("assay", "unknown").lower()).strip("_"),
                "assay_description": row.get("assay", "NOT_REPORTED"),
                "duration_s": duration_s,
                "frame_rate_hz": frame_rate_hz,
                "metadata_source": "attached_synthesis_lead_primary_source_verification_pending",
                "metric_source": row.get("metric", "NOT_REPORTED"),
                "metric_canonical": metric_canonical(row.get("metric", "")),
                "unit": row.get("unit", "NOT_REPORTED"),
                "center_value": "NOT_REPORTED",
                "center_statistic": "NOT_REPORTED_OR_REQUIRES_SOURCE_CHECK",
                "spread_type": spread_type,
                "spread_value": uncertainty_value,
                "sample_size_text": sample_text or "NOT_REPORTED",
                "sample_size_numeric": infer_sample_size(sample_text),
                "sample_unit": infer_sample_unit(sample_text),
                "experimental_unit": infer_sample_unit(sample_text),
                "figure_table": row.get("figure_table", "NOT_REPORTED"),
                "data_origin": "existing_repository_paper_review_audit",
                "digitization_status": "NOT_DIGITIZED_OR_NOT_FINAL",
                "assay_transfer": transfer_status(row.get("flygym_transfer_status", "")),
                "assay_transfer_basis": "PENDING_SOURCE_AND_REVIEW_ADJUDICATION",
                "allocation": allocation,
                "source_risk": "SEE_SOURCE_REGISTRY",
                "reviewer_1": "PENDING_HUMAN_REVIEW",
                "reviewer_2_recorded": row.get("reviewer_2", "NOT_RECORDED"),
                "review_date": row.get("review_date", "NOT_RECORDED"),
                "approval_status": status,
                "notes": row.get("notes_vi", "") or row.get("analysis_vi", "") or "Preserved without conversion; requires source-level review.",
            }
        )
    for item in registry:
        override = METADATA_OVERRIDES.get(item["endpoint_id"], {})
        item.update(override)
        # A source-metadata refresh invalidates the old reviewer/date pair for
        # these rows. Keep the old review in provenance notes, but require a
        # new dual-human confirmation before any allocation is activated.
        if override:
            item["reviewer_1"] = "PENDING_RECONFIRMATION"
            item["reviewer_2_recorded"] = "PENDING_RECONFIRMATION"
            item["review_date"] = "NOT_RECORDED_FOR_UPDATED_METADATA"
    return registry


def build_split_manifest(registry: list[dict[str, str]]) -> dict[str, Any]:
    present = {row["source_id"] for row in registry}
    return {
        "schema_version": "alpha-syn-dopamine-study-split-v1",
        "status": "PREPARED_PENDING_DUAL_HUMAN_REVIEW",
        "preparation_only": True,
        "gpu_execution_authorized": False,
        "parameter_fitting_authorized": False,
        "question": "Can an uncertainty-aware connectome-constrained latent alpha-synuclein/dopamine model explain age trajectory and generalize across driver, assay, and laboratory?",
        "paper_scope": "alpha-synuclein -> dopamine circuit -> locomotion",
        "allocation_rule": "one study has one role; no endpoint/cohort may be used for both fitting and held-out evaluation",
        "planned_allocations": [
            {
                "source_id": source_id,
                "source_role": role,
                "allocation": allocation,
                "registry_status": registry_status,
                "present_in_registry": source_id in present,
                "fit_allowed_now": False,
                "review_status": "PENDING_HUMAN_REVIEW",
            }
            for source_id, role, allocation, registry_status in PLANNED_STUDY_ALLOCATIONS
        ],
        "required_before_lock": [
            "exact endpoint center/spread/unit and sample unit where applicable",
            "source-level reviewer and real review date",
            "study-level split reviewed by both reviewers",
            "assay transfer decision recorded per endpoint",
            "simple baseline set and success metrics preregistered",
        ],
        "prohibited": [
            "fit on a study and later call it holdout",
            "convert median to mean or SE/SEM to another spread type",
            "convert distance, climbing, DAM activity, or activity time into speed without an approved assay rule",
            "launch GPU execution before allocation and analysis plan are locked",
        ],
    }


def build_report(registry: list[dict[str, str]], split_manifest: dict[str, Any]) -> str:
    pending = sum(row["approval_status"] == "PENDING_HUMAN_REVIEW" for row in registry)
    validation_only = sum(row["approval_status"] == "CONTEXT_OR_VALIDATION_ONLY" for row in registry)
    calibration_candidates = sorted({row["source_id"] for row in registry if row["allocation"] == "calibration_candidate"})
    missing_center = [row["endpoint_id"] for row in registry if row["center_value"] == "NOT_REPORTED"]
    missing_spread = [row["endpoint_id"] for row in registry if row["spread_value"] in {"NOT_REPORTED", ""}]
    missing_duration = [row["endpoint_id"] for row in registry if row["duration_s"] == "NOT_REPORTED"]
    missing_experimental_unit = [row["endpoint_id"] for row in registry if row["experimental_unit"] in {"NOT_REPORTED", ""}]
    lines = [
        "# Alpha-synuclein/dopamine direction — Gate A/B preparation report",
        "",
        f"Preparation date: {date.today().isoformat()}",
        "Status: `PREPARATION_ONLY_PENDING_DUAL_HUMAN_REVIEW`",
        "",
        "## Interpretation of the synthesis document",
        "",
        "The attached synthesis is a strategic research direction, not a GPU execution authorization. Its highest-ranked first paper is an alpha-synuclein/dopamine locomotion study; PINK1–serotonin is a later flagship; generic multi-gene scalar burden is explicitly rejected.",
        "",
        "The current Gate29-H null result is retained as a class-level computational result and failure/identifiability evidence. It is not silently promoted into an alpha-synuclein biological claim and it does not authorize retuning the completed protocol.",
        "",
        "## Current Gate A/B findings",
        "",
        f"- Existing paper-review rows imported without changing source statistics: `{len(registry)}`.",
        f"- Rows pending human/source review: `{pending}`; context or validation-only rows: `{validation_only}`.",
        f"- Current calibration candidate paper: `{', '.join(calibration_candidates) or 'none'}`; it is not approved by this preparation step.",
        f"- Rows with unresolved or missing spread metadata: `{len(missing_spread)}`.",
        f"- Rows with unresolved or missing center metadata: `{len(missing_center)}`.",
        f"- Rows with unrecorded assay duration: `{len(missing_duration)}`.",
        f"- Rows with unrecorded experimental unit: `{len(missing_experimental_unit)}`.",
        "- `walking_speed` is kept distinct from the simulation's `mean_planar_speed_mm_s`/`median_planar_speed_mm_s`; no automatic equivalence is asserted.",
        "- Distance, climbing, DAM activity, and activity time remain separate endpoint families; no conversion to speed is performed.",
        "",
        "## Next gate sequence",
        "",
        "1. Complete source-level endpoint records for the current registry and add planned study rows only when their source data are present.",
        "2. Resolve numeric center, spread type/value, duration, assay window, and experimental unit; preserve unresolved values as pending.",
        "3. Review and lock the study-level allocation before any fitting: calibration candidate, unit test, generalization, intervention holdout, validation, prior, or implementation-only.",
        "4. Define simple baselines, uncertainty, ablation, sensitivity, and leave-one-study-out metrics.",
        "5. Only after dual review and a separate execution authorization, implement the alpha-synuclein age-state/dopamine module and its assay adapter.",
        "",
        "## Exit rule",
        "",
        "This preparation package does not launch GPU execution, change Gate29-H outputs, fit parameters, open a holdout, or select a result by significance. The split manifest must move from `PREPARED_PENDING_DUAL_HUMAN_REVIEW` to a reviewed lock before the next scientific run.",
        "",
        "## Artifacts",
        "",
        "- `literature_endpoint_registry_v2.csv`: explicit endpoint records with unresolved fields preserved.",
        "- `alpha_syn_dopamine_study_split_manifest_v1.json`: proposed study-level allocation, not yet locked.",
        "- `alpha_syn_dopamine_direction_review_vi.md`: strategy interpretation and next gates.",
    ]
    return "\n".join(lines)


def build_direction_doc(split_manifest: dict[str, Any]) -> str:
    return """# Đánh giá định hướng Parkinson in silico và quyết định triển khai

## Phân biệt tài liệu định hướng với lệnh thực thi

File tổng hợp trong `Downloads` là tài liệu chiến lược. Nó xếp hạng hướng nghiên cứu, nêu điều kiện bằng chứng và thứ tự các gate; nó không phải execution authorization, không thay thế preregistration, không cấp quyền chạy GPU và không cho phép tự fit hoặc retune.

Yêu cầu hiện tại của nhóm là dùng tài liệu đó để chọn bước tiếp theo cho project. Vì vậy, bước được triển khai ở đây chỉ là chuẩn bị Gate A/B: chuẩn hóa endpoint registry, giữ nguyên các trường chưa đủ bằng chứng ở trạng thái pending, và dựng study-level split để review trước khi fit.

## Quyết định chiến lược được áp dụng

- Paper đầu tiên: `alpha-synuclein -> dopamine circuit -> locomotion`.
- PINK1–serotonin: để ở flagship tiếp theo, sau khi paper alpha-synuclein ổn định.
- Parkin/JNK, DJ-1/stress và LRRK2 axonal transport: module/dự án sau, không trộn vào paper đầu tiên.
- Generic multi-gene scalar burden: không dùng làm kiến trúc mục tiêu.
- Claim cao nhất hiện tại: uncertainty-aware, connectome-constrained computational phenotype comparison; không gọi là biological Parkinson model hay thay thế wet-lab.

## Quan hệ với Gate29-H

Gate29-H đã hoàn thành 15/15, QC PASS và cho kết quả null trong class-level computational protocol. Kết quả này được giữ nguyên trong release packet. Nó không được chuyển thành alpha-synuclein evidence, không được dùng để retune burden, và không mở lại holdout.

## Gate A/B đang triển khai

1. Tách `walking_speed` của paper khỏi `mean_planar_speed_mm_s` và `median_planar_speed_mm_s` của simulator.
2. Giữ riêng distance, climbing, DAM activity và activity time; không suy ra speed khi chưa có assay-transfer rule.
3. Ghi duration, frame rate, assay window, statistic, spread, sample unit và provenance cho từng endpoint.
4. Khóa allocation theo study trước fitting; một study chỉ có một role.
5. Chuẩn bị baselines, leave-one-study-out, uncertainty, ablation, sensitivity và identifiability criteria.

## Trạng thái

`alpha_syn_dopamine_study_split_manifest_v1.json` đang ở trạng thái `PREPARED_PENDING_DUAL_HUMAN_REVIEW`. Chưa có fitting, chưa có GPU execution authorization và chưa có model change nào được coi là scientific result.
"""


def build_review_packet() -> str:
    return """# Alpha-synuclein/dopamine direction review packet

Status: `WAITING_DUAL_HUMAN_DIRECTION_REVIEW`

## Materials

- `literature_endpoint_registry_v2.csv`
- `alpha_syn_dopamine_study_split_manifest_v1.json`
- `alpha_syn_dopamine_direction_review_vi.md`
- `alpha_syn_dopamine_gate_a_b_preparation_report.md`
- `checksums.sha256`

## Checklist for both reviewers

- [ ] The first-paper scope is alpha-synuclein -> dopamine circuit -> locomotion.
- [ ] PINK1–serotonin is deferred; generic multi-gene scalar burden is excluded.
- [ ] `walking_speed`, `mean_planar_speed_mm_s`, and `median_planar_speed_mm_s` are not silently treated as identical.
- [ ] Distance, activity time, climbing, and DAM activity are kept as separate endpoint families.
- [ ] Missing center/spread/unit/duration metadata remains pending rather than being imputed.
- [ ] Study allocation is reviewed before any fitting and no study is reused as both fit and holdout.
- [ ] No GPU execution, fitting, retuning, or holdout opening is authorized by this packet.

## Required attestations

### Reviewer 1 — Lê Tấn Vĩ

- Confirmation: ______________________________
- Date: __________________

### Reviewer 2 — Tô Đặng Minh Tuấn

- Confirmation: ______________________________
- Date: __________________

After both direct confirmations, update the signoff manifest. Until then, this is a preparation draft and no scientific run may start from it.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not INPUT.is_file() or not SOURCES.is_file():
        raise FileNotFoundError("paper review inputs are missing")

    analysis_rows = read_csv(INPUT)
    source_rows = read_csv(SOURCES)
    registry = build_registry(analysis_rows, source_rows)
    split_manifest = build_split_manifest(registry)
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "literature_endpoint_registry_v2.csv", registry)
    write_json(args.output / "alpha_syn_dopamine_study_split_manifest_v1.json", split_manifest)
    write_text(args.output / "alpha_syn_dopamine_direction_review_vi.md", build_direction_doc(split_manifest))
    write_text(args.output / "alpha_syn_dopamine_gate_a_b_preparation_report.md", build_report(registry, split_manifest))
    write_text(args.output / "alpha_syn_dopamine_review_packet.md", build_review_packet())
    write_json(
        args.output / "alpha_syn_dopamine_review_signoff.json",
        {
            "schema_version": "alpha-syn-dopamine-direction-review-signoff-v1",
            "status": "WAITING_DUAL_HUMAN_DIRECTION_REVIEW",
            "scope": "Gate A/B preparation, endpoint registry, and study-level allocation",
            "gpu_execution_authorized": False,
            "parameter_fitting_authorized": False,
            "holdout_opened": False,
            "reviewers": [
                {"name": "Lê Tấn Vĩ", "role": "reviewer_1", "status": "PENDING_HUMAN_CONFIRMATION", "attestation": None},
                {"name": "Tô Đặng Minh Tuấn", "role": "reviewer_2", "status": "PENDING_HUMAN_CONFIRMATION", "attestation": None},
            ],
            "next_action": "Both reviewers directly confirm the direction, registry, and split before any fitting or GPU authorization.",
        },
    )
    write_json(
        args.output / "alpha_syn_dopamine_preparation_manifest.json",
        {
            "schema_version": "alpha-syn-dopamine-preparation-manifest-v1",
            "status": "PREPARATION_ONLY_PENDING_DUAL_HUMAN_REVIEW",
            "input_paper_analysis": str(INPUT),
            "input_paper_analysis_sha256": sha256(INPUT),
            "input_selected_sources": str(SOURCES),
            "input_selected_sources_sha256": sha256(SOURCES),
            "output_root": str(args.output),
            "registry_rows": len(registry),
            "study_allocations": len(split_manifest["planned_allocations"]),
            "review_status": "WAITING_DUAL_HUMAN_DIRECTION_REVIEW",
            "checksums_file": "checksums.sha256",
            "gpu_execution_authorized": False,
            "parameter_fitting_authorized": False,
            "holdout_opened": False,
            "retuning_performed": False,
            "next_required_review": "dual human review of endpoint registry and study split",
        },
    )
    artifact_files = sorted(
        path for path in args.output.rglob("*") if path.is_file() and path.name != "checksums.sha256"
    )
    checksum_lines = [
        f"{sha256(path)}  {path.relative_to(args.output).as_posix()}" for path in artifact_files
    ]
    write_text(args.output / "checksums.sha256", "\n".join(checksum_lines))
    print(json.dumps({
        "status": "ALPHA_SYN_DOPAMINE_PREPARATION_BUILT",
        "output": str(args.output),
        "registry_rows": len(registry),
        "study_allocations": len(split_manifest["planned_allocations"]),
        "gpu_execution_authorized": False,
        "split_status": split_manifest["status"],
        "checksum_files": len(artifact_files) + 1,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
