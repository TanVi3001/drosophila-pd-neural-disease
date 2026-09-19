"""Evaluate spike outputs from the Shiu et al. 2024 Drosophila LIF model.

This evaluator is intentionally independent from the FlyGym locomotion runtime.
It consumes the upstream model's parquet output and writes a provenance-aware
Healthy Baseline Metrics v1 artifact. It does not modify the upstream model or
interpret neural activity as a Parkinson phenotype.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from numbers import Integral
from pathlib import Path
from typing import Any, Sequence

import numpy as np

try:
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - optional brain-runtime dependency
    pd = None  # type: ignore[assignment]


REQUIRED_COLUMNS = {"t", "trial", "flywire_id", "exp_name"}


def _normalize_neuron_id(value: object) -> str:
    """Normalize IDs without accepting a lossy floating-point representation."""

    if isinstance(value, bool) or value is None:
        raise ValueError("neuron IDs must be non-empty decimal strings or integers")
    if isinstance(value, Integral):
        text = str(int(value))
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise ValueError(
            "neuron IDs must be decimal strings or integers; floating-point IDs are rejected"
        )
    if not text or not text.isdigit():
        raise ValueError(f"neuron ID must be a non-empty decimal string: {value!r}")
    return text


def _parse_neuron_id(value: str) -> str:
    return _normalize_neuron_id(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _number(value: Any) -> int | float | None:
    if value is None:
        return None
    value = float(value)
    if not np.isfinite(value):
        return None
    if value.is_integer():
        return int(value)
    return value


def _summary(values: pd.Series | np.ndarray) -> dict[str, int | float | None]:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return {"n": 0, "min": None, "max": None, "mean": None, "sd": None}
    return {
        "n": int(array.size),
        "min": _number(np.min(array)),
        "max": _number(np.max(array)),
        "mean": _number(np.mean(array)),
        "sd": _number(np.std(array, ddof=1) if array.size > 1 else 0.0),
    }


def _relative(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _read_spikes(path: Path) -> pd.DataFrame:
    if pd is None:
        raise RuntimeError(
            "pandas is required to evaluate parquet spike output; install the 'brain' extra"
        )
    frame = pd.read_parquet(path)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required spike columns: {sorted(missing)}")
    if not np.isfinite(frame["t"].to_numpy(dtype=float)).all():
        raise ValueError("Spike times contain NaN or infinity.")
    if frame["trial"].isna().any() or frame["flywire_id"].isna().any():
        raise ValueError("trial and flywire_id must not contain null values.")
    try:
        frame["flywire_id"] = frame["flywire_id"].map(_normalize_neuron_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("flywire_id values must preserve exact decimal neuron IDs") from exc
    try:
        trial_values = frame["trial"].to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("trial values must be numeric integers.") from exc
    if not np.isfinite(trial_values).all() or not np.equal(trial_values, np.floor(trial_values)).all():
        raise ValueError("trial values must be finite integers.")
    return frame


def _declared_trial_count(path: Path) -> int:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Run manifest is not valid JSON: {path}") from exc
    if not isinstance(document, dict):
        raise ValueError(f"Run manifest must be a JSON object: {path}")
    if document.get("schema_version") != "lif-run-manifest-1":
        raise ValueError(f"Run manifest schema_version is not lif-run-manifest-1: {path}")
    if document.get("status") != "PASS":
        raise ValueError(f"Run manifest status must be PASS: {path}")
    value = document.get("trial_count")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"Run manifest must declare a positive integer trial_count: {path}")
    return value


def evaluate(
    *,
    spike_path: Path,
    output_path: Path,
    duration_s: float,
    completeness_path: Path | None = None,
    connectivity_path: Path | None = None,
    input_ids: Sequence[str | int] | None = None,
    readout_ids: Sequence[str | int] | None = None,
    run_manifest_path: Path | None = None,
) -> dict[str, Any]:
    if duration_s <= 0 or not np.isfinite(duration_s):
        raise ValueError("duration_s must be finite and positive.")

    frame = _read_spikes(spike_path)
    observed_trials = sorted(frame["trial"].astype(int).unique().tolist())
    if run_manifest_path is not None:
        n_trials = _declared_trial_count(run_manifest_path)
        invalid_trials = [trial for trial in observed_trials if trial < 0 or trial >= n_trials]
        if invalid_trials:
            raise ValueError(
                f"Spike output contains trial IDs outside the declared manifest range: {invalid_trials}"
            )
        trials = list(range(n_trials))
        trial_count_source = str(run_manifest_path.resolve())
    else:
        if not observed_trials:
            raise ValueError("An empty spike output requires --manifest to declare trial_count.")
        n_trials = len(observed_trials)
        trials = observed_trials
        trial_count_source = "inferred_from_observed_spike_trials"
    trial_series = frame["trial"].astype(int)
    trial_counts = frame.groupby(trial_series).size().reindex(trials, fill_value=0)
    trial_active = frame.groupby(trial_series)["flywire_id"].nunique().reindex(trials, fill_value=0)
    # Convert identifiers to strings only at the reporting boundary. This
    # keeps long FlyWire root IDs intact and makes explicit readout lookup
    # stable across parquet writers that choose integer or string storage.
    frame_id_strings = frame["flywire_id"].astype(str)
    neuron_counts = frame_id_strings.value_counts().sort_values(ascending=False)
    neuron_rates = neuron_counts / (n_trials * duration_s)
    active_ids = sorted(str(value) for value in neuron_counts.index.tolist())
    declared_readout_ids = list(dict.fromkeys(_normalize_neuron_id(value) for value in (readout_ids or [])))
    if declared_readout_ids and completeness_path is None:
        raise ValueError(
            "a completeness inventory is required when explicit readout IDs are supplied; "
            "otherwise absent IDs cannot be distinguished from silent neurons"
        )
    inventory_ids: set[str] | None = None
    if completeness_path is not None:
        completeness = pd.read_csv(completeness_path, index_col=0)
        try:
            inventory_ids = {_normalize_neuron_id(value) for value in completeness.index.tolist()}
        except (TypeError, ValueError) as exc:
            raise ValueError("completeness inventory contains invalid neuron IDs") from exc
        unknown_readouts = sorted(set(declared_readout_ids).difference(inventory_ids))
        if unknown_readouts:
            raise ValueError(
                "declared readout IDs are absent from the completeness inventory: "
                + ", ".join(unknown_readouts)
            )
    readout_spike_counts = {
        neuron_id: int(neuron_counts.get(neuron_id, 0)) for neuron_id in declared_readout_ids
    }
    readout_rates_hz = {
        neuron_id: _number(count / (n_trials * duration_s))
        for neuron_id, count in readout_spike_counts.items()
    }

    metrics: dict[str, Any] = {
        "spike_count_total": int(len(frame)),
        "trial_count": n_trials,
        "neuron_count_in_output": int(frame["flywire_id"].nunique()),
        "experiment_names": sorted(str(value) for value in frame["exp_name"].dropna().unique()),
        "duration_s": float(duration_s),
        "time_min_s": _number(frame["t"].min()) if not frame.empty else None,
        "time_max_s": _number(frame["t"].max()) if not frame.empty else None,
        "spike_count_per_trial": _summary(trial_counts),
        "active_neurons_per_trial": _summary(trial_active),
        "firing_rate_hz_per_active_neuron": _summary(neuron_rates),
        "neurons_with_at_least_one_spike": int(len(neuron_counts)),
        "neurons_with_rate_at_least_1_hz": int((neuron_rates >= 1.0).sum()),
        "neurons_with_rate_at_least_10_hz": int((neuron_rates >= 10.0).sum()),
        "top_responders": [
            {
                "flywire_id": str(neuron_id),
                "spike_count": int(count),
                "mean_rate_hz": _number(neuron_rates.loc[neuron_id]),
            }
            for neuron_id, count in neuron_counts.head(25).items()
        ],
    }
    if declared_readout_ids:
        metrics["readout_spike_counts"] = readout_spike_counts
        metrics["readout_rates_hz"] = readout_rates_hz

    provenance: dict[str, Any] = {
        "spike_output": {
            "path": str(spike_path.resolve()),
            "sha256": _sha256(spike_path),
            "size_bytes": spike_path.stat().st_size,
            "columns": [str(column) for column in frame.columns],
            "row_count": int(len(frame)),
        },
        "model": {
            "family": "leaky_integrate_and_fire",
            "upstream_repository": "https://github.com/philshiu/Drosophila_brain_model",
            "dataset_release_used_by_run": "FlyWire release 630",
            "interpretation_boundary": "computational neural activity only",
        },
    }

    data_audit: dict[str, Any] = {
        "output_flywire_id_min": None if frame.empty else str(frame["flywire_id"].min()),
        "output_flywire_id_max": None if frame.empty else str(frame["flywire_id"].max()),
        "output_ids_are_unique_after_string_cast": len(active_ids) == len(set(active_ids)),
    }
    if input_ids:
        input_as_strings = {_normalize_neuron_id(value) for value in input_ids}
        data_audit["declared_input_ids"] = sorted(input_as_strings)
        data_audit["declared_input_ids_in_output"] = sorted(input_as_strings.intersection(active_ids))
        data_audit["declared_input_ids_missing_from_output"] = sorted(input_as_strings.difference(active_ids))
    if declared_readout_ids:
        data_audit["declared_readout_ids"] = declared_readout_ids
        data_audit["declared_readout_ids_in_output"] = sorted(
            set(declared_readout_ids).intersection(active_ids)
        )
        data_audit["declared_readout_ids_silent"] = sorted(
            set(declared_readout_ids).difference(active_ids)
        )

    if completeness_path is not None:
        completeness = pd.read_csv(completeness_path, index_col=0)
        completeness_ids = inventory_ids or set()
        data_audit["completeness"] = {
            "path": str(completeness_path.resolve()),
            "sha256": _sha256(completeness_path),
            "rows": int(len(completeness)),
            "columns": [str(column) for column in completeness.columns],
            "output_ids_present_in_completeness": int(len(set(active_ids).intersection(completeness_ids))),
            "output_ids_missing_from_completeness": int(len(set(active_ids).difference(completeness_ids))),
        }
        provenance["model"]["completeness_release"] = _relative(completeness_path, completeness_path.parent)

    if connectivity_path is not None:
        connectivity = pd.read_parquet(connectivity_path)
        data_audit["connectivity"] = {
            "path": str(connectivity_path.resolve()),
            "sha256": _sha256(connectivity_path),
            "rows": int(len(connectivity)),
            "columns": [str(column) for column in connectivity.columns],
            "unique_presynaptic_ids": int(connectivity["Presynaptic_ID"].nunique()),
            "unique_postsynaptic_ids": int(connectivity["Postsynaptic_ID"].nunique()),
            "positive_weight_rows": int((connectivity["Excitatory x Connectivity"] > 0).sum()),
            "negative_weight_rows": int((connectivity["Excitatory x Connectivity"] < 0).sum()),
        }

    report: dict[str, Any] = {
        "schema_version": "healthy-baseline-metrics-2024-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "PASS",
        "metrics": metrics,
        "data_audit": data_audit,
        "provenance": provenance,
        "trial_count_source": trial_count_source,
        "scientific_scope": (
            "This is a computational LIF baseline for spike activity. It is not "
            "a locomotion metric, Parkinson validation, or clinical result."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spikes", type=Path, required=True, help="Baseline model parquet output.")
    parser.add_argument("--output", type=Path, required=True, help="Metrics JSON output path.")
    parser.add_argument("--duration-s", type=float, default=1.0)
    parser.add_argument("--completeness", type=Path, default=None)
    parser.add_argument("--connectivity", type=Path, default=None)
    parser.add_argument("--input-id", type=_parse_neuron_id, action="append", default=[])
    parser.add_argument(
        "--readout-id",
        type=_parse_neuron_id,
        action="append",
        default=[],
        help="Explicit neuron ID(s) whose trial-normalized rate is reported.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="lif-run-manifest-1 used as the authoritative trial denominator.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = evaluate(
        spike_path=args.spikes,
        output_path=args.output,
        duration_s=args.duration_s,
        completeness_path=args.completeness,
        connectivity_path=args.connectivity,
        input_ids=args.input_id,
        readout_ids=args.readout_id,
        run_manifest_path=args.manifest,
    )
    print(json.dumps({"status": report["status"], "metrics": report["metrics"]}, indent=2))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
