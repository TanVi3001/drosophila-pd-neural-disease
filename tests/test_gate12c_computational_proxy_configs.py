from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.run_disease_conditions_multiseed import _config_blockers, _is_proxy_plan


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "experiments/gate_12c_computational_proxy_configs/configs"
MANIFEST = ROOT / "experiments/gate_12c_computational_proxy_configs/manifests/proxy_condition_manifest.json"


def _load(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


def test_proxy_schema_and_ready_conditions_exist() -> None:
    schema = _load("proxy_condition_schema.yaml")
    assert schema["schema_version"] == "gate-12c-proxy-condition-schema-v1"
    for name in ("alpha_synuclein_proxy_condition.yaml", "pink1_proxy_condition.yaml"):
        document = _load(name)
        assert document["run_status"] == "RUN_READY_FOR_GATE_12D"
        assert document["scope"] == "organism_level_proxy"
        assert document["burden"]["burden_curve"]
        assert document["burden"]["full_burden"] == 1.0
        assert document["provenance"]["reviewer"]
        assert document["provenance"]["review_date"] == "2026-09-02"
        assert document["target_definition"]["gene_specific_mapping"] is False


def test_empty_proxy_targets_are_not_gene_specific() -> None:
    document = _load("pink1_proxy_condition.yaml")
    assert document["target_definition"]["target_neurons"] == []
    assert document["target_definition"]["target_edges"] == []
    blockers, _ = _config_blockers(
        condition_id="pink1",
        config_path=CONFIG_DIR / "pink1_proxy_condition.yaml",
        mapping_scope="not_available",
        proxy_mode=True,
    )
    assert "target_neurons_or_edges_missing" not in blockers
    assert blockers == []


def test_gene_specific_scope_still_requires_targets_and_mapping(tmp_path: Path) -> None:
    source = _load("pink1_proxy_condition.yaml")
    source["scope"] = "gene_specific"
    source["target_definition"]["gene_specific_mapping"] = True
    path = tmp_path / "gene_specific.yaml"
    path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
    blockers, _ = _config_blockers(
        condition_id="pink1",
        config_path=path,
        mapping_scope="gene_specific",
        proxy_mode=True,
    )
    assert "target_neurons_or_edges_missing" in blockers
    assert "root_id_mapping_source_missing" in blockers
    assert "checkpoint_mapping_provenance_missing" in blockers


def test_blocked_conditions_and_manifest_flags_are_preserved() -> None:
    for name in ("parkin_proxy_condition.yaml", "dj1_proxy_condition.yaml", "lrrk2_proxy_condition.yaml"):
        document = _load(name)
        assert document["run_status"] == "BLOCKED"
        assert document["scope"] == "not_ready"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["no_simulation_run"] is True
    assert manifest["no_calibration_run"] is True
    assert manifest["no_holdout_validation_run"] is True
    assert manifest["proxy_not_gene_specific"] is True
    assert manifest["root_id_mapping_available"] is False


def test_proxy_ready_plan_uses_proxy_contract_without_calibration_flags() -> None:
    plan = yaml.safe_load(
        (CONFIG_DIR / "disease_rollout_plan_proxy_ready.yaml").read_text(encoding="utf-8")
    )
    assert _is_proxy_plan(plan) is True
    assert plan["status"] == "READY_FOR_GATE_12D_PROXY_ROLLOUTS"
    assert all("config" in condition for condition in plan["conditions"])
    assert all("calibration" not in condition for condition in plan["conditions"])
    assert all("holdout_validation" not in condition for condition in plan["conditions"])
