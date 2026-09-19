from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("run_lif_condition", ROOT / "scripts" / "run_lif_condition.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
EVAL_SPEC = importlib.util.spec_from_file_location(
    "evaluate_2024_baseline", ROOT / "scripts" / "evaluate_2024_baseline.py"
)
assert EVAL_SPEC is not None and EVAL_SPEC.loader is not None
EVAL_MODULE = importlib.util.module_from_spec(EVAL_SPEC)
EVAL_SPEC.loader.exec_module(EVAL_MODULE)


def test_lif_manifest_trial_count_is_explicit(tmp_path: Path) -> None:
    manifest = tmp_path / "run_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "lif-run-manifest-1",
                "status": "PASS",
                "trial_count": 7,
            }
        ),
        encoding="utf-8",
    )

    assert MODULE._declared_trial_count(manifest) == 7


def test_lif_intervention_preserves_outgoing_block_semantics() -> None:
    intervention = MODULE._intervention([], [720575940624963786])

    assert intervention["type"] == "outgoing_synapse_block"
    assert intervention["outgoing_synapse_block_ids"] == ["720575940624963786"]
    assert "not neuron death" in intervention["semantic_boundary"]


def test_lif_runner_rejects_invalid_trial_count_before_runtime(tmp_path: Path) -> None:
    args = MODULE.build_parser().parse_args(
        ["--output", str(tmp_path), "--trials", "0"]
    )

    with pytest.raises(ValueError, match="trials must be positive"):
        MODULE.run_condition(args)


def test_evaluator_reports_explicit_readout_rate_including_silent_trials(tmp_path: Path) -> None:
    pd = pytest.importorskip("pandas")
    spikes = tmp_path / "spikes.parquet"
    pd.DataFrame(
        {
            "t": [0.1, 0.2],
            "trial": [0, 1],
            "flywire_id": ["100", "200"],
            "exp_name": ["condition", "condition"],
        }
    ).to_parquet(spikes, index=False)
    manifest = tmp_path / "run_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "lif-run-manifest-1",
                "status": "PASS",
                "trial_count": 4,
            }
        ),
        encoding="utf-8",
    )
    completeness = tmp_path / "completeness.csv"
    pd.DataFrame({"complete": [True, True]}, index=["200", "300"]).to_csv(completeness)
    output = tmp_path / "metrics.json"

    report = EVAL_MODULE.evaluate(
        spike_path=spikes,
        output_path=output,
        duration_s=1.0,
        readout_ids=[200, 300],
        completeness_path=completeness,
        run_manifest_path=manifest,
    )

    assert report["metrics"]["readout_rates_hz"] == {"200": 0.25, "300": 0}
    assert report["data_audit"]["declared_readout_ids_in_output"] == ["200"]
    assert report["data_audit"]["declared_readout_ids_silent"] == ["300"]
    assert report["trial_count_source"] == str(manifest.resolve())


def test_evaluator_does_not_treat_unknown_readout_as_silent(tmp_path: Path) -> None:
    pd = pytest.importorskip("pandas")
    spikes = tmp_path / "spikes.parquet"
    pd.DataFrame(
        {"t": [0.1], "trial": [0], "flywire_id": ["200"], "exp_name": ["condition"]}
    ).to_parquet(spikes, index=False)
    manifest = tmp_path / "run_manifest.json"
    manifest.write_text(
        json.dumps({"schema_version": "lif-run-manifest-1", "status": "PASS", "trial_count": 1}),
        encoding="utf-8",
    )
    completeness = tmp_path / "completeness.csv"
    pd.DataFrame({"complete": [True]}, index=["200"]).to_csv(completeness)

    with pytest.raises(ValueError, match="absent from the completeness inventory"):
        EVAL_MODULE.evaluate(
            spike_path=spikes,
            output_path=tmp_path / "metrics.json",
            duration_s=1.0,
            readout_ids=["300"],
            completeness_path=completeness,
            run_manifest_path=manifest,
        )


def test_neuron_id_parser_rejects_float_and_preserves_long_id() -> None:
    long_id = "720575940660219265"
    assert MODULE.build_parser().parse_args(["--output", "out", "--readout-id", long_id]).readout_id == [long_id]
    with pytest.raises(ValueError, match="floating-point"):
        MODULE._normalize_neuron_id(7.205759406602193e17)


def test_annotation_registry_is_namespace_and_dataset_scoped(tmp_path: Path) -> None:
    pd = pytest.importorskip("pandas")
    registry = tmp_path / "annotations.csv"
    pd.DataFrame(
        {
            "neuron_id": ["100", "200"],
            "role": ["activation_input", "primary_readout"],
            "id_namespace": ["flywire_root_id", "flywire_root_id"],
            "dataset_id": ["flywire-630-2023-03-23", "flywire-630-2023-03-23"],
        }
    ).to_csv(registry, index=False)

    info = MODULE._validate_annotation(
        registry,
        declared_ids=[100, 200],
        id_namespace="flywire_root_id",
        dataset_id="flywire-630-2023-03-23",
    )

    assert info["rows"] == 2
    assert info["id_namespace"] == "flywire_root_id"
    with pytest.raises(ValueError, match="dataset_id"):
        MODULE._validate_annotation(
            registry,
            declared_ids=[100],
            id_namespace="flywire_root_id",
            dataset_id="flywire-783",
        )


def test_stimulus_schedule_requires_bounded_windows_and_preserves_ids() -> None:
    schedule = MODULE._load_stimulus_schedule(
        '[{"start_s": 0.0, "end_s": 0.5, "rate_hz": 150.0, "input_ids": ["100"]}]',
        duration_s=1.0,
        inventory={"100", "200"},
    )
    assert schedule[0]["input_ids"] == ["100"]
    assert schedule[0]["rate_hz"] == 150.0

    with pytest.raises(ValueError, match="same input IDs"):
        MODULE._load_stimulus_schedule(
            '[{"start_s": 0.0, "end_s": 0.5, "rate_hz": 150.0, "input_ids": ["100"]}, '
            '{"start_s": 0.25, "end_s": 0.75, "rate_hz": 150.0, "input_ids": ["100"]}]',
            duration_s=1.0,
            inventory={"100"},
        )


def test_schedule_file_is_exposed_by_cli() -> None:
    args = MODULE.build_parser().parse_args(
        ["--output", "out", "--stimulus-schedule-file", "schedule.json"]
    )
    assert str(args.stimulus_schedule_file) == "schedule.json"
