# Target decision matrix review

Date: 2026-08-30
Reviewer: Tuan Le / ChatGPT-assisted PDF audit
Branch: `review/target-decision-matrix-2026-08-30`

## Executive decision

The target matrix was reviewed from the PDFs supplied in the conversation and the existing repository policy. The repository should remain:

```text
WAITING_TARGET_DATA
```

Do **not** run disease simulation, calibration, holdout validation, or literature-comparison execution yet.

## Files changed in this review

1. Created `research/paper_review/target_decision_matrix.csv`.
2. Updated `calibration_targets/candidate_targets_reviewed.csv` to refine candidate statuses from the uploaded PDFs.
3. Added this review report.

`calibration_targets/targets.csv` was intentionally not promoted to approved because no candidate satisfies all approval requirements.

## Priority decisions

| Candidate | Result | Reason |
|---|---|---|
| Pokrzywa alpha-synuclein day 21 speed | `PENDING_HUMAN_SIGNOFF`; `calibration_candidate` only | The PDF supports age/timepoints and mean velocity decline, but numeric SE is not available from text and unit of analysis is `3-10 independent vials`, not a simple fly count. |
| Pozo Pink1B9 day 28 distance | `PENDING_HUMAN_SIGNOFF`; `holdout_candidate` only | The PDF supports the distance value, n, and spread description, but this is a distance endpoint, not speed. It requires explicit distance/path-length assay-transfer signoff. |
| Riemensperger dopamine-deficiency speed | `PENDING_HUMAN_SIGNOFF` | The PDF reports median speed, not mean speed; no numeric spread compatible with approved target schema is available. |
| Hwang DJ-1 climbing | `VALIDATION_ONLY` | The PDF supports a 5-day-old male climbing assay with mean +/- s.e., but current pipeline has no approved climbing endpoint. |
| Godena LRRK2 climbing/flight | `VALIDATION_ONLY` | The PDF supports LRRK2 climbing/flight locomotor deficits, but endpoint is climbing/flight and neural scope is motor-neuron/VNC, not approved in the current root-ID mapping. |
| Dumitrescu parkin DAM activity | `NOT_COMPARABLE` for speed | DAM beam-break activity is not planar walking speed. The supplied file is a supplement, so existing full-text fallback status remains non-comparable for speed. |

## PDF-backed evidence summary

### Pokrzywa 2017

- Female flies, 10 flies per vial.
- Two sequences per vial were averaged.
- Each treatment was run in 3-10 independent vials.
- Locomotion was measured at days 1, 7, 16, 21, 30, and 42.
- Mean velocity fell from 5.6 to 2.5 mm/s in alpha-synuclein flies and from 6.0 to 5.0 mm/s in controls within the first 3 weeks.
- Figure 2 reports mean values and error bars as +/- SE, but exact numeric SE is not available in the extracted text.

Decision: `PENDING_HUMAN_SIGNOFF`.

Required before approval:

1. Numeric SE or other numeric uncertainty.
2. Explicit unit-of-analysis decision for vial-level data.
3. Assay transfer from vial FlyTracker to FlyGym flat-ground speed.
4. `allocation=calibration` only after the above are approved.

### Pozo 2022

- Open-field locomotor tracking at day 28.
- Sample sizes: n=20 w1118, n=28 w1118+Flx, n=21 Pink1B9, n=23 Pink1B9+Flx.
- Figure 3B/C caption states data are presented as interquartile range with maximum and minimum ranges.
- Untreated Pink1B9 distance: 62.091 +/- 61.288 mm.
- Untreated control distance: 323.326 +/- 236.209 mm.
- Untreated Pink1B9 activity time: 11.865 +/- 12.914 s.
- Untreated control activity time: 51.894 +/- 32.409 s.

Decision:

- Distance: `PENDING_HUMAN_SIGNOFF`, possible `holdout_candidate`.
- Activity time: `NOT_COMPARABLE_AS_SPEED`.

