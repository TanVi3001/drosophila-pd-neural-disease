"""Static regression tests for the Gate 26 completion contract."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import yaml

from scripts import run_gate26_riemensperger_full_completion as gate26
from scripts import run_riemensperger2011_dopamine_replication as disease
from scripts import run_riemensperger2011_healthy_replication as healthy


ROOT = Path(__file__).resolve().parents[1]


def test_gate21d_ready_evidence_is_reconciled_without_new_mapping() -> None:
    summary = json.loads(gate26.MAPPING_SUMMARY.read_text(encoding="utf-8"))
    assert summary["status"] == gate26.MAPPING_READY
    assert summary["mapping_level"] == "DOPAMINE_CLASS_LEVEL_EXPLORATORY"
    assert summary["gene_specific_mapping"] is False
    assert summary["target_count"] == 342
    assert summary["blockers"] == []


def test_scientific_runners_use_memory_safe_profile_without_video_cli() -> None:
    healthy_source = inspect.getsource(healthy.run)
    disease_source = inspect.getsource(disease.run)
    for source in (healthy_source, disease_source):
        assert '"--artifact-profile", "GATE24E_MEMORY_SAFE"' in source
        assert "--video-output" not in source
        assert "--video-fps" not in source
        assert "--video-width" not in source
        assert "--video-height" not in source
        assert "--video-playback-speed" not in source
        assert "--video-camera-mode" not in source
        assert "--compare-to" not in source
        assert "--visualization" not in source


def test_healthy_and_disease_protocols_are_identical_except_transform() -> None:
    healthy_config = yaml.safe_load(gate26.HEALTHY_CONFIG.read_text(encoding="utf-8"))
    disease_config = yaml.safe_load(gate26.DISEASE_CONFIG.read_text(encoding="utf-8"))
    assert healthy_config["seed_policy"]["seeds"] == [0, 1, 2, 3, 4]
    assert disease_config["seed_policy"]["seeds"] == [0, 1, 2, 3, 4]
    assert healthy_config["duration"]["steps"] == 5000
    assert disease_config["healthy_config"] == "configs/replications/riemensperger_2011_healthy.yaml"
    assert healthy_config["duration"]["virtual_duration_s"] == 0.5
    assert healthy_config["timestep_s"] == 0.0001
    assert healthy_config["controller"] == {"stimulus": "p9", "cpg_frequency_hz": 12.0}
    assert healthy_config["world"] == "flat_terrain_default"
    assert disease_config["parameter_policy"]["default_candidate"] == 1.0


def test_gate26_freezes_primary_contract_and_prohibits_recovery() -> None:
    source = inspect.getsource(gate26)
    assert "SEEDS = [0, 1, 2, 3, 4]" in source
    assert "STEPS = 5000" in source
    assert "BURDEN = 1.0" in source
    assert '"simulation_count_authorized": 10' in source
    assert "no retry is allowed" in source
    assert '"simulation_jobs_started": 10' in source


def test_mapping_and_paper_claims_are_class_level_only() -> None:
    source = inspect.getsource(gate26)
    assert "DOPAMINE_CLASS_LEVEL_EXPLORATORY" in source
    assert '"data_fabricated": False' in source
    assert '"quantitative_validation_supported": False' in source
    assert '"biological_validation_supported": False' in source
    assert '"gene_specific_validation_supported": False' in source
    assert "NOT_REPORTED" in source
    assert "auto-sign" in source


def test_gate24e_and_gate25_locks_are_required() -> None:
    gate24e = json.loads((ROOT / "experiments/gate_24e_blinded_parkin_prediction/manifests/gate24e_final_validation_decision.json").read_text(encoding="utf-8"))
    gate25 = json.loads((ROOT / "experiments/gate_25_r2_parkin_reproducibility/manifests/gate25_r2_reproducibility_freeze.json").read_text(encoding="utf-8"))
    assert gate24e["status"] == gate26.GATE24E_STATUS
    assert gate24e["scientific_result"] == gate26.GATE24E_RESULT
    assert gate24e["cross_assay_decision"] == gate26.GATE24E_CROSS_ASSAY
    assert gate25["status"] == gate26.GATE25_STATUS
    assert "Gate24E scientific lock changed" in inspect.getsource(gate26.verify_project_locks)


def test_initial_state_audit_and_human_signoff_boundary_exist() -> None:
    audit = ROOT / "docs/replications/riemensperger_2011/gate26_initial_state_audit.md"
    assert audit.is_file()
    source = inspect.getsource(gate26.write_initial_signoff)
    assert "WAITING_RIEMENSPERGER_FINAL_HUMAN_REVIEW" in source
    assert "PENDING_HUMAN_REVIEW" in source
    assert '"gate26_closed": False' in source
    assert '"auto_sign": False' in source


def test_four_group_primary_direction_is_not_overridden_by_secondary_metrics() -> None:
    source = (ROOT / "scripts/analyze_riemensperger2011_four_group.py").read_text(encoding="utf-8")
    assert "DIRECTIONALLY_CONCORDANT_QUANTITATIVE_MISMATCH" in source
    assert "NOT_ASSESSED_NO_PREREGISTERED_THRESHOLD" in source
    assert "distance_endpoint_status" in source
    assert "No calibration or post-hoc threshold was applied" in source
