"""Kiểm tra đầu vào neural ngoài repository, không chạy simulation."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path


REQUIRED_FILES = (
    "brain_body_bridge.py",
    "code/run_pytorch.py",
    "data/2025_Completeness_783.csv",
    "data/2025_Connectivity_783.parquet",
    "data/plastic_weights.pt",
)


def _license_status(root: Path) -> str:
    license_path = root / "LICENSE"
    if not license_path.is_file():
        return "UNVERIFIED"
    try:
        text = license_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return "UNVERIFIED"
    return "VERIFIED_MIT" if "MIT License" in text else "UNVERIFIED"


def inspect_brain_root(root: Path) -> dict[str, object]:
    checks = {relative: (root / relative).is_file() for relative in REQUIRED_FILES}
    missing = [relative for relative, present in checks.items() if not present]
    status = "READY" if not missing else "WAITING_BRAIN_DATA"
    return {
        "status": status,
        "brain_root": str(root),
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "required_files": checks,
        "license_status": _license_status(root),
        "data_license_status": "REVIEW_CC_BY_NC_4_0",
        "simulation_run": False,
        "message": (
            "Brain source da du file bat buoc; can review license va annotation truoc khi chay."
            if not missing
            else f"Thieu dau vao neural: {', '.join(missing)}"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    # Keep CLI help ASCII so it remains usable on Windows consoles using CP1252.
    parser = argparse.ArgumentParser(description="Check external neural inputs without running simulation.")
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
