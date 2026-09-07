"""Regression tests for the Gate 24 claim-safe concordance package."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import yaml

from scripts.run_gate24_concordance_analysis import (
    DEFAULT_CONFIG,
    DEFAULT_OUTPUT,
    _concordance_rows,
    _descriptive_rows,
    _load_sources,
    _validate_sources,
)

ROOT = Path(__file__).resolve().parents[1]


def test_gate24_analysis_import_does_not_require_matplotlib() -> None:
    script = """
import builtins

real_import = builtins.__import__

def blocked_import(name, *args, **kwargs):
    if name == 'matplotlib' or name.startswith('matplotlib.'):
        raise ModuleNotFoundError(\"No module named 'matplotlib'\")
    return real_import(name, *args, **kwargs)

builtins.__import__ = blocked_import
import scripts.run_gate24_concordance_analysis
print('import-ok')
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "import-ok"


def _config() -> dict:
    return yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))


def test_gate24_is_analysis_only_and_claim_locked() -> None:
    config = _config()
    assert config["analysis_only"] is True
    assert all(config[field] is False for field in ("run_gpu", "run_simulation", "run_calibration", "run_holdout_validation", "run_tuning"))
    assert "biological Parkinson validation" in config["claim_lock"]["forbidden"]


def test_gate24_validates_all_prior_gates() -> None:
    config = _config()
    _, documents = _load_sources(config)
    _validate_sources(config, documents)
    assert documents["gate13b"]["status"] == "CHEN_RATIO_CALIBRATION_PASS"
    assert documents["gate13c"]["status"] == "CHEN_CALIBRATED_CONFIRMATION_PASS"
    assert documents["gate21"]["passed_rollouts"] == 25
    assert documents["gate22"]["passed_comparison_rows"] == 55
    assert documents["gate23"]["status"] == "POZO_HOLDOUT_MISMATCH"


def test_gate24_concordance_matrix_preserves_mismatch_and_scope() -> None:
    config = _config()
    _, documents = _load_sources(config)
    rows = _concordance_rows(documents)
    statuses = {row["evidence_id"]: row["status"] for row in rows}
    assert statuses["chen_calibration"] == "PASS"
    assert statuses["chen_confirmation"] == "PASS"
    assert statuses["pozo_directionality"] == "PASS"
    assert statuses["pozo_quantitative_ratio"] == "MISMATCH"
    assert statuses["gene_specific_validation"] == "NOT_AVAILABLE"
    assert statuses["biological_parkinson_validation"] == "NOT_AVAILABLE"


def test_gate24_descriptive_table_has_primary_metric_statistics() -> None:
    config = _config()
    _, documents = _load_sources(config)
    rows = _descriptive_rows(documents, config["primary_metrics"])
    assert len(rows) == 15
    assert {row["n_pairs"] for row in rows} == {5}
    assert all(row["qc_status"] == "PASS" for row in rows)
    assert all("delta" in row and "paired_standardized_delta" in row for row in rows)


def test_gate24_generated_artifacts_if_present() -> None:
    summary_path = DEFAULT_OUTPUT / "concordance_summary.json"
    manifest_path = DEFAULT_OUTPUT.parent / "manifests/gate24_concordance_manifest.json"
    if not summary_path.is_file() or not manifest_path.is_file():
        return
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert summary["status"] == "CONCORDANCE_REPORT_COMPLETE"
    assert summary["pozo_quantitative_match"] is False
    assert summary["biological_parkinson_validation"] is False
    assert manifest["no_new_simulation"] is True
    assert manifest["pozo_quantitative_match"] is False
