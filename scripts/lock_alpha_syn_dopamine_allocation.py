#!/usr/bin/env python3
"""Lock the reviewed study allocation and write the alpha-syn/dopamine prereg draft.

This workflow requires a completed dual-human direction review. It creates a
design/preregistration artifact and a separate execution-authorization placeholder;
it never authorizes or launches GPU execution.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "research" / "alpha_syn_dopamine_preparation"
SIGNOFF = PREP / "alpha_syn_dopamine_review_signoff.json"
SPLIT = PREP / "alpha_syn_dopamine_study_split_manifest_v1.json"
REGISTRY = PREP / "literature_endpoint_registry_v2.csv"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preregistration_markdown() -> str:
    return """# Alpha-synuclein/dopamine locomotion preregistration v1

Status: `PREREGISTRATION_DRAFT_LOCKED_ALLOCATION_PENDING_FINAL_SOURCE_METADATA_REVIEW`

This document is the design lock produced after dual human review of the Gate A/B
registry and study allocation. It is not a GPU execution authorization.

## Research question

Can an uncertainty-aware, connectome-constrained latent alpha-synuclein/dopamine
model explain age-related locomotor progression and generalize across study, assay,
driver, and laboratory domains better than simpler baselines?

## Scope and claim boundary

The first paper is limited to alpha-synuclein -> dopamine circuit -> locomotion.
The result will be a computational phenotype comparison. It will not be described
as a complete biological Parkinson model, a replacement for live flies, or a
gene-specific/clinical/drug validation unless independent evidence later supports
those claims.

## Study-level allocation lock

Each study has one role. No endpoint or cohort may be used for both fitting and
held-out evaluation. The locked allocation is recorded in
`alpha_syn_dopamine_study_split_manifest_v1.json`:

- Riemensperger 2011: dopamine functional-deficiency unit test.
- Pokrzywa 2017: longitudinal calibration candidate.
- Riemensperger 2013: circuit/driver generalization candidate.
- Haywood 2004: intervention-specificity holdout candidate.
- Aggarwal 2019: assay/gait validation only.
- Dimitrescu 2023: regional/age dopamine constraint and context only.
- Liessem 2026: direction prior only.
- Pugliese/NeuroMechFly: motor/body implementation only.

The roles are locked, but endpoint rows that still lack exact center/spread/unit or
primary-source verification remain pending and cannot be fitted.

## Model comparison

The preregistered comparison set is:

1. no-effect baseline;
2. global action-attenuation baseline;
3. connectome-only model without disease neuromodulation;
4. functional dopamine-deficiency model with alpha-synuclein age state;
5. structural-loss comparator kept distinct from functional deficiency.

The model must keep functional dopamine state and structural cell-loss state as
separate latent variables. A neurotransmitter annotation is not converted into a
receptor map without source evidence.

## Outcomes and evaluation

- Primary estimand: held-out study-level prediction of the reported locomotor
  phenotype relative to the appropriate study control.
- Primary comparison: alpha-synuclein/dopamine latent model versus the simple
  baselines under leave-one-study-out evaluation.
- Primary error metric: absolute error on the predeclared study-level standardized
  effect. Predictive-interval coverage and held-out log predictive density are
  secondary when the source data support them.
- Secondary outputs: age-trajectory error, intervention-rank agreement,
  phenotype-profile similarity, and failure cases.
- Assay-specific endpoints stay separate. `walking_speed`,
  `mean_planar_speed_mm_s`, and `median_planar_speed_mm_s` are not silently
  interchangeable; distance, activity time, climbing, and DAM activity are not
  converted into speed without an approved transfer rule.

## Analysis controls

- Study-level split is fixed before fitting.
- Simple baselines, ablations, sensitivity, identifiability, and uncertainty are
  reported together with the main model.
- No post-hoc endpoint, seed, threshold, burden, or study selection.
- No calibration on a holdout study.
- No claim of biological causality from simulation output alone.

## Execution gate

