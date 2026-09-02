# Gate 09B: Completed reviewer signoff

## Reviewer identity

- Reviewer name: Lê Tấn Vĩ
- Review date: 2026-09-02
- Reviewer role: project scientific reviewer

## Calibration target

- Selected target: Chen 2014 adult horizontal walking speed
- Decision: approved
- Assay transfer: allowed
- Digitization second review: approved
- CI95 policy: approved
- Allocation: calibration
- Provenance: `research/paper_review/digitized/chen_2014_adult_walking_speed.csv`
- Source value: `0.4875 cm/s`
- Source uncertainty: `CI95 = 0.0525 cm/s`
- Sample size: `n=20 fly`
- Computational value: `4.875 mm/s`
- Computational uncertainty: `CI95 = 0.525 mm/s`

The conversion uses `1 cm/s = 10 mm/s`. CI95 is retained as CI95 and is not relabeled as SE.

## Holdout target

- Selected target: Pozo 2022 Pink1B9 `distance_traveled_mm`
- Decision: approved
- Assay transfer: allowed
- Distance/path-length holdout policy: approved
- IQR/min-max policy: approved
- Allocation: holdout
- Provenance: `research/paper_review/pozo_distance_holdout_signoff.md`
- Value: `62.091 mm`
- Paper-reported spread: `61.288`
- Sample size: `n=21 fly`

This endpoint is approved only as a distance/path-length holdout endpoint. It must not be converted into speed or used for calibration. The IQR/min-max spread is retained as paper-reported and is not relabeled as SD or SE.

## Pending candidate

Pokrzywa remains pending because the exact independent-vial sample size is not available. No approval is inferred from the reported `3-10 vials` range.

## Scientific boundary

This signoff authorizes computational calibration readiness only. It is not biological Parkinson validation, clinical diagnosis, drug efficacy validation, or a replacement for wet-lab experiments.
