import csv
import json
from pathlib import Path

import numpy as np

from scripts.prepare_disease_neural_branch import build_branch_manifest
from scripts.prepare_disease_neural_perturbation import build_blocked_manifest
from scripts.run_brain_body_neural_first import _load_npz_evidence


def _write_mapping(path: Path, condition_id: str, status: str = "CLASS_LEVEL_EXPLORATORY_ONLY") -> None:
    fields = ["condition_id", "neuron_provenance", "mapping_status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "condition_id": condition_id,
                "neuron_provenance": "FlyWire v783 reviewed class export",
                "mapping_status": status,
            }
        )


def test_step2_creates_separate_exploratory_branch(tmp_path: Path) -> None:
    condition_id = "dopamine_deficiency_exploratory"
    core_lock = tmp_path / "core-lock.json"
    core_lock.write_text(
        json.dumps(
            {
                "status": "HEALTHY_NEURAL_CORE_LOCKED",
                "healthy_core": {
                    "root": "external/fly-brain",
                    "immutable_reference": True,
                    "source_bytes_copied": False,
                    "files": {"data/plastic_weights.pt": {"sha256": "parent-hash"}},
                },
            }
        ),
        encoding="utf-8",
    )
    config = tmp_path / "condition.yaml"
    config.write_text(
        "\n".join(
            [
                f"condition_id: {condition_id}",
                "gene_model: class_level_dopamine_proxy",
                "target_neurons: ['n1']",
                "target_edges: []",
                "full_burden:",
                "  presynaptic_gain: 0.5",
                "burden_curve:",
                "  - age_days: 5",
                "    burden: 1.0",
                "provenance: ['paper and mapping review']",
            ]
        ),
        encoding="utf-8",
    )
    annotations = tmp_path / "annotations.csv"
    annotations.write_text(
        "neuron_id,cell_type,neurotransmitter,region,motor_role,source\n"
        "n1,PAM,dopamine,,motor,FlyWire v783\n",
        encoding="utf-8",
    )
    mapping = tmp_path / "mapping.csv"
    _write_mapping(mapping, condition_id)

    manifest = build_branch_manifest(
        core_lock_path=core_lock,
        config_path=config,
        annotations_path=annotations,
        mapping_audit_path=mapping,
    )

    assert manifest["status"] == "DISEASE_NEURAL_BRANCH_READY"
    assert manifest["mapping"]["scope"] == "class_level_exploratory"
    assert manifest["mapping"]["gene_specific_mapping"] is False
    assert manifest["branch"]["healthy_core_mutation_allowed"] is False
    assert manifest["checkpoint_manifest"]["healthy_checkpoint_overwrite_allowed"] is False


def test_step2_blocks_template_without_mapping_and_targets(tmp_path: Path) -> None:
    condition_id = "pink1"
    core_lock = tmp_path / "core-lock.json"
    core_lock.write_text(json.dumps({"status": "HEALTHY_NEURAL_CORE_LOCKED", "healthy_core": {"files": {}}}), encoding="utf-8")
    config = tmp_path / "condition.yaml"
    config.write_text(
        f"condition_id: {condition_id}\ngene_model: pink1\ntarget_neurons: []\ntarget_edges: []\nfull_burden: {{}}\nburden_curve: []\nprovenance: []\n",
        encoding="utf-8",
    )
    annotations = tmp_path / "annotations.csv"
    annotations.write_text("neuron_id,cell_type,neurotransmitter,region,motor_role,source\n", encoding="utf-8")
    mapping = tmp_path / "mapping.csv"
    _write_mapping(mapping, condition_id, "WAITING_NEURON_EVIDENCE")

    manifest = build_branch_manifest(core_lock_path=core_lock, config_path=config, annotations_path=annotations, mapping_audit_path=mapping)

    assert manifest["status"] == "WAITING_REVIEWED_MAPPING"
    assert any("target_neurons or target_edges" in blocker for blocker in manifest["blockers"])
    assert manifest["simulation_run"] is False


def test_step3_blocked_manifest_never_claims_simulation(tmp_path: Path) -> None:
    branch = {"status": "WAITING_REVIEWED_MAPPING", "blockers": ["missing mapping"]}
    document = build_blocked_manifest(
        branch_manifest_path=tmp_path / "branch.json",
        branch=branch,
        brain_root=tmp_path / "brain",
        age_days=5,
        status="WAITING_DISEASE_NEURAL_BRANCH",
        message="blocked",
    )
    assert document["simulation_run"] is False
    assert document["data_fabricated"] is False


def test_step4_rollout_evidence_requires_moving_action(tmp_path: Path) -> None:
    rollout = tmp_path / "rollout.npz"
    timestamps = np.array([0.0, 0.01, 0.02])
    thorax = np.array([[0.0, 0.0, 0.1], [0.01, 0.0, 0.1], [0.02, 0.0, 0.1]])
    joints = np.zeros((3, 66))
    joints[1, 0] = 0.1
    actuators = np.zeros((3, 42))
    actuators[2, 0] = 0.2
    np.savez(rollout, timestamp_s=timestamps, thorax=thorax, joint_positions=joints, actuator_position=actuators, contact_found=np.ones((3, 6)))

    evidence = _load_npz_evidence(tmp_path)

    assert evidence["timestamp_monotonic"] is True
    assert evidence["actuator_position_shape"] == [3, 42]
    assert evidence["actuator_trajectory_max_delta"] > 0
