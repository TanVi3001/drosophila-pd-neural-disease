# Reviewer Quickstart

## Recommended reading order

1. `README.md`
2. `docs/claims/current_claim_lock.md`
3. `docs/project_summary.md`
4. `docs/results_timeline.md`
5. `docs/limitations.md`
6. `docs/holdout/gate_14c_holdout_adjudication_report.md`

## Verify without rerunning GPU

```powershell
py -3.12 scripts/adjudicate_pozo_holdout_claims.py
py -3.12 scripts/prepare_pozo_holdout_protocol.py
py -3.12 scripts/run_chen_ratio_calibration.py
py -3.12 scripts/prepare_chen_only_calibration_objective.py
py -3.12 scripts/audit_calibration_targets.py
py -3.12 -m pytest -q -rs -p no:cacheprovider
```

## Important note

GPU rollouts are already recorded in artifact files with checksum. Reviewers do
not need to rerun GPU by default.
