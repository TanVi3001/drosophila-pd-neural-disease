# Repository status

## Software status

| Area | Status | Evidence |
| --- | --- | --- |
| Packaging/import contract | Ready | `pyproject.toml`, package tests |
| Neural models and edge transform | Ready as computational utilities | unit tests and explicit input contracts |
| Platform source compatibility | Inspectable | `scripts/check_platform_contract.py` |
| Platform action adapter | Ready as a protocol implementation | `ProxyBurdenPerturbation` tests |
| Neural checkpoint execution in platform | Waiting | current platform has no compatible checkpoint runner |
| FlyGym/MuJoCo execution | Environment-dependent | owned by canonical platform |
| Literature calibration | Claim/gate-controlled | `calibration_targets/` and `docs/11_calibration_readiness.md` |

## Interpretation

“Ready” describes a software boundary or a reproducible input contract. It does
not mean biological validation. Gate reports and frozen result files are
historical evidence records and must be read together with the current platform
contract and claim lock.
