# Gate29-H results insert for manuscript

## Results

We evaluated a preregistered class-level computational contrast using three conditions (`healthy_control`, `dopamine_class_level_burden_zero`, and `dopamine_class_level_full_burden`) and five matched simulation seeds per condition. The primary endpoint was `median_planar_speed_mm_s`, with the full-burden condition compared with healthy control within seed. All 15 jobs passed the prespecified integrity checks.

The full-burden minus healthy-control primary differences were exactly zero for all five seeds. The preregistered one-sided exact sign-flip test gave p = 1.00 (alpha = 0.05), the median paired difference was 0 mm/s, and the 95% percentile paired bootstrap interval was [0, 0] mm/s (10,000 resamples; analysis seed 29001). The preregistered trace endpoint, `brain_body_drive_mean_l2`, likewise showed zero paired difference for every seed.

## Interpretation and limitation

These data do not support the preregistered directional hypothesis within this computational protocol. The appropriate conclusion is a null result at the class-level computational scope, not evidence that dopamine depletion has no biological effect in Drosophila and not a biological Parkinson validation. No calibration, fitting, retuning, additional burden selection, or holdout analysis was performed after seeing the result.

The complete computational provenance is frozen under `GATE29H_RIEMENSPERGER_SCIENTIFIC_TRACE_V1`. The corresponding QC and statistical-analysis SHA256 values are recorded in the release packet checksum file.

## Suggested figure caption

**Figure X. Gate29-H primary endpoint.** Same-seed median planar speed for healthy control and full dopamine class-level burden (panel A) and paired full-minus-healthy differences (panel B). The two conditions overlap for all five seeds; every paired difference is zero, with exact one-sided sign-flip p = 1.00 and 95% bootstrap CI [0, 0]. This is a class-level computational result and does not establish biological Parkinson causality.
