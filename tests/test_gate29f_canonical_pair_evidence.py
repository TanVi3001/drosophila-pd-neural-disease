"""Regression tests for the lightweight Gate29-F evidence lock."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import package_gate29f_canonical_pair_evidence as gate29f
from scripts import run_gate29_neural_causal_trace as gate29


ROOT = Path(__file__).resolve().parents[1]
GATE_ROOT = ROOT / "experiments/gate_29f_canonical_pair_evidence"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_gate29f_manifest_locks_completed_engineering_pair() -> None:
    manifest = _json(GATE_ROOT / "manifests/canonical_pair_evidence_manifest.json")
    assert manifest["status"] == "GATE29F_CANONICAL_PAIR_EVIDENCE_LOCKED"
    assert manifest["pair_id"] == "GATE29_CANONICAL_PAIR_V1"
    assert manifest["seed"] == 9202
    assert manifest["condition"] == "healthy"
    assert manifest["jobs_executed"] == 2
    assert manifest["baseline_returncode"] == 0
    assert manifest["trace_returncode"] == 0
    assert manifest["execution_state"] == "PAIR_COMPLETE"
    assert manifest["comparison_status"] == "TRACE_OBSERVATION_NONPERTURBING_PASS"
    assert manifest["comparison_rtol"] == 0.0
    assert manifest["comparison_atol"] == 1e-12
    assert manifest["raw_artifacts_outside_git"] is True
    assert manifest["raw_artifact_count"] == 10
    assert manifest["packager_source_sha256"] == hashlib.sha256(
        Path(gate29f.__file__).read_bytes()
    ).hexdigest()
    assert manifest["analyzer_source_sha256"] == hashlib.sha256(
        Path(gate29.__file__).read_bytes()
    ).hexdigest()


def test_gate29f_keeps_scientific_firewall_closed() -> None:
    manifest = _json(GATE_ROOT / "manifests/canonical_pair_evidence_manifest.json")
    assert manifest["claim_scope"] == "ENGINEERING_NONPERTURBATION_EVIDENCE_ONLY"
    assert manifest["scientific_jobs"] == 0
    assert manifest["disease_jobs"] == 0
    assert manifest["calibration_run"] is False
    assert manifest["fitting_run"] is False
    assert manifest["retuning"] is False
    assert manifest["dopamine_implemented"] is False
    assert manifest["biological_validation"] is False


def test_gate29f_raw_checksum_index_matches_manifest() -> None:
    manifest = _json(GATE_ROOT / "manifests/canonical_pair_evidence_manifest.json")
    expected = {
        item["logical_path"]: item["sha256"]
        for item in manifest["raw_artifacts"]
    }
    lines = (
        GATE_ROOT / "manifests/raw_artifact_checksums.sha256"
    ).read_text(encoding="utf-8").splitlines()
    observed = {}
    for line in lines:
        digest, path = line.split("  ", 1)
        observed[path] = digest
    assert observed == expected
    assert all(not path.startswith(("E:/", "E:\\")) for path in observed)


def test_gate29f_lightweight_package_checksums_are_current() -> None:
    lines = (
        GATE_ROOT / "manifests/package_artifact_checksums.sha256"
    ).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    for line in lines:
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_gate29f_exact_comparison_and_scalar_metrics_pass() -> None:
    comparison = _json(GATE_ROOT / "results/canonical_pair_comparison.json")
    assert comparison["status"] == "TRACE_OBSERVATION_NONPERTURBING_PASS"
    assert set(comparison["comparisons"]) == {
        "timestamp_s",
        "thorax",
        "joint_positions",
        "actuator_position",
        "contact_found",
    }
    assert all(item["passed"] is True for item in comparison["comparisons"].values())
    assert all(item["max_abs_diff"] == 0.0 for item in comparison["comparisons"].values())

    metrics = _json(GATE_ROOT / "results/canonical_pair_metrics.json")
    assert metrics["status"] == "GATE29F_CANONICAL_METRICS_EXACT_MATCH"
    assert len(metrics["rows"]) == 3
    assert all(row["baseline"] == row["trace"] for row in metrics["rows"])
    assert all(row["delta"] == 0.0 for row in metrics["rows"])


def test_gate29f_report_preserves_claim_boundary() -> None:
    report = (
        ROOT / "docs/research_design/gate29f_canonical_pair_evidence_report.md"
    ).read_text(encoding="utf-8")
    assert "GATE29F_CANONICAL_PAIR_EVIDENCE_LOCKED" in report
    assert "TRACE_OBSERVATION_NONPERTURBING_PASS" in report
    assert "không phải disease execution" in report
    assert "không phải biological Parkinson validation" in report


def test_analyzer_reads_seed_from_paired_metadata(tmp_path: Path) -> None:
    for name in ("baseline", "trace"):
        path = tmp_path / name / "metadata.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "simulation": {
                        "random_seed": 9202,
                        "condition_id": "healthy",
                        "repository_commit": "runtime-commit",
                        "brain_checkpoint_sha256": "checkpoint-sha",
                        "brain_device": "cuda",
                        "stimulus": "p9",
                        "timestep_s": 0.0001,
                    }
                }
            ),
            encoding="utf-8",
        )
    identity = gate29._paired_execution_identity({"output_root": tmp_path})
    assert identity["seed"] == 9202
    assert identity["seed"] != gate29.TECHNICAL_SEED


def test_analyzer_rejects_seed_mismatch(tmp_path: Path) -> None:
    for name, seed in (("baseline", 9202), ("trace", 9201)):
        path = tmp_path / name / "metadata.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "simulation": {
                        "random_seed": seed,
                        "condition_id": "healthy",
                        "repository_commit": "runtime-commit",
                        "brain_checkpoint_sha256": "checkpoint-sha",
                        "brain_device": "cuda",
                        "stimulus": "p9",
                        "timestep_s": 0.0001,
                    }
                }
            ),
            encoding="utf-8",
        )
    with pytest.raises(gate29.Gate29Error, match="random_seed"):
        gate29._paired_execution_identity({"output_root": tmp_path})


def test_packager_has_no_execution_mode() -> None:
    source = Path(gate29f.__file__).read_text(encoding="utf-8")
    assert "--execute" not in source
    assert "subprocess.Popen" not in source
    assert "scientific_jobs\": 0" in source
