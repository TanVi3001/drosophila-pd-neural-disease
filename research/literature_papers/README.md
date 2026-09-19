# Literature source guide

The project keeps literature metadata and review notes in Git. The original
PDF copies are not part of the GitHub release. This avoids redistributing
publisher files while keeping the evidence trail reproducible.

## Download the four review papers

Open the official article page, use its PDF download control, and save the
file under `research/literature_papers/open_access/` only for local review:

| Paper id | Article and source | Local filename |
| --- | --- | --- |
| `godena_2014_lrrk2_microtubule` | <https://www.nature.com/articles/ncomms6245> | `godena_2014_lrrk2_microtubule.pdf` |
| `hwang_2013_dj1_dlp` | <https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1003412> | `hwang_2013_dj1_dlp.pdf` |
| `pokrzywa_2017_alpha_syn_flytracker` | <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0184117> | `pokrzywa_2017_alpha_syn_flytracker.pdf` |
| `pozo_2022_pink1_serotonin` | <https://www.mdpi.com/2073-4409/11/9/1544> | `pozo_2022_pink1_serotonin.pdf` |

The historical size and SHA-256 for each previously reviewed copy are in
`source_manifest.json`. They are validation values, not a request to commit a
new PDF. Upstream pages and licenses can change, so recheck the article page
before using a replacement copy.

## Riemensperger 2011

`riemensperger_2011_dopamine_deficiency.pdf` is citation-only. The repository
stores metadata and links because the reviewed local PDF did not establish an
explicit redistribution license:

- PMC: <https://pmc.ncbi.nlm.nih.gov/articles/PMC3021077/>
- DOI: <https://doi.org/10.1073/pnas.1010930108>

## Scope

These papers support literature review and phenotype context. They are not a
single dataset and must not be merged into one calibration loss. Assay
transfer, calibration, holdout, and claim-lock rules remain in force.
