# Platform alignment record — 2026-09-06

## Findings

The extension previously described and invoked a superseded brain-body runner.
That path is absent from the current `drosophila-pd-flygym` source of truth.
The current platform instead provides a general `Perturbation` protocol and
canonical healthy/brain-driven entry points.

The previous integration description also mixed three different artifacts:
neural edge/checkpoint preparation, an action-level proxy, and a platform
rollout. They are now documented as separate boundaries.

## Changes

- package metadata now follows the platform's `src`/setuptools conventions;
- platform pins and required files are checked read-only;
- `ProxyBurdenPerturbation` implements the platform protocol without importing
  or modifying platform code;
- `run_platform_proxy_experiment.py` delegates simulation to the platform;
- `run_neural_experiment.py` uses the platform's actual healthy and
  bridge-driven scripts and returns an explicit waiting state for unsupported
  edge-checkpoint execution;
- architecture, API, reproducibility, security, and scientific-boundary docs
  were added as a canonical documentation layer;
- old patch-based integration records are marked historical/superseded rather
  than presented as current platform behavior.

## Verification boundary

Source-level compatibility is verified by tests and the contract inspector. A
real FlyGym/MuJoCo run remains environment-dependent and is not claimed by this
alignment record.
