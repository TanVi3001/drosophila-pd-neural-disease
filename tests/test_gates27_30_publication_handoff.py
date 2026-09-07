"""Regression tests for Gate 27--30 publication handoff preparation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_gates27_30_publication_handoff import DEFAULT_CONFIG, _read_config, run_all
from scripts.verify_gates27_30_publication_handoff import verify

ROOT = Path(__file__).resolve().parents[1]


def test_gates27_30_are_analysis_only_without_external_submission() -> None:
    config = _read_config(DEFAULT_CONFIG)
    assert config["analysis_only"] is True
    assert all(
        config[key] is False
        for key in (
            "run_gpu", "run_simulation", "run_calibration", "run_holdout_validation",
            "run_tuning", "submit_to_external_service",
        )
    )


def test_gates27_30_build_claim_safe_handoff_with_explicit_human_blockers() -> None:
    statuses = run_all()
    assert statuses["gate_27"] == "INTERNAL_REVIEW_PACKAGE_READY"
    assert statuses["gate_28"] == "ARCHIVE_METADATA_PENDING_HUMAN_DECISIONS"
    assert statuses["gate_29"] == "SUBMISSION_METADATA_PENDING_HUMAN_SIGNOFF"
    assert statuses["gate_30"] == "PUBLICATION_HANDOFF_PENDING_HUMAN_AUTHORIZATION"

    archive = json.loads((ROOT / "experiments/gate_28_archive_metadata/results/archive_metadata_audit.json").read_text(encoding="utf-8"))
    submission = json.loads((ROOT / "experiments/gate_29_submission_readiness/results/submission_readiness.json").read_text(encoding="utf-8"))
    handoff = json.loads((ROOT / "experiments/gate_30_publication_handoff/results/publication_handoff.json").read_text(encoding="utf-8"))
    assert archive["doi_minted"] is False
    assert submission["external_submission_executed"] is False
    assert handoff["external_release_created"] is False
    assert handoff["external_submission_executed"] is False


def test_gates27_30_local_checksum_verification_passes() -> None:
    result = verify()
    assert result["status"] == "PUBLICATION_HANDOFF_LOCAL_VERIFICATION_PASS"
    assert result["checked_artifacts"] >= 15
