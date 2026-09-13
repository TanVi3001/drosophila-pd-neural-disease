#!/usr/bin/env python3
"""Freeze the alpha-synuclein/dopamine preregistration without execution.

The preregistration is a versioned design artifact.  It is deliberately
separate from dual-human review signoff and from scientific execution
authorization.  This script never starts a simulator, touches a GPU, fits a
parameter, or opens a holdout.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "research" / "alpha_syn_dopamine_preparation"
REGISTRY = PREP / "literature_endpoint_registry_v2.csv"
SPLIT = PREP / "alpha_syn_dopamine_study_split_manifest_v1.json"
PREREG_MD = PREP / "alpha_syn_dopamine_preregistration_v1.md"
PREREG_JSON = PREP / "alpha_syn_dopamine_preregistration_v1.json"
PREREG_SHA = PREP / "alpha_syn_dopamine_preregistration_v1.sha256"
REVIEW_SIGNOFF = PREP / "alpha_syn_dopamine_updated_registry_prereg_review_signoff_v1.json"
EXEC_AUTH = PREP / "alpha_syn_dopamine_execution_authorization_v1.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_registry() -> list[dict[str, str]]:
    with REGISTRY.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    rows = read_registry()
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    registry_hash = sha256(REGISTRY)
    split_hash_before = sha256(SPLIT)
    missing_center = [row["endpoint_id"] for row in rows if row["center_value"] in {"", "NOT_REPORTED"}]
    missing_spread = [row["endpoint_id"] for row in rows if row["spread_value"] in {"", "NOT_REPORTED"}]
    missing_duration = [row["endpoint_id"] for row in rows if row["duration_s"] in {"", "NOT_REPORTED"}]
    pending_transfer = [row["endpoint_id"] for row in rows if row["assay_transfer"] not in {"allowed", "approved"}]
    pending_review = [row["endpoint_id"] for row in rows if row["approval_status"] != "APPROVED"]

    prereg = {
        "schema_version": "alpha-syn-dopamine-preregistration-v1-final",
        "preregistration_id": "ALPHA_SYN_DOPAMINE_LOCOMOTION_V1",
        "version": "v1",
        "status": "FINAL_PREREGISTRATION_PENDING_DUAL_HUMAN_REVIEW",
        "execution_authorization_required": True,
        "gpu_execution_authorized": False,
        "parameter_fitting_authorized": False,
        "holdout_opened": False,
        "created_at": date.today().isoformat(),
        "frozen_artifacts": {
            "endpoint_registry": REGISTRY.name,
            "endpoint_registry_sha256": registry_hash,
            "study_split_manifest": SPLIT.name,
            "study_split_manifest_sha256_at_freeze": split_hash_before,
            "preregistration_hash_sidecar": PREREG_SHA.name,
        },
        "research_question": (
            "Can an uncertainty-aware, connectome-constrained latent alpha-synuclein/dopamine "
            "model explain age-related locomotor progression and generalize across study, "
            "assay, driver, and laboratory domains better than simpler baselines?"
        ),
        "paper_scope": "alpha-synuclein -> dopamine circuit -> locomotion",
        "claim_boundary": {
            "allowed": [
                "uncertainty-aware computational phenotype comparison",
                "connectome-constrained sensitivity and prediction under the declared protocol",
                "explicit comparison of functional dopamine deficiency and structural-loss comparator",
            ],
            "not_allowed": [
                "biological causality from simulation output alone",
                "gene-specific molecular mapping without a reviewed source-backed mapping",
                "clinical validation, drug efficacy, or replacement of live-fly experiments",
                "post-hoc retuning, burden search, or holdout selection",
            ],
        },
        "study_split": {
            "manifest": SPLIT.name,
            "allocation_rule": "one study has one role; no endpoint/cohort may be used for both fitting and held-out evaluation",
            "status_at_freeze": split["status"],
            "planned_allocations": split.get("planned_allocations", []),
            "holdout_policy": "A holdout is not opened until its registry rows, assay-transfer rule, and reviewer decision are present.",
        },
        "model_comparison": [
            "no-effect baseline",
            "global action-attenuation baseline",
            "connectome-only model without disease neuromodulation",
            "functional dopamine-deficiency model with alpha-synuclein age state",
            "structural-loss comparator kept distinct from functional deficiency",
        ],
        "model_contract": {
            "functional_state": "presynaptic/postsynaptic dopamine-related gain or circuit-level functional perturbation",
            "structural_state": "neuron_survival; never treated as a synonym for dopamine deficiency",
            "age_state": "predeclared burden curve with interpolation only between declared anchor points",
            "mapping": "explicit neuron/edge IDs only; no positional tensor fallback",
            "current_implementation_boundary": "generic disease-layer contract is audited; alpha-synuclein gene-specific mapping is not claimed",
        },
        "endpoint_policy": {
            "primary_metric_family": "walking_speed_mm_s when assay transfer is approved",
            "separate_metric_families": [
                "walking_speed_mm_s",
                "distance_traveled_mm",
                "activity_time_s",
                "DAM_activity_relative",
                "climbing_score",
            ],
            "center_and_spread": "Preserve reported statistic and spread type; median is not mean and SEM/SE/IQR/range are not interchangeable.",
            "missing_metadata": "NOT_REPORTED remains missing; no imputation from bar height, ranges, or sample-size bounds.",
            "assay_transfer": "Each transfer is endpoint-specific; pending or not_comparable rows cannot enter fitting or holdout evaluation.",
            "experimental_unit": "Use the study's analysis unit; do not multiply flies by vials or repeated observations.",
        },
        "registry_completeness_at_freeze": {
            "rows": len(rows),
            "center_filled": len(rows) - len(missing_center),
            "spread_filled": len(rows) - len(missing_spread),
            "duration_filled": len(rows) - len(missing_duration),
            "experimental_unit_filled": sum(row["experimental_unit"] not in {"", "NOT_REPORTED"} for row in rows),
            "assay_transfer_pending": pending_transfer,
            "source_review_pending": pending_review,
            "missing_center": missing_center,
            "missing_spread": missing_spread,
            "missing_duration": missing_duration,
        },
        "estimand_and_evaluation": {
            "primary_estimand": "held-out study-level prediction of control-relative locomotor phenotype",
            "primary_evaluation": "leave-one-study-out absolute error on a predeclared standardized effect when source metadata and assay transfer support it",
            "secondary_evaluations": [
                "predictive interval coverage when the source spread supports it",
                "held-out log predictive density when supported",
                "age-trajectory error",
                "intervention-rank agreement",
                "phenotype-profile similarity",
                "failure cases and identifiability limits",
            ],
            "uncertainty": "Use reported uncertainty only; retain approximate digitization labels and do not convert spread types.",
        },
        "analysis_controls": {
            "study_level_split_locked_before_fitting": True,
            "seeds": "Declared per runner authorization; no unregistered seed addition.",
            "no_posthoc_endpoint_selection": True,
            "no_calibration_on_holdout": True,
            "no_automatic_retry": True,
            "no_calibration_fitting_retuning_before_authorization": True,
            "sensitivity_and_failure_analysis_required": True,
        },
        "review_gate": {
            "signoff_file": REVIEW_SIGNOFF.name,
            "status": "PENDING_DUAL_HUMAN_UPDATED_REGISTRY_AND_PREREG_REVIEW",
            "required": [
                "Reviewer 1 direct attestation of updated registry and preregistration v1",
                "Reviewer 2 direct attestation of updated registry and preregistration v1",
                "Explicit confirmation of claim boundary and unresolved metadata policy",
            ],
        },
        "execution_gate": {
            "authorization_file": EXEC_AUTH.name,
            "status": "WAITING_EXPLICIT_HUMAN_EXECUTION_AUTHORIZATION",
            "gpu_execution_authorized": False,
            "required_before_gpu": [
                "dual-human review signoff complete",
                "code/model audit PASS or explicit documented implementation boundary",
                "runner audit PASS with exact job matrix and hashes",
                "separate explicit authorization from both reviewers",
            ],
        },
    }

    md = f"""# Alpha-synuclein/dopamine locomotion preregistration v1 — FINAL FROZEN DESIGN

