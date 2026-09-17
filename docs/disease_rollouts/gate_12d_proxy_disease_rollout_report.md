# Gate 12D — Computational proxy disease rollouts

## Status

`PROXY_DISEASE_ROLLOUTS_BLOCKED`

The current platform integration boundary is now available through
`drosophila_pd.perturbations.Perturbation` and
`scripts/run_platform_proxy_experiment.py`. The historical Gate 12D records
were created before that contract was adopted and contain no current-platform
rollout data. They remain blocked; no metric is fabricated.

## Scope

This is not biological validation.

The planned `alpha_synuclein` and `pink1` conditions are
`organism_level_proxy` organism-level,
dimensionless action proxies only. They are not gene-specific mappings and do
not establish a biological Parkinson mechanism, clinical prediction, diagnosis,
drug response, or wet-lab result.

Calibration and holdout validation remain disabled. The previous plan also
listed `parkin`, `dj1`, and `lrrk2` as blocked in Gate 12C. The next execution must
use the platform-native launcher and must retain the platform report as the
source of runtime metrics. If raw trajectory export is required by a gate but
is not provided by the platform, the run must remain explicitly blocked.
