# Canonical platform contract

## Source of truth

`drosophila-pd-flygym` owns FlyGym/MuJoCo integration, controller construction,
the action lifecycle, locomotion metrics, rollout artifacts, and platform
documentation. This repository must consume those interfaces instead of
copying or patching platform source.

The current platform checkout is expected to declare Python 3.12, FlyGym 2.1.0,
and MuJoCo 3.9.0 in its `pyproject.toml`. The neural repository checks the
following files:

| Capability | Canonical platform file | Ownership |
| --- | --- | --- |
| Perturbation protocol | `src/drosophila_pd/perturbations/base.py` | platform |
| Controller/action hook | `src/drosophila_pd/experiments/healthy_baseline.py` | platform |
| Healthy entry point | `scripts/run_healthy_baseline.py` | platform |
| Bridge-scale entry point | `scripts/run_brain_driven_experiment.py` | platform |
| Neural proxy adapter | `src/drosophila_pd_neural/platform_perturbation.py` | extension |

Inspect the local checkout without importing FlyGym or mutating files:

```powershell
python scripts/check_platform_contract.py --platform-root ..\drosophila-pd-flygym --json
```

The report includes the observed commit and whether the platform worktree is
dirty. A dirty worktree is recorded as provenance; it is not silently treated
as a release tag.

## Integration semantics

The platform calls `Perturbation.apply_to_controller` after controller creation
and calls `Perturbation.apply_to_action` after `controller.step()` and before
`apply_locomotion_action(...)`. The extension's
`ProxyBurdenPerturbation` transforms only `joint_angles`, copies
`adhesion_onoff`, and never mutates the incoming action.

The superseded brain-body runner path is not part of the current platform
contract. No patch file is required. A neural edge checkpoint is a
separate artifact and cannot be passed to the current platform unless a future
platform owner adds and documents a compatible neural runtime.

## Failure states

- `WAITING_PLATFORM_CAPABILITY`: required platform source files or pins are
  missing;
- `WAITING_PLATFORM_NEURAL_RUNTIME`: an edge-level checkpoint was prepared but
  the current platform has no checkpoint-consuming neural runner;
- `WAITING_RUNTIME`: source compatibility exists but FlyGym/MuJoCo is not
  available in the execution environment;
- `PASS`: a real platform execution returned a passing computational report.

None of these statuses is biological validation.
