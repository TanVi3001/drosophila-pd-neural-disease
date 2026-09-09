# Gate 24E: Final validation decision and limitations

## 1. Question tested

The preregistered question was whether the frozen Parkin computational perturbation would reproduce the direction of locomotor impairment reported by an independent held-out biological source.

## 2. Frozen computational prediction

- Prediction freeze SHA256: `f44e9ad10b9fc4795ae2173d3e8b27fc9ea0d8202925bfc08cdcc72d06b00863`.
- Primary metric: `median_planar_speed_mm_s`.
- Validation axis: `LOCOMOTOR_IMPAIRMENT_DIRECTION`.
- Frozen virtual decision: `DIRECTIONAL_VALIDATION_NOT_SUPPORTED`.
- The virtual prediction was frozen before the biological holdout was opened.

## 3. Held-out biological direction

- Source: Cackovic et al. 2018, DOI `10.3389/fncel.2018.00039`, PMID `29497364`.
- Assay: negative geotaxis/climbing with vertical infrared monitoring.
- Direction: `BIOLOGICAL_IMPAIRMENT_SUPPORTED`.
- Raw individual-level data in the repository: unavailable.

## 4. Directional comparison

The virtual assay measures planar locomotion, while the biological holdout measures climbing. These endpoints are not quantitatively equivalent. Only impairment direction was compared.

- Final cross-assay decision: `DIRECTIONAL_CROSS_ASSAY_DISCORDANCE`.
- Quantitative cross-assay validation: `false`.

## 5. Final result

- Gate status: `GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE`.
- Scientific result: `NEGATIVE_VALIDATION_RESULT`.

> The frozen Parkin computational perturbation did not reproduce the held-out biological locomotor impairment direction under the preregistered cross-assay validation protocol.

Gate24E is therefore historical negative evidence for this frozen perturbation and protocol. It is not a positive disease-model validation.

## 6. What the result does not mean

This result does not establish a biologically validated Parkinson model, a validated Parkinson mechanism, Parkin-expression-specific connectome mapping, human or clinical validation, drug efficacy, drug discovery validation, quantitative assay equivalence, or successful disease phenotype replication.
The driver-defined neural target is not the same as a Parkin-expression-specific root mapping.

## 7. Limitations

- The assays differ: planar speed versus negative geotaxis/climbing; therefore only direction was compared.
- S4K used summary-level held-out evidence; no individual-level raw Cackovic data were available.
- The reviewed driver-defined Parkin perturbation produced essentially no preregistered reduction in virtual speed.
- The scientific unit was five seeds; frames were not statistical replicates.
- Burdens 0.25, 0.50, 0.75 and 1.00 are dimensionless computational sensitivity levels, not measured Parkin knockdown percentages.
- The model is a computational locomotion model, not organism-level biological validation.

## 8. Negative-result integrity

Gate24E must not be rerun or rewritten to obtain a positive result. No retuning, seed replacement, parameter selection, metric substitution, or decision-rule modification may use the opened holdout. Any improved model requires a new version, new prospective experiment, new freeze, and new holdout policy.

## 9. Future hypotheses

The following are future hypotheses, not corrections to Gate24E: a stronger or mechanistically different neural perturbation operator; downstream network-dynamics perturbation; driver/subpopulation-specific perturbation; longer or assay-aligned endpoints; a negative-geotaxis-like virtual task; independent seed expansion; and robustness/ablation studies.

## 10. Provenance

- Final evidence freeze SHA256: `2f056bf5b73ecc4b4de27f714bda681134050c5d82eb2f0f3170b67a5286e967`.
- Raw rollout paths are excluded from this lightweight closure freeze and remain protected by the scientific artifact inventory.

| Artifact | SHA256 | Bytes |
|---|---|---:|
| `experiments/gate_24e_blinded_parkin_prediction/manifests/immutable_virtual_prediction_freeze.json` | `de5f542d642dee351bdecc921180e0721689ba5810bdcd0461f811acca8f5707` | 2386 |
| `experiments/gate_24e_blinded_parkin_prediction/results/virtual_prediction_summary.json` | `c42dd68791139c7829959c599c851548c479f8af48253403e96b1dbad981a590` | 2939 |
| `experiments/gate_24e_blinded_parkin_prediction/manifests/biological_holdout_opening.json` | `715e60383bef47c0ba8f5bd0998cc55a49bd1ba6faa5c9f0a510750990094aa8` | 829 |
| `experiments/gate_24e_blinded_parkin_prediction/results/biological_holdout_direction.csv` | `d766b1c3fa1bfc9480650c4184c777cd13ca73445d1f2f26e5bf6526214dd1c5` | 705 |
| `experiments/gate_24e_blinded_parkin_prediction/results/cross_assay_validation_summary.json` | `1204de5cdf95cc68b7caf0039940b824fbeae02d88aca2b883a0b4c6aa2f7836` | 970 |
| `docs/validation/gate24e_biological_holdout_directional_validation.md` | `1c32f6d0c846a79ddf93d81036b27a8b12045cbb6ab88404b0173726acdc2f23` | 2971 |
| `experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_final_validation_decision.json` | `758c00bc3c8e3aa4849f8285fa73150dc44bc43cf132c9897c464a8a53428574` | 2841 |

## 11. Human final review state

The final reviewer signoff remains `WAITING_GATE24E_FINAL_VALIDATION_REVIEW` / `PENDING_HUMAN_REVIEW`. The closure package does not auto-sign or claim final human approval.

## 12. Boundary

No GPU, simulation, new scientific analysis, retuning, or holdout reinterpretation was performed in S4L.
