# Gate28B virtual assay adapter report

**Status:** `GATE28B_VIRTUAL_ASSAY_ADAPTER_ENGINEERING_COMPLETE`
**Human review:** `WAITING_GATE28B_HUMAN_REVIEW`

## 1. Purpose

Gate28B implements a disease-agnostic computational observation layer and,
when explicitly requested, benchmarks healthy rollout duration scaling. It
does not implement or validate a disease mechanism.

## 2. Relationship to Gate28A

The adapter references the human-closed Gate28A contracts without modifying
them. Gate24E, Gate25, Gate26, and Gate28A scientific content remains frozen.
The first track remains
`RIEMENSPERGER_2011_DOPAMINE_FUNCTIONAL_DEFICIENCY`; Pozo is not a future
sealed holdout and alpha-synuclein LOSO allocation remains unfrozen.

## 3. Assay observation architecture

Raw timestamps and thorax XY positions are mapped explicitly into an immutable
`TrajectoryData`. The `RIEMENSPERGER_2011_OPEN_ARENA_V1` adapter converts one
trajectory into one run-level observation. Disease parameters are absent from
the assay package.

## 4. Statistical hierarchy

The contract separates `LEVEL_0_FRAME`, `LEVEL_1_RUN`,
`LEVEL_2_COMPUTATIONAL_GROUP`, and `LEVEL_3_BIOLOGICAL_STUDY`. Frames, physics
steps, joints, and segments are not replicates. A unique simulation seed may
be a computational replicate. Per-run median framewise speed is not silently
equated to a paper group median.

## 5. Riemensperger adapter

The frozen source contract describes individual flight-disabled flies walking
in a horizontal open arena for 15 minutes. The adapter computes native virtual
distance, displacement, path-derived mean speed, and explicitly named median
framewise speed.

## 6. Known source gaps

The available primary PDF does not report the frame rate, movement threshold,
exclusion rule, or exact per-fly speed algorithm. Therefore:

- status: `RIEMENSPERGER_SPEED_STATISTICAL_HIERARCHY_REQUIRES_SOURCE_REVIEW`;
- paper assay equivalence: `false`;
- strongest claim: `VIRTUAL_ASSAY_ADAPTER_IMPLEMENTED`.

## 7. Metric definitions

- Interval speed is planar step distance divided by its positive time delta.
- Distance is the sum of interval distances.
- Displacement is the norm between first and last XY positions.
- Per-run mean speed is total distance divided by observed duration.
- Median framewise speed is descriptive and is not a paper-level alias.
- Threshold-dependent activity metrics remain
  `NOT_COMPUTED_MISSING_MOVEMENT_THRESHOLD`.

## 8. Window semantics

Windows have explicit start/end bounds. Boundary positions use exact samples
or deterministic linear interpolation. Out-of-range windows fail with
`OBSERVATION_WINDOW_EXCEEDS_ROLLOUT`; no silent truncation occurs.

## 9. Segmented aggregation

Contiguous segments share the boundary sample. Additive metrics are summed,
and rate metrics pool numerator/denominator. Median-of-medians is marked
`INVALID_AS_GENERAL_GLOBAL_MEDIAN_AGGREGATOR`. A segment is never a replicate.

## 10. Synthetic validation

Deterministic stationary, constant-speed, piecewise-speed, turning, irregular
timestamp, and invalid-NaN fixtures test analytic metrics and failure paths.
Current result: `PASS`.

## 11. Runtime schema audit

Exactly one historical Gate26 healthy seed is inspected read-only. The audited
runtime keys map `timestamp_s` to canonical time and `thorax` to planar XY.
Unknown optional-field units remain `UNKNOWN_REQUIRES_RUNTIME_REVIEW`. Raw data
is neither changed nor copied into Git.

## 12. Technical duration benchmark

The only authorized execution is Healthy, no perturbation, technical seed
`9101`, and durations `0.5, 1.0, 2.0, 5.0 s`. This is engineering evidence,
not a scientific replicate.

| Duration (s) | Steps | Wall clock (s) | Steps/s | Bytes | Bytes/step |
|---:|---:|---:|---:|---:|---:|
| 0.5 | 5000 | 67.518 | 74.055 | 28023873 | 5604.775 |
| 1.0 | 10000 | 92.443 | 108.175 | 56050266 | 5605.027 |
| 2.0 | 20000 | 167.538 | 119.376 | 112024563 | 5601.228 |
| 5.0 | 50000 | 346.003 | 144.507 | 279739173 | 5594.783 |

## 13. 15-minute engineering extrapolation

- Median wall-clock projection: `79295.162 s`.
- Conservative wall-clock projection: `121531.733 s`.
- Median storage projection: `50427012375 bytes`.
- Conservative storage projection: `50445239400 bytes`.
- Label: `ENGINEERING_EXTRAPOLATION_ONLY`.
- Direct 15-minute execution: `DIRECT_15_MINUTE_EXECUTION_NOT_TESTED`.

## 14. What is NOT validated

This gate does not reproduce the Riemensperger assay, validate a 15-minute
assay, reproduce Parkinson phenotypes, validate dopamine biology, establish
biological equivalence, calibrate parameters, fit a model, or run disease
jobs.

## 15. Implications for Gate29 and Gate31

Gate29 may review unresolved assay semantics and duration engineering evidence.
Gate31 must compare like with like, use scientific seeds distinct from `9101`,
and obtain a separately reviewed long-horizon protocol before replication.

## 16. Claim boundaries

Allowed: "Gate28B implements and validates a computational assay-observation
layer for virtual Drosophila locomotion and characterizes the engineering
scaling of longer healthy embodied rollouts." Segmented metric consistency
does not establish biological equivalence to one continuous 15-minute assay.

## 17. Human review status

The reviewer template remains `PENDING_HUMAN_REVIEW`; no field is auto-signed.
Exact next action after engineering completion:
`HUMAN_REVIEW_GATE28B_VIRTUAL_ASSAY_ADAPTER`.
