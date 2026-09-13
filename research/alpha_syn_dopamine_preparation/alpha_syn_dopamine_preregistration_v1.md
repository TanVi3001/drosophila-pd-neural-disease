# Alpha-synuclein/dopamine locomotion preregistration v1

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
