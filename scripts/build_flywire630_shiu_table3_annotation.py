#!/usr/bin/env python
"""Build the source-grounded FlyWire-630 registry for the Shiu v2 cases.

This registry records the computational name-to-ID evidence used by the
Workbench.  It does not assert that a published cell-type label is a
driver-line identity or that an assay is biologically interchangeable with a
LIF firing-rate readout.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import pickle
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PICKLE = ROOT.parent / "external" / "Drosophila_brain_model" / "sez_neurons.pickle"
DEFAULT_COMPLETENESS = ROOT.parent / "external" / "Drosophila_brain_model" / "2023_03_23_completeness_630_final.csv"
DEFAULT_OUTPUT = ROOT / "annotations" / "flywire630_shiu_table3_upstream.csv"
DATASET_ID = "flywire-630-2023-03-23"
ID_NAMESPACE = "flywire_root_id"
FIELDS = (
    "neuron_id",
    "role",
    "label",
    "source_locator",
    "source_artifact",
    "id_namespace",
    "dataset_id",
    "verification_status",
    "notes",
)
READOUTS = {
    "720575940645521262": "MN9_left",
    "720575940660219265": "MN9_right",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, list[str]]:
    with path.open("rb") as handle:
        value = pickle.load(handle)
    if not isinstance(value, dict):
        raise ValueError("upstream neuron mapping must be a dictionary")
    result: dict[str, list[str]] = {}
    for label, raw_ids in value.items():
        if not isinstance(raw_ids, (list, tuple)) or not raw_ids:
            raise ValueError(f"mapping for {label!r} must be a non-empty list")
        ids = [str(raw_id).strip() for raw_id in raw_ids]
        if any(not neuron_id.isdigit() for neuron_id in ids) or len(ids) != len(set(ids)):
            raise ValueError(f"mapping for {label!r} contains invalid or duplicate IDs")
        result[str(label)] = ids
    return result


def _inventory(path: Path) -> set[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        values = {row[0].strip().strip('"') for row in reader if row and row[0].strip()}
    return values


def build(pickle_path: Path, output_path: Path, completeness_path: Path | None = None) -> int:
    mapping = _load(pickle_path)
    inventory = _inventory(completeness_path) if completeness_path is not None else None
    source_hash = _sha256(pickle_path)
    by_id: dict[str, dict[str, set[str] | str]] = {}
    for label, ids in mapping.items():
        for neuron_id in ids:
            row = by_id.setdefault(
                neuron_id,
                {
                    "role": set(),
                    "label": set(),
                    "source_locator": set(),
                    "source_artifact": set(),
                },
            )
            row["role"].add("table3_activation_input")  # type: ignore[union-attr]
            row["label"].add(label)  # type: ignore[union-attr]
            row["source_locator"].add("figures.ipynb:types_and_ids")  # type: ignore[union-attr]
            row["source_artifact"].add("sez_neurons.pickle")  # type: ignore[union-attr]
    for neuron_id, label in READOUTS.items():
        row = by_id.setdefault(
            neuron_id,
            {"role": set(), "label": set(), "source_locator": set(), "source_artifact": set()},
        )
        row["role"].add("primary_readout")  # type: ignore[union-attr]
        row["label"].add(label)  # type: ignore[union-attr]
        row["source_locator"].add("figures.ipynb:MN9_readout_definition")  # type: ignore[union-attr]
        row["source_artifact"].add("figures.ipynb")  # type: ignore[union-attr]
    if inventory is not None:
        missing = sorted(set(by_id).difference(inventory))
        if missing:
            raise ValueError(f"annotation IDs are absent from completeness inventory: {missing[:10]}")
    note = (
        f"Computational source mapping only; upstream pickle sha256={source_hash}. "
        "No driver-line, cell-identity, assay-equivalence, or biological-validation claim."
    )
    rows: list[dict[str, str]] = []
    for neuron_id in sorted(by_id, key=lambda value: int(value)):
        row = by_id[neuron_id]
        rows.append(
            {
                "neuron_id": neuron_id,
                "role": ";".join(sorted(row["role"])),  # type: ignore[arg-type]
                "label": ";".join(sorted(row["label"])),  # type: ignore[arg-type]
                "source_locator": ";".join(sorted(row["source_locator"])),  # type: ignore[arg-type]
                "source_artifact": ";".join(sorted(row["source_artifact"])),  # type: ignore[arg-type]
                "id_namespace": ID_NAMESPACE,
                "dataset_id": DATASET_ID,
                "verification_status": "SOURCE_VERIFIED_COMPUTATIONAL",
                "notes": note,
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-pickle", type=Path, default=DEFAULT_PICKLE)
    parser.add_argument("--completeness", type=Path, default=DEFAULT_COMPLETENESS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    count = build(args.upstream_pickle.resolve(), args.output.resolve(), args.completeness.resolve())
    print(f"{{\"status\": \"CREATED\", \"rows\": {count}, \"output\": \"{args.output.resolve()}\"}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
