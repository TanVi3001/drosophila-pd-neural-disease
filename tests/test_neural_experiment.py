from pathlib import Path
from zipfile import ZipFile

from scripts.run_neural_campaign import _baseline_comparisons, _seeds
from scripts.run_neural_experiment import _recover_viewer_bundle, _stage_source, build_parser


def test_seed_parser_accepts_multiple_nonnegative_seeds() -> None:
    assert _seeds("0, 2,5") == [0, 2, 5]


def test_baseline_comparison_uses_only_matching_passed_seeds() -> None:
    rows = [
        {"condition": "healthy", "seed": 0, "status": "PASS", "metric_count": 1, "speed": 2.0},
        {"condition": "pink1", "seed": 0, "status": "PASS", "metric_count": 1, "speed": 1.5},
        {"condition": "pink1", "seed": 1, "status": "WAITING_TARGET_DATA", "metric_count": 0},
    ]
    assert _baseline_comparisons(rows) == [
        {"condition": "pink1", "seed": 0, "metric": "speed", "baseline": 2.0, "condition_value": 1.5, "delta": -0.5}
    ]


def test_experiment_parser_defaults_to_healthy_without_config() -> None:
    args = build_parser().parse_args(["--output", "results/healthy"])
    assert args.config is None
    assert args.video is False


def test_stage_source_copies_required_files_without_mutating_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    stage = tmp_path / "stage"
    checkpoint = source / "data" / "plastic_weights.pt"
    for relative in (
        "brain_body_bridge.py",
        "code/run_pytorch.py",
        "code/benchmark.py",
        "data/2025_Completeness_783.csv",
        "data/2025_Connectivity_783.parquet",
    ):
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(relative.encode("ascii"))
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_bytes(b"checkpoint")
    _stage_source(source, stage, checkpoint)
    for relative in (
        "brain_body_bridge.py",
        "code/run_pytorch.py",
        "code/benchmark.py",
        "data/2025_Completeness_783.csv",
        "data/2025_Connectivity_783.parquet",
        "data/plastic_weights.pt",
    ):
        assert (stage / relative).read_bytes() == (source / relative).read_bytes()


def test_bundle_recovery_streams_existing_stage(tmp_path: Path) -> None:
    output = tmp_path / "output"
    stage = output / "viewer_bundle"
    stage.mkdir(parents=True)
    (stage / "index.html").write_text("<!doctype html>", encoding="utf-8")
    (stage / "viewer" / "pose.js").parent.mkdir()
    (stage / "viewer" / "pose.js").write_text("ok", encoding="utf-8")
    assert _recover_viewer_bundle(output) is True
    with ZipFile(output / "viewer_bundle.zip") as archive:
        assert "viewer_bundle/index.html" in archive.namelist()
        assert "viewer_bundle/manifest.json" in archive.namelist()
