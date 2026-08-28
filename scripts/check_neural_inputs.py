"""Kiểm tra đầu vào neural ngoài repository, không chạy simulation."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path


REQUIRED_FILES = (
    "brain_body_bridge.py",
    "run_pytorch.py",
    "data/2025_Completeness_783.csv",
    "data/2025_Connectivity_783.parquet",
)
OPTIONAL_FILES = ("data/plastic_weights.pt",)


def inspect_brain_root(root: Path) -> dict[str, object]:
    checks = {relative: (root / relative).is_file() for relative in REQUIRED_FILES}
    optional = {relative: (root / relative).is_file() for relative in OPTIONAL_FILES}
    missing = [relative for relative, present in checks.items() if not present]
    status = "READY" if not missing else "WAITING_BRAIN_DATA"
    return {
        "status": status,
        "brain_root": str(root),
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "required_files": checks,
        "optional_files": optional,
        "license_status": "UNVERIFIED",
        "simulation_run": False,
        "message": (
            "Brain source da du file bat buoc; can review license va annotation truoc khi chay."
            if not missing
            else f"Thieu dau vao neural: {', '.join(missing)}"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brain-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = inspect_brain_root(args.brain_root)
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    print(text, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    return 0 if report["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
