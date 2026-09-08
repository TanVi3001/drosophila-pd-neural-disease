"""Preflight and guarded execution entry point for Gate24 Parkin prediction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_gate24_prediction_readiness import audit


def build_execution_plan() -> dict[str, Any]:
    result = audit()
    clean_platform = (ROOT.parent / "drosophila-pd-flygym-gate24-clean").resolve()
    clean_brain = (ROOT.parent / "external/fly-brain-audit").resolve()
    neural_checkpoint = (ROOT / "results/gate24_neural_transform/parkin/plastic_weights.pt").resolve()
    return {
        "status": result["gate24e_status"],
        "healthy_condition": "healthy",
        "parkin_condition": "parkin_driver_defined_neural_transform",
        "primary_disease_representation": result.get("primary_disease_representation"),
        "neural_transform_status": result.get("neural_transform_status"),
        "action_proxy_primary": result.get("action_proxy_primary"),
        "healthy_checkpoint": result.get("healthy_checkpoint_sha256"),
        "parkin_checkpoint": result.get("parkin_checkpoint_sha256"),
        "runtime": {
            "platform_root": str(clean_platform),
            "brain_root": str(clean_brain),
            "platform_commit": "3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06",
            "clean_worktree_required": True,
        },
        "command_template": [
            "python",
            "scripts/run_neural_experiment.py",
            "--brain-root",
            str(clean_brain),
            "--platform-root",
            str(clean_platform),
            "--prepared-checkpoint",
            str(neural_checkpoint),
            "--device",
            "cuda",
            "--seed",
            "<reviewed-seed>",
        ],
        "seed_list": result["seed_list"],
        "primary_validation_axis": result["primary_validation_axis"],
        "holdout_opened": result["holdout_opened"],
        "tuning_using_holdout": result["holdout_used_for_tuning"],
        "commands_built": True,
        "commands_executed": False,
        "gpu_executed": False,
        "simulation_executed": False,
        "blockers": result["blockers"],
    }


def execute(plan: dict[str, Any]) -> None:
    """Guard the future execution path; this function is never reached while blocked."""

    if plan["status"] != "READY_FOR_BLINDED_GPU_PREDICTION":
        raise RuntimeError("Gate24 preflight is blocked; refusing GPU execution.")
    if plan.get("action_proxy_primary") is True:
        raise RuntimeError("Gate24 refuses an action-level proxy as the primary Parkin representation.")
    if plan.get("primary_disease_representation") != "PARKIN_DRIVER_DEFINED_NEURAL_TRANSFORM":
        raise RuntimeError("Gate24 requires the reviewed neural transform as the primary disease representation.")
    # The concrete external runner command is deliberately assembled only after
    # every immutable lock and human signoff has passed.
    raise RuntimeError("External GPU command must be supplied by the reviewed runtime adapter.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Require every gate before attempting execution.")
    args = parser.parse_args()
    plan = build_execution_plan()
    print(json.dumps(plan, indent=2))
    if args.execute:
        execute(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
