# Contributing

This repository is a claim-safe, evidence-constrained extension of
`drosophila-pd-flygym`. Keep platform ownership and neural-extension ownership
separate.

Before opening a change:

- inspect the platform contract with `python scripts/check_platform_contract.py`;
- keep reusable code under `src/drosophila_pd_neural/` and scripts thin;
- add tests for public behavior, serialization, failure states, and platform
  compatibility;
- do not add synthetic datasets, fabricated rollouts, or unsupported biological
  interpretations;
- run the compile, test, and whitespace checks documented in `AGENTS.md`.

Changes to the platform API must be made in the platform repository. This
repository may consume a documented platform API but must not copy or patch its
source.
