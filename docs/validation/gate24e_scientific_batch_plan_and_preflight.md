# Gate 24E-S4E: Frozen scientific batch plan and final preflight

> **NO SCIENTIFIC JOB HAS BEEN EXECUTED.**

This gate freezes the future 25-job plan only. It does not run GPU, FlyGym, simulation, calibration, tuning or holdout analysis.

## Current preflight boundary

The Gate24E technical probe passed, but live storage capacity is still below the locked requirement. Human scientific batch authorization is also pending.
Therefore the batch remains fail-closed.

- Expected audit: `BLOCKED_GATE24E_SCIENTIFIC_BATCH_PREFLIGHT`.
- Required blockers: `STORAGE_CAPACITY_NOT_RESOLVED` and `SCIENTIFIC_BATCH_HUMAN_REVIEW_PENDING`.
- Next allowed action: `RESOLVE_STORAGE_CAPACITY_ONLY`.

## Frozen contract

- Plan checksum: `4515e1916631b019711154dccb5fb887110d5572e3eb82b7ea5118c643db5aac`.
- Model commit: `be4b10a80755d9f7bad931f56b8a739bd64e3619`.
- Runtime commit: `655e854544e3d814dfe422883ff0de66b619d6c1`; profile `GATE24E_MEMORY_SAFE`.
- Mapping SHA256: `776274356c16eb458ef945e2a5153af4676bbddebef31cdb1b698f1d6aeaaf80`; target-root SHA256: `e36b0210ea6d2d2b7225f62feba73ae5c9e6535565c8b936558d0eaaf04a2085`; count `330`.
- Neural transform SHA256: `8f8fe415b9a2d4490783775ef9a4aa45a82bfe624f37d969d89eda1a7bac383b`.
- Steps/duration/timestep: `100000` / `10.0 s` / `0.0001 s`.
- Controller/CPG/stimulus: `HybridTurningController` / `12.0 Hz` / `p9`.
- Primary metric: `median_planar_speed_mm_s`; secondary metric: `distance_traveled_mm`.
- The parameter grid is computational and dimensionless; it is not a biological knockdown percentage.

## Exact SEED-MAJOR matrix

| Index | Job ID | Seed | Condition | Parameter | Checkpoint role |
|---:|---|---:|---|---:|---|
| 1 | `seed00_healthy` | 0 | healthy | 0.00 | healthy_frozen_checkpoint |
| 2 | `seed00_parkin_p025` | 0 | parkin | 0.25 | frozen_disease_checkpoint |
| 3 | `seed00_parkin_p050` | 0 | parkin | 0.50 | frozen_disease_checkpoint |
| 4 | `seed00_parkin_p075` | 0 | parkin | 0.75 | frozen_disease_checkpoint |
| 5 | `seed00_parkin_p100` | 0 | parkin | 1.00 | frozen_disease_checkpoint |
| 6 | `seed01_healthy` | 1 | healthy | 0.00 | healthy_frozen_checkpoint |
| 7 | `seed01_parkin_p025` | 1 | parkin | 0.25 | frozen_disease_checkpoint |
| 8 | `seed01_parkin_p050` | 1 | parkin | 0.50 | frozen_disease_checkpoint |
| 9 | `seed01_parkin_p075` | 1 | parkin | 0.75 | frozen_disease_checkpoint |
| 10 | `seed01_parkin_p100` | 1 | parkin | 1.00 | frozen_disease_checkpoint |
| 11 | `seed02_healthy` | 2 | healthy | 0.00 | healthy_frozen_checkpoint |
| 12 | `seed02_parkin_p025` | 2 | parkin | 0.25 | frozen_disease_checkpoint |
| 13 | `seed02_parkin_p050` | 2 | parkin | 0.50 | frozen_disease_checkpoint |
| 14 | `seed02_parkin_p075` | 2 | parkin | 0.75 | frozen_disease_checkpoint |
| 15 | `seed02_parkin_p100` | 2 | parkin | 1.00 | frozen_disease_checkpoint |
| 16 | `seed03_healthy` | 3 | healthy | 0.00 | healthy_frozen_checkpoint |
| 17 | `seed03_parkin_p025` | 3 | parkin | 0.25 | frozen_disease_checkpoint |
| 18 | `seed03_parkin_p050` | 3 | parkin | 0.50 | frozen_disease_checkpoint |
| 19 | `seed03_parkin_p075` | 3 | parkin | 0.75 | frozen_disease_checkpoint |
| 20 | `seed03_parkin_p100` | 3 | parkin | 1.00 | frozen_disease_checkpoint |
| 21 | `seed04_healthy` | 4 | healthy | 0.00 | healthy_frozen_checkpoint |
| 22 | `seed04_parkin_p025` | 4 | parkin | 0.25 | frozen_disease_checkpoint |
| 23 | `seed04_parkin_p050` | 4 | parkin | 0.50 | frozen_disease_checkpoint |
| 24 | `seed04_parkin_p075` | 4 | parkin | 0.75 | frozen_disease_checkpoint |
| 25 | `seed04_parkin_p100` | 4 | parkin | 1.00 | frozen_disease_checkpoint |

There is no Parkin parameter `0.0` job. Healthy is the sole identity reference for each seed. No duplicate healthy jobs and no 30-job matrix are permitted.

## Checkpoint and output policy

Healthy jobs use the immutable healthy checkpoint. Parkin jobs use the pre-generated frozen checkpoint for their grid level. The runner must not materialize checkpoints dynamically during scientific execution.

The plan contains output paths but this gate deliberately does not create the 25 run directories. Raw rollout files are not part of this plan commit.

## Analysis rule

For each nonzero parameter and paired seed, compute Parkin speed minus healthy speed. A parameter passes directionality only when the median of the five paired deltas is below zero and all QC passes. The grid supports `VIRTUAL_DIRECTIONAL_PREDICTION_SUPPORTED` only when every nonzero level passes. Mixed directions are `DIRECTIONAL_VALIDATION_INCONCLUSIVE` and no consistent impairment is `DIRECTIONAL_VALIDATION_NOT_SUPPORTED`.

Distance cannot override the primary speed decision. Frames are not statistical replicates. No post-hoc p-values, threshold changes, seed replacement or parameter selection are allowed.

## Claim lock

> Parkin-specific intervention represented by a reviewed driver-defined neural perturbation and a preregistered directional computational validation protocol; no biological validation claim.

This plan does not support biological Parkinson validation, clinical diagnosis, drug validation or a claim that the computational parameter is a measured biological severity.

## Scientific firewall

- `scientific_jobs_executed=0`.
- `scientific_batch_authorized=false`.
- Technical seed `9001` is excluded from scientific jobs.
- Holdout remains `SEALED`; no held-out outcomes are imported.
- No GPU or simulation is executed by this planning gate.
