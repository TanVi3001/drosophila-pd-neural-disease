# Gate 24D Reviewer Packet: Parkin Prospective Virtual Prediction

Status: `WAITING_PROSPECTIVE_PREDICTION_REVIEW`

This packet freezes the prospective computational experiment before any GPU
rollout. It is a review artifact, not a simulation result.

## 1. Scientific question

Can a reviewed, TH-GAL4/driver-defined neural transform applied to the locked
healthy Drosophila neural checkpoint produce a preregistered directional
locomotor impairment across the complete computational perturbation grid?

## 2. Parkin intervention

- Primary gene: `parkin`
- Intervention: `UAS-parkin-HMS01800-RNAi`
- Representation: `PARKIN_DRIVER_DEFINED_NEURAL_TRANSFORM`
- No action-level scaling is used as the primary representation.

## 3. TH-GAL4 scope

The reviewed target population is defined by the TH-GAL4 driver scope and
contains 330 reviewed FlyWire root IDs. This is not a claim that FlyWire has a
direct Parkin-expression-specific annotation for those neurons.

## 4. Reviewed mapping summary

- Mapping level: `GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED`
- Target count: `330`
- Edge IDs: none; the transform resolves explicit root IDs through the pinned
  connectome ordering.
- Riemensperger's 342-ID set: not used.
- Mapping SHA256:
  `776274356c16eb458ef945e2a5153af4676bbddebef31cdb1b698f1d6aeaaf80`
- Target root-set SHA256:
  `e36b0210ea6d2d2b7225f62feba73ae5c9e6535565c8b936558d0eaaf04a2085`

## 5. Neural implementation commit

`be4b10a80755d9f7bad931f56b8a739bd64e3619`

- Model freeze SHA256:
  `eb370a25c00b39173272468e050e4ab917a0e99df0c3ee3ab73635868dfe916a`
- Prediction contract SHA256:
  `492ff39aa83f5acdaf2860522d4e99621bedb16a8e93778bfa8588b5a04c428e`

## 6. Neural transform source

- Source: `src/drosophila_pd_neural/parkin/transform.py`
- SHA256:
  `8f8fe415b9a2d4490783775ef9a4aa45a82bfe624f37d969d89eda1a7bac383b`

## 7. Operation level

`operation_level = NEURAL_PRE_ACTION`

For each connectome edge, the transform applies
`w_prime[e] = w[e] * (1 - p)` when the presynaptic root is in the reviewed
target set; all other weights remain unchanged. The transform returns a new
array and does not mutate the healthy input.

## 8. Healthy checkpoint

- Source: `../external/fly-brain-audit/data/plastic_weights.pt`
- SHA256:
  `d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691`
- Policy: immutable input; never overwritten.

## 9. Disease checkpoint grid

The grid manifest is
`research/validation/prospective/parkin_checkpoint_grid_manifest.json` with
SHA256:
`3bbf2a6ca62a952dc1ded8a0865a20e54e4cb60e16442632b232166f8399f04f`.

All positive levels use the same healthy source and the same reviewed mapping:

| Parameter | Checkpoint SHA256 |
| --- | --- |
| 0.25 | `dd2a4413d1aa4baed30df96884afdd030bac3a246d1bcc7a241baa955082cb8c` |
| 0.50 | `f682057bfff2bd523ba9a934970c9986e041ce44cb16fb8781ce2e9c5aebcff1` |
| 0.75 | `0b73e25620d10e56e293f859fb95c45630c7b798073b482d73f95a7d5c51e802` |
| 1.00 | `0ecf37ce96b6d4ea09b00204c3f01c6f41b6a2820b5f21170c6856760850e2b1` |

Parameter `0.0` is the healthy identity and does not require a second
checkpoint. The materialized checkpoint binaries are external/ignored
artifacts; their hashes and manifests are the tracked provenance.

## 10. Parameter grid

`[0.0, 0.25, 0.5, 0.75, 1.0]`

## 11. Parameter interpretation

