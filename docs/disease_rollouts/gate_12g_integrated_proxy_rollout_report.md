# Gate 12G — Integrated proxy rollout record

Scope: organism-level computational proxy; this record is not a biological
Parkinson validation.

Phạm vi: không phải biological parkinson validation.

## Current status

`REQUIRES_REEXECUTION_ON_CURRENT_PLATFORM`

This directory contains a historical 60-row computational proxy artifact. The
record was produced against an earlier integration path and is retained for
provenance, but it must not be treated as a current-platform PASS. The current
source of truth is platform commit `c4505e7`; the current integration uses the
platform `Perturbation` protocol and requires a fresh run through
`scripts/run_platform_proxy_experiment.py`.

## Current contract

- Conditions: `alpha_synuclein` and `pink1` at `organism_level_proxy` scope.
- Operator target: `joint_angles` only; `adhesion_onoff` is preserved.
- Platform protocol: `drosophila_pd.perturbations.Perturbation`.
- Platform hook: `drosophila_pd.experiments.healthy_baseline.run_locomotion`.
- No platform source patch is required.
- Calibration, holdout validation, gene-specific mapping, and biological
  validation remain out of scope.

The historical rows are not fabricated, but their runtime provenance does not
match the current platform contract. They are therefore evidence records, not
new claims. A new run must preserve the platform report as the authority for
locomotion metrics and must stop explicitly if the required trajectory export
is unavailable.
