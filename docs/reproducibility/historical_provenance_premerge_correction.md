# Pre-Merge Historical Provenance Correction

## Scope

- Audit date: `2026-09-09`
- Research branch: `research/riemensperger-2011-computational-replication`
- Starting HEAD: `43df7fb0fe564e4aa8caed022da0390b8cbf2865`
- Canonical remote main: `8f99edbe28f1ff18a00132946ef2df7b416d5b85`
- GPU executed: `NO`
- Simulation executed: `NO`
- Scientific analysis executed: `NO`

This correction is limited to historical provenance integrity before merge. It
does not change Gate24E evidence, results, model parameters, or public-facing
current claims.

## Affected Historical Snapshot

The affected file is:

`experiments/gate_20b_real_mapping_provenance/manifests/gate20b_mapping_manifest.json`

The Gate20B manifest identifies its historical creation time as
`2026-09-06T21:21:57.591291+00:00` and its source commit as
`90d1c0c583d447382905420d54907164a0bd52c8`. The canonical `origin/main` Git
blob is `97dcc6e0c8f0b1baa3eb3431ee225d436182a9d5`.

Before this correction, research-branch blob
`0709842bcc62d74ed6a1864ede0bd7cb1434943f` had replaced the historical hash
recorded for `docs/claims/current_claim_lock.md`:

| State | Recorded SHA256 |
|---|---|
| Historical Gate20B value | `09cf89ae339ff7a1e497ef6c319f8fe10e4c64a9080abe10b938f5d92be39b64` |
| Incorrect branch value | `5d48f18acd14896f669d40682fe78ff9b5e23e0257516484ef92f23454b5953a` |

The second value belongs to the later, current Gate24E claim lock. Propagating
it backward changed historical provenance without changing the historical
manifest timestamp or source commit.

## Correction

The Gate20B manifest was restored directly from `origin/main`; it was not
manually reconstructed. Its restored file SHA256 is
`a4cfa9fd9539e68294c4624dc122a29f24aca28c6d7a60839a00db071d5d086e`.

The exact post-correction comparison against `origin/main` is empty:

```text
git diff origin/main -- experiments/gate_20b_real_mapping_provenance/manifests/gate20b_mapping_manifest.json
(no diff)
```

The Gate20B regression test now treats the manifest's claim-lock entry as an
immutable historical hash. It does not require that historical hash to equal
the contents of the independently advancing current claim-lock file.

## Current Claim Surfaces

No current-facing claim file was reverted. Their retained SHA256 values are:

| File | SHA256 |
|---|---|
| `README.md` | `268b06223aef2177f3a3cae34795f5eb40e1dc6285c357e26cb72f02762de488` |
| `docs/claims/current_claim_lock.md` | `5d48f18acd14896f669d40682fe78ff9b5e23e0257516484ef92f23454b5953a` |
| `docs/claims/public_abstract.md` | `110afbf995dd2d26573d17d47035db4a7f349f5d7357ee2d27755f8139160ffb` |
| `docs/project_summary.md` | `be81169a5d3d407bbc19519f4919b365d8536066b46eded52797c9157366e844` |

## Historical Mutation Audit

All files that existed on `origin/main` and were modified by the research
branch were classified. Aside from the corrected Gate20B manifest, they are
current documentation, repository configuration, implementation source, or
tests. No other modified historical manifest or evidence snapshot was found.

The 15 pre-existing unrelated local dirty entries were excluded from this
correction and were not staged, stashed, deleted, or committed.

## Gate24E Scientific Freeze

The scientific evidence remains unchanged:

- Final evidence freeze SHA256: `2f056bf5b73ecc4b4de27f714bda681134050c5d82eb2f0f3170b67a5286e967`
- Virtual prediction freeze SHA256: `f44e9ad10b9fc4795ae2173d3e8b27fc9ea0d8202925bfc08cdcc72d06b00863`
- Raw-run tree SHA256: `f6e3de6e96cbe3be0f447ea8eeca463087a9381d1c2d2965807d04df1655faff`
- Scientific result: `NEGATIVE_VALIDATION_RESULT`
- Cross-assay decision: `DIRECTIONAL_CROSS_ASSAY_DISCORDANCE`

## Gate25-R2 Impact

The Gate20B historical manifest is not included in the Gate25-R2 inventory or
checksum manifest. Regenerating Gate25-R2 solely for this correction is
therefore neither required nor permitted.

- Gate25-R2 SHA256: `5aa0d5bf05dac950761b8636fdea001072f27c8226139ec1dac9066be6146d05`
- Inventory file count: `95`
- Verify-only status: `GATE25_R2_REPRODUCIBILITY_FREEZE_COMPLETE`
- External raw archive verification in verify-only mode:
  `METADATA_AND_CHECKSUM_MANIFEST`

## Validation

- Gate20B focused tests: `6 passed`
- Full pytest: `649 passed, 1 skipped`
- Compileall: `PASS`
- Gate25-R2 `--verify-only`: `PASS`
- `git diff --check`: `PASS`
- Remote relation before correction commit: behind `0`, ahead `48`
- `origin/main` unchanged from the required SHA: `YES`

The single skipped test concerns unavailable symlink support in the local
environment and is unrelated to this provenance correction.

## Merge Readiness

Final status: `READY_FOR_FAST_FORWARD_MERGE_TO_MAIN`

Required next action: obtain human approval, then fast-forward or otherwise
merge the reviewed research branch into `main` without rewriting historical
evidence.
