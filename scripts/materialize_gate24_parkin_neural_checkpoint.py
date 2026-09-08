"""Materialize a CPU-only Parkin neural checkpoint with auditable provenance.

This command never runs a brain-body simulation and never overwrites the
healthy checkpoint. The default parameter is only a preregistered sensitivity
candidate; it is not a biological percentage or a locked primary value.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.parkin.mapping import load_completeness_root_ids, load_reviewed_mapping, sha256_file
from drosophila_pd_neural.parkin.protocol import PARAMETER_GRID, TRANSFORM_ID, validate_parameter
from drosophila_pd_neural.parkin.transform import apply_parkin_transform_from_root_ids


DEFAULT_BRAIN_ROOT = ROOT.parent / "external" / "fly-brain-audit"
DEFAULT_MAPPING = ROOT / "research/validation/gene_specific/parkin/driver_to_connectome_mapping.csv"
DEFAULT_COMPLETENESS = DEFAULT_BRAIN_ROOT / "data/2025_Completeness_783.csv"
DEFAULT_CONNECTIVITY = DEFAULT_BRAIN_ROOT / "data/2025_Connectivity_783.parquet"
DEFAULT_HEALTHY = DEFAULT_BRAIN_ROOT / "data/plastic_weights.pt"
DEFAULT_OUTPUT = ROOT / "results/gate24_neural_transform/parkin"
EXPECTED_MAPPING_SHA = "776274356c16eb458ef945e2a5153af4676bbddebef31cdb1b698f1d6aeaaf80"
EXPECTED_ROOT_SHA = "e36b0210ea6d2d2b7225f62feba73ae5c9e6535565c8b936558d0eaaf04a2085"
EXPECTED_HEALTHY_SHA = "d51dcd9aa028dd7b54ca870bb795752833f76eac8a613cd28e7cbfd83154a691"
PLATFORM_COMMIT = "3ceb8ce441e2eb40bc6c0b6b7be14c1c1aaecf06"


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def _load_torch():
    try:
        import torch
    except (ImportError, OSError) as exc:
        raise RuntimeError("PyTorch is required for CPU checkpoint materialization.") from exc
    if torch.cuda.is_available() and str(__import__("os").environ.get("CUDA_VISIBLE_DEVICES", "")) not in {"", "-1"}:
        # Loading remains map_location=cpu, but the task must be explicit about
        # not executing any CUDA work.
        pass
    return torch


def _checkpoint_vector(torch: Any, path: Path):
    try:
        loaded = torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        loaded = torch.load(path, map_location="cpu")
    if isinstance(loaded, dict):
        for key in ("weights", "weight", "values", "synaptic_weights"):
            if key in loaded:
                loaded = loaded[key]
                break
    if not isinstance(loaded, torch.Tensor) or loaded.layout != torch.strided or loaded.ndim != 1:
        raise RuntimeError("Healthy checkpoint must be a dense one-dimensional tensor.")
    if not bool(torch.isfinite(loaded).all()):
        raise RuntimeError("Healthy checkpoint contains NaN or Inf.")
    return loaded.detach().cpu()


def _presynaptic_indices(path: Path) -> np.ndarray:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas/pyarrow is required to read the pinned connectome parquet.") from exc
    frame = pd.read_parquet(path, columns=["Presynaptic_Index"])
    values = pd.to_numeric(frame["Presynaptic_Index"], errors="coerce").to_numpy()
    if not np.isfinite(values).all() or not np.equal(values, values.astype(np.int64)).all():
        raise RuntimeError("Connectome presynaptic indices are not finite integers.")
    return values.astype(np.int64)


def _write_blocked(output: Path, status: str, message: str, **extra: object) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "schema_version": "gate24-1-parkin-neural-checkpoint-v1",
        "status": status,
        "message": message,
        "simulation_run": False,
        "calibration_run": False,
        "holdout_validation_run": False,
        "gpu_executed": False,
        "healthy_checkpoint_modified": False,
        "data_fabricated": False,
        "created_at_utc": datetime.now(UTC).isoformat(),
        **extra,
    }
    (output / "manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (output / "status.md").write_text(f"# Gate24.1 Parkin neural checkpoint\n\n**Status:** `{status}`\n\n{message}\n", encoding="utf-8")
    return payload


def materialize(
    *,
    healthy_checkpoint: Path,
    mapping_path: Path,
    completeness_path: Path,
    connectivity_path: Path,
    output: Path,
    parameter: float,
) -> dict[str, object]:
    strength = validate_parameter(parameter)
    if strength not in PARAMETER_GRID:
        raise ValueError(f"Parameter must be one of the preregistered values: {PARAMETER_GRID}")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not healthy_checkpoint.is_file():
        return _write_blocked(output, "WAITING_HEALTHY_CHECKPOINT", f"Missing healthy checkpoint: {healthy_checkpoint}")
    actual_healthy = sha256_file(healthy_checkpoint)
    if actual_healthy != EXPECTED_HEALTHY_SHA:
        return _write_blocked(
            output,
            "WAITING_HEALTHY_CHECKPOINT_INTEGRITY",
            "Healthy checkpoint SHA256 does not match the locked external artifact.",
            expected_healthy_checkpoint_sha256=EXPECTED_HEALTHY_SHA,
            actual_healthy_checkpoint_sha256=actual_healthy,
        )
    mapping = load_reviewed_mapping(
        mapping_path,
        expected_mapping_sha256=EXPECTED_MAPPING_SHA,
        expected_root_set_sha256=EXPECTED_ROOT_SHA,
    )
    connectome_root_ids = load_completeness_root_ids(completeness_path)
    torch = _load_torch()
    healthy_tensor = _checkpoint_vector(torch, healthy_checkpoint)
    presynaptic = _presynaptic_indices(connectivity_path)
    if healthy_tensor.numel() != presynaptic.size:
        raise RuntimeError(f"Checkpoint/connectome length mismatch: {healthy_tensor.numel()} != {presynaptic.size}")
    if presynaptic.size and (presynaptic.min() < 0 or presynaptic.max() >= len(connectome_root_ids)):
        raise RuntimeError("Connectome indices exceed the explicit completeness root-ID ordering.")
    healthy_numpy = healthy_tensor.numpy()
    disease_numpy = apply_parkin_transform_from_root_ids(
        healthy_numpy,
        presynaptic,
        connectome_root_ids,
        mapping.root_ids,
        strength,
    )
    identity = apply_parkin_transform_from_root_ids(
        healthy_numpy,
        presynaptic,
        connectome_root_ids,
        mapping.root_ids,
        0.0,
    )
    identity_status = "PASS" if np.array_equal(identity, healthy_numpy) else "FAIL"
    if identity_status != "PASS":
        raise RuntimeError("Parameter-zero neural identity check failed.")
    if np.array_equal(disease_numpy, healthy_numpy) and strength > 0:
        raise RuntimeError("Positive parameter did not change the target neural structure.")
    disease_path = output / "plastic_weights.pt"
    if disease_path.resolve() == healthy_checkpoint.resolve():
        raise RuntimeError("Refusing to overwrite healthy checkpoint.")
    torch.save(torch.as_tensor(disease_numpy, dtype=healthy_tensor.dtype), disease_path)
    disease_sha = sha256_file(disease_path)
    affected = int(np.count_nonzero(np.isin(presynaptic, np.asarray([connectome_root_ids.index(root) for root in mapping.root_ids], dtype=np.int64))))
    payload = {
        "schema_version": "gate24-1-parkin-neural-checkpoint-v1",
        "status": "PARKIN_DRIVER_DEFINED_NEURAL_TRANSFORM_READY",
        "transform_id": TRANSFORM_ID,
        "operation_level": "NEURAL_PRE_ACTION",
        "healthy_checkpoint": {"path": str(healthy_checkpoint.resolve()), "sha256": actual_healthy},
        "disease_checkpoint": {"path": str(disease_path.resolve()), "sha256": disease_sha},
        "mapping_sha256": mapping.mapping_sha256,
        "target_neurons_sha256": mapping.root_set_sha256,
        "target_count": mapping.count,
        "transform_source_sha256": sha256_file(ROOT / "src/drosophila_pd_neural/parkin/transform.py"),
        "parameter": strength,
        "parameter_status": "SENSITIVITY_CANDIDATE_NOT_PRIMARY_LOCK",
        "identity_test_status": identity_status,
        "affected_edge_count": affected,
        "healthy_checkpoint_modified": sha256_file(healthy_checkpoint) != actual_healthy,
        "simulation_run": False,
        "calibration_run": False,
        "holdout_validation_run": False,
        "gpu_executed": False,
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "platform_commit": PLATFORM_COMMIT,
        "reviewer_1": mapping.reviewer_1,
        "reviewer_2": mapping.reviewer_2,
        "review_date": mapping.review_date,
        "biological_equivalence": "NOT_ASSERTED",
        "data_fabricated": False,
    }
    (output / "manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (output / "status.md").write_text(
        "# Gate24.1 Parkin neural checkpoint\n\n"
        "**Status:** `PARKIN_DRIVER_DEFINED_NEURAL_TRANSFORM_READY`\n\n"
        "CPU-only materialization succeeded. The parameter is a dimensionless sensitivity candidate, not a biological percentage.\n",
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--healthy-checkpoint", type=Path, default=DEFAULT_HEALTHY)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--completeness", type=Path, default=DEFAULT_COMPLETENESS)
    parser.add_argument("--connectivity", type=Path, default=DEFAULT_CONNECTIVITY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--parameter", type=float, default=0.5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = materialize(
            healthy_checkpoint=args.healthy_checkpoint.resolve(),
            mapping_path=args.mapping.resolve(),
            completeness_path=args.completeness.resolve(),
            connectivity_path=args.connectivity.resolve(),
            output=args.output.resolve(),
            parameter=args.parameter,
        )
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        _write_blocked(args.output.resolve(), "FAILED_PREPARATION", str(exc))
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
