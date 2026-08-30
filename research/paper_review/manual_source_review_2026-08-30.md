# Manual source review for calibration target approval

Date: 2026-08-30
Reviewer: ChatGPT-assisted source review
Branch: `review/target-approval`

## Executive decision

Current calibration readiness remains:

```text
WAITING_TARGET_DATA
```

No row in `calibration_targets/targets.csv` should be promoted to `review_status=approved` yet.

This review checked the candidate literature records against the available public full text / article record and the existing repository review tables. The local `temporary/paper_pdf/` files are not in the GitHub repository because `temporary/`, PDFs, and generated/raw data are ignored. Therefore, this file records a source-review decision and the remaining evidence gaps; it does not certify a PDF-level extraction as complete.

## Decision table

| Paper / record | Current use | Source-review decision | Reason |
|---|---|---|---|
| Riemensperger 2011 dopamine deficiency | Candidate speed target | `PENDING_HUMAN_SIGNOFF` | Figure 2A reports spontaneous open-arena walking speed as median values. The candidate value 7.8 mm/s is a median, not a mean, and there is no approved numeric variance compatible with `mean_planar_speed_mm_s`. |
| Pokrzywa 2017 alpha-synuclein FlyTracker | Candidate speed evidence | `PENDING_HUMAN_SIGNOFF` | The paper reports mean velocity decline from 5.6 to 2.5 mm/s for alpha-synuclein and 6.0 to 5.0 mm/s for controls over the first three weeks. Exact numeric SE/variance and endpoint-specific extraction remain unresolved. |
| Pozo 2022 Pink1B9 distance/activity | Candidate distance evidence only | `PENDING_HUMAN_SIGNOFF` for distance; `NOT_COMPARABLE` for activity time | The paper reports 28-day open-field distance and activity time. Distance may be a holdout candidate only after statistic/spread and assay-transfer review. Activity time must not be converted into walking speed or pause fraction without a documented rule. |
| Dumitrescu 2023 parkin RNAi DAM | Not a speed target | `NOT_COMPARABLE` | DAM beam-break activity is not equivalent to FlyGym planar walking speed. It may be qualitative/validation context only. |
| Hwang 2013 DJ-1 climbing | Validation context | `VALIDATION_ONLY` | Negative geotaxis/climbing is not equivalent to flat-ground speed in the current pipeline. Numeric bar centers require manual figure extraction. |
| Godena 2014 LRRK2 climbing/flight | Validation context | `VALIDATION_ONLY` | Climbing/flight and motor-neuron/VNC scope require separate assay and root-ID provenance. Do not use as a speed calibration target. |

## Per-paper notes

### 1. Riemensperger 2011 dopamine deficiency

Repository target currently stores:

- `metric=mean_planar_speed_mm_s`
- `value=7.8`
- `unit=mm/s`
- `variance_type=median`
- `variance=` blank
- `sample_size=13`
- `review_status=pending`

Source check conclusion:

- The locomotion endpoint is spontaneous walking in an open arena, not FlyGym flat-ground CPG locomotion.
- The reported center for the dopamine-deficient group is a median value of 7.8 mm/s.
- The source also reports DTHg;ple at 10.8 mm/s and WT at 15 mm/s as medians.
- PubMed/figure metadata describes box-and-whisker representation with median, mean marker, quartiles, quantiles, and extremes, but the candidate target does not have a numeric variance field compatible with an approved mean endpoint.

Decision:

```text
PENDING_HUMAN_SIGNOFF
```

Do not approve unless a policy is added for median-based targets or the exact mean/spread can be extracted and reviewed.

### 2. Pokrzywa 2017 alpha-synuclein FlyTracker

Repository target currently stores only one candidate value:

- `metric=mean_planar_speed_mm_s`
- `value=2.5`
- `unit=mm/s`
- `variance_type=mean_SE`
- `variance=` blank
- `sample_size=3-10 vials; 10 flies/vial`
- `review_status=pending`

Source check conclusion:

