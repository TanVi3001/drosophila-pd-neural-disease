# Module responsibilities

| Area | Responsibility | Must not do |
| --- | --- | --- |
| `models.py` | Validate neural condition/profile data | Invent literature targets |
| `annotations.py` | Load ID-based annotations with provenance | Infer neuron identity from tensor position |
| `perturbations.py` | Transform supplied edge weights or signals | Run FlyGym or mutate source arrays |
| `platform_perturbation.py` | Implement the platform `Perturbation` protocol | Own simulation state or metrics |
| `proxy_burden_operator.py` | Apply a bounded action-level transform | Claim a biological mechanism |
| `platform_contract.py` | Inspect the platform source contract | Install dependencies or edit the platform |
| `calibration.py` | Compute transparent loss/readiness primitives | Auto-approve targets or run simulation |
| `provenance.py` | Write checksums and manifests | Hide missing or unverifiable inputs |
| `scripts/` | Orchestrate checks and delegate to platform | Duplicate platform algorithms |
| `docs/` and `experiments/` | Record protocol, evidence, and scope | Upgrade computational results into biology |

When a change crosses rows, prefer a narrow adapter or explicit artifact over
shared global state.
