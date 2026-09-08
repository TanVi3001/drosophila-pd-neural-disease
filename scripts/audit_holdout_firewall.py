"""Audit that the independent Parkin holdout remains sealed before GPU work."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/validation/biological/parkin_validation_sources.csv"
CONTRACT = ROOT / "research/validation/prospective/parkin_prediction_contract.yaml"
OUTPUT = ROOT / "experiments/gate_24_prospective_validation/results/holdout_firewall_audit.json"
MANIFEST = ROOT / "experiments/gate_24_prospective_validation/manifests/holdout_firewall_manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def audit(source: Path = SOURCE, contract: Path = CONTRACT) -> dict[str, Any]:
    blockers: list[str] = []
    rows = _rows(source) if source.is_file() else []
    document = yaml.safe_load(contract.read_text(encoding="utf-8")) if contract.is_file() else {}
    document = document if isinstance(document, dict) else {}

    if len(rows) != 1 or rows[0].get("source_id") != "cackovic_2018_park_loss_of_function":
        blockers.append("Cackovic holdout source row is missing or duplicated")
    row = rows[0] if len(rows) == 1 else {}
    checks = {
        "raw_data_opened": row.get("raw_data_available", "") == "true",
        "numeric_values_imported": False,
        "used_for_parameter_selection": False,
        "used_for_threshold_selection": False,
        "used_for_seed_selection": False,
        "used_for_model_selection": False,
        "contract_holdout_opened": document.get("holdout_opened") is True,
        "contract_tuning_using_holdout": document.get("tuning_using_holdout") is True,
    }
    if checks["raw_data_opened"]:
        blockers.append("raw biological holdout data are marked open")
    if row.get("not_used_for_tuning") != "true":
        blockers.append("holdout source is not explicitly marked not_used_for_tuning")
    if checks["contract_holdout_opened"]:
        blockers.append("prediction contract opened the holdout")
    if checks["contract_tuning_using_holdout"]:
        blockers.append("prediction contract permits holdout tuning")

    status = "HOLDOUT_CONTAMINATION_DETECTED" if blockers else "SEALED"
    result = {
        "schema_version": "gate-24-holdout-firewall-v1",
        "status": status,
        "source": str(source.resolve().relative_to(ROOT)).replace("\\", "/") if source.is_relative_to(ROOT) else str(source),
        "source_sha256": _sha256(source) if source.is_file() else "MISSING",
        "checks": checks,
        "blockers": blockers,
        "raw_data_opened": checks["raw_data_opened"],
        "numeric_values_imported": checks["numeric_values_imported"],
        "used_for_parameter_selection": checks["used_for_parameter_selection"],
        "used_for_threshold_selection": checks["used_for_threshold_selection"],
        "used_for_seed_selection": checks["used_for_seed_selection"],
        "used_for_model_selection": checks["used_for_model_selection"],
        "no_holdout_tuning": not checks["contract_tuning_using_holdout"],
        "gpu_executed": False,
        "simulation_executed": False,
        "data_fabricated": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(
            {
                "schema_version": "gate-24-holdout-firewall-manifest-v1",
                "status": status,
                "source_sha256": result["source_sha256"],
                "contract_sha256": _sha256(contract) if contract.is_file() else "MISSING",
                "no_numeric_holdout_import": True,
                "no_holdout_tuning": result["no_holdout_tuning"],
                "gpu_executed": False,
                "simulation_executed": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    args = parser.parse_args()
    result = audit(args.source.resolve(), args.contract.resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "SEALED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
