import json
from pathlib import Path

from scripts.check_neural_inputs import inspect_brain_root


def test_missing_brain_source_is_waiting(tmp_path: Path) -> None:
    report = inspect_brain_root(tmp_path / "missing")
    assert report["status"] == "WAITING_BRAIN_DATA"
    assert report["simulation_run"] is False


def test_complete_file_shape_is_ready_but_license_stays_unverified(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    for relative in (
        "brain_body_bridge.py",
        "code/run_pytorch.py",
        "data/2025_Completeness_783.csv",
        "data/2025_Connectivity_783.parquet",
        "data/flywire_annotations.tsv",
        "data/plastic_weights.pt",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder", encoding="utf-8")
    report = inspect_brain_root(root)
    assert report["status"] == "READY"
    assert report["integrity"]["status"] == "UNVERIFIED_NO_MANIFEST"
    assert report["license_status"] == "UNVERIFIED"


def test_manifest_mismatch_invalidates_brain_data(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    records = []
    for relative in (
        "brain_body_bridge.py",
        "code/run_pytorch.py",
        "data/2025_Completeness_783.csv",
        "data/2025_Connectivity_783.parquet",
        "data/flywire_annotations.tsv",
        "data/plastic_weights.pt",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder", encoding="utf-8")
        records.append({"path": relative, "size": path.stat().st_size, "sha256": "0" * 64})
    (root / "source_manifest.json").write_text(
        json.dumps({"files": records}), encoding="utf-8"
    )

    report = inspect_brain_root(root)

    assert report["status"] == "INVALID_BRAIN_DATA"
    assert report["integrity"]["status"] == "FAILED"
