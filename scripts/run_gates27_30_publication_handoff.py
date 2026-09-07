"""Prepare Gates 27--30 publication handoff artifacts without external submission.

The workflow is intentionally conservative. It audits the frozen evidence,
creates templates for decisions that must be made by real people, and builds a
checksummed handoff package. It never starts GPU/simulation/calibration or
uploads data, creates a DOI, tags a release, or submits a manuscript.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "experiments/gate_27_internal_scientific_review/configs/publication_handoff.yaml"
GATE27_ROOT = ROOT / "experiments/gate_27_internal_scientific_review"
GATE28_ROOT = ROOT / "experiments/gate_28_archive_metadata"
GATE29_ROOT = ROOT / "experiments/gate_29_submission_readiness"
GATE30_ROOT = ROOT / "experiments/gate_30_publication_handoff"
DOCS_ROOT = ROOT / "docs/publication"
SUBMISSION_ROOT = ROOT / "submission"


class PublicationHandoffError(ValueError):
    """Raised when frozen evidence or publication handoff boundaries fail."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise PublicationHandoffError(f"Path is outside repository: {path}") from exc


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationHandoffError(f"Invalid JSON: {_relative(path)}") from exc
    if not isinstance(value, dict):
        raise PublicationHandoffError(f"Expected JSON object: {_relative(path)}")
    return value


