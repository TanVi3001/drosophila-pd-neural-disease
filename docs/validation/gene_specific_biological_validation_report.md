# Gate 22 - Gene-specific and biological validation ladder

**Status:** `WAITING_BIOLOGICAL_VALIDATION_DATA`

## Validation question
Can a reviewed Parkin-specific Drosophila perturbation be represented in the neural model and tested against independent biological evidence?

## Current evidence
- Track A Riemensperger 2011 remains a dopamine-class computational replication.
- Dumitrescu 2023 provides a Parkin RNAi/DAM biological context, but native DAM beam-break activity is not converted to FlyGym speed.
- Existing Parkin DAN root IDs remain `CLASS_LEVEL_EXPLORATORY`; they are not reused as gene-specific IDs.

## Gate statuses
- Evidence: `GENE_SPECIFIC_EVIDENCE_INCOMPLETE`
- Mapping: `WAITING_GENE_SPECIFIC_MAPPING`
- Prospective prediction: `WAITING_GENE_SPECIFIC_MAPPING`
- Biological holdout: `WAITING_BIOLOGICAL_VALIDATION_DATA`
- Gene-specific validation: `GENE_SPECIFIC_VALIDATION_NOT_SUPPORTED`
- Parkinson-like biological support: `PARKINSON_LIKE_BIOLOGICAL_SUPPORT_INCOMPLETE`

## Blockers
- exact matched control genotype is not locked
- DAM beam-break activity is not a validated FlyGym planar-speed transfer
- direct Parkin gene-to-root-ID or gene-to-edge-ID mapping is absent
- two-human-review signoff for gene-specific mapping is incomplete
- prospective prediction contract is not locked
- independent biological validation dataset is absent
- molecular readout evidence requires second review
- rescue/orthogonal evidence is not available; no rescue claim is made

## Claim lock
The repository currently supports a class-level computational disease scaffold and a paper-guided validation architecture. It does not support a gene-specific or biological Parkinson validation claim.

No biological measurements were generated. No GPU simulation, calibration, tuning, or holdout opening was performed by this audit.

## Gate 23 driver-defined readiness
- Status: `GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED_READY`
- Supported root IDs: `330`
- Direct Parkin-expression-specific root-ID mapping: `NOT_ASSERTED`
- Claim: the intervention is Parkin-specific; the connectome target is driver-defined rather than Parkin-expression-defined.
