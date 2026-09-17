# Gate 12F-B — Platform-native action-hook integration

## Result

The proxy operator is connected through the current platform's public
`Perturbation` protocol. No source patch is required or applied to
`drosophila-pd-flygym`.

- Platform protocol: `src/drosophila_pd/perturbations/base.py: Perturbation`
- Platform hook: `src/drosophila_pd/experiments/healthy_baseline.py:run_locomotion`
- Target adapter: `src/drosophila_pd_neural/platform_perturbation.py:ProxyBurdenPerturbation`
- Action shape: `joint_angles=(42,)`, `adhesion_onoff=(6,)`
- Integration stage: after `controller.step()` and before
  `apply_locomotion_action(...)`

The thin launcher is `scripts/run_platform_proxy_experiment.py`. It performs
read-only contract inspection, creates the perturbation object, and delegates
simulation ownership to the platform.

## Probe and execution boundary

The action-boundary probe checks identity at burden zero, attenuation at
positive burden, shape, finiteness, deterministic seeding, no in-place
mutation, and adhesion preservation. The probe does not create disease
metrics. A real run is only reported when the platform runtime itself exports
the required report; otherwise the launcher writes an explicit waiting or
runtime-failure status.

`CONNECTED_TO_PLATFORM_PERTURBATION_PROTOCOL`

This is computational action-level wiring only. It is not a biological
Parkinson model, clinical prediction, gene-specific mechanism, calibration,
holdout validation, or treatment-efficacy result.
