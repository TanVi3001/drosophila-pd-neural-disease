"""Audit the Gate 22 gene-specific and biological validation ladder.

The audit is intentionally conservative: existing literature context can be
reported, but it cannot promote class-level mapping, a paper target, or a
simulation result into gene-specific biological validation.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.riemensperger2011.protocol import git_commit, read_json, sha256_file, write_json
from scripts.decide_gene_specific_validation import decide


TARGET = ROOT / "research/validation/claim_policy/validation_target.yaml"
CONFIG = ROOT / "configs/validation/gate_22_validation_ladder.yaml"
PARKIN = ROOT / "research/validation/gene_specific/parkin"
INTERVENTION = PARKIN / "intervention_evidence.yaml"
PHENOTYPE = PARKIN / "phenotype_evidence.csv"
MOLECULAR = PARKIN / "molecular_evidence.csv"
RESCUE = PARKIN / "rescue_evidence.csv"
MAPPING = PARKIN / "mapping_spec.yaml"
SIGNOFF = PARKIN / "reviewer_signoff.json"
BIO_CONTRACT = ROOT / "research/validation/biological/parkin_biological_data_contract.yaml"
PROSPECTIVE = ROOT / "research/validation/prospective/parkin_prediction_contract.yaml"
TRACK_A = ROOT / "experiments/gate_21f_four_group_analysis/results/four_group_summary.json"
BIO_IMPORT = ROOT / "experiments/gate_22g_real_biological_validation/results/biological_validation_import_summary.json"
VIRTUAL = ROOT / "experiments/gate_22f_blinded_virtual_prediction/results/virtual_prediction_summary.json"


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def _read_json(path: Path) -> dict[str, Any]:
    return read_json(path) if path.is_file() else {}


def _reviewer_ok(value: object) -> bool:
    text = str(value or "").strip().upper()
    return bool(text) and not text.startswith(("NOT_", "PENDING", "TODO", "TBD"))


def _gate_artifact(gate: str, status: str, result_name: str, result: dict[str, Any], inputs: Iterable[Path]) -> None:
    gate_dir = ROOT / "experiments" / gate
    result_path = gate_dir / "results" / result_name
    manifest_path = gate_dir / "manifests" / f"{Path(result_name).stem.replace('_summary', '')}_manifest.json"
    write_json(result_path, result)
    input_records = []
    for path in inputs:
        record: dict[str, Any] = {"path": str(path.resolve().relative_to(ROOT)).replace("\\", "/") if path.resolve().is_relative_to(ROOT) else str(path)}
        if path.is_file():
            record["sha256"] = sha256_file(path)
            record["size_bytes"] = path.stat().st_size
        else:
            record["status"] = "MISSING"
        input_records.append(record)
    write_json(manifest_path, {
        "schema_version": "gate-22-validation-manifest-v1",
        "gate": gate,
        "status": status,
        "git_commit": git_commit(),
        "inputs": input_records,
        "simulation_run": False,
        "biological_data_created": False,
        "data_fabricated": False,
    })


def audit() -> dict[str, Any]:
    target = _read_yaml(TARGET)
    intervention = _read_yaml(INTERVENTION)
    mapping = _read_yaml(MAPPING)
    signoff = _read_json(SIGNOFF)
    contract = _read_yaml(BIO_CONTRACT)
    prospective = _read_yaml(PROSPECTIVE)
    phenotype_rows = _read_rows(PHENOTYPE)
    molecular_rows = _read_rows(MOLECULAR)
    rescue_rows = _read_rows(RESCUE)
    biological = _read_json(BIO_IMPORT)
    virtual = _read_json(VIRTUAL)

    evidence_status = "GENE_SPECIFIC_EVIDENCE_INCOMPLETE"
    if intervention.get("status") == "GENE_SPECIFIC_EVIDENCE_LOCKED" and phenotype_rows:
        evidence_status = "GENE_SPECIFIC_EVIDENCE_LOCKED"
    mapping_status = str(mapping.get("status", "WAITING_GENE_SPECIFIC_MAPPING"))
    review_complete = all(_reviewer_ok(signoff.get(field)) for field in ("reviewer_1", "reviewer_2", "review_date")) and signoff.get("decision") not in {"", "PENDING_HUMAN_SIGNOFF"}
    biological_available = biological.get("status") == "BIOLOGICAL_VALIDATION_DATA_READY"
    molecular_status = "REPORTED_NOT_FULLY_LOCKED" if molecular_rows else "NOT_AVAILABLE"
    rescue_status = "AVAILABLE" if rescue_rows else "RESCUE_EVIDENCE_NOT_AVAILABLE"

    blockers = [
        "exact matched control genotype is not locked",
        "DAM beam-break activity is not a validated FlyGym planar-speed transfer",
        "direct Parkin gene-to-root-ID or gene-to-edge-ID mapping is absent",
        "two-human-review signoff for gene-specific mapping is incomplete",
        "prospective prediction contract is not locked",
        "independent biological validation dataset is absent",
    ]
    if not molecular_rows or any(row.get("review_status") != "APPROVED" for row in molecular_rows):
        blockers.append("molecular readout evidence requires second review")
    if not rescue_rows:
        blockers.append("rescue/orthogonal evidence is not available; no rescue claim is made")

    criteria = {
        "exact_gene_intervention": bool(intervention.get("exact_intervention")) and intervention.get("status") != "UNKNOWN",
        "matched_control": intervention.get("control_genotype") not in {None, "", "AGE_MATCHED_CONTROL_EXACT_GENOTYPE_NOT_LOCKED"},
        "biological_phenotype": bool(phenotype_rows),
        "gene_specific_mapping": mapping.get("mapping_level") in {"GENE_SPECIFIC_DIRECT", "GENE_SPECIFIC_DRIVER_LEVEL"} and bool(mapping.get("directly_supported_root_ids") or mapping.get("directly_supported_edge_ids")),
        "two_human_review": review_complete,
        "prospective_prediction": prospective.get("status") == "PROSPECTIVE_PREDICTION_LOCKED",
        "validation_not_used_for_tuning": contract.get("policy", {}).get("used_for_calibration") is False and contract.get("policy", {}).get("used_for_validation") is True,
        "direction_concordance": biological_available and biological.get("direction_concordance") is True,
        "quantitative_criterion": biological_available and biological.get("quantitative_match") is True,
        "qc_pass": biological_available and biological.get("qc_pass") is True,
        "no_claim_leakage": True,
    }
    decision_input = {
        "criteria": criteria,
        "biological_data_available": biological_available,
        "direction_concordance": biological.get("direction_concordance", "NOT_AVAILABLE"),
        "independent_biological_axis": False,
    }
    decision = decide(decision_input)
    status = "WAITING_BIOLOGICAL_VALIDATION_DATA" if not biological_available else decision["status"]
    result: dict[str, Any] = {
        "schema_version": "gate-22-gene-specific-validation-readiness-v1",
        "status": status,
        "primary_gene": target.get("primary_gene", "parkin"),
        "evidence": evidence_status,
        "mapping": mapping_status,
        "human_review": "COMPLETE" if review_complete else "INCOMPLETE",
        "prospective_prediction": prospective.get("status", "NOT_AVAILABLE"),
        "biological_holdout": biological.get("status", "WAITING_BIOLOGICAL_VALIDATION_DATA"),
        "molecular_evidence": molecular_status,
        "rescue_evidence": rescue_status,
        "real_phenotype": "EXISTS_NATIVE_DAM_NOT_FLYGYM_COMPARABLE" if phenotype_rows else "NOT_AVAILABLE",
        "virtual_phenotype": virtual.get("status", "WAITING_VALIDATION_RUNTIME"),
        "direction_concordance": biological.get("direction_concordance", "NOT_AVAILABLE"),
        "quantitative_match": biological.get("quantitative_match", "NOT_AVAILABLE"),
        "real_effect_ratio": biological.get("real_effect_ratio", "NOT_AVAILABLE"),
        "virtual_effect_ratio": biological.get("virtual_effect_ratio", "NOT_AVAILABLE"),
        "criteria": criteria,
        "decision": decision,
        "blockers": blockers,
        "data_fabricated": False,
        "biological_data_created": False,
        "simulation_run": False,
    }

    common_inputs = [TARGET, CONFIG, INTERVENTION, PHENOTYPE, MAPPING, SIGNOFF, BIO_CONTRACT, PROSPECTIVE]
    _gate_artifact("gate_22a_validation_target_lock", "VALIDATION_TARGET_LOCKED", "validation_target_summary.json", {"status": "VALIDATION_TARGET_LOCKED", "primary_gene": "parkin", "excluded_claims": target.get("excluded_claims", []), "data_fabricated": False}, [TARGET])
    _gate_artifact("gate_22b_gene_specific_evidence", evidence_status, "gene_specific_evidence_summary.json", {"status": evidence_status, "source_count": 1, "phenotype_rows": len(phenotype_rows), "directly_supported_root_ids": 0, "data_fabricated": False}, [INTERVENTION, PHENOTYPE, MOLECULAR, RESCUE])
    _gate_artifact("gate_22c_gene_to_neural_mapping", mapping_status, "gene_to_neural_mapping_summary.json", {"status": mapping_status, "mapping_level": mapping.get("mapping_level", "UNRESOLVED"), "directly_supported_root_ids": 0, "directly_supported_edge_ids": 0, "gene_specific_mapping": False, "data_fabricated": False}, [MAPPING, SIGNOFF])
    _gate_artifact("gate_22d_biological_data_contract", "WAITING_BIOLOGICAL_VALIDATION_DATA", "biological_data_contract_summary.json", {"status": "WAITING_BIOLOGICAL_VALIDATION_DATA", "source_types": contract.get("allowed_source_types", []), "data_fabricated": False}, [BIO_CONTRACT])
    _gate_artifact("gate_22e_preregistered_prediction", prospective.get("status", "WAITING_GENE_SPECIFIC_MAPPING"), "prospective_prediction_summary.json", {"status": prospective.get("status", "WAITING_GENE_SPECIFIC_MAPPING"), "holdout_opened": False, "data_fabricated": False}, [PROSPECTIVE])
    _gate_artifact("gate_22f_blinded_virtual_prediction", "WAITING_VALIDATION_RUNTIME", "virtual_prediction_summary.json", {"status": "WAITING_VALIDATION_RUNTIME", "simulation_run": False, "data_fabricated": False}, [CONFIG, MAPPING, PROSPECTIVE])
    _gate_artifact("gate_22g_real_biological_validation", biological.get("status", "WAITING_BIOLOGICAL_VALIDATION_DATA"), "biological_validation_summary.json", {"status": biological.get("status", "WAITING_BIOLOGICAL_VALIDATION_DATA"), "rows_imported": biological.get("rows_imported", 0), "data_fabricated": False}, [BIO_CONTRACT, BIO_IMPORT])
    _gate_artifact("gate_22h_final_validation_decision", decision["status"], "final_validation_decision.json", result, common_inputs)

    triangulation = {
        "status": "WAITING_TRACK_B_DATA",
        "track_a_status": _read_json(TRACK_A).get("status", "NOT_AVAILABLE"),
        "track_b_status": decision["status"],
        "real_effect_ratio": "NOT_AVAILABLE",
        "virtual_effect_ratio": "NOT_AVAILABLE",
        "direction_concordance": "NOT_AVAILABLE",
        "data_fabricated": False,
    }
    write_json(ROOT / "experiments/gate_22h_final_validation_decision/results/triangulation_summary.json", triangulation)
    write_json(ROOT / "experiments/gate_22_validation_ladder_status.json", result)
    _write_report(result)
    return result


def _write_report(result: dict[str, Any]) -> None:
    lines = [
        "# Gate 22 - Gene-specific and biological validation ladder",
        "",
        f"**Status:** `{result['status']}`",
        "",
        "## Validation question",
        "Can a reviewed Parkin-specific Drosophila perturbation be represented in the neural model and tested against independent biological evidence?",
        "",
        "## Current evidence",
        "- Track A Riemensperger 2011 remains a dopamine-class computational replication.",
        "- Dumitrescu 2023 provides a Parkin RNAi/DAM biological context, but native DAM beam-break activity is not converted to FlyGym speed.",
        "- Existing Parkin DAN root IDs remain `CLASS_LEVEL_EXPLORATORY`; they are not reused as gene-specific IDs.",
        "",
        "## Gate statuses",
        f"- Evidence: `{result['evidence']}`",
        f"- Mapping: `{result['mapping']}`",
        f"- Prospective prediction: `{result['prospective_prediction']}`",
        f"- Biological holdout: `{result['biological_holdout']}`",
        f"- Gene-specific validation: `{result['decision']['status']}`",
        f"- Parkinson-like biological support: `{result['decision']['parkinson_like_biological_support']}`",
        "",
        "## Blockers",
        *[f"- {item}" for item in result["blockers"]],
        "",
        "## Claim lock",
        "The repository currently supports a class-level computational disease scaffold and a paper-guided validation architecture. It does not support a gene-specific or biological Parkinson validation claim.",
        "",
        "No biological measurements were generated. No GPU simulation, calibration, tuning, or holdout opening was performed by this audit.",
    ]
    path = ROOT / "docs/validation/gene_specific_biological_validation_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    result = audit()
    print(f"Status: {result['status']}")
    for blocker in result["blockers"]:
        print(f"Blocker: {blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
