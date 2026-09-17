# Controlled dataset and neural-source intake

The repository stores small provenance records and review decisions. Large
connectomes, checkpoints, and external source trees remain outside Git and
must be fetched and verified according to `data/source_catalog.json`.

## Intake rules

- Do not turn numbers in a source report into a dataset without a record-level
  provenance decision.
- Verify declared size, checksum, license, and source revision before use.
- Do not infer gene-specific neuron IDs from a cell class, genotype, or tensor
  position.
- Keep assay endpoint, unit, uncertainty, sample size, and age/sex metadata
  explicit.
- Missing review or compatibility information means `WAITING_TARGET_DATA`.

The candidate literature records in `datasets/literature_phenotypes/` are not
automatically approved calibration or holdout targets. Their manifest and
second-review audits are part of the evidence boundary.

## Preparation versus execution

`prepare_neural_checkpoint.py` can apply a declared edge perturbation and write
a checksum-bearing checkpoint artifact when the required inputs are present.
That artifact is not a rollout. The supported rollout boundary is instead:

```text
reviewed inputs -> condition/checkpoint artifact
                         |
                         v
             platform Perturbation or bridge-scale input
                         |
                         v
              canonical platform simulation/report
```

Use `scripts/check_platform_contract.py` before integration. Use
`scripts/run_platform_proxy_experiment.py` for the action-level proxy. A neural
checkpoint condition stops at `WAITING_PLATFORM_NEURAL_RUNTIME` until the
platform owner documents a compatible neural runner.

## Scientific boundary

This intake supports computational experiment preparation. It does not confirm
biological Parkinson mechanisms, gene-to-neuron causality, clinical prediction,
diagnosis, drug efficacy, or equivalence between a literature assay and a
platform metric.
