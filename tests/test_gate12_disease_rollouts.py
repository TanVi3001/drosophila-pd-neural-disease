from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "experiments/gate_12_disease_rollouts/configs/disease_rollout_plan.yaml"
METRICS = ROOT / "experiments/gate_12_disease_rollouts/results/disease_metrics.csv"
MANIFEST = ROOT / "experiments/gate_12_disease_rollouts/manifests/disease_rollout_manifest.json"
CANONICAL = {"mean_planar_speed_mm_s", "distance_traveled_mm", "displacement_mm"}


def _rows() -> list[dict[str, str]]:
    with METRICS.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_gate12_plan_exists_and_declares_required_conditions() -> None:
    document = yaml.safe_load(PLAN.read_text(encoding="utf-8"))
    assert document["schema_version"] == "gate-12-disease-rollout-plan-v1"
    assert document["seeds"]["values"] == [0, 1, 2, 3, 4, 5]
    assert {row["condition_id"] for row in document["conditions"]} == {
        "alpha_synuclein",
        "pink1",
        "parkin",
        "dj1",
        "lrrk2",
    }


def test_gate12_outputs_exist_and_use_only_canonical_metrics() -> None:
    assert METRICS.is_file()
    assert MANIFEST.is_file()
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert set(document["metric_contract"]) == CANONICAL
    for row in _rows():
        assert "distance_to_speed" not in row
        if row["run_status"] == "PASS":
            for metric in CANONICAL:
                assert math.isfinite(float(row[metric]))
        elif row["run_status"] == "SKIPPED":
            assert row["skip_reason"].strip()
            assert all(not row[metric].strip() for metric in CANONICAL)


def test_gate12_manifest_forbids_calibration_and_holdout() -> None:
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert document["no_calibration"] is True
    assert document["no_holdout_validation"] is True
    assert "no_distance_to_speed_conversion" in document["forbidden_uses"]
