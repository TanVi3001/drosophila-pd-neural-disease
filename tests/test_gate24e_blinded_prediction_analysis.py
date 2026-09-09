from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Callable

import numpy as np
import pytest

from scripts import analyze_gate24e_blinded_prediction as analyzer


EXECUTOR_SHA = "e" * 64


def _write_json(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")


def _record(path: Path, root: Path) -> dict:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def _speed_default(condition: str, parameter: float, seed: int) -> float:
    healthy = 2.0 + seed * 0.1
    return healthy if condition == "healthy" else healthy - parameter


def _distance_default(condition: str, parameter: float, seed: int) -> float:
    healthy = 20.0 + seed
    return healthy if condition == "healthy" else healthy - 2.0 * parameter


def _case(
    tmp_path: Path,
    *,
    speed: Callable[[str, float, int], float] = _speed_default,
    distance: Callable[[str, float, int], float] = _distance_default,
    derive_job: str | None = None,
) -> dict:
    root = tmp_path
    runs = root / "runs"
    jobs = []
    inventory_jobs = []
    for index, (job_id, seed, condition, parameter) in enumerate(
        analyzer._expected_job_matrix(), start=1
    ):
        output = runs / job_id
        checkpoint = hashlib.sha256(f"checkpoint-{parameter}".encode()).hexdigest()
        job = {
            "job_index": index,
            "job_id": job_id,
            "seed": seed,
            "condition": condition,
            "parameter": parameter,
            "checkpoint_path": str(root / f"checkpoint-{parameter}.pt"),
            "checkpoint_sha256": checkpoint,
            "checkpoint_role": "healthy_frozen_checkpoint"
            if condition == "healthy"
            else "frozen_disease_checkpoint",
            "output_directory": str(output.resolve()),
            "command": ["python", "runner.py"],
        }
        jobs.append(job)
        primary = speed(condition, parameter, seed)
        secondary = distance(condition, parameter, seed)
        _write_json(output / "status.json", {"status": "PASS", "simulation_run": True})
        _write_json(output / "manifest.json", {"artifact_profile": "GATE24E_MEMORY_SAFE"})
        _write_json(
            output / "metadata.json",
            {
                "artifact_profile": "GATE24E_MEMORY_SAFE",
                "simulation": {
                    "random_seed": seed,
                    "brain_checkpoint_sha256": checkpoint,
                },
            },
        )
        metrics = {
            "frame_count": 3,
            "primary_metric": analyzer.PRIMARY_METRIC,
            "secondary_metric": analyzer.SECONDARY_METRIC,
            "scalar_metrics": {
                analyzer.PRIMARY_METRIC: primary,
                analyzer.SECONDARY_METRIC: secondary,
            },
            analyzer.PRIMARY_METRIC: primary,
            analyzer.SECONDARY_METRIC: secondary,
        }
        if job_id == derive_job:
            metrics["scalar_metrics"] = {"walking_speed_mm_s": 999.0}
            metrics.pop(analyzer.PRIMARY_METRIC)
            metrics.pop(analyzer.SECONDARY_METRIC)
        _write_json(output / "metrics/metrics.json", metrics)
        positions = np.asarray(
            [[0.0, 0.0, 0.0], [primary, 0.0, 0.0], [2.0 * primary, 0.0, 0.0]],
            dtype=float,
        )
        np.savez(
            output / "rollout.npz",
            thorax=positions,
            timestamp_s=np.asarray([0.0, 1.0, 2.0]),
        )
        artifacts = {
            name: _record(output / Path(name), root)
            for name in analyzer.REQUIRED_ARTIFACTS
        }
        inventory_jobs.append(
            {
                "job_index": index,
                "job_id": job_id,
                "seed": seed,
                "condition": condition,
                "parameter": parameter,
                "output_relative_path": output.relative_to(root).as_posix(),
                "artifacts": artifacts,
            }
        )

    plan = {
        "schema_version": "gate24e-scientific-batch-plan-v1",
        "study_id": "parkin_prospective_validation",
        "status": analyzer.EXPECTED_PLAN_STATUS,
        "job_count": 25,
        "ordering": "SEED_MAJOR",
        "scientific_seeds": list(analyzer.SEEDS),
        "parameter_grid": [0.0, *analyzer.PARAMETERS],
        "healthy_job_count": 5,
        "parkin_job_count": 20,
        "technical_seed_excluded": 9001,
        "model_commit": "model-commit",
        "runtime_commit": "runtime-commit",
        "artifact_profile": "GATE24E_MEMORY_SAFE",
        "primary_metric": analyzer.PRIMARY_METRIC,
        "secondary_metric": analyzer.SECONDARY_METRIC,
        "jobs": jobs,
        "scientific_jobs_executed": 0,
        "scientific_batch_authorized": False,
        "holdout": "SEALED",
        "tuning_allowed": False,
        "posthoc_selection_allowed": False,
        "simulation_executed": False,
        "gpu_executed": False,
    }
    plan_sha = analyzer._canonical_json_sha256(plan)
    plan_path = root / "scientific_batch_plan.json"
    _write_json(plan_path, plan)
    execution = {
        "status": analyzer.EXPECTED_EXECUTION_STATUS,
        "planned_job_count": 25,
        "executed_job_count": 25,
        "completed_job_count": 25,
        "failed_job_count": 0,
        "gpu_jobs_executed": 25,
        "simulation_jobs_executed": 25,
        "analysis_performed": False,
        "scientific_interpretation_performed": False,
        "scientific_batch_authorized": True,
        "holdout": "SEALED",
        "plan_sha256": plan_sha,
        "completed_job_ids": [job["job_id"] for job in jobs],
    }
    execution_path = root / "scientific_batch_execution.json"
    _write_json(execution_path, execution)
    inventory = {
        "status": analyzer.EXPECTED_INVENTORY_STATUS,
        "job_count": 25,
        "artifact_count": 125,
        "scientific_plan_sha256": plan_sha,
        "executor_sha256": EXECUTOR_SHA,
        "holdout": "SEALED",
        "analysis_performed": False,
        "scientific_interpretation_performed": False,
        "technical_artifact_qc": "PASS",
        "jobs": inventory_jobs,
    }
    inventory_path = root / "scientific_batch_artifact_inventory.json"
    _write_json(inventory_path, inventory)
    return {
        "root": root,
        "runs": runs,
        "plan": plan,
        "plan_path": plan_path,
        "plan_sha": plan_sha,
        "execution": execution,
        "execution_path": execution_path,
        "inventory": inventory,
        "inventory_path": inventory_path,
        "output": root / "results",
        "freeze": root / "manifests/immutable_virtual_prediction_freeze.json",
    }


def _analyze(case: dict) -> dict:
    return analyzer.analyze(
        plan_path=case["plan_path"],
        execution_path=case["execution_path"],
        inventory_path=case["inventory_path"],
        output_dir=case["output"],
        freeze_path=case["freeze"],
        report_path=None,
        repository_root=case["root"],
        runs_root=case["runs"],
        expected_plan_sha256=case["plan_sha"],
        expected_executor_sha256=EXECUTOR_SHA,
        analyzer_source_path=Path(analyzer.__file__),
    )


def _rewrite_plan(case: dict) -> None:
    case["plan_sha"] = analyzer._canonical_json_sha256(case["plan"])
    _write_json(case["plan_path"], case["plan"])
    case["execution"]["plan_sha256"] = case["plan_sha"]
    _write_json(case["execution_path"], case["execution"])
    case["inventory"]["scientific_plan_sha256"] = case["plan_sha"]
    _write_json(case["inventory_path"], case["inventory"])


def test_repository_scientific_plan_has_exact_canonical_sha() -> None:
    plan = analyzer.load_scientific_plan(analyzer.SCIENTIFIC_PLAN)
    assert analyzer._canonical_json_sha256(plan) == analyzer.EXPECTED_PLAN_SHA256


def test_stale_job_plan_cannot_be_used() -> None:
    with pytest.raises(analyzer.AnalysisError, match="Only scientific_batch_plan"):
        analyzer.load_scientific_plan(analyzer.STALE_JOB_PLAN)


def test_wrong_scientific_plan_sha_is_rejected(tmp_path: Path) -> None:
    case = _case(tmp_path)
    with pytest.raises(analyzer.AnalysisError, match="SHA256 mismatch"):
        analyzer.load_scientific_plan(case["plan_path"], expected_sha256="0" * 64)


def test_execution_must_be_25_of_25_complete(tmp_path: Path) -> None:
    case = _case(tmp_path)
    case["execution"]["completed_job_count"] = 24
    _write_json(case["execution_path"], case["execution"])
    with pytest.raises(analyzer.AnalysisError, match="completed_job_count"):
        _analyze(case)


def test_artifact_drift_stops_before_any_metric_json_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(tmp_path)
    metric = case["runs"] / "seed00_healthy/metrics/metrics.json"
    metric.write_text("{}\n", encoding="utf-8")
    reads: list[Path] = []
    original = analyzer._read_json

    def recording_read(path: Path) -> dict:
        reads.append(path)
        return original(path)

    monkeypatch.setattr(analyzer, "_read_json", recording_read)
    with pytest.raises(analyzer.AnalysisError) as caught:
        _analyze(case)
    assert caught.value.status == analyzer.ARTIFACT_DRIFT_STATUS
    assert not any(path.name == "metrics.json" for path in reads)
    assert not case["output"].exists()


def test_exact_five_scientific_seeds_are_required(tmp_path: Path) -> None:
    case = _case(tmp_path)
    case["plan"]["scientific_seeds"] = [0, 1, 2, 3]
    _rewrite_plan(case)
    with pytest.raises(analyzer.AnalysisError, match="exactly seeds"):
        _analyze(case)


def test_technical_seed_9001_is_rejected(tmp_path: Path) -> None:
    case = _case(tmp_path)
    case["plan"]["jobs"][0]["seed"] = 9001
    _rewrite_plan(case)
    with pytest.raises(analyzer.AnalysisError, match="job matrix"):
        _analyze(case)


def test_parkin_parameter_zero_is_not_in_expected_matrix() -> None:
    matrix = analyzer._expected_job_matrix()
    assert not any(condition == "parkin" and parameter == 0.0 for _, _, condition, parameter in matrix)
    assert len(matrix) == 25


def test_same_seed_pairing_is_preserved(tmp_path: Path) -> None:
    case = _case(tmp_path)
    _analyze(case)
    with (case["output"] / "paired_effects.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 20
    assert all(row["healthy_job_id"].startswith(f"seed{int(row['seed']):02d}_") for row in rows)
    assert all(row["parkin_job_id"].startswith(f"seed{int(row['seed']):02d}_") for row in rows)


def test_median_paired_delta_rule_supports_all_negative_levels(tmp_path: Path) -> None:
    case = _case(tmp_path)
    summary = _analyze(case)
    assert summary["grid_decision"] == "VIRTUAL_DIRECTIONAL_PREDICTION_SUPPORTED"
    assert all(row["median_paired_delta_speed_mm_s"] < 0 for row in summary["parameter_summaries"])


def test_mixed_direction_is_inconclusive() -> None:
    assert analyzer.decision_for_directions(
        {0.25: True, 0.50: False, 0.75: True, 1.00: True}
    ) == "DIRECTIONAL_VALIDATION_INCONCLUSIVE"


def test_failure_at_maximum_parameter_is_not_supported() -> None:
    assert analyzer.decision_for_directions(
        {0.25: True, 0.50: True, 0.75: True, 1.00: False}
    ) == "DIRECTIONAL_VALIDATION_NOT_SUPPORTED"


def test_all_four_nonzero_parameters_are_required() -> None:
    assert analyzer.PARAMETERS == (0.25, 0.50, 0.75, 1.00)
    assert analyzer.decision_for_directions({0.25: True, 0.50: True, 0.75: True}) == (
        "DIRECTIONAL_VALIDATION_NOT_SUPPORTED"
    )


def test_secondary_distance_cannot_override_primary_speed(tmp_path: Path) -> None:
    def faster_disease(condition: str, parameter: float, seed: int) -> float:
        return 2.0 if condition == "healthy" else 3.0

    def shorter_distance(condition: str, parameter: float, seed: int) -> float:
        return 20.0 if condition == "healthy" else 1.0

    case = _case(tmp_path, speed=faster_disease, distance=shorter_distance)
    summary = _analyze(case)
    assert summary["grid_decision"] == "DIRECTIONAL_VALIDATION_NOT_SUPPORTED"


def test_no_posthoc_parameter_selection(tmp_path: Path) -> None:
    case = _case(tmp_path)
    summary = _analyze(case)
    assert summary["posthoc_parameter_selection"] is False
    assert "selected_parameter" not in summary


def test_analyzer_does_not_access_uninventoried_holdout_file(tmp_path: Path) -> None:
    case = _case(tmp_path)
    trap = tmp_path / "sealed_validation_data.json"
    trap.write_text("DO_NOT_READ", encoding="utf-8")
    before = trap.read_bytes()
    summary = _analyze(case)
    assert trap.read_bytes() == before
    assert summary["holdout"] == "SEALED"
    assert summary["holdout_opened"] is False
    assert summary["tuning_using_holdout"] is False


def test_exactly_25_valid_jobs_are_required(tmp_path: Path) -> None:
    case = _case(tmp_path)
    metric = case["runs"] / "seed04_parkin_p100/metrics/metrics.json"
    document = json.loads(metric.read_text(encoding="utf-8"))
    document[analyzer.PRIMARY_METRIC] = None
    document["scalar_metrics"][analyzer.PRIMARY_METRIC] = None
    metric.write_text(json.dumps(document) + "\n", encoding="utf-8")
    inventory_row = case["inventory"]["jobs"][-1]
    inventory_row["artifacts"]["metrics/metrics.json"] = _record(metric, case["root"])
    _write_json(case["inventory_path"], case["inventory"])
    with pytest.raises(analyzer.AnalysisError, match="metric/QC contract is incomplete"):
        _analyze(case)


def test_missing_exact_metrics_are_derived_from_frozen_rollout(tmp_path: Path) -> None:
    case = _case(tmp_path, derive_job="seed00_healthy")
    summary = _analyze(case)
    assert summary["metric_provenance_counts"] == {
        "DIRECT_LOCKED_METRIC": 24,
        "DERIVED_FROM_FROZEN_ROLLOUT": 1,
    }
    with (case["output"] / "virtual_per_seed.csv").open(encoding="utf-8", newline="") as handle:
        first = next(csv.DictReader(handle))
    assert first["metric_provenance"] == "DERIVED_FROM_FROZEN_ROLLOUT"
    assert float(first[analyzer.PRIMARY_METRIC]) != 999.0


def test_mean_speed_alias_is_never_substituted_for_median(tmp_path: Path) -> None:
    case = _case(tmp_path, derive_job="seed00_healthy")
    _analyze(case)
    with (case["output"] / "virtual_per_seed.csv").open(encoding="utf-8", newline="") as handle:
        first = next(csv.DictReader(handle))
    assert float(first[analyzer.PRIMARY_METRIC]) == pytest.approx(2.0)


def test_output_contract_has_exact_four_analysis_files(tmp_path: Path) -> None:
    case = _case(tmp_path)
    _analyze(case)
    assert {path.name for path in case["output"].iterdir()} == {
        "virtual_per_seed.csv",
        "paired_effects.csv",
        "parameter_summary.csv",
        "virtual_prediction_summary.json",
    }


def test_freeze_hash_is_deterministic(tmp_path: Path) -> None:
    artifact = tmp_path / "result.json"
    artifact.write_text("{}\n", encoding="utf-8")
    kwargs = {
        "analysis_artifacts": [artifact],
        "repository_root": tmp_path,
        "scientific_plan_sha256": "1" * 64,
        "scientific_plan_file_sha256": "2" * 64,
        "artifact_inventory_sha256": "3" * 64,
        "execution_manifest_sha256": "4" * 64,
        "analyzer_source_sha256": "5" * 64,
        "executor_sha256": "6" * 64,
        "runtime_commit": "runtime",
        "model_commit": "model",
        "grid_decision": "decision",
    }
    first = analyzer.build_freeze_document(**kwargs)
    second = analyzer.build_freeze_document(**kwargs)
    assert first["virtual_prediction_freeze_sha256"] == second["virtual_prediction_freeze_sha256"]


def test_changed_result_changes_freeze_sha(tmp_path: Path) -> None:
    artifact = tmp_path / "result.json"
    artifact.write_text("{\"value\": 1}\n", encoding="utf-8")
    kwargs = {
        "analysis_artifacts": [artifact],
        "repository_root": tmp_path,
        "scientific_plan_sha256": "1" * 64,
        "scientific_plan_file_sha256": "2" * 64,
        "artifact_inventory_sha256": "3" * 64,
        "execution_manifest_sha256": "4" * 64,
        "analyzer_source_sha256": "5" * 64,
        "executor_sha256": "6" * 64,
        "runtime_commit": "runtime",
        "model_commit": "model",
        "grid_decision": "decision",
    }
    before = analyzer.build_freeze_document(**kwargs)["virtual_prediction_freeze_sha256"]
    artifact.write_text("{\"value\": 2}\n", encoding="utf-8")
    after = analyzer.build_freeze_document(**kwargs)["virtual_prediction_freeze_sha256"]
    assert before != after


def test_frozen_prediction_cannot_be_silently_rerun(tmp_path: Path) -> None:
    case = _case(tmp_path)
    _analyze(case)
    with pytest.raises(analyzer.AnalysisError, match="already present"):
        _analyze(case)


def test_artifact_inventory_cannot_escape_runs_root(tmp_path: Path) -> None:
    case = _case(tmp_path)
    case["inventory"]["jobs"][0]["artifacts"]["metrics/metrics.json"]["path"] = (
        "sealed_validation_data.json"
    )
    _write_json(case["inventory_path"], case["inventory"])
    with pytest.raises(analyzer.AnalysisError, match="escapes the frozen runs"):
        _analyze(case)


def test_summary_preserves_statistical_and_claim_boundaries(tmp_path: Path) -> None:
    case = _case(tmp_path)
    summary = _analyze(case)
    assert summary["statistical_unit"] == "seed"
    assert summary["frame_is_statistical_replicate"] is False
    assert summary["biological_validation_claim"] == "NOT_ALLOWED_AT_GATE24E"
    assert summary["seed_list"] == [0, 1, 2, 3, 4]


def test_repository_freeze_package_hashes_are_self_consistent() -> None:
    if not analyzer.FREEZE_MANIFEST.is_file():
        pytest.skip("Gate24E-S4J package is generated after unit validation.")
    freeze = json.loads(analyzer.FREEZE_MANIFEST.read_text(encoding="utf-8"))
    frozen_sha = freeze.pop("virtual_prediction_freeze_sha256")
    assert analyzer._canonical_json_sha256(freeze) == frozen_sha
    assert freeze["holdout"] == "SEALED"
    assert freeze["holdout_opened"] is False
    for record in freeze["analysis_artifacts"]:
        path = analyzer.ROOT / record["path"]
        assert path.stat().st_size == record["size_bytes"]
        assert analyzer._sha256(path) == record["sha256"]
