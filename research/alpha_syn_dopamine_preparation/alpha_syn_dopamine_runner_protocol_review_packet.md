# Alpha-synuclein/dopamine runner protocol review packet v1

Status: `DUAL_HUMAN_RUNNER_PROTOCOL_REVIEW_PASS`
This packet reviews the new runner implementation only. It is not scientific GPU execution authorization.

## Scope

The runner implements the declared alpha-synuclein → dopamine → locomotion computational direction as a **class-level dopamine proxy**. It does not claim that the shared dopamine target set is a gene-specific alpha-synuclein map.

The matrix is three declared states × five seeds:

- `healthy_control`, seeds `0–4`;
- `alpha_synuclein_functional_dopamine`, seeds `0–4`;
- `alpha_synuclein_structural_loss`, seeds `0–4`.

## Materials to review

- `experiments/alpha_syn_dopamine/configs/alpha_syn_dopamine_runner_v1.yaml`
- `scripts/run_alpha_syn_dopamine.py`
- `src/drosophila_pd_neural/alpha_syn_dopamine_runner.py`
- `research/alpha_syn_dopamine_preparation/alpha_syn_dopamine_runner_dry_run_manifest.json`
- `research/alpha_syn_dopamine_preparation/alpha_syn_dopamine_runner_audit_v1.json`
- `research/alpha_syn_dopamine_preparation/alpha_syn_dopamine_preregistration_v1.md`

## Required checks

- [x] The functional dopamine state and structural-loss comparator are separate.
- [x] The dopamine target set is explicitly sourced and remains `gene_specific_mapping=false`.
- [x] The provisional gains, survival parameter, age point, 5,000-step runtime, stimulus, and CPG frequency are accepted and locked for this execution authorization.
- [x] The 15 job IDs and seeds are complete and unique; no automatic retry is permitted.
- [x] Existing output is never overwritten; no holdout is opened; no calibration/fitting/retuning is performed by the runner.
- [x] `--execute` remains blocked unless this packet is PASS and a separate explicit GPU authorization is recorded.
- [x] The claim boundary remains computational and uncertainty-aware, not biological causality or clinical validation.

## Attestations

### Reviewer 1 — Lê Tấn Vĩ

- Runner protocol reviewed: Yes
- Decision: PASS
- Confirmation: Direct confirmation recorded from Le Tan Vi in the project conversation on 2026-09-13; runner protocol and parameters accepted for separate GPU authorization.
- Date: 2026-09-13

### Reviewer 2 — Tô Đặng Minh Tuấn

- Runner protocol reviewed: Yes
- Decision: PASS
- Confirmation: Direct confirmation recorded from To Dang Minh Tuan in the project conversation on 2026-09-13; runner protocol and parameters accepted for separate GPU authorization.
- Date: 2026-09-13

Both attestations are recorded as PASS. The separate execution authorization must still name the frozen config/checkpoint/job-matrix hashes; no runner process is started by this review step.
