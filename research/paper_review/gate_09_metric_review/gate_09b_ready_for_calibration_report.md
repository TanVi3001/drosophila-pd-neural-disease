# Gate 09B: Final calibration readiness report

## Audit result

- Status: `READY_FOR_CALIBRATION`
- Approved targets: 2
- Calibration targets: 1
- Holdout targets: 1
- Blockers: None

The status is produced by `scripts/audit_calibration_targets.py` from the current `calibration_targets/targets.csv`. It indicates that the repository contains the minimum signed literature target set for computational calibration readiness. It does not indicate biological validation.

## Promoted targets

### Calibration

Chen 2014 adult horizontal walking speed is the calibration target. The signed review accepts the source endpoint as adult horizontal walking speed/velocity, records the source value as `0.4875 cm/s`, converts it to `4.875 mm/s`, and retains the reported uncertainty as `CI95 = 0.525 mm/s`. The independent review and provenance are recorded in `chen_2014_metric_review_completed.csv` and `research/paper_review/digitized/chen_2014_adult_walking_speed.csv`.

### Holdout

Pozo 2022 Pink1B9 `distance_traveled_mm` is the holdout target. The signed review accepts the endpoint only as distance/path length, with value `62.091 mm`, paper-reported spread `61.288`, and `n=21 fly`. It is not converted to speed and is not used for calibration.

## Policy fix

`paper_reported_center` remains holdout-only. The audit emits `PAPER_CENTER_HOLDOUT_ONLY` when that statistic is paired with `allocation=calibration`, and emits `DISTANCE_HOLDOUT_ONLY` when `distance_traveled_mm` is assigned to calibration. The valid Pozo holdout pairing remains eligible, while Chen uses `statistic=mean` and is unaffected by this rule.

## Validation

- `py -3.12 -m compileall -q src scripts tests`: PASS
- `py -3.12 -m pytest -q -rs -p no:cacheprovider`: PASS
- `git diff --check`: PASS
- CSV parse and required target metadata: PASS

No simulation, calibration, or holdout validation was run in this gate.

## Remaining non-promoted evidence

- Pokrzywa remains pending until numeric independent-vial sample size and the required metric metadata are confirmed.
- Riemensperger remains pending because the reported endpoint is median speed and its compatible uncertainty representation and transfer policy are not complete.
- Hwang and Godena remain validation-only because climbing/flight endpoints are not implemented as calibration endpoints.
- Dumitrescu remains not comparable for walking-speed calibration because DAM beam-break activity is not planar walking speed.

## Scientific boundary

This gate establishes readiness for a computational locomotion calibration workflow only. It is not a biological Parkinson model validation, clinical or diagnostic model, drug efficacy validation, or replacement for wet-lab experiments.
