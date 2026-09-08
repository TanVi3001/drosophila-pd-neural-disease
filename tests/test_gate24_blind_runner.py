from scripts.run_gate24_blinded_parkin_prediction import build_execution_plan


def test_gate24_blind_runner_builds_ready_plan_without_executing_gpu() -> None:
    plan = build_execution_plan()
    assert plan["status"] == "READY_FOR_BLINDED_GPU_PREDICTION"
    assert plan["commands_built"] is True
    assert plan["commands_executed"] is False
    assert plan["gpu_executed"] is False
    assert plan["blockers"] == []


def test_gate24_blind_runner_keeps_holdout_closed() -> None:
    plan = build_execution_plan()
    assert plan["holdout_opened"] is False
    assert plan["tuning_using_holdout"] is False
