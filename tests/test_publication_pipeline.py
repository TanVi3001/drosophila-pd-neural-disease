import json
from pathlib import Path

from scripts.run_publication_pipeline import assess_healthy_baseline, _artifact_inventory


def test_healthy_gate_requires_all_seed_rows(tmp_path: Path) -> None:
    summary = tmp_path / "healthy.json"
    summary.write_text(
        json.dumps(
            {
                "status": "HEALTHY_BASELINE_PASS",
                "simulation_run": True,
                "disease_layer_enabled": False,
                "seeds": [0, 1],
                "steps": 100,
                "timestep_s": 0.1,
                "rows": [
                    {"seed": 0, "status": "PASS", "required_metric_status": "PASS", "quality_status": "PASS"},
                    {"seed": 1, "status": "PASS", "required_metric_status": "PASS", "quality_status": "PASS"},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = assess_healthy_baseline(summary, expected_seeds=[0, 1], expected_steps=100, expected_timestep_s=0.1)

    assert result["status"] == "HEALTHY_BASELINE_QC_PASS"


def test_healthy_gate_blocks_incomplete_quality(tmp_path: Path) -> None:
    summary = tmp_path / "healthy.json"
    summary.write_text(
        json.dumps(
            {
                "status": "HEALTHY_BASELINE_PASS",
                "simulation_run": True,
                "disease_layer_enabled": False,
                "seeds": [0],
                "steps": 100,
                "timestep_s": 0.1,
                "rows": [{"seed": 0, "status": "PASS", "required_metric_status": "PASS", "quality_status": "FAIL"}],
            }
        ),
        encoding="utf-8",
    )

    result = assess_healthy_baseline(summary, expected_seeds=[0], expected_steps=100, expected_timestep_s=0.1)

    assert result["status"] == "HEALTHY_BASELINE_QC_BLOCKED"
    assert any("physical QC" in item for item in result["blockers"])


def test_artifact_inventory_hashes_only_declared_small_outputs(tmp_path: Path) -> None:
    output = tmp_path / "package"
    output.mkdir()
    (output / "summary.json").write_text("{}\n", encoding="utf-8")

    inventory = _artifact_inventory(output, extra_paths=[])

    assert inventory["status"] == "ARTIFACT_PACKAGE_READY"
    assert inventory["large_raw_rollouts_included"] is False
    assert inventory["records"][0]["sha256"]
