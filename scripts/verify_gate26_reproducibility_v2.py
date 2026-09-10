"""Verify Gate26 reproducibility hashes against exact Git blob bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "experiments/gate_26_riemensperger_full_completion/manifests/reproducibility_inventory_v2_git_blob.json"


def git_blob(ref: str, path: str) -> bytes:
    return subprocess.run(["git", "cat-file", "blob", f"{ref}:{path}"], cwd=ROOT, stdout=subprocess.PIPE, check=True).stdout


def verify(ref: str = "HEAD") -> tuple[int, list[str]]:
    document = json.loads(INVENTORY.read_text(encoding="utf-8"))
    failures: list[str] = []
    records = document.get("records", [])
    for record in records:
        path = record["path"]
        blob = git_blob(ref, path)
        actual_sha = hashlib.sha256(blob).hexdigest()
        if actual_sha != record["sha256"]:
            failures.append(f"{path}: sha256 {actual_sha} != {record['sha256']}")
        if len(blob) != record["size_bytes"]:
            failures.append(f"{path}: size {len(blob)} != {record['size_bytes']}")
    if document.get("record_count") != len(records):
        failures.append("inventory record_count does not match records")
    return len(records), failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default="HEAD")
    args = parser.parse_args()
    count, failures = verify(args.ref)
    if failures:
        print("GATE26_CANONICAL_REPRODUCIBILITY_FAILED")
        print(f"verified_records={count}")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("GATE26_CANONICAL_REPRODUCIBILITY_PASS")
    print(f"verified_records={count}/{count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
