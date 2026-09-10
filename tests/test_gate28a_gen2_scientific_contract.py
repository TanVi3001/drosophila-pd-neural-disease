from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

from scripts.verify_gate26_reproducibility_v2 import verify as verify_gate26_v2


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/gate_28a_gen2_scope_metric_study_split"
CURRENT_MAIN = "cbd1ca071b2a8f28983d1cb78096501847fefbc1"
ORIGINAL_GATE28A = "2dafaafc5a09eca1908457a54d8a0a5dc4e45b24"
ALIGNMENT_MANIFEST = (
    "experiments/gate_28b_virtual_assay_adapter/manifests/"
    "gate28a_human_closure_test_alignment.json"
)


def _json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob(relative: str, ref: str = "HEAD") -> bytes:
    result = subprocess.run(
        ["git", "cat-file", "blob", f"{ref}:{relative}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return result.stdout


def _documented_gate28a_transitions() -> dict[str, dict]:
    alignment = _json(ALIGNMENT_MANIFEST)
    assert alignment["status"] == "GATE28A_HUMAN_CLOSURE_TEST_ALIGNED_FAIL_CLOSED"
    assert alignment["fail_closed"] is True
    transitions = alignment["documented_transitions"]
    assert len(transitions) == 2
    return {item["path"]: item for item in transitions}


def test_generation2_and_gate_status() -> None:
    manifest = _json("experiments/gate_28a_gen2_scope_metric_study_split/manifests/gate28a_manifest.json")
    assert manifest["generation"] == 2
    assert manifest["gate"] == "28A"
    assert manifest["status"] == "GATE28A_GEN2_SCIENTIFIC_CONTRACT_COMPLETE"
    assert manifest["gate27_execution_state"] == "NOT_EXECUTED_AS_GENERATION2_EXPERIMENT"


def test_generation1_protected_directories_are_unchanged() -> None:
    protected_prefixes = (
        "experiments/gate_24e_blinded_parkin_prediction/",
        "experiments/gate_25_r2_parkin_reproducibility/",
        "experiments/gate_26_riemensperger_full_completion/",
        "experiments/gate_21b_riemensperger_healthy/",
        "experiments/gate_21e_riemensperger_disease/",
        "experiments/gate_21f_four_group_analysis/",
        "research/validation/prospective/riemensperger_2011_final_reviewer_signoff.json",
    )
    changed = subprocess.run(
        ["git", "diff", "--name-only", "origin/main...HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert not [path for path in changed if path.startswith(protected_prefixes)]


def test_gate26_legacy_mismatch_is_preserved_and_canonical_v2_passes() -> None:
    inventory_path = ROOT / "experiments/gate_26_riemensperger_full_completion/manifests/reproducibility_inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    assert inventory["record_count"] == 37
    legacy_audit = _json("experiments/gate_28a_gen2_scope_metric_study_split/manifests/gate26_legacy_checksum_audit.json")
    assert legacy_audit["record_count"] == 37
    assert legacy_audit["mismatch_count"] == 11
    assert legacy_audit["hashes_verified"] is False
    assert legacy_audit["action"] == "DEFERRED_LEGACY_EVIDENCE_RECONCILIATION"
    canonical = _json("experiments/gate_26_riemensperger_full_completion/manifests/reproducibility_inventory_v2_git_blob.json")
    assert canonical["record_count"] == 37
    assert canonical["status"] == "COMPLETE_CANONICAL_GIT_BLOB"
    assert verify_gate26_v2("HEAD") == (37, [])
    recheck = _json("experiments/gate_28a_gen2_scope_metric_study_split/manifests/gate26_canonical_recheck.json")
    assert recheck["status"] == "GATE26_CANONICAL_RECHECK_PASS"
    assert recheck["checked_against_main"] == CURRENT_MAIN
    assert recheck["legacy_mismatch_count"] == 11
    assert recheck["canonical_verified_count"] == 37
    assert recheck["canonical_verification_pass"] is True
    assert recheck["canonical_reconciliation_status"] == "HUMAN_APPROVED_CLOSED"
    assert recheck["unexplained_content_drift"] is False
    gate26_signoff = _json("research/validation/prospective/gate26_reproducibility_canonicalization_reviewer_signoff.json")
    assert gate26_signoff["status"] == "GATE26_REPRODUCIBILITY_CANONICALIZATION_REVIEW_APPROVED"
    assert gate26_signoff["decision"] == "APPROVED_GATE26_REPRODUCIBILITY_CANONICALIZATION_CLOSURE"
    assert gate26_signoff["gate26_reconciliation_closed"] is True
    completion = _json("experiments/gate_26_riemensperger_full_completion/manifests/gate26_completion_manifest.json")
    assert completion["final_directional_decision"] == "NOT_REPRODUCED"


def test_generation2_scientific_content_matches_original_gate28a_commit() -> None:
    paths = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ORIGINAL_GATE28A, "configs/generation2"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    paths += [
        "docs/research_design/canonical_metric_dictionary.md",
        "docs/research_design/generation2_research_charter.md",
        "docs/research_design/parkinson_in_silico_research_synthesis_vi.md",
        "docs/claims/generation2_claim_policy.md",
        "research/literature_v2/literature_endpoint_registry_v2.csv",
        "research/literature_v2/riemensperger_2011_endpoint_contract.yaml",
        "research/literature_v2/study_split_manifest.yaml",
        "results/duration_comparability_audit.csv",
        "results/walking_speed_semantic_audit.csv",
        "experiments/gate_28a_gen2_scope_metric_study_split/metrics/current_metric_audit.csv",
    ]
    for relative in sorted(set(paths)):
        assert _git_blob(relative, "HEAD") == _git_blob(relative, ORIGINAL_GATE28A), relative


def test_metric_dictionary_keeps_endpoints_distinct() -> None:
    dictionary = (ROOT / "configs/generation2/canonical_metric_dictionary.yaml").read_text(encoding="utf-8")
    assert "name: mean_planar_speed_mm_s" in dictionary
    assert "name: median_planar_speed_mm_s" in dictionary
    assert "name: distance_traveled_mm" in dictionary
    assert "name: activity_time_s" in dictionary
    assert "name: climbing_success_fraction" in dictionary
    assert "never_alias_to_mean_without_distribution_model" in dictionary
    assert "never_convert_to_speed_without_time_aligned_endpoint" in dictionary


def test_statistic_and_unit_contracts_are_conservative() -> None:
    statistic = (ROOT / "configs/generation2/statistic_contract.yaml").read_text(encoding="utf-8")
    unit = (ROOT / "configs/generation2/experimental_unit_contract.yaml").read_text(encoding="utf-8")
    assert "default_policy: NO_IMPLICIT_STATISTIC_CONVERSION" in statistic
    assert "mean_from_median: forbidden" in statistic
    assert "sd_from_se: forbidden" in statistic
    assert "frame" in unit and "physics_step" in unit
    assert "frames_are_not_replicates: true" in unit
    assert "physics_steps_are_not_replicates: true" in unit
    assert "simulation_seed" in unit


def test_riemensperger_contract_is_median_and_uncertainty_not_reported() -> None:
    contract = (ROOT / "research/literature_v2/riemensperger_2011_endpoint_contract.yaml").read_text(encoding="utf-8")
    assert "primary_statistic: median" in contract
    assert "spread_for_speed: NOT_REPORTED" in contract
    assert "duration: 15" in contract
    assert "duration_unit: min" in contract


def test_duration_policy_does_not_equate_half_second_and_fifteen_minutes() -> None:
    policy = (ROOT / "configs/generation2/duration_policy.yaml").read_text(encoding="utf-8")
    audit = (ROOT / "results/duration_comparability_audit.csv").read_text(encoding="utf-8")
    assert "not automatically quantitatively comparable" in policy
    assert "Gate26_current_FlyGym" in audit
    assert "Riemensperger_2011" in audit
    assert ",false,Short virtual rollout" in audit


def test_pozo_is_not_a_new_future_holdout() -> None:
    split = (ROOT / "research/literature_v2/study_split_manifest.yaml").read_text(encoding="utf-8")
    manifest = _json("experiments/gate_28a_gen2_scope_metric_study_split/manifests/gate28a_manifest.json")
    assert "HISTORICAL_EXPOSED_EVALUATION_SOURCE" in split
    assert "future_sealed_holdout: false" in split
    assert "NOT_YET_FROZEN" in split
    assert manifest["pozo_future_holdout_allowed"] is False


def test_study_roles_and_registry_exist_without_auto_approval() -> None:
    split = (ROOT / "research/literature_v2/study_split_manifest.yaml").read_text(encoding="utf-8")
    registry = ROOT / "research/literature_v2/literature_endpoint_registry_v2.csv"
    with registry.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) >= 9
    assert "FUTURE_ALPHA_SYN_LONGITUDINAL_CALIBRATION_CANDIDATE" in split
    assert "GEN2_DOPAMINE_FUNCTIONAL_DEFICIENCY_REFERENCE" in split
    assert all(row["review_status"] == "PENDING_SOURCE_REVIEW" for row in rows)


def test_public_synthesis_is_sanitized() -> None:
    public = (ROOT / "docs/research_design/parkinson_in_silico_research_synthesis_vi.md").read_text(encoding="utf-8")
    assert "C:\\Users\\" not in public
    assert "E:\\Drosophila_Parkinson\\" not in public
    assert "SOURCE_REGISTERED_EXTERNALLY" in public


def test_generation2_claim_policy_and_architecture_are_not_biological_validation_claims() -> None:
    policy = (ROOT / "docs/claims/generation2_claim_policy.md").read_text(encoding="utf-8")
    charter = (ROOT / "docs/research_design/generation2_research_charter.md").read_text(encoding="utf-8")
    assert "chưa phải mô hình Parkinson sinh học hoàn chỉnh" in charter
    assert "biologically validated Parkinson model" in policy
    assert "digital twin" in policy
    assert "generic multi-gene" not in charter.lower()


def test_no_execution_or_fitting_in_gate28a() -> None:
    manifest = _json("experiments/gate_28a_gen2_scope_metric_study_split/manifests/gate28a_manifest.json")
    assert manifest["gpu_simulation_run"] is False
    assert manifest["model_fitting_run"] is False
    assert manifest["parameter_calibration_run"] is False
    assert manifest["retuning"] is False
    assert manifest["gate28b_execution"] is False
    assert manifest["data_fabricated"] is False
    pipeline = _json("experiments/gate_28a_gen2_scope_metric_study_split/manifests/generation2_pipeline_plan.json")
    assert all(item["status"] in {"COMPLETE", "NOT_STARTED"} for item in pipeline["gates"])
    assert pipeline["gates"][0]["status"] == "COMPLETE"
    assert all(item["status"] == "NOT_STARTED" for item in pipeline["gates"][1:])


def test_human_review_is_closed_by_the_explicit_gate28a_signoff() -> None:
    review = _json("research/validation/prospective/gate28a_gen2_scope_metric_study_split_reviewer_signoff.json")
    assert review["status"] == "GATE28A_GEN2_SCIENTIFIC_CONTRACT_REVIEW_APPROVED"
    assert review["decision"] == "APPROVED_GATE28A_GEN2_SCIENTIFIC_CONTRACT_CLOSURE"
    assert review["no_auto_sign"] is True
    assert review["gate28a_closed"] is True
    assert review["reviewer_1"]
    assert review["reviewer_2"]
    assert review["review_date"]
    assert review["approved_head"] == "2bd8bc39337abe37b30acfe305a87123293ccf7c"


def test_gate28a_inventory_and_checksums_verify() -> None:
    inventory = _json("experiments/gate_28a_gen2_scope_metric_study_split/manifests/reproducibility_inventory.json")
    transitions = _documented_gate28a_transitions()
    assert inventory["record_count"] > 0
    for record in inventory["records"]:
        blob = _git_blob(record["path"])
        transition = transitions.get(record["path"])
        if transition is not None:
            # Gate 28A remains immutable. Only the two exact, documented
            # post-freeze review/test transitions are accepted.
            assert record["sha256"] == transition["historical"]["sha256"]
            assert record["size_bytes"] == transition["historical"]["size_bytes"]
            assert hashlib.sha256(blob).hexdigest() == transition["current"]["sha256"]
            assert len(blob) == transition["current"]["size_bytes"]
            continue
        assert hashlib.sha256(blob).hexdigest() == record["sha256"], record["path"]
        assert len(blob) == record["size_bytes"], record["path"]
    checksums = (GATE / "manifests/checksums.sha256").read_text(encoding="utf-8").splitlines()
    assert len(checksums) == inventory["record_count"] + 1
    for line in checksums:
        expected, relative = line.split("  ", 1)
        transition = transitions.get(relative)
        if transition is not None:
            assert expected == transition["historical"]["sha256"]
            blob = _git_blob(relative)
            assert hashlib.sha256(blob).hexdigest() == transition["current"]["sha256"]
            assert len(blob) == transition["current"]["size_bytes"]
            continue
        assert hashlib.sha256(_git_blob(relative)).hexdigest() == expected, relative
