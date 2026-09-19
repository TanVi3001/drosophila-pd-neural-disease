"""Inspect the canonical FlyGym platform integration contract read-only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from drosophila_pd_neural.platform_contract import (  # noqa: E402
    default_platform_root,
    inspect_platform,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform-root", type=Path, default=default_platform_root())
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    contract = inspect_platform(args.platform_root)
    if args.json:
        print(json.dumps(contract.as_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"Platform: {contract.root}")
        print(f"Status: {contract.status}")
        print(f"Commit: {contract.git_commit or 'UNAVAILABLE'}")
        print(f"Capabilities: {', '.join(contract.capabilities) or 'NONE'}")
        for blocker in contract.blockers:
            print(f"Blocker: {blocker}")
    return 0 if contract.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
