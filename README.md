# drosophila-pd-neural-disease

[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-blue)](https://pytest.org/)

An evidence-constrained neural and locomotion perturbation extension for the
canonical [`drosophila-pd-flygym`](https://github.com/TanVi3001/drosophila-pd-flygym)
platform.

## Ownership boundary

`drosophila-pd-flygym` is the source of truth for FlyGym/MuJoCo versions,
simulation construction, controller/action contracts, locomotion metrics,
artifacts, and platform documentation. This repository is additive: it owns
neural-condition records, annotation/provenance checks, calibration readiness,
edge-level checkpoint preparation, and a platform-compatible action-level
proxy adapter.

```text
canonical platform
  FlyGym/MuJoCo -> controller -> action hook -> simulation -> artifacts/metrics
                                      ^
                                      |
neural extension ---------------- Perturbation protocol adapter
  annotations -> condition -> provenance/checkpoint preparation
```

The extension does not copy or patch platform source. The current platform no
longer exposes the superseded brain-body runner. The
supported platform interfaces are:

- `src/drosophila_pd/perturbations/base.py` — `Perturbation` protocol;
- `src/drosophila_pd/experiments/healthy_baseline.py` — canonical action hook;
- `scripts/run_healthy_baseline.py` — healthy baseline entry point;
- `scripts/run_brain_driven_experiment.py` — bridge-scale entry point.

Inspect this contract before running integration work:

```powershell
python scripts/check_platform_contract.py --json
```

## Scientific scope

The project provides computational locomotion proxies and provenance-aware
research tooling. It does not establish biological Parkinson validation,
gene-specific neural mechanisms, clinical prediction, diagnosis, drug
efficacy, or equivalence between a proxy burden and dopamine or disease
severity. Missing data and unsupported platform capabilities remain explicit
waiting states; they are never filled with synthetic values.

The current literature/gate artifacts remain claim-locked. Read
[`docs/claims/current_claim_lock.md`](docs/claims/current_claim_lock.md) and
[`docs/architecture/scientific_boundaries.md`](docs/architecture/scientific_boundaries.md)
before interpreting any result.

## Locked historical results

The repository retains historical literature/gate records for provenance, but
they are not silently promoted to current platform results. The recorded
labels include `CHEN_RATIO_CALIBRATION_PASS`,
`CHEN_CALIBRATED_CONFIRMATION_PASS`, and `POZO_HOLDOUT_RUNTIME_PASS`; the
Pozo record reports `DIRECTIONAL_CONCORDANCE_WITH_QUANTITATIVE_MISMATCH`.
Reference ratios `0.9470` and `0.1920` remain source-reported values, not
claims of biological or clinical validation. Gate 12G is marked for
re-execution on the current platform contract. The locked Gate 12 runtime
protocol uses a `0.5 s` physical simulation duration.

## Installation

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

The optional `brain` extra is for caller-supplied PyTorch/connectome tooling.
The FlyGym and MuJoCo runtime remains owned and pinned by the platform
repository; install its documented `.[simulation]` extra in the platform
environment when a real simulation is authorized.

## Checks

```powershell
python scripts/check_platform_contract.py
python -m compileall -q src scripts tests
python -m pytest -q -rs -p no:cacheprovider
git diff --check
```

## Supported workflows

Prepare an edge-level neural artifact only after annotation and provenance are
available:

```powershell
python scripts/apply_neural_condition.py `
  --config configs/conditions/alpha_synuclein.template.yaml `
  --age-days 20 `
  --annotations annotations/neuron_annotations.csv `
  --edges data/edge_list.csv `
  --output results/alpha_synuclein/day_020
```

This creates an edge artifact, not a rollout. A condition with missing review
inputs must stop at `WAITING_TARGET_DATA`.

Build a bridge artifact only when each spike output has a run manifest. The
manifest must use `lif-run-manifest-1` and declare a positive integer
`trial_count`; the bridge never infers the denominator from observed spike
rows, because silent trials have no rows.

```powershell
python scripts/build_bridge_scales.py `
  --reference-spikes path\reference.parquet `
  --condition-spikes path\condition.parquet `
  --reference-manifest path\reference.run.json `
  --condition-manifest path\condition.run.json `
  --model reviewed_readout `
  --output results\bridge_scales.json
```

Run the action-level proxy through the platform's public perturbation contract:

```powershell
python scripts/run_platform_proxy_experiment.py `
  --platform-root ..\drosophila-pd-flygym `
  --burden 0.5 `
  --seed 0 `
  --output results/platform_proxy/seed_000
```

Run a platform bridge-scale experiment when a real `bridge_scales.json` is
available:

```powershell
python scripts/run_neural_experiment.py `
  --scales-json ..\drosophila-pd-flygym\data\bridge_scales\pink1_bridge_scales.json `
  --platform-root ..\drosophila-pd-flygym `
  --output results/brain_driven/pink1
```

Passing a neural edge/checkpoint condition to `run_neural_experiment.py`
prepares the checkpoint and returns `WAITING_PLATFORM_NEURAL_RUNTIME` because
the current canonical platform has no runner that consumes that checkpoint.
This is an intentional capability gate, not a reason to fabricate a rollout.

## Repository map

- `src/drosophila_pd_neural/` — models, annotation, edge perturbation,
  provenance, platform contract, and platform adapter;
- `annotations/`, `data/`, `datasets/` — small provenance-aware inputs and
  review records; large external artifacts stay ignored;
- `configs/` — condition and operator configuration templates;
- `experiments/` — frozen gate protocols, manifests, and review boundaries;
- `scripts/` — thin operational entry points;
- `tests/` — regression and contract tests;
- `docs/` — canonical architecture, scientific boundaries, reproducibility,
  gate reports, and legacy-to-platform alignment notes.

Start at the [`documentation hub`](docs/README.md), then read the
[`platform contract`](docs/architecture/platform_contract.md).