Status: `FINAL_PREREGISTRATION_PENDING_DUAL_HUMAN_REVIEW`
Execution: `NOT AUTHORIZED` — no fitting, holdout opening, or GPU execution is permitted by this file.

## Research question

Can an uncertainty-aware, connectome-constrained latent alpha-synuclein/dopamine model explain age-related locomotor progression and generalize across study, assay, driver, and laboratory domains better than simpler baselines?

## Scope and claim boundary

The first paper is limited to **alpha-synuclein → dopamine circuit → locomotion**. The output is an uncertainty-aware computational phenotype comparison. It is not a claim of biological causality, a gene-specific molecular mapping, clinical validation, drug efficacy, or replacement for live-fly experiments.

## Frozen artifacts

- Endpoint registry: `{REGISTRY.name}`
- Endpoint registry SHA-256: `{registry_hash}`
- Study split: `{SPLIT.name}`
- Study split SHA-256 at freeze: `{split_hash_before}`
- This document SHA-256: recorded in `{PREREG_SHA.name}` after writing

## Registry and split policy

Each study has one role. No endpoint or cohort may be used for both fitting and held-out evaluation. The current split remains `{split["status"]}`; rows with unresolved source metadata or assay transfer remain ineligible for fitting/holdout until reviewed. `NOT_REPORTED` is preserved as missing; no value is imputed from a plot, range, or sample-size bound.