Required before approval:

1. Distance/path-length endpoint must be accepted as a separate endpoint from speed.
2. Assay transfer must be approved for distance, not speed.
3. Spread policy must preserve the paper's IQR/max-min reporting.
4. `allocation=holdout` only after the above are approved.

### Riemensperger 2011

- PDF reports DTHgFS+/-; ple walking speed as median 7.8 mm/s.
- Control medians: DTHg; ple 10.8 mm/s and WT 15 mm/s.
- Distance over 15 min is also median-reported: DTHgFS+/-; ple 193 cm, DTHg; ple 425 cm, WT 474 cm.
- Methods report 2- to 5-day-old adults, individual flight-disabled flies, 15 min open arena.

Decision: `PENDING_HUMAN_SIGNOFF`.

Required before approval:

1. Median-aware target schema and simulation metric.
2. Numeric IQR/range or approved multi-bound spread representation.
3. Do not approve as `mean_planar_speed_mm_s`.

### Hwang 2013

- Figure 5E uses 5-day-old flies.
- Climbing assay is male flies.
- Caption reports n >= 12 and mean +/- s.e.
- Methods: 10 male flies per test vial, 1 h acclimation, tap to bottom, count flies climbing to top within 4 s; ten trials per group; repeated at least 10 times.

Decision: `VALIDATION_ONLY`.

Reason: no approved FlyGym climbing metric, and exact bar centers are not machine-readable.

### Godena 2014

- LRRK2-R1441C and LRRK2-Y1699C inhibit Drosophila motor-neuron mitochondrial transport and cause significant decreases in climbing and flight.
- Fig. 1c sample sizes include R1441C n=93 and Y1699C n=122 for locomotion assays.
- Fig. 6C/Supplementary Fig. 3C rescue-related climbing charts include R1441C Ctrl n=43 and Y1699C Ctrl n=59.
- Methods state treated animals were tested after 5 days and were 6-7 days old.

Decision: `VALIDATION_ONLY`.

Reason: current project has no approved climbing/flight endpoint and no motor-neuron/VNC root-ID provenance.

### Dumitrescu 2023

Decision remains `NOT_COMPARABLE` for speed.

Reason: DAM infrared beam-break activity is not planar walking speed. Keep only as age-dependent activity context unless a DAM endpoint is implemented.

## Root-ID mapping decision

No new root IDs were inferred from the PDFs.

- Dopamine-deficiency remains class-level/exploratory only.
- Alpha-synuclein/nSyb-GAL4 remains broad pan-neuronal expression without reviewed root-ID export.
- Parkin TH-GAL4 remains a driver class, not a gene-specific root-ID set.
- Pink1B9 remains organism-level mutant scope.
- DJ-1beta climbing evidence does not specify cell-specific root-ID manipulation.
- LRRK2 D42-GAL4 is motor-neuron/VNC scope, while current catalog is brain-only.

Therefore root-ID statuses remain `PENDING`, `NOT_MAPPABLE`, or class-level exploratory as appropriate. Do not infer root IDs.

## Why `targets.csv` was not approved

`targets.csv` can only be updated to approved when all are present:

- numeric uncertainty;
- numeric sample size with a valid unit of analysis;
- reviewer and review date;
- assay transfer allowed;
- allocation `calibration` or `holdout`;
- provenance from PDF/table/figure;
- no statistic mismatch.

Current blockers:

1. Pokrzywa: missing numeric SE and simple approved sample-size unit.
2. Pozo: distance endpoint not yet accepted as calibration/holdout endpoint by audit; spread policy needs signoff.
3. Riemensperger: median/mean mismatch and missing numeric spread.
4. Hwang/Godena: climbing/flight validation-only.
5. Dumitrescu: DAM not comparable to speed.

## Expected audit result

If `scripts/audit_calibration_targets.py` is run after this PR without changing `targets.csv`, expected status is still:

```text
WAITING_TARGET_DATA
```

This is correct and not a software failure.
