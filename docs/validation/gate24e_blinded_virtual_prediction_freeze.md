# Gate 24E-S4J: Frozen blinded virtual prediction

## Provenance and execution gate

- Starting HEAD: `5569774ebdb0401ab5cb9b37b34f20e6e0e9ab82`.
- Scientific plan SHA256: `4515e1916631b019711154dccb5fb887110d5572e3eb82b7ea5118c643db5aac`.
- Execution status: `GATE24E_25_JOB_SCIENTIFIC_BATCH_COMPLETE_UNANALYZED`.
- Artifact QC: `25/25` jobs and `125/125` recorded artifacts verified by SHA256.
- Analyzer SHA256: `7e0315196f6f041faebf5e6872b4605222a97cf2b45ce2db381545809319c42f`.
- Metric provenance: `25` direct locked metrics; `0` derived from frozen rollout.
- Source inventory/execution hashes in the freeze use Git-canonical LF bytes; the separately recorded analyzed-worktree hashes preserve the Windows CRLF byte provenance.

## Locked decision

Primary rule: `median_across_five_same_seed_paired_deltas_lt_0` using statistical unit `seed` and same-seed pairing.
The secondary distance metric cannot override the primary speed decision.

| Parameter | Valid seeds | Median paired delta (mm/s) | Direction |
|---:|---:|---:|---|
| 0.25 | 5 | 0 | FAIL |
| 0.50 | 5 | 7.74238684604e-05 | FAIL |
| 0.75 | 5 | 7.74238684604e-05 | FAIL |
| 1.00 | 5 | 6.02694778529e-08 | FAIL |

- Grid decision: `DIRECTIONAL_VALIDATION_NOT_SUPPORTED`.
- Prediction freeze SHA256: `f44e9ad10b9fc4795ae2173d3e8b27fc9ea0d8202925bfc08cdcc72d06b00863`.

## Scientific firewall

- Biological holdout remained `SEALED`; it was not imported or compared.
- Holdout tuning: `false`.
- Post-hoc parameter selection: `false`.
- Biological validation claim: `NOT_ALLOWED_AT_GATE24E`.
- Allowed statement: "Frozen blinded computational prediction under the preregistered locomotor-direction protocol."

## Validation and handoff

- Pre-analysis holdout audit: `SEALED`.
- Post-analysis holdout audit: `SEALED`.
- `python -m compileall -q src scripts tests`: `PASS`.
- `python -m pytest -q -rs -p no:cacheprovider`: `603 passed`.
- `git diff --check`: `PASS`.
- Commit message: `analysis: freeze Gate24E blinded virtual prediction`; the immutable commit SHA is recorded by Git history.
- Push target: `origin/research/riemensperger-2011-computational-replication`; push outcome is recorded in the task close-out after the commit exists.

Next allowed action: `HUMAN_REVIEW_BEFORE_OPENING_GATE24E_BIOLOGICAL_HOLDOUT`.