No fitting or GPU execution is authorized by this document. A separate authorization
must name the final preregistration hash, runner audit/commit, exact job matrix,
checkpoint/config hashes, and explicit human authorization before execution.
"""


def main() -> int:
    signoff = read_json(SIGNOFF)
    if signoff.get("status") != "DUAL_HUMAN_DIRECTION_REVIEW_PASS":
        raise RuntimeError("dual human direction review is not PASS")
    if any(reviewer.get("status") != "CONFIRMED" for reviewer in signoff.get("reviewers", [])):
        raise RuntimeError("both reviewers must be CONFIRMED")
    split = read_json(SPLIT)
    if not REGISTRY.is_file():
        raise FileNotFoundError(REGISTRY)

    for allocation in split["planned_allocations"]:
        allocation["allocation_status"] = "LOCKED_FOR_PREREGISTRATION"
        allocation["review_status"] = "DUAL_HUMAN_DIRECTION_REVIEW_PASS"
        allocation["fit_allowed_now"] = False
    split["status"] = "ALLOCATION_LOCKED_FOR_PREREGISTRATION"
    split["preparation_only"] = True
    split["allocation_lock"] = {
        "locked_at": date.today().isoformat(),
        "basis": "DUAL_HUMAN_DIRECTION_REVIEW_PASS",
        "registry_sha256": sha256(REGISTRY),
        "fitting_authorized": False,
        "gpu_execution_authorized": False,
    }
    split["required_before_fitting"] = [
        "complete and source-verify endpoint center, spread, unit, duration, and experimental unit",
        "approve final preregistration after endpoint metadata completion",
        "complete separate runner audit and execution authorization",
    ]
    write_json(SPLIT, split)

    prereg_json = {
        "schema_version": "alpha-syn-dopamine-preregistration-v1",
        "preregistration_id": "ALPHA_SYN_DOPAMINE_LOCOMOTION_V1",
        "status": "PREREGISTRATION_DRAFT_LOCKED_ALLOCATION_PENDING_FINAL_SOURCE_METADATA_REVIEW",
        "created_at": date.today().isoformat(),
        "question": "Can an uncertainty-aware connectome-constrained latent alpha-synuclein/dopamine model explain age trajectory and generalize across study, assay, driver, and laboratory?",
        "paper_scope": "alpha-synuclein -> dopamine circuit -> locomotion",
        "allocation_manifest": SPLIT.name,
        "allocation_manifest_sha256": sha256(SPLIT),
        "endpoint_registry": REGISTRY.name,
        "endpoint_registry_sha256": sha256(REGISTRY),
        "model_comparison": [
            "no_effect_baseline",
            "global_action_attenuation_baseline",
            "connectome_only_without_disease_neuromodulation",
            "functional_dopamine_deficiency_with_alpha_synuclein_age_state",
            "structural_loss_comparator",
        ],
        "primary_estimand": "held_out_study_level_prediction_of_control_relative_locomotor_phenotype",
        "primary_evaluation": "leave_one_study_out_absolute_error_on_predeclared_standardized_effect",
        "secondary_evaluation": [
            "predictive_interval_coverage_when_supported",
            "held_out_log_predictive_density_when_supported",
            "age_trajectory_error",
            "intervention_rank_agreement",
            "phenotype_profile_similarity",
            "failure_cases",
        ],
        "controls": {
            "study_split_locked_before_fitting": True,
            "no_posthoc_selection": True,
            "no_holdout_calibration": True,
            "no_gpu_execution_authorized": True,
            "no_parameter_fitting_authorized": True,
            "no_biological_causality_claim": True,
        },
        "final_source_metadata_review_required": True,
        "execution_authorization_required": True,
    }
    write_json(PREP / "alpha_syn_dopamine_preregistration_v1.json", prereg_json)
    write_text(PREP / "alpha_syn_dopamine_preregistration_v1.md", preregistration_markdown())

    authorization = {
        "schema_version": "alpha-syn-dopamine-execution-authorization-v1",
        "authorization_id": "ALPHA_SYN_DOPAMINE_EXECUTION_AUTH_V1",
        "status": "WAITING_EXPLICIT_HUMAN_EXECUTION_AUTHORIZATION",
        "authorized": False,
        "authorized_jobs": 0,
        "gpu_execution_authorized": False,
        "simulation_execution_authorized": False,
        "preregistration_id": prereg_json["preregistration_id"],
        "preregistration_sha256": sha256(PREP / "alpha_syn_dopamine_preregistration_v1.json"),
        "allocation_manifest_sha256": sha256(SPLIT),
        "required_before_authorization": [
            "final source metadata review complete",
            "preregistration status changed to final and hash recorded",
            "runner audit and code commit recorded",
            "exact job matrix, config, and checkpoint hashes recorded",
            "explicit authorization from both human reviewers",
        ],
        "prohibitions": [
            "no automatic retry",
            "no retuning",
            "no burden search after observing results",
            "no holdout opening",
        ],
    }
    write_json(PREP / "alpha_syn_dopamine_execution_authorization_v1.json", authorization)

    preparation_manifest_path = PREP / "alpha_syn_dopamine_preparation_manifest.json"
    preparation_manifest = read_json(preparation_manifest_path)
    preparation_manifest.update(
        {
            "status": "ALLOCATION_LOCKED_FOR_PREREGISTRATION_PENDING_FINAL_SOURCE_METADATA_REVIEW",
            "review_status": signoff["status"],
            "allocation_status": split["status"],
            "preregistration_id": prereg_json["preregistration_id"],
            "preregistration_status": prereg_json["status"],
            "execution_authorization_status": authorization["status"],
            "gpu_execution_authorized": False,
            "parameter_fitting_authorized": False,
        }
    )
    write_json(preparation_manifest_path, preparation_manifest)

    review_packet_path = PREP / "alpha_syn_dopamine_review_packet.md"
    review_packet = review_packet_path.read_text(encoding="utf-8")
    review_packet = review_packet.replace(
        "Status: `WAITING_DUAL_HUMAN_DIRECTION_REVIEW`",
        "Status: `DUAL_HUMAN_DIRECTION_REVIEW_PASS_ALLOCATION_LOCKED`",
    )
    review_packet += "\n\nDirection review is complete. The next required gate is final source-metadata completion and preregistration review; this packet still does not authorize fitting or GPU execution.\n"
    write_text(review_packet_path, review_packet)

    signoff["next_action"] = "Allocation locked; complete source metadata, finalize preregistration, then request separate explicit execution authorization."
    signoff["allocation_status"] = "LOCKED_FOR_PREREGISTRATION"
    write_json(SIGNOFF, signoff)

    artifact_files = sorted(
        path for path in PREP.rglob("*") if path.is_file() and path.name != "checksums.sha256"
    )
    checksum_lines = [
        f"{sha256(path)}  {path.relative_to(PREP).as_posix()}" for path in artifact_files
    ]
    write_text(PREP / "checksums.sha256", "\n".join(checksum_lines))
    print(json.dumps({
        "status": "ALPHA_SYN_DOPAMINE_ALLOCATION_LOCKED_AND_PREREG_BUILT",
        "allocation_status": split["status"],
        "preregistration_id": prereg_json["preregistration_id"],
        "execution_authorization_status": authorization["status"],
        "gpu_execution_authorized": False,
        "artifact_count": len(artifact_files) + 1,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
