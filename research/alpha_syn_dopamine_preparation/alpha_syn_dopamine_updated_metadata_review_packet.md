# Alpha-synuclein/dopamine updated metadata review packet

Status: `READY_FOR_DUAL_HUMAN_UPDATED_REGISTRY_AND_PREREG_REVIEW`
Review date prepared: 2026-09-13

## What changed

The endpoint registry was refreshed from the primary-source full text and
existing project review artifacts. The new explicit fields are `center_value`,
`spread_type`, `spread_value`, `unit`, `duration_s`, `assay_transfer`, and
`experimental_unit`. Values that remain unavailable are recorded as
`NOT_REPORTED`; no bar height or sample-size range was converted into a false
numeric observation.

## Current source-audit counts

- Registry rows: `14`
- Rows still pending human review: `7`
- Missing numeric center: `5`
- Missing numeric spread: `8`
- Missing assay duration: `2`

## Required reviewer checks

- [ ] Every newly filled center and spread matches the cited primary source or
  a clearly labelled project digitization artifact.
- [ ] `median` is not relabelled as `mean`; IQR/min-max is not relabelled as
  SD/SE; approximate digitization remains labelled approximate.
- [ ] Experimental unit is the unit used by the study analysis, not the number
  of flies multiplied by the number of vials.
- [ ] Distance, activity time, DAM activity, and climbing remain separate from
  planar walking speed.
- [ ] Assay transfer is adjudicated per endpoint; unresolved transfer remains
  `pending` and cannot open a fitting gate.
- [ ] The preregistration scope, baselines, split, estimand, and claim boundary
  are acceptable before any model fitting.
- [ ] This review is not GPU execution authorization.

## Explicit attestations

### Reviewer 1 — Lê Tấn Vĩ

- Registry reviewed: ______________________________
- Preregistration v1 reviewed: _____________________
- Confirmation: ___________________________________
- Date: __________________

### Reviewer 2 — Tô Đặng Minh Tuấn

- Registry reviewed: ______________________________
- Preregistration v1 reviewed: _____________________
- Confirmation: ___________________________________
- Date: __________________

Until both attestations are recorded, the separate execution authorization
must remain `authorized=false` and no scientific GPU run may start.
