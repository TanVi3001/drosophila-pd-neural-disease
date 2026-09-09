# Gate25-R2: Parkin reproducibility freeze

**Status:** `GATE25_R2_REPRODUCIBILITY_FREEZE_COMPLETE`

## Purpose

Gate25-R2 is a new reproducibility freeze for the closed Gate24E Parkin
track. The historical pre-Parkin Gate25 report is preserved unchanged. This
freeze audits existing contracts, manifests, checksums, and relocation
provenance only; it does not rerun Gate24E or create new scientific evidence.

## Frozen result

- Gate24E status: `GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE`.
- Scientific result: `NEGATIVE_VALIDATION_RESULT`.
- Cross-assay decision: `DIRECTIONAL_CROSS_ASSAY_DISCORDANCE`.
- Inventory entries: `95` deterministic lightweight files.
- Gate25-R2 canonical freeze SHA256: `23b91653c01a068ee4836c24797a195010bb3b861e3c5a98e0faf058355a6d76`.
- Previous Gate25-R2 freeze SHA256: `5aa0d5bf05dac950761b8636fdea001072f27c8226139ec1dac9066be6146d05`.
- Historical Gate25 report SHA256: `e09347664edbc069c8d8bdd0340811cbaf8a4b9f75a25d1e356a24086cb309f0`.
- Refresh reason: `CROSS_PLATFORM_FROZEN_ARTIFACT_TRANSPORT_FIX`.

The allowed primary claim is: **The frozen Parkin computational perturbation
did not reproduce the held-out biological locomotor impairment direction under
the preregistered cross-assay validation protocol.** Gate24E therefore records
a negative prospective directional validation result.

## Exact provenance lock

- Scientific plan: `4515e1916631b019711154dccb5fb887110d5572e3eb82b7ea5118c643db5aac`.
- Virtual prediction freeze: `f44e9ad10b9fc4795ae2173d3e8b27fc9ea0d8202925bfc08cdcc72d06b00863`.
- Final evidence freeze: `2f056bf5b73ecc4b4de27f714bda681134050c5d82eb2f0f3170b67a5286e967`.
- Raw-run tree: `f6e3de6e96cbe3be0f447ea8eeca463087a9381d1c2d2965807d04df1655faff`.
- Executor SHA256: `4d10edecbc8d987285ea82eb36a7bcfd686da3abde3b5160a3dcec23a2e78f3f`.
- Model commit: `be4b10a80755d9f7bad931f56b8a739bd64e3619`.
- External runtime commit: `655e854544e3d814dfe422883ff0de66b619d6c1` (`GATE24E_MEMORY_SAFE`).

The main repository code and the external FlyGym runtime are distinct. The
runtime is not vendored into this repository.

## Raw evidence boundary

The 25-job raw rollout evidence is not committed to Git. It is preserved at
the external archive path recorded in the relocation manifest with 275 files,
13,958,129,260 bytes, and the locked tree SHA256. Current live archive check:
`METADATA_AND_CHECKSUM_MANIFEST` using
`metadata_checksum_manifest_and_tree_hash`. This does not make the raw data publicly
available; public availability requires a separately authorized archive
release.

## Reproducibility audit

From the repository root, run:

```powershell
py -3.12 scripts/run_gate25_r2_reproducibility_freeze.py --verify-only
py -3.12 -m compileall -q src scripts tests
py -3.12 -m pytest -q -rs -p no:cacheprovider
git diff --check
```

These commands verify repository hashes, the locked plans and manifests, the
external relocation metadata, the deterministic inventory, and the checksum
manifest. They do not require a new 25-job scientific rerun. A future
intentional replication is a new experiment and must receive a new gate.

## Claim boundary and limitations

This freeze does not support claims of a biologically validated Parkinson
model, a validated Parkinson mechanism, Parkin-expression-specific connectome
root mapping, human or clinical validation, drug validation, successful
phenotype replication, or quantitative biological validation. The biological
holdout supports only the recorded directional cross-assay interpretation;
the quantitative mismatch remains explicit.

## Merge readiness

`READY_FOR_RESEARCH_BRANCH_MERGE_REVIEW` when Gate24E remains closed, the R2
freeze and tests pass, no critical Gate24E changes are uncommitted, and the
historical Gate25 report remains unchanged. This task does not merge `main`.
