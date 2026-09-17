# Gate 12F-A — Action-hook discovery

## Result

The current `drosophila-pd-flygym` checkout is the source of truth. Static
inspection was performed against platform commit `c4505e7` (the worktree was
dirty at inspection time); no simulation was run.

The canonical path is:

```text
controller.step()
  -> Perturbation.apply_to_action(...)
  -> apply_locomotion_action(...)
  -> sim.step()
```

The implementation is in
`../drosophila-pd-flygym/src/drosophila_pd/experiments/healthy_baseline.py`.
The protocol is defined in
`../drosophila-pd-flygym/src/drosophila_pd/perturbations/base.py`.

The action is `LocomotionAction` with `joint_angles=(42,)` and
`adhesion_onoff=(6,)`. The platform does not declare a numeric joint-angle
range; actuator force limits must not be misreported as action limits.

## Integration contract

The neural repository supplies `ProxyBurdenPerturbation` from
`src/drosophila_pd_neural/platform_perturbation.py`. It implements the
platform `Perturbation` protocol by duck typing, so the neural repository does
not import, patch, or copy the platform runtime.

The operator must preserve shape, finiteness, deterministic seeded behavior,
input immutability, and `adhesion_onoff` when it modifies only joint angles.

## Readiness and boundary

`DISCOVERED`

`READY_FOR_GATE_12F_B_INTEGRATION`

This means the current platform protocol and hook were identified. It does not
mean that a disease rollout, calibration, holdout validation, biological
validation, or gene-specific mapping has been performed.
