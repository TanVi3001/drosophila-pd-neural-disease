# Gate 24E-S4C: attempt_04 technical storage probe result

## Scope

This is a technical and storage record for exactly one `attempt_04` execution.
It is not a scientific result, did not open the scientific batch, did not run
calibration, and did not open or interpret the holdout. Scalar metrics remain
local only for rollout integrity checks and are not given biological meaning in
this gate.

## Runtime provenance

| Field | Value |
|---|---|
| Attempt | `attempt_04` |
| Technical seed | `9001` |
| Requested steps | `100000` |
| Duration | `10.0 s` |
| Device | `cuda` |
| Platform commit | `655e854544e3d814dfe422883ff0de66b619d6c1` |
| Artifact profile | `GATE24E_MEMORY_SAFE` |
| Python | `3.12.10` |
| FlyGym | `2.1.0` |
| PyTorch | `2.5.1+cu121` |
| CUDA | `12.1` |
| GPU | NVIDIA GeForce RTX 3050 6GB Laptop GPU |

## Technical execution result

- The `--execute` command was invoked exactly once.
- Simulation started and ended with return code `0`.
- The final progress marker was `100000/100000`; the rollout produced
  `100001` frames.
- `status.json` reports `status=PASS` and `simulation_run=true`.
- Artifact validation: `PASS`. The run contains `rollout.npz`, `metadata.json`,
  `manifest.json`, and `metrics/metrics.json`; the manifest confirms the
  `GATE24E_MEMORY_SAFE` profile.
- `attempt_04` is consumed. Automatic retry and manual retry are forbidden.

## Storage measurements

These values are used only for the `attempt_04` storage qualification:

| Measurement | Bytes |
|---|---:|
| Free before | 13,796,921,344 |
| Minimum free during run | 12,570,980,352 |
| Free after | 13,238,644,736 |
| Final artifact | 558,250,361 |
| Peak disk consumption | 1,225,940,992 |
| Transient bytes | 667,690,631 |
| Projected final for 25 jobs | 13,956,259,025 |
| Projected peak for 25 jobs | 14,623,949,656 |
| Reserve (20%) | 2,924,789,932 |
| Required bytes | 17,548,739,588 |

The Gate 24E formulas were applied without modification:

```text
transient = max(0, peak_disk_consumption - final_artifact)
projected_peak = projected_final_25 + transient
reserve = ceil(projected_peak * 0.20)
required = projected_peak + reserve
```

Strict comparison:

```text
free_after > required
13,238,644,736 > 17,548,739,588  => FALSE
```

## Post-probe state

| Field | Value |
|---|---|
| Probe execution status | `ATTEMPT_04_STORAGE_PROBE_PASS` |
| Storage measurements valid | `true` |
| Storage qualification assessed | `true` |
| Storage qualified | `false` |
| Qualification status | `WAITING_GATE24E_STORAGE_CAPACITY` |
| Scientific jobs executed | `0` |
| Scientific batch authorized | `false` |
| Holdout | `SEALED` |
| Scientific interpretation | `false` |

Conclusion: the technical probe is valid, but the current machine does not
meet the projected 25-job capacity requirement with the 20% reserve. The exact
next allowed action is `RESOLVE_STORAGE_CAPACITY_ONLY`. Do not run a scientific
batch or create `attempt_05` in this gate.

## Referenced artifacts

- Execution manifest:
  `experiments/gate_24e_storage_probe/attempt_04/manifests/attempt_04_execution.json`
- Storage qualification:
  `experiments/gate_24e_storage_probe/attempt_04/manifests/storage_qualification.json`
- Storage history:
  `experiments/gate_24e_storage_probe/manifests/storage_qualification.json`

The large raw rollout and log remain local for audit and are intentionally not
committed.
