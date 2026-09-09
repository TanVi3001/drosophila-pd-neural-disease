# Gate 24E-S4F: Storage artifact reconciliation and cleanup decision package

> **READ-ONLY AUDIT. No file was deleted, moved, renamed, compressed, truncated or modified.**

## Current gate state

- Repository branch: `research/riemensperger-2011-computational-replication`; starting HEAD: `8399a85`.
- Current free space: `13,238,046,720 bytes (13.238 GB)`.
- Locked requirement: `17,548,739,588 bytes (17.549 GB)`; deficit: `4,310,692,868 bytes (4.311 GB)`.
- Capacity rule: `current_free_bytes > required_bytes`; current result: `FAIL`.
- Gate24E plan: 25 jobs frozen; scientific jobs executed: `0`; batch authorized: `false`; holdout: `SEALED`.
- attempt_04 and all Gate24 evidence remain protected.

## Candidate inventory

The three candidate trees were fully enumerated and every file was hashed in memory. The committed manifest stores compact summaries rather than a large raw inventory.

| Group | Total bytes | Files | Canonical interpretation | Active code reference |
|---|---:|---:|---|---|
| `gate11` | 4,704,802,797 bytes (4.705 GB) | 1346 | CANONICAL_GATE_EVIDENCE | True (76 refs) |
| `healthy_reproducible` | 3,935,172,359 bytes (3.935 GB) | 1185 | DERIVED_REPRODUCIBILITY_PACKAGE | True (54 refs) |
| `gate18` | 2,816,614,089 bytes (2.817 GB) | 67 | HISTORICAL_MOVEMENT_VERIFICATION_EVIDENCE | True (9 refs) |

### File-type summaries

#### Gate 11 canonical healthy baseline

| Extension | Files | Bytes |
|---|---:|---:|
| `.css` | 12 | 243,852 bytes (0.000 GB) |
| `.csv` | 19 | 480,379,812 bytes (0.480 GB) |
| `.html` | 24 | 761,202 bytes (0.001 GB) |
| `.js` | 660 | 3,703,524 bytes (0.004 GB) |
| `.json` | 83 | 3,692,532,954 bytes (3.693 GB) |
| `.log` | 7 | 54,387 bytes (0.000 GB) |
| `.md` | 18 | 25,213 bytes (0.000 GB) |
| `.npz` | 6 | 168,411,896 bytes (0.168 GB) |
| `.png` | 42 | 2,149,754 bytes (0.002 GB) |
| `.stl` | 468 | 39,983,712 bytes (0.040 GB) |
| `.yaml` | 1 | 1,206 bytes (0.000 GB) |
| `.zip` | 6 | 316,555,285 bytes (0.317 GB) |

#### reproducible healthy baseline package

| Extension | Files | Bytes |
|---|---:|---:|
| `.css` | 10 | 203,210 bytes (0.000 GB) |
| `.csv` | 57 | 400,659,126 bytes (0.401 GB) |
| `.html` | 20 | 638,066 bytes (0.001 GB) |
| `.js` | 550 | 3,086,270 bytes (0.003 GB) |
| `.json` | 79 | 3,077,598,767 bytes (3.078 GB) |
| `.md` | 24 | 33,899 bytes (0.000 GB) |
| `.mp4` | 2 | 8,186,060 bytes (0.008 GB) |
| `.npz` | 5 | 140,352,674 bytes (0.140 GB) |
| `.png` | 41 | 2,734,052 bytes (0.003 GB) |
| `.stl` | 390 | 33,319,760 bytes (0.033 GB) |
| `.yaml` | 1 | 1,720 bytes (0.000 GB) |
| `.zip` | 6 | 268,358,755 bytes (0.268 GB) |

#### Gate 18 movement verification

| Extension | Files | Bytes |
|---|---:|---:|
| `.csv` | 4 | 19,731 bytes (0.000 GB) |
| `.html` | 2 | 2,281,946 bytes (0.002 GB) |
| `.json` | 8 | 2,242,579,478 bytes (2.243 GB) |
| `.md` | 3 | 5,521 bytes (0.000 GB) |
| `.mp4` | 2 | 9,310,086 bytes (0.009 GB) |
| `.npz` | 1 | 558,690,372 bytes (0.559 GB) |
| `.png` | 7 | 393,910 bytes (0.000 GB) |
| `.stl` | 39 | 3,331,976 bytes (0.003 GB) |
| `.yaml` | 1 | 1,069 bytes (0.000 GB) |