- The paper uses FlyTracker locomotion tracking in vials.
- It reports mean velocity declining from 5.6 mm/s to 2.5 mm/s for alpha-synuclein flies and from 6.0 mm/s to 5.0 mm/s for controls within the first three weeks.
- The source text supports the trend and approximate endpoints but not the exact numeric SE required for an approved calibration target in this repository.
- The sample unit is vial/recording/flies, not a single simple integer fly count. Do not coerce `3-10 vials; 10 flies/vial` into a single sample size.

Decision:

```text
PENDING_HUMAN_SIGNOFF
```

This paper is promising for within-paper relative-change evidence, but it still needs exact age endpoint, uncertainty extraction, and an assay-transfer decision.

### 3. Pozo 2022 Pink1B9 serotonin / locomotion

Repository review records include:

- Pink1B9 distance at Day 28: 62.091 mm; spread 61.288; n=21 flies.
- Control distance at Day 28: 323.326 mm; spread 236.209; n=20 flies.
- Pink1B9 activity time: 11.865 s; spread 12.914.
- Control activity time: 51.894 s; spread 32.409.

Source check conclusion:

- The paper directly reports a decrease in distance traveled and activity time in untreated 28-day-old Pink1B9 flies compared with controls.
- Distance traveled is closer to a FlyGym path/displacement endpoint than walking speed, but the current calibration target table does not yet define an approved transfer policy for this assay and statistic.
- Activity time is not walking speed and should not be mapped to pause fraction without a separate, approved conversion rule.
- The spread label remains unresolved in the review files; do not convert it to SD/SE unless confirmed.

Decision:

```text
PENDING_HUMAN_SIGNOFF for distance
NOT_COMPARABLE for activity_time as speed
```

Pozo may become a holdout or distance-based validation target after statistic/spread and assay-transfer policy are approved.

### 4. Dumitrescu 2023 parkin RNAi DAM activity

Source check conclusion:

- The paper reports locomotor inhibition of approximately 30% in young parkin-RNAi flies and 85% in older flies.
- The activity endpoint comes from Drosophila Activity Monitor infrared beam-break counts, not planar walking speed in mm/s.
- The endpoint is valuable biological context for age-dependent locomotor impairment, but it is not a calibration target for `mean_planar_speed_mm_s`.

Decision:

```text
NOT_COMPARABLE
```

Keep as qualitative or validation context only.

### 5. Hwang 2013 DJ-1 climbing

Source check conclusion:

- The paper reports 5-day-old DJ-1beta climbing ability using negative geotaxis and mean ± SE style reporting.
- The figure center is not provided as a machine-readable numeric value in the text record.
- The current FlyGym pipeline is flat-ground locomotion; no approved climbing assay transfer is present.

Decision:

```text
VALIDATION_ONLY
```

Do not approve as a walking-speed calibration target.

### 6. Godena 2014 LRRK2 locomotor deficits

Source check conclusion:

- The paper reports climbing and flight deficits in Drosophila expressing LRRK2 variants in motor neurons.
- The assay is not current FlyGym flat-ground speed.
- Motor-neuron/VNC scope is not represented by the current brain-only root-ID mapping table.

Decision:

```text
VALIDATION_ONLY
```

Do not approve for calibration until there is a climbing assay implementation and reviewed neuron-scope/root-ID provenance.

## Assay-transfer policy from this review

A candidate can only move toward calibration when all are true:

1. Same or explicitly mapped locomotor concept.
2. Same or convertible unit with written transfer rule.
3. Statistic type is compatible with the target metric.
4. Numeric uncertainty is present and its type is known.
5. Sample size is numeric and unit of analysis is defined.
6. Age, sex, genotype, assay duration, and condition are recorded.
7. `reviewer`, `review_date`, and `allocation=calibration|holdout` are present.
8. Calibration and holdout are separated; the same target is not used for both.

## Recommended next data work

1. Add support for median/IQR targets or keep Riemensperger as pending.
2. Extract exact numeric SE from Pokrzywa Figure 2A or supplementary source; otherwise do not approve.
3. Consider adding a distance/path-length target type for Pozo rather than forcing it into speed.
4. Do not use DAM, climbing, or activity time as speed calibration targets.
5. Keep root-ID mapping conservative: current mappings are class-level/exploratory or not mappable, not gene-specific intervention maps.

## Final status

```text
WAITING_TARGET_DATA
```

This is a correct scientific status, not a software failure.
