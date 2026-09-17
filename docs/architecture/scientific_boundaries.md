# Scientific boundaries

This repository supports computational neural/locomotion perturbations,
provenance checks, calibration readiness, and comparison of supplied
computational outputs. Software execution alone does not:

- validate Parkinson's disease biology;
- establish a gene-to-neuron causal mapping;
- measure dopamine, alpha-synuclein aggregation, mitochondrial pathology, or
  cell death;
- provide clinical prediction, diagnosis, drug efficacy, or treatment response;
- make a platform proxy burden equivalent to disease severity;
- replace experiments in real Drosophila.

Reports must distinguish:

1. software contract checks;
2. neural edge/checkpoint preparation;
3. real FlyGym/MuJoCo simulation output;
4. derived computational metrics;
5. biological interpretation, which remains outside the software claim.

If a required input or runtime is absent, the correct result is a waiting or
blocked status. No synthetic value may be inserted to make a gate pass.
