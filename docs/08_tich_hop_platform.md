# Platform integration contract

The `drosophila-pd-flygym` checkout is the source of truth for simulation and
platform documentation. This repository must not patch or duplicate its
runtime.

## Canonical integration

The platform defines `Perturbation` in
`src/drosophila_pd/perturbations/base.py` and invokes it in the locomotion
pipeline in `src/drosophila_pd/experiments/healthy_baseline.py`:

```text
controller.step()
  -> perturbation.apply_to_action(...)
  -> apply_locomotion_action(...)
  -> simulation.step()
```

`ProxyBurdenPerturbation` in this repository implements that protocol without
importing platform internals. The thin launcher
`scripts/run_platform_proxy_experiment.py` checks the platform contract,
constructs the perturbation, and delegates simulation and metrics to the
platform.

## Separate neural boundary

`prepare_neural_checkpoint.py` creates a provenance-aware edge/checkpoint
artifact when the external inputs are available. That artifact is not a
rollout and cannot be passed to the current platform as if it were a neural
runtime. `run_neural_experiment.py` therefore returns
`WAITING_PLATFORM_NEURAL_RUNTIME` for this case.

Platform runtime failures remain explicit `WAITING_RUNTIME` or failure reports;
mock data is never promoted to a simulation result.
