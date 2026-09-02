# Gate 09B Completed Reviewer Signoff

## Reviewer identity

- Reviewer name: Lê Tấn Vĩ
- Review date: 2026-09-02
- Reviewer role: project scientific reviewer

## Calibration target approval

- Selected target: Chen 2014 adult horizontal walking speed
- Decision: approved
- Assay transfer: allowed
- Digitization second review: approved
- CI95 policy: approved
- Allocation: calibration
- Provenance: `research/paper_review/digitized/chen_2014_adult_walking_speed.csv`

Reviewer statement:

I approve the Chen 2014 Old A30P adult horizontal walking speed target for
computational calibration readiness. The source endpoint is adult horizontal
walking speed/velocity. The digitized disease value is 0.4875 cm/s with CI95
0.0525 cm/s and sample size n=20 fly. The physical unit conversion 1 cm/s = 10
mm/s is allowed, giving 4.875 mm/s and CI95 0.525 mm/s. CI95 is retained as
CI95 and is not relabeled as SE.

## Holdout target approval

- Selected target: Pozo 2022 Pink1B9 `distance_traveled_mm`
- Decision: approved
- Assay transfer: allowed
- Distance/path-length holdout policy: approved
- IQR/min-max policy: approved
- Allocation: holdout
- Provenance: `research/paper_review/pozo_distance_holdout_signoff.md`

Reviewer statement:

I approve the Pozo 2022 Pink1B9 `distance_traveled_mm` target for computational
holdout readiness. The target value is 62.091 mm, with paper-reported spread
61.288 and sample size n=21 fly. This endpoint is approved only as a
distance/path-length holdout endpoint. It must not be converted into speed and
must not be used for calibration. The IQR/min-max spread is retained as
paper-reported and is not relabeled as SD or SE.

## Pokrzywa decision

- Decision: pending
- Reason: exact independent-vial sample size is still missing; do not promote.

## Scientific boundary

This signoff only authorizes computational calibration readiness. It is not
biological Parkinson validation, clinical diagnosis, drug efficacy validation,
or a replacement for wet-lab experiments.
