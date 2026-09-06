"""Validate the human-review handoff for disease gene-to-neuron mappings."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "research/disease_mapping/gene_specific_mapping_review.csv"
DEFAULT_OUTPUT = ROOT / "experiments/gate_20a_disease_mapping"
EXPECTED_CONDITIONS = {"alpha_synuclein", "pink1", "parkin", "dj1", "lrrk2"}
APPROVED = "APPROVED"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{str(key): str(value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def audit(path: Path) -> dict[str, Any]:
    rows = _rows(path)
    required = {
        "condition_id",
        "gene_model",
        "paper_provenance",
        "literature_neural_scope",
        "requested_model_scope",
        "connectome_version",
        "mapping_identifier_type",
        "mapping_identifier_count",
        "mapping_identifier_source",
        "driver_scope",
        "reviewer_2",
        "review_date",
        "mapping_status",
        "decision",
        "allowed_use",
        "blockers_vi",
    }
    if not rows:
        raise ValueError("Mapping review file khong co record.")
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Mapping review file thieu cot: {', '.join(sorted(missing))}")
    seen = {row["condition_id"] for row in rows}
    if seen != EXPECTED_CONDITIONS:
        raise ValueError(f"Mapping review phai co dung 5 condition: {sorted(EXPECTED_CONDITIONS)}")

    blockers: list[dict[str, str]] = []
    approved_count = 0
    for row in rows:
        condition_id = row["condition_id"]
        try:
            identifier_count = int(row["mapping_identifier_count"])
        except ValueError as exc:
            raise ValueError(f"{condition_id}: mapping_identifier_count phai la so nguyen") from exc
        if identifier_count < 0:
            raise ValueError(f"{condition_id}: mapping_identifier_count khong the am")
        if not row["paper_provenance"] or not row["mapping_identifier_source"]:
            blockers.append({"condition_id": condition_id, "reason": "provenance is missing"})
        if not row["reviewer_2"] or not _valid_date(row["review_date"]):
            blockers.append({"condition_id": condition_id, "reason": "reviewer_2/review_date is missing or invalid"})
        if row["mapping_status"] == APPROVED:
            approved_count += 1
            if identifier_count == 0:
                blockers.append({"condition_id": condition_id, "reason": "approved mapping has zero identifiers"})
            if row["decision"] != APPROVED:
                blockers.append({"condition_id": condition_id, "reason": "approved mapping decision is not APPROVED"})

    return {
        "schema_version": "gene-specific-mapping-review-v1",
        "source": {"path": str(path.resolve()), "sha256": _sha256(path)},
        "condition_count": len(rows),
        "approved_mapping_count": approved_count,
        "status": "MAPPING_REVIEW_READY_FOR_HUMAN_SIGNOFF" if not blockers and approved_count else "MAPPING_REVIEW_BLOCKED",
        "conditions": rows,
        "blockers": blockers,
        "no_root_id_inference": True,
        "no_simulation_run": True,
        "no_calibration_run": True,
        "no_holdout_validation_run": True,
        "data_fabricated": False,
        "scientific_scope": "Mapping handoff audit; no gene-specific or biological Parkinson validation.",
    }


def _write_report(path: Path, document: Mapping[str, Any]) -> None:
    lines = [
        "# Gene-specific mapping review handoff",
        "",
        f"**Trạng thái:** `{document['status']}`",
        "",
        f"- Condition: `{document['condition_count']}`.",
        f"- Mapping APPROVED: `{document['approved_mapping_count']}`.",
        "- Không suy ra root ID từ tên gene.",
        "- Không chạy simulation, calibration hoặc holdout.",
        "",
        "| Condition | Mapping status | Decision | Số ID | Phạm vi được phép |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in document["conditions"]:
        lines.append(
            f"| `{row['condition_id']}` | `{row['mapping_status']}` | `{row['decision']}` | {row['mapping_identifier_count']} | {row['allowed_use']} |"
        )
    lines.extend(
        [
            "",
            "## Quy tắc chuyển trạng thái",
            "",
            "Chỉ chuyển `mapping_status` sang `APPROVED` khi file export root-ID/edge-ID có provenance connectome, driver/cell scope, reviewer và ngày review. Không xem mapping class-level hoặc whole-animal là gene-specific.",
            "",
            "## Giới hạn",
            "",
            "Hồ sơ này bổ sung handoff có kiểm soát; nó không tạo neuron ID mới và không phải bằng chứng biological Parkinson validation.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(*, input_path: Path, output_root: Path) -> int:
    document = audit(input_path.resolve())
    output_root.mkdir(parents=True, exist_ok=True)
    results = output_root / "results"
    manifests = output_root / "manifests"
    results.mkdir(exist_ok=True)
    manifests.mkdir(exist_ok=True)
    report = results / "gene_specific_mapping_review.md"
    manifest = manifests / "gene_specific_mapping_review_manifest.json"
    _write_report(report, document)
    document = dict(document)
    document["report"] = str(report.resolve())
    manifest.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Status: {document['status']}")
    print(f"Approved mappings: {document['approved_mapping_count']}/{document['condition_count']}")
    print(f"Report: {report.resolve()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(input_path=args.input, output_root=args.output_root)
    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
