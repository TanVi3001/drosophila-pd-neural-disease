# Current Claim Lock

## Current project track

This file is the active claim policy for the current Parkin Gate24E
prospective-validation track. Earlier Chen/Pozo evidence is preserved as a
historical track and is not the current Gate24E conclusion.

## Locked current result

- Gate24E status: `GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE`
- Scientific result: `NEGATIVE_VALIDATION_RESULT`
- Virtual decision: `DIRECTIONAL_VALIDATION_NOT_SUPPORTED`
- Biological direction: `BIOLOGICAL_IMPAIRMENT_SUPPORTED`
- Cross-assay decision: `DIRECTIONAL_CROSS_ASSAY_DISCORDANCE`
- Final evidence freeze SHA256: `2f056bf5b73ecc4b4de27f714bda681134050c5d82eb2f0f3170b67a5286e967`
- Virtual prediction freeze SHA256: `f44e9ad10b9fc4795ae2173d3e8b27fc9ea0d8202925bfc08cdcc72d06b00863`
- Raw-run tree SHA256: `f6e3de6e96cbe3be0f447ea8eeca463087a9381d1c2d2965807d04df1655faff`

## Primary allowed statement

> The frozen Parkin computational perturbation did not reproduce the held-out
> biological locomotor impairment direction under the preregistered
> cross-assay validation protocol.

Also allowed:

> Gate24E records a negative prospective directional validation result.

## Interpretation

- The virtual Parkin perturbation did not support the preregistered locomotor
  impairment direction.
- Held-out biological Parkin evidence supported locomotor/climbing impairment.
- The final result is therefore directional cross-assay discordance.
- Climbing and planar speed are non-equivalent assays.
- Quantitative cross-assay validation is forbidden by this evidence package.

The driver-defined neural target is not a Parkin-expression-specific
connectome root mapping:

`driver-defined neural target != Parkin-expression-specific root mapping`

## Forbidden claims

Do not present this project as any of the following:

- biologically validated Parkinson model;
- validated Parkinson mechanism;
- Parkin-expression-specific connectome root mapping;
- gene-specific biological validation;
- human Parkinson validation;
- clinical validation;
- drug efficacy or drug discovery validation;
- quantitative cross-assay equivalence;
- successful Parkin disease phenotype replication.

## Historical Chen/Pozo track

The earlier Chen calibration and Pozo PINK1 holdout results remain valid
historical evidence. They are not the current Parkin Gate24E conclusion.

That historical track used Chen for a locked organism-level calibration and
Pozo as an independent holdout. It reported directional concordance together
with a substantial quantitative ratio mismatch. It must not be rewritten as
Parkin biological validation, gene-specific validation, or quantitative
cross-assay equivalence.

## Reproducibility boundary

Gate24E evidence, the virtual prediction freeze, and the external raw archive
must be referenced by their locked checksums. The raw rollout archive is
checksum-preserved outside Git and is not publicly available through this
repository. Reproducibility normally means auditing the frozen manifests and
hashes; it does not require rerunning the 25-job GPU batch.
