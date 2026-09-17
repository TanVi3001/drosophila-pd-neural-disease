# Submission bundle

## Project

Drosophila Parkinson-like locomotion proxy — computational research extension.

## Evidence status

The bundle contains historical Chen calibration and Pozo holdout evidence with
claim locks. Those records are not current-platform reruns: Gate 12G is marked
`REQUIRES_REEXECUTION_ON_CURRENT_PLATFORM`, and downstream confirmation/holdout
records must be rechecked after the platform-native protocol is executed.

The historical records include the phrases `CHEN_RATIO_CALIBRATION_PASS`,
`CHEN_CALIBRATED_CONFIRMATION_PASS`, and `POZO_HOLDOUT_RUNTIME_PASS` as their
recorded statuses. They do not establish biological, clinical, gene-specific,
drug, or therapeutic validation.

## Included components

- `README.md`
- `docs/project_summary.md`
- `docs/architecture/`
- `docs/claims/current_claim_lock.md`
- `docs/results_timeline.md`
- gate protocols, manifests, and historical result summaries

## Boundary

The bundle is suitable for review of code, provenance, computational proxy
logic, and claim discipline. It is not a claim that the current platform has
reproduced the historical runs. No new simulation, calibration, or tuning is
performed by this document.