Every value is a dimensionless computational perturbation level. No value is
interpreted as a Parkin knockdown percentage, dopamine-loss percentage,
biological severity, patient severity, or experimentally measured synaptic
loss. No single primary parameter is selected.

## 12. Seeds

`[0, 1, 2, 3, 4]`

The statistical unit is the seed. Frames are not statistical replicates.
Healthy and Parkin runs use paired identical seeds at every grid level.

## 13. Duration

Each planned rollout uses `100000` FlyGym steps and `10.0` seconds of physical
time.

## 14. Timestep

`0.0001` seconds, shared between healthy and Parkin conditions.

## 15. FlyGym, MuJoCo, and runtime provenance

- FlyGym: `2.1.0`
- MuJoCo: `3.9.0`
- Python: `3.12.10`
- PyTorch: `2.5.1+cu121`
- CUDA runtime recorded: `12.1`
- Clean runtime commit: `3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06`
- Clean runtime worktree: `E:/Drosophila_Parkinson/drosophila-pd-flygym-gate24-clean`
- Runner SHA256:
  `6c27c6ca9421f3b358ed8ce17e8192be586b6777ce52c2201530ec713db03059`

The dirty development worktree is not the runtime source for the prospective
experiment.

## 16. Primary virtual metric

`median_planar_speed_mm_s`

## 17. Primary validation axis

`LOCOMOTOR_IMPAIRMENT_DIRECTION`

The primary comparison is virtual Parkin versus virtual healthy control. It is
not a quantitative cross-assay claim against an incompatible paper endpoint.

## 18. Primary decision rule

For each nonzero parameter `p` and paired seed `s`, compute:

`paired_delta(p, s) = speed_parkin(p, s) - speed_healthy(s)`

A nonzero level is directionally impaired when the median paired delta across
seeds is less than zero and all required QC passes. The grid-level outcome is
`VIRTUAL_DIRECTIONAL_PREDICTION_SUPPORTED` only if every nonzero level passes.
Mixed directions produce `DIRECTIONAL_VALIDATION_INCONCLUSIVE`. If the grid
does not show consistent impairment, the outcome is
`DIRECTIONAL_VALIDATION_NOT_SUPPORTED`.

## 19. Secondary metrics

- `distance_traveled_mm`
- `displacement_mm`
- distance effect ratios
- magnitude of virtual speed reduction
- monotonicity across computational levels
- seed variability
- trajectory, contact, joint, and orientation QC

Secondary outcomes cannot override a failed primary direction rule.

## 20. Holdout firewall state

- Status: `SEALED`
- Holdout opened: `false`
- Numeric holdout values imported: `false`
- Used for parameter, model, seed, threshold, or post-hoc selection: `false`
- Firewall manifest SHA256:
  `0bb75ba2f4f8a11ab742d95f4889fc62b262add9c3482c582f4c2c5ce416aac6`

## 21. Failure policy

The experiment must not relabel a failed result. Disease speed greater than
or equal to healthy is `DIRECTIONAL_VALIDATION_NOT_SUPPORTED`; strong
between-seed variation is `DIRECTIONAL_VALIDATION_INCONCLUSIVE`. No parameter
is removed after observing results, and no tuning is performed using holdout
data.

## 22. Claim boundary

The allowed claim is:

> Parkin-specific intervention represented by a reviewed driver-defined neural
> perturbation and a preregistered directional computational validation
> protocol; no biological validation claim.

The following claims are forbidden: biological Parkinson validation, direct
Parkin-expression validation in FlyWire, clinical validation, diagnosis, drug
efficacy, and replacement of wet-lab experiments.

## 23. Required explicit scope statement

> The Parkin intervention is gene-specific, while the connectome target is
> TH-GAL4/driver-defined. The computational perturbation strength is not a
> measured Parkin knockdown percentage or biological severity.

## Reviewer action

Gate24D remains `WAITING_PROSPECTIVE_PREDICTION_REVIEW` until two real human
reviewers complete the signoff file. This packet does not authorize GPU,
simulation, calibration, holdout analysis, or tuning.
