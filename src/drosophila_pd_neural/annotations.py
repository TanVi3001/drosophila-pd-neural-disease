"""Doc annotation neuron/edge voi provenance, khong doan index."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NeuronAnnotation:
    neuron_id: str
    cell_type: str
    neurotransmitter: str
    region: str
    motor_role: str
    source: str


REQUIRED_COLUMNS = (
    "neuron_id",
    "cell_type",
    "neurotransmitter",
    "region",
    "motor_role",
    "source",
)


def load_neuron_annotations(path: str | Path) -> dict[str, NeuronAnnotation]:
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != REQUIRED_COLUMNS:
            raise ValueError(
                f"Annotation schema phai la {list(REQUIRED_COLUMNS)}, nhan {reader.fieldnames}."
            )
        result: dict[str, NeuronAnnotation] = {}
        for line_number, row in enumerate(reader, start=2):
            neuron_id = (row.get("neuron_id") or "").strip()
            source = (row.get("source") or "").strip()
            if not neuron_id or not source:
                raise ValueError(f"Annotation dong {line_number} thieu neuron_id hoac source.")
            if neuron_id in result:
                raise ValueError(f"Neuron bi trung lap: {neuron_id}")
            result[neuron_id] = NeuronAnnotation(
                neuron_id=neuron_id,
                cell_type=(row.get("cell_type") or "").strip(),
                neurotransmitter=(row.get("neurotransmitter") or "").strip(),
                region=(row.get("region") or "").strip(),
                motor_role=(row.get("motor_role") or "").strip(),
                source=source,
            )
    return result
