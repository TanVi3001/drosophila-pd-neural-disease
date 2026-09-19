import json
from pathlib import Path

import pytest

from drosophila_pd_neural.connectome import (
    ConnectomeRegistry,
    RegistryError,
    evaluate_promotion,
    load_registry,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "configs" / "connectome_source_registry.json"


def test_registry_loads_and_has_explicit_namespaces() -> None:
    registry = load_registry(REGISTRY)
    assert len(registry.repositories) == 11
    assert len(registry.artifacts) >= 8
    datasets = {item["dataset_id"] for item in registry.primary_datasets}
    assert {"male-cns:v1.0", "flywire:783"} <= datasets
    assert all(artifact.id_namespace for artifact in registry.artifacts)


def test_registry_verifies_pinned_repositories_and_artifacts() -> None:
    registry = load_registry(REGISTRY)
    report = registry.to_report(
        workspace_root=ROOT,
        verify_git=True,
        verify_checksums=True,
    )
    assert report["verification"]["failures"] == []
    assert all(row["git_head_matches"] for row in report["repositories"])
    hashed = [row for row in report["artifacts"] if row["sha256"]]
    assert hashed
    assert all(row["sha256_matches"] for row in hashed)


def test_registry_detects_unknown_artifact_source() -> None:
    value = json.loads(REGISTRY.read_text(encoding="utf-8"))
    value["artifacts"][0]["source_repo"] = "not-a-cloned-repo"
    with pytest.raises(RegistryError, match="khong co trong registry"):
        ConnectomeRegistry.from_mapping(value)


def test_audit_artifact_cannot_be_promoted_to_rollout() -> None:
    decision = evaluate_promotion(
        {
            "source_repo": "2025malecns",
            "source_dataset": "male-cns:v1.0+flywire:783",
            "id_namespace": "mixed_male_body_id_and_flywire_root_id",
            "sha256": "a" * 64,
            "mapping_status": "crossmatch_audit_only",
            "target_reviewed": False,
            "runtime_consumer_available": False,
        },
        "rollout",
    )
    assert not decision.allowed
    assert decision.status == "BLOCKED"
    assert "mapping_is_not_verified" in decision.reasons
    assert "platform_neural_consumer_unavailable" in decision.reasons


def test_verified_mapping_can_prepare_checkpoint_but_not_rollout() -> None:
    record = {
        "source_repo": "2025malecns",
        "source_dataset": "male-cns:v1.0",
        "id_namespace": "male_cns_body_id",
        "sha256": "b" * 64,
        "mapping_status": "verified",
        "target_reviewed": True,
        "runtime_consumer_available": False,
    }
    checkpoint = evaluate_promotion(record, "checkpoint_preparation")
    rollout = evaluate_promotion(record, "rollout")
    assert checkpoint.allowed
    assert checkpoint.status == "CHECKPOINT_ELIGIBLE"
    assert not rollout.allowed
    assert "platform_neural_consumer_unavailable" in rollout.reasons
