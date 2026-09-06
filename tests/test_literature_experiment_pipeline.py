import json
from pathlib import Path

import yaml

from drosophila_pd_neural.literature_experiment import validate_experiment_plan
from scripts.prepare_literature_constrained_experiment import prepare


ROOT = Path(__file__).resolve().parents[1]
CHEN = ROOT / "experiments/literature_constrained/configs/chen_alpha_syn_calibration.yaml"
POZO = ROOT / "experiments/literature_constrained/configs/pozo_pink1_holdout.yaml"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_chen_protocol_is_ready_without_running_simulation() -> None:
    result = validate_experiment_plan(_load(CHEN), root=ROOT)
    assert result["status"] == "READY_FOR_RUNTIME"
    assert result["ready_for_runtime"] is True
    assert result["virtual_metric"] == "mean_planar_speed_mm_s"


def test_pozo_protocol_is_holdout_distance_only() -> None:
    document = _load(POZO)
    result = validate_experiment_plan(document, root=ROOT)
    assert result["status"] == "READY_FOR_RUNTIME"
    assert result["allocation"] == "holdout"
    assert result["virtual_metric"] == "distance_traveled_mm"


def test_median_is_not_silently_used_as_mean() -> None:
    document = _load(CHEN)
    document["endpoint"]["literature"]["statistic"] = "median"
    result = validate_experiment_plan(document, root=ROOT)
    assert result["status"] == "INVALID_PROTOCOL"
    assert any(item["code"] == "STATISTIC_MISMATCH" for item in result["issues"])


def test_distance_to_speed_bridge_is_rejected() -> None:
    document = _load(POZO)
    document["endpoint"]["virtual"]["metric"] = "mean_planar_speed_mm_s"
    document["endpoint"]["virtual"]["unit"] = "mm/s"
    document["endpoint"]["bridge"] = {
        "type": "physical_unit_conversion",
        "source_unit": "mm",
        "target_unit": "mm/s",
        "factor": 1.0,
        "rationale": "invalid semantic conversion",
        "provenance": "test",
    }
    result = validate_experiment_plan(document, root=ROOT)
    assert result["status"] in {"INVALID_PROTOCOL", "WAITING_TARGET_DATA"}
    assert any(item["code"] == "SEMANTIC_CONVERSION_NOT_ALLOWED" for item in result["issues"])


def test_prepare_writes_manifest_without_simulation(tmp_path: Path) -> None:
    manifest = prepare(CHEN, tmp_path / "prepared")
    saved = json.loads((tmp_path / "prepared" / "experiment_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "READY_FOR_RUNTIME"
    assert saved["simulation_executed"] is False
    assert saved["calibration_executed"] is False
    assert (tmp_path / "prepared" / "preflight_report.md").is_file()
