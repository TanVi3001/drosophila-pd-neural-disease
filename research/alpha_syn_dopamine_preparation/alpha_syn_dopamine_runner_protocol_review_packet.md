# Alpha-synuclein/dopamine runner protocol review packet v1

Status: `READY_FOR_DUAL_HUMAN_RUNNER_PROTOCOL_REVIEW`  
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

- [ ] The functional dopamine state and structural-loss comparator are separate.
- [ ] The dopamine target set is explicitly sourced and remains `gene_specific_mapping=false`.
- [ ] The provisional gains, survival parameter, age point, 5,000-step runtime, stimulus, and CPG frequency are accepted or revised before lock.
- [ ] The 15 job IDs and seeds are complete and unique; no automatic retry is permitted.
- [ ] Existing output is never overwritten; no holdout is opened; no calibration/fitting/retuning is performed by the runner.
- [ ] `--execute` must remain blocked until this packet is PASS and a separate explicit GPU authorization is recorded.
- [ ] The claim boundary remains computational and uncertainty-aware, not biological causality or clinical validation.

## Attestations

### Reviewer 1 — Lê Tấn Vĩ

- Runner protocol reviewed: ______________________________
- Decision: _____________________________________________
- Confirmation: _________________________________________
- Date: __________________

### Reviewer 2 — Tô Đặng Minh Tuấn

- Runner protocol reviewed: ______________________________
- Decision: _____________________________________________
- Confirmation: _________________________________________
- Date: __________________

Until both attestations are recorded as PASS, `parameter_lock_status` must remain `PROVISIONAL_NO_GPU`, and `alpha_syn_dopamine_execution_authorization_v1.json` must remain `authorized=false` and `gpu_execution_authorized=false`.
