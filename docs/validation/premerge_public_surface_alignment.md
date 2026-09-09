# Gate25-R2.1: Pre-merge public-surface alignment

## Scope

This review updates only current public-facing claim and status surfaces. It
does not change Gate24E evidence, raw metrics, model code, runtime provenance,
or historical Chen/Pozo artifacts.

## Files inspected

- `README.md`
- `docs/claims/current_claim_lock.md`
- `docs/claims/public_abstract.md`
- `docs/project_summary.md`
- `docs/limitations.md`
- `docs/claims/claim_safe_wording_guide.md`
- `docs/reproducibility/gate_25_reproducibility_freeze_report.md`
- Gate24E final decision, final evidence freeze, virtual prediction freeze,
  and raw relocation manifest

## Stale current-facing files found

The README and current claim lock still presented the earlier Chen/Pozo proxy
track as the active project conclusion. The public abstract and project
summary also needed a current Parkin status section so that a new reader
would not confuse historical proxy evidence with the closed Gate24E result.

## Files updated

- `README.md`: current Parkin status is now shown before historical material.
- `docs/claims/current_claim_lock.md`: rewritten as the active Gate24E claim
  policy with explicit forbidden claims.
- `docs/claims/public_abstract.md`: aligned with the negative Gate24E result.
- `docs/project_summary.md`: aligned with current Parkin validation and
  historical Chen/Pozo separation.
- Gate25-R2 inventory, checksum manifest, freeze manifest, and report were
  regenerated because these public surfaces are frozen reproducibility inputs.

## Historical files intentionally preserved

The historical Gate25 report, Chen calibration artifacts, Pozo holdout
artifacts, and historical Gate13/Gate14 evidence were not modified.

## Scientific invariants

- Gate24E status remains `GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE`.
- Scientific result remains `NEGATIVE_VALIDATION_RESULT`.
- Cross-assay decision remains `DIRECTIONAL_CROSS_ASSAY_DISCORDANCE`.
- Final evidence, virtual prediction, scientific plan, and raw tree checksums
  remain locked and unchanged.
- Raw rollout evidence remains external and checksum-preserved, not public Git
  data.
- No GPU, simulation, retuning, new scientific analysis, or holdout
  reinterpretation was performed.
