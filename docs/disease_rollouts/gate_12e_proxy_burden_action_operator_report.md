# Gate 12E — Proxy burden action operator

## Operator

The operator applies the declared amplitude attenuation to `joint_angles` for
an organism-level computational locomotion proxy:

```text
output = action * (1 - attenuation_strength * burden_level)
```

`burden_level` is constrained to `[0, 1]`; the default attenuation strength is
`0.5`, and optional noise is seeded. Input actions are copied, shapes remain
valid, outputs are finite, and `adhesion_onoff` is preserved.

The implementation lives in
`src/drosophila_pd_neural/platform_perturbation.py:ProxyBurdenPerturbation` and
uses the current platform `Perturbation` protocol. The platform owns the
controller, action lifecycle, simulation step, and runtime artifacts.

## Readiness

The local action/protocol smoke test is source-level only and does not run
FlyGym. A real execution is available only when the platform contract and
runtime dependencies are ready. No calibration, holdout validation,
gene-specific mapping, biological validation, or disease metric is implied by
this operator.
