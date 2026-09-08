"""Import Gate 23 second-human signoff without changing mapping evidence."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
PARKIN = ROOT / "research/validation/gene_specific/parkin"
MAPPING = PARKIN / "driver_to_connectome_mapping.csv"
SIGNOFF = PARKIN / "driver_mapping_reviewer_signoff.json"
CONTRACT = PARKIN / "experiment_contract.yaml"
RESULT = ROOT / "experiments/gate_23_parkin_driver_defined_validation/results/gate23_signoff_import.json"
MANIFEST = ROOT / "experiments/gate_23_parkin_driver_defined_validation/manifests/gate23_signoff_import_manifest.json"

EXPECTED_ROOT_COUNT = 330
EXPECTED_SOURCE_SHA256 = "30be6c73975a70c56d930e27911f36455d3886e15abf383b78edd2a5d679e0b6"
EXPECTED_EXPORT_SHA256 = "4e381aa1e8d9f9e57e9961f8890e1132ad6b9d6a34e9e6c1e69c0effe21d68c8"
EXPECTED_MAPPING_LEVEL = "GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED"
PROPAGATED_FIELDS = ("reviewer_1", "reviewer_2", "review_date")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _valid_reviewer(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.upper() not in {"TBD", "TODO", "PENDING", "PLACEHOLDER", "<NAME>"}


def validate_signoff(signoff: dict[str, Any]) -> None:
    errors: list[str] = []
    for field in ("reviewer_1", "reviewer_2"):
        if not _valid_reviewer(signoff.get(field)):
            errors.append(f"invalid_{field}")
    review_date = str(signoff.get("review_date", ""))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", review_date):
        errors.append("invalid_review_date")
    if signoff.get("gene") != "parkin":
        errors.append("gene_must_be_parkin")
    if signoff.get("intervention") != "UAS-parkin-HMS01800-RNAi":
        errors.append("intervention_mismatch")
    if signoff.get("driver") != "TH-GAL4":
        errors.append("driver_mismatch")
    if signoff.get("decision") != "APPROVED_GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED":
        errors.append("invalid_decision")
    if signoff.get("mapping_level") != EXPECTED_MAPPING_LEVEL:
        errors.append("invalid_mapping_level")
    if signoff.get("direct_gene_expression_mapping") is not False:
        errors.append("direct_gene_expression_mapping_must_be_false")
    if "Parkin-expression-specific" in str(signoff.get("allowed_claim", "")):
        errors.append("allowed_claim_must_not_be_expression_specific")
    if errors:
        raise ValueError("Invalid Gate 23 signoff: " + ", ".join(errors))


def load_mapping(path: Path = MAPPING) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("mapping_has_no_header")
        return list(reader.fieldnames), list(reader)


def validate_mapping(fieldnames: list[str], rows: list[dict[str, str]]) -> list[str]:
    required = {
        "gene", "intervention", "driver", "root_id", "edge_id", "source_url",
        "source_sha256", "export_sha256", "reviewer_1", "reviewer_2",
        "review_date", "mapping_level", "notes",
    }
    missing = required.difference(fieldnames)
    if missing:
        raise ValueError(f"mapping_missing_columns={sorted(missing)}")
    if len(rows) != EXPECTED_ROOT_COUNT:
        raise ValueError(f"target_count={len(rows)} expected={EXPECTED_ROOT_COUNT}")
    roots = [row["root_id"] for row in rows]
    if len(set(roots)) != EXPECTED_ROOT_COUNT:
        raise ValueError("duplicate_root_id")
    for row in rows:
        if row["gene"] != "parkin":
            raise ValueError("gene_must_be_parkin")
        if row["intervention"] != "UAS-parkin-HMS01800-RNAi":
            raise ValueError("intervention_mismatch")
        if row["driver"] != "TH-GAL4":
            raise ValueError("driver_mismatch")
        if not row["root_id"].isdigit():
            raise ValueError("root_id_must_be_numeric")
        if row["edge_id"]:
            raise ValueError("unexpected_edge_id")
        if row["mapping_level"] != EXPECTED_MAPPING_LEVEL:
            raise ValueError("mapping_level_mismatch")
        if row["source_sha256"] != EXPECTED_SOURCE_SHA256:
            raise ValueError("source_sha256_mismatch")
        if row["export_sha256"] != EXPECTED_EXPORT_SHA256:
            raise ValueError("export_sha256_mismatch")
        if not row["source_url"]:
            raise ValueError("source_url_missing")
        if "Parkin-expression-specific" not in row["notes"]:
            raise ValueError("mapping_boundary_missing")
    return roots


def propagate_signoff(rows: list[dict[str, str]], signoff: dict[str, Any]) -> list[dict[str, str]]:
    validate_signoff(signoff)
    updated = [dict(row) for row in rows]
    for row in updated:
        for field in PROPAGATED_FIELDS:
            row[field] = str(signoff[field])
    return updated


def _write_mapping(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        # Preserve the repository's existing CSV line endings so the signoff
        # import shows only the reviewed metadata changes in the diff.
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def _update_contract(signoff: dict[str, Any]) -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8")) or {}
    protected = {key: contract.get(key) for key in ("intervention", "control", "assays", "sample_sizes", "statistics")}
    contract["review"] = {
        "reviewer_1": signoff["reviewer_1"],
        "reviewer_2": signoff["reviewer_2"],
        "review_date": signoff["review_date"],
        "decision": signoff["decision"],
        "evidence_boundary": (
            "Exact Parkin intervention and matched control are locked. The connectome "
            "target is TH-GAL4/driver-defined and is not Parkin-expression-specific."
        ),
    }
    for key, value in protected.items():
        if contract.get(key) != value:
            raise ValueError(f"protected_contract_field_changed={key}")
    CONTRACT.write_text(yaml.safe_dump(contract, sort_keys=False, allow_unicode=False), encoding="utf-8")


def apply_signoff(
    mapping_path: Path = MAPPING,
    signoff_path: Path = SIGNOFF,
    contract_path: Path = CONTRACT,
) -> dict[str, Any]:
    global CONTRACT
    CONTRACT = contract_path
    signoff = json.loads(signoff_path.read_text(encoding="utf-8"))
    validate_signoff(signoff)
    fieldnames, before_rows = load_mapping(mapping_path)
    before_roots = validate_mapping(fieldnames, before_rows)
    before_hash = sha256_file(mapping_path)
    after_rows = propagate_signoff(before_rows, signoff)
    for before, after in zip(before_rows, after_rows):
        for field in fieldnames:
            if field not in PROPAGATED_FIELDS and before[field] != after[field]:
                raise ValueError(f"unexpected_mapping_field_change={field}")
    after_roots = validate_mapping(fieldnames, after_rows)
    if before_roots != after_roots:
        raise ValueError("root_id_set_changed")
    _write_mapping(mapping_path, fieldnames, after_rows)
    _update_contract(signoff)
    after_hash = sha256_file(mapping_path)
    result = {
        "schema_version": "gate-23f-signoff-import-v1",
        "status": "SIGNOFF_IMPORTED",
        "reviewer_1": signoff["reviewer_1"],
        "reviewer_2": signoff["reviewer_2"],
        "review_date": signoff["review_date"],
        "decision": signoff["decision"],
        "root_id_count_before": len(before_roots),
        "root_id_count_after": len(after_roots),
        "root_id_set_changed": before_roots != after_roots,
        "mapping_sha256_before": before_hash,
        "mapping_sha256_after": after_hash,
        "source_sha256_preserved": all(row["source_sha256"] == EXPECTED_SOURCE_SHA256 for row in after_rows),
        "export_sha256_preserved": all(row["export_sha256"] == EXPECTED_EXPORT_SHA256 for row in after_rows),
        "mapping_fields_changed": list(PROPAGATED_FIELDS),
        "gpu_executed": False,
        "simulation_executed": False,
        "calibration_executed": False,
        "tuning_executed": False,
        "data_fabricated": False,
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "gate-23f-signoff-import-manifest-v1",
        "gate": "gate_23_parkin_driver_defined_validation",
        "status": "SIGNOFF_IMPORTED",
        "signoff_sha256": sha256_file(signoff_path),
        "mapping_sha256_before": before_hash,
        "mapping_sha256_after": after_hash,
        "root_id_count_before": len(before_roots),
        "root_id_count_after": len(after_roots),
        "root_id_set_changed": False,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "export_sha256": EXPECTED_EXPORT_SHA256,
        "simulation_run": False,
        "data_fabricated": False,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = apply_signoff()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
