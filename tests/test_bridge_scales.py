import csv
import json
from pathlib import Path

import pytest

from drosophila_pd_neural import bridge


def _write_annotations(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["neuron_id", "motor_role"])
        writer.writeheader()
        writer.writerows(
            [
                {"neuron_id": "f1", "motor_role": "forward locomotion"},
                {"neuron_id": "f2", "motor_role": "forward locomotion"},
                {"neuron_id": "l1", "motor_role": "left turning"},
                {"neuron_id": "r1", "motor_role": "right turning"},
            ]
        )


def _write_run_manifest(path: Path, trial_count: int, *, status: str = "PASS") -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": bridge.RUN_MANIFEST_SCHEMA_VERSION,
                "status": status,
                "trial_count": trial_count,
            }
        ),
        encoding="utf-8",
    )


def test_bridge_scales_are_deterministic_and_record_readout_gaps(tmp_path, monkeypatch) -> None:
    pd = pytest.importorskip("pandas")
    annotations = tmp_path / "annotations.csv"
    reference_path = tmp_path / "reference.parquet"
    condition_path = tmp_path / "condition.parquet"
    reference_manifest = tmp_path / "reference.manifest.json"
    condition_manifest = tmp_path / "condition.manifest.json"
    _write_annotations(annotations)
    _write_run_manifest(reference_manifest, 3)
    _write_run_manifest(condition_manifest, 3)
    reference_path.write_bytes(b"reference")
    condition_path.write_bytes(b"condition")

    reference = pd.DataFrame({"flywire_id": ["f1", "f2"], "trial": [0, 0]})
    condition = pd.DataFrame(
        {"flywire_id": ["f1", "f1", "l1", "r1"], "trial": [0, 0, 0, 0]}
    )
    monkeypatch.setattr(
        bridge,
        "_read_spikes",
        lambda path: reference if path == reference_path else condition,
    )

    result = bridge.build_bridge_scales(
        reference_spikes=reference_path,
        condition_spikes=condition_path,
        annotations=annotations,
        model="test",
        reference_manifest=reference_manifest,
        condition_manifest=condition_manifest,
        allow_missing_turn=True,
        condition_label="unit-test",
    )

    assert result["status"] == "PASS_WITH_READOUT_GAPS"
    assert result["motor_scale"] == pytest.approx(1.0)
    assert result["coupling_scale"] == pytest.approx(1.0)
    assert result["readout_summary"]["groups"]["forward"]["condition_rate_hz"] == pytest.approx(1 / 3)
    assert result["readout_summary"]["reference_trial_count"] == 3
    assert result["readout_summary"]["condition_trial_count"] == 3
    assert result["biological_mechanism"]["validated_biologically"] is False
    assert result["provenance"]["sha256"]["annotations"]


def test_bridge_rejects_zero_reference_forward_readout(tmp_path, monkeypatch) -> None:
    pd = pytest.importorskip("pandas")
    annotations = tmp_path / "annotations.csv"
    reference_path = tmp_path / "reference.parquet"
    condition_path = tmp_path / "condition.parquet"
    reference_manifest = tmp_path / "reference.manifest.json"
    condition_manifest = tmp_path / "condition.manifest.json"
    _write_annotations(annotations)
    _write_run_manifest(reference_manifest, 1)
    _write_run_manifest(condition_manifest, 1)
    reference_path.write_bytes(b"reference")
    condition_path.write_bytes(b"condition")
    reference = pd.DataFrame({"flywire_id": ["l1"], "trial": [0]})
    condition = pd.DataFrame({"flywire_id": ["l1"], "trial": [0]})
    monkeypatch.setattr(
        bridge,
        "_read_spikes",
        lambda path: reference if path == reference_path else condition,
    )

    with pytest.raises(ValueError, match="Reference forward readout is zero"):
        bridge.build_bridge_scales(
            reference_spikes=reference_path,
            condition_spikes=condition_path,
            annotations=annotations,
            model="test",
            reference_manifest=reference_manifest,
            condition_manifest=condition_manifest,
        )


def test_bridge_rejects_missing_trial_manifest_even_when_spikes_have_trials(tmp_path, monkeypatch) -> None:
    pd = pytest.importorskip("pandas")
    annotations = tmp_path / "annotations.csv"
    reference_path = tmp_path / "reference.parquet"
    condition_path = tmp_path / "condition.parquet"
    _write_annotations(annotations)
    reference_path.write_bytes(b"reference")
    condition_path.write_bytes(b"condition")
    frame = pd.DataFrame({"flywire_id": ["f1"], "trial": [0]})
    monkeypatch.setattr(bridge, "_read_spikes", lambda path: frame)

    with pytest.raises(FileNotFoundError):
        bridge.build_bridge_scales(
            reference_spikes=reference_path,
            condition_spikes=condition_path,
            annotations=annotations,
            model="test",
            reference_manifest=tmp_path / "missing-reference.manifest.json",
            condition_manifest=tmp_path / "missing-condition.manifest.json",
        )


