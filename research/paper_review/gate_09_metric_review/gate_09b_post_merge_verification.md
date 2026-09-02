# Gate 09B Post-Merge Verification

## Merge status

- Gate 09B branch: `review/gate-09b-fill-reviewed-metrics-ready`
- Main commit after merge: `ee878ef`
- Merge date: 2026-09-02
- Merge result: PASS, no conflicts

## Audit result on main

- Status: `READY_FOR_CALIBRATION`
- Approved targets: `2`
- Calibration targets: `1`
- Holdout targets: `1`
- Blockers: none

## Approved targets

### Calibration

- Chen 2014 adult horizontal walking speed
- Metric: `mean_planar_speed_mm_s`
- Value: `4.875 mm/s`
- Uncertainty: `CI95 = 0.525 mm/s`
- Sample size: `20 fly`
- Allocation: `calibration`

### Holdout

- Pozo 2022 Pink1B9 distance
- Metric: `distance_traveled_mm`
- Value: `62.091 mm`
- Spread: `61.288`, retained as paper-reported IQR/min-max spread
- Sample size: `21 fly`
- Allocation: `holdout`

## Validation

- `py -3.12 -m compileall -q src scripts tests`: PASS
- `py -3.12 -m pytest -q -rs -p no:cacheprovider`: PASS, `61 passed`
- `git diff --check`: PASS

No disease simulation, calibration, or holdout validation was run during this merge verification.

## Scientific boundary

This merge establishes computational calibration readiness only. It is not biological Parkinson validation, clinical diagnosis, drug efficacy validation, or a replacement for wet-lab experiments.

## Next scientific state

- `TARGET_DATA_READY`
- `READY_FOR_CALIBRATION`
- `NOT_YET_CALIBRATED`
- `NOT_YET_HOLDOUT_VALIDATED`

The next recommended task is Gate 10: Calibration Run Preparation. Disease simulation must remain stopped until the Gate 10 run plan has been reviewed.
