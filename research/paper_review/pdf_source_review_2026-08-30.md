# PDF-backed source review for calibration target approval

Date: 2026-08-30
Reviewer: ChatGPT-assisted PDF review
Branch: `review/target-approval`

## Executive decision

The uploaded PDFs strengthen the evidence audit, but they do **not** provide enough information to approve any calibration or holdout target yet.

Final status remains:

```text
WAITING_TARGET_DATA
```

No row in `calibration_targets/targets.csv` should be promoted to `review_status=approved` from this review alone.

## Uploaded PDFs reviewed

| File | Pages | SHA256 |
|---|---:|---|
| `riemensperger_2011_dopamine_deficiency.pdf` | 6 | `c7d38229a999caac81ffb1ff6fce2e14d767e9993d30a5dc4497e0f49a377330` |
| `pokrzywa_2017_alpha_syn_flytracker.pdf` | 21 | `722e4551cf039f4dcb3623e71c8e3e55ee0f3cef2b42174e08fcb294e2f014e4` |
| `pozo_2022_pink1_serotonin.pdf` | 16 | `b181d10535d860de97bc1008b38c191c66d70c58bbafe3c7283dc518b1158155` |
| `hwang_2013_dj1_dlp.pdf` | 17 | `bc2ff6abe060ed101184ea5ac4677579e15be3df6ff2ba5d62e504478c9acf84` |
| `godena_2014_lrrk2_microtubule.pdf` | 11 | `307887377ec688fe6178ed32369f73b4dd377d3b40ee17cd5c2ad015132717f4` |

`dumitrescu_2023_parkin_rnai.pdf` was not provided in this upload, so its prior `NOT_COMPARABLE` decision remains based on the existing full-text fallback and review table.

## Decision table after PDF review

| Paper / record | PDF-backed decision | Calibration target status | Reason |
|---|---|---|---|
| Riemensperger 2011 dopamine deficiency | `PENDING_HUMAN_SIGNOFF` | Do not approve | Walking speed is reported as a median, while the target is named `mean_planar_speed_mm_s`; no numeric variance compatible with an approved mean endpoint is available. |
| Pokrzywa 2017 alpha-synuclein FlyTracker | `PENDING_HUMAN_SIGNOFF` | Do not approve | Mean velocity values and time points are supported, but exact numeric SE/variance and a simple integer sample-size unit are still unresolved; vial/recording unit must not be coerced. |
| Pozo 2022 Pink1B9 locomotion | Distance: `PENDING_HUMAN_SIGNOFF`; activity time: `NOT_COMPARABLE` as speed | Do not approve | Distance is useful candidate evidence, but the statistic/spread and assay transfer must be formally decided. Activity time must not be converted into walking speed or pause fraction without a separate approved rule. |
| Hwang 2013 DJ-1 climbing | `VALIDATION_ONLY` | Do not approve | Negative geotaxis/climbing is not equivalent to current FlyGym flat-ground speed; numeric bar-center extraction remains manual and assay transfer is not approved. |
| Godena 2014 LRRK2 climbing/flight | `VALIDATION_ONLY` | Do not approve | LRRK2 motor-neuron climbing/flight evidence is biologically relevant, but current pipeline lacks approved climbing/flight target and VNC/motor-neuron root-ID provenance. |
| Dumitrescu 2023 parkin RNAi DAM | `NOT_COMPARABLE` | Do not approve | No PDF was uploaded here; existing decision remains that DAM beam-break activity is not equivalent to planar walking speed. |

## Per-paper PDF findings

### 1. Riemensperger 2011 dopamine deficiency

PDF evidence:

- Page 2 reports reduced walking speed in DTHgFS±; ple flies as `median = 7.8 mm/s`, compared with DTHg; ple `median = 10.8 mm/s` and WT `median = 15 mm/s`.
- The same paragraph reports distance covered over 15 min as medians: DTHgFS±; ple `193 cm`, DTHg; ple `425 cm`, WT `474 cm`.
- Page 5 Methods states that spontaneous locomotor behavior was tested in `2- to 5-d-old adult Drosophila`; walking speed and covered distance were computed from video recordings of individual flight-disabled flies walking freely for 15 min in an open arena.