def test_silent_spike_table_uses_declared_trial_count(tmp_path, monkeypatch) -> None:
    pd = pytest.importorskip("pandas")
    annotations = tmp_path / "annotations.csv"
    reference_path = tmp_path / "reference.parquet"
    condition_path = tmp_path / "condition.parquet"
    reference_manifest = tmp_path / "reference.manifest.json"
    condition_manifest = tmp_path / "condition.manifest.json"
    _write_annotations(annotations)
    _write_run_manifest(reference_manifest, 2)
    _write_run_manifest(condition_manifest, 2)
    reference_path.write_bytes(b"reference")
    condition_path.write_bytes(b"condition")
    reference = pd.DataFrame({"flywire_id": ["f1"], "trial": [0]})
    condition = pd.DataFrame(columns=["flywire_id", "trial"])
    monkeypatch.setattr(
        bridge,
        "_read_spikes",
        lambda path: reference if path == reference_path else condition,
    )

    result = bridge.build_bridge_scales(
        reference_spikes=reference_path,
        condition_spikes=condition_path,
        annotations=annotations,
        model="test",
        reference_manifest=reference_manifest,
        condition_manifest=condition_manifest,
        allow_missing_turn=True,
    )

    assert result["readout_summary"]["reference_trial_count"] == 2
    assert result["readout_summary"]["condition_trial_count"] == 2
    assert result["readout_summary"]["groups"]["forward"]["condition_rate_hz"] == 0.0


def test_bridge_rejects_non_finite_duration(tmp_path) -> None:
    annotations = tmp_path / "annotations.csv"
    reference_path = tmp_path / "reference.parquet"
    condition_path = tmp_path / "condition.parquet"
    reference_manifest = tmp_path / "reference.manifest.json"
    condition_manifest = tmp_path / "condition.manifest.json"
    _write_annotations(annotations)
    _write_run_manifest(reference_manifest, 1)
    _write_run_manifest(condition_manifest, 1)
    reference_path.write_bytes(b"reference")
    condition_path.write_bytes(b"condition")

    with pytest.raises(ValueError, match="finite positive"):
        bridge.build_bridge_scales(
            reference_spikes=reference_path,
            condition_spikes=condition_path,
            annotations=annotations,
            model="test",
            reference_manifest=reference_manifest,
            condition_manifest=condition_manifest,
            duration_s=float("nan"),
        )


def test_bridge_rejects_failed_run_manifest(tmp_path) -> None:
    manifest = tmp_path / "failed.run.json"
    _write_run_manifest(manifest, 2, status="FAILED")

    with pytest.raises(ValueError, match="status must be PASS"):
        bridge.load_declared_trial_count(manifest)


def test_id_scope_requires_namespace_and_inventory(tmp_path) -> None:
    manifest = tmp_path / "scoped.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": bridge.RUN_MANIFEST_SCHEMA_VERSION,
                "status": "PASS",
                "trial_count": 1,
                "id_namespace": "flywire-v1",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="neuron_ids inventory"):
        bridge.load_declared_id_scope(manifest)


def test_id_scope_rejects_annotation_or_spike_outside_inventory() -> None:
    class Column:
        def __init__(self, values):
            self.values = values

        def tolist(self):
            return list(self.values)

    class Frame:
        def __init__(self, values):
            self.values = values

        def __getitem__(self, key):
            return Column(self.values)

    scope = {
        "id_namespace": "flywire-v1",
        "dataset_id": "dataset-a",
        "neuron_ids": ["f1"],
    }
    rows = [
        {
            "neuron_id": "unknown",
            "motor_role": "forward locomotion",
            "id_namespace": "flywire-v1",
            "dataset_id": "dataset-a",
        }
    ]

    with pytest.raises(ValueError, match="outside the declared inventory"):
        bridge._validate_id_scope(
            rows,
            Frame(["f1"]),
            Frame(["f1"]),
            scope,
            scope,
        )

    rows[0]["neuron_id"] = "f1"
    with pytest.raises(ValueError, match="outside the declared inventory"):
        bridge._validate_id_scope(
            rows,
            Frame(["unknown"]),
            Frame(["f1"]),
            scope,
            scope,
        )
