"""Main-repository audit for the Gate24E memory-safe exporter preparation."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "experiments/gate_24e_storage_probe/manifests/memory_safe_export_fix.json"
REPORT = ROOT / "docs/gate24e_memory_failure_root_cause.md"


def test_memory_safe_fix_manifest_preserves_gate24_boundaries() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert payload["status"] == "MEMORY_SAFE_EXPORT_IMPLEMENTED"
    assert payload["previous_attempt"] == "attempt_02"
    assert payload["previous_simulation_completed_steps"] == 100000
    assert payload["previous_storage_measurements_valid"] is False
    assert payload["frozen_original_platform_commit"] == "3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06"
    assert len(payload["memory_safe_platform_commit"]) == 40
    assert payload["artifact_profile"] == "GATE24E_MEMORY_SAFE"
    assert payload["full_rollout_json_required"] is False
    assert payload["rollout_npz_required"] is True
    assert payload["viewer_required"] is False
    assert payload["primary_analysis_changed"] is False
    assert payload["holdout_opened"] is False
    assert payload["scientific_jobs_executed"] == 0
    assert payload["attempt_03_authorized"] is False
    assert payload["gpu_simulation_executed"] is False


def test_root_cause_report_documents_all_memory_hazards() -> None:
    report = REPORT.read_text(encoding="utf-8")
    for evidence in (
        "rollout.to_dict()",
        '"frames": [frame.to_dict() for frame in self.frames]',
        "json.loads(json_path.read_text",
        "build_viewer_pose()",
        "np.stack(...)",
        "GATE24E_MEMORY_SAFE",
        "WAITING_GATE24E_RUNTIME_PROVENANCE_AMENDMENT",
    ):
        assert evidence in report


def test_attempt_03_is_not_silently_reusable() -> None:
    attempt_03 = ROOT / "experiments/gate_24e_storage_probe/attempt_03"
    if attempt_03.exists():
        assert any(path.is_file() for path in attempt_03.rglob("*"))
