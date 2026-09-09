import json

import pytest

from scripts import run_gate24_blinded_parkin_prediction as runner
from scripts.run_gate24e_runtime_adapter import PLAN as FROZEN_PLAN_PATH


FROZEN_PLAN = json.loads(FROZEN_PLAN_PATH.read_text(encoding="utf-8"))


def _frozen_ready_result() -> dict:
    """Return the reviewed pre-execution state without auditing local externals."""

    return {
        "gate24e_status": "READY_FOR_BLINDED_GPU_PREDICTION",
        "primary_disease_representation": "PARKIN_DRIVER_DEFINED_NEURAL_TRANSFORM",
        "neural_transform_status": "PARKIN_DRIVER_DEFINED_NEURAL_TRANSFORM_READY",
        "action_proxy_primary": False,
        "healthy_checkpoint_sha256": FROZEN_PLAN["jobs"][0]["healthy_checkpoint_sha256"],
        "primary_parameter_status": FROZEN_PLAN["parameter_policy"],
        "seed_list": FROZEN_PLAN["seed_list"],
        "primary_validation_axis": "LOCOMOTOR_IMPAIRMENT_DIRECTION",
        "holdout_opened": False,
        "holdout_used_for_tuning": False,
        "blockers": [],
    }


@pytest.fixture
def frozen_runner(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(runner, "audit", _frozen_ready_result)
    return runner


def test_gate24_blind_runner_builds_ready_plan_without_executing_gpu(frozen_runner) -> None:
    plan = frozen_runner.build_execution_plan()
    assert plan["status"] == "READY_FOR_BLINDED_GPU_PREDICTION"
    assert plan["commands_built"] is True
    assert plan["commands_executed"] is False
    assert plan["gpu_executed"] is False
    assert plan["blockers"] == []


def test_gate24_blind_runner_keeps_holdout_closed(frozen_runner) -> None:
    plan = frozen_runner.build_execution_plan()
    assert plan["holdout_opened"] is False
    assert plan["tuning_using_holdout"] is False
