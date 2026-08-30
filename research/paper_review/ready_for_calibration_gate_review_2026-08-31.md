# READY_FOR_CALIBRATION gate review

Date: 2026-08-31
Reviewer: ChatGPT-assisted adjudication review
Branch: `review/target-decision-matrix-2026-08-30`

## Executive decision

The requested target adjudication was re-checked against the supplied PDFs and the current repository target policy. The gate **cannot** be advanced to `READY_FOR_CALIBRATION` without inventing or over-interpreting missing evidence.

Final status remains:

```text
WAITING_TARGET_DATA
```

This is a scientific-data blocker, not a software failure.

## Why READY_FOR_CALIBRATION is not justified yet

The audit requires at least:

1. one approved `allocation=calibration` target;
2. one approved `allocation=holdout` target;
3. numeric value;
4. numeric uncertainty;
5. numeric sample size with a valid unit of analysis;
6. reviewer and review date;
7. provenance;
8. approved assay transfer.

The supplied PDFs support several promising candidates, but they do not satisfy the full approval gate.

## Candidate-by-candidate adjudication

### 1. Pokrzywa alpha-synuclein — calibration candidate, not approved

Decision:

```text
PENDING_HUMAN_SIGNOFF
allocation=calibration_candidate
```

PDF-supported facts:

- Genotype: `w; +; UAS-Hsap/nSyb-Gal4` for alpha-synuclein expressing flies.
- Sex: female.
- Assay: FlyTracker locomotion tracking in vials.
- Time points: days 1, 7, 16, 21, 30, 42.
- Endpoint: mean velocity, mm/s.
- Reported values: alpha-synuclein mean velocity drops from 5.6 mm/s to 2.5 mm/s, while control drops from 6.0 mm/s to 5.0 mm/s within the first 3 weeks.
- Figure 2 legend states mean values and error bars as ± SE.
- Methods report 10 female flies per vial; recordings from each vial were acquired in two independent sequences and averaged; each treatment was run in 3–10 independent vials.

Blockers:

1. Numeric SE is not available in the PDF text or uploaded source.
2. Exact numeric SE would require figure digitization or a supplementary numeric table.
3. The unit of analysis is not a simple fly count: it is vial/recording based, with 10 flies per vial and 3–10 independent vials.
4. The current evidence does not justify converting `3–10 vials` into a single integer sample size.
5. Assay transfer from vial FlyTracker to FlyGym `mean_planar_speed_mm_s` still requires explicit research-lead signoff.

Do not approve this target until either the original S1 table or a documented digitization file provides a numeric SE and an approved `sample_size`/`sample_unit`.

### 2. Pozo Pink1B9 — holdout candidate, not approved

Decision:

```text
PENDING_HUMAN_SIGNOFF
allocation=holdout_candidate
```

PDF-supported facts:

- Genotype: `Pink1B9`.
- Age: 28 days.
- Assay: open-field locomotor tracking.
- Endpoint: distance traveled in mm.
- Pink1B9 distance: `62.091 ± 61.288 mm`, n = 21 flies.
- Control distance: `323.326 ± 236.209 mm`, n = 20 flies.
- Figure 3 caption states data are presented as interquartile range with maximum and minimum ranges.

Blockers:

1. This is distance, not walking speed. It must remain `distance_traveled_mm` or a path-length/distance endpoint.
2. The `±` value must be preserved as paper-reported spread under the paper's IQR/min-max wording; do not relabel it as SD or SE.
3. Holdout approval requires explicit confirmation that the simulation artifact exports a compatible distance/path-length metric for the same comparison.
4. Assay transfer for distance/path-length is still `TRANSFER_REVIEW_REQUIRED`.

Pozo is the best holdout candidate, but it should not be approved until the distance endpoint and spread policy are signed off.

### 3. Riemensperger dopamine-deficiency — median candidate, not approved

Decision:

```text
PENDING_HUMAN_SIGNOFF
```

PDF-supported facts:

- Age: 2- to 5-day-old adult Drosophila.
- Assay: spontaneous locomotor behavior; individual flight-disabled flies walking freely for 15 min in an open arena.
- Walking speed: DTHgFS±; ple `median = 7.8 mm/s`, DTHg; ple `median = 10.8 mm/s`, WT `median = 15 mm/s`.
- Distance covered in 15 min: DTHgFS±; ple `median = 193 cm`, DTHg; ple `median = 425 cm`, WT `median = 474 cm`.

Blockers:

1. The paper reports median, not mean.
2. Do not place this in `mean_planar_speed_mm_s`.
3. No numeric IQR/range suitable for the current target row is available.
4. Median-compatible simulation and loss handling must be confirmed before approval.

### 4. Hwang DJ-1 — validation-only

Decision:

```text
VALIDATION_ONLY
```

Reason:

The paper supports DJ-1-related locomotive dysfunction through a 5-day-old male negative-geotaxis/climbing assay, with mean ± s.e. and n ≥ 12. However, the current pipeline does not have an approved FlyGym climbing endpoint. Do not convert this to planar speed.

### 5. Godena LRRK2 — validation-only

Decision:

```text
VALIDATION_ONLY
```

Reason:

The paper supports LRRK2 Roc-COR mutation locomotor deficits in climbing/flight assays and motor-neuron/VNC scope. The current pipeline lacks a climbing/flight endpoint and lacks reviewed motor-neuron/VNC root-ID provenance. Do not convert to planar speed.

### 6. Dumitrescu Parkin — not comparable for speed

Decision:

```text
NOT_COMPARABLE
```

Reason:

DAM beam-break activity is useful age-dependent phenotype context, but it is not equivalent to `mean_planar_speed_mm_s`. It should not be used as a walking-speed calibration target.

## Root-ID mapping adjudication

No new gene-specific root IDs are approved by this review.

Current safe decisions remain:

- dopamine deficiency: class-level exploratory only;
- alpha-synuclein: pan-neuronal nSyb-Gal4 is not a reviewed root-ID set;
- parkin: TH-GAL4 class scope without reviewed root-ID export;
- Pink1B9: organism-level mutant, not a cell-specific intervention;
- DJ-1: not mappable from paper;
- LRRK2: motor-neuron/VNC scope not covered by current brain-only mapping.

Do not infer root IDs from gene names, driver names, or phenotype labels.

## What would be required to reach READY_FOR_CALIBRATION

Minimum evidence package:

### Calibration target package

For Pokrzywa:

- numeric SE for alpha-synuclein day 21 mean velocity;
- numeric SE for matched control day 21 mean velocity, if delta-literature computation requires paired control uncertainty;
- approved numeric sample size and sample unit, preferably independent vial count for the exact group/time point;
- explicit `assay_transfer=allowed` for FlyTracker vial mean velocity → FlyGym `mean_planar_speed_mm_s`;
- human reviewer and date.

### Holdout target package

For Pozo:

- explicit endpoint approval for `distance_traveled_mm` or matching simulation path-length metric;
- explicit policy for storing `61.288` and `236.209` as paper-reported IQR/min-max spread, without relabeling as SD/SE;
- approved `assay_transfer=allowed` for open-field distance → simulation distance/path-length;
- human reviewer and date.

## Final recommendation

Do not update `calibration_targets/targets.csv` to `approved` in this PR. The correct next artifact is one of:

1. an original supplementary table from Pokrzywa containing numeric SE/sample sizes; or
2. a documented manual digitization CSV with figure coordinates, calibration axes, extracted SE values, reviewer signoff, and uncertainty notes; plus
3. a signed distance-endpoint policy for Pozo.

Until then:

```text
WAITING_TARGET_DATA
```

is the correct and defensible scientific status.
