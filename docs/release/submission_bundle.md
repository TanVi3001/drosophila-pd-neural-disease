# Submission Bundle

## Project

Drosophila Parkinson-like Locomotion Proxy

## Current evidence level

Chen-calibrated organism-level computational locomotion proxy with directional Pozo holdout concordance and substantial quantitative ratio mismatch.

## Included components

- `README.md`
- `docs/project_summary.md`
- `docs/limitations.md`
- `docs/results_timeline.md`
- `docs/claims/current_claim_lock.md`
- `docs/claims/public_abstract.md`
- `docs/claims/claim_safe_wording_guide.md`
- `docs/holdout/gate_14c_holdout_adjudication_report.md`
- `experiments/gate_14c_holdout_adjudication/`
- `experiments/gate_14b_pozo_holdout_validation/`
- `experiments/gate_13c_calibrated_confirmation/`
- `experiments/gate_13b_chen_ratio_calibration/`

## Main result

- Chen-only ratio calibration selected `proxy_burden_level = 0.5`.
- Gate 13C confirmed locked parameter behavior.
- Gate 14B Pozo holdout runtime passed with `12/12` rollouts.
- Pozo directionality passed.
- Quantitative ratio mismatch remains large.

## Boundary

This is not biological validation, not gene-specific validation, not clinical validation, not drug validation, or therapeutic validation.

Gate 15B does not run new simulation, calibration, or tuning and does not
modify raw metrics or previous gate manifests.
