"""Apply the Gate 22 gene-specific decision policy without hard-coded PASS."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.riemensperger2011.protocol import read_json, write_json


REQUIRED_CRITERIA = (
    "exact_gene_intervention",
    "matched_control",
    "biological_phenotype",
    "gene_specific_mapping",
    "two_human_review",
    "prospective_prediction",
    "validation_not_used_for_tuning",
    "direction_concordance",
    "quantitative_criterion",
    "qc_pass",
    "no_claim_leakage",
)


def decide(summary: dict[str, Any]) -> dict[str, Any]:
    criteria = {name: bool(summary.get("criteria", {}).get(name, False)) for name in REQUIRED_CRITERIA}
    failed = [name for name, passed in criteria.items() if not passed]
    biological_data = bool(summary.get("biological_data_available", False))
    if not biological_data:
        status = "GENE_SPECIFIC_VALIDATION_NOT_SUPPORTED"
    elif not failed:
        status = "GENE_SPECIFIC_VALIDATION_SUPPORTED"
    elif summary.get("direction_concordance") == "INCONCLUSIVE":
        status = "GENE_SPECIFIC_VALIDATION_INCONCLUSIVE"
    else:
        status = "GENE_SPECIFIC_VALIDATION_NOT_SUPPORTED"
    parkinson_support = (
        "BIOLOGICALLY_SUPPORTED_PARKINSON_LIKE_DROSOPHILA_MODEL"
        if status == "GENE_SPECIFIC_VALIDATION_SUPPORTED" and summary.get("independent_biological_axis", False)
        else "PARKINSON_LIKE_BIOLOGICAL_SUPPORT_INCOMPLETE"
    )
    return {
        "status": status,
        "failed_criteria": failed,
        "criteria": criteria,
        "parkinson_like_biological_support": parkinson_support,
        "biological_data_available": biological_data,
        "model_result_does_not_promote_itself": True,
        "claim_lock": "No biological Parkinson or human/clinical claim is permitted.",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = decide(read_json(args.summary))
    write_json(args.output, result)
    print(f"Status: {result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
