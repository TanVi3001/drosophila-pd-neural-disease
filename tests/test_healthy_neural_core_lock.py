import json
from pathlib import Path

from scripts.lock_healthy_neural_core import build_lock_manifest


def test_healthy_core_lock_requires_verified_source_and_does_not_copy_bytes(tmp_path: Path) -> None:
    inspection = {
        "status": "READY",
        "required_files": {"brain_body_bridge.py": True},
        "integrity": {
            "status": "VERIFIED_SHA256",
            "files": {"brain_body_bridge.py": {"status": "PASS", "sha256": "abc"}},
        },
        "license_status": "VERIFIED_MIT",
        "data_license_status": "REVIEW_CC_BY_NC_4_0",
    }
    manifest = build_lock_manifest(
        brain_root=tmp_path / "brain",
        inspection=inspection,
        project_commit="project-commit",
    )

    assert manifest["status"] == "HEALTHY_NEURAL_CORE_LOCKED"
    assert manifest["simulation_run"] is False
    assert manifest["healthy_core"]["source_bytes_copied"] is False
    assert manifest["disease_branch_policy"]["healthy_core_mutation_allowed"] is False
    json.dumps(manifest)


def test_healthy_core_lock_stays_waiting_when_source_is_incomplete(tmp_path: Path) -> None:
    manifest = build_lock_manifest(
        brain_root=tmp_path / "brain",
        inspection={
            "status": "WAITING_BRAIN_DATA",
            "required_files": {},
            "integrity": {"status": "UNVERIFIED_NO_MANIFEST", "files": {}},
            "license_status": "UNVERIFIED",
        },
        project_commit=None,
    )
    assert manifest["status"] == "WAITING_BRAIN_DATA"
