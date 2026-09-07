"""Create authorization-gated local artifacts for publication Gates 31--37.

This workflow prepares templates and reads only existing, human-supplied local
receipts. It cannot create an external release, DOI, venue submission, review
decision, or acceptance. It also never runs GPU, simulation, or tuning.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "experiments/gate_31_internal_scientific_signoff/configs/publication_control_plane.yaml"
DOCS = ROOT / "docs/publication"
SUBMISSION = ROOT / "submission"


class PublicationControlPlaneError(ValueError):
    """A frozen source or authorization boundary is invalid."""


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
        raise PublicationControlPlaneError(f"Path outside repository: {path}") from exc


def _write_text(path: Path, lines: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")


def _write_json(path: Path, content: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationControlPlaneError(f"Invalid JSON: {_relative(path)}") from exc
    if not isinstance(content, dict):
        raise PublicationControlPlaneError(f"Expected JSON object: {_relative(path)}")
    return content


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise PublicationControlPlaneError(f"Invalid YAML: {_relative(path)}") from exc
    if not isinstance(content, dict):
        raise PublicationControlPlaneError(f"Expected YAML mapping: {_relative(path)}")
    return content


def _optional_yaml(path: Path) -> dict[str, Any] | None:
    return _read_yaml(path) if path.is_file() else None


def _optional_json(path: Path) -> dict[str, Any] | None:
    return _read_json(path) if path.is_file() else None


def _record(path: Path, role: str) -> dict[str, Any]:
    if not path.is_file():
        raise PublicationControlPlaneError(f"Missing artifact: {_relative(path)}")
    return {"path": _relative(path), "role": role, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}


def _gate_root(gate: int) -> Path:
    suffix = {
        31: "internal_scientific_signoff", 32: "metadata_finalization",
        33: "venue_manuscript", 34: "public_archive", 35: "external_submission",
        36: "reviewer_response", 37: "acceptance_archive",
    }[gate]
    return ROOT / "experiments" / f"gate_{gate}_{suffix}"


def _placeholder(value: Any) -> bool:
    if value is None or not isinstance(value, str):
        return value is None
    value = value.strip().upper()
    return not value or value in {"PENDING", "TBD", "UNKNOWN", "N/A"} or "REQUIRED" in value or "YYYY-MM-DD" in value


def _valid_date(value: Any) -> bool:
    if _placeholder(value):
        return False
    try:
        date.fromisoformat(str(value))
    except ValueError:
        return False
    return True


def _valid_fields(document: Mapping[str, Any] | None, fields: Sequence[str], *, date_field: str | None, missing_file: str) -> tuple[bool, list[str]]:
    if document is None:
        return False, [f"{missing_file} is absent"]
    blockers: list[str] = []
    for field in fields:
        value = document.get(field)
        if _placeholder(value) or (field == date_field and not _valid_date(value)):
            blockers.append(f"missing field: {field}")
    return not blockers, blockers


def _validate_config(config: Mapping[str, Any]) -> dict[str, Path]:
    disabled = (
        "run_gpu", "run_simulation", "run_calibration", "run_holdout_validation",
        "run_tuning", "create_external_release", "submit_to_venue",
    )
    if config.get("analysis_only") is not True or any(config.get(field) is not False for field in disabled):
        raise PublicationControlPlaneError("Gate 31--37 must stay authorization-gated and local")
    sources = {name: ROOT / relative for name, relative in config["sources"].items()}
    if _read_json(sources["gate_26_manifest"]).get("status") != "SUBMISSION_PACKAGE_READY_FOR_INTERNAL_REVIEW":
        raise PublicationControlPlaneError("Gate 26 package status is invalid")
    if _read_json(sources["gate_30_manifest"]).get("status") != "PUBLICATION_HANDOFF_PENDING_HUMAN_AUTHORIZATION":
        raise PublicationControlPlaneError("Gate 30 authorization boundary is invalid")
    manuscript = sources["manuscript"].read_text(encoding="utf-8")
    if config["allowed_claim"] not in manuscript:
        raise PublicationControlPlaneError("The Gate 26 manuscript lacks the allowed claim")
    if "not a biological, gene-specific, clinical, or therapeutic validation" not in " ".join(manuscript.split()):
        raise PublicationControlPlaneError("The Gate 26 manuscript lacks its claim boundary")
    return sources


def _signoff_state(document: Mapping[str, Any] | None) -> tuple[bool, list[str]]:
    if document is None:
        return False, ["publication_signoff.local.yaml is absent"]
    signoff = document.get("internal_signoff")
    blockers: list[str] = []
    if not isinstance(signoff, dict):
        blockers.append("internal_signoff is absent")
    else:
        for key in ("scientific_reviewer", "methods_reviewer", "corresponding_author"):
            signer = signoff.get(key)
            if not isinstance(signer, dict) or _placeholder(signer.get("name")) or _placeholder(signer.get("role")) or not _valid_date(signer.get("date")) or str(signer.get("decision", "")).lower() != "approved":
                blockers.append(f"invalid approved signoff: {key}")
    confirmations = document.get("scientific_confirmations")
    if not isinstance(confirmations, dict):
        blockers.append("scientific_confirmations is absent")
    else:
        for key in ("methods_figures_reviewed", "pozo_mismatch_retained", "claim_lock_accepted"):
            if confirmations.get(key) is not True:
                blockers.append(f"confirmation is not true: {key}")
    if document.get("all_authors_approved") is not True:
        blockers.append("all_authors_approved is not true")
    return not blockers, blockers


def _metadata_state(document: Mapping[str, Any] | None) -> tuple[bool, list[str]]:
    if document is None or not isinstance(document.get("publication_metadata"), dict):
        return False, ["publication_metadata is absent"]
    metadata = document["publication_metadata"]
    ok, blockers = _valid_fields(metadata, ("license_identifier", "target_venue", "corresponding_author", "funding_statement", "conflict_of_interest_statement", "ethics_statement"), date_field=None, missing_file="publication_signoff.local.yaml")
    authors = metadata.get("authors")
    if not isinstance(authors, list) or not authors:
        blockers.append("authors are missing")
    else:
        for index, author in enumerate(authors, start=1):
            if not isinstance(author, dict) or _placeholder(author.get("name")) or _placeholder(author.get("affiliation")):
                blockers.append(f"author {index} name/affiliation is missing")
    return ok and not blockers, blockers


def _write_gate(gate: int, result_name: str, status: str, details: Mapping[str, Any], report_name: str, report_lines: Sequence[str], extra: Mapping[str, Any] | None = None) -> tuple[Path, Path, Path]:
    result = _gate_root(gate) / "results" / result_name
    report = DOCS / report_name
    manifest = _gate_root(gate) / "manifests" / result_name.replace("status", "manifest")
    _write_json(result, {"schema_version": f"gate-{gate}-status-v1", "status": status, **details})
    _write_text(report, report_lines)
    content: dict[str, Any] = {"schema_version": f"gate-{gate}-manifest-v1", "status": status, "analysis_only": True, "result": _relative(result), "report": _relative(report)}
    if extra:
        content.update(extra)
    _write_json(manifest, content)
    return result, manifest, report


def _write_templates() -> dict[str, list[Path]]:
    locations = {
        "signoff": SUBMISSION / "gate_31_internal_scientific_signoff/publication_signoff.local.yaml.example",
        "venue": SUBMISSION / "gate_33_venue_manuscript/manuscript_en_venue_template.md",
        "refs": SUBMISSION / "gate_33_venue_manuscript/references.bib.template",
        "archive": SUBMISSION / "gate_34_public_archive/archive_receipt.local.yaml.example",
        "submission": SUBMISSION / "gate_35_external_submission/submission_receipt.local.json.example",
        "decision": SUBMISSION / "gate_36_reviewer_response/editorial_decision.local.yaml.example",
        "ledger": SUBMISSION / "gate_36_reviewer_response/reviewer_response_ledger.md",
        "acceptance": SUBMISSION / "gate_37_acceptance_archive/acceptance_record.local.yaml.example",
        "checklist": SUBMISSION / "gate_37_acceptance_archive/camera_ready_checklist.md",
    }
    _write_text(locations["signoff"], ["# Copy to publication_signoff.local.yaml after real approval. Do not commit it.", "internal_signoff:", "  scientific_reviewer: {name: PENDING, role: PENDING, date: YYYY-MM-DD, decision: pending}", "  methods_reviewer: {name: PENDING, role: PENDING, date: YYYY-MM-DD, decision: pending}", "  corresponding_author: {name: PENDING, role: PENDING, date: YYYY-MM-DD, decision: pending}", "all_authors_approved: false", "scientific_confirmations: {methods_figures_reviewed: false, pozo_mismatch_retained: false, claim_lock_accepted: false}", "publication_metadata:", "  license_identifier: PENDING", "  target_venue: PENDING", "  corresponding_author: PENDING", "  authors: [{name: PENDING, affiliation: PENDING, orcid: OPTIONAL}]", "  funding_statement: PENDING", "  conflict_of_interest_statement: PENDING", "  ethics_statement: PENDING"])
    _write_text(locations["venue"], ["# Venue-specific manuscript template", "", "This manuscript reports Chen calibration, independent confirmation, Pozo directional concordance and the retained quantitative mismatch.", "It is not a biological, gene-specific, clinical or therapeutic validation.", "", "Apply author-approved venue formatting, references, declarations and page limits only after Gate 31 and Gate 32."])
    _write_text(locations["refs"], ["% Verify publisher records before final submission.", "@article{Chen2014, title = {AUTHOR-VERIFIED CHEN 2014 REFERENCE REQUIRED} }", "@article{Pozo2022, title = {AUTHOR-VERIFIED POZO 2022 REFERENCE REQUIRED}, doi = {10.3390/cells11091544} }"])
    _write_text(locations["archive"], ["github_release_url: PENDING", "archive_url: PENDING", "doi: PENDING", "released_by: PENDING", "release_date: YYYY-MM-DD"])
    _write_text(locations["submission"], ["{", "  \"venue\": \"PENDING\",", "  \"submission_id\": \"PENDING\",", "  \"submission_date\": \"YYYY-MM-DD\",", "  \"submitted_by\": \"PENDING\"", "}"])
    _write_text(locations["decision"], ["decision: PENDING", "decision_date: YYYY-MM-DD", "recorded_by: PENDING", "editorial_reference: PENDING", "requires_new_experiment: false"])
    _write_text(locations["ledger"], ["# Reviewer response ledger", "", "| Reviewer comment | Response | Manuscript change | New experiment gate | Author approval |", "| --- | --- | --- | --- | --- |", "| PENDING | PENDING | PENDING | PENDING | PENDING |", "", "New experiments need a new config, manifest, checksum, QC and claim adjudication."])
    _write_text(locations["acceptance"], ["acceptance_date: YYYY-MM-DD", "venue: PENDING", "bibliographic_record_url: PENDING", "final_archive_url: PENDING", "camera_ready_approved: false", "recorded_by: PENDING"])
    _write_text(locations["checklist"], ["# Camera-ready checklist", "", "- [ ] Acceptance is recorded by the corresponding author.", "- [ ] Camera-ready PDF is author-approved.", "- [ ] Figure/table checksums match frozen evidence.", "- [ ] Bibliographic record and final archive URL are recorded."])
    return {"gate31": [locations["signoff"]], "gate33": [locations["venue"], locations["refs"]], "gate34": [locations["archive"]], "gate35": [locations["submission"]], "gate36": [locations["decision"], locations["ledger"]], "gate37": [locations["acceptance"], locations["checklist"]]}


def _write_checksums(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    _write_text(path, [f"{record['sha256']}  {record['path']}" for record in sorted(records, key=lambda item: item["path"])])


def run_all(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Refresh all Gate 31--37 artifacts from frozen inputs and optional receipts."""
    config = _read_yaml(config_path)
    sources = _validate_config(config)
    local = {name: ROOT / relative for name, relative in config["local_inputs"].items()}
    signoff = _optional_yaml(local["signoff"])
    archive = _optional_yaml(local["archive_receipt"])
    submitted = _optional_json(local["submission_receipt"])
    decision = _optional_yaml(local["editorial_decision"])
    acceptance = _optional_yaml(local["acceptance_record"])
    signoff_ok, signoff_blockers = _signoff_state(signoff)
    metadata_ok, metadata_blockers = _metadata_state(signoff)
    archive_ok, archive_blockers = _valid_fields(archive, ("github_release_url", "archive_url", "doi", "released_by", "release_date"), date_field="release_date", missing_file="archive_receipt.local.yaml")
    submitted_ok, submitted_blockers = _valid_fields(submitted, ("venue", "submission_id", "submission_date", "submitted_by"), date_field="submission_date", missing_file="submission_receipt.local.json")
    decision_ok, decision_blockers = _valid_fields(decision, ("decision", "decision_date", "recorded_by"), date_field="decision_date", missing_file="editorial_decision.local.yaml")
    accepted = decision_ok and str((decision or {}).get("decision", "")).lower() == "accept"
    acceptance_ok, acceptance_blockers = _valid_fields(acceptance, ("acceptance_date", "venue", "bibliographic_record_url", "final_archive_url", "recorded_by"), date_field="acceptance_date", missing_file="acceptance_record.local.yaml")
    if acceptance is not None and acceptance.get("camera_ready_approved") is not True:
        acceptance_ok = False
        acceptance_blockers.append("camera_ready_approved is not true")
    templates = _write_templates()
    statuses = {
        "gate_31": "INTERNAL_SCIENTIFIC_SIGNOFF_APPROVED" if signoff_ok else "WAITING_AUTHORIZED_INTERNAL_SIGNOFF",
        "gate_32": "PUBLICATION_METADATA_APPROVED" if metadata_ok else "WAITING_APPROVED_PUBLICATION_METADATA",
        "gate_33": "VENUE_MANUSCRIPT_READY_FOR_CORRESPONDING_AUTHOR" if signoff_ok and metadata_ok else "VENUE_MANUSCRIPT_TEMPLATE_READY",
        "gate_34": "PUBLIC_ARCHIVE_RELEASE_RECORDED" if signoff_ok and metadata_ok and archive_ok else "ARCHIVE_RELEASE_PENDING_AUTHORIZATION",
        "gate_35": "EXTERNAL_SUBMISSION_RECORDED" if archive_ok and submitted_ok else "EXTERNAL_SUBMISSION_PENDING_CORRESPONDING_AUTHOR",
        "gate_36": "EDITORIAL_DECISION_RECORDED" if submitted_ok and decision_ok else "WAITING_FOR_EDITORIAL_DECISION",
        "gate_37": "FINAL_PUBLICATION_ARCHIVE_RECORDED" if accepted and acceptance_ok else "WAITING_FOR_ACCEPTANCE",
    }
    gate31 = _write_gate(31, "internal_signoff_status.json", statuses["gate_31"], {"completed": signoff_ok, "blockers": signoff_blockers, "external_action": False}, "gate_31_internal_scientific_signoff.md", ["# Gate 31: Internal scientific signoff", "", f"**Status:** `{statuses['gate_31']}`", "", config["allowed_claim"], "", "Named reviewers must approve methods, figures, Pozo mismatch, claim lock and authorship.", "", *[f"- {item}" for item in signoff_blockers]], {"sources": [_record(path, "frozen_source") for path in sources.values()], "templates": [_relative(path) for path in templates["gate31"]]})
    gate32 = _write_gate(32, "metadata_finalization_status.json", statuses["gate_32"], {"completed": metadata_ok, "blockers": metadata_blockers, "license_created": False, "citation_created": False}, "gate_32_metadata_finalization.md", ["# Gate 32: Metadata finalization", "", f"**Status:** `{statuses['gate_32']}`", "", "License, authors, affiliation, ORCID, funding, COI and ethics statement require authorized human confirmation.", "", *[f"- {item}" for item in metadata_blockers]])
    gate33 = _write_gate(33, "venue_manuscript_status.json", statuses["gate_33"], {"signoff_completed": signoff_ok, "metadata_completed": metadata_ok, "external_submission": False}, "gate_33_venue_specific_manuscript.md", ["# Gate 33: Venue-specific manuscript", "", f"**Status:** `{statuses['gate_33']}`", "", "A venue-neutral English template is available. Final venue formatting waits for approved Gate 31/32 metadata."], {"templates": [_relative(path) for path in templates["gate33"]]})
    gate34 = _write_gate(34, "public_archive_status.json", statuses["gate_34"], {"archive_recorded": archive_ok, "blockers": archive_blockers, "external_release_created_by_script": False}, "gate_34_public_archive_release.md", ["# Gate 34: Public archive release", "", f"**Status:** `{statuses['gate_34']}`", "", "A DOI/release is recorded only after an authorized human supplies a real receipt."], {"templates": [_relative(path) for path in templates["gate34"]], "no_external_release_by_script": True})
    gate35 = _write_gate(35, "external_submission_status.json", statuses["gate_35"], {"submission_recorded": submitted_ok, "blockers": submitted_blockers, "external_submission_by_script": False}, "gate_35_external_submission.md", ["# Gate 35: External submission", "", f"**Status:** `{statuses['gate_35']}`", "", "Only the corresponding author can submit through the selected venue portal."], {"templates": [_relative(path) for path in templates["gate35"]], "no_external_submission_by_script": True})
    gate36 = _write_gate(36, "reviewer_response_status.json", statuses["gate_36"], {"editorial_decision_recorded": decision_ok, "blockers": decision_blockers, "new_experiment_by_script": False}, "gate_36_reviewer_response_revision.md", ["# Gate 36: Reviewer response and revision", "", f"**Status:** `{statuses['gate_36']}`", "", "Do not overwrite frozen metrics. New experiments require a new research gate."], {"templates": [_relative(path) for path in templates["gate36"]]})
    gate37 = _write_gate(37, "acceptance_archive_status.json", statuses["gate_37"], {"acceptance_recorded": acceptance_ok, "blockers": acceptance_blockers, "external_publication_by_script": False}, "gate_37_acceptance_final_archive.md", ["# Gate 37: Acceptance and final publication archive", "", f"**Status:** `{statuses['gate_37']}`", "", "Acceptance and camera-ready information are recorded only from authorized evidence."], {"templates": [_relative(path) for path in templates["gate37"]], "no_external_publication_by_script": True})
    status_path = _gate_root(37) / "results/publication_control_plane_status.json"
    _write_json(status_path, {"schema_version": "gates-31-37-status-v1", "status": "PUBLICATION_CONTROL_PLANE_READY", "gate_statuses": statuses, "no_external_release_created": True, "no_external_submission_executed": True, "next_required_human_file": _relative(local["signoff"])})
    paths = [config_path, *sources.values(), *gate31, *gate32, *gate33, *templates["gate33"], *gate34, *templates["gate34"], *gate35, *templates["gate35"], *gate36, *templates["gate36"], *gate37, *templates["gate37"], *templates["gate31"], status_path]
    records = [_record(path, "publication_control_plane") for path in paths]
    global_manifest = _gate_root(37) / "manifests/publication_control_plane_manifest.json"
    _write_json(global_manifest, {"schema_version": "gates-31-37-manifest-v1", "status": "PUBLICATION_CONTROL_PLANE_READY", "analysis_only": True, "no_gpu": True, "no_simulation": True, "no_calibration": True, "no_holdout_validation": True, "no_tuning": True, "no_external_release": True, "no_external_submission": True, "gate_statuses": statuses, "artifacts": records})
    records.append(_record(global_manifest, "publication_control_plane"))
    checksums = _gate_root(37) / "manifests/checksums.sha256"
    _write_checksums(checksums, records)
    return {"status": "PUBLICATION_CONTROL_PLANE_READY", "gate_statuses": statuses, "manifest": _relative(global_manifest), "checksums": _relative(checksums)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    try:
        outcome = run_all(args.config)
    except PublicationControlPlaneError as exc:
        print(f"Status: PUBLICATION_CONTROL_PLANE_FAILED\nReason: {exc}")
        return 1
    for gate, status in outcome["gate_statuses"].items():
        print(f"{gate}: {status}")
    print(f"Status: {outcome['status']}")
    print(f"Manifest: {ROOT / outcome['manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
