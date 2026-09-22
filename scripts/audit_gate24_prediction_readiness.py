"""Audit Gate24 prospective Parkin prediction readiness without running GPU."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
GATE23_MANIFEST = ROOT / "experiments/gate_23_parkin_driver_defined_validation/manifests/gate23_readiness_manifest.json"
MAPPING = ROOT / "research/validation/gene_specific/parkin/driver_to_connectome_mapping.csv"
COMPATIBILITY = ROOT / "research/validation/prospective/parkin_assay_compatibility.yaml"
FREEZE = ROOT / "research/validation/prospective/parkin_model_freeze.yaml"
CONTRACT = ROOT / "research/validation/prospective/parkin_prediction_contract.yaml"
NEURAL_CONTRACT = ROOT / "research/validation/prospective/parkin_neural_transform_contract.yaml"
SIGNOFF = ROOT / "research/validation/prospective/parkin_prediction_reviewer_signoff.json"
GRID_MANIFEST = ROOT / "research/validation/prospective/parkin_checkpoint_grid_manifest.json"
FIREWALL_MANIFEST = ROOT / "experiments/gate_24_prospective_validation/manifests/holdout_firewall_manifest.json"
EXEC_CONFIG = ROOT / "experiments/gate_24_prospective_validation/configs/gate24_execution_config.yaml"
RESULT = ROOT / "experiments/gate_24_prospective_validation/results/gate24_readiness.json"
MANIFEST = ROOT / "experiments/gate_24_prospective_validation/manifests/gate24_readiness_manifest.json"
REPORT = ROOT / "docs/validation/gate_24_prospective_validation_report.md"
CHECKPOINT = ROOT.parent / "external/fly-brain-audit/data/plastic_weights.pt"
TRANSFORM = ROOT / "src/drosophila_pd_neural/parkin/transform.py"
ACTION_PROXY = ROOT / "src/drosophila_pd_neural/proxy_burden_operator.py"
METRICS = ROOT / "scripts/analyze_healthy_baseline.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return value if isinstance(value, dict) else {}


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return value if isinstance(value, dict) else {}


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _valid_reviewer(value: object) -> bool:
    text = str(value or "").strip().upper()
    return bool(text) and not text.startswith(("NOT_", "PENDING", "TODO", "TBD"))


def _root_set_hash(rows: list[dict[str, str]]) -> str:
    ids = sorted(row.get("root_id", "") for row in rows)
    return hashlib.sha256(("\n".join(ids) + "\n").encode()).hexdigest()


def _resolve_artifact_path(value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else (ROOT / path).resolve()


def _valid_sha(value: object) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text.lower())


def audit(*, write_outputs: bool = True) -> dict[str, Any]:
    """Evaluate Gate 24 readiness, optionally refreshing tracked artifacts."""
    gate23 = _json(GATE23_MANIFEST)
    compatibility = _yaml(COMPATIBILITY)
    freeze = _yaml(FREEZE)
    contract = _yaml(CONTRACT)
    neural_contract = _yaml(NEURAL_CONTRACT)
    grid_manifest = _json(GRID_MANIFEST)
    signoff = _json(SIGNOFF)
    execution = _yaml(EXEC_CONFIG)
    mapping_rows = _rows(MAPPING)
    blockers: list[str] = []

    mapping_sha = _sha256(MAPPING) if MAPPING.is_file() else "MISSING"
    root_hash = _root_set_hash(mapping_rows) if mapping_rows else "MISSING"
    checkpoint_sha = _sha256(CHECKPOINT) if CHECKPOINT.is_file() else "MISSING"
    config_sha = _sha256(EXEC_CONFIG) if EXEC_CONFIG.is_file() else "MISSING"
    transform_sha = _sha256(TRANSFORM) if TRANSFORM.is_file() else "MISSING"
    action_proxy_sha = _sha256(ACTION_PROXY) if ACTION_PROXY.is_file() else "MISSING"
    metric_sha = _sha256(METRICS) if METRICS.is_file() else "MISSING"
    grid_healthy = grid_manifest.get("healthy_checkpoint") or {}
    grid_checkpoint_rows = grid_manifest.get("checkpoints") or []
    grid_parameters = [row.get("parameter") for row in grid_checkpoint_rows if isinstance(row, dict)]
    expected_grid = [0.0, 0.25, 0.5, 0.75, 1.0]
    grid_checkpoint_hashes: dict[str, str] = {}
    grid_artifacts_ready = True
    for row in grid_checkpoint_rows:
        if not isinstance(row, dict):
            grid_artifacts_ready = False
            continue
        parameter = row.get("parameter")
        checkpoint_path = _resolve_artifact_path(row.get("checkpoint_path", ""))
        actual_sha = _sha256(checkpoint_path) if checkpoint_path.is_file() else "MISSING"
        grid_checkpoint_hashes[str(parameter)] = actual_sha
        if not _valid_sha(row.get("checkpoint_sha256")) or actual_sha != row.get("checkpoint_sha256"):
            grid_artifacts_ready = False
        manifest_path = _resolve_artifact_path(row.get("manifest_path", ""))
        artifact_manifest = _json(manifest_path)
        if (
            artifact_manifest.get("status") != "PARKIN_DRIVER_DEFINED_NEURAL_TRANSFORM_READY"
            or artifact_manifest.get("parameter") != parameter
            or artifact_manifest.get("mapping_sha256") != mapping_sha
            or artifact_manifest.get("target_neurons_sha256") != root_hash
            or artifact_manifest.get("target_count") != 330
            or artifact_manifest.get("healthy_checkpoint_modified") is not False
            or artifact_manifest.get("simulation_run") is not False
            or artifact_manifest.get("gpu_executed") is not False
        ):
            grid_artifacts_ready = False

    gate23_status = gate23.get("status", "MISSING")
    if gate23_status != "GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED_READY":
        blockers.append("Gate23 driver-defined mapping is not ready")
    if len(mapping_rows) != 330 or len({row.get("root_id") for row in mapping_rows}) != 330:
        blockers.append("mapping does not contain exactly 330 unique root IDs")
    if mapping_sha != freeze.get("mapping_sha256"):
        blockers.append("Gate23 mapping SHA256 does not match model freeze")
    if root_hash != freeze.get("target_neurons_sha256"):
        blockers.append("330-root set SHA256 does not match model freeze")
    if mapping_rows and any(row.get("mapping_level") != "GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED" for row in mapping_rows):
        blockers.append("mapping level is not consistently driver-defined")
    if mapping_rows and any(row.get("edge_id", "").strip() for row in mapping_rows):
        blockers.append("unexpected edge IDs are present")

    gate24a = compatibility.get("status") == "ASSAY_COMPATIBILITY_LOCKED_DIRECTION_ONLY"
    if not gate24a:
        blockers.append("assay compatibility is not direction-only locked")
    if compatibility.get("quantitative_cross_assay_validation", {}).get("allowed") is not False:
        blockers.append("quantitative cross-assay validation is enabled")

    checkpoint_match = checkpoint_sha == freeze.get("checkpoint", {}).get("sha256")
    config_match = config_sha == freeze.get("config", {}).get("sha256")
    transform_match = transform_sha == freeze.get("disease_transform", {}).get("sha256")
    metric_match = metric_sha == freeze.get("metric_implementation", {}).get("sha256")
    freeze_grid = freeze.get("parkin_checkpoint_grid") or {}
    freeze_grid_hashes = freeze_grid.get("checkpoint_sha256") or {}
    freeze_grid_complete = (
        freeze_grid.get("manifest_path") == _relative(GRID_MANIFEST)
        and freeze_grid.get("manifest_sha256") == (_sha256(GRID_MANIFEST) if GRID_MANIFEST.is_file() else "MISSING")
        and freeze_grid.get("identity_parameter") == 0.0
        and freeze_grid.get("disease_parameters") == [0.25, 0.5, 0.75, 1.0]
        and freeze_grid_hashes == {key: grid_checkpoint_hashes.get(key) for key in ("0.25", "0.5", "0.75", "1.0")}
    )
    model_freeze_complete = (
        freeze.get("status") == "MODEL_FREEZE_COMPLETE"
        and checkpoint_match
        and config_match
        and transform_match
        and metric_match
        and freeze.get("seed_list") == [0, 1, 2, 3, 4]
        and freeze.get("parameter_policy") == "PREREGISTERED_GRID_NO_SINGLE_BIOLOGICAL_PARAMETER"
        and freeze.get("parameter_grid") == expected_grid
        and freeze.get("biological_parameter_equivalence") == "NOT_ASSERTED"
        and freeze.get("posthoc_parameter_selection_allowed") is False
        and freeze.get("neural_transform_contract", {}).get("sha256") == _sha256(NEURAL_CONTRACT)
        and freeze.get("model_commit") == grid_manifest.get("neural_implementation_commit")
        and freeze_grid_complete
        and not any(str(value).startswith("NOT_LOCKED") for value in freeze.values())
    )
    if not model_freeze_complete:
        blockers.append("model freeze hashes or required locks are incomplete")

    neural_contract_locked = (
        neural_contract.get("operation_level") == "NEURAL_PRE_ACTION"
        and neural_contract.get("target_count") == 330
        and neural_contract.get("target_sha256") == root_hash
        and neural_contract.get("mapping_sha256") == mapping_sha
        and neural_contract.get("biological_equivalence") == "NOT_ASSERTED"
        and neural_contract.get("source_code_sha256") == transform_sha
        and neural_contract.get("sensitivity_grid") == [0.0, 0.25, 0.5, 0.75, 1.0]
        and neural_contract.get("parameter_policy") == "PREREGISTERED_GRID_NO_SINGLE_BIOLOGICAL_PARAMETER"
        and neural_contract.get("primary_parameter_selected") is False
        and neural_contract.get("disease_parameters") == [0.25, 0.5, 0.75, 1.0]
    )
    if not neural_contract_locked:
        blockers.append("Parkin neural transform contract is incomplete or stale")
    neural_transform_ready = (
        grid_manifest.get("status") == "GRID_MATERIALIZED"
        and grid_manifest.get("parameter_policy") == "PREREGISTERED_GRID_NO_SINGLE_BIOLOGICAL_PARAMETER"
        and grid_manifest.get("biological_parameter_equivalence") == "NOT_ASSERTED"
        and grid_manifest.get("neural_implementation_commit") == freeze.get("model_commit")
        and grid_manifest.get("operation_level") == "NEURAL_PRE_ACTION"
        and grid_manifest.get("target_count") == 330
        and grid_manifest.get("mapping_sha256") == mapping_sha
        and grid_manifest.get("target_sha256") == root_hash
        and grid_manifest.get("transform_source_sha256") == transform_sha
        and grid_healthy.get("sha256") == checkpoint_sha
        and grid_parameters == [0.25, 0.5, 0.75, 1.0]
        and grid_artifacts_ready
        and all(row.get("identity_test_status") == "PASS" for row in grid_checkpoint_rows if isinstance(row, dict))
    )
    if not neural_transform_ready:
        blockers.append("Parkin neural checkpoint/manifest is not ready; action proxy cannot be primary")

    required_contract_fields = (
        "primary_validation_axis", "expected_direction", "virtual_metrics", "seed_list",
        "holdout_opened", "calibration_data_reused", "tuning_using_holdout",
    )
    contract_locked = (
        contract.get("status") == "PROSPECTIVE_PREDICTION_DRAFTED"
        and all(field in contract for field in required_contract_fields)
        and contract.get("primary_validation_axis") == "LOCOMOTOR_IMPAIRMENT_DIRECTION"
        and contract.get("holdout_opened") is False
        and contract.get("tuning_using_holdout") is False
        and contract.get("calibration_data_reused") is False
        and contract.get("seed_list") == [0, 1, 2, 3, 4]
        and "median_planar_speed_mm_s" in contract.get("virtual_metrics", [])
        and "distance_traveled_mm" in contract.get("virtual_metrics", [])
        and contract.get("primary_disease_representation") == "PARKIN_DRIVER_DEFINED_NEURAL_TRANSFORM"
        and contract.get("operation_level") == "NEURAL_PRE_ACTION"
        and contract.get("action_level_proxy") == "NEGATIVE_CONTROL_ONLY"
        and contract.get("action_proxy_primary") is False
        and contract.get("neural_transform_status") == "PARKIN_DRIVER_DEFINED_NEURAL_TRANSFORM_READY"
        and contract.get("virtual_primary_metric") == "median_planar_speed_mm_s"
        and contract.get("virtual_secondary_metric") == "distance_traveled_mm"
        and contract.get("statistical_unit") == "seed"
        and contract.get("frame_is_statistical_replicate") is False
        and contract.get("paired_seed_policy") == "same seed healthy versus each Parkin parameter"
        and contract.get("parameter_policy", {}).get("type") == "PREREGISTERED_GRID"
        and contract.get("parameter_policy", {}).get("healthy_identity_parameter") == 0.0
        and contract.get("parameter_policy", {}).get("disease_parameters") == [0.25, 0.5, 0.75, 1.0]
        and contract.get("parameter", {}).get("primary_parameter_selected") is False
        and contract.get("grid_level_decision_rule", "").startswith("VIRTUAL_DIRECTIONAL_PREDICTION_SUPPORTED")
        and contract.get("model_commit") == freeze.get("model_commit")
        and contract.get("model_freeze_sha256") == _sha256(FREEZE)
        and contract.get("parkin_checkpoint_grid_manifest_sha256") == _sha256(GRID_MANIFEST)
        and not any("NOT_LOCKED" in str(contract.get(field, "")) for field in required_contract_fields)
    )
    if not contract_locked:
        blockers.append("prospective prediction contract is not locked")

    signoff_complete = (
        signoff.get("status") == "PROSPECTIVE_PREDICTION_LOCKED"
        and signoff.get("decision") == "APPROVED_FOR_BLINDED_VIRTUAL_PREDICTION"
        and _valid_reviewer(signoff.get("reviewer_1"))
        and _valid_reviewer(signoff.get("reviewer_2"))
        and _valid_reviewer(signoff.get("review_date"))
        and signoff.get("holdout_opened") is False
        and signoff.get("tuning_using_holdout") is False
        and signoff.get("mapping_sha256") == mapping_sha
        and signoff.get("target_sha256") == root_hash
        and signoff.get("neural_implementation_commit") == freeze.get("model_commit")
        and signoff.get("parameter_policy") == "PREREGISTERED_GRID_NO_SINGLE_BIOLOGICAL_PARAMETER"
        and signoff.get("model_freeze_sha256") == _sha256(FREEZE)
        and signoff.get("prediction_contract_sha256") == _sha256(CONTRACT)
        and signoff.get("checkpoint_manifest_sha256") == _sha256(GRID_MANIFEST)
        and signoff.get("holdout_firewall_sha256") == _sha256(FIREWALL_MANIFEST)
    )
    if not signoff_complete:
        blockers.append("Gate24D human preregistration signoff is missing")

    if freeze.get("runtime", {}).get("external_runtime_worktree_clean") is not True:
        blockers.append("external FlyGym runtime worktree is dirty; clean runtime commit required before GPU")
    if freeze.get("disease_transform", {}).get("ready_for_parkin_neural_execution") is not True:
        blockers.append("Parkin neural transform is not frozen in model provenance")
    if contract.get("action_proxy_primary") is True:
        blockers.append("action-level proxy is marked primary, which Gate24 forbids")
    gate24e_ready = all((gate23_status == "GENE_SPECIFIC_INTERVENTION_DRIVER_DEFINED_READY", gate24a, model_freeze_complete, contract_locked, signoff_complete, neural_transform_ready)) and not any(
        phrase in blockers for phrase in (
            "external FlyGym runtime worktree is dirty; clean runtime commit required before GPU",
            "Parkin neural transform is not frozen in model provenance",
        )
    )
    result = {
        "schema_version": "gate-24-prospective-validation-readiness-v1",
        "gate23_status": gate23_status,
        "gate24a_status": compatibility.get("status", "MISSING"),
        "gate24b_status": "MODEL_FREEZE_COMPLETE" if model_freeze_complete else "WAITING_MODEL_FREEZE",
        "gate24c_status": contract.get("status", "MISSING") if contract_locked else "WAITING_PROSPECTIVE_PREDICTION_CONTRACT",
        "gate24d_status": "PROSPECTIVE_PREDICTION_LOCKED" if signoff_complete else "WAITING_PROSPECTIVE_PREDICTION_REVIEW",
        "gate24e_status": "READY_FOR_BLINDED_GPU_PREDICTION" if gate24e_ready else "NOT_EXECUTED",
        "holdout_status": "SEALED",
        "mapping_count": len(mapping_rows),
        "mapping_sha256": mapping_sha,
        "target_neurons_sha256": root_hash,
        "checkpoint_sha256": checkpoint_sha,
        "config_sha256": config_sha,
        "metric_implementation_sha256": metric_sha,
        "disease_transform_sha256": transform_sha,
        "action_proxy_sha256": action_proxy_sha,
        "primary_disease_representation": "PARKIN_DRIVER_DEFINED_NEURAL_TRANSFORM",
        "operation_level": "NEURAL_PRE_ACTION",
        "neural_transform_status": "PARKIN_DRIVER_DEFINED_NEURAL_TRANSFORM_READY" if neural_transform_ready else "WAITING_NEURAL_TRANSFORM",
        "action_proxy_primary": False,
        "healthy_checkpoint_sha256": checkpoint_sha,
        "parkin_checkpoint_sha256": "GRID_MANIFEST",
        "parkin_checkpoint_manifest_sha256": _sha256(GRID_MANIFEST) if GRID_MANIFEST.is_file() else "MISSING",
        "parkin_checkpoint_grid": grid_checkpoint_hashes,
        "primary_parameter": "NONE_SELECTED",
        "primary_parameter_status": "PREREGISTERED_GRID_NO_SINGLE_BIOLOGICAL_PARAMETER",
        "seed_list": [0, 1, 2, 3, 4],
        "primary_validation_axis": "LOCOMOTOR_IMPAIRMENT_DIRECTION",
        "virtual_quantitative_endpoints": ["median_planar_speed_mm_s", "distance_traveled_mm", "displacement_mm"],
        "quantitative_cross_assay_validation_allowed": False,
        "holdout_opened": False,
        "holdout_used_for_tuning": False,
        "reviewer_1": signoff.get("reviewer_1", ""),
        "reviewer_2": signoff.get("reviewer_2", ""),
        "blockers": blockers,
        "gpu_executed": False,
        "simulation_executed": False,
        "calibration_executed": False,
        "tuning_executed": False,
        "data_fabricated": False,
        "allowed_claim": "Parkin-specific intervention represented by a reviewed driver-defined neural perturbation and a preregistered directional computational validation protocol; no biological validation claim.",
        "forbidden_claims": ["BIOLOGICALLY_VALIDATED", "PARKINSON_VALIDATED", "GENE_SPECIFIC_BIOLOGICAL_VALIDATION_SUPPORTED", "drug validation"],
    }
    manifest = {
        "schema_version": "gate-24-prospective-validation-manifest-v1",
        "status": result["gate24e_status"],
        "inputs": {
            "assay_compatibility": {"path": _relative(COMPATIBILITY), "sha256": _sha256(COMPATIBILITY)},
            "model_freeze": {"path": _relative(FREEZE), "sha256": _sha256(FREEZE)},
            "prediction_contract": {"path": _relative(CONTRACT), "sha256": _sha256(CONTRACT)},
            "neural_transform_contract": {"path": _relative(NEURAL_CONTRACT), "sha256": _sha256(NEURAL_CONTRACT)},
            "reviewer_signoff": {"path": _relative(SIGNOFF), "sha256": _sha256(SIGNOFF)},
            "mapping": {"path": _relative(MAPPING), "sha256": mapping_sha},
            "parkin_checkpoint_grid_manifest": {"path": _relative(GRID_MANIFEST), "sha256": _sha256(GRID_MANIFEST) if GRID_MANIFEST.is_file() else "MISSING"},
        },
        "holdout_opened": False,
        "no_holdout_tuning": True,
        "gpu_executed": False,
        "simulation_executed": False,
        "data_fabricated": False,
    }
    if write_outputs:
        RESULT.parent.mkdir(parents=True, exist_ok=True)
        RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        _write_report(result)
    return result


def _write_report(result: dict[str, Any]) -> None:
    lines = [
        "# Gate 24 - Parkin prospective validation",
        "",
        f"**Gate23:** `{result['gate23_status']}`",
        f"**Gate24A:** `{result['gate24a_status']}`",
        f"**Gate24B:** `{result['gate24b_status']}`",
        f"**Gate24C:** `{result['gate24c_status']}`",
        f"**Gate24D:** `{result['gate24d_status']}`",
        f"**Gate24E:** `{result['gate24e_status']}`",
        f"**Holdout:** `{result['holdout_status']}`",
        "",
        "## Khóa provenance",
        f"- 330 root IDs: `{result['mapping_count']}`; mapping SHA256 `{result['mapping_sha256']}`.",
        f"- Root-set SHA256: `{result['target_neurons_sha256']}`.",
        f"- Checkpoint SHA256: `{result['checkpoint_sha256']}`; checkpoint không commit vào Git.",
        f"- Parkin neural checkpoint SHA256: `{result['parkin_checkpoint_sha256']}`; materialized CPU-side, không chạy simulation.",
        f"- Neural transform: `{result['neural_transform_status']}`; operation level `{result['operation_level']}`.",
        "- Action-level proxy: `NEGATIVE_CONTROL_ONLY`; không phải primary disease representation.",
        f"- Primary parameter: `{result['primary_parameter']}`; status `{result['primary_parameter_status']}`.",
        f"- Grid checkpoint hashes: `{result['parkin_checkpoint_grid']}`.",
        f"- Config SHA256: `{result['config_sha256']}`.",
        f"- Seed: `{result['seed_list']}`; đơn vị thống kê là seed, frame không phải replicate.",
        "",
        "## Assay và prediction",
        "- DAM counts và climbing position không được chuyển thành FlyGym planar speed.",
        "- Trục xác nhận chính: `LOCOMOTOR_IMPAIRMENT_DIRECTION`.",
        "- Metric ảo phụ: `median_planar_speed_mm_s`, `distance_traveled_mm`, `displacement_mm`.",
        "- Quantitative cross-assay validation: `false`.",
        "- Cackovic holdout chưa mở và không được dùng để chọn burden, seed, checkpoint hoặc threshold.",
        "",
        "## Blocker hiện tại",
        *[f"- {item}" for item in result["blockers"]],
        "",
        "## Claim lock",
        f"> {result['allowed_claim']}",
        "",
        "Không được viết rằng mô hình đã biological Parkinson validation, Parkinson validated, clinical validation hoặc drug validation.",
        "",
        "## Execution boundary",
        "Gate24 lần này chỉ tạo preregistration, firewall, audit và blind-runner. GPU, simulation, calibration, tuning và holdout numerical analysis chưa chạy.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = audit()
    for key in ("gate23_status", "gate24a_status", "gate24b_status", "gate24c_status", "gate24d_status", "gate24e_status", "holdout_status"):
        print(f"{key}: {result[key]}")
    for blocker in result["blockers"]:
        print(f"Blocker: {blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
