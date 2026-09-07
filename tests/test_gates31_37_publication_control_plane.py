"""Regression tests for the authorization-gated publication control plane."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_gates31_37_publication_control_plane import DEFAULT_CONFIG, _read_yaml, run_all
from scripts.verify_gates31_37_publication_control_plane import verify

ROOT = Path(__file__).resolve().parents[1]


def test_gates31_37_are_local_and_analysis_only() -> None:
    config = _read_yaml(DEFAULT_CONFIG)
    assert config["analysis_only"] is True
    assert all(
        config[field] is False
        for field in (
            "run_gpu", "run_simulation", "run_calibration", "run_holdout_validation",
            "run_tuning", "create_external_release", "submit_to_venue",
        )
    )


def test_gates31_37_create_templates_without_faking_human_actions() -> None:
    outcome = run_all()
    assert outcome["gate_statuses"] == {
        "gate_31": "WAITING_AUTHORIZED_INTERNAL_SIGNOFF",
        "gate_32": "WAITING_APPROVED_PUBLICATION_METADATA",
        "gate_33": "VENUE_MANUSCRIPT_TEMPLATE_READY",
        "gate_34": "ARCHIVE_RELEASE_PENDING_AUTHORIZATION",
        "gate_35": "EXTERNAL_SUBMISSION_PENDING_CORRESPONDING_AUTHOR",
        "gate_36": "WAITING_FOR_EDITORIAL_DECISION",
        "gate_37": "WAITING_FOR_ACCEPTANCE",
    }
    status = json.loads((ROOT / "experiments/gate_37_acceptance_archive/results/publication_control_plane_status.json").read_text(encoding="utf-8"))
    assert status["no_external_release_created"] is True
    assert status["no_external_submission_executed"] is True
    assert (ROOT / "submission/gate_31_internal_scientific_signoff/publication_signoff.local.yaml.example").is_file()
    assert (ROOT / "submission/gate_35_external_submission/submission_receipt.local.json.example").is_file()


def test_gates31_37_checksum_verification_passes() -> None:
    result = verify()
    assert result["status"] == "PUBLICATION_CONTROL_PLANE_LOCAL_VERIFICATION_PASS"
    assert result["checked_artifacts"] >= 30
