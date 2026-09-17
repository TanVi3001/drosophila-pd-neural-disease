# Key artifacts index

| Artifact | Path | Purpose | Current status |
| --- | --- | --- | --- |
| Current claim lock | `docs/claims/current_claim_lock.md` | Interpretation boundary | ACTIVE |
| Public abstract | `docs/claims/public_abstract.md` | Claim-safe summary | HISTORICAL EVIDENCE |
| Project summary | `docs/project_summary.md` | Current architecture/status | READY |
| Platform contract | `docs/architecture/platform_contract.md` | Source-of-truth integration | ACTIVE |
| Gate 13B calibration summary | `experiments/gate_13b_chen_ratio_calibration/results/chen_ratio_calibration_summary.json` | Historical calibration evidence | HISTORICAL |
| Gate 13C confirmation manifest | `experiments/gate_13c_calibrated_confirmation/manifests/calibrated_confirmation_manifest.json` | Historical confirmation evidence | REQUIRES CURRENT-PLATFORM RECHECK |
| Gate 14B holdout result summary | `experiments/gate_14b_pozo_holdout_validation/results/pozo_holdout_result_summary.json` | Historical holdout evidence | REQUIRES CURRENT-PLATFORM RECHECK |
| Gate 14C adjudication summary | `experiments/gate_14c_holdout_adjudication/results/holdout_adjudication_summary.json` | Historical claim adjudication | HISTORICAL |
| Gate 15B release manifest | `experiments/gate_15b_release_bundle/manifests/release_bundle_manifest.json` | Bundle provenance | HISTORICAL |

The platform contract and current source inspection take precedence over any
historical PASS label in the evidence tree.
