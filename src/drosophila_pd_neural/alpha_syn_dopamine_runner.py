"""Model-specific alpha-synuclein/dopamine runner contract.

This module resolves a declared class-level dopamine proxy into explicit
functional and structural comparator conditions.  It does not infer a
gene-specific FlyWire map and it contains no implicit GPU execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import DiseaseCondition, DiseaseProfile, NeuralParameters


@dataclass(frozen=True)
class AlphaSynDopamineJob:
    job_id: str
    state: str
    seed: int


@dataclass(frozen=True)
class AlphaSynDopamineSpec:
    config_path: Path
    condition_id: str
    gene_model: str
    model_scope: str
    gene_specific_mapping: bool
    target_neurons: tuple[str, ...]
    target_edges: tuple[tuple[str, str], ...]
    functional_profile: DiseaseProfile
    structural_profile: DiseaseProfile
    seeds: tuple[int, ...]
    age_days: float
    steps: int
    device: str
    output_root: Path
    platform_root: Path
    brain_root: Path
    annotations: Path
    backend: Path
    parameter_lock_status: str
    protocol_review_status: str


def _mapping_source(project_root: Path, source_config: str) -> dict[str, Any]:
    source = (project_root / source_config).resolve()
    document = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        raise ValueError("Dopamine mapping source must be a YAML mapping.")
    if document.get("condition_id") != "dopamine_deficiency_exploratory":
        raise ValueError("Unexpected dopamine mapping source condition.")
    if document.get("status") != "EXPLORATORY_NOT_CALIBRATED":
        raise ValueError("Dopamine mapping source is not the declared exploratory source.")
    return document


def _profile(
    *,
    condition_id: str,
    gene_model: str,
    target_neurons: tuple[str, ...],
    target_edges: tuple[tuple[str, str], ...],
    state: dict[str, Any],
) -> DiseaseProfile:
    params = NeuralParameters(**(state.get("full_burden") or {}))
    curve = tuple(
        (float(row["age_days"]), float(row["burden"]))
        for row in (state.get("burden_curve") or [])
    )
    if not curve:
        raise ValueError(f"No burden curve declared for {condition_id}.")
    return DiseaseProfile(
        condition_id=condition_id,
        gene_model=gene_model,
        seed=0,
        target_neurons=target_neurons,
        target_edges=target_edges,
        full_burden=params,
        burden_curve=curve,
        provenance=("alpha_syn_dopamine_runner_v1",),
        notes="Class-level dopamine proxy; not gene-specific alpha-synuclein mapping.",
    )


def load_spec(config_path: Path, *, project_root: Path) -> AlphaSynDopamineSpec:
    config_path = config_path.resolve()
    document = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if document.get("schema_version") != "alpha-syn-dopamine-runner-v1":
        raise ValueError("Unexpected alpha-syn dopamine runner schema.")
    model = document.get("model") or {}
    mapping = document.get("mapping") or {}
    runtime = document.get("runtime") or {}
    matrix = document.get("job_matrix") or {}
    if model.get("condition_id") != "alpha_synuclein":
        raise ValueError("Runner must declare condition_id=alpha_synuclein.")
    if model.get("gene_specific_mapping") is not False:
        raise ValueError("Runner cannot claim a gene-specific mapping.")
    if model.get("biological_mapping_claim") is not False:
        raise ValueError("Runner cannot claim biological mapping.")

    source = _mapping_source(project_root, str(mapping["source_config"]))
    target_neurons = tuple(str(value) for value in source.get("target_neurons", []))
    target_edges = tuple(
        (str(row["pre"]), str(row["post"])) for row in mapping.get("target_edges", [])
    )
    if not target_neurons or not bool(mapping.get("target_ids_are_explicit")):
        raise ValueError("The runner requires an explicit target-neuron set.")

    functional = _profile(
        condition_id="alpha_synuclein_functional_dopamine",
        gene_model=str(model["gene_model"]),
        target_neurons=target_neurons,
        target_edges=target_edges,
        state=model["functional_state"],
    )
    structural = _profile(
        condition_id="alpha_synuclein_structural_loss",
        gene_model=str(model["gene_model"]),
        target_neurons=target_neurons,
        target_edges=target_edges,
        state=model["structural_comparator"],
    )
    seeds = tuple(int(value) for value in matrix.get("seeds", []))
    if not seeds or any(seed < 0 for seed in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("Runner seeds must be unique non-negative integers.")
    backend = (project_root / str(runtime["backend"])).resolve()
    output_root = (project_root / str(runtime["output_root"])).resolve()
    return AlphaSynDopamineSpec(
        config_path=config_path,
        condition_id=str(model["condition_id"]),
        gene_model=str(model["gene_model"]),
        model_scope=str(model["model_scope"]),
        gene_specific_mapping=False,
        target_neurons=target_neurons,
        target_edges=target_edges,
        functional_profile=functional,
        structural_profile=structural,
        seeds=seeds,
        age_days=float(runtime["age_days"]),
        steps=int(runtime["steps"]),
        device=str(runtime["device"]),
        output_root=output_root,
        platform_root=(project_root / str(runtime["platform_root"])).resolve(),
        brain_root=(project_root / str(runtime["brain_root"])).resolve(),
        annotations=(project_root / str(runtime["annotations"])).resolve(),
        backend=backend,
        parameter_lock_status=str(document["parameter_lock_status"]),
        protocol_review_status=str(document["protocol_review_status"]),
    )


def resolve_condition(spec: AlphaSynDopamineSpec, state: str, *, seed: int) -> DiseaseCondition:
    if state == "no_effect":
        return DiseaseCondition(
            condition_id="healthy_control",
            gene_model="no_effect_baseline",
            age_days=spec.age_days,
            seed=seed,
            parameters=NeuralParameters(),
            provenance=("alpha_syn_dopamine_runner_v1",),
            notes="No-effect baseline.",
        )
    profile = {
        "functional_state": spec.functional_profile,
        "structural_comparator": spec.structural_profile,
    }.get(state)
    if profile is None:
        raise ValueError(f"Unknown alpha-syn dopamine runner state: {state}")
    condition = profile.at_age(spec.age_days)
    if condition is None:
        raise ValueError("Declared age is outside the resolvable burden curve.")
    return DiseaseCondition(
        condition_id=condition.condition_id,
        gene_model=condition.gene_model,
        age_days=condition.age_days,
        seed=seed,
        target_neurons=condition.target_neurons,
        target_edges=condition.target_edges,
        parameters=condition.parameters,
        provenance=condition.provenance,
        notes=condition.notes,
    )


def build_job_matrix(spec: AlphaSynDopamineSpec) -> tuple[AlphaSynDopamineJob, ...]:
    jobs: list[AlphaSynDopamineJob] = []
    for condition in ("healthy_control", "alpha_synuclein_functional_dopamine", "alpha_synuclein_structural_loss"):
        state = {
            "healthy_control": "no_effect",
            "alpha_synuclein_functional_dopamine": "functional_state",
            "alpha_synuclein_structural_loss": "structural_comparator",
        }[condition]
        for seed in spec.seeds:
            jobs.append(AlphaSynDopamineJob(job_id=f"{condition}_seed_{seed:03d}", state=state, seed=seed))
    return tuple(jobs)


__all__ = [
    "AlphaSynDopamineJob",
    "AlphaSynDopamineSpec",
    "build_job_matrix",
    "load_spec",
    "resolve_condition",
]
