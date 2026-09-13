# Alpha-synuclein/dopamine locomotion preregistration v1 — FINAL FROZEN DESIGN

Status: `FINAL_PREREGISTRATION_PENDING_DUAL_HUMAN_REVIEW`
Execution: `NOT AUTHORIZED` — no fitting, holdout opening, or GPU execution is permitted by this file.

## Research question

Can an uncertainty-aware, connectome-constrained latent alpha-synuclein/dopamine model explain age-related locomotor progression and generalize across study, assay, driver, and laboratory domains better than simpler baselines?

## Scope and claim boundary

The first paper is limited to **alpha-synuclein → dopamine circuit → locomotion**. The output is an uncertainty-aware computational phenotype comparison. It is not a claim of biological causality, a gene-specific molecular mapping, clinical validation, drug efficacy, or replacement for live-fly experiments.

## Frozen artifacts

- Endpoint registry: `literature_endpoint_registry_v2.csv`
- Endpoint registry SHA-256: `942b6ddf332035ef1553444790383abc63c58799f6ad89f21001e3abba04e0e1`
- Study split: `alpha_syn_dopamine_study_split_manifest_v1.json`
- Study split SHA-256 at freeze: `de93c8525c81cf67a092004069b995e0216f709f0c6c3b5350473d56f2175268`
- This document SHA-256: recorded in `alpha_syn_dopamine_preregistration_v1.sha256` after writing

## Registry and split policy

Each study has one role. No endpoint or cohort may be used for both fitting and held-out evaluation. The current split remains `ALLOCATION_LOCKED_PENDING_UPDATED_METADATA_REVIEW`; rows with unresolved source metadata or assay transfer remain ineligible for fitting/holdout until reviewed. `NOT_REPORTED` is preserved as missing; no value is imputed from a plot, range, or sample-size bound.

The registry contains `14` rows. At freeze, center is recorded for `9`, spread for `6`, duration for `12`, and experimental unit for `14` rows. Pending transfer and source-review decisions are not silently promoted.

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

This frozen design is awaiting two direct human attestations in `alpha_syn_dopamine_updated_registry_prereg_review_signoff_v1.json`. Review is not GPU authorization. After review, a separate runner audit and execution authorization must name the exact code commit, configuration/checkpoint hashes, job matrix, seeds, and this preregistration hash. Until that authorization is explicitly granted, scientific GPU execution remains forbidden.
