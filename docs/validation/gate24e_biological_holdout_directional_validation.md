# Gate 24E-S4K: Biological holdout directional validation

## Scope

This gate opened the authorized biological holdout exactly once after the
blinded virtual prediction was frozen. It performs directional cross-assay
validation only. No GPU, FlyGym simulation, retuning, parameter selection, or
numeric cross-assay conversion was performed.

## Frozen virtual prediction

- Freeze SHA256: `f44e9ad10b9fc4795ae2173d3e8b27fc9ea0d8202925bfc08cdcc72d06b00863`.
- Frozen grid decision: `DIRECTIONAL_VALIDATION_NOT_SUPPORTED`.
- Authorization commit: `648e0dbc5a845be4186ce76a6130b95aa06842ce`.
- Prediction was frozen before the holdout was opened: `true`.

The frozen virtual result did not support the preregistered locomotor
impairment direction. That result is retained and is not relabeled after
opening the holdout.

## Human authorization

- Status: `VIRTUAL_PREDICTION_FREEZE_REVIEW_APPROVED`.
- Decision: `APPROVED_TO_OPEN_GATE24E_BIOLOGICAL_HOLDOUT`.
- Reviewers: `Tuan Le` and `To Dang Minh Tuan`.
- Review date: `2026-09-09`.
- Opened at UTC: `2026-09-09T02:48:00.118674Z`.

## Held-out biological evidence

- Source: Cackovic et al. 2018, DOI `10.3389/fncel.2018.00039`, PMID `29497364`.
- Assay: `negative geotaxis climbing with vertical infrared activity monitor`.
- Endpoint: `climbing position and climbing deficit`.
- Age context: `5; 10; 20`.
- Biological direction: `BIOLOGICAL_IMPAIRMENT_SUPPORTED`.
- Evidence type: `SUMMARY_LEVEL_VALIDATION_EVIDENCE`.
- Raw data available in the repository: `false`.

The preserved source package supports a Parkin loss-of-function climbing
impairment direction at summary level. It does not provide raw individual
values in this repository, so no numeric value is reported here.

## Cross-assay decision

The biological assay is negative geotaxis/climbing, whereas the virtual assay
uses planar locomotion. These endpoints are not quantitatively equivalent.
The only permitted comparison is locomotor impairment direction.

- Quantitative cross-assay validation: `false`.
- Cross-assay decision: `DIRECTIONAL_CROSS_ASSAY_DISCORDANCE`.
- Retuning after holdout: `false`.
- Post-hoc parameter selection: `false`.

Because the biological source supports impairment while the frozen virtual
prediction did not support impairment, this is a directional discordance under
the preregistered cross-assay protocol. This negative validation result does
not authorize changing the model or re-running Gate24E.

## Claim boundary

This result does not support a biologically validated Parkinson model, a
validated Parkinson mechanism, human or clinical validation, or drug
validation. The allowed statement is:

> The frozen Parkin computational perturbation did not reproduce the held-out
> biological locomotor impairment direction under the preregistered
> cross-assay validation protocol.

Any improved model must be a new experiment with a new gate and versioned
provenance; it must not rewrite the Gate24E frozen evidence.
