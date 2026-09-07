"""Materialize the Riemensperger class-level neural checkpoint transform."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.riemensperger2011.dopamine_transform import apply_dopamine_class_presynaptic_transform
from drosophila_pd_neural.riemensperger2011.protocol import sha256_file, write_json
from scripts.prepare_neural_checkpoint import _checkpoint_tensor, _load_torch, _numeric_edges


def materialize(*, brain_root: Path, condition_config: Path, age_days: float, burden: float, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(condition_config.read_text(encoding="utf-8")) or {}
    target_ids = [str(value) for value in config.get("target_neurons", [])]
    if not target_ids:
        return _write_status(output, "WAITING_TARGET_DATA", "No reviewed dopamine-class target IDs are available.")
    if not brain_root.is_dir():
        return _write_status(output, "WAITING_BRAIN_DATA", f"Missing brain root: {brain_root}")
    required = (
        "data/2025_Completeness_783.csv",
        "data/2025_Connectivity_783.parquet",
        "data/plastic_weights.pt",
    )
    missing = [relative for relative in required if not (brain_root / relative).is_file()]
    if missing:
        return _write_status(output, "WAITING_BRAIN_DATA", f"Missing neural artifacts: {missing}")
    try:
        torch = _load_torch()
        edges = _numeric_edges(brain_root)
        original_path = brain_root / "data/plastic_weights.pt"
        original = _checkpoint_tensor(torch, original_path)
        if original.numel() != len(edges["Presynaptic_Index"]):
            raise RuntimeError("Checkpoint length does not match connectome edge count.")
        root_ids = edges["root_ids"]
        presynaptic_ids = root_ids[edges["Presynaptic_Index"]]
        full_gain = float((config.get("full_burden") or {}).get("presynaptic_gain", 0.15))
        modified = apply_dopamine_class_presynaptic_transform(original.numpy(), presynaptic_ids, target_ids, burden=burden, full_presynaptic_gain=full_gain)
        child_path = output / "plastic_weights.pt"
        torch.save(torch.as_tensor(modified, dtype=original.dtype), child_path)
    except (OSError, RuntimeError, ValueError, KeyError, ImportError) as exc:
        return _write_status(output, "FAILED_PREPARATION", str(exc))

    manifest = {
        "schema_version": "riemensperger-2011-dopamine-checkpoint-v1",
        "status": "CHECKPOINT_READY",
        "operator": "drosophila_pd_neural.riemensperger2011.dopamine_transform.apply_dopamine_class_presynaptic_transform",
        "burden": burden,
        "full_presynaptic_gain": full_gain,
        "age_days": age_days,
        "target_count": len(target_ids),
        "parent_healthy_checkpoint": {"path": str(original_path), "sha256": sha256_file(original_path)},
        "child_disease_checkpoint": {"path": str(child_path), "sha256": sha256_file(child_path)},
        "healthy_checkpoint_unchanged": True,
        "simulation_run": False,
        "data_fabricated": False,
    }
    write_json(output / "riemensperger_dopamine_checkpoint_manifest.json", manifest)
    return _write_status(output, "CHECKPOINT_READY", "Created from the real connectome using the Riemensperger transform module.", manifest=manifest)


def _write_status(output: Path, status: str, message: str, **extra: Any) -> dict[str, Any]:
    payload = {"status": status, "message": message, "simulation_run": False, "data_fabricated": False, **extra}
    write_json(output / "status.json", payload)
    (output / "status.md").write_text(f"# Riemensperger dopamine checkpoint\n\n**Status:** `{status}`\n\n{message}\n", encoding="utf-8")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brain-root", type=Path, required=True)
    parser.add_argument("--condition-config", type=Path, required=True)
    parser.add_argument("--age-days", type=float, default=5.0)
    parser.add_argument("--burden", type=float, default=1.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = materialize(brain_root=args.brain_root.resolve(), condition_config=args.condition_config.resolve(), age_days=args.age_days, burden=args.burden, output=args.output.resolve())
    print(result.get("status", "UNKNOWN"))
    return 0 if result.get("status") in {"CHECKPOINT_READY", "WAITING_BRAIN_DATA", "WAITING_TARGET_DATA"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
