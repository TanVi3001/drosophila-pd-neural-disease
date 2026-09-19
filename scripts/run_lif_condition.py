#!/usr/bin/env python
"""Run one explicit Shiu-2024 Brian2 LIF condition and write a run manifest.

The upstream model remains an external dependency and is imported by file
path.  This wrapper owns the reproducibility contract that the upstream
``run_exp`` function does not provide: explicit seed, trial denominator,
dataset/ID scope, configuration, checksums, and a metrics artifact.  It does
not change the upstream model source and does not turn a computational
condition into a biological or disease claim.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from numbers import Integral
from typing import Any, Mapping, Sequence
import uuid

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_ROOT = ROOT.parent / "external" / "Drosophila_brain_model"
MANIFEST_SCHEMA = "lif-run-manifest-1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_component(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip())
    return normalized.strip("._") or "condition"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _declared_trial_count(path: Path) -> int:
    """Validate the manifest denominator used by bridge/evaluator consumers."""

    document = _load_json(path)
    if document.get("schema_version") != MANIFEST_SCHEMA:
        raise ValueError(f"Run manifest schema_version is not {MANIFEST_SCHEMA}: {path}")
    if document.get("status") != "PASS":
        raise ValueError(f"Run manifest status must be PASS: {path}")
    value = document.get("trial_count")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"Run manifest must declare a positive integer trial_count: {path}")
    return value


def _load_external_model(model_root: Path) -> Any:
    source = model_root / "model.py"
    if not source.is_file():
        raise FileNotFoundError(f"Upstream LIF model was not found: {source}")
    if str(model_root) not in sys.path:
        sys.path.insert(0, str(model_root))
    spec = importlib.util.spec_from_file_location("fly_research_upstream_lif_model", source)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load upstream LIF model: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalize_neuron_id(value: object) -> str:
    """Return an exact decimal neuron ID without passing through float."""

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
    """argparse converter that preserves long FlyWire IDs as strings."""

    return _normalize_neuron_id(value)


def _load_inventory(path: Path) -> list[str]:
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "The LIF runtime requires pandas and pyarrow in the separate neural environment."
        ) from exc
    frame = pd.read_csv(path, index_col=0)
    identifiers = [_normalize_neuron_id(value) for value in frame.index.tolist()]
    if not identifiers or len(identifiers) != len(set(identifiers)):
        raise ValueError(f"Completeness materialization must contain unique neuron IDs: {path}")
    return identifiers


def _validate_annotation(
    path: Path,
    *,
    declared_ids: Sequence[str],
    id_namespace: str,
    dataset_id: str,
) -> dict[str, Any]:
    """Validate and fingerprint the reviewed ID registry used by a run."""

    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("Annotation validation requires pandas in the neural environment.") from exc
    frame = pd.read_csv(path, dtype=str)
    required = {"neuron_id", "id_namespace", "dataset_id"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Annotation registry is missing required columns: {missing}")
    raw_identifiers = frame["neuron_id"]
    identifiers = raw_identifiers.astype(str).str.strip()
    if raw_identifiers.isna().any() or not identifiers.all() or identifiers.duplicated().any():
        raise ValueError("Annotation registry neuron_id values must be non-empty and unique")
    namespaces = {str(value).strip() for value in frame["id_namespace"].dropna().tolist()}
    datasets = {str(value).strip() for value in frame["dataset_id"].dropna().tolist()}
    if namespaces != {str(id_namespace)}:
        raise ValueError(
            f"Annotation registry id_namespace {sorted(namespaces)} does not match {id_namespace!r}"
        )
    if datasets != {str(dataset_id)}:
        raise ValueError(
            f"Annotation registry dataset_id {sorted(datasets)} does not match {dataset_id!r}"
        )
    declared = {str(value) for value in declared_ids}
    unknown = sorted(declared.difference(set(identifiers.tolist())))
    if unknown:
        raise ValueError(f"Declared input/silence/readout IDs are absent from annotation registry: {unknown}")
    return {
        "path": str(path.resolve()),
        "sha256": _sha256(path),
        "rows": int(len(frame)),
        "columns": [str(column) for column in frame.columns],
        "id_namespace": str(id_namespace),
        "dataset_id": str(dataset_id),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _set_seeds(seed: int) -> None:
    np.random.seed(seed)
    try:
        from brian2 import seed as brian_seed
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("Brian2 is required for a real LIF condition run.") from exc
    brian_seed(seed)


def _intervention(input_ids: list[str], silence_ids: list[str]) -> dict[str, Any]:
    if silence_ids and input_ids:
        intervention_type = "activation_plus_outgoing_synapse_block"
    elif silence_ids:
        intervention_type = "outgoing_synapse_block"
    elif input_ids:
        intervention_type = "activation"
    else:
        intervention_type = "none"
    return {
        "type": intervention_type,
        "input_ids": [_normalize_neuron_id(value) for value in input_ids],
        "outgoing_synapse_block_ids": [_normalize_neuron_id(value) for value in silence_ids],
        "semantic_boundary": (
            "outgoing_synapse_block zeros outgoing synaptic weights in the upstream model; "
            "it is not neuron death or biological absence."
        ),
    }


def _load_stimulus_schedule(
    raw: str | None,
    *,
    duration_s: float,
    inventory: set[str],
) -> list[dict[str, Any]]:
    """Parse a time-window stimulus protocol without implicit unit conversion.

    Each window uses seconds and Hz explicitly.  Overlapping windows are
    allowed for coactivation, but the same neuron cannot appear in two
    overlapping windows because that would make the effective rate ambiguous.
    """

    if raw is None or not str(raw).strip():
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("stimulus-schedule-json must contain valid JSON") from exc
    if not isinstance(value, list) or not value:
        raise ValueError("stimulus-schedule-json must be a non-empty list")
    schedule: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"stimulus schedule item {index} must be an object")
        missing = [key for key in ("start_s", "end_s", "rate_hz", "input_ids") if key not in item]
        if missing:
            raise ValueError(f"stimulus schedule item {index} is missing: {', '.join(missing)}")
        try:
            start = float(item["start_s"])
            end = float(item["end_s"])
            rate = float(item["rate_hz"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"stimulus schedule item {index} has non-numeric timing/rate") from exc
        if not np.isfinite(start) or not np.isfinite(end) or start < 0 or end <= start or end > duration_s:
            raise ValueError(f"stimulus schedule item {index} must satisfy 0 <= start_s < end_s <= duration_s")
        if not np.isfinite(rate) or rate < 0:
            raise ValueError(f"stimulus schedule item {index} rate_hz must be finite and non-negative")
        raw_ids = item["input_ids"]
        if not isinstance(raw_ids, Sequence) or isinstance(raw_ids, (str, bytes)) or not raw_ids:
            raise ValueError(f"stimulus schedule item {index} input_ids must be a non-empty list")
        input_ids = list(dict.fromkeys(_normalize_neuron_id(value) for value in raw_ids))
        unknown = sorted(set(input_ids).difference(inventory))
        if unknown:
            raise ValueError(f"stimulus schedule item {index} contains IDs outside the inventory: {unknown}")
        schedule.append(
            {
                "start_s": start,
                "end_s": end,
                "rate_hz": rate,
                "input_ids": input_ids,
                "label": None if item.get("label") is None else str(item["label"]),
            }
        )
    for left_index, left in enumerate(schedule):
        left_ids = set(left["input_ids"])
        for right in schedule[left_index + 1 :]:
            if float(left["end_s"]) <= float(right["start_s"]) or float(right["end_s"]) <= float(left["start_s"]):
                continue
            overlap = sorted(left_ids.intersection(right["input_ids"]))
            if overlap:
                raise ValueError(
                    "overlapping stimulus windows cannot repeat the same input IDs: "
                    + ", ".join(overlap)
                )
    return schedule


def _run_scheduled_trial(
    model: Any,
    schedule: Sequence[Mapping[str, Any]],
    silence_ids: Sequence[str],
    path_comp: Path,
    path_con: Path,
    params: Mapping[str, Any],
) -> dict[int, Any]:
    """Run a Brian2 trial with explicit time-varying Poisson input windows."""

    from brian2 import Hz, Network, PoissonGroup, Synapses, TimedArray, ms, second, start_scope

    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError("scheduled LIF runs require pandas") from exc

    start_scope()
    frame = pd.read_csv(path_comp, index_col=0)
    flyid2i = {_normalize_neuron_id(value): index for index, value in enumerate(frame.index.tolist())}
    neu, syn, spk_mon = model.create_model(path_comp, path_con, dict(params))
    syn = model.silence([flyid2i[_normalize_neuron_id(value)] for value in silence_ids], syn)
    input_objects: list[Any] = []
    duration_s = float(params["t_run"] / second)
    # The upstream model integrates at 0.05 ms; use the same grid for the
    # TimedArray so window boundaries do not introduce a second time unit.
    dt = 0.05 * ms
    sample_count = int(np.ceil(duration_s / 0.00005)) + 1
    time_values = np.arange(sample_count, dtype=float) * 0.00005
    for index, window in enumerate(schedule):
        rates = np.zeros(sample_count, dtype=float)
        active = (time_values >= float(window["start_s"])) & (time_values < float(window["end_s"]))
        rates[active] = float(window["rate_hz"])
        timed = TimedArray(rates * Hz, dt=dt, name=f"stimulus_{index}")
        source = PoissonGroup(
            len(window["input_ids"]),
            rates=f"stimulus_{index}(t)",
            namespace={f"stimulus_{index}": timed},
            name=f"scheduled_input_{index}",
        )
        target_indices = [flyid2i[_normalize_neuron_id(value)] for value in window["input_ids"]]
        # Match the upstream ``add_poisson_input`` contract: neurons receiving
        # external drive do not enter the recurrent refractory period solely
        # because they are stimulus targets.
        for target_index in target_indices:
            neu.rfc[target_index] = 0 * ms
        input_synapses = Synapses(
            source,
            neu,
            on_pre="v_post += input_weight",
            namespace={"input_weight": params["w_syn"] * params["f_poi"]},
            name=f"scheduled_synapses_{index}",
        )
        input_synapses.connect(i=np.arange(len(target_indices)), j=np.asarray(target_indices))
        input_objects.extend((source, input_synapses))
    network = Network(neu, syn, spk_mon, *input_objects)
    network.run(params["t_run"])
    return model.get_spk_trn(spk_mon)


def run_condition(args: argparse.Namespace) -> dict[str, Any]:
    if args.seed < 0:
        raise ValueError("seed must be non-negative")
    if args.trials <= 0:
        raise ValueError("trials must be positive")
    if not np.isfinite(args.duration_s) or args.duration_s <= 0:
        raise ValueError("duration-s must be finite and positive")
    if not np.isfinite(args.stimulus_rate_hz) or args.stimulus_rate_hz < 0:
        raise ValueError("stimulus-rate-hz must be finite and non-negative")

    model_root = args.model_root.resolve()
    completeness = (args.completeness or model_root / "2023_03_23_completeness_630_final.csv").resolve()
    connectivity = (args.connectivity or model_root / "2023_03_23_connectivity_630_final.parquet").resolve()
    for path in (completeness, connectivity):
        if not path.is_file():
            raise FileNotFoundError(path)
    annotation_file = args.annotation_file.resolve() if args.annotation_file is not None else None
    if annotation_file is not None and not annotation_file.is_file():
        raise FileNotFoundError(annotation_file)

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    exp_name = _safe_component(args.exp_name or args.condition_label)
    spike_path = output / f"{exp_name}.parquet"
    manifest_path = output / "run_manifest.json"
    metrics_path = output / "metrics.json"
    if not args.overwrite and any(path.exists() for path in (spike_path, manifest_path, metrics_path)):
        raise FileExistsError(
            f"Output already contains a LIF artifact; choose a new run directory or pass --overwrite: {output}"
        )

    inventory = _load_inventory(completeness)
    inventory_set = set(inventory)
    input_ids = list(dict.fromkeys(_normalize_neuron_id(value) for value in args.input_id))
    silence_ids = list(dict.fromkeys(_normalize_neuron_id(value) for value in args.silence_id))
    readout_ids = list(dict.fromkeys(_normalize_neuron_id(value) for value in args.readout_id))
    unknown_ids = sorted(set((*input_ids, *silence_ids, *readout_ids)).difference(inventory_set))
    if unknown_ids:
        raise ValueError(
            f"Input/silence/readout IDs are outside the declared completeness inventory: {unknown_ids}"
        )
    schedule_raw = args.stimulus_schedule_json
    if args.stimulus_schedule_file is not None:
        schedule_path = args.stimulus_schedule_file.resolve()
        if not schedule_path.is_file():
            raise FileNotFoundError(schedule_path)
        schedule_raw = schedule_path.read_text(encoding="utf-8")
    stimulus_schedule = _load_stimulus_schedule(
        schedule_raw,
        duration_s=float(args.duration_s),
        inventory=inventory_set,
    )
    scheduled_input_ids = list(
        dict.fromkeys(
            value
            for window in stimulus_schedule
            for value in window["input_ids"]
        )
    )
    if stimulus_schedule:
        input_ids = list(dict.fromkeys((*input_ids, *scheduled_input_ids)))
    annotation_info = None
    schedule_source = None
    if args.stimulus_schedule_file is not None:
        schedule_source = {
            "path": str(schedule_path),
            "sha256": _sha256(schedule_path),
        }
    if annotation_file is not None:
        annotation_info = _validate_annotation(
            annotation_file,
            declared_ids=(*input_ids, *silence_ids, *readout_ids),
            id_namespace=args.id_namespace,
            dataset_id=args.dataset_id,
        )

    model = _load_external_model(model_root)
    _set_seeds(args.seed)
    try:
        from brian2 import Hz, second
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("Brian2 is required for a real LIF condition run.") from exc
    params = dict(model.default_params)
    params["t_run"] = float(args.duration_s) * second
    params["n_run"] = int(args.trials)
    params["r_poi"] = float(args.stimulus_rate_hz) * Hz
    params["r_poi2"] = 0 * Hz

    config = {
        "schema_version": "lif-condition-config-1",
        "condition_label": args.condition_label,
        "exp_name": exp_name,
        "seed": int(args.seed),
        "trial_count": int(args.trials),
        "duration_s": float(args.duration_s),
        "stimulus_rate_hz": float(args.stimulus_rate_hz),
        "stimulus_schedule": stimulus_schedule,
        "stimulus_schedule_source": schedule_source,
        "input_ids": [str(value) for value in input_ids],
        "outgoing_synapse_block_ids": [str(value) for value in silence_ids],
        "readout_ids": [str(value) for value in readout_ids],
        "annotation_file": None if annotation_file is None else str(annotation_file),
        "model_root": str(model_root),
        "completeness": str(completeness),
        "connectivity": str(connectivity),
        "id_namespace": args.id_namespace,
        "dataset_id": args.dataset_id,
        "intervention": _intervention(input_ids, silence_ids),
    }
    _write_json(output / "condition_config.json", config)

    # The upstream model indexes integer IDs. Convert only at this private
    # boundary; all config, manifest, CLI and report values remain exact
    # strings so JavaScript/JSON cannot round them.  The schedule path builds
    # the same LIF network but replaces constant PoissonInput with explicit
    # TimedArray windows, leaving the upstream source untouched.
    if stimulus_schedule:
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover - runtime dependency
            raise RuntimeError("scheduled LIF runs require pandas") from exc
        frame = pd.read_csv(completeness, index_col=0)
        flyid2i = {_normalize_neuron_id(value): index for index, value in enumerate(frame.index.tolist())}
        results = [
            _run_scheduled_trial(
                model,
                stimulus_schedule,
                silence_ids,
                completeness,
                connectivity,
                params,
            )
            for _ in range(int(args.trials))
        ]
        dataframe = model.construct_dataframe(results, exp_name, {index: value for value, index in flyid2i.items()})
        dataframe.to_parquet(spike_path, compression="brotli")
    else:
        model.run_exp(
            exp_name=exp_name,
            neu_exc=[int(value) for value in input_ids],
            path_res=output,
            path_comp=completeness,
            path_con=connectivity,
            params=params,
            neu_slnc=[int(value) for value in silence_ids],
            n_proc=1,
            force_overwrite=True,
        )
    if not spike_path.is_file():
        raise RuntimeError(f"Upstream LIF runner did not create the expected spike output: {spike_path}")

    run_id = str(uuid.uuid4())
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "run_id": run_id,
        "status": "PASS",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "trial_count": int(args.trials),
        "duration_s": float(args.duration_s),
        "seed": int(args.seed),
        "id_namespace": args.id_namespace,
        "dataset_id": args.dataset_id,
        "neuron_ids": inventory,
        "readout_ids": [str(value) for value in readout_ids],
        "stimulus_schedule": stimulus_schedule,
        "stimulus_schedule_source": schedule_source,
        "condition": config,
        "spike_output": {
            "path": str(spike_path),
            "sha256": _sha256(spike_path),
            "size_bytes": spike_path.stat().st_size,
        },
        "source_provenance": {
            "model_py": {"path": str(model_root / "model.py"), "sha256": _sha256(model_root / "model.py")},
            "completeness": {"path": str(completeness), "sha256": _sha256(completeness)},
            "connectivity": {"path": str(connectivity), "sha256": _sha256(connectivity)},
            "stimulus_schedule": schedule_source,
            "upstream_repository": "https://github.com/philshiu/Drosophila_brain_model",
            "model_family": "leaky_integrate_and_fire",
        },
        "scientific_scope": (
            "New computational Brian2 LIF run using the pinned upstream model and FlyWire 630 inputs; "
            "not biological validation, disease validation, or a firing-to-behavior calibration."
        ),
    }
    if annotation_info is not None:
        manifest["source_provenance"]["annotation_registry"] = annotation_info
    _write_json(manifest_path, manifest)

    evaluator = (args.evaluator or ROOT / "scripts" / "evaluate_2024_baseline.py").resolve()
    command = [
        sys.executable,
        str(evaluator),
        "--spikes",
        str(spike_path),
        "--output",
        str(metrics_path),
        "--duration-s",
        str(args.duration_s),
        "--manifest",
        str(manifest_path),
        "--completeness",
        str(completeness),
        "--connectivity",
        str(connectivity),
    ]
    for value in input_ids:
        command.extend(("--input-id", str(value)))
    for value in readout_ids:
        command.extend(("--readout-id", str(value)))
    evaluation = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    (output / "metrics.log").write_text(
        (evaluation.stdout or "") + "\n--- STDERR ---\n" + (evaluation.stderr or ""),
        encoding="utf-8",
    )
    if evaluation.returncode != 0 or not metrics_path.is_file():
        manifest["status"] = "FAILED"
        manifest["failure"] = {
            "stage": "metrics",
            "return_code": evaluation.returncode,
            "stdout": evaluation.stdout,
            "stderr": evaluation.stderr,
        }
        _write_json(manifest_path, manifest)
        raise RuntimeError("LIF simulation completed but metrics evaluation failed; see metrics.log")

    manifest["metrics"] = {
        "path": str(metrics_path),
        "sha256": _sha256(metrics_path),
        "size_bytes": metrics_path.stat().st_size,
    }
    manifest["finished_at_utc"] = datetime.now(UTC).isoformat()
    _write_json(manifest_path, manifest)
    status = {
        "status": "PASS",
        "run_id": run_id,
        "manifest": str(manifest_path),
        "spike_output": str(spike_path),
        "metrics": str(metrics_path),
        "scientific_scope": manifest["scientific_scope"],
    }
    _write_json(output / "status.json", status)
    print(json.dumps(status, indent=2, sort_keys=True))
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--completeness", type=Path, default=None)
    parser.add_argument("--connectivity", type=Path, default=None)
    parser.add_argument("--annotation-file", type=Path, default=None)
    parser.add_argument("--evaluator", type=Path, default=None)
    parser.add_argument("--condition-label", default="condition")
    parser.add_argument("--exp-name", default=None)
    parser.add_argument("--input-id", type=_parse_neuron_id, action="append", default=[])
    parser.add_argument("--silence-id", type=_parse_neuron_id, action="append", default=[])
    parser.add_argument("--readout-id", type=_parse_neuron_id, action="append", default=[])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--duration-s", type=float, default=1.0)
    parser.add_argument("--stimulus-rate-hz", type=float, default=150.0)
    parser.add_argument(
        "--stimulus-schedule-json",
        default=None,
        help="JSON list of {start_s,end_s,rate_hz,input_ids} windows; supports coactivation.",
    )
    parser.add_argument(
        "--stimulus-schedule-file",
        type=Path,
        default=None,
        help="Path to a UTF-8 JSON list of stimulus windows; safer than shell-escaping JSON on Windows.",
    )
    parser.add_argument("--id-namespace", default="flywire_root_id")
    parser.add_argument("--dataset-id", default="flywire-630-2023-03-23")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run_condition(args)
    except (FileExistsError, FileNotFoundError, ImportError, OSError, RuntimeError, ValueError) as exc:
        args.output.mkdir(parents=True, exist_ok=True)
        _write_json(
            args.output / "status.json",
            {
                "status": "FAILED",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "scientific_scope": "No valid LIF result was produced.",
            },
        )
        print(f"LIF condition failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
