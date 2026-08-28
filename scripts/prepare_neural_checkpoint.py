"""Tao checkpoint perturbation tu connectome that, khong chay simulation."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.annotations import load_neuron_annotations
from drosophila_pd_neural.models import profile_from_mapping
from drosophila_pd_neural.provenance import sha256_file, write_manifest


CONNECTIVITY_COLUMNS = (
    "Postsynaptic_Index",
    "Presynaptic_Index",
    "Excitatory x Connectivity",
)


def _write_status(output: Path, status: str, message: str, config: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "message": message,
        "config": config,
        "simulation_run": False,
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    (output / "status.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "status.md").write_text(
        f"# Chuan bi checkpoint neural\n\n**Trang thai:** `{status}`\n\n{message}\n",
        encoding="utf-8",
    )


def _load_torch():
    try:
        import torch
    except (ImportError, OSError) as exc:
        raise RuntimeError("Thieu PyTorch; cai PyTorch CUDA trong moi truong chay brain.") from exc
    return torch


def _load_pandas():
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("Thieu pandas/pyarrow; khong doc duoc connectome Parquet.") from exc
    return pd


def _checkpoint_tensor(torch: Any, path: Path):
    try:
        loaded = torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        loaded = torch.load(path, map_location="cpu")
    if isinstance(loaded, dict):
        for key in ("weights", "weight", "values", "synaptic_weights"):
            if key in loaded:
                loaded = loaded[key]
                break
    if not isinstance(loaded, torch.Tensor):
        raise RuntimeError("Checkpoint phai la Tensor hoac mapping chua Tensor weights.")
    if loaded.layout != torch.strided:
        loaded = loaded.values()
    if loaded.ndim != 1:
        raise RuntimeError(f"Checkpoint phai la vector 1 chieu, nhan shape={tuple(loaded.shape)}.")
    if not bool(torch.isfinite(loaded).all()):
        raise RuntimeError("Checkpoint chua NaN hoac Inf.")
    return loaded.detach().cpu()


def _numeric_edges(brain_root: Path):
    pd = _load_pandas()
    connectivity_path = brain_root / "data/2025_Connectivity_783.parquet"
    completeness_path = brain_root / "data/2025_Completeness_783.csv"
    frame = pd.read_parquet(connectivity_path, columns=list(CONNECTIVITY_COLUMNS))
    missing = [column for column in CONNECTIVITY_COLUMNS if column not in frame.columns]
    if missing:
        raise RuntimeError(f"Connectome thieu cot: {missing}")
    complete = pd.read_csv(completeness_path, index_col=0)
    root_ids = np.asarray([str(value) for value in complete.index], dtype=object)
    result: dict[str, np.ndarray] = {}
    for column in CONNECTIVITY_COLUMNS[:2]:
        values = pd.to_numeric(frame[column], errors="coerce").to_numpy()
        if not np.isfinite(values).all() or not np.equal(values, values.astype(np.int64)).all():
            raise RuntimeError(f"Chi so {column} khong phai so nguyen huu han.")
        indices = values.astype(np.int64)
        if indices.size and (indices.min() < 0 or indices.max() >= root_ids.size):
            raise RuntimeError(f"Chi so {column} vuot pham vi completeness.")
        result[column] = indices
    weights = pd.to_numeric(frame[CONNECTIVITY_COLUMNS[2]], errors="coerce").to_numpy(dtype=np.float32)
    if not np.isfinite(weights).all():
        raise RuntimeError("Connectome chua NaN hoac Inf trong cot trong so.")
    result[CONNECTIVITY_COLUMNS[2]] = weights
    result["root_ids"] = root_ids
    return result


def _perturb_numeric(
    edges: dict[str, np.ndarray], condition, base_weights: np.ndarray
) -> np.ndarray:
    params = condition.parameters
    root_ids = edges["root_ids"]
    target_index = {value: index for index, value in enumerate(root_ids.tolist())}
    missing = sorted(set(condition.target_neurons) - set(target_index))
    if missing:
        raise RuntimeError(f"Target neuron khong co trong completeness: {missing}")
    targets = np.asarray([target_index[value] for value in condition.target_neurons], dtype=np.int64)
    pre = edges["Presynaptic_Index"]
    post = edges["Postsynaptic_Index"]
    factor = np.ones(pre.shape, dtype=np.float32)
    pre_target = np.isin(pre, targets)
    post_target = np.isin(post, targets)
    factor[pre_target] *= np.float32(params.presynaptic_gain)
    factor[post_target] *= np.float32(params.postsynaptic_gain)
    factor[pre_target | post_target] *= np.float32(params.neuron_survival)
    if condition.target_edges:
        encoded = pre.astype(np.int64) * np.int64(root_ids.size) + post.astype(np.int64)
        try:
            target_pairs = np.asarray(
                [
                    target_index[pre_id] * root_ids.size + target_index[post_id]
                    for pre_id, post_id in condition.target_edges
                ],
                dtype=np.int64,
            )
        except KeyError as exc:
            raise RuntimeError(
                f"Target edge chua co neuron trong completeness: {exc.args[0]}"
            ) from exc
        factor[np.isin(encoded, target_pairs)] *= np.float32(params.presynaptic_gain)
    result = np.asarray(base_weights, dtype=np.float32).copy()
    if result.ndim != 1 or result.shape != factor.shape:
        raise RuntimeError(
            "Checkpoint khong khop shape cua connectome: "
            f"{result.shape} != {factor.shape}."
        )
    result *= factor
    if not np.isfinite(result).all():
        raise RuntimeError("Perturbation tao ra weight khong huu han.")
    return result


def prepare_checkpoint(
    *,
    brain_root: Path,
    config_path: Path,
    age_days: float,
    annotations_path: Path,
    output: Path,
) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    profile = profile_from_mapping(config)
    condition = profile.at_age(age_days)
    if condition is None:
        _write_status(output, "WAITING_TARGET_DATA", "Chua co burden curve theo tuoi da duoc review.", config)
        return {"status": "WAITING_TARGET_DATA"}
    annotations = load_neuron_annotations(annotations_path)
    missing = sorted(set(condition.target_neurons) - set(annotations))
    if missing:
        _write_status(output, "WAITING_ANNOTATION_DATA", f"Thieu annotation cho target: {missing}", config)
        return {"status": "WAITING_ANNOTATION_DATA"}
    for required in (
        "brain_body_bridge.py",
        "code/run_pytorch.py",
        "data/2025_Completeness_783.csv",
        "data/2025_Connectivity_783.parquet",
        "data/plastic_weights.pt",
    ):
        if not (brain_root / required).is_file():
            _write_status(output, "WAITING_BRAIN_DATA", f"Thieu file neural: {required}", config)
            return {"status": "WAITING_BRAIN_DATA"}
    torch = _load_torch()
    edges = _numeric_edges(brain_root)
    checkpoint_path = brain_root / "data/plastic_weights.pt"
    original = _checkpoint_tensor(torch, checkpoint_path)
    if original.numel() != len(edges["Excitatory x Connectivity"]):
        raise RuntimeError(
            "So luong checkpoint khong khop so dong connectome: "
            f"{original.numel()} != {len(edges['Excitatory x Connectivity'])}."
        )
    modified = _perturb_numeric(edges, condition, original.numpy())
    output.mkdir(parents=True, exist_ok=True)
    target_checkpoint = output / "plastic_weights.pt"
    torch.save(torch.as_tensor(modified, dtype=original.dtype), target_checkpoint)
    result_config = condition.to_dict()
    inputs = [
        {"path": str(config_path), "sha256": sha256_file(config_path)},
        {"path": str(annotations_path), "sha256": sha256_file(annotations_path)},
        {"path": str(checkpoint_path), "sha256": sha256_file(checkpoint_path)},
        {"path": str(brain_root / "data/2025_Connectivity_783.parquet"), "sha256": sha256_file(brain_root / "data/2025_Connectivity_783.parquet")},
        {"path": str(brain_root / "data/2025_Completeness_783.csv"), "sha256": sha256_file(brain_root / "data/2025_Completeness_783.csv")},
    ]
    write_manifest(output / "manifest.json", inputs=inputs, config=result_config, status="CHECKPOINT_READY")
    _write_status(output, "CHECKPOINT_READY", "Da tao checkpoint tu connectome that; chua chay simulation.", result_config)
    return {"status": "CHECKPOINT_READY", "checkpoint": str(target_checkpoint)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brain-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--age-days", type=float, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare_checkpoint(
            brain_root=args.brain_root.resolve(),
            config_path=args.config.resolve(),
            age_days=args.age_days,
            annotations_path=args.annotations.resolve(),
            output=args.output.resolve(),
        )
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        _write_status(args.output.resolve(), "FAILED_PREPARATION", str(exc), {})
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
