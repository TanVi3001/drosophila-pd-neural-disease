# Repository architecture

```text
annotations/        reviewed neuron annotation templates and records
calibration_targets/ literature target intake and review status
configs/             condition and operator YAML
data/                source catalog and provenance metadata
datasets/            candidate literature records and intake manifests
docs/                architecture, gates, reports, and claim boundaries
experiments/         protocol/config/manifest evidence by gate
research/            paper review and dataset intake records
scripts/             thin checks, preparation, and platform launchers
src/                 reusable extension package
tests/               unit, integration-contract, and gate regression tests
```

The platform repository contains the simulation package and its own runtime,
analysis, viewer, and publication layers. Those directories are intentionally
not duplicated here.

The two supported execution boundaries are:

- edge-level preparation: neural source + annotations -> checkpoint artifact;
- platform action-level proxy: platform controller -> extension perturbation ->
  platform simulation.

The current platform does not provide a neural edge-checkpoint runner, so those
boundaries must not be conflated.
