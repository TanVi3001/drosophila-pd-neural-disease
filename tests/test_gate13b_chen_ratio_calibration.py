from __future__ import annotations

import csv
import importlib.util
import json
import math
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/gate_13b_chen_ratio_calibration"
CONFIG = GATE / "configs/chen_ratio_calibration_config.yaml"
CALIBRATED_CONFIG = GATE / "configs/calibrated_alpha_synuclein_proxy.yaml"
RESULTS = GATE / "results/chen_ratio_calibration_results.csv"
SUMMARY = GATE / "results/chen_ratio_calibration_summary.json"
MANIFEST = GATE / "manifests/chen_ratio_calibration_manifest.json"
REPORT = ROOT / "docs/calibration/gate_13b_chen_ratio_calibration_report.md"
SCRIPT = ROOT / "scripts/run_chen_ratio_calibration.py"


def _rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))


def test_gate13b_script_imports_and_outputs_exist() -> None:
    assert SCRIPT.is_file()
    spec = importlib.util.spec_from_file_location("gate13b_runner", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.run_calibration)
    for path in (CONFIG, CALIBRATED_CONFIG, RESULTS, SUMMARY, MANIFEST, REPORT):
        assert path.is_file(), path


def test_gate13b_config_locks_chen_ratio_scope() -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["schema_version"] == "gate-13b-chen-ratio-calibration-config-v1"
    assert config["calibration_scope"]["condition_id"] == "alpha_synuclein"
    assert config["calibration_scope"]["gene_specific_mapping"] is False
    assert config["chen_target"]["metric"] == "mean_planar_speed_ratio_to_control"
    assert config["chen_target"]["ratio_target"] == 0.6701030927835051
    assert config["chen_target"]["uncertainty_type"] == "CI95"
    assert config["forbidden"]["use_pozo"] is True
    assert config["forbidden"]["use_pink1_for_calibration"] is True
    assert config["forbidden"]["holdout_validation"] is True
    assert config["forbidden"]["ci95_to_se_conversion"] is True


def test_gate13b_selects_one_nonzero_burden_and_preserves_boundary() -> None:
    rows = _rows(RESULTS)
    assert len(rows) == 5
    assert {row["condition_id"] for row in rows} == {"alpha_synuclein"}
    selected = [row for row in rows if row["selected"] == "true"]
    assert len(selected) == 1
    assert float(selected[0]["burden_level"]) == 0.5
    assert float(selected[0]["ratio_error"]) < 0.1
    assert math.isfinite(float(selected[0]["simulated_ratio_to_burden0"]))
    assert all(row["chen_ratio_target"] == "0.670103092784" for row in rows)
    assert rows[0]["burden_level"] == "0"
    assert rows[0]["selected"] == "false"
    assert rows[0]["usable_for_calibration"] == "false"

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["status"] == "CHEN_RATIO_CALIBRATION_PASS"
    assert summary["selected_burden_level"] == 0.5
    assert summary["pozo_used"] is False
    assert summary["pink1_used_for_calibration"] is False
    assert summary["no_holdout_validation_run"] is True
    assert summary["no_new_simulation_run"] is True
    assert summary["gene_specific_mapping"] is False
    assert summary["biological_validation_claim"] is False

    calibrated = yaml.safe_load(CALIBRATED_CONFIG.read_text(encoding="utf-8"))
    assert calibrated["status"] == "CHEN_RATIO_CALIBRATED"
    assert calibrated["selected_parameter"]["selected_value"] == 0.5
    assert calibrated["calibration_source"]["uncertainty_type"] == "CI95"
    assert calibrated["calibration_source"]["ci95_converted_to_se"] is False


def test_gate13b_manifest_and_report_forbid_downstream_overclaim() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "gate-13b-chen-ratio-calibration-manifest-v1"
    assert manifest["status"] == "CHEN_RATIO_CALIBRATION_PASS"
    assert manifest["no_pozo_used"] is True
    assert manifest["no_pink1_calibration"] is True
    assert manifest["no_holdout_validation_run"] is True
    assert manifest["no_new_simulation_run"] is True
    assert manifest["no_gene_specific_mapping"] is True
    assert manifest["no_biological_validation_claim"] is True
    assert manifest["large_artifacts_committed"] is False
    report = REPORT.read_text(encoding="utf-8")
    assert "CHEN_RATIO_CALIBRATION_PASS" in report
    assert "Không chạy holdout validation" in report
    assert "Không dùng Pozo" in report
    assert "Không phải biological Parkinson validation" in report
