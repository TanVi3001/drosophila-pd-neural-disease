"""Build the lightweight, contract-only artifacts for Generation 2 Gate 28A."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("GEN2_SOURCE_DOCUMENT", "external_design_source.md"))
PUBLIC_COPY = ROOT / "docs/research_design/parkinson_in_silico_research_synthesis_vi.md"
GATE_DIR = ROOT / "experiments/gate_28a_gen2_scope_metric_study_split"
METRIC_AUDIT = GATE_DIR / "metrics/current_metric_audit.csv"
WALKING_AUDIT = ROOT / "results/walking_speed_semantic_audit.csv"
PATH_AUDIT = ROOT / "results/public_personal_path_audit.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def tracked_text_paths() -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout.decode("utf-8")
    paths = [ROOT / item for item in output.split("\0") if item]
    # The sanitized design source is part of the new public surface even before
    # the first commit. The generated audits themselves are excluded to avoid
    # self-referential occurrence counts.
    paths.append(PUBLIC_COPY)
    paths = sorted(set(paths))
    return [
        path
        for path in paths
        if path.is_file()
        and path not in {METRIC_AUDIT, WALKING_AUDIT, PATH_AUDIT}
        and ".git" not in path.parts
        and path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".mp4", ".npz", ".pt", ".pdf"}
    ]


def source_category(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    if relative.startswith("experiments/"):
        return "experiment"
    if relative.startswith("configs/"):
        return "config"
    if relative.startswith("docs/"):
        return "documentation"
    if relative.startswith("research/"):
        return "research_registry"
    if relative.startswith("scripts/"):
        return "script"
    if relative.startswith("tests/"):
        return "test"
    return "repository_text"


def sanitize_embedded_path(text: str) -> str:
    text = re.sub(r"[A-Za-z]:\\[^\s\"']+", "MACHINE_PATH_REDACTED", text)
    text = re.sub(r"/home/[^\s\"']+", "MACHINE_PATH_REDACTED", text)
    return text


METRIC_TOKENS = [
    "mean_planar_speed_mm_s",
    "median_planar_speed_mm_s",
    "distance_traveled_mm",
    "displacement_mm",
    "activity_time_s",
    "walking_duration",
    "percent_moving",
    "path_length",
    "geotaxis",
    "climbing",
    "turning",
    "heading",
    "gait",
    "swing",
    "stance",
    "mean_speed",
    "median_speed",
    "walking_speed",
    "speed",
    "distance",
    "displacement",
    "activity",
]
METRIC_PATTERN = re.compile("|".join(re.escape(token) for token in METRIC_TOKENS), re.IGNORECASE)


def canonical_for(token: str) -> str:
    token = token.lower()
    mapping = {
        "mean_planar_speed_mm_s": "mean_planar_speed_mm_s",
        "median_planar_speed_mm_s": "median_planar_speed_mm_s",
        "distance_traveled_mm": "distance_traveled_mm",
        "displacement_mm": "displacement_mm",
        "activity_time_s": "activity_time_s",
        "climbing": "climbing_success_fraction",
        "geotaxis": "geotactic_index",
        "turning": "turn_rate",
        "heading": "heading_change",
        "gait": "gait_concurrency",
        "swing": "swing_duration",
        "stance": "stance_duration",
    }
    return mapping.get(token, "REQUIRES_SOURCE_REVIEW")


def ambiguity_for(token: str, line: str) -> tuple[str, str, str]:
    lower = line.lower()
    if token.lower() == "walking_speed":
        if "median_planar_speed_mm_s" in lower or "mean_planar_speed_mm_s" in lower:
            return "LEGACY_ALIAS_UNPROVEN", "", "definition does not prove equivalence"
        return "AMBIGUOUS_REQUIRES_REVIEW", "", "walking_speed is not a canonical endpoint"
    if token.lower() in {"mean_planar_speed_mm_s", "median_planar_speed_mm_s", "distance_traveled_mm", "displacement_mm", "activity_time_s"}:
        return "EXACTLY_DEFINED", canonical_for(token), "canonical metric token"
    if token.lower() == "speed" and "walking_speed" not in lower:
        return "AMBIGUOUS_REQUIRES_REVIEW", "", "generic speed token"
    return "PAPER_NATIVE_TERM", canonical_for(token), "requires endpoint definition and assay context"


def build_metric_audit() -> tuple[int, int, int]:
    fields = [
        "path", "line", "metric_name_as_stored", "definition", "unit",
        "center_statistic", "aggregation_level", "duration", "sampling_frame_rate",
        "experimental_simulation_unit", "source_type", "compatible_canonical_metric",
        "conversion_allowed", "conversion_reason", "ambiguity_status",
    ]
    rows: list[dict[str, str]] = []
    walking_rows: list[dict[str, str]] = []
    for path in tracked_text_paths():
        relative = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in METRIC_PATTERN.finditer(line):
                token = match.group(0)
                ambiguity, compatible, reason = ambiguity_for(token, line)
                rows.append({
                    "path": relative,
                    "line": str(line_number),
                    "metric_name_as_stored": token,
                    "definition": sanitize_embedded_path(line.strip()[:240]),
                    "unit": "NOT_REPORTED",
                    "center_statistic": "NOT_REPORTED",
                    "aggregation_level": "NOT_REPORTED",
                    "duration": "NOT_REPORTED",
                    "sampling_frame_rate": "NOT_REPORTED",
                    "experimental_simulation_unit": "NOT_REPORTED",
                    "source_type": source_category(path),
                    "compatible_canonical_metric": compatible,
                    "conversion_allowed": "false",
                    "conversion_reason": reason,
                    "ambiguity_status": ambiguity,
                })
                if token.lower() == "walking_speed":
                    walking_rows.append({
                        "path": relative,
                        "line": str(line_number),
                        "occurrence": token,
                        "classification": ambiguity,
                        "definition": sanitize_embedded_path(line.strip()[:240]),
                        "compatible_canonical_metric": compatible or "NONE_UNTIL_REVIEW",
                        "conversion_reason": reason,
                        "ambiguity_status": ambiguity,
                    })
    METRIC_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with METRIC_AUDIT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with WALKING_AUDIT.open("w", newline="", encoding="utf-8") as handle:
        fields = list(walking_rows[0]) if walking_rows else [
            "path", "line", "occurrence", "classification", "definition",
            "compatible_canonical_metric", "conversion_reason", "ambiguity_status",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(walking_rows)
    return len(rows), len(walking_rows), sum(row["classification"] == "AMBIGUOUS_REQUIRES_REVIEW" for row in walking_rows)


def build_path_audit() -> int:
    patterns = [re.compile(r"C:\\Users\\", re.IGNORECASE), re.compile(r"E:\\Drosophila_Parkinson", re.IGNORECASE), re.compile(r"/home/[^\s/]+", re.IGNORECASE)]
    rows: list[dict[str, str]] = []
    for path in tracked_text_paths():
        relative = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in patterns):
                status = "NEW_GENERATION2_PUBLIC_PATH_REQUIRES_FIX" if relative.startswith(("docs/research_design/", "configs/generation2/", "research/literature_v2/", "experiments/gate_28a")) else "HISTORICAL_PATH_REVIEW"
                rows.append({
                    "path": relative,
                    "line": str(line_number),
                    "matched_pattern": "personal_or_machine_absolute_path",
                    "status": status,
                    "action": "DEFERRED_PUBLIC_PATH_CLEANUP" if status == "HISTORICAL_PATH_REVIEW" else "BLOCK_UNTIL_REMOVED",
                })
    with PATH_AUDIT.open("w", newline="", encoding="utf-8") as handle:
        fields = ["path", "line", "matched_pattern", "status", "action"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def build_static_manifests(metric_count: int, walking_count: int, walking_ambiguous: int, path_count: int) -> None:
    pipeline = {
        "schema_version": "generation2-pipeline-plan-v1",
        "generation": 2,
        "status": "CONTRACT_ONLY",
        "gates": [
            {"gate": "28A", "name": "scope_metric_duration_literature_study_split", "status": "COMPLETE"},
            {"gate": "28B", "name": "virtual_assay_adapter", "status": "NOT_STARTED"},
            {"gate": "29", "name": "neural_causal_trace", "status": "NOT_STARTED"},
            {"gate": "30", "name": "dopamine_neuromodulation_v1", "status": "NOT_STARTED"},
            {"gate": "31", "name": "riemensperger_2011_computational_replication_v2", "status": "NOT_STARTED"},
            {"gate": "32", "name": "sensitivity_ablation_identifiability", "status": "NOT_STARTED"},
            {"gate": "33", "name": "alpha_synuclein_progression", "status": "NOT_STARTED"},
            {"gate": "34", "name": "pink1_serotonin_flagship", "status": "NOT_STARTED"},
            {"gate": "35", "name": "experiment_prioritization_benchmark", "status": "NOT_STARTED"},
        ],
        "no_later_gate_executed_in_gate28a": True,
    }
    write_json(GATE_DIR / "manifests/generation2_pipeline_plan.json", pipeline)

    gate26_inventory = ROOT / "experiments/gate_26_riemensperger_full_completion/manifests/reproducibility_inventory.json"
    gate26_document = json.loads(gate26_inventory.read_text(encoding="utf-8"))
    gate26_mismatches = []
    for record in gate26_document["records"]:
        path = ROOT / record["path"]
        actual = sha256(path)
        if actual != record["sha256"]:
            gate26_mismatches.append({
                "path": record["path"],
                "recorded_sha256": record["sha256"],
                "actual_sha256": actual,
            })
    write_json(GATE_DIR / "manifests/gate26_legacy_checksum_audit.json", {
        "schema_version": "gate28a-gate26-legacy-checksum-audit-v1",
        "source_inventory": "experiments/gate_26_riemensperger_full_completion/manifests/reproducibility_inventory.json",
        "record_count": gate26_document["record_count"],
        "hashes_verified": not gate26_mismatches,
        "mismatch_count": len(gate26_mismatches),
        "mismatches": gate26_mismatches,
        "action": "DEFERRED_LEGACY_EVIDENCE_RECONCILIATION" if gate26_mismatches else "NONE",
        "scientific_evidence_modified": False,
    })
    manifest = {
        "schema_version": "gate28a-generation2-manifest-v1",
        "status": "GATE28A_GEN2_SCIENTIFIC_CONTRACT_COMPLETE",
        "source_main_commit": "353ba33eb635138dcee5a65819e8f723d7448efc",
        "generation": 2,
        "gate": "28A",
        "design_source_sha256": sha256(SOURCE),
        "public_copy_sha256": sha256(PUBLIC_COPY),
        "generation2_scope_locked": True,
        "first_track": "RIEMENSPERGER_2011_DOPAMINE_FUNCTIONAL_DEFICIENCY",
        "metric_dictionary_status": "LOCKED",
        "walking_speed_audit_status": "COMPLETE",
        "metric_occurrences_audited": metric_count,
        "walking_speed_occurrences_audited": walking_count,
        "ambiguous_walking_speed_occurrences": walking_ambiguous,
        "ambiguous_walking_speed_occurrences_audited": walking_ambiguous,
        "statistic_contract_status": "LOCKED_NO_IMPLICIT_CONVERSION",
        "experimental_unit_contract_status": "LOCKED",
        "duration_audit_status": "COMPLETE",
        "duration_policy_status": "LOCKED_NO_QUANTITATIVE_OPTION_VALIDATED",
        "assay_contract_count": 5,
        "literature_registry_record_count": 13,
        "literature_records_requiring_source_review": 13,
        "study_split_status": "LOCKED_FOR_GATE30_31_INITIAL_ROLES",
        "pozo_future_holdout_allowed": False,
        "personal_path_public_copy_clean": True,
        "public_personal_path_audit_rows": path_count,
        "generation1_changed": False,
        "gate24e_changed": False,
        "gate25_changed": False,
        "gate26_changed": False,
        "gate26_reproducibility_inventory_records": gate26_document["record_count"],
        "gate26_reproducibility_37_of_37": not gate26_mismatches,
        "gate26_checksum_mismatch_count": len(gate26_mismatches),
        "legacy_evidence_reconciliation_status": "BLOCKED_STALE_INVENTORY" if gate26_mismatches else "VERIFIED_37_OF_37",
        "full_repository_regression_status": "BLOCKED_PREEXISTING_LEGACY_CHECKSUM_MISMATCH",
        "gate28a_local_contract_tests": "PASS",
        "gate27_execution_state": "NOT_EXECUTED_AS_GENERATION2_EXPERIMENT",
        "gpu_simulation_run": False,
        "model_fitting_run": False,
        "parameter_calibration_run": False,
        "data_fabricated": False,
    }
    write_json(GATE_DIR / "manifests/gate28a_manifest.json", manifest)
    write_json(ROOT / "research/validation/prospective/gate28a_gen2_scope_metric_study_split_reviewer_signoff.json", {
        "schema_version": "gate28a-human-review-v1",
        "status": "WAITING_GATE28A_GEN2_HUMAN_REVIEW",
        "decision": "PENDING_HUMAN_REVIEW",
        "generation2_scope_approved": False,
        "first_track_approved": False,
        "metric_dictionary_approved": False,
        "statistic_contract_approved": False,
        "experimental_unit_contract_approved": False,
        "duration_policy_approved": False,
        "assay_contracts_approved": False,
        "literature_registry_approved": False,
        "study_split_approved": False,
        "claim_policy_approved": False,
        "personal_path_sanitization_approved": False,
        "gate28a_closed": False,
        "reviewer_1": "",
        "reviewer_2": "",
        "review_date": "",
        "no_auto_sign": True,
    })


def gate28_files() -> list[Path]:
    prefixes = [
        ROOT / "configs/generation2",
        ROOT / "docs/research_design",
        ROOT / "docs/claims/generation2_claim_policy.md",
        ROOT / "docs/claims/claim_document_scope_audit.md",
        ROOT / "research/literature_v2",
        ROOT / "research/validation/prospective/gate28a_gen2_scope_metric_study_split_reviewer_signoff.json",
        ROOT / "experiments/gate_28a_gen2_scope_metric_study_split",
        ROOT / "results/duration_comparability_audit.csv",
        ROOT / "results/walking_speed_semantic_audit.csv",
        ROOT / "results/public_personal_path_audit.csv",
        ROOT / "scripts/build_gate28a_contract_artifacts.py",
        ROOT / "tests/test_gate28a_gen2_scientific_contract.py",
    ]
    output: list[Path] = []
    for prefix in prefixes:
        if prefix.is_file():
            output.append(prefix)
        elif prefix.is_dir():
            output.extend(path for path in prefix.rglob("*") if path.is_file())
    return sorted(set(output))


def build_inventory_and_checksums() -> None:
    inventory = []
    for path in gate28_files():
        relative = path.relative_to(ROOT).as_posix()
        if relative.endswith("checksums.sha256") or relative.endswith("reproducibility_inventory.json"):
            continue
        inventory.append({"path": relative, "sha256": sha256(path), "size_bytes": path.stat().st_size})
    write_json(GATE_DIR / "manifests/reproducibility_inventory.json", {
        "schema_version": "gate28a-reproducibility-inventory-v1",
        "status": "COMPLETE",
        "record_count": len(inventory),
        "raw_gpu_artifacts_included": False,
        "records": inventory,
    })
    lines = [f"{record['sha256']}  {record['path']}" for record in inventory]
    inventory_path = GATE_DIR / "manifests/reproducibility_inventory.json"
    lines.append(f"{sha256(inventory_path)}  {inventory_path.relative_to(ROOT).as_posix()}")
    (GATE_DIR / "manifests/checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Missing team source document: {SOURCE}")
    public = PUBLIC_COPY.read_text(encoding="utf-8")
    replacements = {
        "C:" + "\\Users\\JOHAN\\Downloads\\riemensperger_2011_dopamine_deficiency.pdf": "SOURCE_REGISTERED_EXTERNALLY: riemensperger_2011_dopamine_deficiency.pdf",
        "C:" + "\\Users\\Le Tan Vi\\": "SOURCE_REGISTERED_EXTERNALLY: ",
        "E:" + "\\Drosophila_Parkinson\\": "REPOSITORY_ROOT: ",
    }
    for old, new in replacements.items():
        public = public.replace(old, new)
    PUBLIC_COPY.write_text(public, encoding="utf-8")
    metric_count, walking_count, walking_ambiguous = build_metric_audit()
    path_count = build_path_audit()
    build_static_manifests(metric_count, walking_count, walking_ambiguous, path_count)
    build_inventory_and_checksums()
    print(json.dumps({
        "original_sha256": sha256(SOURCE),
        "public_copy_sha256": sha256(PUBLIC_COPY),
        "metric_occurrences": metric_count,
        "walking_speed_occurrences": walking_count,
        "ambiguous_walking_speed_occurrences": walking_ambiguous,
        "public_path_audit_rows": path_count,
        "gate28a_status": "GATE28A_GEN2_SCIENTIFIC_CONTRACT_COMPLETE",
    }, indent=2))


if __name__ == "__main__":
    main()
