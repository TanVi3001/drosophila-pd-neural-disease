"""Build a reproducible chart/report bundle from an original FlyWire LIF run.

This script consumes an already materialized output from the upstream
``philshiu/Drosophila_brain_model`` repository.  It does not rerun or modify
the upstream model.  The generated bundle is intended as a computational
reference baseline for the Workbench benchmark.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Sequence

import numpy as np
import pandas as pd

from evaluate_2024_baseline import evaluate


REQUIRED_COLUMNS = {"t", "trial", "flywire_id", "exp_name"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_dump(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _upstream_commit(model_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(model_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _load_frame(spike_path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(spike_path)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required spike columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("The spike output is empty.")
    frame = frame.copy()
    frame["flywire_id"] = frame["flywire_id"].astype(str)
    frame["trial"] = frame["trial"].astype(int)
    frame["t"] = frame["t"].astype(float)
    if not np.isfinite(frame["t"].to_numpy()).all():
        raise ValueError("Spike times contain NaN or infinity.")
    return frame


def _write_tables(
    frame: pd.DataFrame,
    tables_dir: Path,
    *,
    duration_s: float,
    input_ids: Sequence[str],
    readout_ids: Sequence[str],
) -> dict[str, Any]:
    tables_dir.mkdir(parents=True, exist_ok=True)
    trial_counts = frame.groupby("trial").size().rename("spike_count")
    trial_active = frame.groupby("trial")["flywire_id"].nunique().rename("active_neurons")
    trial_table = pd.concat([trial_counts, trial_active], axis=1).reset_index()
    trial_table["duration_s"] = float(duration_s)
    trial_table["spike_rate_hz"] = trial_table["spike_count"] / duration_s
    trial_table.to_csv(tables_dir / "per_trial_metrics.csv", index=False)

    neuron_counts = frame["flywire_id"].value_counts().rename("spike_count")
    neuron_table = neuron_counts.to_frame().reset_index(names="flywire_id")
    neuron_table["trial_count_with_spike"] = (
        frame.groupby("flywire_id")["trial"].nunique().reindex(neuron_table["flywire_id"]).to_numpy()
    )
    neuron_table["mean_rate_hz"] = neuron_table["spike_count"] / (
        frame["trial"].nunique() * duration_s
    )
    neuron_table.to_csv(tables_dir / "per_neuron_rates.csv", index=False)

    declared = list(dict.fromkeys([*input_ids, *readout_ids]))
    declared_table = pd.DataFrame({"flywire_id": declared})
    rates = neuron_table.set_index("flywire_id")["mean_rate_hz"]
    counts = neuron_table.set_index("flywire_id")["spike_count"]
    declared_table["spike_count"] = declared_table["flywire_id"].map(counts).fillna(0).astype(int)
    declared_table["mean_rate_hz"] = declared_table["flywire_id"].map(rates).fillna(0.0)
    declared_table["role"] = declared_table["flywire_id"].map(
        lambda value: "readout" if value in readout_ids else "input"
    )
    declared_table.to_csv(tables_dir / "declared_input_readout_rates.csv", index=False)

    return {
        "per_trial_metrics": str((tables_dir / "per_trial_metrics.csv").resolve()),
        "per_neuron_rates": str((tables_dir / "per_neuron_rates.csv").resolve()),
        "declared_input_readout_rates": str(
            (tables_dir / "declared_input_readout_rates.csv").resolve()
        ),
    }


def _build_figures(
    frame: pd.DataFrame,
    figures_dir: Path,
    *,
    duration_s: float,
    input_ids: Sequence[str],
    readout_ids: Sequence[str],
) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures_dir.mkdir(parents=True, exist_ok=True)
    trial_counts = frame.groupby("trial").size()
    trial_active = frame.groupby("trial")["flywire_id"].nunique()
    neuron_counts = frame["flywire_id"].value_counts()
    rates = neuron_counts / (frame["trial"].nunique() * duration_s)
    top_ids = rates.head(20).index.tolist()

    figure, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    axes[0, 0].plot(trial_counts.index, trial_counts.values, marker="o", color="#1769aa")
    axes[0, 0].set_title("Spikes per trial")
    axes[0, 0].set_xlabel("Trial")
    axes[0, 0].set_ylabel("Spike count")
    axes[0, 1].plot(trial_active.index, trial_active.values, marker="o", color="#2e8b57")
    axes[0, 1].set_title("Active neurons per trial")
    axes[0, 1].set_xlabel("Trial")
    axes[0, 1].set_ylabel("Unique neurons")
    axes[1, 0].hist(rates.values, bins=30, color="#8c6bb1", edgecolor="white")
    axes[1, 0].set_title("Distribution of mean firing rates")
    axes[1, 0].set_xlabel("Mean firing rate (Hz)")
    axes[1, 0].set_ylabel("Neuron count")
    axes[1, 1].barh(range(len(top_ids))[::-1], rates.loc[top_ids].values, color="#d95f02")
    axes[1, 1].set_yticks(range(len(top_ids))[::-1], [str(value)[-8:] for value in top_ids])
    axes[1, 1].set_title("Top 20 responders")
    axes[1, 1].set_xlabel("Mean firing rate (Hz)")
    figure.suptitle("Original FlyWire-630 LIF baseline activity")
    overview_path = figures_dir / "brain_activity_overview.png"
    figure.savefig(overview_path, dpi=180)
    plt.close(figure)

    raster_ids = set(top_ids[:50])
    raster = frame[frame["flywire_id"].isin(raster_ids)].copy()
    order = {neuron_id: index for index, neuron_id in enumerate(top_ids[:50])}
    raster["neuron_rank"] = raster["flywire_id"].map(order)
    figure, axis = plt.subplots(figsize=(12, 6), constrained_layout=True)
    axis.scatter(raster["t"], raster["neuron_rank"], s=2, alpha=0.35, color="#1769aa")
    axis.set_title("Spike raster for the 50 highest-rate neurons")
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Neuron rank by mean rate")
    axis.set_xlim(0, max(duration_s, float(frame["t"].max())))
    raster_path = figures_dir / "spike_raster_top50.png"
    figure.savefig(raster_path, dpi=180)
    plt.close(figure)

    declared = list(dict.fromkeys([*input_ids, *readout_ids]))
    declared_rates = rates.reindex(declared, fill_value=0.0)
    labels = [f"{value[-8:]} ({'readout' if value in readout_ids else 'input'})" for value in declared]
    figure, axis = plt.subplots(figsize=(12, 5), constrained_layout=True)
    axis.bar(range(len(declared)), declared_rates.values, color=[
        "#d95f02" if value in readout_ids else "#2e8b57" for value in declared
    ])
    axis.set_xticks(range(len(declared)), labels, rotation=75, ha="right")
    axis.set_title("Declared input and readout firing rates")
    axis.set_ylabel("Mean firing rate (Hz)")
    input_readout_path = figures_dir / "declared_input_readout_rates.png"
    figure.savefig(input_readout_path, dpi=180)
    plt.close(figure)

    return [str(path.resolve()) for path in (overview_path, raster_path, input_readout_path)]


def _build_gif(frame: pd.DataFrame, output_path: Path, *, duration_s: float) -> str | None:
    """Create a small neural raster animation when Pillow is available."""

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.animation import FuncAnimation, PillowWriter
    except (ImportError, RuntimeError):
        return None

    neuron_counts = frame["flywire_id"].value_counts()
    top_ids = neuron_counts.head(50).index.tolist()
    selected = frame[frame["flywire_id"].isin(top_ids)].copy()
    order = {neuron_id: index for index, neuron_id in enumerate(top_ids)}
    selected["neuron_rank"] = selected["flywire_id"].map(order)
    bins = np.linspace(0.0, max(duration_s, float(frame["t"].max())), 31)
    figure, axis = plt.subplots(figsize=(8, 5), constrained_layout=True)
    axis.set_xlim(0.0, bins[-1])
    axis.set_ylim(-1, len(top_ids))
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Top-rate neuron rank")
    axis.set_title("Original FlyWire LIF activity")
    points = axis.scatter([], [], s=8, color="#1769aa")

    def update(index: int):
        cutoff = bins[index + 1]
        window = selected[selected["t"] <= cutoff]
        points.set_offsets(window[["t", "neuron_rank"]].to_numpy())
        axis.set_title(f"Original FlyWire LIF activity — t ≤ {cutoff:.2f} s")
        return (points,)

    animation = FuncAnimation(figure, update, frames=len(bins) - 1, interval=120, blit=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        animation.save(output_path, writer=PillowWriter(fps=8))
    except (OSError, RuntimeError):
        plt.close(figure)
        return None
    plt.close(figure)
    return str(output_path.resolve())


def build_artifact(
    *,
    spike_path: Path,
    output_root: Path,
    model_root: Path,
    duration_s: float,
    completeness_path: Path | None,
    connectivity_path: Path | None,
    input_ids: Sequence[str],
    readout_ids: Sequence[str],
    activation_hz: float,
) -> dict[str, Any]:
    spike_path = spike_path.resolve()
    output_root = output_root.resolve()
    frame = _load_frame(spike_path)
    metrics_path = output_root / "metrics" / "flywire_lif_metrics.json"
    report = evaluate(
        spike_path=spike_path,
        output_path=metrics_path,
        duration_s=duration_s,
        completeness_path=completeness_path.resolve() if completeness_path else None,
        connectivity_path=connectivity_path.resolve() if connectivity_path else None,
        input_ids=input_ids,
        readout_ids=readout_ids,
    )
    tables = _write_tables(
        frame,
        output_root / "tables",
        duration_s=duration_s,
        input_ids=input_ids,
        readout_ids=readout_ids,
    )
    figures = _build_figures(
        frame,
        output_root / "figures",
        duration_s=duration_s,
        input_ids=input_ids,
        readout_ids=readout_ids,
    )
    animation = _build_gif(frame, output_root / "video" / "neural_activity_raster.gif", duration_s=duration_s)

    source = {
        "upstream_repository": "https://github.com/philshiu/Drosophila_brain_model",
        "upstream_commit": _upstream_commit(model_root.resolve()),
        "model_root": str(model_root.resolve()),
        "spike_output": str(spike_path),
        "spike_output_sha256": _sha256(spike_path),
        "dataset_release": "FlyWire release 630",
        "activation_hz": activation_hz,
        "duration_s": duration_s,
        "trial_count": int(frame["trial"].nunique()),
    }
    if completeness_path:
        source["completeness_630"] = {
            "path": str(completeness_path.resolve()),
            "sha256": _sha256(completeness_path.resolve()),
        }
    if connectivity_path:
        source["connectivity_630"] = {
            "path": str(connectivity_path.resolve()),
            "sha256": _sha256(connectivity_path.resolve()),
        }

    generated = {
        "metrics_json": str(metrics_path.resolve()),
        "tables": tables,
        "figures": figures,
        "neural_activity_animation": animation,
    }
    manifest = {
        "schema_version": "flywire-original-baseline-artifact-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "PASS",
        "source": source,
        "declared_input_ids": list(input_ids),
        "declared_readout_ids": list(readout_ids),
        "generated": generated,
        "metrics_snapshot": report["metrics"],
        "scientific_scope": (
            "Original Shiu et al. 2024 Brian2 LIF computational neural baseline. "
            "The charts describe model spike activity only; they are not biological "
            "validation, locomotion metrics, or clinical evidence."
        ),
        "video_note": (
            "The GIF is a visualization of the recorded neural spike output, not a "
            "new model simulation and not a body-locomotion video."
        ),
    }
    _json_dump(output_root / "manifests" / "baseline_manifest.json", manifest)
    readme = "\n".join(
        [
            "# Original FlyWire-630 LIF baseline artifact",
            "",
            "This folder records the original Shiu et al. 2024 Drosophila LIF run used as a computational reference.",
            "The upstream parquet is referenced by absolute path and is not copied into this bundle.",
            "",
            "## Contents",
            "",
            "- `metrics/flywire_lif_metrics.json`: provenance-aware aggregate metrics.",
            "- `tables/`: per-trial, per-neuron, and declared input/readout tables.",
            "- `figures/`: overview, raster, and input/readout rate charts.",
            "- `video/neural_activity_raster.gif`: simple animation of recorded spikes, if generated.",
            "- `manifests/baseline_manifest.json`: source hashes, upstream commit, and scope boundary.",
            "",
            "## Interpretation boundary",
            "",
            "This is a computational neural baseline. It must not be presented as biological Parkinson validation or as a FlyGym locomotion result.",
            "",
        ]
    )
    output_root.mkdir(parents=True, exist_ok=True)
    readme_path = output_root / "README.md"
    readme_path.write_text(readme, encoding="utf-8")
    artifact_paths = [metrics_path, readme_path]
    artifact_paths.extend(Path(path) for path in tables.values())
    artifact_paths.extend(Path(path) for path in figures)
    if animation:
        artifact_paths.append(Path(animation))
    checksums = {
        path.resolve().relative_to(output_root).as_posix(): _sha256(path.resolve())
        for path in artifact_paths
    }
    checksums_path = output_root / "manifests" / "checksums.sha256"
    checksums_path.write_text(
        "".join(f"{digest}  {relative}\n" for relative, digest in sorted(checksums.items())),
        encoding="utf-8",
    )
    manifest["generated"]["checksums_sha256"] = str(checksums_path.resolve())
    manifest["artifact_checksums"] = checksums
    _json_dump(output_root / "manifests" / "baseline_manifest.json", manifest)
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spikes", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--duration-s", type=float, default=1.0)
    parser.add_argument("--activation-hz", type=float, default=150.0)
    parser.add_argument("--completeness", type=Path, default=None)
    parser.add_argument("--connectivity", type=Path, default=None)
    parser.add_argument("--input-id", action="append", default=[])
    parser.add_argument("--readout-id", action="append", default=[])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    manifest = build_artifact(
        spike_path=args.spikes,
        output_root=args.output_root,
        model_root=args.model_root,
        duration_s=args.duration_s,
        completeness_path=args.completeness,
        connectivity_path=args.connectivity,
        input_ids=args.input_id,
        readout_ids=args.readout_id,
        activation_hz=args.activation_hz,
    )
    print(json.dumps({"status": manifest["status"], "output_root": str(args.output_root.resolve())}, indent=2))
    print(f"Figures: {len(manifest['generated']['figures'])}")
    print(f"Animation: {manifest['generated']['neural_activity_animation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
