"""Audit and compact large local simulation artifacts safely.

The command keeps small scientific summaries and removes only explicitly
recognized frame-level artifacts under a user-selected ``results/`` child.
It is a dry-run by default; ``--apply`` is required for deletion.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import fnmatch
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = (ROOT / "results").resolve()
COMPACT_FILE_NAMES = {
    "rollout.npz",
    "rollout.csv",
    "rollout.json",
    "viewer_pose.json",
    "viewer_bundle.zip",
}
VIDEO_SUFFIXES = {".mp4", ".avi", ".mov"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _matches_keep(relative: str, keep_globs: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(relative, pattern) for pattern in keep_globs)


def _candidate_kind(path: Path, *, drop_viewer: bool, include_videos: bool) -> str | None:
    if path.name in {"rollout.npz", "rollout.csv", "rollout.json"}:
        return "raw_rollout"
    if drop_viewer and (path.name == "viewer_pose.json" or "viewer_bundle" in path.parts):
        return "viewer_artifact"
    if path.name == "viewer_bundle.zip" and drop_viewer:
        return "viewer_artifact"
    if include_videos and path.suffix.lower() in VIDEO_SUFFIXES:
        return "video"
    return None


def plan_compaction(
    root: str | Path,
    *,
    drop_viewer: bool = True,
    include_videos: bool = False,
    keep_globs: Iterable[str] = (),
) -> dict[str, Any]:
    """Return a deletion plan without modifying files."""

    base = Path(root).expanduser().resolve()
    if not base.is_dir():
        raise ValueError(f"Results root does not exist: {base}")
    keep = tuple(str(pattern).replace("\\", "/") for pattern in keep_globs)
    candidates: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    for path in sorted(item for item in base.rglob("*") if item.is_file() and not item.is_symlink()):
        relative = _relative(path, base)
        kind = _candidate_kind(path, drop_viewer=drop_viewer, include_videos=include_videos)
        record = {
            "path": relative,
            "size_bytes": path.stat().st_size,
            "kind": kind or "retained",
        }
        if kind and not _matches_keep(relative, keep):
            candidates.append(record)
        else:
            retained.append(record)
    before_bytes = sum(int(item["size_bytes"]) for item in candidates + retained)
    reclaimable_bytes = sum(int(item["size_bytes"]) for item in candidates)
    return {
        "root": str(base),
        "drop_viewer": drop_viewer,
        "include_videos": include_videos,
        "keep_globs": list(keep),
        "file_count": len(candidates) + len(retained),
        "candidate_count": len(candidates),
        "retained_count": len(retained),
        "before_bytes": before_bytes,
        "reclaimable_bytes": reclaimable_bytes,
        "candidates": candidates,
        "retained": retained,
    }


def _safe_cli_root(value: str | Path) -> Path:
    root = Path(value).expanduser().resolve()
    if root == RESULTS_ROOT or not root.is_relative_to(RESULTS_ROOT):
        raise ValueError(f"Only a child of results/ may be compacted: {root}")
    return root


def _with_hashes(records: list[dict[str, Any]], root: Path) -> list[dict[str, Any]]:
    hashed: list[dict[str, Any]] = []
    for record in records:
        path = root / str(record["path"])
        if not path.is_file():
            raise OSError(f"Artifact disappeared before hashing: {path}")
        hashed.append({**record, "sha256": _sha256(path)})
    return hashed


def compact(
    root: str | Path,
    *,
    apply: bool,
    report_path: str | Path,
    drop_viewer: bool,
    include_videos: bool,
    keep_globs: Iterable[str],
    enforce_results_root: bool = True,
) -> dict[str, Any]:
    """Create a compaction audit and optionally delete planned artifacts."""

    base = _safe_cli_root(root) if enforce_results_root else Path(root).expanduser().resolve()
    if not base.is_dir():
        raise ValueError(f"Results root does not exist: {base}")
    plan = plan_compaction(
        base,
        drop_viewer=drop_viewer,
        include_videos=include_videos,
        keep_globs=keep_globs,
    )
    records = _with_hashes(plan["candidates"], base) if apply else plan["candidates"]
    payload: dict[str, Any] = {
        "schema_version": "results-storage-compaction-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "APPLIED" if apply else "DRY_RUN",
        "simulation_data_modified": False,
        "scientific_data_recomputed": False,
        "plan": {key: value for key, value in plan.items() if key not in {"candidates", "retained"}},
        "candidates": records,
        "retained": plan["retained"],
        "policy": {
            "kept": "metrics, manifests, logs, reports and all files outside the explicit compact allowlist",
            "hash_before_delete": apply,
            "delete_requires_explicit_apply": True,
        },
    }
    if apply:
        for record in records:
            path = base / str(record["path"])
            path.unlink()
        payload["deleted_count"] = len(records)
        payload["deleted_bytes"] = sum(int(record["size_bytes"]) for record in records)
        payload["simulation_data_modified"] = True
    destination = Path(report_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def _format_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.2f} {unit}"
        amount /= 1024
    return f"{value} B"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Mot results/ cu the can compact.")
    parser.add_argument("--report", type=Path, default=None, help="JSON audit output; mac dinh nam trong root.")
    parser.add_argument("--apply", action="store_true", help="Xoa artifact trong allowlist sau khi hash.")
    parser.add_argument("--keep-glob", action="append", default=[], help="Glob relative to root that must be retained.")
    parser.add_argument("--keep-viewer", action="store_true", help="Khong xoa viewer_pose/viewer_bundle.")
    parser.add_argument("--include-videos", action="store_true", help="Them MP4/AVI/MOV vao allowlist compact.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = _safe_cli_root(args.root)
        report = args.report or root / "storage_compaction_report.json"
        payload = compact(
            root,
            apply=args.apply,
            report_path=report,
            drop_viewer=not args.keep_viewer,
            include_videos=args.include_videos,
            keep_globs=args.keep_glob,
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    plan = payload["plan"]
    print(f"Status: {payload['status']}")
    print(f"Root: {plan['root']}")
    print(f"Candidates: {plan['candidate_count']}")
    print(f"Reclaimable: {_format_bytes(int(plan['reclaimable_bytes']))}")
    print(f"Report: {Path(report).resolve()}")
    if not args.apply:
        print("No files deleted. Add --apply only after reviewing the JSON report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
