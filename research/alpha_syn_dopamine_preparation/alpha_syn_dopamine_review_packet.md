# Alpha-synuclein/dopamine direction review packet

Status: `WAITING_DUAL_HUMAN_DIRECTION_REVIEW`

## Materials

- `literature_endpoint_registry_v2.csv`
- `alpha_syn_dopamine_study_split_manifest_v1.json`
- `alpha_syn_dopamine_direction_review_vi.md`
- `alpha_syn_dopamine_gate_a_b_preparation_report.md`
- `checksums.sha256`

## Checklist for both reviewers

- [ ] The first-paper scope is alpha-synuclein -> dopamine circuit -> locomotion.
- [ ] PINK1–serotonin is deferred; generic multi-gene scalar burden is excluded.
- [ ] `walking_speed`, `mean_planar_speed_mm_s`, and `median_planar_speed_mm_s` are not silently treated as identical.
- [ ] Distance, activity time, climbing, and DAM activity are kept as separate endpoint families.
- [ ] Missing center/spread/unit/duration metadata remains pending rather than being imputed.
- [ ] Study allocation is reviewed before any fitting and no study is reused as both fit and holdout.
- [ ] No GPU execution, fitting, retuning, or holdout opening is authorized by this packet.

## Required attestations

### Reviewer 1 — Lê Tấn Vĩ

- Confirmation: ______________________________
- Date: __________________

### Reviewer 2 — Tô Đặng Minh Tuấn

- Confirmation: ______________________________
- Date: __________________

After both direct confirmations, update the signoff manifest. Until then, this is a preparation draft and no scientific run may start from it.
