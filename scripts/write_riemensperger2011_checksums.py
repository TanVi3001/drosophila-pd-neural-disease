"""Write portable SHA256 manifests for the committed Riemensperger gate artifacts."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
GATES = (
    ROOT / "experiments/gate_21a_riemensperger_evidence_lock",
    ROOT / "experiments/gate_21b_riemensperger_healthy",
    ROOT / "experiments/gate_21c_riemensperger_healthy_comparability",
    ROOT / "experiments/gate_21d_riemensperger_dopamine_mapping",
    ROOT / "experiments/gate_21e_riemensperger_disease",
    ROOT / "experiments/gate_21f_four_group_analysis",
    ROOT / "experiments/gate_21g_riemensperger_robustness",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_gate_checksums(gate: Path) -> Path:
    """Write hashes relative to one gate, never embedding a machine path."""

    manifest = gate / "manifests/checksums.sha256"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(gate.rglob("*")):
        if not path.is_file() or path == manifest:
            continue
        rows.append(f"{_sha256(path)}  {path.relative_to(gate).as_posix()}")
    manifest.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, action="append", help="Gate directory; repeat to limit the update.")
    args = parser.parse_args(argv)
    gates = [path.resolve() for path in args.gate] if args.gate else list(GATES)
    for gate in gates:
        print(write_gate_checksums(gate))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
