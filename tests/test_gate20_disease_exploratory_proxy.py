from pathlib import Path

import json
import pytest

from scripts.run_disease_exploratory_gate20 import (
    _build_command,
    _load_config,
    _load_checkpoint,
    _read_gate19_metrics,
    _runner_summary,
    build_parser,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments/gate_20_disease_exploratory_proxy/configs/disease_exploratory_proxy_multiseed.yaml"


def test_gate20_config_locks_organism_proxy_protocol() -> None:
    config = _load_config(CONFIG)
    assert config["runtime"]["seeds"] == [0, 1, 2, 3, 4]
    assert config["runtime"]["steps"] == 100000
    assert config["runtime"]["timestep_s"] == 0.0001
    assert [item["condition_id"] for item in config["conditions"]] == ["alpha_synuclein", "pink1"]
    assert all(item["scope"] == "organism_level_proxy" for item in config["conditions"])
    assert all(item["gene_specific_mapping"] is False for item in config["conditions"])
    assert config["scientific_boundary"]["calibration_run"] is False
    assert config["scientific_boundary"]["holdout_validation"] is False


def test_gate20_parser_defaults_to_gate20_config() -> None:
    assert build_parser().parse_args([]).config == CONFIG


def test_gate20_command_uses_real_action_hook_and_healthy_controller() -> None:
    command = _build_command(
        brain_python=Path("brain-python"),
        platform_root=Path("platform"),
        brain_root=Path("brain"),
        operator_config=Path("operator.yaml"),
        seed=2,
        burden=0.5,
        output=Path("output"),
        steps=100000,
        device="cuda",
        stimulus="p9",
        cpg_frequency_hz=12.0,
        video=False,
    )
    assert "--condition" in command and command[command.index("--condition") + 1] == "healthy"
    assert "--enable-proxy-burden-operator" in command
    assert command[command.index("--proxy-burden") + 1] == "0.5"
    assert "--video-output" not in command


def test_gate20_metric_reader_rejects_nonfinite_mapping(tmp_path: Path) -> None:
    path = tmp_path / "metrics.json"
    path.write_text(json.dumps({"contact_ratio": {"contact_0": 1.0, "contact_1": None}}), encoding="utf-8")
    with pytest.raises(ValueError, match="non-numeric"):
        _read_gate19_metrics(path)


def test_gate20_runner_summary_reads_post_run_operator_metadata() -> None:
    summary = _runner_summary(
        "Progress: 1000/1000\n"
        '{"operator_applied": true, "burden_level": 0.5, '
        '"joint_angles_first_before_sha256": "before", '
        '"joint_angles_first_after_sha256": "after"}\n'
        "READY: output\n"
    )
    assert summary["operator_applied"] is True
    assert summary["burden_level"] == 0.5
    assert summary["joint_angles_first_after_sha256"] == "after"


def test_gate20_checkpoint_loads_only_verified_rows(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "pass.qc.json").write_text(
        json.dumps({"condition_id": "alpha_synuclein", "burden_level": 0.5, "seed": 0, "status": "PASS"}),
        encoding="utf-8",
    )
    (logs / "failed.qc.json").write_text(
        json.dumps({"condition_id": "pink1", "burden_level": 0.5, "seed": 0, "status": "FAILED_QC"}),
        encoding="utf-8",
    )
    rows = _load_checkpoint(tmp_path)
    assert len(rows) == 1
    assert rows[0]["condition_id"] == "alpha_synuclein"
