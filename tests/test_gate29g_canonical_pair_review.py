"""Regression tests for Gate29-G canonical-pair review and integration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import audit_gate29g_canonical_pair_review as gate29g


ROOT = Path(__file__).resolve().parents[1]


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_gate29g_audit_reaches_reviewed_status() -> None:
    audit = gate29g.audit_review()
    assert audit["status"] == "GATE29_CANONICAL_PAIR_INDEPENDENTLY_REVIEWED"
    assert audit["trace_instrumentation_status"] == "TRACE_INSTRUMENTATION_VALIDATED"
    assert audit["next_status"] == "READY_FOR_GATE29_H_SCIENTIFIC_TRACE_PREREGISTRATION"
    assert audit["merge_authorized"] is True


def test_gate29g_records_two_distinct_human_reviewers() -> None:
    signoff = _json(gate29g.SIGNOFF)
    assert signoff["no_auto_sign"] is True
    assert signoff["signature_type"] == "RECORDED_HUMAN_ATTESTATION_NOT_CRYPTOGRAPHIC"
    assert len(signoff["reviewers"]) == 2
    assert len({item["name"] for item in signoff["reviewers"]}) == 2
    assert all(item["decision"] == "APPROVED" for item in signoff["reviewers"])


def test_gate29g_review_is_anchored_to_immutable_gate29f_commit() -> None:
    signoff = _json(gate29g.SIGNOFF)
    manifest_blob = gate29g._git_blob(
        signoff["reviewed_evidence_commit"],
        "experiments/gate_29f_canonical_pair_evidence/manifests/canonical_pair_evidence_manifest.json",
    )
    raw_index_blob = gate29g._git_blob(
        signoff["reviewed_evidence_commit"],
        "experiments/gate_29f_canonical_pair_evidence/manifests/raw_artifact_checksums.sha256",
    )
    assert hashlib.sha256(manifest_blob).hexdigest() == signoff["reviewed_gate29f_manifest_git_blob_sha256"]
    assert hashlib.sha256(raw_index_blob).hexdigest() == signoff["reviewed_raw_checksum_index_git_blob_sha256"]


def test_gate29g_covers_all_raw_artifacts_and_locked_signals() -> None:
    audit = gate29g.audit_review()
    assert audit["raw_artifact_count"] == 10
    assert audit["raw_artifact_total_bytes"] == 66431868
    assert audit["locked_signal_count"] == 5
    assert audit["locked_signal_max_abs_diff"] == 0.0


def test_gate29g_preserves_scientific_firewall() -> None:
    audit = gate29g.audit_review()
    assert audit["gpu_executed"] is False
    assert audit["simulation_executed"] is False
    assert audit["scientific_jobs"] == 0
    assert audit["disease_jobs"] == 0
    assert audit["calibration_run"] is False
    assert audit["retuning"] is False
    assert audit["biological_validation"] is False
    assert audit["claim_scope"] == "ENGINEERING_NONPERTURBATION_EVIDENCE_ONLY"


def test_gate29g_fails_closed_if_one_reviewer_is_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    signoff = _json(gate29g.SIGNOFF)
    signoff["reviewers"][1]["decision"] = "PENDING"
    monkeypatch.setattr(gate29g, "_read_json", lambda path: signoff if path == gate29g.SIGNOFF else _json(path))
    with pytest.raises(gate29g.Gate29GError, match="both reviewer decisions"):
        gate29g.audit_review()


def test_gate29g_fails_closed_if_reviewed_evidence_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    original = gate29g._read_json

    def changed(path: Path) -> dict:
        value = original(path)
        if path == gate29g.EVIDENCE_MANIFEST:
            value["raw_artifact_total_bytes"] += 1
        return value

    monkeypatch.setattr(gate29g, "_read_json", changed)
    with pytest.raises(gate29g.Gate29GError, match="reviewed evidence changed"):
        gate29g.audit_review()


def test_gate29g_fails_closed_if_locked_signal_is_not_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    original = gate29g._read_json

    def changed(path: Path) -> dict:
        value = original(path)
        if path == gate29g.COMPARISON:
            value["comparisons"]["thorax"]["max_abs_diff"] = 1e-9
        return value

    monkeypatch.setattr(gate29g, "_read_json", changed)
    with pytest.raises(gate29g.Gate29GError, match="locked signal is not exact"):
        gate29g.audit_review()


def test_gate29g_reviewed_artifact_checksum_index_is_current() -> None:
    lines = gate29g.AUDIT_CHECKSUMS.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 8
    for line in lines:
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_gate29g_report_has_scope_and_next_gate_lock() -> None:
    report = gate29g.REPORT.read_text(encoding="utf-8")
    assert "GATE29_CANONICAL_PAIR_INDEPENDENTLY_REVIEWED" in report
    assert "TRACE_INSTRUMENTATION_VALIDATED" in report
    assert "READY_FOR_GATE29_H_SCIENTIFIC_TRACE_PREREGISTRATION" in report
    assert "không xác nhận mô hình Parkinson sinh học" in report
