# Gate 24E-S4D: Storage capacity cleanup candidates

## Purpose and boundary

This report records a read-only inventory for resolving the Gate 24E storage
capacity blocker. No file was deleted, moved, truncated, recompressed or
modified. No GPU, simulation, probe, scientific job or holdout access was
performed.

The locked qualification requirement is:

```text
current_free_bytes > 17,548,739,588
```

## Current capacity

| Field | Value |
|---|---:|
| Filesystem | `E:` |
| Current free bytes | `13,238,411,264` |
| Required bytes | `17,548,739,588` |
| Deficit | `4,310,328,324` |
| Strict capacity rule | `FALSE` |
| Current status | `WAITING_GATE24E_STORAGE_CAPACITY` |

The capacity model was not recalculated. The locked `required_bytes` value is
used exactly as recorded by `attempt_04`.

## Protected paths

The following paths are excluded from cleanup recommendations and must remain
unchanged:

- `main-public-docs/experiments/gate_24e_storage_probe/attempt_01`
- `main-public-docs/experiments/gate_24e_storage_probe/attempt_02`
- `main-public-docs/experiments/gate_24e_storage_probe/attempt_03`
- `main-public-docs/experiments/gate_24e_storage_probe/attempt_04`
- `main-public-docs/experiments/gate_24e_storage_probe/manifests/storage_qualification.json`
- `drosophila-pd-flygym-gate24-memorysafe-clean`
- `drosophila-pd-neural-disease/external/fly-brain`
- `drosophila-pd-neural-disease/temporary/paper_pdf`

The current scientific source repository and approved runtime directories are
also treated as protected until the research team explicitly changes that
decision.

## Candidate inventory

Sizes are recursive file totals measured read-only. A candidate is not an
authorization to delete it.

| Path | Size | Category | Safe to remove now? | Reason / required review |
|---|---:|---|---|---|
| `drosophila-pd-neural-disease/experiments/gate_11_healthy_baseline` | 4.38 GB | Derived healthy rollout, viewer and raw exports | NO; conditional | May duplicate `results/healthy_baseline_reproducible`, but must be compared by manifest/checksum before archival or removal. |
| `drosophila-pd-neural-disease/results/healthy_baseline_reproducible` | 3.66 GB | Derived healthy baseline artifacts | NO; conditional | Research evidence may still be needed for reproduction; archive and verify checksums first. |
| `drosophila-pd-neural-disease/experiments/gate_18_movement_verified_rollout` | 2.62 GB | Derived movement rollout and viewer artifacts | NO; conditional | Keep until the representative video/metrics and provenance are archived elsewhere. |
| `drosophila-pd-neural-disease/.venv` | 173.41 MB | Local Python environment | NO; conditional | Disposable only after confirming no active notebook or runner depends on it. |
| `drosophila-pd-neural-disease/tmp` | 83.89 MB | Temporary QA/render/build artifacts | CONDITIONAL | Candidate after confirming the images and build cache are no longer needed. |
| `gate21-worktree` | 169.42 MB | Historical worktree | CONDITIONAL | Remove only after `git worktree list` and branch ownership confirm it is unused. |
| `temporary` | 4.65 MB | Paper/QA temporary files | NO | Not material for capacity and may contain source evidence. |
| `tmp` | 1.10 MB | Temporary PDF renders | CONDITIONAL | Small gain; remove only after visual QA artifacts are archived. |
| `drosophila-pd-flygym-gate24-memorysafe` | 89.25 MB | Runtime worktree candidate | NO | Runtime provenance has not been independently cleared for deletion. |
| `drosophila-pd-flygym-gate24-clean` | 84.80 MB | Runtime worktree candidate | NO | Runtime provenance has not been independently cleared for deletion. |

## Important finding

The first three derived-output groups together are approximately `10.66 GB`,
which would exceed the current `4.31 GB` deficit if the research team confirms
that they are duplicate or archived artifacts. They are the only candidates
large enough to resolve the blocker without touching protected brain data or
Gate24 evidence. They must not be removed based on size alone.

## Required human cleanup decision

Before deletion or archival, the research team should:

1. Compare the Gate 11 and reproducible-baseline manifests and checksums.
2. Preserve at least one complete provenance-backed copy of every baseline used
   in the manuscript or report.
3. Confirm whether Gate 18 outputs are still needed for the movement video and
   metrics evidence.
4. Archive approved evidence outside the active filesystem if required.
5. Remove only explicitly approved disposable duplicates/cache files.

After cleanup, perform only this read-only check:

```powershell
$free = (Get-PSDrive -Name E).Free
$required = 17548739588
"free=$free required=$required pass=$($free -gt $required)"
```

If `pass=True`, the next state is
`GATE24E_STORAGE_CAPACITY_RESOLVED` and the next allowed action is
`GATE24E_SCIENTIFIC_BATCH_AUTHORIZATION_AND_FINAL_PREFLIGHT`. Otherwise the
state remains `WAITING_GATE24E_STORAGE_CAPACITY` and the allowed action remains
`RESOLVE_STORAGE_CAPACITY_ONLY`.

## Scientific firewall snapshot

- `scientific_jobs_executed=0`
- `scientific_batch_authorized=false`
- `holdout=SEALED`
- `holdout_opened=false`
- GPU executed in S4D: `NO`
- Simulation executed in S4D: `NO`
