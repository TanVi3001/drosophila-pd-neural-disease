# Agent Instructions

This repository is an additive research extension to
`drosophila-pd-flygym`. The platform repository is the source of truth for
FlyGym/MuJoCo APIs, simulation ownership, controller/action contracts, and
platform documentation.

## Hard rules

- Do not invent FlyGym or MuJoCo APIs.
- Inspect the platform source, signatures, tests, and examples before changing
  integration code.
- Keep neural edge/checkpoint preparation separate from platform simulation.
- Use the platform `Perturbation` protocol for action-level integration.
- Do not patch or copy platform source into this repository.
- Do not infer biological conclusions from computational outputs.
- Missing input or runtime capability must produce an explicit waiting status;
  do not create mock rollouts or fabricated scientific values.
- Preserve provenance, deterministic seeds, manifests, and claim-safe wording.
- Run relevant tests, compile checks, and `git diff --check` after changes.
- Report verified and unverified behavior separately.

## Canonical platform contract

The current platform contract is documented in
`docs/architecture/platform_contract.md` and inspected by:

```powershell
python scripts/check_platform_contract.py --json
```

The expected platform pins are Python 3.12, FlyGym 2.1.0, and MuJoCo 3.9.0.

## Development baseline

```powershell
python -m compileall -q src scripts tests
python -m pytest -q -rs -p no:cacheprovider
git diff --check
```
