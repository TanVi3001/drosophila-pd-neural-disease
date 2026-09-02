from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/gate_12f_action_hook_discovery"
CONTRACT = GATE / "action_hook_contract.yaml"
MANIFEST = GATE / "action_hook_discovery_manifest.json"
REPORT = ROOT / "docs/disease_rollouts/gate_12f_a_action_hook_discovery_report.md"


def test_action_hook_contract_exists_and_has_discovery_status() -> None:
    document = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))

    assert document["schema_version"] == "gate-12f-a-action-hook-contract-v1"
    assert document["status"] in {"DISCOVERED", "NOT_DISCOVERED"}
    assert document["discovery"]["simulation_run"] is False

    action_pipeline = document["action_pipeline"]
    if document["status"] == "DISCOVERED":
        assert action_pipeline["action_source_file"] not in {"", "NOT_FOUND"}
        assert action_pipeline["action_hook_file"] not in {"", "NOT_FOUND"}
        assert action_pipeline["simulation_step_call"] not in {"", "NOT_FOUND"}
        assert action_pipeline["action_type"] == "flygym_demo.complex_terrain.common.LocomotionAction"
        assert action_pipeline["action_shape"] == "joint_angles=(42,), adhesion_onoff=(6,)"
    else:
        assert document["readiness"]["blocker"].strip()


def test_discovery_manifest_preserves_no_execution_boundary() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["status"] == "DISCOVERED"
    assert manifest["no_disease_rollout"] is True
    assert manifest["no_calibration"] is True
    assert manifest["no_holdout_validation"] is True
    assert manifest["no_fake_hook"] is True
    assert manifest["no_biological_validation_claim"] is True
    assert manifest["action_joint_angles_shape"] == [42]
    assert manifest["action_adhesion_shape"] == [6]


def test_report_describes_hook_and_gate12f_b_boundary() -> None:
    report = REPORT.read_text(encoding="utf-8")

    assert "layer.apply_to_action" in report
    assert "apply_locomotion_action" in report
    assert "simulation.step" in report
    assert "READY_FOR_GATE_12F_B_INTEGRATION" in report
    assert "không phải biological Parkinson validation" in report
