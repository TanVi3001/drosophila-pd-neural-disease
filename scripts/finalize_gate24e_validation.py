"""Build the immutable, claim-safe Gate24E closure package.

This script consolidates already frozen artifacts. It does not run simulation,
read raw rollout files, recalculate metrics, or perform a new analysis.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
PREDICTION_FREEZE = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/immutable_virtual_prediction_freeze.json"
VIRTUAL_SUMMARY = ROOT / "experiments/gate_24e_blinded_parkin_prediction/results/virtual_prediction_summary.json"
OPENING_MANIFEST = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/biological_holdout_opening.json"
BIOLOGICAL_DIRECTION = ROOT / "experiments/gate_24e_blinded_parkin_prediction/results/biological_holdout_direction.csv"
CROSS_ASSAY_SUMMARY = ROOT / "experiments/gate_24e_blinded_parkin_prediction/results/cross_assay_validation_summary.json"
S4K_REPORT = ROOT / "docs/validation/gate24e_biological_holdout_directional_validation.md"

DECISION_MANIFEST = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_final_validation_decision.json"
EVIDENCE_FREEZE = ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_final_evidence_freeze.json"
REVIEW_SIGNOFF = ROOT / "research/validation/prospective/gate24e_final_validation_reviewer_signoff.json"
REPORT = ROOT / "docs/validation/gate24e_final_validation_decision_and_limitations.md"

EXPECTED_VIRTUAL_FREEZE_SHA256 = "f44e9ad10b9fc4795ae2173d3e8b27fc9ea0d8202925bfc08cdcc72d06b00863"
EXPECTED_VIRTUAL_DECISION = "DIRECTIONAL_VALIDATION_NOT_SUPPORTED"
EXPECTED_BIOLOGICAL_DIRECTION = "BIOLOGICAL_IMPAIRMENT_SUPPORTED"
EXPECTED_CROSS_ASSAY_DECISION = "DIRECTIONAL_CROSS_ASSAY_DISCORDANCE"
EXPECTED_PLAN_SHA256 = "4515e1916631b019711154dccb5fb887110d5572e3eb82b7ea5118c643db5aac"
EXPECTED_EXECUTOR_SHA256 = "4d10edecbc8d987285ea82eb36a7bcfd686da3abde3b5160a3dcec23a2e78f3f"
EXPECTED_RUNTIME_COMMIT = "655e854544e3d814dfe422883ff0de66b619d6c1"
EXPECTED_MODEL_COMMIT = "be4b10a80755d9f7bad931f56b8a739bd64e3619"

FINAL_STATUS = "GATE24E_VALIDATION_COMPLETE_DIRECTIONAL_DISCORDANCE"
ALLOWED_CLAIM = (
    "The frozen Parkin computational perturbation did not reproduce the held-out "
    "biological locomotor impairment direction under the preregistered cross-assay validation protocol."
)


class ClosureError(RuntimeError):
    """Raised when immutable Gate24E evidence is inconsistent."""


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ClosureError(f"Expected a JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ClosureError(message)


def _canonical_sha256(document: Mapping[str, Any]) -> str:
    payload = dict(document)
    payload.pop("gate24e_final_evidence_freeze_sha256", None)
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _artifact(path: Path, root: Path) -> dict[str, Any]:
    _require(path.is_file(), f"required closure artifact is missing: {path}")
    return {
        "path": path.resolve().relative_to(root.resolve()).as_posix(),
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
    }


def _direction_record(path: Path) -> dict[str, str]:
    _require(path.is_file(), f"biological direction artifact is missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    _require(len(rows) == 1, "biological direction artifact must contain exactly one row")
    row = rows[0]
    _require(row.get("direction_label") == EXPECTED_BIOLOGICAL_DIRECTION, "biological direction artifact changed")
    _require(row.get("raw_data_available") == "false", "biological direction artifact exposes raw data")
    _require(row.get("quantitative_cross_assay_allowed") == "false", "biological direction artifact enables quantitative comparison")
    return row


def validate_locked_evidence(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    freeze = _json(root / PREDICTION_FREEZE.relative_to(ROOT))
    virtual = _json(root / VIRTUAL_SUMMARY.relative_to(ROOT))
    opening = _json(root / OPENING_MANIFEST.relative_to(ROOT))
    _direction_record(root / BIOLOGICAL_DIRECTION.relative_to(ROOT))
    cross_assay = _json(root / CROSS_ASSAY_SUMMARY.relative_to(ROOT))

    _require(freeze.get("virtual_prediction_freeze_sha256") == EXPECTED_VIRTUAL_FREEZE_SHA256, "virtual freeze SHA changed")
    _require(freeze.get("grid_decision") == EXPECTED_VIRTUAL_DECISION, "virtual decision changed")
    _require(freeze.get("holdout_opened") is False, "immutable virtual freeze was modified after holdout opening")
    _require(virtual.get("grid_decision") == EXPECTED_VIRTUAL_DECISION, "virtual summary decision changed")
    _require(virtual.get("holdout_opened") is False, "virtual summary holdout state changed")
    _require(virtual.get("posthoc_parameter_selection") is False, "virtual summary permits post-hoc selection")
    _require(virtual.get("tuning_using_holdout") is False, "virtual summary permits holdout tuning")
    _require(opening.get("status") == "BIOLOGICAL_HOLDOUT_OPENED_FOR_VALIDATION", "holdout opening status is not locked")
    _require(opening.get("holdout_opened") is True, "holdout opening is not recorded")
    _require(opening.get("virtual_prediction_freeze_sha256") == EXPECTED_VIRTUAL_FREEZE_SHA256, "opening freeze SHA changed")
    _require(cross_assay.get("biological_direction") == EXPECTED_BIOLOGICAL_DIRECTION, "biological direction changed")
    _require(cross_assay.get("cross_assay_decision") == EXPECTED_CROSS_ASSAY_DECISION, "cross-assay decision changed")
    _require(cross_assay.get("quantitative_cross_assay_validation") is False, "quantitative cross-assay validation is enabled")
    _require(cross_assay.get("retuning_after_holdout") is False, "retuning after holdout is enabled")
    _require(cross_assay.get("posthoc_parameter_selection") is False, "post-hoc selection is enabled")
    _require(cross_assay.get("biological_validation_claim") == "NOT_SUPPORTED", "biological validation claim was promoted")

    return {
        "immutable_virtual_prediction_freeze": freeze,
        "virtual_prediction_summary": virtual,
        "biological_holdout_opening": opening,
        "cross_assay_validation_summary": cross_assay,
    }


def build_decision_document(artifacts: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "gate24e-final-validation-decision-v1",
        "status": FINAL_STATUS,
        "gate_complete": True,
        "scientific_result": "NEGATIVE_VALIDATION_RESULT",
        "virtual_prediction_freeze_sha256": EXPECTED_VIRTUAL_FREEZE_SHA256,
        "virtual_decision": EXPECTED_VIRTUAL_DECISION,
        "biological_direction": EXPECTED_BIOLOGICAL_DIRECTION,
        "cross_assay_decision": EXPECTED_CROSS_ASSAY_DECISION,
        "primary_validation_axis": "LOCOMOTOR_IMPAIRMENT_DIRECTION",
        "quantitative_cross_assay_validation": False,
        "holdout_opened": True,
        "retuning_after_holdout": False,
        "posthoc_parameter_selection": False,
        "biological_validation_supported": False,
        "clinical_validation_supported": False,
        "drug_validation_supported": False,
        "future_model_requires_new_prospective_gate": True,
        "allowed_final_claim": ALLOWED_CLAIM,
        "forbidden_claims": [
            "biologically validated Parkinson model",
            "validated Parkinson mechanism",
            "Parkin-expression-specific connectome mapping",
            "human Parkinson validation",
            "clinical validation",
            "drug efficacy",
            "drug discovery validation",
            "quantitative assay equivalence",
            "successful disease phenotype replication",
        ],
        "source_artifacts": list(artifacts.values()),
    }


def build_evidence_freeze(artifacts: list[dict[str, Any]], decision: dict[str, Any]) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": "gate24e-final-evidence-freeze-v1",
        "status": "GATE24E_FINAL_EVIDENCE_FROZEN",
        "gate_status": FINAL_STATUS,
        "scientific_result": "NEGATIVE_VALIDATION_RESULT",
        "source_artifacts": artifacts,
        "final_decision_manifest": decision,
        "scientific_plan_sha256": EXPECTED_PLAN_SHA256,
        "executor_sha256": EXPECTED_EXECUTOR_SHA256,
        "runtime_commit": EXPECTED_RUNTIME_COMMIT,
        "model_commit": EXPECTED_MODEL_COMMIT,
        "raw_rollouts_included": False,
        "raw_rollouts_policy": "Preserved separately by the scientific artifact inventory; not required for this lightweight closure freeze.",
        "prediction_is_immutable": True,
        "holdout_reinterpretation": False,
        "retuning_performed": False,
        "parameter_selection_performed": False,
        "quantitative_cross_assay_validation": False,
        "biological_validation_supported": False,
    }
    document["gate24e_final_evidence_freeze_sha256"] = _canonical_sha256(document)
    return document


def _write_json(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _write_report(path: Path, source_artifacts: list[dict[str, Any]], final_freeze_sha256: str) -> None:
    lines = [
        "# Gate 24E: Final validation decision and limitations",
        "",
        "## 1. Question tested",
        "",
        "The preregistered question was whether the frozen Parkin computational perturbation would reproduce the direction of locomotor impairment reported by an independent held-out biological source.",
        "",
        "## 2. Frozen computational prediction",
        "",
        f"- Prediction freeze SHA256: `{EXPECTED_VIRTUAL_FREEZE_SHA256}`.",
        f"- Primary metric: `median_planar_speed_mm_s`.",
        f"- Validation axis: `LOCOMOTOR_IMPAIRMENT_DIRECTION`.",
        f"- Frozen virtual decision: `{EXPECTED_VIRTUAL_DECISION}`.",
        "- The virtual prediction was frozen before the biological holdout was opened.",
        "",
        "## 3. Held-out biological direction",
        "",
        "- Source: Cackovic et al. 2018, DOI `10.3389/fncel.2018.00039`, PMID `29497364`.",
        "- Assay: negative geotaxis/climbing with vertical infrared monitoring.",
        "- Direction: `BIOLOGICAL_IMPAIRMENT_SUPPORTED`.",
        "- Raw individual-level data in the repository: unavailable.",
        "",
        "## 4. Directional comparison",
        "",
        "The virtual assay measures planar locomotion, while the biological holdout measures climbing. These endpoints are not quantitatively equivalent. Only impairment direction was compared.",
        "",
        f"- Final cross-assay decision: `{EXPECTED_CROSS_ASSAY_DECISION}`.",
        "- Quantitative cross-assay validation: `false`.",
        "",
        "## 5. Final result",
        "",
        f"- Gate status: `{FINAL_STATUS}`.",
        "- Scientific result: `NEGATIVE_VALIDATION_RESULT`.",
        "",
        f"> {ALLOWED_CLAIM}",
        "",
        "Gate24E is therefore historical negative evidence for this frozen perturbation and protocol. It is not a positive disease-model validation.",
        "",
        "## 6. What the result does not mean",
        "",
        "This result does not establish a biologically validated Parkinson model, a validated Parkinson mechanism, Parkin-expression-specific connectome mapping, human or clinical validation, drug efficacy, drug discovery validation, quantitative assay equivalence, or successful disease phenotype replication.",
        "The driver-defined neural target is not the same as a Parkin-expression-specific root mapping.",
        "",
        "## 7. Limitations",
        "",
        "- The assays differ: planar speed versus negative geotaxis/climbing; therefore only direction was compared.",
        "- S4K used summary-level held-out evidence; no individual-level raw Cackovic data were available.",
        "- The reviewed driver-defined Parkin perturbation produced essentially no preregistered reduction in virtual speed.",
        "- The scientific unit was five seeds; frames were not statistical replicates.",
        "- Burdens 0.25, 0.50, 0.75 and 1.00 are dimensionless computational sensitivity levels, not measured Parkin knockdown percentages.",
        "- The model is a computational locomotion model, not organism-level biological validation.",
        "",
        "## 8. Negative-result integrity",
        "",
        "Gate24E must not be rerun or rewritten to obtain a positive result. No retuning, seed replacement, parameter selection, metric substitution, or decision-rule modification may use the opened holdout. Any improved model requires a new version, new prospective experiment, new freeze, and new holdout policy.",
        "",
        "## 9. Future hypotheses",
        "",
        "The following are future hypotheses, not corrections to Gate24E: a stronger or mechanistically different neural perturbation operator; downstream network-dynamics perturbation; driver/subpopulation-specific perturbation; longer or assay-aligned endpoints; a negative-geotaxis-like virtual task; independent seed expansion; and robustness/ablation studies.",
        "",
        "## 10. Provenance",
        "",
        f"- Final evidence freeze SHA256: `{final_freeze_sha256}`.",
        "- Raw rollout paths are excluded from this lightweight closure freeze and remain protected by the scientific artifact inventory.",
        "",
        "| Artifact | SHA256 | Bytes |",
        "|---|---|---:|",
    ]
    lines.extend(f"| `{item['path']}` | `{item['sha256']}` | {item['size_bytes']} |" for item in source_artifacts)
    lines.extend([
        "",
        "## 11. Human final review state",
        "",
        "The final reviewer signoff remains `WAITING_GATE24E_FINAL_VALIDATION_REVIEW` / `PENDING_HUMAN_REVIEW`. The closure package does not auto-sign or claim final human approval.",
        "",
        "## 12. Boundary",
        "",
        "No GPU, simulation, new scientific analysis, retuning, or holdout reinterpretation was performed in S4L.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def build_closure(root: Path = ROOT) -> dict[str, Any]:
    locked = validate_locked_evidence(root)
    source_paths = [
        root / PREDICTION_FREEZE.relative_to(ROOT),
        root / VIRTUAL_SUMMARY.relative_to(ROOT),
        root / OPENING_MANIFEST.relative_to(ROOT),
        root / BIOLOGICAL_DIRECTION.relative_to(ROOT),
        root / CROSS_ASSAY_SUMMARY.relative_to(ROOT),
        root / S4K_REPORT.relative_to(ROOT),
    ]
    source_artifacts = [_artifact(path, root) for path in source_paths]
    decision = build_decision_document({item["path"]: item for item in source_artifacts})
    _write_json(root / DECISION_MANIFEST.relative_to(ROOT), decision)
    decision_artifact = _artifact(root / DECISION_MANIFEST.relative_to(ROOT), root)
    freeze_artifacts = source_artifacts + [decision_artifact]
    freeze = build_evidence_freeze(freeze_artifacts, decision_artifact)
    _write_json(root / EVIDENCE_FREEZE.relative_to(ROOT), freeze)
    _write_report(root / REPORT.relative_to(ROOT), freeze_artifacts, freeze["gate24e_final_evidence_freeze_sha256"])
    signoff = {
        "schema_version": "gate24e-final-validation-review-v1",
        "status": "WAITING_GATE24E_FINAL_VALIDATION_REVIEW",
        "decision": "PENDING_HUMAN_REVIEW",
        "reviewer_1": "",
        "reviewer_2": "",
        "review_date": "",
        "gate24e_final_evidence_freeze_sha256": freeze["gate24e_final_evidence_freeze_sha256"],
        "accepted_cross_assay_decision": EXPECTED_CROSS_ASSAY_DECISION,
        "accepted_negative_result": False,
        "gate24e_closed": False,
        "no_auto_sign": True,
    }
    _write_json(root / REVIEW_SIGNOFF.relative_to(ROOT), signoff)
    # Keep the returned source document independent of raw rollout paths.
    return {
        "status": FINAL_STATUS,
        "scientific_result": "NEGATIVE_VALIDATION_RESULT",
        "final_evidence_freeze_sha256": freeze["gate24e_final_evidence_freeze_sha256"],
        "source_artifacts": freeze_artifacts,
        "human_review_status": signoff["status"],
        "raw_rollouts_included": freeze["raw_rollouts_included"],
        "locked_evidence_keys": sorted(locked),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = build_closure(args.root.resolve())
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
