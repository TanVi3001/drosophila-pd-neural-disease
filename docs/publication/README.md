# Publication Handoff Gates 27--37

| Gate | Purpose | Current status |
| --- | --- | --- |
| 27 | Internal scientific review package | `INTERNAL_REVIEW_PACKAGE_READY` |
| 28 | Archive/license/citation templates | `ARCHIVE_METADATA_PENDING_HUMAN_DECISIONS` |
| 29 | Venue submission metadata templates | `SUBMISSION_METADATA_PENDING_HUMAN_SIGNOFF` |
| 30 | Authorized publication handoff | `PUBLICATION_HANDOFF_PENDING_HUMAN_AUTHORIZATION` |
| 31 | Internal scientific signoff | `WAITING_AUTHORIZED_INTERNAL_SIGNOFF` |
| 32 | License, authorship and declarations | `WAITING_APPROVED_PUBLICATION_METADATA` |
| 33 | Venue-specific manuscript | `VENUE_MANUSCRIPT_TEMPLATE_READY` |
| 34 | Public archive and DOI receipt | `ARCHIVE_RELEASE_PENDING_AUTHORIZATION` |
| 35 | External submission receipt | `EXTERNAL_SUBMISSION_PENDING_CORRESPONDING_AUTHOR` |
| 36 | Reviewer response and revision ledger | `WAITING_FOR_EDITORIAL_DECISION` |
| 37 | Acceptance and final archive | `WAITING_FOR_ACCEPTANCE` |

These gates do not submit to a venue or publish externally. They preserve the
Gate 24 claim boundary and make every human-only decision explicit.

For Gate 31--37, copy the matching `.local.*.example` file, fill it only after
an authorized real-world action, and rerun
`py -3.12 scripts/run_gates31_37_publication_control_plane.py`. Local receipts
are ignored by Git because they can contain personal, editorial or portal data.