The registry contains `{len(rows)}` rows. At freeze, center is recorded for `{len(rows) - len(missing_center)}`, spread for `{len(rows) - len(missing_spread)}`, duration for `{len(rows) - len(missing_duration)}`, and experimental unit for `{sum(row["experimental_unit"] not in {"", "NOT_REPORTED"} for row in rows)}` rows. Pending transfer and source-review decisions are not silently promoted.

## Model contract

1. Functional dopamine state and structural neuron-loss state are separate latent variables.
2. Age dependence uses only the declared burden curve and deterministic interpolation between declared anchors.
3. Perturbation uses explicit neuron/edge identifiers; positional tensor fallback is prohibited.
4. The current code audit may establish a generic disease-layer contract, but it does not create a gene-specific alpha-synuclein mapping where none is source-supported.

## Preregistered comparison and evaluation

The comparison set is: no-effect baseline; global action-attenuation baseline; connectome-only model without disease neuromodulation; functional dopamine-deficiency model with alpha-synuclein age state; and a structurally distinct cell-loss comparator.

The primary estimand is held-out study-level prediction of a control-relative locomotor phenotype. The primary evaluation is leave-one-study-out absolute error on a predeclared standardized effect, only for endpoints whose source metadata and assay-transfer decision support that operation. Secondary outputs are predictive-interval coverage, held-out log predictive density, age-trajectory error, intervention-rank agreement, phenotype-profile similarity, and failure cases when supported.

Walking speed, distance, activity time, DAM activity, and climbing remain separate metric families. Median/mean and IQR/SE/SEM/range are not interchangeable. No assay transfer is allowed without an endpoint-specific rule and reviewer decision.

## Review and execution gates

This frozen design is awaiting two direct human attestations in `{REVIEW_SIGNOFF.name}`. Review is not GPU authorization. After review, a separate runner audit and execution authorization must name the exact code commit, configuration/checkpoint hashes, job matrix, seeds, and this preregistration hash. Until that authorization is explicitly granted, scientific GPU execution remains forbidden.
"""

    PREREG_JSON.write_text(json.dumps(prereg, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    PREREG_MD.write_text(md, encoding="utf-8")
    prereg_hash = sha256(PREREG_MD)
    PREREG_SHA.write_text(f"{prereg_hash}  {PREREG_MD.name}\n", encoding="utf-8")

    review = json.loads(REVIEW_SIGNOFF.read_text(encoding="utf-8"))
    review["preregistration"] = PREREG_MD.name
    review["preregistration_sha256"] = prereg_hash
    review["status"] = "PENDING_DUAL_HUMAN_UPDATED_REGISTRY_AND_PREREG_REVIEW"
    review["gpu_execution_authorized"] = False
    review["parameter_fitting_authorized"] = False
    write_json(REVIEW_SIGNOFF, review)

    auth = json.loads(EXEC_AUTH.read_text(encoding="utf-8"))
    auth["preregistration_sha256"] = prereg_hash
    auth["registry_sha256"] = registry_hash
    auth["authorized"] = False
    auth["authorized_jobs"] = 0
    auth["gpu_execution_authorized"] = False
    auth["simulation_execution_authorized"] = False
    auth["status"] = "WAITING_EXPLICIT_HUMAN_EXECUTION_AUTHORIZATION"
    auth["required_before_authorization"] = [
        "dual human review signoff complete for updated registry and final preregistration",
        "alpha-synuclein/dopamine code and model audit complete",
        "CPU synthetic/unit tests pass",
        "runner audit complete with exact job matrix, config, checkpoint, and code hashes",
        "explicit authorization from both human reviewers",
    ]
    write_json(EXEC_AUTH, auth)

    prereg["preregistration_sha256"] = prereg_hash
    write_json(PREREG_JSON, prereg)
    print(json.dumps({"preregistration_sha256": prereg_hash, "registry_sha256": registry_hash, "gpu_execution_authorized": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
