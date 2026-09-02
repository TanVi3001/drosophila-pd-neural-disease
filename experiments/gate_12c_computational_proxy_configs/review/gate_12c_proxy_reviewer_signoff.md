# Gate 12C Proxy Reviewer Signoff

## Reviewer identity

- Reviewer name: Lê Tấn Vĩ
- Review date: 2026-09-02
- Reviewer role: project scientific reviewer

## Decision

I approve alpha_synuclein and pink1 for Gate 12D computational proxy rollouts only.

This approval does not assert gene-specific neuron mapping, biological disease mechanism validation, or clinical relevance.

## Approved proxy scope

- alpha_synuclein: organism_level_proxy
- pink1: organism_level_proxy

## Not approved for run-ready

- parkin: remains BLOCKED
- dj1: remains BLOCKED
- lrrk2: remains BLOCKED

## Rationale

alpha_synuclein and pink1 may be used as computational perturbation proxy labels for exploratory disease-layer rollout testing because Gate 11 established a healthy runtime and metric contract. These proxy configs are not gene-specific and must not be interpreted as validated biological mapping.

## Restrictions

- Do not claim gene-specific mapping.
- Do not claim biological Parkinson validation.
- Do not tune to Chen in Gate 12C.
- Do not tune to Pozo.
- Do not convert Pozo distance to speed.
- Do not convert CI95 to SE.
- Do not use holdout for tuning.
- Do not run simulation in Gate 12C.
