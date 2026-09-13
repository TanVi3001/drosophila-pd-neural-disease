# Gate29-H continuation 003 release packet

This packet contains the frozen Gate29-H QC and statistical-analysis outputs for preregistration `GATE29H_RIEMENSPERGER_SCIENTIFIC_TRACE_V1`.

## Result

15/15 jobs passed QC. The full-burden minus healthy-control primary endpoint difference was exactly zero for every matched seed; exact one-sided sign-flip p = 1.00 and 95% bootstrap CI [0, 0]. The locked decision is `NOT_REPRODUCED_WITHIN_COMPUTATIONAL_SCOPE`.

## Reproducibility

The raw rollout and trace arrays are intentionally not copied into this lightweight repository packet. Their source paths and SHA256 hashes are recorded per job in `manifests/gate29h_result_freeze_manifest.json`. The QC report and statistical-analysis JSON are copied verbatim into `manifests/`. Verify all packet files using `checksums.sha256`.

This release step is analysis-only. It does not launch GPU execution, modify raw outputs, retune the model, change burden, or open a holdout.

## Human review

Review `reports/gate29h_review_packet.md` and record both direct human attestations in `manifests/gate29h_analysis_review_signoff.json` only after Lê Tấn Vĩ and Tô Đặng Minh Tuấn have reviewed the materials.
