"""Ap dung condition vao edge-list that, khong chay FlyGym.

Script dung de kiem tra buoc neural perturbation truoc khi tich hop vao brain
engine. Neu thieu annotation, connectome hoac target thi chi ghi WAITING.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.annotations import load_neuron_annotations
from drosophila_pd_neural.models import profile_from_mapping
from drosophila_pd_neural.perturbations import perturb_edges
from drosophila_pd_neural.provenance import sha256_file, write_manifest


def _write_status(output: Path, status: str, message: str, config: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    document = {"status": status, "message": message, "config": config}
    (output / "status.json").write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "status.md").write_text(f"# Neural condition\n\n**Status:** `{status}`\n\n{message}\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--age-days", type=float, required=True)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--edges", type=Path, help="CSV co cot pre_id,post_id,weight.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    config = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    profile = profile_from_mapping(config)
    condition = profile.at_age(args.age_days)
    if condition is None:
        _write_status(args.output, "WAITING_TARGET_DATA", "Chua co burden curve theo tuoi da duoc duyet.", config)
        return 0
    if args.annotations is None or not args.annotations.is_file():
        _write_status(args.output, "WAITING_ANNOTATION_DATA", "Thieu neuron annotation co provenance; khong doan index neuron.", config)
        return 0
    annotations = load_neuron_annotations(args.annotations)
    missing = sorted(set(condition.target_neurons) - set(annotations))
    if missing:
        _write_status(args.output, "INVALID_ANNOTATION", f"Neuron target chua co annotation: {missing}", config)
        return 2
    if args.edges is None or not args.edges.is_file():
        _write_status(args.output, "WAITING_BRAIN_DATA", "Thieu edge-list connectome that; khong sinh output gia.", config)
        return 0

    pre_ids: list[str] = []
    post_ids: list[str] = []
    weights: list[float] = []
    with args.edges.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != ("pre_id", "post_id", "weight"):
            raise ValueError("Edge CSV phai co cot pre_id,post_id,weight.")
        for row in reader:
            pre_ids.append(str(row["pre_id"]))
            post_ids.append(str(row["post_id"]))
            weights.append(float(row["weight"]))
    perturbed = perturb_edges(pre_ids, post_ids, weights, condition)
    args.output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output / "perturbed_edges.npz", pre_id=np.asarray(pre_ids), post_id=np.asarray(post_ids), weight=perturbed)
    input_records = [
        {"path": str(args.config), "sha256": sha256_file(args.config)},
        {"path": str(args.annotations), "sha256": sha256_file(args.annotations)},
        {"path": str(args.edges), "sha256": sha256_file(args.edges)},
    ]
    write_manifest(args.output / "manifest.json", inputs=input_records, config=condition.to_dict(), status="PERTURBATION_READY")
    _write_status(args.output, "PERTURBATION_READY", "Perturbation da duoc ap dung tren edge-list co annotation. Chua chay simulation.", condition.to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
