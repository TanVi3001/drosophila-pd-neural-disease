"""Compare Track A and Track B only when both evidence packages exist."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from drosophila_pd_neural.riemensperger2011.protocol import read_json, write_json


def triangulate(*, track_a: Path, track_b: Path, output: Path) -> dict[str, Any]:
    a = read_json(track_a) if track_a.is_file() else {}
    b = read_json(track_b) if track_b.is_file() else {}
    result = {
        "status": "WAITING_TRACK_B_DATA" if not b or b.get("status") not in {"GENE_SPECIFIC_VALIDATION_SUPPORTED", "GENE_SPECIFIC_VALIDATION_INCONCLUSIVE", "GENE_SPECIFIC_VALIDATION_NOT_SUPPORTED"} else "TRIANGULATION_READY_FOR_REVIEW",
        "track_a_status": a.get("status", "NOT_AVAILABLE"),
        "track_b_status": b.get("status", "NOT_AVAILABLE"),
        "real_effect_ratio": "NOT_AVAILABLE",
        "virtual_effect_ratio": "NOT_AVAILABLE",
        "direction_concordance": "NOT_AVAILABLE",
        "effect_magnitude_comparison": "NOT_AVAILABLE",
        "assay_difference": "Must be reviewed; Track A and Track B are not assumed equivalent.",
        "gene_scope_difference": "Track A is dopamine-class exploratory; Track B requires gene-specific evidence.",
        "data_fabricated": False,
        "claim": "Triangulation cannot support a biological claim without independent Track B evidence.",
    }
    write_json(output, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track-a", type=Path, required=True)
    parser.add_argument("--track-b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = triangulate(track_a=args.track_a, track_b=args.track_b, output=args.output)
    print(f"Status: {result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
