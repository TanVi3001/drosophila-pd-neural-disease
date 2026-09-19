"""Build a reproducible LIF-to-FlyGym bridge artifact.

The 2024 Brian2 model and the FlyGym platform use different state spaces.  This
module intentionally implements only the narrow, auditable conversion between
them: annotated descending-neuron population rates become non-negative action
and coupling scales.  It does not claim that a spike-rate ratio is a validated
biological motor command.

Parquet support is imported lazily so the core package remains usable without
the optional ``brain`` dependencies.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "lif-to-flygym-bridge-scales-2"
RUN_MANIFEST_SCHEMA_VERSION = "lif-run-manifest-1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_annotations(path: str | Path) -> list[dict[str, str]]:
    """Load the reviewed neuron-role CSV without silently dropping malformed rows."""

    csv_path = Path(path)
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"neuron_id", "motor_role"}
    if not rows or not required.issubset(set(rows[0])):
        raise ValueError(f"Annotation CSV must contain {sorted(required)}: {csv_path}")
    ids: set[str] = set()
    for row in rows:
        neuron_id = row.get("neuron_id")
        if not isinstance(neuron_id, str) or not neuron_id:
            raise ValueError(f"Annotation CSV contains an empty neuron_id: {csv_path}")
        if neuron_id in ids:
            raise ValueError(f"Annotation CSV contains duplicate neuron_id {neuron_id!r}: {csv_path}")
        ids.add(neuron_id)
        if not isinstance(row.get("motor_role"), str) or not row["motor_role"].strip():
            raise ValueError(f"Annotation CSV contains an empty motor_role: {csv_path}")
    return rows


def _read_spikes(path: Path):
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise RuntimeError(
            "Reading Brian2 parquet requires the optional brain dependencies "
            "(pandas and pyarrow)."
        ) from exc
    frame = pd.read_parquet(path)
    required = {"flywire_id", "trial"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Spike parquet is missing columns {sorted(missing)}: {path}")
    frame = frame.copy()
    series = frame["flywire_id"]
    if bool(series.isna().any()):
        raise ValueError(f"Spike parquet contains null flywire_id values: {path}")
    if getattr(series.dtype, "kind", "") == "f":
        raise ValueError(
            "Spike parquet flywire_id must not use floating-point storage; "
            "floating-point conversion can lose identifier precision"
        )
    frame["flywire_id"] = series.map(str)
    return frame


def _read_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Run manifest is not valid JSON: {manifest_path}") from exc
    if not isinstance(document, dict):
        raise ValueError(f"Run manifest must be a JSON object: {manifest_path}")
    if document.get("schema_version") != RUN_MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"Run manifest schema_version must be {RUN_MANIFEST_SCHEMA_VERSION!r}: "
            f"{manifest_path}"
        )
    return document


def load_declared_trial_count(path: str | Path) -> int:
    """Load the completed trial count from a run manifest.

    The count is deliberately not inferred from a spike table: a completely
    silent trial has no rows and would otherwise disappear from the sample
    denominator.  The v0.1 manifest contract keeps the field at the top level
    so it cannot be confused with an observed-trial count.
    """

    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    document = _read_manifest(manifest_path)
    if document.get("status") != "PASS":
        raise ValueError(f"Run manifest status must be PASS: {manifest_path}")
    value = document.get("trial_count")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(
            f"Run manifest must declare a positive integer trial_count: {manifest_path}"
        )
    return value


def load_declared_id_scope(path: str | Path) -> dict[str, Any] | None:
    """Load the optional dataset/namespace inventory for spike IDs.

    Older manifests may omit this field.  Returning ``None`` is intentional:
    callers must report the resulting scope gap instead of treating unknown
    IDs as silent neurons.
    """

    document = _read_manifest(path)
    raw_ids = document.get("neuron_ids")
    raw_namespace = document.get("id_namespace")
    raw_dataset = document.get("dataset_id")
    if raw_ids is None and raw_namespace is None and raw_dataset is None:
        return None
    if not isinstance(raw_namespace, str) or not raw_namespace.strip():
        raise ValueError(f"Run manifest must declare non-empty id_namespace: {path}")
    if not isinstance(raw_ids, list) or not raw_ids:
        raise ValueError(f"Run manifest must declare non-empty neuron_ids inventory: {path}")
    ids = [str(value) for value in raw_ids]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Run manifest neuron_ids inventory contains duplicates: {path}")
    if raw_dataset is not None and (not isinstance(raw_dataset, str) or not raw_dataset.strip()):
        raise ValueError(f"Run manifest dataset_id must be a non-empty string when present: {path}")
    return {
        "id_namespace": raw_namespace.strip(),
        "dataset_id": raw_dataset.strip() if isinstance(raw_dataset, str) else None,
        "neuron_ids": ids,
        "source": str(Path(path).resolve()),
    }


def _validate_id_scope(
    rows: list[dict[str, str]],
    reference: Any,
    condition: Any,
    reference_scope: Mapping[str, Any] | None,
    condition_scope: Mapping[str, Any] | None,
) -> tuple[list[str], dict[str, Any]]:
    """Reject namespace/inventory mismatches while preserving silent neurons."""

    if (reference_scope is None) != (condition_scope is None):
        raise ValueError("reference and condition manifests must both declare id scope or both omit it")
    if reference_scope is None or condition_scope is None:
        return ["id_scope_not_declared"], {"status": "NOT_DECLARED"}
    for key in ("id_namespace", "dataset_id"):
        if reference_scope.get(key) != condition_scope.get(key):
            raise ValueError(f"reference and condition {key} do not match")
    inventory = set(reference_scope["neuron_ids"])
    if set(condition_scope["neuron_ids"]) != inventory:
        raise ValueError("reference and condition neuron_ids inventories do not match")

    annotation_namespaces = {str(row.get("id_namespace", "")).strip() for row in rows}
    if annotation_namespaces == {""}:
        raise ValueError("annotation CSV must declare id_namespace when manifests declare id scope")
    if annotation_namespaces != {str(reference_scope["id_namespace"])}:
        raise ValueError("annotation id_namespace does not match the run manifest")
    manifest_dataset = reference_scope.get("dataset_id")
    if manifest_dataset is not None:
        annotation_datasets = {str(row.get("dataset_id", "")).strip() for row in rows}
        if annotation_datasets != {str(manifest_dataset)}:
            raise ValueError("annotation dataset_id does not match the run manifest")

    annotation_ids = {str(row["neuron_id"]) for row in rows}
    unknown_annotations = sorted(annotation_ids - inventory)
    if unknown_annotations:
        raise ValueError(f"annotation neuron IDs are outside the declared inventory: {unknown_annotations}")
    for label, frame in (("reference", reference), ("condition", condition)):
        observed_ids = {str(value) for value in frame["flywire_id"].tolist()}
        unknown_spikes = sorted(observed_ids - inventory)
        if unknown_spikes:
            raise ValueError(f"{label} spike IDs are outside the declared inventory: {unknown_spikes}")
    return [], {
        "status": "PASS",
        "id_namespace": reference_scope["id_namespace"],
        "dataset_id": reference_scope.get("dataset_id"),
        "neuron_count": len(inventory),
    }


def _rates_for_ids(
    frame: Any,
    ids: Iterable[str],
    duration_s: float,
    trial_count: int,
) -> dict[str, float]:
    ids = [str(value) for value in ids]
    counts = frame.groupby("flywire_id").size().to_dict()
    denominator = float(trial_count) * float(duration_s)
    return {neuron_id: float(counts.get(neuron_id, 0)) / denominator for neuron_id in ids}


def _group(rows: list[dict[str, str]], role: str) -> list[str]:
    return [str(row["neuron_id"]) for row in rows if row.get("motor_role", "").strip() == role]


def _mean(rates: Mapping[str, float]) -> float:
    if not rates:
        return 0.0
    return sum(float(value) for value in rates.values()) / len(rates)


def build_bridge_scales(
    *,
    reference_spikes: str | Path,
    condition_spikes: str | Path,
    annotations: str | Path,
    model: str,
    reference_manifest: str | Path,
    condition_manifest: str | Path,
    duration_s: float = 1.0,
    allow_missing_turn: bool = False,
    condition_label: str = "condition",
) -> dict[str, Any]:
    """Convert two Brian2 spike tables into a FlyGym bridge artifact.

    ``reference_spikes`` and ``condition_spikes`` must be comparable runs with
    the same duration convention.  Turn coupling is left at 1.0 when either
    turn population has no observed spikes only when ``allow_missing_turn`` is
    explicitly set; the gap is then recorded in the artifact.
    """

    reference_path = Path(reference_spikes)
    condition_path = Path(condition_spikes)
    annotation_path = Path(annotations)
    reference_manifest_path = Path(reference_manifest)
    condition_manifest_path = Path(condition_manifest)
    duration_value = float(duration_s)
    if not math.isfinite(duration_value) or duration_value <= 0:
        raise ValueError("duration_s must be a finite positive number")
    for path in (
        reference_path,
        condition_path,
        annotation_path,
        reference_manifest_path,
        condition_manifest_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    reference_trial_count = load_declared_trial_count(reference_manifest_path)
    condition_trial_count = load_declared_trial_count(condition_manifest_path)
    reference_scope = load_declared_id_scope(reference_manifest_path)
    condition_scope = load_declared_id_scope(condition_manifest_path)
    rows = load_annotations(annotation_path)
    reference = _read_spikes(reference_path)
    condition = _read_spikes(condition_path)
    id_scope_warnings, id_scope_summary = _validate_id_scope(
        rows,
        reference,
        condition,
        reference_scope,
        condition_scope,
    )

    role_names = {
        "forward": "forward locomotion",
        "left_turn": "left turning",
        "right_turn": "right turning",
    }
    groups = {name: _group(rows, role) for name, role in role_names.items()}
    reference_rates = {
        name: _rates_for_ids(reference, ids, duration_value, reference_trial_count)
        for name, ids in groups.items()
    }
    condition_rates = {
        name: _rates_for_ids(condition, ids, duration_value, condition_trial_count)
        for name, ids in groups.items()
    }
    reference_means = {name: _mean(values) for name, values in reference_rates.items()}
    condition_means = {name: _mean(values) for name, values in condition_rates.items()}

    warnings: list[str] = list(id_scope_warnings)
    reference_forward = reference_means["forward"]
    if reference_forward <= 0:
        raise ValueError(
            "Reference forward readout is zero; cannot derive a motor scale. "
            "Choose a stimulus that activates a reviewed forward DN group."
        )
    motor_scale = condition_means["forward"] / reference_forward
    if condition_means["forward"] <= 0:
        warnings.append(
            "forward: condition readout is zero; motor_scale=0.0 is a sparse-readout "
            "proxy and should not be interpreted as complete motor silencing"
        )

    turn_scales: list[float] = []
    for name in ("left_turn", "right_turn"):
        ref_rate = reference_means[name]
        cond_rate = condition_means[name]
        if ref_rate > 0:
            turn_scales.append(cond_rate / ref_rate)
        elif allow_missing_turn:
            warnings.append(f"{name}: reference readout is zero; coupling contribution omitted")
        else:
            raise ValueError(
                f"{name} reference readout is zero; pass allow_missing_turn=True only "
                "when the missing readout is an explicit documented limitation."
            )
    coupling_scale = sum(turn_scales) / len(turn_scales) if turn_scales else 1.0
    if not turn_scales:
        warnings.append("No valid bilateral turn ratio; coupling_scale fixed at 1.0")

    status = "PASS_WITH_READOUT_GAPS" if warnings else "PASS"
    group_summary: dict[str, Any] = {}
    for name, role in role_names.items():
        group_summary[name] = {
            "motor_role": role,
            "neuron_ids": groups[name],
            "reference_rate_hz": reference_means[name],
            "condition_rate_hz": condition_means[name],
            "reference_per_neuron_rate_hz": reference_rates[name],
            "condition_per_neuron_rate_hz": condition_rates[name],
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "model": str(model),
        "motor_scale": float(motor_scale),
        "left_motor_scale": float(motor_scale),
        "right_motor_scale": float(motor_scale),
        "coupling_scale": float(coupling_scale),
        "biological_mechanism": {
            "type": "computational_readout_ratio",
            "condition": condition_label,
            "source_model": "Shiu et al. 2024 Brian2 LIF baseline",
            "target_platform": "FlyGym native locomotion runner",
            "validated_biologically": False,
        },
        "readout_summary": {
            "duration_s": duration_value,
            "reference_trial_count": reference_trial_count,
            "condition_trial_count": condition_trial_count,
            "id_scope": id_scope_summary,
            "trial_count_source": {
                "reference": str(reference_manifest_path.resolve()),
                "condition": str(condition_manifest_path.resolve()),
            },
            "groups": group_summary,
            "warnings": warnings,
        },
        "provenance": {
            "reference_spikes": str(reference_path.resolve()),
            "condition_spikes": str(condition_path.resolve()),
            "annotations": str(annotation_path.resolve()),
            "reference_manifest": str(reference_manifest_path.resolve()),
            "condition_manifest": str(condition_manifest_path.resolve()),
            "id_scope": id_scope_summary,
            "sha256": {
                "reference_spikes": _sha256(reference_path),
                "condition_spikes": _sha256(condition_path),
                "annotations": _sha256(annotation_path),
                "reference_manifest": _sha256(reference_manifest_path),
                "condition_manifest": _sha256(condition_manifest_path),
            },
        },
        "scientific_scope": (
            "Computational bridge only: rate ratios are a proxy for FlyGym action "
            "and CPG scales; no biological efficacy or disease claim is implied."
        ),
    }


def write_bridge_scales(data: Mapping[str, Any], output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(data), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


__all__ = [
    "RUN_MANIFEST_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "build_bridge_scales",
    "load_annotations",
    "load_declared_id_scope",
    "load_declared_trial_count",
    "write_bridge_scales",
]
