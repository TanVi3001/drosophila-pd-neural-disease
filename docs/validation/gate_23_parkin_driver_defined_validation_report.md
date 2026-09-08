# Gate 23 - Parkin evidence acquisition and driver-defined mapping

**Status:** `WAITING_SECOND_HUMAN_REVIEW`

## Evidence layers
- Intervention: `INTERVENTION_GENE_SPECIFIC` when the exact Parkin UAS construct and TH-GAL4 experiment are locked.
- Connectome: `DRIVER_DEFINED_CONNECTOME_MAPPING` when real root IDs have public-source provenance.
- Direct gene expression mapping: explicitly not asserted.

## Counts
- Supported root IDs: `330`
- Biological evidence rows: `7`
- Molecular evidence rows: `3`
- Rescue/orthogonal evidence rows: `1`
- Independent holdout sources: `1`

## Claim boundary
> The intervention is Parkin-specific; the connectome target is driver-defined rather than Parkin-expression-defined.
The table is not a Parkin-expression-specific mapping; it is a driver-defined population candidate.
Two-human signoff is still pending, so the mapping cannot authorize a gene-specific rollout.

No gene-specific biological validation, clinical validation, or drug validation claim is allowed at this gate.

## Blockers
- reviewer_2 and review_date are missing for the driver-defined mapping

## Execution boundary
Execution boundary: no GPU, simulation, calibration or tuning was performed.
No biological data were created and no raw values were digitized from plots.
