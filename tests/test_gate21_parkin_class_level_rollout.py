"""Regression tests for Gate 21 Parkin class-level exploratory rollout."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.run_gate21_parkin_class_level_rollout import (
    _load_mapping,
    _preflight,
    _runtime_config,
    build_parser,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "experiments/gate_21_parkin_class_level_rollout/configs/parkin_class_level_exploratory.yaml"
MAPPING_PATH = ROOT / "research/disease_mapping/manual_imports/parkin/codex_export.csv"
SIGNOFF_PATH = ROOT / "research/disease_mapping/manual_imports/parkin/reviewer_signoff.json"
HEALTHY_PATH = ROOT / "experiments/gate_11_healthy_baseline/manifests/healthy_baseline_manifest.json"


def _config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def test_gate21_protocol_is_class_level_only() -> None:
    config = _config()
    assert config["condition_id"] == "parkin"
    assert config["mapping_scope"] == "class_level_exploratory"
    assert config["gene_specific_mapping"] is False
    assert config["allowed_rollout_scope"] == "CLASS_LEVEL_EXPLORATORY_ONLY"
    assert [item["value"] for item in config["burden_levels"]] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert config["runtime"]["seeds"] == [0, 1, 2, 3, 4]


def test_gate21_uses_reviewed_parkin_mapping_without_inference() -> None:
    root_ids, digest = _load_mapping(MAPPING_PATH)
    assert len(root_ids) == 330
    assert len(set(root_ids)) == 330
    assert all(value.isdigit() for value in root_ids)
    assert digest


def test_gate21_materialized_condition_contains_real_ids_and_explicit_proxy() -> None:
    config = _config()
    root_ids, _ = _load_mapping(MAPPING_PATH)
    condition = _runtime_config(config=config, root_ids=root_ids, burden=0.5, seed=2, mapping_path=MAPPING_PATH, signoff_path=SIGNOFF_PATH)
    assert condition["target_neurons"] == root_ids
    assert condition["target_edges"] == []
    assert condition["burden_curve"] == [{"age_days": 20.0, "burden": 0.5}]
    assert condition["full_burden"]["neuron_survival"] == 0.5
    assert condition["provenance"]


def test_gate21_preflight_accepts_mapping_and_healthy_gate() -> None:
    result = _preflight(config=_config(), mapping_path=MAPPING_PATH, signoff_path=SIGNOFF_PATH, healthy_path=HEALTHY_PATH)
    assert result["status"] == "PASS", result["blockers"]
    assert result["mapping_count"] == 330


def test_gate21_preflight_never_claims_gene_specific() -> None:
    config = _config()
    config["gene_specific_mapping"] = True
    result = _preflight(config=config, mapping_path=MAPPING_PATH, signoff_path=SIGNOFF_PATH, healthy_path=HEALTHY_PATH)
    assert result["status"] == "BLOCKED"
    assert "gene_specific_mapping_must_be_false" in result["blockers"]


def test_gate21_cli_defaults_to_preflightable_protocol() -> None:
    args = build_parser().parse_args([])
    assert args.config == CONFIG_PATH
    assert args.preflight_only is False


def test_gate21_protocol_manifest_has_25_planned_rollouts() -> None:
    manifest = json.loads((ROOT / "experiments/gate_21_parkin_class_level_rollout/manifests/gate21_protocol_manifest.json").read_text(encoding="utf-8"))
    assert manifest["planned_rollout_count"] == 25
    assert manifest["gene_specific_mapping"] is False
    assert manifest["calibration_run"] is False
    assert manifest["holdout_validation_run"] is False
