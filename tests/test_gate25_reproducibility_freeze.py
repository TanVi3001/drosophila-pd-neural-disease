"""Regression tests for the file-only Gate 25 reproducibility freeze."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from scripts.run_gate25_reproducibility_freeze import (
    DEFAULT_CONFIG,
    DEFAULT_OUTPUT,
    ReproducibilityFreezeError,
    _read_config,
    _validate_gate24_sources,
    run,
)

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_gate25_is_file_only_and_claim_safe() -> None:
    config = _read_config(DEFAULT_CONFIG)
    assert config["analysis_only"] is True
    assert all(
        config[key] is False
        for key in ("run_gpu", "run_simulation", "run_calibration", "run_holdout_validation", "run_tuning")
    )
    assert "biological Parkinson validation" in config["claim_lock"]["forbidden"]


def test_gate25_freeze_outputs_validate_existing_evidence(tmp_path: Path) -> None:
    del tmp_path
    manifest = run()

    assert manifest["status"] == "REPRODUCIBILITY_FREEZE_COMPLETE"
    assert manifest["no_simulation"] is True
    assert manifest["pozo_quantitative_match"] is False
    assert manifest["gene_specific_validation"] is False
    assert manifest["biological_parkinson_validation"] is False

    inventory = DEFAULT_OUTPUT / "results" / "freeze_inventory.csv"
    with inventory.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == manifest["locked_evidence_count"]
    assert all(Path(row["path"]).suffix not in {".mp4", ".npz", ".pt"} for row in rows)
    assert any(row["artifact_id"] == "gate_24_concordance" for row in rows)
    assert any(row["artifact_id"] == "gate23_summary" for row in rows)

    checksums = DEFAULT_OUTPUT / "manifests" / "checksums.sha256"
    for line in checksums.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        assert _sha256(ROOT / relative) == expected


def test_gate25_rejects_mutated_gate24_source_checksum() -> None:
    document = json.loads(
        (
            ROOT
            / "experiments/gate_24_concordance/manifests/gate24_concordance_manifest.json"
        ).read_text(encoding="utf-8")
    )
    document["source_artifacts"]["healthy_manifest"]["sha256"] = "0" * 64
    try:
        _validate_gate24_sources(document)
    except ReproducibilityFreezeError as exc:
        assert "Checksum mismatch" in str(exc)
    else:
        raise AssertionError("Gate 25 must reject an altered source checksum")