Decision:

```text
PENDING_HUMAN_SIGNOFF
```

Why not approved:

1. Center statistic is median, not mean.
2. Current target name is `mean_planar_speed_mm_s`.
3. No approved numeric variance/spread compatible with the current target schema is available.
4. Open-arena flight-disabled walking is not automatically assay-equivalent to FlyGym flat-ground CPG walking.

Allowed future use:

- Candidate median-speed or distance evidence if the repository adds median/IQR-aware targets.
- Not approved for current speed calibration.

### 2. Pokrzywa 2017 alpha-synuclein FlyTracker

PDF evidence:

- Page 3 Methods reports newly eclosed female flies, 10 flies per vial.
- Page 4 Methods reports two independent sequences per vial whose results were averaged; each treatment was run in 3–10 independent vials.
- Page 6 Results reports measurements at days 1, 7, 16, 21, 30 and 42. Mean velocity decreases in alpha-synuclein flies from 5.6 mm/s to 2.5 mm/s, versus control from 6.0 mm/s to 5.0 mm/s, within the first three weeks.
- Figure 2 legend reports mean values with error bars as ±SE.

Decision:

```text
PENDING_HUMAN_SIGNOFF
```

Why not approved:

1. The PDF supports the trend and approximate endpoint values, but not a machine-readable numeric SE for the target row.
2. `sample_size` is not a single integer: the experimental unit includes vials, flies per vial, and repeated sequences.
3. The target row must not coerce `3–10 vials; 10 flies/vial` into one integer without a unit-of-analysis decision.
4. Vial FlyTracker locomotion may be useful, but assay-transfer to FlyGym flat-ground speed remains unresolved.

Allowed future use:

- Strong candidate for relative-change evidence.
- Can move toward calibration/holdout only after exact uncertainty and unit-of-analysis policy are documented.

### 3. Pozo 2022 Pink1B9 serotonin / locomotion

PDF evidence:

- Page 8 reports 28-day-old control and Pink1B9 mutant flies, treated or untreated with fluoxetine.
- Sample sizes are reported as n = 20 (`w1118`), 28 (`w1118 + Flx`), 21 (`Pink1B9`), and 23 (`Pink1B9 + Flx`).
- The figure caption states data are presented as interquartile range with maximum and minimum ranges.
- Untreated Pink1B9 values are: distance traveled `62.091 ± 61.288 mm`, activity time `11.865 ± 12.914 s`.
- Untreated control values are: distance traveled `323.326 ± 236.209 mm`, activity time `51.894 ± 32.409 s`.

Decision:

```text
PENDING_HUMAN_SIGNOFF for distance_traveled
NOT_COMPARABLE for activity_time as speed
```

Why not approved:

1. Distance traveled is a closer candidate for path length/distance validation, but current calibration target file does not define a distance target with approved transfer policy.
2. The reported spread must be preserved with its paper-defined statistic; do not convert it to SD/SE without review.
3. Activity time is not walking speed and must not be converted to pause fraction unless a separate mapping rule is approved.

Allowed future use:

- Candidate holdout for distance/path-length if the repository adds a dedicated distance endpoint and assay-transfer policy.
- Activity time remains validation context only.

### 4. Hwang 2013 DJ-1 / DLP climbing

PDF evidence:

- Figure 5E compares climbing abilities of WT, DLP, DJ-1bex54 and double mutants.
- The Figure 5E caption states climbing abilities of 5-day-old flies were tested; ANOVA/Tukey HSD analysis used n ≥ 12 and all data are expressed as means ± s.e.
- Methods state that 10 male flies were transferred into a climbing vial, acclimated for 1 h, tapped to the bottom, and the number climbing to the top within 4 s was counted. Ten trials were conducted per group, experiments repeated at least 10 times, and climbing score was expressed as a percentage.

