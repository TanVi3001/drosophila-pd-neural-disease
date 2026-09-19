"""Validate the cross-repository connectome registry without loading large data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from drosophila_pd_neural.connectome import RegistryError, load_registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "configs" / "connectome_source_registry.json",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help="Workspace root used to check cloned repositories and artifact paths.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Also verify pinned git HEADs and SHA-256 checksums.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        registry = load_registry(args.registry)
        report = registry.to_report(
            workspace_root=args.workspace_root,
            verify_git=args.verify,
            verify_checksums=args.verify,
        )
    except (OSError, json.JSONDecodeError, RegistryError) as exc:
        print(f"CONNECTOME_REGISTRY_INVALID: {exc}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("CONNECTOME_REGISTRY_VALID")
        print(f"repositories={report['repository_count']}")
        print(f"artifacts={report['artifact_count']}")
        if args.workspace_root:
            missing_repos = [row["name"] for row in report["repositories"] if not row["exists"]]
            missing_artifacts = [row["artifact_id"] for row in report["artifacts"] if not row["exists"]]
            print(f"missing_repositories={len(missing_repos)}")
            print(f"missing_artifacts={len(missing_artifacts)}")
            if missing_repos:
                print("missing_repo_names=" + ",".join(missing_repos))
            if missing_artifacts:
                print("missing_artifact_ids=" + ",".join(missing_artifacts))
    failures = report.get("verification", {}).get("failures", [])
    if failures:
        if not args.as_json:
            print("verification_failures=" + str(len(failures)))
            for failure in failures:
                print(f"- {failure}")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
