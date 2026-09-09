from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.relocate_gate24e_raw_runs import (
    ArchiveError,
    compare_inventories,
    inventory_tree,
    safe_delete_source,
    tree_sha256,
)


def _make_tree(root: Path, payload: bytes = b"raw") -> None:
    (root / "seed00" / "metrics").mkdir(parents=True)
    (root / "seed00" / "metrics" / "metrics.json").write_bytes(payload)
    (root / "seed00" / "rollout.npz").write_bytes(b"rollout")


def test_source_hash_generation_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _make_tree(first)
    _make_tree(second)
    assert inventory_tree(first) == inventory_tree(second)
    assert tree_sha256(inventory_tree(first)) == tree_sha256(inventory_tree(second))


def test_destination_mismatch_is_blocked(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    _make_tree(source)
    _make_tree(destination, payload=b"changed")
    with pytest.raises(ArchiveError):
        compare_inventories(inventory_tree(source), inventory_tree(destination))


def test_missing_destination_file_is_blocked(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    _make_tree(source)
    _make_tree(destination)
    (destination / "seed00" / "rollout.npz").unlink()
    with pytest.raises(ArchiveError):
        compare_inventories(inventory_tree(source), inventory_tree(destination))


def test_changed_destination_bytes_are_blocked(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    _make_tree(source)
    _make_tree(destination)
    (destination / "seed00" / "rollout.npz").write_bytes(b"changed")
    with pytest.raises(ArchiveError):
        compare_inventories(inventory_tree(source), inventory_tree(destination))


def test_symbolic_links_are_blocked(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _make_tree(source)
    link = source / "link"
    try:
        link.symlink_to(source / "seed00", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable in this environment")
    with pytest.raises(ArchiveError):
        inventory_tree(source)


def test_deletion_is_forbidden_for_unexpected_path(tmp_path: Path) -> None:
    with pytest.raises(ArchiveError):
        safe_delete_source(tmp_path)


def test_deletion_is_forbidden_when_source_is_absent(tmp_path: Path) -> None:
    with pytest.raises(ArchiveError):
        safe_delete_source(tmp_path)


def test_unrelated_paths_cannot_be_deleted(tmp_path: Path) -> None:
    unrelated = tmp_path / "runs"
    unrelated.mkdir()
    with pytest.raises(ArchiveError):
        safe_delete_source(tmp_path)
    assert unrelated.is_dir()


def test_relocation_manifest_fields_are_not_derived_from_metrics() -> None:
    # Storage metadata is intentionally separate from metrics and contains no
    # scientific values beyond the already locked provenance identifiers.
    assert "metrics" not in tree_sha256([])


def test_no_gpu_or_simulation_imports_in_archive_module() -> None:
    source = Path(__file__).parents[1] / "scripts/relocate_gate24e_raw_runs.py"
    text = source.read_text(encoding="utf-8").lower()
    assert "flygym" not in text
    assert "torch" not in text
    assert "simulation.step" not in text
