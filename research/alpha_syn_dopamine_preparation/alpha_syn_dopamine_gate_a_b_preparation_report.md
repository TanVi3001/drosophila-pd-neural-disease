# Alpha-synuclein/dopamine direction — Gate A/B preparation report

Preparation date: 2026-09-13
Status: `PREPARATION_ONLY_PENDING_DUAL_HUMAN_REVIEW`

## Interpretation of the synthesis document

The attached synthesis is a strategic research direction, not a GPU execution authorization. Its highest-ranked first paper is an alpha-synuclein/dopamine locomotion study; PINK1–serotonin is a later flagship; generic multi-gene scalar burden is explicitly rejected.

The current Gate29-H null result is retained as a class-level computational result and failure/identifiability evidence. It is not silently promoted into an alpha-synuclein biological claim and it does not authorize retuning the completed protocol.

## Current Gate A/B findings

- Existing paper-review rows imported without changing source statistics: `14`.
- Rows pending human/source review: `7`; context or validation-only rows: `7`.
- Current calibration candidate paper: `pokrzywa_2017_alpha_syn_flytracker`; it is not approved by this preparation step.
- Rows with unresolved or missing spread metadata: `6`.
- Rows with unrecorded assay duration: `4`.
- `walking_speed` is kept distinct from the simulation's `mean_planar_speed_mm_s`/`median_planar_speed_mm_s`; no automatic equivalence is asserted.
- Distance, climbing, DAM activity, and activity time remain separate endpoint families; no conversion to speed is performed.

## Next gate sequence

1. Complete source-level endpoint records for Riemensperger 2011/2013, Pokrzywa, Haywood, Aggarwal, and Dimitrescu.
2. Resolve numeric center, spread type/value, duration, assay window, and experimental unit; preserve unresolved values as pending.
3. Review and lock the study-level allocation before any fitting: calibration candidate, unit test, generalization, intervention holdout, validation, prior, or implementation-only.
4. Define simple baselines, uncertainty, ablation, sensitivity, and leave-one-study-out metrics.
5. Only after dual review and a separate execution authorization, implement the alpha-synuclein age-state/dopamine module and its assay adapter.

## Exit rule

This preparation package does not launch GPU execution, change Gate29-H outputs, fit parameters, open a holdout, or select a result by significance. The split manifest must move from `PREPARED_PENDING_DUAL_HUMAN_REVIEW` to a reviewed lock before the next scientific run.

## Artifacts

- `literature_endpoint_registry_v2.csv`: explicit endpoint records with unresolved fields preserved.
- `alpha_syn_dopamine_study_split_manifest_v1.json`: proposed study-level allocation, not yet locked.
- `alpha_syn_dopamine_direction_review_vi.md`: strategy interpretation and next gates.
