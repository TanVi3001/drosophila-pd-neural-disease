from pathlib import Path

import pytest

from scripts.compact_results import compact, plan_compaction


def test_compaction_keeps_metrics_and_plans_only_known_large_files(tmp_path: Path) -> None:
    root = tmp_path / "results"
    (root / "seed_000" / "metrics").mkdir(parents=True)
    (root / "seed_000" / "viewer_bundle").mkdir()
    (root / "seed_000" / "rollout.npz").write_bytes(b"raw")
    (root / "seed_000" / "viewer_pose.json").write_bytes(b"pose")
    (root / "seed_000" / "viewer_bundle" / "viewer_pose.json").write_bytes(b"pose2")
    (root / "seed_000" / "metrics" / "metrics.json").write_text("{}", encoding="utf-8")
    (root / "seed_000" / "manifest.json").write_text("{}", encoding="utf-8")
    plan = plan_compaction(root)
    paths = {item["path"] for item in plan["candidates"]}
    assert "seed_000/rollout.npz" in paths
    assert "seed_000/viewer_pose.json" in paths
    assert "seed_000/viewer_bundle/viewer_pose.json" in paths
    assert "seed_000/metrics/metrics.json" not in paths
    assert "seed_000/manifest.json" not in paths


def test_compaction_can_keep_representative_video_and_apply_with_hashes(tmp_path: Path) -> None:
    root = tmp_path / "results"
    root.mkdir()
    (root / "rollout.json").write_text("raw", encoding="utf-8")
    (root / "keep.mp4").write_bytes(b"video")
    (root / "drop.mp4").write_bytes(b"video")
    report = tmp_path / "report.json"
    payload = compact(
        root,
        apply=True,
        report_path=report,
        drop_viewer=True,
        include_videos=True,
        keep_globs=["keep.mp4"],
        enforce_results_root=False,
    )
    assert payload["status"] == "APPLIED"
    assert not (root / "rollout.json").exists()
    assert not (root / "drop.mp4").exists()
    assert (root / "keep.mp4").is_file()
    assert payload["candidates"][0]["sha256"]


def test_cli_root_must_be_results_child(tmp_path: Path) -> None:
    from scripts.compact_results import _safe_cli_root

    with pytest.raises(ValueError):
        _safe_cli_root(Path("C:/outside-results"))
