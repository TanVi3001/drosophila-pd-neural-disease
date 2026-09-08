"""Validate an externally supplied Parkin biological validation table.

This importer never creates biological measurements. With no input it writes a
waiting artifact; with input it rejects rows that cannot be traced to a real
biological replicate and source.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import yaml

from drosophila_pd_neural.riemensperger2011.protocol import sha256_file, write_json


CONTRACT = ROOT / "research/validation/biological/parkin_biological_data_contract.yaml"
DEFAULT_OUTPUT = ROOT / "experiments/gate_22g_real_biological_validation"
REQUIRED_FIELDS = (
    "experiment_id", "source_type", "genotype", "control_genotype", "driver",
    "sex", "age_days", "temperature", "assay", "arena", "duration",
    "sample_id", "biological_replicate", "metric", "unit", "statistic",
    "raw_data_path", "source", "DOI", "reviewer", "blinded",
    "used_for_calibration", "used_for_validation",
)
ALLOWED_SOURCE_TYPES = {
    "PUBLISHED_INDEPENDENT",
    "NEW_WETLAB",
    "EXTERNAL_COLLABORATOR",
    "HELD_OUT_PUBLIC_DATASET",
}
REJECTED_SOURCE_TYPES = {"SYNTHETIC", "GENERATED", "SIMULATION_AS_REAL"}


def _truth(value: object) -> bool | None:
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def validate_rows(rows: Iterable[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    seen_replicates: set[str] = set()
    for index, row in enumerate(rows, start=2):
        for field in REQUIRED_FIELDS:
            if not str(row.get(field, "")).strip():
                errors.append(f"row_{index}:missing_{field}")
        source_type = str(row.get("source_type", "")).strip()
        if source_type in REJECTED_SOURCE_TYPES:
            errors.append(f"row_{index}:rejected_source_type_{source_type}")
        elif source_type not in ALLOWED_SOURCE_TYPES:
            errors.append(f"row_{index}:invalid_source_type_{source_type or 'EMPTY'}")
        replicate = str(row.get("biological_replicate", "")).strip()
        if replicate and replicate in seen_replicates:
            errors.append(f"row_{index}:duplicate_biological_replicate_{replicate}")
        if replicate:
            seen_replicates.add(replicate)
        if _truth(row.get("used_for_calibration")) is not False:
            errors.append(f"row_{index}:used_for_calibration_must_be_false")
        if _truth(row.get("used_for_validation")) is not True:
            errors.append(f"row_{index}:used_for_validation_must_be_true")
        if str(row.get("sample_id", "")).strip() == str(row.get("biological_replicate", "")).strip() == "frame":
            errors.append(f"row_{index}:frame_cannot_be_biological_replicate")
    return errors


def import_validation_data(*, input_path: Path | None, output: Path, contract_path: Path = CONTRACT) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
    if input_path is None:
        result = {
            "status": "WAITING_BIOLOGICAL_VALIDATION_DATA",
            "primary_gene": "parkin",
            "rows_imported": 0,
            "errors": ["No biological validation input was supplied."],
            "simulation_as_real": False,
            "data_created": False,
            "used_for_calibration": False,
        }
    else:
        if not input_path.is_file():
            result = {
                "status": "WAITING_BIOLOGICAL_VALIDATION_DATA",
                "primary_gene": "parkin",
                "rows_imported": 0,
                "errors": [f"Input file not found: {input_path}"],
                "simulation_as_real": False,
                "data_created": False,
            }
        else:
            with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = [dict(row) for row in reader]
            errors = validate_rows(rows)
            result = {
                "status": "BIOLOGICAL_VALIDATION_DATA_READY" if rows and not errors else "BIOLOGICAL_VALIDATION_DATA_REJECTED",
                "primary_gene": "parkin",
                "rows_imported": len(rows) if not errors else 0,
                "input_path": str(input_path),
                "input_sha256": sha256_file(input_path),
                "errors": errors,
                "simulation_as_real": False,
                "data_created": False,
                "used_for_calibration": False,
            }
    result["contract_status"] = contract.get("status", "UNKNOWN")
    result["validation_unit"] = contract.get("policy", {}).get("unit_of_analysis", "biological_replicate")
    write_json(output / "results/biological_validation_import_summary.json", result)
    write_json(output / "manifests/biological_validation_import_manifest.json", {
        "schema_version": "gate-22-biological-validation-import-manifest-v1",
        "status": result["status"],
        "contract_sha256": sha256_file(contract_path),
        "input_sha256": result.get("input_sha256", "NOT_PROVIDED"),
        "rows_imported": result["rows_imported"],
        "data_created": False,
        "simulation_as_real": False,
    })
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = import_validation_data(input_path=args.input.resolve() if args.input else None, output=args.output.resolve(), contract_path=args.contract.resolve())
    print(f"Status: {result['status']}")
    return 0 if result["status"] != "BIOLOGICAL_VALIDATION_DATA_REJECTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