def _read_config(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise PublicationHandoffError("Publication handoff config must be a YAML mapping")
    return value


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _record(path: Path, role: str) -> dict[str, Any]:
    if not path.is_file():
        raise PublicationHandoffError(f"Missing artifact: {_relative(path)}")
    return {"path": _relative(path), "role": role, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}


def _validate_execution_boundary(config: Mapping[str, Any]) -> None:
    false_fields = (
        "run_gpu",
        "run_simulation",
        "run_calibration",
        "run_holdout_validation",
        "run_tuning",
        "submit_to_external_service",
    )
    if config.get("analysis_only") is not True or any(config.get(field) is not False for field in false_fields):
        raise PublicationHandoffError("Gates 27--30 must stay local and analysis-only")


def _validate_frozen_sources(config: Mapping[str, Any]) -> dict[str, Path]:
    _validate_execution_boundary(config)
    paths = {name: ROOT / relative for name, relative in config["sources"].items()}
    documents = {
        "gate_24_manifest": _read_json(paths["gate_24_manifest"]),
        "gate_25_manifest": _read_json(paths["gate_25_manifest"]),
        "gate_26_manifest": _read_json(paths["gate_26_manifest"]),
    }
    expected = {
        "gate_24_manifest": "CONCORDANCE_REPORT_COMPLETE",
        "gate_25_manifest": "REPRODUCIBILITY_FREEZE_COMPLETE",
        "gate_26_manifest": "SUBMISSION_PACKAGE_READY_FOR_INTERNAL_REVIEW",
    }
    for key, status in expected.items():
        if documents[key].get("status") != status:
            raise PublicationHandoffError(f"Unexpected {key} status: {documents[key].get('status')!r}")
    gate24 = documents["gate_24_manifest"]
    if gate24.get("pozo_quantitative_match") is not False:
        raise PublicationHandoffError("Pozo quantitative mismatch must stay explicit")
    if gate24.get("gene_specific_validation") is not False or gate24.get("biological_parkinson_validation") is not False:
        raise PublicationHandoffError("Gate 24 claim boundaries are incomplete")
    gate25 = documents["gate_25_manifest"]
    if any(gate25.get(key) is not True for key in ("no_gpu", "no_simulation", "no_calibration", "no_holdout_validation", "no_tuning")):
        raise PublicationHandoffError("Gate 25 freeze boundary is incomplete")
    manuscript = paths["manuscript"].read_text(encoding="utf-8")
    normalized = " ".join(manuscript.split())
    if "not a biological, gene-specific, clinical, or therapeutic validation" not in normalized:
        raise PublicationHandoffError("Manuscript lacks the required scientific boundary")
    if config["allowed_claim"] not in manuscript:
        raise PublicationHandoffError("Manuscript lacks the locked allowed claim")
    return paths


def _write_gate27(config: Mapping[str, Any], paths: Mapping[str, Path]) -> tuple[Path, Path, Path]:
    result_path = GATE27_ROOT / "results/internal_scientific_review_audit.json"
    manifest_path = GATE27_ROOT / "manifests/internal_scientific_review_manifest.json"
    report_path = DOCS_ROOT / "gate_27_internal_scientific_review.md"
    result = {
        "schema_version": "gate-27-internal-review-audit-v1",
        "status": "INTERNAL_REVIEW_PACKAGE_READY",
        "human_scientific_review_completed": False,
        "claim_lock_verified": True,
        "pozo_directionality": "PASS",
        "pozo_quantitative_ratio": "MISMATCH",
        "gene_specific_validation": False,
        "biological_parkinson_validation": False,
        "required_human_reviews": [
            "Methods/statistics review by a domain reviewer",
            "Claim/limitation review by supervisor or corresponding author",
            "Authorship, contribution and conflict-of-interest confirmation",
        ],
    }
    _write_json(result_path, result)
    _write_text(
        report_path,
        f"""# Gate 27: Internal scientific review package

**Status:** `INTERNAL_REVIEW_PACKAGE_READY`

Gate 27 kiem tra claim lock, provenance freeze va manuscript Gate 26. Ket qua
computational duoc bao cao nhu sau:

> {config['allowed_claim']}

Pozo directionality la `PASS`; quantitative ratio la `MISMATCH`. Gate nay
khong tu dong tao peer review va khong coi reviewer chua xac dinh la da dong y.

## Viec can nguoi that xac nhan

1. Domain reviewer kiem tra Methods, metric va gioi han assay.
2. Giang vien huong dan/corresponding author duyet claim va limitations.
3. Toan bo tac gia duyet authorship, contribution, funding va conflict of interest.
""",
    )
    source_records = [_record(path, "frozen_source") for path in paths.values()]
    manifest = {
        "schema_version": "gate-27-internal-review-manifest-v1",
        "status": result["status"],
        "analysis_only": True,
        "human_scientific_review_completed": False,
        "source_artifacts": source_records,
        "result": _relative(result_path),
        "report": _relative(report_path),
    }
    _write_json(manifest_path, manifest)
    return result_path, manifest_path, report_path


def _write_gate28() -> tuple[Path, Path, Path, list[Path]]:
    result_path = GATE28_ROOT / "results/archive_metadata_audit.json"
    manifest_path = GATE28_ROOT / "manifests/archive_metadata_manifest.json"
    report_path = DOCS_ROOT / "gate_28_archive_metadata.md"
    package = SUBMISSION_ROOT / "gate_28_archive_metadata"
    license_present = any((ROOT / name).is_file() for name in ("LICENSE", "LICENSE.md", "COPYING"))
    citation_present = any((ROOT / name).is_file() for name in ("CITATION.cff", "CITATION.md"))
    result = {
        "schema_version": "gate-28-archive-metadata-audit-v1",
        "status": "ARCHIVE_METADATA_PENDING_HUMAN_DECISIONS",
        "repository_license_present": license_present,
        "citation_metadata_present": citation_present,
        "doi_minted": False,
        "archive_deposited": False,
        "required_human_decisions": [
            "Choose a repository license compatible with all dependencies and bundled materials",
            "Confirm author order, affiliations and ORCID identifiers",
            "Create a GitHub release and archive DOI through an authorized account",
            "Confirm data/video hosting and licensing for any large external artifact",
        ],
    }
    _write_json(result_path, result)
    citation_template = """# CITATION.cff template - complete only after author confirmation
cff-version: 1.2.0
message: "If you use this software, please cite it after author approval."
title: "Drosophila Parkinson-like Locomotion Proxy"
version: "TO_BE_ASSIGNED_AT_RELEASE"
date-released: "TO_BE_ASSIGNED_AT_RELEASE"
authors:
  - family-names: "AUTHOR_FAMILY_NAME_REQUIRED"
    given-names: "AUTHOR_GIVEN_NAMES_REQUIRED"
repository-code: "https://github.com/TanVi3001/drosophila-pd-neural-disease"
license: "LICENSE_DECISION_REQUIRED"
"""
    zenodo_template = """{
  "title": "Drosophila Parkinson-like Locomotion Proxy",
  "upload_type": "software",
  "description": "AUTHOR-APPROVED DESCRIPTION REQUIRED. The release must retain the computational-proxy claim boundary.",
  "creators": [
    {"name": "AUTHOR_NAME_REQUIRED", "affiliation": "AFFILIATION_REQUIRED", "orcid": "OPTIONAL_ORCID"}
  ],
  "license": "LICENSE_DECISION_REQUIRED",
  "related_identifiers": []
}
"""
    data_statement = """# Data and code availability statement template

Code, compact metrics, manifests and checksums are available in the public
repository after release authorization. Raw simulation/video/checkpoint files
must be deposited only when their license, consent and storage location have
been reviewed. Insert the final DOI and archive URL only after an authorized
Zenodo or institutional archive deposition.
"""
    _write_text(package / "CITATION.cff.template", citation_template)
    _write_text(package / "zenodo.json.template", zenodo_template)
    _write_text(package / "data_availability_statement.md", data_statement)
    _write_text(
        report_path,
        """# Gate 28: Archive and metadata handoff

**Status:** `ARCHIVE_METADATA_PENDING_HUMAN_DECISIONS`

Gate 28 tao template CITATION, Zenodo va data-availability. Repository hien
chua co license/CITATION release da duoc con nguoi xac nhan, DOI hay archive
deposit. Khong duoc tao DOI, gan license hay gan tac gia bang script nay.
""",
    )
    generated = [package / "CITATION.cff.template", package / "zenodo.json.template", package / "data_availability_statement.md", report_path]
    manifest = {
        "schema_version": "gate-28-archive-metadata-manifest-v1",
        "status": result["status"],
        "analysis_only": True,
        "no_external_upload": True,
        "result": _relative(result_path),
        "generated_templates": [_relative(path) for path in generated],
    }
    _write_json(manifest_path, manifest)
    return result_path, manifest_path, report_path, generated


def _write_gate29() -> tuple[Path, Path, Path, list[Path]]:
    result_path = GATE29_ROOT / "results/submission_readiness.json"
    manifest_path = GATE29_ROOT / "manifests/submission_readiness_manifest.json"
    report_path = DOCS_ROOT / "gate_29_submission_readiness.md"
    package = SUBMISSION_ROOT / "gate_29_submission_metadata"
    result = {
        "schema_version": "gate-29-submission-readiness-v1",
        "status": "SUBMISSION_METADATA_PENDING_HUMAN_SIGNOFF",
        "external_submission_executed": False,
        "required_missing_fields": [
            "target_venue",
            "author_order_and_affiliations",
            "corresponding_author",
            "funding_statement",
            "conflict_of_interest_statement",
            "supervisor_and_coauthor_approval",
            "venue_specific_formatting",
        ],
        "scientific_scope": "bounded computational locomotion proxy",
    }
    _write_json(result_path, result)
    metadata_template = """# Fill with real, approved submission metadata only.
target_venue: TARGET_VENUE_REQUIRED
article_type: ORIGINAL_RESEARCH_OR_SOFTWARE_REQUIRED
corresponding_author: NAME_EMAIL_REQUIRED
authors:
  - name: AUTHOR_NAME_REQUIRED
    affiliation: AFFILIATION_REQUIRED
    orcid: OPTIONAL_ORCID
funding_statement: FUNDING_OR_NO_FUNDING_DECLARATION_REQUIRED
conflict_of_interest_statement: COI_DECLARATION_REQUIRED
ethics_statement: NOT_APPLICABLE_OR_APPROVED_STATEMENT_REQUIRED
supervisor_approval: PENDING
coauthor_approval: PENDING
"""
    cover_letter = """# Cover letter template

Dear Editor,

We submit a manuscript describing a provenance-tracked computational locomotion
proxy for Drosophila Parkinson-like phenotypes. The manuscript reports Chen
calibration, independent confirmation, directional Pozo holdout concordance and
the remaining quantitative mismatch. It does not claim biological,
gene-specific, clinical or therapeutic validation.

Replace all author, venue, originality and conflict-of-interest statements only
after approval by the corresponding author and coauthors.
"""
    contributions = """# CRediT contribution template

| Contributor | Roles | Approved by contributor |
| --- | --- | --- |
| AUTHOR_NAME_REQUIRED | Conceptualization; Methodology; Software; Validation; Writing | PENDING |

Do not infer authorship from Git history. Each contributor must confirm this
table before submission.
"""
    _write_text(package / "submission_metadata_template.yaml", metadata_template)
    _write_text(package / "cover_letter_template.md", cover_letter)
    _write_text(package / "contributions_template.md", contributions)
    _write_text(
        report_path,
        """# Gate 29: Venue submission readiness

**Status:** `SUBMISSION_METADATA_PENDING_HUMAN_SIGNOFF`

Gate 29 da tao template venue, authorship, cover letter va CRediT. Chua co
venue, tac gia/affiliation, funding/COI hay phe duyet cua tac gia nen script
khong the nop bai hay gan trang thai submitted.
""",
    )
    generated = [package / "submission_metadata_template.yaml", package / "cover_letter_template.md", package / "contributions_template.md", report_path]
    manifest = {
        "schema_version": "gate-29-submission-readiness-manifest-v1",
        "status": result["status"],
        "analysis_only": True,
        "external_submission_executed": False,
        "result": _relative(result_path),
        "generated_templates": [_relative(path) for path in generated],
    }
    _write_json(manifest_path, manifest)
    return result_path, manifest_path, report_path, generated


def _write_gate30(
    config: Mapping[str, Any],
    gate27: tuple[Path, Path, Path],
    gate28: tuple[Path, Path, Path, list[Path]],
    gate29: tuple[Path, Path, Path, list[Path]],
) -> tuple[Path, Path, Path]:
    result_path = GATE30_ROOT / "results/publication_handoff.json"
    manifest_path = GATE30_ROOT / "manifests/publication_handoff_manifest.json"
    checksums_path = GATE30_ROOT / "manifests/checksums.sha256"
    report_path = DOCS_ROOT / "gate_30_publication_handoff.md"
    package = SUBMISSION_ROOT / "gate_30_publication_handoff"
    gate27_result = _read_json(gate27[0])
    gate28_result = _read_json(gate28[0])
    gate29_result = _read_json(gate29[0])
    result = {
        "schema_version": "gate-30-publication-handoff-v1",
        "status": "PUBLICATION_HANDOFF_PENDING_HUMAN_AUTHORIZATION",
        "external_release_created": False,
        "external_submission_executed": False,
        "gate_27_status": gate27_result["status"],
        "gate_28_status": gate28_result["status"],
        "gate_29_status": gate29_result["status"],
        "next_human_actions": [
            "Approve license and authorship metadata",
            "Select target venue and apply its author guidelines",
            "Obtain supervisor/coauthor signoff",
            "Create an authorized GitHub Release and archive DOI if desired",
            "Submit through the selected venue portal using the approved account",
        ],
    }
    _write_json(result_path, result)
    _write_text(
        package / "README.md",
        """# Gate 30 Publication Handoff

This package is a local handoff only. It does not create a GitHub Release,
Zenodo DOI, journal submission, author list, license, or claim of acceptance.

## Required human sequence

1. Complete and approve Gate 28 archive metadata.
2. Complete and approve Gate 29 submission metadata.
3. Ask every author and the supervisor to approve manuscript, figures, tables,
   claims, limitations and venue choice.
4. Create the external release/archive from an authorized account.
5. Submit through the selected venue portal and store the confirmation outside
   this repository if it contains personal or editorial information.
""",
    )
    _write_text(
        report_path,
        """# Gate 30: Publication handoff

**Status:** `PUBLICATION_HANDOFF_PENDING_HUMAN_AUTHORIZATION`

Code-side packaging is complete, but public release/submission is deliberately
not automated. License, author list, affiliations, venue, funding/COI,
supervisor approval, archive DOI and portal submission require real human
authorization. The scientific claim stays bounded to a computational proxy.
""",
    )
    source_paths = [
        DEFAULT_CONFIG,
        *gate27,
        gate28[0], gate28[1], gate28[2], *gate28[3],
        gate29[0], gate29[1], gate29[2], *gate29[3],
        ROOT / "experiments/gate_26_submission_package/manifests/submission_package_manifest.json",
        ROOT / "submission/gate_26/manuscript_vi.md",
    ]
    source_records = [_record(path, "handoff_input") for path in source_paths]
    manifest = {
        "schema_version": "gate-30-publication-handoff-manifest-v1",
        "status": result["status"],
        "analysis_only": True,
        "no_external_release": True,
        "no_external_submission": True,
        "scientific_claim": config["allowed_claim"],
        "source_artifacts": source_records,
        "result": _relative(result_path),
        "report": _relative(report_path),
        "handoff_readme": _relative(package / "README.md"),
    }
    _write_json(manifest_path, manifest)
    checksum_inputs = [
        *source_records,
        _record(result_path, "handoff_output"),
        _record(report_path, "handoff_output"),
        _record(package / "README.md", "handoff_output"),
        _record(manifest_path, "handoff_output"),
    ]
    lines = [f"{record['sha256']}  {record['path']}" for record in sorted(checksum_inputs, key=lambda item: item["path"])]
    _write_text(checksums_path, "\n".join(lines))
    return result_path, manifest_path, checksums_path


def _write_publication_readme() -> Path:
    path = DOCS_ROOT / "README.md"
    if path.is_file() and "# Publication Handoff Gates 27--37" in path.read_text(encoding="utf-8"):
        return path
    _write_text(
        path,
        """# Publication Handoff Gates 27--30

| Gate | Purpose | Current status |
| --- | --- | --- |
| 27 | Internal scientific review package | `INTERNAL_REVIEW_PACKAGE_READY` |
| 28 | Archive/license/citation templates | `ARCHIVE_METADATA_PENDING_HUMAN_DECISIONS` |
| 29 | Venue submission metadata templates | `SUBMISSION_METADATA_PENDING_HUMAN_SIGNOFF` |
| 30 | Authorized publication handoff | `PUBLICATION_HANDOFF_PENDING_HUMAN_AUTHORIZATION` |

These gates do not submit to a venue or publish externally. They preserve the
Gate 24 claim boundary and make every human-only decision explicit.
""",
    )
    return path


def run_all(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Run Gate 27--30 package construction and return their exact statuses."""
    config = _read_config(config_path)
    paths = _validate_frozen_sources(config)
    gate27 = _write_gate27(config, paths)
    gate28 = _write_gate28()
    gate29 = _write_gate29()
    gate30 = _write_gate30(config, gate27, gate28, gate29)
    readme = _write_publication_readme()
    return {
        "gate_27": _read_json(gate27[0])["status"],
        "gate_28": _read_json(gate28[0])["status"],
        "gate_29": _read_json(gate29[0])["status"],
        "gate_30": _read_json(gate30[0])["status"],
        "publication_readme": _relative(readme),
        "handoff_manifest": _relative(gate30[1]),
        "handoff_checksums": _relative(gate30[2]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    try:
        result = run_all(args.config)
    except PublicationHandoffError as exc:
        print(f"Status: PUBLICATION_HANDOFF_FAILED\nReason: {exc}")
        return 1
    print("Gate 27: " + result["gate_27"])
    print("Gate 28: " + result["gate_28"])
    print("Gate 29: " + result["gate_29"])
    print("Gate 30: " + result["gate_30"])
    print("Handoff manifest: " + str(ROOT / result["handoff_manifest"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
