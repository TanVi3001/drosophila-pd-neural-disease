from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/gate_13a_chen_objective"
CONFIG = GATE / "configs/chen_only_calibration_objective.yaml"
FEASIBILITY = GATE / "results/chen_objective_feasibility.csv"
CANDIDATES = GATE / "results/chen_calibration_candidates.csv"
MANIFEST = GATE / "manifests/chen_objective_manifest.json"
REPORT = ROOT / "docs/calibration/gate_13a_chen_objective_feasibility_report.md"


def _rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))


def test_gate13a_artifacts_exist_and_have_expected_schema() -> None:
    assert CONFIG.is_file()
    assert FEASIBILITY.is_file()
    assert CANDIDATES.is_file()
    assert MANIFEST.is_file()
    assert REPORT.is_file()

    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["schema_version"] == "gate-13a-chen-only-objective-v1"
    assert config["calibration_scope"]["condition_id"] == "alpha_synuclein"
    assert config["calibration_scope"]["gene_specific_mapping"] is False
    assert config["forbidden"]["use_pozo"] is False
    assert config["forbidden"]["holdout_validation"] is False
    assert config["forbidden"]["calibration_optimization_in_gate_13a"] is False

    feasibility = _rows(FEASIBILITY)
    assert {row["objective_type"] for row in feasibility} == {"absolute", "ratio"}
    absolute = next(row for row in feasibility if row["objective_type"] == "absolute")
    assert absolute["metric"] == "mean_planar_speed_mm_s"
    assert absolute["target_value"] == "4.875"
    assert absolute["uncertainty"] == "0.525"
    assert absolute["uncertainty_type"] == "CI95"
    ratio = next(row for row in feasibility if row["objective_type"] == "ratio")
    assert ratio["metric"] == "mean_planar_speed_ratio_to_control"
    assert math.isclose(float(ratio["target_value"]), 4.875 / 7.275, rel_tol=1e-12)


def test_gate13a_manifest_preserves_no_execution_boundary() -> None:
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert document["status"] == "READY_FOR_GATE_13B_CHEN_RATIO_CALIBRATION"
    assert document["no_calibration_run"] is True
    assert document["no_holdout_validation_run"] is True
    assert document["pozo_used"] is False
    assert document["pink1_used_for_calibration"] is False
    assert document["gene_specific_mapping"] is False
    assert document["biological_validation_claim"] is False
    assert document["objective"]["preferred"] == "mean_planar_speed_ratio_to_control"
    assert document["chen_target"]["matched_control_value_mm_s"] == 7.275
    assert math.isclose(document["chen_target"]["ratio_target"], 4.875 / 7.275, rel_tol=1e-12)


def test_gate13a_candidates_use_only_alpha_synuclein_and_keep_ci95() -> None:
    candidates = _rows(CANDIDATES)
    assert len(candidates) == 5
    assert {row["condition_id"] for row in candidates} == {"alpha_synuclein"}
    assert {row["burden_level"] for row in candidates} == {"0", "0.25", "0.5", "0.75", "1"}
    assert all(row["chen_absolute_target_mm_s"] == "4.875" for row in candidates)
    assert all(row["chen_ratio_target"] for row in candidates)
    positive = [row for row in candidates if float(row["burden_level"]) > 0]
    assert {int(row["candidate_rank_by_ratio"]) for row in positive} == {1, 2, 3, 4}
    assert all(row["usable_for_gate_13b"] == "true" for row in positive)

    feasibility = _rows(FEASIBILITY)
    assert next(row for row in feasibility if row["objective_type"] == "absolute")["uncertainty_type"] == "CI95"
    report = REPORT.read_text(encoding="utf-8")
    assert "Pozo" in report
    assert "PINK1" in report
    assert "CI95" in report
    assert "không chạy calibration" in report