## Gate 11 versus reproducible baseline

Gate 11 is the canonical gate evidence because its manifest, aggregate metrics and external-input audit are referenced by active disease/calibration gates and the Gate25 freeze. The reproducible baseline is a separate derived package: it has five seeds and a different output layout/protocol record, so it cannot silently replace Gate 11.

Exact cross-tree duplicate bytes counted on the reproducible-package side: `596,455,802 bytes (0.596 GB)`.
The duplicate comparison uses SHA256 and size, not filename matching. Duplicate examples and matching hash counts are recorded in the machine-readable manifest.

The two trees are not treated as numerically equivalent merely because they represent healthy locomotion. Their seed counts and stored protocol metadata differ; equivalence would require a separately reviewed metric-level comparison.

## Gate 18 review

Gate 18 contains a 10-second movement verification rollout, a representative tracking MP4, metrics summaries, manifests and a large raw rollout/metrics export. The MP4 and manifest-backed summary are unique movement evidence. The large raw exports are reproducible candidates only after an external archive and checksum verification; the manifest also records that the original runtime worktree was dirty, so this is not publication-grade replacement evidence.

The Gate24 attempt_04 `rollout.npz` is not a cleanup candidate and is not included in any reclaim estimate.

## Reference analysis

The audit found `139` meaningful references across the two repositories. Active runtime references include Gate11 manifests/metrics and scripts that use the reproducible baseline path; tests and documentation are recorded separately in `storage_cleanup_reconciliation.json`.
No reference is rewritten by this gate.

## Minimum preservation sets

- Gate 11: keep the multiseed config, canonical manifest, external-input audit, aggregate metrics CSV/JSON and run log. Raw rollout/viewer artifacts are archive-eligible only after a verified external archive; they are not automatically delete-safe.
- Reproducible baseline: keep neural-input status, summary manifest, provenance lock, per-seed metrics, summary statistics, summary report and package README. Raw runs and viewer assets may be archived only after preserving a verified package and checking active analysis dependencies.
- Gate 18: keep config, movement manifest, movement summary CSV/JSON and the representative tracking MP4. Keep Gate18 raw outputs until an external archive has been verified because the runtime was dirty and viewer export was incomplete.

Files not confidently classified remain `UNKNOWN`; no uncertain file is delete-eligible.

## Capacity options

| Option | Interpretation | Estimated release | Projected free | Capacity pass |
|---|---|---:|---:|---|
| `OPTION_A_LOW_RISK` | Exact duplicate bytes only; low risk, likely insufficient. | 596,455,802 bytes (0.596 GB) | 13,834,502,522 bytes (13.835 GB) | `False` |
| `OPTION_B_MODERATE` | Archive reproducible baseline and Gate18 regenerable/viewer outputs while retaining canonical Gate11 and representative evidence. | 6,726,320,773 bytes (6.726 GB) | 19,964,367,493 bytes (19.964 GB) | `True` |
| `OPTION_C_MAXIMUM_SAFE_AFTER_ARCHIVE` | Archive all classified non-preservation outputs from the three groups after independent checksum verification. | 11,426,665,237 bytes (11.427 GB) | 24,664,711,957 bytes (24.665 GB) | `True` |

Recommended for human review: `OPTION_B_MODERATE`. This is a proposal only; it does not authorize deletion or archival. A 1-2 GB operational margin above the locked requirement should be retained when possible.

## Required human decision

A reviewer must approve exact paths and the action (external archive or deletion) after confirming that the minimum preservation set, checksums and active references are preserved. Until that signoff, the only valid action is `HUMAN_REVIEW_GATE24E_STORAGE_CLEANUP`.

## Scientific firewall

- No GPU or simulation was executed.
- Scientific jobs remain `0`; scientific batch remains unauthorized.
- Holdout remains `SEALED`; no holdout values were read or imported.
- No Gate24 attempt_04 artifact was used as a cleanup source.
