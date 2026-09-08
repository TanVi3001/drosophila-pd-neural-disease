"""Freeze the non-executable Gate24E 25-job scientific batch plan."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests"
PLAN_PATH = PLAN_DIR / "scientific_batch_plan.json"
CHECKSUM_PATH = PLAN_DIR / "scientific_batch_plan.sha256"
AUTHORIZATION_PATH = ROOT / "research/validation/prospective/parkin_scientific_batch_authorization_reviewer_signoff.json"
REPORT_PATH = ROOT / "docs/validation/gate24e_scientific_batch_plan_and_preflight.md"

RUNTIME_PYTHON = r"E:\Drosophila_Parkinson\drosophila-pd-flygym\.venv\Scripts\python.exe"
BRAIN_ROOT = r"E:\Drosophila_Parkinson\external\fly-brain-audit"
PLATFORM_ROOT = r"E:\Drosophila_Parkinson\drosophila-pd-flygym-gate24-memorysafe-clean"
RUNNER = str(ROOT / "scripts/run_neural_experiment.py")
OUTPUT_ROOT = ROOT / "experiments/gate_24e_blinded_parkin_prediction/runs"

MODEL_COMMIT = "be4b10a80755d9f7bad931f56b8a739bd64e3619"
RUNTIME_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"
ARTIFACT_PROFILE = "GATE24E_MEMORY_SAFE"
MAPPING_SHA256 = "776274356c16eb458ef945e2a5153af4676bbddebef31cdb1b698f1d6aeaaf80"
TARGET_ROOTS_SHA256 = "e36b0210ea6d2d2b7225f62feba73ae5c9e6535565c8b936558d0eaaf04a2085"
NEURAL_TRANSFORM_SHA256 = "8f8fe415b9a2d4490783775ef9a4aa45a82bfe624f37d969d89eda1a7bac383b"
HEALTHY_CHECKPOINT_SHA256 = "d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691"
DISEASE_CHECKPOINT_SHA256 = {
    "0.25": "dd2a4413d1aa4baed30df96884afdd030bac3a246d1bcc7a241baa955082cb8c",
    "0.5": "f682057bfff2bd523ba9a934970c9986e041ce44cb16fb8781ce2e9c5aebcff1",
    "0.75": "0b73e25620d10e56e293f859fb95c45630c7b798073b482d73f95a7d5c51e802",
    "1.0": "0ecf37ce96b6d4ea09b00204c3f01c6f41b6a2820b5f21170c6856760850e2b1",
}
SEEDS = [0, 1, 2, 3, 4]
PARAMETER_GRID = [0.0, 0.25, 0.5, 0.75, 1.0]
DISEASE_PARAMETERS = [0.25, 0.5, 0.75, 1.0]


def canonical_plan_bytes(plan: dict[str, Any]) -> bytes:
    return (json.dumps(plan, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def canonical_plan_sha256(plan: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_plan_bytes(plan)).hexdigest()


def _checkpoint_path(parameter: float) -> str:
    if parameter == 0.0:
        return r"E:\Drosophila_Parkinson\external\fly-brain-audit\data\plastic_weights.pt"
    label = f"{parameter:.2f}".replace(".", "_")
    return str((ROOT / f"results/gate24_neural_transform/parkin_grid/parameter_{label}/plastic_weights.pt").resolve())


def _job_command(seed: int, output: Path, parameter: float) -> list[str]:
    command = [
        RUNTIME_PYTHON,
        RUNNER,
        "--brain-root",
        BRAIN_ROOT,
        "--platform-root",
        PLATFORM_ROOT,
        "--seed",
        str(seed),
        "--steps",
        "100000",
        "--stimulus",
        "p9",
        "--device",
        "cuda",
        "--artifact-profile",
        ARTIFACT_PROFILE,
        "--output",
        str(output.resolve()),
    ]
    if parameter != 0.0:
        command.extend(["--prepared-checkpoint", _checkpoint_path(parameter)])
    return command


def build_jobs() -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    index = 1
    for seed in SEEDS:
        healthy_id = f"seed{seed:02d}_healthy"
        healthy_output = OUTPUT_ROOT / healthy_id
        jobs.append(
            {
                "job_index": index,
                "job_id": healthy_id,
                "seed": seed,
                "condition": "healthy",
                "parameter": 0.0,
                "checkpoint_path": _checkpoint_path(0.0),
                "checkpoint_sha256": HEALTHY_CHECKPOINT_SHA256,
                "checkpoint_role": "healthy_frozen_checkpoint",
                "output_directory": str(healthy_output.resolve()),
                "command": _job_command(seed, healthy_output, 0.0),
            }
        )
        index += 1
        for parameter in DISEASE_PARAMETERS:
            label = f"{parameter:.2f}".replace(".", "")
            job_id = f"seed{seed:02d}_parkin_p{label}"
            output = OUTPUT_ROOT / job_id
            jobs.append(
                {
                    "job_index": index,
                    "job_id": job_id,
                    "seed": seed,
                    "condition": "parkin",
                    "parameter": parameter,
                    "checkpoint_path": _checkpoint_path(parameter),
                    "checkpoint_sha256": DISEASE_CHECKPOINT_SHA256[str(parameter)],
                    "checkpoint_role": "frozen_disease_checkpoint",
                    "output_directory": str(output.resolve()),
                    "command": _job_command(seed, output, parameter),
                }
            )
            index += 1
    return jobs


def build_plan() -> dict[str, Any]:
    return {
        "schema_version": "gate24e-scientific-batch-plan-v1",
        "study_id": "parkin_prospective_validation",
        "status": "SCIENTIFIC_BATCH_PLAN_FROZEN",
        "job_count": 25,
        "ordering": "SEED_MAJOR",
        "scientific_seeds": SEEDS,
        "parameter_grid": PARAMETER_GRID,
        "healthy_job_count": 5,
        "parkin_job_count": 20,
        "technical_seed_excluded": 9001,
        "model_commit": MODEL_COMMIT,
        "runtime_commit": RUNTIME_COMMIT,
        "runtime_python": RUNTIME_PYTHON,
        "runtime_root": PLATFORM_ROOT,
        "artifact_profile": ARTIFACT_PROFILE,
        "brain_root": BRAIN_ROOT,
        "model_mapping_sha256": MAPPING_SHA256,
        "target_roots_sha256": TARGET_ROOTS_SHA256,
        "target_root_count": 330,
        "neural_transform_sha256": NEURAL_TRANSFORM_SHA256,
        "healthy_checkpoint_sha256": HEALTHY_CHECKPOINT_SHA256,
        "disease_checkpoint_sha256": DISEASE_CHECKPOINT_SHA256,
        "parameter_policy": "PREREGISTERED_GRID_NO_SINGLE_BIOLOGICAL_PARAMETER",
        "timestep_s": 0.0001,
        "duration_s": 10.0,
        "steps": 100000,
        "controller": "HybridTurningController",
        "cpg_frequency_hz": 12.0,
        "stimulus": "p9",
        "primary_metric": "median_planar_speed_mm_s",
        "secondary_metric": "distance_traveled_mm",
        "output_root": str(OUTPUT_ROOT.resolve()),
        "jobs": build_jobs(),
        "scientific_jobs_executed": 0,
        "scientific_batch_authorized": False,
        "holdout": "SEALED",
        "tuning_allowed": False,
        "posthoc_selection_allowed": False,
        "simulation_executed": False,
        "gpu_executed": False,
    }


def _write_report(plan: dict[str, Any], checksum: str) -> None:
    lines = [
        "# Gate 24E-S4E: Frozen scientific batch plan and final preflight",
        "",
        "> **NO SCIENTIFIC JOB HAS BEEN EXECUTED.**",
        "",
        "This gate freezes the future 25-job plan only. It does not run GPU, FlyGym, "
        "simulation, calibration, tuning or holdout analysis.",
        "",
        "## Current preflight boundary",
        "",
        "The Gate24E technical probe passed, but live storage capacity is still below "
        "the locked requirement. Human scientific batch authorization is also pending.",
        "Therefore the batch remains fail-closed.",
        "",
        "- Expected audit: `BLOCKED_GATE24E_SCIENTIFIC_BATCH_PREFLIGHT`.",
        "- Required blockers: `STORAGE_CAPACITY_NOT_RESOLVED` and "
        "`SCIENTIFIC_BATCH_HUMAN_REVIEW_PENDING`.",
        "- Next allowed action: `RESOLVE_STORAGE_CAPACITY_ONLY`.",
        "",
        "## Frozen contract",
        "",
        f"- Plan checksum: `{checksum}`.",
        f"- Model commit: `{plan['model_commit']}`.",
        f"- Runtime commit: `{plan['runtime_commit']}`; profile `{plan['artifact_profile']}`.",
        f"- Mapping SHA256: `{plan['model_mapping_sha256']}`; target-root SHA256: `{plan['target_roots_sha256']}`; count `330`.",
        f"- Neural transform SHA256: `{plan['neural_transform_sha256']}`.",
        f"- Steps/duration/timestep: `{plan['steps']}` / `{plan['duration_s']} s` / `{plan['timestep_s']} s`.",
        f"- Controller/CPG/stimulus: `{plan['controller']}` / `{plan['cpg_frequency_hz']} Hz` / `{plan['stimulus']}`.",
        f"- Primary metric: `{plan['primary_metric']}`; secondary metric: `{plan['secondary_metric']}`.",
        "- The parameter grid is computational and dimensionless; it is not a biological knockdown percentage.",
        "",
        "## Exact SEED-MAJOR matrix",
        "",
        "| Index | Job ID | Seed | Condition | Parameter | Checkpoint role |",
        "|---:|---|---:|---|---:|---|",
    ]
    for job in plan["jobs"]:
        lines.append(
            f"| {job['job_index']} | `{job['job_id']}` | {job['seed']} | {job['condition']} | {job['parameter']:.2f} | {job['checkpoint_role']} |"
        )
    lines.extend(
        [
            "",
            "There is no Parkin parameter `0.0` job. Healthy is the sole identity "
            "reference for each seed. No duplicate healthy jobs and no 30-job matrix "
            "are permitted.",
            "",
            "## Checkpoint and output policy",
            "",
            "Healthy jobs use the immutable healthy checkpoint. Parkin jobs use the "
            "pre-generated frozen checkpoint for their grid level. The runner must not "
            "materialize checkpoints dynamically during scientific execution.",
            "",
            "The plan contains output paths but this gate deliberately does not create "
            "the 25 run directories. Raw rollout files are not part of this plan commit.",
            "",
            "## Analysis rule",
            "",
            "For each nonzero parameter and paired seed, compute Parkin speed minus "
            "healthy speed. A parameter passes directionality only when the median of "
            "the five paired deltas is below zero and all QC passes. The grid supports "
            "`VIRTUAL_DIRECTIONAL_PREDICTION_SUPPORTED` only when every nonzero level "
            "passes. Mixed directions are `DIRECTIONAL_VALIDATION_INCONCLUSIVE` and no "
            "consistent impairment is `DIRECTIONAL_VALIDATION_NOT_SUPPORTED`.",
            "",
            "Distance cannot override the primary speed decision. Frames are not "
            "statistical replicates. No post-hoc p-values, threshold changes, seed "
            "replacement or parameter selection are allowed.",
            "",
            "## Claim lock",
            "",
            "> Parkin-specific intervention represented by a reviewed driver-defined neural perturbation and a preregistered directional computational validation protocol; no biological validation claim.",
            "",
            "This plan does not support biological Parkinson validation, clinical "
            "diagnosis, drug validation or a claim that the computational parameter is "
            "a measured biological severity.",
            "",
            "## Scientific firewall",
            "",
            "- `scientific_jobs_executed=0`.",
            "- `scientific_batch_authorized=false`.",
            "- Technical seed `9001` is excluded from scientific jobs.",
            "- Holdout remains `SEALED`; no held-out outcomes are imported.",
            "- No GPU or simulation is executed by this planning gate.",
        ]
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_artifacts() -> dict[str, Any]:
    plan = build_plan()
    checksum = canonical_plan_sha256(plan)
    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    PLAN_PATH.write_bytes(json.dumps(plan, indent=2, ensure_ascii=True) .encode("utf-8") + b"\n")
    CHECKSUM_PATH.write_text(f"{checksum}  scientific_batch_plan.json\n", encoding="ascii")
    authorization = {
        "schema_version": "gate24e-scientific-batch-authorization-v1",
        "study_id": plan["study_id"],
        "status": "WAITING_SCIENTIFIC_BATCH_AUTHORIZATION_REVIEW",
        "decision": "PENDING_HUMAN_REVIEW",
        "reviewer_1": "",
        "reviewer_2": "",
        "review_date": "",
        "scientific_batch_plan_sha256": checksum,
        "job_count": 25,
        "storage_capacity_resolved": False,
        "scientific_jobs_executed": 0,
        "scientific_batch_authorized": False,
        "holdout": "SEALED",
        "gpu_executed": False,
        "simulation_executed": False,
        "human_signoff_required": True,
    }
    AUTHORIZATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUTHORIZATION_PATH.write_bytes(json.dumps(authorization, indent=2, ensure_ascii=True).encode("utf-8") + b"\n")
    _write_report(plan, checksum)
    return {"plan": plan, "checksum": checksum, "authorization": authorization}


if __name__ == "__main__":
    result = write_artifacts()
    print(f"scientific_batch_plan_sha256: {result['checksum']}")
    print("status: SCIENTIFIC_BATCH_PLAN_FROZEN")
    print("scientific_jobs_executed: 0")