Decision:

```text
VALIDATION_ONLY
```

Why not approved:

1. Assay is negative geotaxis/climbing, not flat-ground walking speed.
2. Current FlyGym target schema has no approved climbing endpoint.
3. Numeric center values still require manual figure extraction.
4. Even with mean ± SE, it cannot be used as `mean_planar_speed_mm_s`.

Allowed future use:

- Validation-only phenotype evidence for DJ-1 locomotor impairment.
- Possible future target if a climbing simulation/metric is implemented and figure extraction is independently reviewed.

### 5. Godena 2014 LRRK2 / microtubule acetylation

PDF evidence:

- Page 2 reports that LRRK2-R1441C and LRRK2-Y1699C inhibit mitochondrial transport in Drosophila motor neurons.
- Adult flies expressing LRRK2/Lrrk variants in motor neurons were assayed for climbing and flight ability.
- LRRK2-R1441C and LRRK2-Y1699C caused significant decreases in both climbing and flight ability.
- Figure 1c describes locomotion assays for climbing and flight behavior of LRRK2 variants expressed in motor neurons by D42-GAL4, with sample sizes: Ctrl 95, WT 141, R1441C 93, Y1699C 122, G2019S 59 animals.
- Later TSA rescue assays include sample sizes for R1441C Ctrl 43 and Y1699C Ctrl 59 in the relevant climbing charts.
- Methods state that climbing assays after drug treatment were performed after 5 days; animals were 6–7 days old.

Decision:

```text
VALIDATION_ONLY
```

Why not approved:

1. The paper is highly relevant for LRRK2 locomotor impairment, but the endpoint is climbing/flight, not flat-ground speed.
2. The intervention scope is motor-neuron/VNC-oriented, while the current root-ID mapping audit is brain-only or not reviewed for this scope.
3. Sample sizes are available, but this does not solve assay incompatibility.
4. Current calibration file lacks an approved climbing/flight target type.

Allowed future use:

- Strong validation-only evidence for LRRK2 locomotor impairment and rescue.
- Could become a future climbing/flight target only after assay implementation and motor-neuron/VNC provenance are added.

## Root-ID mapping implications

The PDF review does not change the root-ID conclusion:

- Dopamine-class IDs remain exploratory/class-level only.
- Alpha-synuclein nSyb-Gal4 is broad pan-neuronal expression, not a reviewed root-ID set.
- TH-GAL4/parkin RNAi is a driver class, not gene-specific root-ID evidence.
- Pink1B9/DJ-1beta are organism-level behavioral mutants unless a paper supplies a cell-specific intervention map.
- LRRK2 D42-GAL4 uses motor-neuron scope; current brain-only annotations must not be substituted for VNC/motor-neuron mapping.

## Calibration readiness after PDF review

Still blocked by:

1. No approved calibration target.
2. No approved holdout target.
3. Median/mean mismatch for Riemensperger.
4. Missing numeric SE/variance for Pokrzywa.
5. Assay-transfer unresolved for open arena, vial tracking, open-field distance, DAM activity, climbing, and flight.
6. No approved root-ID provenance for gene-specific interventions.

## Recommended next steps

1. Keep `calibration_targets/targets.csv` unchanged; do not approve current rows.
2. Add a target schema that supports `median` / `IQR` / `quartile` evidence, or keep Riemensperger pending.
3. Extract Pokrzywa numeric SE from the original figure/supplement using a documented manual digitization protocol if no table provides it.
4. Add distance/path-length targets if Pozo is to be used quantitatively; do not force it into speed.
5. Add climbing/flight metrics before using Hwang or Godena as quantitative targets.
6. Keep Dumitrescu as non-comparable for speed until a DAM activity endpoint exists.
7. Re-run `scripts/audit_calibration_targets.py` only after a human reviewer updates target rows with full provenance.

## Final status

```text
WAITING_TARGET_DATA
```

This is the correct scientific result. The PDFs improve provenance, but they do not justify calibration or holdout approval yet.
