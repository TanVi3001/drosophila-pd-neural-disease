from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "experiments/gate_12b_disease_mapping/configs"
MANIFEST = ROOT / "experiments/gate_12b_disease_mapping/manifests/disease_mapping_manifest.json"
CONDITIONS = ("alpha_synuclein", "pink1", "parkin", "dj1", "lrrk2")


def _load(path: Path) -> dict:
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    assert isinstance(document, dict), path
    return document


def test_gate12b_schema_and_condition_configs_exist() -> None:
    assert (CONFIG_DIR / "disease_condition_schema.yaml").is_file()
    for condition_id in CONDITIONS:
        assert (CONFIG_DIR / f"{condition_id}_condition.yaml").is_file()


def test_gate12b_condition_decisions_are_conservative() -> None:
    for condition_id in CONDITIONS:
        document = _load(CONFIG_DIR / f"{condition_id}_condition.yaml")
        assert document["condition_id"] == condition_id
        decision = document["decision"]
        assert decision["run_status"] in {"RUN_READY", "BLOCKED"}
        if decision["run_status"] == "RUN_READY":
            target = document["target_definition"]
            assert target["target_neurons"] or target["target_edges"]
            assert document["burden"]["burden_curve"] != "NOT_AVAILABLE"
            assert document["burden"]["full_burden"] != "NOT_AVAILABLE"
            assert document["provenance"]["mapping_source"] != "NOT_AVAILABLE"
        else:
            assert decision["blocked_reason"]


def test_gate12b_manifest_is_non_simulation_and_matches_conditions() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert {row["condition_id"] for row in manifest["conditions"]} == set(CONDITIONS)
    assert all(row["run_status"] == "BLOCKED" for row in manifest["conditions"])
    assert manifest["no_simulation_run"] is True
    assert manifest["no_calibration_run"] is True
    assert manifest["no_holdout_validation_run"] is True
